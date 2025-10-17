# league_analysis/data_retrieval.py

from espn_api.football import League
import espnsecrets

def initialize_league(league_id, year):

    # Initializes and returns the League object using ESPN API credentials.

    league = League(
        league_id=league_id,
        year=year,
        swid=espnsecrets.swid,
        espn_s2=espnsecrets.espn_s2
    )
    return league
