import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from scipy.stats import linregress

# Plots a team's weekly point distribution as a histogram with a KDE overlay.
def plot_distribution(team, start, end, binsize):

    points = [week.pts for week in team.stats]
    mean = np.mean(points)
    median = np.median(points)

    bins = np.arange(start, end + binsize, binsize)  
    plt.figure(figsize=(10, 5))

    sns.histplot(
        points,
        bins=bins,       
        kde=True,        
        color='blue',
        alpha=0.7
    )

    plt.axvline(x=mean, color='red', linestyle='--', linewidth=2, 
                label=f'Mean = {mean:.2f}')
    plt.axvline(x=median, color='green', linestyle='--', linewidth=2, 
                label=f'Median = {median:.2f}')
  
    plt.title(f"{team.name}'s Weekly Point Distribution", fontsize=14)
    plt.xlabel('Weekly Points', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.legend()
    plt.tight_layout()
    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig(f"{team.name}_dist")
    plt.show()
   
# plots the distribution of all teams given, option to include mean/median
def plot_all_teams_dist(teams, start, end, binsize, incl_mean_med):
    # build DataFrame
    data = []
    for _, team in teams.items():
        for week_stat in team.stats:
            data.append({'team': team.name, 'points': week_stat.pts})
    
    df = pd.DataFrame(data, columns=['team', 'points'])
    if df.empty:
        print("No weekly points recorded.")
        return

    mean = df['points'].mean()
    median = df['points'].median()

    ax = plt.subplots(figsize=(20, 5))


  
    colors = sns.color_palette("Set3", len(teams))
    color_map = dict(zip(teams, colors))

    sns.histplot(
        data=df,
        x='points',
        hue='team',
        multiple='stack',
        binrange=(50, 200),
        binwidth=5,
        edgecolor='black',
        alpha=0.9,
        palette=color_map,
        ax=ax
    )

    # plot mean and median
    if(incl_mean_med):
        ax.axvline(mean, color='red', linewidth=2, label=f"Mean = {mean:.2f}")
        ax.axvline(median, color='green', linewidth=2, label=f"Median = {median:.2f}")

    ax.set_xlim(start, end)
    ax.set_xticks(np.arange(start, end + binsize, binsize))
    ax.set_xlabel("Weekly Points", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("Score Count", fontsize=14)

    # KDE Axis
    ax2 = ax.twinx()
    ax2.set_ylabel("Probability Density", fontsize=12)

    for team_name in teams:
        subset = df.loc[df['team'] == team_name, 'points']
        sns.kdeplot(
            data=subset,
            color=color_map[team_name],
            fill=False,
            linewidth=2,
            ax=ax2,
            label=f"{team_name} KDE" 
        )

    # Custom legend:
    # Patches for histogram
    patches = [mpatches.Patch(color=color_map[t], label=t) for t in teams]

    # Lines for KDE
    kde_lines = [
        Line2D([0], [0], color=color_map[t], linewidth=2, label=f"{t} KDE")
        for t in teams
    ]
    all_handles = patches + kde_lines
    ax.legend(handles=all_handles, title="Legend", loc='best')

    plt.tight_layout()

    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig("teams_histogram")
    plt.show()

# plots only team's PDF with KDE (No histogram)
def plot_pdfs(teams):
    # Aggregate data
    data = []
    for _, team in teams.items():
        for week_stat in team.stats:
            data.append({'team': team.name, 'points': week_stat.pts})

    df = pd.DataFrame(data, columns=['team', 'points'])

    if df.empty:
        print("No weekly points recorded for the specified teams.")
        return

    # Initialize the plot
    fig, ax = plt.subplots(figsize=(10, 5))

    # Generate a color palette
    colors = sns.color_palette("Set3", len(teams))
    
    # Create a color map with team names as keys
    color_map = {team.name: color for team, color in zip(teams.values(), colors)}

    # Track if any plots are actually added
    plots_added = False

    for team in teams.values():
        team_name = team.name
        subset = df.loc[df['team'] == team_name, 'points']
        
        if subset.empty:
            print(f"No data for team '{team_name}'. Skipping.")
            continue

        plots_added = True  # At least one plot will be added

        sns.kdeplot(
            data=subset,
            color=color_map[team_name],
            fill=True,       
            linewidth=2,
            label=team_name,  
            ax=ax
        )

    if not plots_added:
        print("No valid data to plot after filtering. Exiting function.")
        return

    # Configure plot aesthetics
    ax.set_title("PDF of Selected Teams' Weekly Scores", fontsize=14)
    ax.set_xlabel("Weekly Points", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.legend(title="Team")
    plt.tight_layout()

    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig("teams_pdf_smooth.png")
    plt.show()


def plot_cdfs(teams):
    # Aggregate data
    data = []
    for team_id, team in teams.items():
        for week_stat in team.stats:
            data.append({'team': team.name, 'points': week_stat.pts})

    df = pd.DataFrame(data, columns=['team', 'points'])

    if df.empty:
        print("No weekly points recorded for the specified teams.")
        return

    # Initialize the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Generate a color palette
    colors = sns.color_palette("Set3", len(teams))
    
    # Correctly map each team to a color using zip
    color_map = {team.name: color for team, color in zip(teams.values(), colors)}

    # Track if any plots are actually added
    plots_added = False

    for team in teams.values():
        team_name = team.name
        subset = df.loc[df['team'] == team_name, 'points']
        
        if subset.empty:
            print(f"No data for team '{team_name}'. Skipping.")
            continue

        plots_added = True  # At least one plot will be added

        sns.ecdfplot(
            data=subset,
            color=color_map[team_name],
            linestyle='-',    # Solid line for CDF
            linewidth=2,
            label=team_name,
            ax=ax
        )

    if not plots_added:
        print("No valid data to plot after filtering. Exiting function.")
        return

    # Configure plot aesthetics
    ax.set_title("CDF of Selected Teams' Weekly Scores", fontsize=16)
    ax.set_xlabel("Weekly Points", fontsize=14)
    ax.set_ylabel("Cumulative Probability", fontsize=14)
    ax.legend(title="Team", fontsize=12, title_fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig("teams_cdf.png")
    plt.show()

def plot_quadrant(teams, NUM_WEEKS, NUM_PLAYERS):
    
    team_names = [team.name for _, team in teams.items()]
    act_wp = [team.calc_wp(NUM_WEEKS) for _, team in teams.items()]
    exp_wp = [team.calc_exp_wp(NUM_WEEKS, NUM_PLAYERS) for _, team in teams.items()]
    win_diff = [a - t for a, t in zip(act_wp, exp_wp)]
    x_mid = 0 
    #y_mid = sum(exp_wp) / len(exp_wp)
    y_mid = 50
    
    plt.figure(figsize=(8, 8))
    plt.scatter(win_diff, exp_wp, color='blue', alpha=0.7, edgecolors='black')

    # Add labels for each point in the quadrant plot
    for i, name in enumerate(team_names):
        plt.text(
            win_diff[i] + 1,    # small offset to the right
            exp_wp[i] + 1,  # small offset above
            name, fontsize=7, ha='left', va='bottom', zorder=4
        )

    # Add quadrant lines
    plt.axhline(y=y_mid, color='black', linestyle='--', linewidth=1)
    plt.axvline(x=x_mid, color='black', linestyle='--', linewidth=1)

    # Annotate quadrants
    plt.text(x_mid + 20, y_mid + 20, "Good and Lucky", fontsize=10, color="black", ha='left')
    plt.text(x_mid - 20, y_mid + 20, "Good and Unlucky", fontsize=10, color="black", ha='right')
    plt.text(x_mid - 20, y_mid - 20, "Bad and Unlucky", fontsize=10, color="black", ha='right')
    plt.text(x_mid + 20, y_mid - 20, "Bad and Lucky", fontsize=10, color="black", ha='left')

    # Adjust axis limits
    plt.xlim(-50, 50)  # Adjust as needed
    plt.ylim(0, 100)

    plt.title("Win % vs. expected Win % Difference", fontsize=14)
    plt.xlabel("<-------Luck------->", fontsize=12)
    plt.ylabel("<-------Strength------->", fontsize=12)
    plt.tight_layout()
    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig("quadrant_plot.png", dpi=300, bbox_inches='tight')
    plt.show()
   

def plot_actual_vs_exp(teams, NUM_WEEKS, NUM_PLAYERS):
    
    team_names_unsorted = [team.name for _, team in teams.items()]
    act_wp_unsorted = [team.calc_wp(NUM_WEEKS) for _, team in teams.items()]
    exp_wp_unsorted = [team.calc_exp_wp(NUM_WEEKS, NUM_PLAYERS) for _, team in teams.items()]
    combined = zip(act_wp_unsorted, exp_wp_unsorted, team_names_unsorted)
    sort_comb = sorted(combined)
    act_wp, exp_wp, team_names = zip(*sort_comb)
    plt.figure()

    # Plot expected and actual win percentages as separate scatter points
    plt.scatter(range(len(team_names)), exp_wp, color='black', label='expected Win %')
    plt.scatter(range(len(team_names)), act_wp, color='gold', label='Actual Win %', marker='*', s=200)

    # Connect each team's expected and actual points with a dotted line and annotate with rank difference
    for i, name in enumerate(team_names):
        plt.plot(
            [i, i],
            [exp_wp[i], act_wp[i]],
            linestyle='--',
            color='red' if exp_wp[i] > act_wp[i] else 'green',
            
            
        )
        label_y = max(exp_wp[i], act_wp[i]) + 1
        plt.text(i, label_y, f"{name}", fontsize=7, ha='center', va='bottom',  color='red' if exp_wp[i] > act_wp[i] else 'green')

    plt.ylim(0, 120)
    plt.title("Comparison of Actual vs. expected Win %", fontsize=14)
    plt.xticks([])  # Remove x-axis ticks since we used team indices
    plt.xlabel("Teams (sorted by Actual Win %)")
    plt.ylabel("Win Percentage")
    plt.legend()
    plt.tight_layout()
    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
        plt.savefig("comparison_plot.png", dpi=300, bbox_inches='tight')
    plt.show()
   


def plot_linreg(teams, NUM_WEEKS):
    plt.figure(figsize=(8, 8))

    # Gather data: total_points_scored, expected_win_percentage
    x_points = []
    y_expected_win = []
    labels = []

    for _, team in teams.items():
        x_points.append(team.total_points())
        y_expected_win.append(team.calc_exp_wp(NUM_WEEKS, len(teams)))
        labels.append(team.name)

    # Convert to numpy arrays
    x_array = np.array(x_points, dtype=float)
    y_array = np.array(y_expected_win, dtype=float)

    # Perform linear regression using scipy.stats
    slope, intercept, r_value, p_value, _ = linregress(x_array, y_array)

    # Compute R^2
    r_squared = r_value**2

    # Generate points for best-fit line
    x_line = np.linspace(min(x_array), max(x_array), 100)
    y_line = slope * x_line + intercept

    # Plot scatter of actual data
    plt.scatter(x_array, y_array, color='blue', alpha=0.7, edgecolors='black', label='Teams')

    # Plot the regression line
    plt.plot(x_line, y_line, color='red', linestyle='-', linewidth=2, label='Best-Fit Line')

    # Prepare text objects for adjustText
    texts = []

    for i, name in enumerate(labels):
        # Place text initially near the point
        txt = plt.text(
            x_array[i],          # x-coordinate (we'll let adjustText move it if needed)
            y_array[i],          # y-coordinate
            name,
            fontsize=7,
            ha='left',
            va='bottom'
        )
        texts.append(txt)



    # Display statistical info (R^2, p-value, slope, intercept) on the plot
    stat_text = (
        f"$R^2 = {r_squared:.3f}$\n"
        f"p-value = {p_value:.3g}\n"
        f"slope = {slope:.3f}\n"
        f"intercept = {intercept:.3f}"
    )

    plt.text(
        0.95, 0.05, stat_text,
        fontsize=10,
        ha='right',
        va='bottom',
        transform=plt.gca().transAxes,
        bbox=dict(facecolor='white', alpha=0.7)
    )

    plt.title("expected Win % vs. Total Points Scored", fontsize=14)
    plt.xlabel("Total Points Scored", fontsize=12)
    plt.ylabel("expected Win Percentage", fontsize=12)
    plt.legend()
    plt.tight_layout()
    choice = input("do you want to save locally?? If so, type 'save'. If not, type anything (or nothing).")
    if choice == "save":
          plt.savefig("regression_exp_wp_vs_points.png", dpi=300, bbox_inches='tight')
    plt.show()
   





