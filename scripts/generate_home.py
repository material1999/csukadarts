# -------------------------
# Imports
# -------------------------

import pandas as pd
import json

from utils import (
    MATCHES_FILE,
    BONUS_FILE,
    OUTPUT_FILES,
    prepare_data,
    calculate_round_results,
    calculate_season_standings,
)

# -------------------------
# Load data
# -------------------------

matches = pd.read_csv(
    MATCHES_FILE,
    sep=";"
)

bonus_points = pd.read_csv(
    BONUS_FILE,
    sep=";"
)

# -------------------------
# Prepare data
# -------------------------

matches, bonus_points = prepare_data(
    matches,
    bonus_points,
)

# -------------------------
# Current season
# -------------------------

current_season = matches["season"].max()

# -------------------------
# Last round
# -------------------------

last_round = (
    matches[
        matches["season"] == current_season
    ]["round"]
    .max()
)

last_round_winner = calculate_round_results(
    current_season,
    last_round,
    matches,
    bonus_points,
)["player_id"].values[0]

last_round_runner_up = calculate_round_results(
    current_season,
    last_round,
    matches,
    bonus_points,
)["player_id"].values[1]

# -------------------------
# Current standings
# -------------------------

standings = calculate_season_standings(
    current_season,
    matches,
    bonus_points,
)

standings = standings[
    [
        "#",
        "player_id",
        "nights_won",
        "matches_won",
        "leg_difference",
        "legs_won",
        "total_points",
    ]
]

# -------------------------
# Generate home
# -------------------------

home = {
    "season": int(current_season),
    "last_round": int(last_round),
    "last_round_winner": str(last_round_winner),
    "last_round_runner_up": str(last_round_runner_up),
    "standings": standings.to_dict(
        orient="records"
    ),
}

# -------------------------
# Save home
# -------------------------

with open(
    OUTPUT_FILES["home"],
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        home,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("Home generated successfully.")