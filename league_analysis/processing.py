import numpy as np
from math import sqrt
from scipy.stats import norm
from league_analysis.models import week_stats

#statistical odds of t1 beating t2
def calc_win_prob(t1, t2):

    t1_points = [week.pts for week in t1.stats]
    t2_points = [week.pts for week in t2.stats]

    mean_t1 = np.mean(t1_points)
    var_t1 = np.var(t1_points, ddof=1) 
    mean_t2 = np.mean(t2_points)
    var_t2 = np.var(t2_points, ddof=1)

    mean_diff = mean_t1 - mean_t2
    var_diff = var_t1 + var_t2

    z_score = mean_diff / sqrt(var_diff)
    probability = norm.cdf(z_score)
   
    return probability

#Historical odds of team1 beating team2 (compare every week = num_weeks * num_weeks comparisons)
def hist_win_prob(t1, t2):
    if t1 == t2: return 0.5
    t1_points = [week.pts for week in t1.stats]
    t2_points = [week.pts for week in t2.stats]
    num_weeks = len(t1.stats)

    t1_wins = 0
    for t1_pts in t1_points:
        for t2_pts in t2_points:
            if t1_pts > t2_pts:
                t1_wins += 1

    historical_odds = t1_wins/(num_weeks*num_weeks)

    return historical_odds

def populate_stats(league, teams, numWeeks, numPlayers):
    for week in range(1, numWeeks + 1):
        matchups = league.scoreboard(week=week)
        scores = []
        for match in matchups:
            home_win = match.home_score > match.away_score
            home_stats = week_stats(match.home_score, match.away_score, home_win)
            away_stats = week_stats(match.away_score, match.home_score, not home_win)
            home_team = teams[match._home_team_id]
            away_team = teams[match._away_team_id]
            home_team.stats.append(home_stats)
            away_team.stats.append(away_stats)
            if home_win:
                home_team.wins += 1
            else:
                away_team.wins += 1
            scores.append((match.home_score, match._home_team_id))
            scores.append((match.away_score, match._away_team_id))
        
        scores.sort()
        for i in range(numPlayers):
            id = scores[i][1]
            teams[id].exp_wins += i # calculate total expected wins over season







