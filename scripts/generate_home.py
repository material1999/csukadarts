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
        "total_points",
    ]
]

# -------------------------
# Generate home
# -------------------------

home = {
    "season": int(current_season),
    "last_round": int(last_round),
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