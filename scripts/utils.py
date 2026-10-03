import pandas as pd


MATCHES_FILE = "../public/results/matches.csv"
BONUS_FILE = "../public/results/bonus_points.csv"

OUTPUT_FILES = {
    "home": "../public/results/generated/home.json",
    "standings": "../public/results/generated/standings.json",
    "results": "../public/results/generated/results.json",
    "stats": "../public/results/generated/stats.json",
    "players": "../public/results/generated/players.json",
    "head_to_head": "../public/results/generated/head_to_head.json",
    "memories": "../public/results/generated/memories.json"
}


def prepare_data(matches, bonus_points):

    # -------------------------
    # Matches
    # -------------------------
    matches["date"] = pd.to_datetime(
        matches[["year", "month", "day"]]
    )

    matches["season"] = matches["year"].astype(int)
    matches["round"] = matches["round"].astype(int)
    matches["player1_score"] = matches["player1_score"].astype(int)
    matches["player2_score"] = matches["player2_score"].astype(int)
    matches["phase"] = matches["phase"].astype(str)

    matches = matches[
        [
            "date",
            "season",
            "round",
            "phase",
            "player1_id",
            "player1_score",
            "player2_id",
            "player2_score",
        ]
    ]

    # -------------------------
    # Bonus Points
    # -------------------------
    bonus_points["season"] = bonus_points["season"].astype(int)
    bonus_points["round"] = bonus_points["round"].astype(int)
    bonus_points["bonus"] = bonus_points["bonus"].astype(int)
    bonus_points["player_id"] = bonus_points["player_id"].astype(str)

    round_dates = (
        matches
        .drop_duplicates(["season", "round"])
        .set_index(["season", "round"])["date"]
    )

    bonus_points["date"] = bonus_points.set_index(
        ["season", "round"]
    ).index.map(round_dates)

    bonus_points = bonus_points[
        [
            "date",
            "season",
            "round",
            "player_id",
            "bonus",
        ]
    ]

    return matches, bonus_points


