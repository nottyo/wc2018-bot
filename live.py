import json, os

import requests
import time, redis
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from flask import Blueprint
from linebot import (
    LineBotApi
)

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
match_event_url = 'https://api.fifa.com/api/v1/timelines/{0}/{1}/{2}/{3}?language=en'
fifa_player_api = 'https://api.fifa.com/api/v1/players/{0}'

channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

line_bot_api = LineBotApi(channel_access_token)

live_data = []
live_bp = Blueprint('live_bp', __name__)

db = redis.from_url(os.getenv('REDISCLOUD_URL'))

with open('countries_emoji.json') as f2:
    countries_emoji = json.load(f2)


def get_country_emoji(country_name):
    for country in countries_emoji:
        if country['name'] == country_name:
            return country['emoji']


def get_events_data(stage_id, match_id):
    url = match_event_url.format(ID_COMPETITION, ID_SEASON, stage_id, match_id)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['Event']
    return None


def get_fifa_player_name(player_id):
    response = requests.get(fifa_player_api.format(player_id))
    if response.status_code == 200:
        json = response.json()
        name = json['Name'][0]['Description']
        split = str(name).split(' ')
        name = split[0][0] + '.' + split[1].title()
        return name
    return None


def get_live_data_by_match_id(match_id):
    for live in live_data:
        if live['match_id'] == match_id:
            return live


def get_live_score():
    all_matches_resp = requests.get(all_matches_url)
    if all_matches_resp.status_code == 200:
        matches = all_matches_resp.json()['Results']
        text = ''
        current_timestamp = time.time()
        for match in matches:
            # if match['MatchStatus'] == MATCH_STATUS_LIVE:
            if match['IdMatch'] == '300331501':
                match_id = match['IdMatch']
                home_team_name = match['Home']['TeamName'][0]['Description']
                home_team_score = str(match['Home']['Score'])
                home_team_flag = get_country_emoji(home_team_name)
                home_team_id = str(match['Home']['IdTeam'])
                away_team_name = match['Away']['TeamName'][0]['Description']
                away_team_score = str(match['Away']['Score'])
                away_team_flag = get_country_emoji(away_team_name)
                away_team_id = str(match['Away']['IdTeam'])
                text += '[LIVE] {0}{1} {2} - {3} {4}{5}\n'.format(home_team_flag, home_team_name, home_team_score,
                    away_team_score, away_team_name, away_team_flag)
                id_stage = match['IdStage']
                id_match = match['IdMatch']
                print('id_stage: {0}, id_match: {1}'.format(id_stage, id_match))
                events = get_events_data(id_stage, id_match)

                for event in events:
                    event_id = event['EventId']
                    if event['Type'] == EVENT_GOAL or event['Type'] == EVENT_FREE_KICK_GOAL:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} ⚽ GOAL! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} ⚽ GOAL! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_OWN_GOAL:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} ⚽ O.G! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} ⚽ O.G! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_PENALTY_GOAL:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} {1}{2} (Pen)\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} {1}{2} (Pen)\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_FOUL_PENALTY:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} Penalty! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} Penalty! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_PENALTY_MISSED:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} Penalty Missed! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} Penalty Missed! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_YELLOW_CARD:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} Yellow Card! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} Yellow Card! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    if event['Type'] is EVENT_STRAIGHT_RED or event['Type'] is EVENT_SECOND_YELLOW_CARD_RED:
                        event_team_id = event['IdTeam']
                        match_min = event['MatchMinute']
                        if event_team_id == home_team_id:
                            text += '{0} Red Card! {1}{2}\n'.format(match_min, home_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                        else:
                            text += '{0} Red Card! {1}{2}\n'.format(match_min, away_team_flag,
                                                                get_fifa_player_name(event['IdPlayer']))
                    live['event_id'].append(event_id)
                    # push message
                    try:
                        line_bot_api.push_message('U826fdeef198fe30a18c98b8039dd8253', TextSendMessage(text))
                    except LineBotApiError as e:
                        print(str(e))
    return "done"

