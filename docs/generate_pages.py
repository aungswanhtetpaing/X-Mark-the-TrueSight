import os
import json
from pathlib import Path

# --- Paths ---
RAW_DIR = Path("docs/opendotaraw")
DICT_DIR = Path("docs/dictionaries/data")
IMAGE_DIR = Path("docs/dictionaries/image")
OUTPUT_ROOT = Path("docs/matches")     # ✅ GitHub Pages-compatible output
INDEX_PATH = Path("docs/index.html")   # ✅ index inside /docs

# --- Load hero data ---
with open(DICT_DIR / "heroes.json", "r", encoding="utf-8") as f:
    heroes_data = json.load(f)

hero_dict = {}
for hero in heroes_data:
    hero_id = str(hero["id"])
    hero_dict[hero_id] = {
        "name": hero.get("localized_name", ""),
        "image": f"../../{IMAGE_DIR}/{hero.get('name', '').replace('npc_dota_hero_', '')}.png"
    }

# --- Create output root ---
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# --- Helper for HTML escaping ---
def esc(text):
    return str(text).replace("<", "&lt;").replace(">", "&gt;")

# --- Helper to format player stats ---
def format_stats(player):
    kda = f"KDA: {player.get('kills',0)} / {player.get('deaths',0)} / {player.get('assists',0)}"
    gpm_xpm = f"GPM/XPM: {player.get('gold_per_min',0)} / {player.get('xp_per_min',0)}"
    lane_eff = f"Lane efficiency: {player.get('lane_efficiency_pct',0)*100:.1f}%"
    
    b = player.get("benchmarks", {})
    lh = b.get("last_hits_per_min", {}).get("pct", 0) * 100
    hdm = b.get("hero_damage_per_min", {}).get("pct", 0) * 100
    tdm = b.get("tower_damage", {}).get("pct", 0) * 100
    benchmarks = f"LH/HDM/TDM: {lh:.0f}/{hdm:.0f}/{tdm:.0f}"

    return f"""
        <div style="text-align:left; line-height:1.5;">
            <pre style="font-family: monospace; color:#ccc;">
KDA:             {player.get('kills',0)} / {player.get('deaths',0)} / {player.get('assists',0)}
GPM/XPM:         {player.get('gold_per_min',0)} / {player.get('xp_per_min',0)}
Lane efficiency: {player.get('lane_efficiency_pct',0)*100:.1f}%
LH/HDM/TDM:      {lh:.0f}/{hdm:.0f}/{tdm:.0f}/{""}
            </pre>
        </div>
    """

# --- Loop through tournaments ---
index_links = []

for tournament_dir in RAW_DIR.iterdir():
    if not tournament_dir.is_dir():
        continue

    tour_output = OUTPUT_ROOT / tournament_dir.name
    tour_output.mkdir(parents=True, exist_ok=True)

    match_groups = {}
    for json_file in sorted(tournament_dir.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        radiant_name = data["radiant_team"]["name"]
        dire_name = data["dire_team"]["name"]
        radiant_win = data.get("radiant_win", False)
        match_name = json_file.stem.split("_")[0]
        winner = radiant_name if radiant_win else dire_name

        # --- Picks & Bans ---
        picks_bans = sorted(data.get("picks_bans", []), key=lambda x: x["order"])
        radiant_side, dire_side = [], []
        player_map = {p["hero_id"]: p for p in data.get("players", []) if p.get("hero_id")}

        for item in picks_bans:
            hero_id = str(item["hero_id"])
            hero_info = hero_dict.get(hero_id, {"image": "", "name": "Unknown"})
            is_pick = item["is_pick"]
            team = item["team"]
            order_num = item["order"] + 1

            if is_pick:
                player = player_map.get(item["hero_id"], {})
                hero_img = hero_info["image"]
                stats = format_stats(player)
                label = f"<b style='color:#00ff66'>{order_num}. Pick</b><br><img src='{hero_img}' width='90'><br>{stats}"
            else:
                label = f"<b style='color:#ff3333'>{order_num}. Ban</b><br>{hero_info['name']}"

            if team == 0:
                radiant_side.append((item["order"], label))
            else:
                dire_side.append((item["order"], label))

        radiant_side.sort(key=lambda x: x[0])
        dire_side.sort(key=lambda x: x[0])

        # --- HTML Build ---
        html_content = f"""
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{radiant_name} vs {dire_name} - {'Radiant Win' if radiant_win else 'Dire Win'}</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        background-color: #0d0d0d;
        color: #f0f0f0;
        margin: 0;
        padding: 0;
    }}
    .back {{
        text-align: left;
        padding: 10px;
    }}
    .back a {{
        color: #00bfff;
        text-decoration: none;
        font-weight: bold;
    }}
    h2 {{
        text-align: center;
    }}
    .match {{
        display: flex;
        flex-wrap: wrap;
        justify-content: space-around;
        margin: 10px;
    }}
    .team {{
        flex: 1;
        min-width: 300px;
        background: #1b1b1b;
        border-radius: 10px;
        margin: 10px;
        padding: 15px;
    }}
    .team h3 {{
        text-align: center;
        border-bottom: 1px solid #333;
        padding-bottom: 5px;
    }}
</style>
</head>
<body>
<div class="back"><a href="../../index.html">⬅ Back to Match List</a></div>
<h2>{radiant_name} vs {dire_name} - <span style='color:#00ff66'>{winner} Win</span></h2>

<div class="match">
    <div class="team"><h3>{radiant_name}</h3>
        {''.join([f"<div>{x[1]}</div>" for x in radiant_side])}
    </div>
    <div class="team"><h3>{dire_name}</h3>
        {''.join([f"<div>{x[1]}</div>" for x in dire_side])}
    </div>
</div>
</body>
</html>
"""
        game_name = f"Game{match_name.split('.')[1] if '.' in match_name else 'X'}.html"
        output_path = tour_output / game_name

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        group_key = match_name.split("_")[0]
        match_groups.setdefault(group_key, []).append((winner, output_path))

    # --- Tournament summary folder ---
    summary_name = tournament_dir.name
    index_links.append(f"<li><a href='matches/{summary_name}/'>{summary_name}</a></li>")

# --- Write index.html ---
index_html = f"""
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>True Sight - Match Index</title>
<style>
    body {{
        background: #101010;
        color: #fff;
        font-family: Arial, sans-serif;
        text-align: center;
        padding: 20px;
    }}
    ul {{
        list-style: none;
        padding: 0;
    }}
    li {{
        margin: 8px 0;
    }}
    a {{
        color: #00bfff;
        text-decoration: none;
        font-size: 1.1em;
    }}
</style>
</head>
<body>
<h2>🏆 Dota 2 Match Archive</h2>
<ul>
{''.join(index_links)}
</ul>
</body>
</html>
"""

INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(index_html)

print("✅ All pages generated successfully in /docs/")
