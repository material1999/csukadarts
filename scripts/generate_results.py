# -------------------------
# Imports
# -------------------------

import pandas as pd
import json

from utils import (
    MATCHES_FILE,
    BONUS_FILE,
    OUTPUT_FILES
)

from utils import (
    prepare_data,
    calculate_round_group,
    calculate_round_results,
    calculate_round_info,
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
# Generate results
# -------------------------

results_df = {}

for season, round in (
    matches[["season", "round"]]
    .drop_duplicates()
    .sort_values(["season", "round"])
    .itertuples(index=False)
):

    season = str(season)
    round = str(round)

    results_df.setdefault(season, {})

    results_df[season][round] = {
        "info": calculate_round_info(
            int(season),
            int(round),
            matches,
            bonus_points
        ),
        "group": calculate_round_group(
            int(season),
            int(round),
            matches
        ).to_dict(orient="records"),
        "results": calculate_round_results(
            int(season),
            int(round),
            matches,
            bonus_points
        ).to_dict(orient="records"),
    }

# -------------------------
# Save results
# -------------------------

with open(
    OUTPUT_FILES["results"],
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        results_df,
        f,
        indent=2,
        ensure_ascii=False,
    )