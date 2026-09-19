import os
import pandas as pd

# Folder containing the yearly result folders
results_folder = "public/results"

# Output file
merged_file = os.path.join(
    results_folder,
    "matches.csv"
)

all_matches = []

# Go through each year
for year in sorted(os.listdir(results_folder)):

    year_folder = os.path.join(results_folder, year)

    # Only process directories
    if not os.path.isdir(year_folder):
        continue

    # Only process year directories
    if not year.isdigit():
        continue

    for filename in sorted(os.listdir(year_folder)):

        if not filename.lower().endswith(".csv"):
            continue

        csv_file = os.path.join(
            year_folder,
            filename
        )

        print(f"Reading {csv_file}...")

        df = pd.read_csv(
            csv_file,
            sep=";"
        )

        all_matches.append(df)


if not all_matches:
    print("No match CSV files found.")
    exit()


# Merge all rounds
matches = pd.concat(
    all_matches,
    ignore_index=True
)


# Sort chronologically
matches = matches.sort_values(
    by=[
        "year",
        "month",
        "day",
        "round"
    ]
).reset_index(drop=True)


# Save
matches.to_csv(
    merged_file,
    sep=";",
    index=False
)

print()
print(f"Merged {len(matches)} matches.")
print(f"Saved to {merged_file}")