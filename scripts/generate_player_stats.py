import pandas as pd
import json
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

MATCHES_FILE = "public/results/matches.csv"
BONUS_FILE = "public/results/bonus_points.csv"
OUTPUT_FILE = "public/results/generated/player_stats.json"


# ============================================================
# Load data
# ============================================================

matches = pd.read_csv(
    MATCHES_FILE,
    sep=";"
)

bonus_points = pd.read_csv(
    BONUS_FILE,
    sep=";"
)


# ============================================================
# Normalize data
# ============================================================

matches["year"] = matches["year"].astype(int)
matches["month"] = matches["month"].astype(int)
matches["day"] = matches["day"].astype(int)
matches["round"] = matches["round"].astype(int)

matches["player1_score"] = matches["player1_score"].astype(int)
matches["player2_score"] = matches["player2_score"].astype(int)

matches["date"] = pd.to_datetime(
    matches[["year", "month", "day"]]
)

matches["phase"] = matches["phase"].astype(str)

bonus_points["season"] = bonus_points["season"].astype(int)
bonus_points["round"] = bonus_points["round"].astype(int)
bonus_points["bonus"] = bonus_points["bonus"].astype(int)


# ============================================================
# Helper functions
# ============================================================

def percentage(value, total):
    if total == 0:
        return None

    return round(value / total * 100, 2)


def average(values):
    if not values:
        return None

    return round(sum(values) / len(values), 2)


def result(player_score, opponent_score):
    if player_score > opponent_score:
        return "W"

    if player_score < opponent_score:
        return "L"

    return "D"


def get_player_matches(player_id):
    """
    Returns all matches involving the player.

    The returned dataframe always contains:

        player_score
        opponent_score
        opponent_id

    regardless of whether the player was player1 or player2.
    """

    player1_matches = matches[
        matches["player1_id"] == player_id
    ].copy()

    player1_matches["player_score"] = (
        player1_matches["player1_score"]
    )

    player1_matches["opponent_score"] = (
        player1_matches["player2_score"]
    )

    player1_matches["opponent_id"] = (
        player1_matches["player2_id"]
    )

    player2_matches = matches[
        matches["player2_id"] == player_id
    ].copy()

    player2_matches["player_score"] = (
        player2_matches["player2_score"]
    )

    player2_matches["opponent_score"] = (
        player2_matches["player1_score"]
    )

    player2_matches["opponent_id"] = (
        player2_matches["player1_id"]
    )

    player_matches = pd.concat(
        [
            player1_matches,
            player2_matches
        ],
        ignore_index=True
    )

    return (
        player_matches
        .sort_values("date")
        .reset_index(drop=True)
    )


def calculate_streaks(results):
    """
    Calculate current and longest winning/losing streaks.
    """

    longest_winning = 0
    longest_losing = 0

    current_type = None
    current_length = 0

    for r in results:

        if r == current_type:
            current_length += 1
        else:
            current_type = r
            current_length = 1

        if r == "W":
            longest_winning = max(
                longest_winning,
                current_length
            )

        elif r == "L":
            longest_losing = max(
                longest_losing,
                current_length
            )

    current_type = None
    current_length = 0

    if results:

        current_type = results[-1]
        current_length = 1

        for i in range(len(results) - 2, -1, -1):

            if results[i] == current_type:
                current_length += 1
            else:
                break

    return {
        "current": current_length,
        "currentType": current_type,
        "longestWinning": longest_winning,
        "longestLosing": longest_losing,
    }


def calculate_phase_stats(
    player_matches,
    phase
):
    """
    Calculate match and leg statistics for a phase.
    """

    phase_matches = player_matches[
        player_matches["phase"].str.lower()
        == phase.lower()
    ]

    matches_played = len(phase_matches)

    matches_won = int(
        (
            phase_matches["player_score"]
            > phase_matches["opponent_score"]
        ).sum()
    )

    matches_lost = int(
        (
            phase_matches["player_score"]
            < phase_matches["opponent_score"]
        ).sum()
    )

    legs_won = int(
        phase_matches["player_score"].sum()
    )

    legs_lost = int(
        phase_matches["opponent_score"].sum()
    )

    legs_played = (
        legs_won
        + legs_lost
    )

    return {
        "matches": {
            "played": matches_played,
            "won": matches_won,
            "lost": matches_lost,
            "winRate": percentage(
                matches_won,
                matches_played
            ),
        },

        "legs": {
            "played": legs_played,
            "won": legs_won,
            "lost": legs_lost,
            "winRate": percentage(
                legs_won,
                legs_played
            ),
        },
    }


