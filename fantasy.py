from espn_api.football import League
import espnsecrets
import matplotlib.pyplot as plt


# Initialize the league object
league = League(league_id=27029413, year=2024, swid=espnsecrets.swid, espn_s2=espnsecrets.espn_s2)

# Data collection
win_scores = [[] for _ in range(15)]  
lose_scores = [[] for _ in range(15)] 
win_scores_flat = []
lose_scores_flat = []
weeks = []
week_labels = []



for week in range(1, 15):
    weeks.append(week)
    matchups = league.scoreboard(week=week)
    for matchup in matchups:
        win_scores[week].append(max(matchup.away_score, matchup.home_score))
        lose_scores[week].append(min(matchup.away_score, matchup.home_score))
        win_scores_flat.append(max(matchup.away_score, matchup.home_score))
        lose_scores_flat.append(min(matchup.away_score, matchup.home_score))
        week_labels.append(week)
lose_avgs = []
win_avgs = []
avg_diffs = []

for week in range(1, 15):
    win_avg = sum(win_scores[week]) / 6
    lose_avg = sum(lose_scores[week]) / 6
    win_avgs.append(win_avg)
    lose_avgs.append(lose_avg)
    avg_diffs.append((win_avg - lose_avg))




    
fig, axs = plt.subplots(2, 2, figsize=(10, 10))

axs[1][0].plot(weeks, win_avgs, color='green', label='Winner Scores Average')
axs[1][0].plot(weeks, lose_avgs, color='red', label='Loser Scores Average')

axs[1][0].set_title("Avg W/L Scores/Wk")
axs[1][0].set_xlabel("Week")
axs[1][0].set_ylabel("Scores")
axs[1][0].legend()
axs[1][0].grid(True)

axs[0][1].plot(weeks, avg_diffs, color='black', label='Avg Difference In Each Matchup')
axs[0][1].set_title("Avg Difference in Winner/Loser Avg Scores")
axs[0][1].set_xlabel("Week")
axs[0][1].set_ylabel("Difference")
axs[0][1].legend()
axs[0][1].grid(True)



axs[0][0].scatter(week_labels, lose_scores_flat, color='red', label='Loser Scores')
axs[0][0].scatter(week_labels, win_scores_flat, color='green', label='Winner Scores')
axs[0][0].set_title("Winner/Loser Scores")
axs[0][0].set_xlabel("Week")
axs[0][0].set_ylabel("Scores")
axs[0][0].legend()
axs[0][0].grid(True)
axs[0][0].set_axisbelow(True)
axs[0][0].set_xticks(range(1, 15))



plt.tight_layout() 
plt.show()


