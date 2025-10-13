#!/usr/bin/env python3
"""
generate_pages.py

- Scans `opendotaraw/` for tournament subfolders and JSONs named like:
    1.1_XtremeGaming_vs_Falcons_G1.json
- Uses heroes JSON in `dictionaries/data/heroes.json` and images in `dictionaries/image/`
- Produces HTML pages under matches/<tournament>/<series_folder>/...
- Builds series index pages and a global main/index.html
"""

import os
import re
import json
import shutil
from collections import defaultdict, Counter
import urllib.parse

# -------------------------
# Config (edit if needed)
# -------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OPENDOTA_DIR = os.path.join(ROOT, "opendotaraw")
DICTS_HEROES = os.path.join(ROOT, "dictionaries", "data", "heroes.json")
IMAGES_DIR = os.path.join(ROOT, "dictionaries", "image")
MATCHES_DIR = os.path.join(ROOT, "matches")
MAIN_DIR = os.path.join(ROOT, "main")
MAIN_INDEX = os.path.join(MAIN_DIR, "index.html")

# Regex to parse filenames such as: 1.1_XtremeGaming_vs_Falcons_G1.json
FILENAME_RE = re.compile(r'^(?P<prefix>[^_]+)_(?P<body>.+?)_G(?P<gnum>\d+)\.json$', re.IGNORECASE)

# -------------------------
# Utilities
# -------------------------
def safe_mkdir(path):
    os.makedirs(path, exist_ok=True)

def sanitize_folder_name(name):
    return re.sub(r'[\\/:"*?<>|]+', '', name).replace(" ", "_")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_hero_filename(internal_name):
    return internal_name.replace("npc_dota_hero_", "")

def pretty_team_name_from_body(series_body):
    s = series_body.replace("_vs_", " vs ")
    s = s.replace("_VS_", " vs ")
    s = s.replace("_v_", " v ")
    s = s.replace("_", " ")
    return s

# -------------------------
# Load heroes
# -------------------------
if not os.path.exists(DICTS_HEROES):
    raise FileNotFoundError(f"Heroes JSON not found at: {DICTS_HEROES}")

heroes_json = load_json(DICTS_HEROES)
hero_list = heroes_json.get("heroes") if isinstance(heroes_json, dict) and "heroes" in heroes_json else heroes_json

hero_dict = {}
if isinstance(hero_list, list):
    for h in hero_list:
        hid = str(h.get("id"))
        internal_name = h.get("name", "")
        localized = h.get("localized_name") or h.get("localized") or h.get("name", internal_name)
        clean_name = clean_hero_filename(internal_name)
        hero_dict[hid] = {
            "image": clean_name + ".png",
            "clean_name": clean_name,
            "localized_name": localized
        }

# -------------------------
# Scan tournaments
# -------------------------
if not os.path.isdir(OPENDOTA_DIR):
    raise FileNotFoundError(f"opendotaraw directory not found at: {OPENDOTA_DIR}")

tournaments = {}
for tournament_name in sorted(os.listdir(OPENDOTA_DIR)):
    tourn_path = os.path.join(OPENDOTA_DIR, tournament_name)
    if os.path.isdir(tourn_path):
        files = sorted([f for f in os.listdir(tourn_path) if f.lower().endswith(".json")])
        if files:
            tournaments[tournament_name] = [os.path.join(tourn_path, f) for f in files]

# -------------------------
# Prepare output dirs
# -------------------------
safe_mkdir(MATCHES_DIR)
safe_mkdir(MAIN_DIR)

# -------------------------
# HTML Templates (CSS)
# -------------------------
PAGE_CSS = """
body { font-family: Arial, sans-serif; background:#101010; color:#f0f0f0; text-align:center; margin:0; padding:8px; }
a.back-link { display:inline-block; margin:10px 0; color:#66b3ff; text-decoration:none; }
h2 { margin-top:6px; margin-bottom:8px; font-size:20px; }
table { margin:10px auto; border-collapse:collapse; width:98%; max-width:900px; background:#1b1b1b; border-radius:8px; overflow:hidden; }
th, td { border:1px solid #333; padding:12px; vertical-align:top; width:50%; }
.player-info { display:flex; align-items:center; gap:12px; margin-top:6px; justify-content:flex-start; }
.hero-image img { width:80px; border-radius:6px; }
.stats { text-align:left; font-size:13px; color:#ccc; line-height:1.4em; display:flex; flex-direction:column; gap:3px; }
.player-name { color:#fff; margin-bottom:4px; font-weight:600; }
.stat-row { display:flex; justify-content:space-between; width:220px; }
.stat-row .label { color:#aaa; }
.stat-row .value { color:#fff; text-align:right; }
.benchmarks { font-size:12px; color:#999; margin-top:4px; }
@media (max-width:600px) { .player-info { flex-wrap:wrap; gap:8px; } .stat-row { width:100%; justify-content:space-between; } }
"""

SERIES_INDEX_CSS = """
body { background:#101010; color:#f0f0f0; font-family:Arial, sans-serif; text-align:center; }
a { color:#66b3ff; text-decoration:none; }
ul { list-style:none; padding:0; margin-top:20px; }
li { margin:10px 0; font-size:16px; }
"""

