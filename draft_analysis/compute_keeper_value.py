#!/usr/bin/env python3
"""Compute keeper value adjustment for each player.

Reads ppr_rankings.csv, applies a per-player keeper value function,
and writes keeper_rankings.csv with all original columns plus value_change.

Keeper rules (12-team league):
  - Keep up to 2 players year-over-year
  - Keeper cost = drafted round - 2 (escalates each year)
  - Waiver wire adds cost an 8th round pick

Model: keeper value = runway_premium * sustainability + age_bonus + injury_bonus

The model captures three things the user specified:
  1. Right-tail on draft round: later-round players have more keeper years (runway)
  2. Non-linear round value: sustainability matters more for valuable players
  3. Upside vs risk: age (position-specific cliffs), injury risk, experience
"""

import csv
import math

TEAMS = 12
MAX_ROUNDS = 16


# ── Age sustainability curves ────────────────────────────────────
# Research-backed position-specific age factors.
# Returns 0.15 (post-cliff) to 1.15 (ascending/prime).

def age_factor(pos: str, age: int) -> float:
    if pos == 'RB':
        # Peak 24-26, cliff at 27-28. Sharpest of any position.
        # Source: Northwestern Sports Analytics, Fantasy Football Blueprint
        if age <= 23:   return 1.15
        if age <= 26:   return 1.10
        if age == 27:   return 0.75
        if age == 28:   return 0.45
        if age == 29:   return 0.25
        return 0.15

    if pos == 'WR':
        # Peak 25-28 (avg 26.95). 87% of peak seasons before 30.
        # Source: Apex Fantasy, Footballguys
        if age <= 24:   return 1.10
        if age <= 28:   return 1.05
        if age == 29:   return 0.90
        if age <= 31:   return 0.70
        if age == 32:   return 0.45
        return 0.25

    if pos == 'TE':
        # Longest peak of skill positions. Avg peak 27.5, cliff after 32.
        # Source: PFF, Rotoballer
        if age <= 24:   return 1.10
        if age <= 27:   return 1.10
        if age <= 30:   return 1.00
        if age <= 32:   return 0.60
        if age == 33:   return 0.35
        return 0.20

    if pos == 'QB':
        # Pocket passers peak at 30.7, dual-threat at 26.1.
        # Single curve is a compromise. Source: PFF, ESPN
        if age <= 25:   return 1.10
        if age <= 30:   return 1.05
        if age <= 34:   return 0.90
        if age <= 37:   return 0.55
        if age <= 39:   return 0.30
        return 0.15

    return 0.80


# ── Injury risk factor ───────────────────────────────────────────
# "Pretty discriminatory" — high injury risk tanks keeper value.

def injury_factor(injury_risk_str: str) -> float:
    pct = float(injury_risk_str.replace('%', '')) / 100.0
    if pct <= 0.20:   return 1.15
    if pct <= 0.30:   return 1.05
    if pct <= 0.40:   return 0.90
    if pct <= 0.50:   return 0.75
    if pct <= 0.65:   return 0.55
    if pct <= 0.80:   return 0.35
    return 0.20


# ── Years in NFL factor ──────────────────────────────────────────

def experience_factor(pos: str, age: int, years_exp: int) -> float:
    if years_exp is None or age is None:
        return 1.0

    if pos == 'RB':
        if age <= 24 and years_exp <= 2: return 1.10
        if age <= 26 and years_exp <= 3: return 1.05
    elif pos == 'WR':
        if age <= 25 and years_exp <= 3: return 1.10
        if age <= 27 and years_exp <= 4: return 1.05
    elif pos == 'TE':
        if age <= 26 and years_exp <= 3: return 1.10
        if age <= 28 and years_exp <= 4: return 1.05
    elif pos == 'QB':
        if age <= 26 and years_exp <= 3: return 1.10
        if age <= 28 and years_exp <= 4: return 1.05

    if pos == 'RB' and age >= 28 and years_exp >= 6:  return 0.90
    if pos == 'WR' and age >= 31 and years_exp >= 8:  return 0.90
    if pos == 'TE' and age >= 32 and years_exp >= 9:  return 0.90
    if pos == 'QB' and age >= 36 and years_exp >= 12: return 0.90

    return 1.0


# ── Main keeper value function ───────────────────────────────────

