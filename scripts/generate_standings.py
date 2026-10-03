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
    calculate_season_info,
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
# Generate standings
# -------------------------

standings_df = {}

seasons = (
    matches["season"]
    .drop_duplicates()
    .sort_values()
)

for season in seasons:

    season_key = str(season)

    standings_df[season_key] = {
        "info": calculate_season_info(
            int(season),
            matches,
            bonus_points,
        ),
        "standings": calculate_season_standings(
            int(season),
            matches,
            bonus_points,
        ).to_dict(orient="records"),
    }

# -------------------------
# Save standings
# -------------------------

with open(
    OUTPUT_FILES["standings"],
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        standings_df,
        f,
        indent=2,
        ensure_ascii=False,
    )