# ============================================================
# Find all players
# ============================================================

player_ids = set(
    matches["player1_id"]
)

player_ids.update(
    matches["player2_id"]
)

player_ids.update(
    bonus_points["player_id"]
)


# ============================================================
# Generate statistics
# ============================================================

player_stats = {}


for player_id in sorted(player_ids):

    player_matches = get_player_matches(
        player_id
    )

    # --------------------------------------------------------
    # Basic match information
    # --------------------------------------------------------

    match_results = [
        result(
            row.player_score,
            row.opponent_score
        )
        for row in player_matches.itertuples()
    ]

    matches_played = len(
        player_matches
    )

    matches_won = match_results.count("W")
    matches_lost = match_results.count("L")

    # --------------------------------------------------------
    # Leg statistics
    # --------------------------------------------------------

    legs_won = int(
        player_matches["player_score"].sum()
    )

    legs_lost = int(
        player_matches["opponent_score"].sum()
    )

    legs_played = (
        legs_won
        + legs_lost
    )

    # --------------------------------------------------------
    # Whitewashes
    #
    # Won the match without losing a leg.
    # --------------------------------------------------------

    whitewashes = int(
        (
            (player_matches["player_score"]
             > player_matches["opponent_score"])
            &
            (player_matches["opponent_score"] == 0)
        ).sum()
    )

    # --------------------------------------------------------
    # Shutouts
    #
    # Lost the match without winning a leg.
    # --------------------------------------------------------

    shutouts = int(
        (
            (player_matches["player_score"]
             < player_matches["opponent_score"])
            &
            (player_matches["player_score"] == 0)
        ).sum()
    )

    # --------------------------------------------------------
    # Streaks
    # --------------------------------------------------------

    streaks = calculate_streaks(
        match_results
    )

    # --------------------------------------------------------
    # Last 10 form
    # --------------------------------------------------------

    last10 = match_results[-10:]

    # --------------------------------------------------------
    # Phase statistics
    # --------------------------------------------------------

    phases = {}

    available_phases = (
        player_matches["phase"]
        .dropna()
        .unique()
    )

    for phase in sorted(available_phases):

        phases[phase] = calculate_phase_stats(
            player_matches,
            phase
        )

    # --------------------------------------------------------
    # Season statistics
    #
    # These do NOT depend on the standings system.
    # --------------------------------------------------------

    seasons = {}

    for season, season_matches in (
        player_matches.groupby("year")
    ):

        season_results = [
            result(
                row.player_score,
                row.opponent_score
            )
            for row in season_matches.itertuples()
        ]

        season_wins = (
            season_results.count("W")
        )

        season_losses = (
            season_results.count("L")
        )

        season_legs_won = int(
            season_matches["player_score"].sum()
        )

        season_legs_lost = int(
            season_matches["opponent_score"].sum()
        )

        seasons[str(int(season))] = {

            "matches": {
                "played": len(season_matches),
                "won": season_wins,
                "lost": season_losses,
                "winRate": percentage(
                    season_wins,
                    len(season_matches)
                ),
            },

            "legs": {
                "played": (
                    season_legs_won
                    + season_legs_lost
                ),
                "won": season_legs_won,
                "lost": season_legs_lost,
                "winRate": percentage(
                    season_legs_won,
                    season_legs_won
                    + season_legs_lost
                ),
            },

            "roundsPlayed": int(
                season_matches["round"]
                .nunique()
            ),

            # TODO:
            # Add season standing once the ranking/
            # points system is known.
            "standing": None,

            # TODO:
            # Add total season points once the
            # points system is known.
            "points": None,
        }

    # --------------------------------------------------------
    # Round statistics
    #
    # These are statistics about the matches in a round.
    # They do NOT assume anything about how a "night"
    # or round standing is calculated.
    # --------------------------------------------------------

    round_results = []

    grouped_rounds = player_matches.groupby(
        ["year", "round"]
    )

    for (
        season,
        round_number
    ), round_matches in grouped_rounds:

        round_wins = int(
            (
                round_matches["player_score"]
                >
                round_matches["opponent_score"]
            ).sum()
        )

        round_losses = int(
            (
                round_matches["player_score"]
                <
                round_matches["opponent_score"]
            ).sum()
        )

        round_legs_won = int(
            round_matches["player_score"].sum()
        )

        round_legs_lost = int(
            round_matches["opponent_score"].sum()
        )

        round_results.append({

            "season": int(season),

            "round": int(round_number),

            "matches": len(round_matches),

            "wins": round_wins,

            "losses": round_losses,

            "winRate": percentage(
                round_wins,
                len(round_matches)
            ),

            "legsWon": round_legs_won,

            "legsLost": round_legs_lost,

            "legWinRate": percentage(
                round_legs_won,
                round_legs_won
                + round_legs_lost
            ),

            # TODO:
            # This is the player's standing after
            # this round. Requires the competition's
            # ranking/points rules.
            "standing": None,

            # TODO:
            # Points awarded during this round.
            "points": None,
        })

    round_results.sort(
        key=lambda x: (
            x["season"],
            x["round"]
        )
    )

    # --------------------------------------------------------
    # Last 10 rounds
    # --------------------------------------------------------

    last10_rounds = sorted(
        round_results,
        key=lambda x: (
            x["season"],
            x["round"]
        ),
        reverse=True
    )[:10]

    # --------------------------------------------------------
    # Bonus points
    #
    # Rules:
    #
    # - Highest checkout in a round = 1 point
    # - 170 checkout = 2 points
    # - Each 180 = 2 points
    #
    # bonus_points.csv already contains only the
    # highest checkout(s) and 180s for each round.
    # --------------------------------------------------------

    player_bonuses = bonus_points[
        bonus_points["player_id"]
        == player_id
    ].sort_values(
        ["season", "round"]
    )

    bonus_history = []

    total_bonus_points = 0
    career_180s = 0
    highest_checkout = None

    # Process each round separately
    for (
        season,
        round_number
    ), round_bonuses in player_bonuses.groupby(
        ["season", "round"]
    ):

        round_bonus_points = 0
        round_180s = 0
        round_checkout = None
        round_checkout_points = 0
        round_180_points = 0

        for row in round_bonuses.itertuples():

            bonus = int(row.bonus)

            # 180
            if bonus == 180:

                round_180s += 1
                round_180_points += 2
                round_bonus_points += 2

            # Checkout
            else:

                # 170 checkout is worth 2 points
                # Any other highest checkout is worth 1 point
                checkout_points = (
                    2
                    if bonus == 170
                    else 1
                )

                round_checkout_points += checkout_points
                round_bonus_points += checkout_points

                if (
                    round_checkout is None
                    or bonus > round_checkout
                ):
                    round_checkout = bonus

                if (
                    highest_checkout is None
                    or bonus > highest_checkout
                ):
                    highest_checkout = bonus

        total_bonus_points += round_bonus_points
        career_180s += round_180s

        bonus_history.append({

            "season": int(season),

            "round": int(round_number),

            "highestCheckout": round_checkout,

            "180s": round_180s,

            "checkoutPoints": round_checkout_points,

            "oneEightyPoints": round_180_points,

            "total": round_bonus_points,
        })

    # Number of bonus events in the CSV
    bonus_events = len(
        player_bonuses
    )

    # --------------------------------------------------------
    # Head-to-head
    # --------------------------------------------------------

    head_to_head = {}

    for (
        opponent_id,
        opponent_matches
    ) in player_matches.groupby(
        "opponent_id"
    ):

        opponent_wins = int(
            (
                opponent_matches["player_score"]
                >
                opponent_matches["opponent_score"]
            ).sum()
        )

        opponent_losses = int(
            (
                opponent_matches["player_score"]
                <
                opponent_matches["opponent_score"]
            ).sum()
        )

        opponent_legs_won = int(
            opponent_matches["player_score"].sum()
        )

        opponent_legs_lost = int(
            opponent_matches["opponent_score"].sum()
        )

        differences = (
            opponent_matches["player_score"]
            -
            opponent_matches["opponent_score"]
        )

        head_to_head[opponent_id] = {

            "matches": len(
                opponent_matches
            ),

            "wins": opponent_wins,

            "losses": opponent_losses,

            "winRate": percentage(
                opponent_wins,
                len(opponent_matches)
            ),

            "legsWon": opponent_legs_won,

            "legsLost": opponent_legs_lost,

            "legWinRate": percentage(
                opponent_legs_won,
                opponent_legs_won
                + opponent_legs_lost
            ),

            "averageScoreDifference": average(
                differences.tolist()
            ),
        }

    # --------------------------------------------------------
    # Dominating opponent
    # --------------------------------------------------------

    dominating = None

    if head_to_head:

        dominating_id = max(
            head_to_head,
            key=lambda opponent:
                head_to_head[opponent]["wins"]
        )

        dominating_wins = (
            head_to_head[dominating_id]["wins"]
        )

        if dominating_wins > 0:

            dominating = {

                "playerId": dominating_id,

                "matchesWon":
                    dominating_wins,
            }

    # --------------------------------------------------------
    # Archenemy
    # --------------------------------------------------------

    archenemy = None

    if head_to_head:

        archenemy_id = max(
            head_to_head,
            key=lambda opponent:
                head_to_head[opponent]["losses"]
        )

        archenemy_losses = (
            head_to_head[archenemy_id]["losses"]
        )

        if archenemy_losses > 0:

            archenemy = {

                "playerId": archenemy_id,

                "matchesLost":
                    archenemy_losses,
            }

    # --------------------------------------------------------
    # Match history
    # --------------------------------------------------------

    match_history = []

    for row in player_matches.itertuples():

        match_history.append({

            "date": row.date.strftime(
                "%Y-%m-%d"
            ),

            "season": int(row.year),

            "round": int(row.round),

            "phase": row.phase,

            "opponentId": row.opponent_id,

            "score": int(
                row.player_score
            ),

            "opponentScore": int(
                row.opponent_score
            ),

            "result": result(
                row.player_score,
                row.opponent_score
            ),
        })

    # --------------------------------------------------------
    # Build final player object
    # --------------------------------------------------------

    player_stats[player_id] = {

        "playerId": player_id,

        # ====================================================
        # Overview
        # ====================================================

        "overview": {

            "matchesPlayed": matches_played,

            "matchesWon": matches_won,

            "matchesLost": matches_lost,

            "winRate": percentage(
                matches_won,
                matches_played
            ),

            "legsPlayed": legs_played,

            "legsWon": legs_won,

            "legsLost": legs_lost,

            "legWinRate": percentage(
                legs_won,
                legs_played
            ),

            "seasonsPlayed": int(
                player_matches["year"]
                .nunique()
            ),

            "roundsPlayed": int(
                player_matches[
                    ["year", "round"]
                ]
                .drop_duplicates()
                .shape[0]
            ),
        },

        # ====================================================
        # Phases
        # ====================================================

        "phases": phases,

        # ====================================================
        # Seasons
        # ====================================================

        "seasons": seasons,

        # ====================================================
        # Rounds
        # ====================================================

        "rounds": {

            "played": len(
                round_results
            ),

            "all": round_results,

            "last10": last10_rounds,

            # TODO:
            # This is specifically the average standing
            # per round, not average match result.
            "averageStanding": None,

            # TODO:
            # Depends on the round ranking system.
            "best": None,

            # TODO:
            # Depends on the round ranking system.
            "worst": None,
        },

        # ====================================================
        # Form
        # ====================================================

        "form": {

            "last10": last10,

            "last10WinRate": percentage(
                last10.count("W"),
                len(last10)
            ),

            "streaks": streaks,
        },

        # ====================================================
        # Bonuses
        # ====================================================

        "bonuses": {

            "total": total_bonus_points,

            "events": bonus_events,

            "180s": career_180s,

            "highestCheckout":
                highest_checkout,

            "history": bonus_history,
        },

        # ====================================================
        # Head-to-head
        # ====================================================

        "headToHead": head_to_head,

        # ====================================================
        # Rivals
        # ====================================================

        "rivals": {

            "dominating": dominating,

            "archenemy": archenemy,
        },

        # ====================================================
        # Whitewashes
        # ====================================================

        "whitewashes": {

            "count": whitewashes,

            "percentage": percentage(
                whitewashes,
                matches_played
            ),
        },

        # ====================================================
        # Shutouts
        # ====================================================

        "shutouts": {

            "count": shutouts,

            "percentage": percentage(
                shutouts,
                matches_played
            ),
        },

        # ====================================================
        # Standing-related statistics
        #
        # These intentionally remain TODO until the exact
        # round/standing system is provided.
        # ====================================================

        "standing": {

            # TODO
            "current": None,

            # TODO
            "currentPoints": None,

            # TODO
            "bestSeason": None,

            # TODO
            "worstSeason": None,

            # TODO
            "chasing": None,

            # TODO
            "chasedBy": None,

            # TODO
            "gapToLeader": None,

            # TODO
            "firstNightWon": None,

            # TODO
            "lastNightWon": None,

            # TODO
            "nightsWon": None,
        },

        # ====================================================
        # Match history
        # ====================================================

        "matches": match_history,
    }


# ============================================================
# Save JSON
# ============================================================

output_path = Path(
    OUTPUT_FILE
)

output_path.parent.mkdir(
    parents=True,
    exist_ok=True
)


with open(
    output_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        player_stats,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    f"Generated statistics for "
    f"{len(player_stats)} players."
)

print(
    f"Saved to: {OUTPUT_FILE}"
)