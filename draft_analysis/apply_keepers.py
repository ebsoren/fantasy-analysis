#!/usr/bin/env python3
"""Apply keeper adjustments and regenerate index.html data.

Reads ppr_rankings.csv + keepers.json, computes adjusted ranks,
and rewrites the DATA and KEEPERS blocks in index.html.

Usage:
    python apply_keepers.py

Pipeline:
    1. python parse_rankings.py      # scrape fresh rankings
    2. python apply_keepers.py        # apply keepers to draft board
    3. python compute_keeper_value.py # (optional) regenerate keeper value table
"""

import csv
import json
import re

BASE_DIR = '/Users/esbensorensen/code/fantasy/draft_analysis'
CSV_PATH = f'{BASE_DIR}/ppr_rankings.csv'
ESPN_PATH = f'{BASE_DIR}/espn_rankings.csv'
FP_PATH = f'{BASE_DIR}/fp_rankings.csv'
BOONE_PATH = f'{BASE_DIR}/boone_rankings.csv'
CIELY_PATH = f'{BASE_DIR}/fpx_rankings.csv'
KEEPERS_PATH = f'{BASE_DIR}/keepers.json'
HTML_PATH = f'{BASE_DIR}/index.html'
ROOT_HTML_PATH = f'{BASE_DIR}/../index.html'

TEAMS = 12

ALIAS_TO_DS = {
    'James Cook III': 'James Cook',
    'Cam Skattebo': 'Cameron Skattebo',
    'Travis Etienne Jr.': 'Travis Etienne',
    'Kyle Pitts Sr.': 'Kyle Pitts',
    'Kenny Gainwell': 'Kenneth Gainwell',
    'Aaron Jones Sr.': 'Aaron Jones',
    'Deebo Samuel Sr.': 'Deebo Samuel',
    'Chris Godwin Jr.': 'Chris Godwin',
    'DJ Moore': 'D.J. Moore',
    'DK Metcalf': 'D.K. Metcalf',
    'Chris Rodriguez Jr.': 'Chris Rodriguez',
    'Patrick Mahomes II': 'Patrick Mahomes',
    'Cam Ward': 'Cameron Ward',
    'Chig Okonkwo': 'Chigoziem Okonkwo',
}


def load_rankings():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def load_keepers():
    with open(KEEPERS_PATH) as f:
        return json.load(f)


def build_data_array(players):
    data = []
    for r in players:
        data.append([
            int(r['rank']),
            r['name'],
            r['position'],
            r['team'],
            r['bye'],
            r['injury_risk'],
            r['floor_proj'],
            r['ds_proj'],
            r['ceiling_proj'],
            r['three_d_value'],
            r['age'],
            r['years_in_nfl']
        ])
    return data


def compute_adjusted_ranks(data, keepers):
    keeper_set = {k['name'] for k in keepers}
    keeper_rank_info = []
    for row in data:
        name = row[1]
        if name in keeper_set:
            k = next(ki for ki in keepers if ki['name'] == name)
            overall_pick = (k['round'] - 1) * TEAMS + k['pick']
            keeper_rank_info.append({
                'origRank': row[0],
                'overallPick': overall_pick
            })

    results = []
    for row in data:
        orig = row[0]
        is_keeper = row[1] in keeper_set
        if is_keeper:
            adj = None
        else:
            delta = sum(
                1 for k in keeper_rank_info
                if k['origRank'] < orig and k['overallPick'] > orig
            )
            adj = orig - delta
        results.append((row[1], orig, adj, is_keeper))
    return results


def load_base_ranking(path, rank_field):
    """Load a base ranking CSV into a minimal data array [[rank, name, pos], ...]."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return [[int(r[rank_field]), r['name'], r['pos']] for r in rows]


def build_offense_ranks(data):
    """Build offense-only sequential rank array [[name, pos, rank], ...] from any data."""
    OFFENSE = {'QB', 'RB', 'WR', 'TE'}
    rows = sorted([r for r in data if r[2] in OFFENSE], key=lambda r: r[0])
    return [[r[1], r[2], i + 1] for i, r in enumerate(rows)]


def load_ext_ranks(path, rank_field):
    """Load an external CSV and return offense-only sequential ranks."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r[rank_field]))
    result = []
    for i, r in enumerate(rows):
        name = ALIAS_TO_DS.get(r['name'], r['name'])
        result.append([name, r['pos'], i + 1])
    return result


def update_html(data, keepers, boone_data, ciely_data, ranks):
    with open(HTML_PATH) as f:
        html = f.read()

    blocks = {
        'DATA': 'const DATA=' + json.dumps(data, separators=(',', ':')) + ';',
        'KEEPERS': 'const KEEPERS=' + json.dumps(keepers, separators=(',', ':')) + ';',
        'RANKS': 'const RANKS=' + json.dumps(ranks, separators=(',', ':')) + ';',
        'DATA_BOONE': 'const DATA_BOONE=' + json.dumps(boone_data, separators=(',', ':')) + ';',
        'DATA_CIELY': 'const DATA_CIELY=' + json.dumps(ciely_data, separators=(',', ':')) + ';',
    }

    for name, js in blocks.items():
        html = re.sub(
            rf'/\*BEGIN_{name}\*/.*?/\*END_{name}\*/',
            f'/*BEGIN_{name}*/\n{js}\n/*END_{name}*/',
            html,
            flags=re.DOTALL
        )

    for path in (HTML_PATH, ROOT_HTML_PATH):
        with open(path, 'w') as f:
            f.write(html)


def main():
    players = load_rankings()
    keepers = load_keepers()
    data = build_data_array(players)

    print(f"Loaded {len(players)} players, {len(keepers)} keepers\n")

    results = compute_adjusted_ranks(data, keepers)

    boone_data = load_base_ranking(BOONE_PATH, 'boone_ppr_rank')
    ciely_data = load_base_ranking(CIELY_PATH, 'fpx_ppr_rank')

    ranks = {
        'ds': build_offense_ranks(data),
        'boone': build_offense_ranks(boone_data),
        'ciely': build_offense_ranks(ciely_data),
        'espn': load_ext_ranks(ESPN_PATH, 'espn_ppr_rank'),
        'fp': load_ext_ranks(FP_PATH, 'fp_ppr_rank'),
    }

    update_html(data, keepers, boone_data, ciely_data, ranks)
    for key, arr in ranks.items():
        print(f"  {key}: {len(arr)} players")
    print(f"Updated {HTML_PATH}\n")

    print(f"{'Name':<28} {'Pos':<4} {'Rank':>4} {'Adj':>4} {'Δ':>3}")
    print("-" * 46)
    movers = [(name, orig, adj, is_k) for name, orig, adj, is_k in results
              if not is_k and adj is not None and orig != adj]
    movers.sort(key=lambda x: x[1] - x[2], reverse=True)

    for name, orig, adj, _ in movers[:20]:
        pos = next(r['position'] for r in players if r['name'] == name)
        delta = orig - adj
        print(f"{name:<28} {pos:<4} {orig:>4} {adj:>4} {'+' + str(delta):>3}")

    kept = [(name, orig) for name, orig, _, is_k in results if is_k]
    kept.sort(key=lambda x: x[1])
    print(f"\n── Keepers ({len(kept)}) ──")
    for name, orig in kept:
        k = next(ki for ki in keepers if ki['name'] == name)
        print(f"  {name:<28} Rank {orig:>3} → Kept {k['round']}.{k['pick']:02d}")


if __name__ == '__main__':
    main()