def compute_value_change(player: dict) -> float:
    """
    Compute keeper value adjustment to 3D value.

    Components:
      1. Runway premium: right-tail on value round — later-round players
         have more keeper years, making them better keeper candidates.
      2. Sustainability multiplier: age × injury × experience modulates
         the runway. Only young/healthy players realize keeper potential.
      3. Direct age + injury bonus/penalty: even without runway, youth
         and health have keeper value, and age/injury have costs.
    """
    rank = int(player['rank'])
    pos = player['position']
    age = int(player['age']) if player['age'] else 27
    years_exp = int(player['years_in_nfl']) if player['years_in_nfl'] else None
    injury_str = player['injury_risk'] if player['injury_risk'] else '40%'

    # What round this player is worth (by overall rank)
    value_round = min(MAX_ROUNDS, max(1, math.ceil(rank / TEAMS)))

    # ── Runway premium ──
    # Right-tail: later round = more keeper years = more premium.
    # Rounds 1-2 have no keeper runway (cost immediately hits round 1).
    # Power > 1 gives convex (accelerating) shape.
    if value_round <= 2:
        runway_score = 0.0
    else:
        runway_score = (value_round - 2) ** 1.15 * 0.5

    # ── Sustainability ──
    age_mult = age_factor(pos, age)
    inj_mult = injury_factor(injury_str)
    exp_mult = experience_factor(pos, age, years_exp)
    sustainability = age_mult * inj_mult * exp_mult

    # Runway is only valuable if the player will maintain/improve value.
    # sustainability > 0.5 → runway adds value (ascending/prime player)
    # sustainability < 0.5 → runway subtracts value (declining player)
    runway_component = runway_score * (sustainability - 0.5)

    # ── Direct age and injury bonuses ──
    age_direct = (age_mult - 0.7) * 6
    injury_direct = (inj_mult - 0.7) * 5

    value_change = runway_component + age_direct + injury_direct
    return round(value_change, 1)


def main():
    input_path = '/Users/esbensorensen/code/fantasy/draft_analysis/ppr_rankings.csv'
    output_path = '/Users/esbensorensen/code/fantasy/draft_analysis/keeper_rankings.csv'

    with open(input_path) as f:
        reader = csv.DictReader(f)
        input_fields = reader.fieldnames
        players = list(reader)

    output_fields = input_fields + ['value_change']

    for p in players:
        p['value_change'] = compute_value_change(p)

    # Sort by keeper-adjusted value (3D + change), descending
    def keeper_sort_key(p):
        base = float(p['three_d_value']) if p['three_d_value'] else 0
        return -(base + p['value_change'])

    players.sort(key=keeper_sort_key)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(players)

    print(f"Wrote {len(players)} players to {output_path}\n")

    print(f"{'':>3} {'Name':<25} {'Pos':<4} {'Age':<4} {'Rd':<3} {'Inj':<6} "
          f"{'3D':>5} {'Chg':>6} {'Adj':>6}")
    print("-" * 72)
    for p in players[:25]:
        base = float(p['three_d_value']) if p['three_d_value'] else 0
        chg = p['value_change']
        adj = base + chg
        value_round = min(16, max(1, math.ceil(int(p['rank']) / 12)))
        print(f"{p['rank']:>3} {p['name']:<25} {p['position']:<4} {p['age']:<4} "
              f"{value_round:<3} {p['injury_risk']:<6} "
              f"{base:>5.0f} {chg:>+6.1f} {adj:>6.1f}")

    print("\n── Biggest keeper value boosts ──")
    by_change = sorted(players, key=lambda p: -p['value_change'])
    for p in by_change[:10]:
        base = float(p['three_d_value']) if p['three_d_value'] else 0
        vr = min(16, max(1, math.ceil(int(p['rank']) / 12)))
        print(f"  {p['name']:<25} {p['position']:<4} Age:{p['age']:<3} Rd:{vr:<3} "
              f"3D:{base:>5.0f} Δ{p['value_change']:>+6.1f}")

    print("\n── Biggest keeper value drops ──")
    for p in by_change[-10:]:
        base = float(p['three_d_value']) if p['three_d_value'] else 0
        vr = min(16, max(1, math.ceil(int(p['rank']) / 12)))
        print(f"  {p['name']:<25} {p['position']:<4} Age:{p['age']:<3} Rd:{vr:<3} "
              f"3D:{base:>5.0f} Δ{p['value_change']:>+6.1f}")


if __name__ == '__main__':
    main()
