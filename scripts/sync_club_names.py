import sqlite3
import unicodedata
import re

def normalize_name(name):
    if not name: return ""
    # Remove accents
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    # Remove all non-alphanumeric
    name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return name

conn = sqlite3.connect('backend/database/ttcn.db')
c = conn.cursor()

c.execute("SELECT id, name FROM clubs")
clubs = c.fetchall()

c.execute("SELECT DISTINCT tm_club FROM player_info WHERE tm_club IS NOT NULL")
player_tm_clubs = [row[0] for row in c.fetchall()]

c.execute("SELECT DISTINCT team_title FROM player_info WHERE team_title IS NOT NULL")
player_titles = [row[0] for row in c.fetchall()]

all_pcnames = set(player_tm_clubs + player_titles)

mapping = {}
for cid, cname in clubs:
    norm_c = normalize_name(cname)
    for pcname in all_pcnames:
        if normalize_name(pcname) == norm_c and pcname != cname:
            mapping[pcname] = cname

print("Mapping found:")
for k, v in mapping.items():
    print(f"'{k}' -> '{v}'")

if mapping:
    for pcname, cname in mapping.items():
        print(f"Updating '{pcname}' to '{cname}' in player_info...")
        c.execute("UPDATE player_info SET tm_club = ? WHERE tm_club = ?", (cname, pcname))
        c.execute("UPDATE player_info SET team_title = ? WHERE team_title = ?", (cname, pcname))
    conn.commit()
    print("Done.")
else:
    print("No mismatches found.")

conn.close()