MAIN_INDEX_CSS = SERIES_INDEX_CSS

# -------------------------
# Generate match HTML
# -------------------------
def generate_match_html(data, heroes_map, out_html_path, title_text_override=None):
    import urllib.parse
    radiant_name = data.get("radiant_team", {}).get("name", "Radiant")
    dire_name = data.get("dire_team", {}).get("name", "Dire")
    radiant_win = data.get("radiant_win", False)
    title_text = title_text_override or (f"{radiant_name} (Winner) vs {dire_name}" if radiant_win else f"{radiant_name} vs {dire_name} (Winner)")

    # Player info map
    player_map = {}
    for p in data.get("players", []):
        hid = p.get("hero_id")
        if hid is None:
            continue
        hid_str = str(hid)
        kda = f"{p.get('kills',0)}/{p.get('deaths',0)}/{p.get('assists',0)}"
        gpm_xpm = f"{p.get('gold_per_min',0)}/{p.get('xp_per_min',0)}"
        lane_eff = f"{p.get('lane_efficiency_pct',0)*100:.1f}%"
        benchmarks = p.get("benchmarks",{})
        lh_pct = benchmarks.get("last_hits_per_min", {}).get("pct",0)*100 if benchmarks else 0
        hdm_pct = benchmarks.get("hero_damage_per_min", {}).get("pct",0)*100 if benchmarks else 0
        tdm_pct = benchmarks.get("tower_damage", {}).get("pct",0)*100 if benchmarks else 0
        benchmark_str = f"LH {lh_pct:.1f}% | HDM {hdm_pct:.1f}% | TDM {tdm_pct:.1f}%"
        player_map[hid_str] = {
            "name": p.get("name","Unknown"),
            "kda": kda,
            "gpm_xpm": gpm_xpm,
            "lane_eff": lane_eff,
            "benchmarks": benchmark_str
        }

    picks_bans = sorted(data.get("picks_bans",[]), key=lambda x: x.get("order",0))
    radiant_side, dire_side = [], []
    for item in picks_bans:
        hid = item.get("hero_id")
        hid_str = str(hid) if hid is not None else ""
        hero_info = heroes_map.get(hid_str, {"image":"","clean_name":"","localized_name":"Unknown"})
        hero_image_name = hero_info.get("image","")
        hero_clean = hero_info.get("clean_name", hero_image_name.replace(".png",""))
        hero_local = hero_info.get("localized_name","Unknown")
        is_pick = item.get("is_pick",False)
        team = item.get("team",0)
        order_num = item.get("order",0)+1
        label = f"<b><span style='color:#00ff66'>{order_num}. Pick:</span></b>" if is_pick else f"<b><span style='color:#ff3333'>{order_num}. Ban:</span></b>"

        if is_pick:
            player = player_map.get(hid_str)
            if player:
                img_src = f"../../../dictionaries/image/{hero_clean}.png"
                player_text = f"""
                <div class='player-info'>
                    <div class='hero-image'><img src="{img_src}" alt=""></div>
                    <div class='stats'>
                        <div class='player-name'>{player['name']}</div>
                        <div class='stat-row'><span class='label'>KDA:</span><span class='value'>{player['kda']}</span></div>
                        <div class='stat-row'><span class='label'>GPM/XPM:</span><span class='value'>{player['gpm_xpm']}</span></div>
                        <div class='stat-row'><span class='label'>Lane Efficiency:</span><span class='value'>{player['lane_eff']}</span></div>
                        <div class='benchmarks'>{player['benchmarks']}</div>
                    </div>
                </div>"""
            else:
                player_text = "<div class='player-info'><i>No player info</i></div>"
        else:
            player_text = f"<div class='player-info'><div class='hero-name'><b>{hero_local}</b></div></div>"

        record = (item.get("order",0), f"{label}{player_text}")
        if team==0: radiant_side.append(record)
        else: dire_side.append(record)

    radiant_side.sort(key=lambda x:x[0])
    dire_side.sort(key=lambda x:x[0])

    html = []
    html.append("<!doctype html><html><head>")
    html.append('<meta charset="utf-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append(f"<title>{title_text} - Picks & Bans</title>")
    html.append(f"<style>{PAGE_CSS}</style></head><body>")
    html.append(f'<a class="back-link" href="../../../main/index.html">⬅ Back to Match List</a>')
    html.append(f"<h2>{title_text}</h2>")
    html.append("<table>")
    html.append(f"<tr><th>Radiant</th><th>Dire</th></tr>")

    max_rows = max(len(radiant_side), len(dire_side))
    for i in range(max_rows):
        left_text = radiant_side[i][1] if i<len(radiant_side) else ""
        right_text = dire_side[i][1] if i<len(dire_side) else ""
        html.append("<tr>")
        html.append(f"<td>{left_text}</td><td>{right_text}</td>")
        html.append("</tr>")

    html.append("</table></body></html>")

    safe_mkdir(os.path.dirname(out_html_path))
    with open(out_html_path,"w",encoding="utf-8") as f:
        f.write("\n".join(html))

# -------------------------
# Main processing loop
# -------------------------
tournament_series_index = {}

for tourn_name, filepaths in tournaments.items():
    series_groups = defaultdict(list)
    for fp in filepaths:
        fname = os.path.basename(fp)
        m = FILENAME_RE.match(fname)
        if not m: continue
        prefix = m.group("prefix")
        body = m.group("body")
        game_no = int(m.group("gnum"))
        series_id = prefix.split(".")[0]
        series_key = f"{series_id}.{body}"
        series_groups[series_key].append((game_no, fp, prefix, body))

    tournament_series_index[tourn_name] = {}

    for series_key, games in series_groups.items():
        games_sorted = sorted(games,key=lambda x:x[0])
        per_game_meta = []
        winner_counter = Counter()
        for game_no, fp, prefix, body in games_sorted:
            try: data = load_json(fp)
            except Exception as e: 
                print(f"Cannot read {fp}: {e}")
                continue
            radiant_name = data.get("radiant_team", {}).get("name","Radiant")
            dire_name = data.get("dire_team", {}).get("name","Dire")
            radiant_win = data.get("radiant_win",False)
            game_winner = radiant_name if radiant_win else dire_name
            winner_counter[game_winner]+=1
            per_game_meta.append({"game_no":game_no,"data":data,"game_winner":game_winner,"radiant_win":radiant_win})

        if per_game_meta:
            _, series_body = series_key.split(".",1)
            pretty_name = pretty_team_name_from_body(series_body)
            series_winner, _ = winner_counter.most_common(1)[0]
            safe_series_folder_name = sanitize_folder_name(f"{series_key}({series_winner})")
            out_series_folder = os.path.join(MATCHES_DIR, tourn_name, safe_series_folder_name)
            safe_mkdir(out_series_folder)

            for meta in per_game_meta:
                game_no = meta["game_no"]
                data = meta["data"]
                game_winner = meta["game_winner"]
                safe_game_winner = sanitize_folder_name(game_winner)
                out_name = f"Game{game_no}_{safe_game_winner}.html"
                out_path = os.path.join(out_series_folder,out_name)
                head_title = f"{data.get('radiant_team', {}).get('name','Radiant')} (Winner) vs {data.get('dire_team', {}).get('name','Dire')}" if meta["radiant_win"] else f"{data.get('radiant_team', {}).get('name','Radiant')} vs {data.get('dire_team', {}).get('name','Dire')} (Winner)"
                generate_match_html(data, hero_dict, out_path, title_text_override=head_title)
                print(f"Generated {out_path}")

            # Series index
            series_index_path = os.path.join(out_series_folder,"index.html")
            list_html = []
            list_html.append("<!doctype html><html><head>")
            list_html.append('<meta charset="utf-8">')
            list_html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            list_html.append(f"<title>{pretty_name} - Series</title>")
            list_html.append(f"<style>{SERIES_INDEX_CSS}</style></head><body>")
            list_html.append(f'<a class="back-link" href="../../../main/index.html">⬅ Back to Match List</a>')
            list_html.append(f"<h2>{pretty_name} — Series Winner: {series_winner}</h2>")
            list_html.append("<ul>")
            for meta in per_game_meta:
                game_no = meta["game_no"]
                game_winner = meta["game_winner"]
                safe_game_winner = sanitize_folder_name(game_winner)
                game_file_name = f"Game{game_no}_{safe_game_winner}.html"
                link = urllib.parse.quote(game_file_name)
                list_html.append(f'<li><a href="./{link}">Game{game_no} — {game_winner}</a></li>')
            list_html.append("</ul></body></html>")
            with open(series_index_path,"w",encoding="utf-8") as f:
                f.write("\n".join(list_html))
            print(f"Series index created: {series_index_path}")

            tournament_series_index[tourn_name][safe_series_folder_name] = {
                "pretty_name": pretty_name,
                "series_winner": series_winner,
                "series_path": os.path.relpath(out_series_folder, MATCHES_DIR).replace("\\","/")
            }

# -------------------------
# Main index.html
# -------------------------
main_html = []
main_html.append("<!doctype html><html><head>")
main_html.append('<meta charset="utf-8">')
main_html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
main_html.append("<title>Dota 2 Match List</title>")
main_html.append(f"<style>{MAIN_INDEX_CSS}</style></head><body>")
main_html.append("<h2>Dota 2 Match List</h2>")

for tourn, series_dict in sorted(tournament_series_index.items()):
    main_html.append(f"<h3>{tourn}</h3><ul>")
    for series_folder, meta in sorted(series_dict.items()):
        link = os.path.join("..","matches",tourn,series_folder,"index.html").replace("\\","/")
        link = urllib.parse.quote(link,safe="/")
        label = f"{meta['pretty_name']} — Winner: {meta['series_winner']}"
        main_html.append(f'<li><a href="{link}">{label}</a></li>')
    main_html.append("</ul>")

main_html.append("</body></html>")

with open(MAIN_INDEX,"w",encoding="utf-8") as f:
    f.write("\n".join(main_html))

print(f"\nMain index generated at: {MAIN_INDEX}")
print("Done.")
