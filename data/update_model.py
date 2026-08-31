#!/usr/bin/env python3
"""Deterministic pipeline to update ffmarket/src/lib/model.ts.

Steps:
  1. Read DraftSharks rankings from ppr_rankings.csv
  2. Fetch ESPN rosters, schedule, and projected points via espn_api
  3. Merge: DS projections preferred, ESPN projections as fallback
  4. Generate TypeScript constants and splice into model.ts

Usage:
    python update_model.py              # fetch ESPN + read DS, update model.ts
    python update_model.py --dry-run    # print what would be generated

Prerequisite:
    python parse_rankings.py            # scrape fresh DraftSharks data first
"""

import csv
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'analysis'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'ffmarket', 'src', 'lib', 'model.ts')
CSV_PATH = os.path.join(BASE_DIR, 'ppr_rankings.csv')
ROSTERS_PATH = os.path.join(BASE_DIR, 'espn_rosters.json')


def norm_name(n: str) -> str:
    n = re.sub(r'\s+(Jr\.?|Sr\.?|III|II|IV|V)$', '', n, flags=re.IGNORECASE)
    return n.replace('.', '').replace("'", '').replace('-', '').lower().strip()


ALIASES = {
    'cam skattebo': 'cameron skattebo',
    'kenny gainwell': 'kenneth gainwell',
    'chig okonkwo': 'chigoziem okonkwo',
}


def load_ds_rankings() -> dict[str, tuple[str, float, float]]:
    """Load DraftSharks rankings: name -> (pos, ds_proj, games_missed)."""
    players = {}
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            if row['position'] in ('K', 'DEF') or not row['ds_proj']:
                continue
            players[row['name']] = (
                row['position'],
                float(row['ds_proj']),
                float(row['projected_games_missed']) if row['projected_games_missed'] else 1.5,
            )
    return players


