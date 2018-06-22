import requests
import json
from flask import Blueprint
# FIFA API
# 2018 World Cup
ID_COMPETITION = 17
ID_SEASON = 254645
# # Match Statuses
MATCH_STATUS_FINISHED = 0
MATCH_STATUS_NOT_STARTED = 1
MATCH_STATUS_LIVE = 3
MATCH_STATUS_PREMATCH = 12 # Maybe?
# Event Types
EVENT_GOAL = 0
EVENT_YELLOW_CARD = 2
EVENT_SECOND_YELLOW_CARD_RED = 3 # Maybe?
EVENT_STRAIGHT_RED = 4 # Maybe?
EVENT_PERIOD_START = 7
EVENT_PERIOD_END = 8
EVENT_OWN_GOAL = 34
EVENT_FREE_KICK_GOAL = 39
EVENT_PENALTY_GOAL = 41
EVENT_PENALTY_SAVED = 60
EVENT_PENALTY_MISSED = 65
EVENT_FOUL_PENALTY = 72
# Periods
PERIOD_1ST_HALF = 3
PERIOD_2ND_HALF = 5
# all match url 
all_matches_url = 'https://api.fifa.com/api/v1/calendar/matches?idCompetition={0}&idSeason={1}&count=500&language=en'.format(ID_COMPETITION, ID_SEASON)
# match event url
# match_event_url = 'https://api.fifa.com/api/v1/timelines/{0}/{1}/{2}/{3}?language=en'.format(ID_COMPETITION, ID_SEASON, ID_STAGE, ID_MATCH)
#https://api.fifa.com/api/v1/timelines/17/254645/275073/300331545?language=en

live_bp = Blueprint('live_bp', __name__)

with open('countries_emoji.json') as f2:
    countries_emoji = json.load(f2)

def get_country_emoji(country_name):
    for country in countries_emoji:
        if country['name'] == country_name:
            return country['emoji']

@live_bp.route('/live')
def get_live_score():
    all_matches_resp = requests.get(all_matches_url)
    if all_matches_resp.status_code == 200:
        matches = all_matches_resp.json()['Results']
        text = ''
        for match in matches:
            # if match['MatchStatus'] == MATCH_STATUS_LIVE:
            if match['MatchStatus'] == MATCH_STATUS_FINISHED:
                home_team_name = match['Home']['TeamName'][0]['Description']
                home_team_score = str(match['Home']['Score'])
                home_team_flag = get_country_emoji(home_team_name)
                away_team_name = match['Away']['TeamName'][0]['Description']
                away_team_score = str(match['Away']['Score'])
                away_team_flag = get_country_emoji(away_team_name)
                text += '[LIVE] {0} {1} {2} - {3} {4} {5}\n'.format(home_team_name, home_team_flag, home_team_score, 
                    away_team_score, away_team_name, away_team_flag)
                id_stage = match['IdStage']
                id_match = match['IdMatch']
                print('id_stage: {0}, id_match: {1}'.format(id_stage, id_match))
    print(text)
    return text    

