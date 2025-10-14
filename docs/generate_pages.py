import os

root = "matches"
output = "index.html"

html_start = """<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>True Sight - Match Index</title>
<link rel="stylesheet" href="assets/css/main.css">
<style>
    body {
        background: #101010;
        color: #fff;
        font-family: Arial, sans-serif;
        text-align: center;
        padding: 20px;
    }
    ul {
        list-style: none;
        padding: 0;
    }
    li {
        margin: 8px 0;
    }
    a {
        color: #00bfff;
        text-decoration: none;
        font-size: 1.1em;
    }
</style>
</head>
<body>
<h2>🏆 Dota 2 Match Archive</h2>
<ul>
"""

html_end = """
</ul>
</body>
</html>
"""

def walk_matches(base):
    html = ""
    for tournament in sorted(os.listdir(base)):
        tournament_path = os.path.join(base, tournament)
        if not os.path.isdir(tournament_path):
            continue
        html += f"<li><a href='{base}/{tournament}/'>{tournament}</a>\n<ul>\n"
        for match in sorted(os.listdir(tournament_path)):
            match_path = os.path.join(tournament_path, match)
            if os.path.isdir(match_path):
                html += f"  <li><a href='{base}/{tournament}/{match}/index.html'>{match}</a></li>\n"
        html += "</ul>\n</li>\n"
    return html

match_list_html = walk_matches(root)

with open(output, "w", encoding="utf-8") as f:
    f.write(html_start + match_list_html + html_end)

print(f"✅ Generated index.html with matches under {root}/")