def calculate_round_group(season, round, matches):

    group_matches = matches[
        (matches["season"] == season) &
        (matches["round"] == round) &
        (matches["phase"] == "group")
    ].copy()

    players = set(
        group_matches["player1_id"]
    ) | set(
        group_matches["player2_id"]
    )

    results = {
        player: {
            "player_id": player,
            "matches_played": 0,
            "matches_won": 0,
            "matches_lost": 0,
            "legs_played": 0,
            "legs_won": 0,
            "legs_lost": 0,
        }
        for player in players
    }

    # Calculate match results
    for _, match in group_matches.iterrows():

        p1 = match["player1_id"]
        p2 = match["player2_id"]
        s1 = match["player1_score"]
        s2 = match["player2_score"]

        results[p1]["matches_played"] += 1
        results[p2]["matches_played"] += 1

        results[p1]["legs_played"] += s1 + s2
        results[p2]["legs_played"] += s1 + s2

        results[p1]["legs_won"] += s1
        results[p1]["legs_lost"] += s2

        results[p2]["legs_won"] += s2
        results[p2]["legs_lost"] += s1

        if s1 > s2:
            results[p1]["matches_won"] += 1
            results[p2]["matches_lost"] += 1

        elif s2 > s1:
            results[p2]["matches_won"] += 1
            results[p1]["matches_lost"] += 1

    standings = pd.DataFrame(results.values())

    standings["leg_difference"] = (
        standings["legs_won"] - standings["legs_lost"]
    )

    # Initial sorting
    standings = standings.sort_values(
        ["matches_won", "leg_difference", "legs_won"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    # Find groups tied on all three criteria
    tied_columns = [
        "matches_won",
        "leg_difference",
        "legs_won",
    ]

    final_groups = []

    for _, tied_group in standings.groupby(
        tied_columns,
        sort=False
    ):

        # No tie
        if len(tied_group) == 1:
            final_groups.append(tied_group)
            continue

        tied_players = tied_group["player_id"].tolist()

        # Only matches between tied players
        h2h_matches = group_matches[
            group_matches["player1_id"].isin(tied_players) &
            group_matches["player2_id"].isin(tied_players)
        ]

        # Calculate H2H wins and leg difference
        h2h = {
            player: {
                "matches_won": 0,
                "leg_difference": 0,
            }
            for player in tied_players
        }

        for _, match in h2h_matches.iterrows():

            p1 = match["player1_id"]
            p2 = match["player2_id"]
            s1 = match["player1_score"]
            s2 = match["player2_score"]

            # Leg difference
            h2h[p1]["leg_difference"] += s1 - s2
            h2h[p2]["leg_difference"] += s2 - s1

            # Match winner
            if s1 > s2:
                h2h[p1]["matches_won"] += 1

            elif s2 > s1:
                h2h[p2]["matches_won"] += 1

        # Add H2H criteria
        tied_group = tied_group.copy()

        tied_group["h2h_matches_won"] = tied_group["player_id"].map(
            lambda p: h2h[p]["matches_won"]
        )

        tied_group["h2h_leg_difference"] = tied_group["player_id"].map(
            lambda p: h2h[p]["leg_difference"]
        )

        # H2H order
        tied_group = tied_group.sort_values(
            [
                "h2h_matches_won",
                "h2h_leg_difference",
            ],
            ascending=[False, False]
        )

        final_groups.append(tied_group)

    standings = pd.concat(
        final_groups,
        ignore_index=True
    )

    # Remove temporary H2H columns
    standings = standings.drop(
        columns=[
            "h2h_matches_won",
            "h2h_leg_difference",
        ],
        errors="ignore"
    )

    # Add position
    standings["#"] = range(1, len(standings) + 1)

    standings = standings[
        [
            "#",
            "player_id",
            "matches_played",
            "matches_won",
            "matches_lost",
            "legs_played",
            "legs_won",
            "legs_lost",
            "leg_difference",
        ]
    ]

    return standings


def calculate_round_results(season, round, matches, bonus_points):

    # -------------------------
    # Group standings
    # -------------------------
    group_standings = calculate_round_group(season, round, matches)

    # Start with group statistics
    results = group_standings.copy()

    # -------------------------
    # Knockout matches
    # -------------------------
    knockout_matches = matches[
        (matches["season"] == season) &
        (matches["round"] == round) &
        (matches["phase"].isin(["semi", "final"]))
    ].copy()

    semi_matches = knockout_matches[
        knockout_matches["phase"] == "semi"
    ]

    final_matches = knockout_matches[
        knockout_matches["phase"] == "final"
    ]

    # -------------------------
    # Determine semifinal results
    # -------------------------
    semi_winners = []
    semi_losers = []

    for _, match in semi_matches.iterrows():

        if match["player1_score"] > match["player2_score"]:
            winner = match["player1_id"]
            loser = match["player2_id"]
        else:
            winner = match["player2_id"]
            loser = match["player1_id"]

        semi_winners.append(winner)
        semi_losers.append(loser)

    # -------------------------
    # Determine final results
    # -------------------------
    winner = None
    second_place = None

    if len(final_matches) > 0:

        final_match = final_matches.iloc[0]

        if final_match["player1_score"] > final_match["player2_score"]:
            winner = final_match["player1_id"]
            second_place = final_match["player2_id"]
        else:
            winner = final_match["player2_id"]
            second_place = final_match["player1_id"]

    # -------------------------
    # Determine bronze / 3rd place
    # -------------------------
    bronze_matches = matches[
        (matches["season"] == season) &
        (matches["round"] == round) &
        (matches["phase"] == "bronze")
    ].copy()

    third_place = None
    fourth_place = None

    if len(bronze_matches) > 0:

        bronze_match = bronze_matches.iloc[0]

        if bronze_match["player1_score"] > bronze_match["player2_score"]:
            third_place = bronze_match["player1_id"]
            fourth_place = bronze_match["player2_id"]
        else:
            third_place = bronze_match["player2_id"]
            fourth_place = bronze_match["player1_id"]

    else:

        # No bronze match:
        # use group standings to determine 3rd/4th
        # among the two semifinal losers

        semi_losers_df = results[
            results["player_id"].isin(semi_losers)
        ].copy()

        semi_losers_df = semi_losers_df.sort_values(
            [
                "matches_won",
                "leg_difference",
                "legs_won",
            ],
            ascending=[False, False, False]
        )

        third_place = semi_losers_df.iloc[0]["player_id"]
        fourth_place = semi_losers_df.iloc[1]["player_id"]

    # -------------------------
    # Add knockout statistics
    # -------------------------
    knockout_all = matches[
        (matches["season"] == season) &
        (matches["round"] == round) &
        (matches["phase"].isin(["semi", "final", "bronze"]))
    ].copy()

    for _, match in knockout_all.iterrows():

        p1 = match["player1_id"]
        p2 = match["player2_id"]
        s1 = match["player1_score"]
        s2 = match["player2_score"]

        # Matches played
        results.loc[
            results["player_id"] == p1,
            "matches_played"
        ] += 1

        results.loc[
            results["player_id"] == p2,
            "matches_played"
        ] += 1

        # Legs played
        results.loc[
            results["player_id"] == p1,
            "legs_played"
        ] += s1 + s2

        results.loc[
            results["player_id"] == p2,
            "legs_played"
        ] += s1 + s2

        # Legs won / lost
        results.loc[
            results["player_id"] == p1,
            "legs_won"
        ] += s1

        results.loc[
            results["player_id"] == p1,
            "legs_lost"
        ] += s2

        results.loc[
            results["player_id"] == p2,
            "legs_won"
        ] += s2

        results.loc[
            results["player_id"] == p2,
            "legs_lost"
        ] += s1

        # Match result
        if s1 > s2:

            results.loc[
                results["player_id"] == p1,
                "matches_won"
            ] += 1

            results.loc[
                results["player_id"] == p2,
                "matches_lost"
            ] += 1

        elif s2 > s1:

            results.loc[
                results["player_id"] == p2,
                "matches_won"
            ] += 1

            results.loc[
                results["player_id"] == p1,
                "matches_lost"
            ] += 1

    # -------------------------
    # Recalculate leg difference
    # -------------------------
    results["leg_difference"] = (
        results["legs_won"] - results["legs_lost"]
    )

    # -------------------------
    # Assign final positions
    # -------------------------

    # calculate_round_group() already returns players
    # in group-standing order.
    results = results.reset_index(drop=True)

    # Store original group position
    results["group_position"] = range(
        1,
        len(results) + 1
    )

    # Assign positions to knockout players
    positions = {
        winner: 1,
        second_place: 2,
        third_place: 3,
        fourth_place: 4,
    }

    results["#"] = results["player_id"].map(positions)

    # Everyone without a knockout position keeps
    # their original group position.
    results["#"] = results["#"].fillna(
        results["group_position"]
    )

    results["#"] = results["#"].astype(int)

    # Remove temporary column
    results = results.drop(
        columns=["group_position"]
    )

    # -------------------------
    # Tournament points
    # -------------------------

    results["points"] = results["#"].map({
        1: 10,
        2: 6,
        3: 4,
        4: 4,
        5: 2,
        6: 1,
    }).fillna(0).astype(int)

    # -------------------------
    # Bonus points
    # -------------------------
    round_bonus = bonus_points[
        (bonus_points["season"] == season) &
        (bonus_points["round"] == round)
    ].copy()

    # 180 -> 2 points
    # Anything below 180 -> 1 point
    round_bonus["bonus_points"] = round_bonus["bonus"].apply(
        lambda x: 2 if x == 180 else 1
    )

    bonus_totals = (
        round_bonus
        .groupby("player_id")["bonus_points"]
        .sum()
    )

    results["bonus_points"] = (
        results["player_id"]
        .map(bonus_totals)
        .fillna(0)
        .astype(int)
    )

    # -------------------------
    # Total points
    # -------------------------
    results["total_points"] = (
        results["points"] +
        results["bonus_points"]
    )

    # -------------------------
    # Final ordering
    # -------------------------
    results = results.sort_values(
        "#"
    ).reset_index(drop=True)

    # -------------------------
    # Final columns
    # -------------------------
    results = results[
        [
            "#",
            "player_id",
            "matches_played",
            "matches_won",
            "matches_lost",
            "legs_played",
            "legs_won",
            "legs_lost",
            "leg_difference",
            "points",
            "bonus_points",
            "total_points",
        ]
    ]

    return results


def calculate_round_info(season, round, matches, bonus_points):

    # -------------------------
    # Round matches
    # -------------------------
    round_matches = matches[
        (matches["season"] == season) &
        (matches["round"] == round)
    ].copy()

    # -------------------------
    # Date
    # -------------------------
    date = round_matches["date"].iloc[0]

    # -------------------------
    # Number of players
    # -------------------------
    players = sorted(
        set(round_matches["player1_id"]) |
        set(round_matches["player2_id"])
    )

    number_of_players = len(players)

    # -------------------------
    # Matches played
    # -------------------------
    matches_played = len(round_matches)

    # -------------------------
    # Legs played
    # -------------------------
    legs_played = (
        round_matches["player1_score"] +
        round_matches["player2_score"]
    ).sum()

    # -------------------------
    # Highest checkout
    # -------------------------
    round_bonus = bonus_points[
        (bonus_points["season"] == season) &
        (bonus_points["round"] == round)
    ].copy()

    checkout_values = round_bonus[
        round_bonus["bonus"] < 180
    ]

    if len(checkout_values) > 0:

        highest_checkout = checkout_values["bonus"].max()

        highest_checkout_by = (
            checkout_values[
                checkout_values["bonus"] == highest_checkout
            ]["player_id"]
            .unique()
            .tolist()
        )

    else:
        highest_checkout = None
        highest_checkout_by = []

    # -------------------------
    # 180s
    # -------------------------
    one_eighties = round_bonus[
        round_bonus["bonus"] == 180
    ]

    total_180s = len(one_eighties)

    one_eighties_by = (
        one_eighties
        .groupby("player_id")
        .size()
        .sort_values(ascending=False)
        .to_dict()
    )

    round_results = calculate_round_results(season, round, matches, bonus_points)
    podium = {
        "winner": round_results.loc[round_results["#"] == 1, "player_id"].iloc[0],
        "second": round_results.loc[round_results["#"] == 2, "player_id"].iloc[0],
        "third": round_results.loc[round_results["#"] == 3, "player_id"].iloc[0]
    }

    
    # -------------------------
    # Return round information
    # -------------------------
    return {
        "date": str(date.date()),
        "number_of_players": int(number_of_players),
        "players": players,
        "matches_played": int(matches_played),
        "legs_played": int(legs_played),
        "highest_checkout": int(highest_checkout),
        "highest_checkout_by": highest_checkout_by,
        "180s": int(total_180s),
        "180s_by": one_eighties_by,
        "podium": podium
    }