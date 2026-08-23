#!/usr/bin/env python3
"""Apply keeper adjustments and regenerate draft_board.html data.

Reads ppr_rankings.csv + keepers.json, computes adjusted ranks,
and rewrites the DATA and KEEPERS blocks in draft_board.html.

Usage:
    python apply_keepers.py

Pipeline:
    1. python parse_rankings.py      # scrape fresh rankings
    2. python apply_keepers.py        # apply keepers to draft board
    3. python compute_keeper_value.py # (optional) regenerate keeper value table
"""

import csv
import json
import math
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


def build_comp_data(data, keepers, ext_path, rank_field):
    """Build comparison data between a base ranking and an external ranking source."""
    keeper_set = {k['name'] for k in keepers}
    ds_by_name = {row[1]: row for row in data}

    try:
        with open(ext_path) as f:
            ext_players = list(csv.DictReader(f))
    except FileNotFoundError:
        return []

    ext_by_name = {}
    for ep in ext_players:
        ds_name = ALIAS_TO_DS.get(ep['name'], ep['name'])
        ext_by_name[ds_name] = int(ep[rank_field])

    ds_keeper_info = []
    ext_keeper_info = []
    for row in data:
        if row[1] in keeper_set:
            k = next(ki for ki in keepers if ki['name'] == row[1])
            overall_pick = (k['round'] - 1) * TEAMS + k['pick']
            ds_keeper_info.append({
                'origRank': row[0],
                'overallPick': overall_pick
            })
            ext_rank = ext_by_name.get(row[1], row[0])
            ext_keeper_info.append({
                'origRank': ext_rank,
                'overallPick': overall_pick
            })

    def adj_ds(orig):
        return orig - sum(1 for k in ds_keeper_info
                          if k['origRank'] < orig and k['overallPick'] > orig)

    def adj_ext(rank):
        return rank - sum(1 for k in ext_keeper_info
                          if k['origRank'] < rank and k['overallPick'] > rank)

    comp = []
    for ep in ext_players:
        ds_name = ALIAS_TO_DS.get(ep['name'], ep['name'])
        ext_rank = int(ep[rank_field])
        if ds_name not in ds_by_name or ds_name in keeper_set:
            continue
        ds_rank = ds_by_name[ds_name][0]
        ds_adj = adj_ds(ds_rank)
        ext_adj = adj_ext(ext_rank)
        pos = ds_by_name[ds_name][2]
        if ext_adj > 155 and ds_adj > 155:
            continue
        comp.append([ds_name, pos, ds_adj, ext_adj, ds_rank, ext_rank])

    comp.sort(key=lambda x: x[3])
    return comp


def update_html(data, keepers, comp, comp_fp, comp_boone, comp_boone_fp,
                comp_ciely, comp_ciely_fp):
    with open(HTML_PATH) as f:
        html = f.read()

    blocks = {
        'DATA': 'const DATA=' + json.dumps(data, separators=(',', ':')) + ';',
        'KEEPERS': 'const KEEPERS=' + json.dumps(keepers, separators=(',', ':')) + ';',
        'COMP': 'const COMP=' + json.dumps(comp, separators=(',', ':')) + ';',
        'COMP_FP': 'const COMP_FP=' + json.dumps(comp_fp, separators=(',', ':')) + ';',
        'COMP_BOONE': 'const COMP_BOONE=' + json.dumps(comp_boone, separators=(',', ':')) + ';',
        'COMP_BOONE_FP': 'const COMP_BOONE_FP=' + json.dumps(comp_boone_fp, separators=(',', ':')) + ';',
        'COMP_CIELY': 'const COMP_CIELY=' + json.dumps(comp_ciely, separators=(',', ':')) + ';',
        'COMP_CIELY_FP': 'const COMP_CIELY_FP=' + json.dumps(comp_ciely_fp, separators=(',', ':')) + ';',
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
    comp = build_comp_data(data, keepers, ESPN_PATH, 'espn_ppr_rank')
    comp_fp = build_comp_data(data, keepers, FP_PATH, 'fp_ppr_rank')

    boone_data = load_base_ranking(BOONE_PATH, 'boone_ppr_rank')
    comp_boone = build_comp_data(boone_data, keepers, ESPN_PATH, 'espn_ppr_rank')
    comp_boone_fp = build_comp_data(boone_data, keepers, FP_PATH, 'fp_ppr_rank')

    ciely_data = load_base_ranking(CIELY_PATH, 'fpx_ppr_rank')
    comp_ciely = build_comp_data(ciely_data, keepers, ESPN_PATH, 'espn_ppr_rank')
    comp_ciely_fp = build_comp_data(ciely_data, keepers, FP_PATH, 'fp_ppr_rank')

    update_html(data, keepers, comp, comp_fp, comp_boone, comp_boone_fp,
                comp_ciely, comp_ciely_fp)
    print(f"Comparison data: DS({len(comp)} ESPN, {len(comp_fp)} FP) "
          f"Boone({len(comp_boone)} ESPN, {len(comp_boone_fp)} FP) "
          f"Ciely({len(comp_ciely)} ESPN, {len(comp_ciely_fp)} FP)")
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