def fetch_espn_data() -> dict:
    """Fetch rosters and schedule from ESPN API, save to espn_rosters.json."""
    from espnsecrets import LEAGUE_ID, YEAR, espn_s2, swid
    from espn_api.football import League

    league = League(league_id=LEAGUE_ID, year=YEAR, swid=swid, espn_s2=espn_s2)
    reg_weeks = league.settings.reg_season_count

    data = {'teams': {}, 'schedule': {}, 'reg_weeks': reg_weeks}

    for team in league.teams:
        tid = team.team_id
        players = []
        for p in team.roster:
            players.append({
                'name': p.name,
                'position': p.position,
                'proTeam': p.proTeam,
                'playerId': p.playerId,
                'projected_points': round(p.projected_total_points, 1)
                    if hasattr(p, 'projected_total_points') and p.projected_total_points else None,
            })
        data['teams'][tid] = {
            'team_id': tid,
            'team_name': team.team_name,
            'owner': team.owners[0].get('firstName', '') + ' ' + team.owners[0].get('lastName', '')
                if team.owners else 'Unknown',
            'players': players,
        }

    for week in range(1, reg_weeks + 1):
        matchups = league.scoreboard(week=week)
        opponents = {}
        for m in matchups:
            opponents[m._home_team_id] = m._away_team_id
            opponents[m._away_team_id] = m._home_team_id
        data['schedule'][week] = opponents

    with open(ROSTERS_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Saved ESPN data to {ROSTERS_PATH}')
    return data


def load_espn_data() -> dict:
    """Load cached ESPN data, or fetch if missing."""
    if not os.path.exists(ROSTERS_PATH):
        return fetch_espn_data()
    with open(ROSTERS_PATH) as f:
        data = json.load(f)
    if 'teams' not in data:
        return fetch_espn_data()
    return data


def merge_players(ds: dict, espn_data: dict) -> dict[str, tuple[str, float, float]]:
    """Start with DS rankings, add ESPN fallbacks for rostered players not in DS."""
    merged = dict(ds)
    ds_norm = {norm_name(n) for n in ds}
    ds_norm.update({ALIASES.get(norm_name(n), norm_name(n)) for n in ds})

    for team in espn_data['teams'].values():
        for p in team['players']:
            if p['position'] in ('K', 'D/ST'):
                continue
            name = p['name']
            normed = norm_name(name)
            alias = ALIASES.get(normed, normed)
            if normed in ds_norm or alias in ds_norm:
                continue
            if name in merged:
                continue
            proj = p.get('projected_points')
            if proj and proj > 0:
                merged[name] = (p['position'], proj, 1.5)

    return merged


def generate_ds_players(merged: dict) -> str:
    lines = ['const DS_PLAYERS: Record<string, [string, number, number]> = {']
    items = list(merged.items())
    for i in range(0, len(items), 2):
        pair = items[i:i+2]
        entries = []
        for name, (pos, proj, gm) in pair:
            gm_str = f'{gm:.2f}' if gm != round(gm, 1) else str(round(gm, 1))
            entries.append(f'"{name}": ["{pos}", {round(proj, 1)}, {gm_str}]')
        lines.append('  ' + ', '.join(entries) + ',')
    lines.append('};')
    return '\n'.join(lines)


def generate_teams_raw(espn_data: dict) -> str:
    lines = ['const TEAMS_RAW: [number, string, [string, string][]][] = [']
    for tid in sorted(espn_data['teams'], key=lambda k: int(k)):
        team = espn_data['teams'][tid]
        name = team['team_name']
        offense = [p for p in team['players'] if p['position'] not in ('K', 'D/ST')]
        roster_str = ', '.join(f'["{p["name"]}", "{p["position"]}"]' for p in offense)
        lines.append(f'  [{tid}, {json.dumps(name)}, [{roster_str}]],')
    lines.append('];')
    return '\n'.join(lines)


def generate_schedule(espn_data: dict) -> str:
    lines = ['const SCHEDULE: Record<number, number[]> = {']
    team_ids = sorted(espn_data['teams'], key=lambda k: int(k))
    reg_weeks = espn_data.get('reg_weeks', 14)
    for tid in team_ids:
        tid_int = int(tid)
        opponents = []
        for week in range(1, reg_weeks + 1):
            week_data = espn_data['schedule'].get(str(week), espn_data['schedule'].get(week, {}))
            opp = week_data.get(str(tid_int), week_data.get(tid_int, 0))
            opponents.append(str(opp))
        pad = ' ' * (2 - len(str(tid_int)))
        lines.append(f'  {tid_int}:{pad} [{", ".join(opponents)}],')
    lines.append('};')
    return '\n'.join(lines)


def generate_espn_k_dst(espn_data: dict) -> str:
    lines = ['const ESPN_K_DST: Record<number, { k?: [string, number]; dst?: [string, number] }> = {']
    for tid in sorted(espn_data['teams'], key=lambda k: int(k)):
        team = espn_data['teams'][tid]
        ks = [p for p in team['players'] if p['position'] == 'K' and p.get('projected_points')]
        dsts = [p for p in team['players'] if p['position'] == 'D/ST' and p.get('projected_points')]

        best_k = max(ks, key=lambda p: p['projected_points']) if ks else None
        best_dst = max(dsts, key=lambda p: p['projected_points']) if dsts else None

        parts = []
        if best_k:
            parts.append(f'k: ["{best_k["name"]}", {best_k["projected_points"]}]')
        if best_dst:
            parts.append(f'dst: ["{best_dst["name"]}", {best_dst["projected_points"]}]')

        pad = ' ' * (2 - len(str(int(tid))))
        if parts:
            lines.append(f'  {tid}:{pad} {{ {", ".join(parts)} }},')
        else:
            lines.append(f'  {tid}:{pad} {{}},')
    lines.append('};')
    return '\n'.join(lines)


def splice_block(source: str, marker_start: str, marker_end: str, new_block: str) -> str:
    pattern = re.compile(
        re.escape(marker_start) + r'.*?' + re.escape(marker_end),
        re.DOTALL,
    )
    return pattern.sub(new_block, source)


MARKERS = {
    'DS_PLAYERS': (
        'const DS_PLAYERS: Record<string, [string, number, number]> = {',
        '};',
    ),
    'TEAMS_RAW': (
        'const TEAMS_RAW: [number, string, [string, string][]][] = [',
        '];',
    ),
    'SCHEDULE': (
        'const SCHEDULE: Record<number, number[]> = {',
        '};',
    ),
    'ESPN_K_DST': (
        'const ESPN_K_DST: Record<number, { k?: [string, number]; dst?: [string, number] }> = {',
        '};',
    ),
}


def update_model_ts(blocks: dict[str, str]):
    with open(MODEL_PATH) as f:
        source = f.read()

    for name, new_block in blocks.items():
        start_marker, end_marker = MARKERS[name]
        start_idx = source.find(start_marker)
        if start_idx == -1:
            print(f'WARNING: Could not find {name} block in model.ts')
            continue
        end_idx = source.find(end_marker, start_idx + len(start_marker))
        if end_idx == -1:
            print(f'WARNING: Could not find end of {name} block')
            continue
        source = source[:start_idx] + new_block + source[end_idx + len(end_marker):]

    with open(MODEL_PATH, 'w') as f:
        f.write(source)
    print(f'Updated {MODEL_PATH}')


def main():
    dry_run = '--dry-run' in sys.argv
    refetch = '--fetch' in sys.argv

    print('Loading DraftSharks rankings...')
    ds = load_ds_rankings()
    print(f'  {len(ds)} players from ppr_rankings.csv')

    if refetch or not os.path.exists(ROSTERS_PATH) or '--fetch' in sys.argv:
        print('Fetching ESPN data...')
        espn_data = fetch_espn_data()
    else:
        print('Loading cached ESPN data...')
        espn_data = load_espn_data()

    team_count = len(espn_data['teams'])
    print(f'  {team_count} teams')

    print('Merging player projections...')
    merged = merge_players(ds, espn_data)
    espn_only = len(merged) - len(ds)
    print(f'  {len(ds)} DraftSharks + {espn_only} ESPN fallbacks = {len(merged)} total')

    blocks = {
        'DS_PLAYERS': generate_ds_players(merged),
        'TEAMS_RAW': generate_teams_raw(espn_data),
        'SCHEDULE': generate_schedule(espn_data),
        'ESPN_K_DST': generate_espn_k_dst(espn_data),
    }

    if dry_run:
        for name, block in blocks.items():
            print(f'\n=== {name} ===')
            print(block)
    else:
        update_model_ts(blocks)

    print('\nTeam summary:')
    for tid in sorted(espn_data['teams'], key=lambda k: int(k)):
        team = espn_data['teams'][tid]
        offense = [p for p in team['players'] if p['position'] not in ('K', 'D/ST')]
        ks = [p for p in team['players'] if p['position'] == 'K']
        dsts = [p for p in team['players'] if p['position'] == 'D/ST']
        print(f'  {int(tid):>2}. {team["team_name"]:<35} {len(offense)} off, {len(ks)} K, {len(dsts)} DST')

    unmatched = []
    ds_norm = {norm_name(n) for n in ds}
    ds_norm.update({ALIASES.get(norm_name(n), norm_name(n)) for n in ds})
    for team in espn_data['teams'].values():
        for p in team['players']:
            if p['position'] in ('K', 'D/ST'):
                continue
            normed = norm_name(p['name'])
            alias = ALIASES.get(normed, normed)
            if normed not in ds_norm and alias not in ds_norm and p['name'] not in merged:
                unmatched.append((p['name'], p['position'], p.get('projected_points')))

    if unmatched:
        print(f'\nRostered players with no projection at all ({len(unmatched)}):')
        for name, pos, pts in sorted(unmatched, key=lambda x: -(x[2] or 0)):
            print(f'  {pos:<4} {name:<30} ESPN proj={pts}')


if __name__ == '__main__':
    main()
