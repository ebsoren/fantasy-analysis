#!/usr/bin/env python3
"""Parse DraftSharks PPR rankings HTML into a SQLite database.
Fetches age/experience from the Sleeper API."""

import re
import sqlite3
import csv
import subprocess
import json


def parse_player_blocks(html: str) -> list[dict]:
    """Extract player data from the DraftSharks table HTML."""
    players = []
    blocks = re.split(r'<tbody\s+data-player-row', html)

    for block in blocks[1:]:
        player = {}

        m = re.search(r'data-player-name="([^"]+)"', block)
        if not m:
            continue
        player['name'] = m.group(1)

        m = re.search(r'data-fantasy-position="([^"]+)"', block)
        player['position'] = m.group(1) if m else ''

        m = re.search(r'<span class="player-details-group__team-name">([^<]+)</span>', block)
        player['team'] = m.group(1).strip() if m else ''

        m = re.search(r'<div class="column-title rank-index">\s*<span>(\d+)</span>', block)
        player['rank'] = int(m.group(1)) if m else 999

        def get_data_value(attr_name):
            pattern = rf'data-value="([^"]*)"[^>]*data-attribute="{re.escape(attr_name)}"'
            match = re.search(pattern, block)
            if not match:
                pattern = rf'data-attribute="{re.escape(attr_name)}"[^>]*data-value="([^"]*)"'
                match = re.search(pattern, block)
            return match.group(1) if match else ''

        player['games'] = get_data_value('games_played')
        player['adp'] = get_data_value('adp')
        player['bye'] = get_data_value('player.team.bye')
        player['sos'] = get_data_value('strength_of_schedule')
        player['injury_risk'] = get_data_value('player.sipPlayerProfile.injury_prob')
        player['floor_proj'] = get_data_value('floor_points')
        player['consensus_proj'] = get_data_value('consensus_projection')
        player['ds_proj'] = get_data_value('fantasy_points')
        player['ceiling_proj'] = get_data_value('ceiling_points')
        player['three_d_value'] = get_data_value('dsValue')

        m = re.search(r'data-tier-overall="([^"]*)"', block)
        player['tier_overall'] = m.group(1) if m else ''
        m = re.search(r'data-tier-positional="([^"]*)"', block)
        player['tier_positional'] = m.group(1) if m else ''

        players.append(player)

    return players


