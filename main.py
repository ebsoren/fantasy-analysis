# main.py

from league_analysis.retrieval import initialize_league
from league_analysis.models import Team, week_stats
from league_analysis.processing import calc_win_prob, hist_win_prob
from league_analysis.plotting import plot_quadrant, plot_actual_vs_exp, plot_linreg, plot_pdfs, plot_cdfs
from espnsecrets import LEAGUE_ID, YEAR, NUM_WEEKS, NUM_PLAYERS



#Object which stores team info from given league
league = initialize_league(LEAGUE_ID, YEAR)

#dictionary to store teams by ID
teams = {}

#Fill dictionary with teams: team name, id, and user
for team in league.teams:
    teams[team.team_id] = Team(team.team_name, team.team_id)


# Process each week
for week in range(1, NUM_WEEKS + 1):
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
    for i in range(NUM_PLAYERS):
        team_id = scores[i][1]
        teams[team_id].exp_wins += i

    team_names = [team.name for _, team in teams.items()]
    act_wp = [team.calc_wp(NUM_WEEKS) for _, team in teams.items()]
    exp_wp = [team.calc_exp_wp(NUM_WEEKS, NUM_PLAYERS) for _, team in teams.items()]
    win_diff = [a - t for a, t in zip(act_wp, exp_wp)]
    x_mid = 0 
    y_mid = sum(exp_wp) / len(exp_wp)

# choice of plot
def main_menu():
    print("Fantasy League Analysis - Main Menu")
    print("1. Print Team Stats")
    print("2. Plot Quadrant Plot")
    print("3. Plot Comparison Plot")
    print("4. Plot Regression Plot")
    print("5. Plot Teams' PDFs")
    print("6. Plot Teams' CDFs")
    print("7. Calculate Statistical Win Probability Between 2 Teams")
    print("8. Calculate Historical Win Probability Between 2 Teams")
    print("9. Exit")

    choice = safe_menu("Enter the number corresponding to your choice: ")
    return choice

def print_team_stats():
    for _, team in teams_in.items():
        mean, std = team.calc_stats()
        print(
            f"{team.name}'s stats: Mean: {mean}. STD: {std}. Points: {team.total_points()}"
        )
def safe_menu(prompt):
    while True:
        user_input = input(prompt).strip()
        if not user_input:
            print("Input cannot be empty.")
            continue
        if not user_input.isdigit():
            print("Invalid input. Please enter a numeric value.")
            continue
        choice = int(user_input)
        if choice not in range(1, 10):
            print("Choose a valid menu option")
            continue
        return choice

def safe_prompt(prompt, teams):
    while True:
        user_input = input(prompt).strip()
        if not user_input:
            print("Input cannot be empty. Please enter a valid team ID.")
            continue
        if not user_input.isdigit():
            print("Invalid input. Please enter a numeric team ID.")
            continue
        team_id = int(user_input)
        if team_id not in teams:
            print(f"Team ID {team_id} does not exist. Please enter a valid team ID.")
            continue
        return teams[team_id]

# Main Loop
if __name__ == "__main__":
    Outer = True
    while Outer:
        choice = main_menu()
        teams_in = {}
        if(choice != 4 and choice < 7):
            print("Here's a list of teams:")
            for team_id, team in teams.items():
                print(f"ID {team_id}: ", end="")
                team.print_basic()

            print("Select teams by ID (comma-separated), or press enter to select all:")
            user_input = input().strip()

            selected_ids = set()

            if user_input == "":      
                teams_in = teams.copy()
            else:# Split the input by commas and process each entry
                input_parts = user_input.split(',')
                for part in input_parts:
                    part = part.strip()
                    if part.isdigit():
                        team_id = int(part)
                        if team_id in teams:
                            selected_ids.add(team_id)
                        else:
                            print(f"Warning: Team with ID {team_id} does not exist.")
                    else:
                        print(f"Warning: '{part}' is not a valid integer.")

                if not selected_ids:
                    print("No valid team IDs were selected. Selecting all teams by default.")
                    teams_in = teams.copy()
                else:
                    teams_in = {team_id: teams[team_id] for team_id in selected_ids}

        if choice == 1:
            print_team_stats()
        elif choice == 2:
            plot_quadrant(teams_in, NUM_WEEKS, NUM_PLAYERS)
        elif choice == 3:
            plot_actual_vs_exp(teams_in, NUM_WEEKS, NUM_PLAYERS)
        elif choice == 4:
            plot_linreg(teams, NUM_WEEKS)
        elif choice == 5:
            plot_pdfs(teams_in)
        elif choice == 6:
            plot_cdfs(teams_in)
        elif (choice == 7 or choice == 8):
            print("Here's a list of teams:")
            for team_id, team in teams.items():
                print(f"ID {team_id}: ", end="")
                team.print_basic()
            t1 = safe_prompt("Enter first team ID: ",teams)    
            t2 = safe_prompt("Enter second team ID: ",teams)  
                   
            prob = round(100*calc_win_prob(t1, t2), 2) if choice == 7 else round(100*hist_win_prob(t1, t2), 2)
            opt = "historical likelihood" if choice == 8 else "statistical probability"
            print(
                f"The {opt} of {t1.name} beating {t2.name} in any given week is {prob}%."
            )
        elif choice == 9:
            print("Exiting Fantasy League Analysis.")
            break
        else:
            print("Invalid choice. Please try again.")
        while True:
            choice = input("continue? (y/n) ")
            if choice == 'n': 
                Outer = False
                print("Exiting...")
                break
            if choice != 'y': 
                print("type 'y' or 'n' ")
                continue
            else: 
                break


