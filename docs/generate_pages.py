import os
import json
from datetime import datetime

# === CONFIG ===
RAW_DATA_DIR = "opendotaraw"       # Input JSONs
OUTPUT_DIR = "matches"             # Output HTML folders
DICTIONARIES_DIR = "dictionaries"  # Hero data + images
ASSETS_DIR = "assets"              # CSS and JS (optional)

# === Load Hero Data ===
hero_json_path = os.path.join(DICTIONARIES_DIR, "data", "heroes.json")
with open(hero_json_path, "r", encoding="utf-8") as f:
    heroes = json.load(f)

# Convert hero list to dictionary
hero_dict = {str(h["id"]): h for h in heroes}


def hero_img(hero_id):
    """Return hero image HTML tag"""
    hero = hero_dict.get(str(hero_id))
    if not hero:
        return f"<span>Unknown Hero {hero_id}</span>"
    img_path = f"../../{DICTIONARIES_DIR}/image/{hero['name']}.png"
    return f'<img src="{img_path}" alt="{hero["localized_name"]}" title="{hero["localized_name"]}" class="hero-icon">'


def load_json(path):
    """Load JSON safely"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_match_page(series_dir, match_file):
    """Generate one match HTML"""
    data = load_json(match_file)
    match_name = os.path.splitext(os.path.basename(match_file))[0]
    output_path = os.path.join(series_dir, f"{match_name}.html")

    radiant_heroes = [hero_img(h) for h in data["radiant_heroes"]]
    dire_heroes = [hero_img(h) for h in data["dire_heroes"]]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{match_name}</title>
    <link rel="stylesheet" href="../../assets/css/match.css">
</head>
<body>
    <h1>{match_name}</h1>
    <div class="team radiant">
        <h2>Radiant</h2>
        <div class="heroes">{''.join(radiant_heroes)}</div>
    </div>
    <div class="team dire">
        <h2>Dire</h2>
        <div class="heroes">{''.join(dire_heroes)}</div>
    </div>
    <a href="../index.html" class="back-link">← Back to Series</a>
</body>
</html>
""")


def generate_series_page(series_name, match_files, output_subdir):
    """Generate per-series index page and match pages"""
    os.makedirs(output_subdir, exist_ok=True)
    match_links = []

    for file in match_files:
        generate_match_page(output_subdir, file)
        fname = os.path.basename(file)
        match_links.append(f'<li><a href="{fname}">{fname}</a></li>')

    index_path = os.path.join(output_subdir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{series_name}</title>
    <link rel="stylesheet" href="../../assets/css/series.css">
</head>
<body>
    <h1>{series_name}</h1>
    <ul>
        {''.join(match_links)}
    </ul>
    <a href="../../index.html" class="back-link">← Back to Main</a>
</body>
</html>
""")


def generate_main_index():
    """Generate top-level index listing all series"""
    index_path = os.path.join("index.html")
    content = "<h1>Match Series</h1><ul>"

    # Find all series folders inside opendotaraw
    for event_folder in os.listdir(RAW_DATA_DIR):
        event_path = os.path.join(RAW_DATA_DIR, event_folder)
        if not os.path.isdir(event_path):
            continue

        # Create corresponding output folder
        output_event_dir = os.path.join(OUTPUT_DIR, event_folder)
        os.makedirs(output_event_dir, exist_ok=True)

        # Process each series folder (like 1.XG_vs_Thundra)
        for series_folder in os.listdir(event_path):
            series_path = os.path.join(event_path, series_folder)
            if not os.path.isdir(series_path):
                continue

            output_series_dir = os.path.join(output_event_dir, series_folder)
            os.makedirs(output_series_dir, exist_ok=True)

            # Find JSON match files
            match_files = [
                os.path.join(series_path, f)
                for f in os.listdir(series_path)
                if f.endswith(".json")
            ]
            if not match_files:
                continue

            # Generate pages
            generate_series_page(series_folder, match_files, output_series_dir)

            # Add to main index
            rel_path = f"{OUTPUT_DIR}/{event_folder}/{series_folder}/index.html"
            content += f'<li><a href="{rel_path}">{series_folder}</a></li>'

    content += "</ul>"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dota 2 Matches</title>
    <link rel="stylesheet" href="assets/css/main.css">
</head>
<body>
    {content}
</body>
</html>
""")

    print("✅ Pages generated successfully!")


if __name__ == "__main__":
    generate_main_index()
