# leage_analysis/models.py

import numpy as np

#Defines a team within ESPN Fantasy
class Team:
    def __init__(self, name, id):
        self.name = name # name
        self.id = id # ID
        self.stats = [] # weekly stats list
        self.wins = 0 # total wins
        self.exp_wins = 0 # expected wins

    def print_basic(self):
        print(f"{self.name}: ID {self.id}.")
    # Print's team's Name, ID, Win total, Win Percentage, and expected Win Percentage
    def print_team_info(self, num_weeks, num_players): 
        print(
            f"Name: {self.name}. ID: {self.id}. Wins: {self.wins} "
            f"WP: {self.calc_wp(num_weeks)}% expected WP: {self.calc_exp_wp(num_weeks, num_players)}%\nWeek Stats:"
        )
    
    def calc_stats(self): #returns tuple of mean and standard devation of score over weeks
        pts = [week.pts for week in self.stats] # list of points scored each week
        mean = np.mean(pts) # mean weekly score
        std = np.std(pts) # standard deviation of score 
        return round(mean, 2), round(std, 2)
        
    # calculates total points in a year
    def total_points(self): 
        return round(sum(st.pts for st in self.stats), 2) 
    
    # calculates expected win percentage over season
    def calc_exp_wp(self, num_weeks, num_players):
        return round(100 * self.exp_wins / ((num_players - 1) * num_weeks), 2)
    
    # calculates actual win percentage over season
    def calc_wp(self, num_weeks):
        return round(100 * self.wins / num_weeks, 2)

# basic class to store a team's weekly stats; points, points against, and W/L (boolean)
class week_stats:
    def __init__(self, pts, pa, win): # Initializer for week stats class
        self.pts = pts  # Points scored by the team in a given week
        self.pa = pa    # Points allowed (opponent's points)
        self.win = win  # Boolean indicating if the team won the matchup
    