def fetch_html(position_filter: str) -> str:
    """Fetch the rankings table HTML from DraftSharks."""
    url = f'https://www.draftsharks.com/rankings/load-table?pprSuperflexSlug=ppr&fantasyPosition={position_filter}&researchDepth=rankings&playerGroup=all&sort='
    result = subprocess.run(
        ['curl', '-s', url,
         '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
         '-H', 'HX-Request: true'],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout


def safe_float(val):
    try:
        return float(val) if val else None
    except (ValueError, TypeError):
        return None


def safe_int(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def create_database(players: list[dict], db_path: str):
    """Write player data to SQLite."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS players')
    c.execute('''
        CREATE TABLE players (
            rank INTEGER,
            name TEXT,
            position TEXT,
            team TEXT,
            games INTEGER,
            adp REAL,
            bye INTEGER,
            sos TEXT,
            injury_risk TEXT,
            floor_proj REAL,
            consensus_proj REAL,
            ds_proj REAL,
            ceiling_proj REAL,
            three_d_value REAL,
            tier_overall INTEGER,
            tier_positional INTEGER,
            age INTEGER,
            years_in_nfl INTEGER,
            nfl_draft_round INTEGER
        )
    ''')

    for p in players:
        c.execute('''
            INSERT INTO players (rank, name, position, team, games, adp, bye, sos,
                injury_risk, floor_proj, consensus_proj, ds_proj, ceiling_proj,
                three_d_value, tier_overall, tier_positional, age, years_in_nfl,
                nfl_draft_round)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            p['rank'], p['name'], p['position'], p['team'],
            safe_int(p['games']), safe_float(p['adp']),
            safe_int(p['bye']), p['sos'], p['injury_risk'],
            safe_float(p['floor_proj']), safe_float(p['consensus_proj']),
            safe_float(p['ds_proj']), safe_float(p['ceiling_proj']),
            safe_float(p['three_d_value']),
            safe_int(p['tier_overall']), safe_int(p['tier_positional']),
            p.get('age'), p.get('years_in_nfl'),
            safe_int(p.get('nfl_draft_round')),
        ))

    conn.commit()
    conn.close()


def write_csv(players: list[dict], csv_path: str):
    """Also write a CSV."""
    fields = ['rank', 'name', 'position', 'team', 'games', 'adp', 'bye', 'sos',
              'injury_risk', 'floor_proj', 'consensus_proj', 'ds_proj', 'ceiling_proj',
              'three_d_value', 'tier_overall', 'tier_positional', 'age', 'years_in_nfl',
              'nfl_draft_round']
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(players)


def load_sleeper_data() -> dict[str, dict]:
    """Fetch age and experience data from Sleeper API."""
    print("Fetching age/experience from Sleeper API...")
    result = subprocess.run(
        ['curl', '-s', 'https://api.sleeper.app/v1/players/nfl',
         '-H', 'User-Agent: Mozilla/5.0'],
        capture_output=True, text=True, timeout=30
    )
    data = json.loads(result.stdout)
    lookup = {}
    for pid, p in data.items():
        name = p.get('full_name')
        if name and p.get('position') in ('QB', 'RB', 'WR', 'TE', 'K', 'DEF'):
            lookup[name] = {
                'age': p.get('age'),
                'years_exp': p.get('years_exp'),
            }
    print(f"  Loaded {len(lookup)} player profiles")
    return lookup


def normalize_name(name: str) -> str:
    """Strip suffixes and punctuation for fuzzy matching."""
    name = name.strip()
    for suffix in [' Jr.', ' Jr', ' III', ' II', ' IV', ' Sr.', ' Sr']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.replace('.', '').replace("'", '').lower()


ALIASES = {
    'Cameron Skattebo': 'Cam Skattebo',
    'Chigoziem Okonkwo': 'Chig Okonkwo',
    'Kenneth Gainwell': 'Kenny Gainwell',
}


def load_nfl_draft_rounds() -> dict[str, int]:
    """Fetch NFL draft round for active players from nflverse."""
    print("Fetching NFL draft rounds from nflverse...")
    url = 'https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv'
    result = subprocess.run(
        ['curl', '-sL', url, '-H', 'User-Agent: Mozilla/5.0'],
        capture_output=True, text=True, timeout=30
    )
    lookup = {}
    reader = csv.DictReader(result.stdout.splitlines())
    for row in reader:
        name = row.get('pfr_player_name', '')
        rd = row.get('round', '')
        if name and rd:
            lookup[name] = int(rd)
    norm_lookup = {}
    for name, rd in lookup.items():
        norm_lookup[normalize_name(name)] = rd
    print(f"  Loaded {len(lookup)} draft picks")
    return lookup, norm_lookup


def enrich_with_age(players: list[dict], sleeper: dict[str, dict],
                    draft_rounds: dict[str, int], draft_rounds_norm: dict[str, int]) -> int:
    """Add age, years_in_nfl, nfl_draft_round from Sleeper + nflverse data. Returns count of matches."""
    norm_lookup = {}
    for name, info in sleeper.items():
        norm_lookup[normalize_name(name)] = info

    matched = 0
    for p in players:
        info = sleeper.get(p['name'])
        if not info:
            alias = ALIASES.get(p['name'], p['name'])
            info = sleeper.get(alias)
        if not info:
            info = norm_lookup.get(normalize_name(p['name']))
        if info:
            p['age'] = info['age']
            p['years_in_nfl'] = info['years_exp']
            matched += 1
        else:
            p['age'] = None
            p['years_in_nfl'] = None

        dr = draft_rounds.get(p['name'])
        if not dr:
            alias = ALIASES.get(p['name'], p['name'])
            dr = draft_rounds.get(alias)
        if not dr:
            dr = draft_rounds_norm.get(normalize_name(p['name']))
        p['nfl_draft_round'] = dr
    return matched


def main():
    print("Fetching PPR rankings...")
    default_html = fetch_html('')
    IDP_POSITIONS = {'LB', 'DL', 'DB'}
    all_players = parse_player_blocks(default_html)
    all_players = [p for p in all_players if p['position'] not in IDP_POSITIONS]
    print(f"  Got {len(all_players)} players (excluding IDP)")

    # Sort by overall rank, re-rank after IDP removal
    # IDP isn't drafted — their rank slots inflate everyone below them
    # K/DEF ARE drafted so they keep their (now compressed) rank positions
    all_players.sort(key=lambda p: p['rank'])
    for i, p in enumerate(all_players):
        p['rank'] = i + 1
    all_players = all_players[:250]

    print(f"\nTotal: {len(all_players)} players")
    pos_counts = {}
    for p in all_players:
        pos_counts[p['position']] = pos_counts.get(p['position'], 0) + 1
    print(f"Position breakdown: {pos_counts}")

    sleeper = load_sleeper_data()
    draft_rounds, draft_rounds_norm = load_nfl_draft_rounds()
    matched = enrich_with_age(all_players, sleeper, draft_rounds, draft_rounds_norm)
    unmatched = [p['name'] for p in all_players if p['age'] is None]
    print(f"  Matched {matched}/{len(all_players)} players")
    if unmatched:
        print(f"  Unmatched: {unmatched}")

    db_path = '/Users/esbensorensen/code/fantasy/draft_analysis/fantasy_rankings.db'
    csv_path = '/Users/esbensorensen/code/fantasy/draft_analysis/ppr_rankings.csv'

    create_database(all_players, db_path)
    write_csv(all_players, csv_path)

    print(f"\nDatabase: {db_path}")
    print(f"CSV: {csv_path}")

    print("\nTop 15:")
    for p in all_players[:15]:
        age_str = str(p.get('age', '?'))
        exp_str = str(p.get('years_in_nfl', '?'))
        print(f"  {p['rank']:>3}. {p['name']:<25} {p['position']:<3} {p['team']:<4} "
              f"Age:{age_str:<3} Exp:{exp_str:<3} "
              f"Injury:{p['injury_risk']:<5} 3D:{p['three_d_value']:<5} ADP:{p['adp']}")


if __name__ == '__main__':
    main()
