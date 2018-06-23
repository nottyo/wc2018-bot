import os, re, json
from datetime import datetime, date, timedelta
from flask import Flask, request, abort
from googletrans import Translator
from live import live_bp
import requests
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, SpacerComponent, IconComponent, ButtonComponent,
    SeparatorComponent, CarouselContainer
)

app = Flask(__name__)
app.register_blueprint(live_bp)

translator = Translator()
with open('countries.json') as f:
    countries = json.load(f)


channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

wc_api = 'http://api.football-data.org/v1/competitions/467'
wc_api_key = os.getenv('FOOTBALL_API_KEY', None)
wc_api_headers = {'X-Auth-Token': wc_api_key}

# ch = {
#     '207': 'https://image.ibb.co/nP2WKo/True4U96.png',
#     'da0': 'https://image.ibb.co/jAN95T/amarin_no_margin.png',
#     'c05': 'https://image.ibb.co/j2ttX8/ch5.png'
# }

ch = {
    '207': 'https://fn.dmpcdn.com/TrueIDWeb/Sport/True4U.png',
    'da0': 'https://fn.dmpcdn.com/TrueIDWeb/Sport/amarintv-hd.png',
    'c05': 'https://fn.dmpcdn.com/TrueIDWeb/Sport/ch5.png'
}

wc_logo_url = 'https://vectors.pro/wp-content/uploads/2017/10/fifa-world-cup-2018-logo-vector.png'

fifa_api = 'https://api.fifa.com/api/v1/calendar/matches?idCompetition=17&idSeason=254645&count=500&language=en'
fifa_match_event_api = 'https://api.fifa.com/api/v1/timelines/17/254645/{0}/{1}?language=en'
fifa_player_api = 'https://api.fifa.com/api/v1/players/{0}'

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

with open('countries_emoji.json') as f2:
    countries_emoji = json.load(f2)


def get_country_emoji(country_name):
    for country in countries_emoji:
        if country['name'] == country_name:
            return country['emoji']


def normalize_position_name(position_name):
    if ' ' in position_name:
        split = str(position_name).split(' ')
        return (split[0][0] + split[1][0]).upper()
    if '-' in position_name:
        split = str(position_name).split('-')
        return (split[0][0] + split[1][0]).upper()
    if position_name == 'Keeper':
        return 'GK'


def get_fifa_matches():
    response = requests.get(fifa_api)
    return response


def get_fifa_match_events(stage_id, match_id):
    response = requests.get(fifa_match_event_api.format(stage_id, match_id))
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

@app.route('/')
def homepage():
    the_time = datetime.now().strftime("%A, %d %b %Y %l:%M %p")

    return """
    <h1>Hello heroku</h1>
    <p>It is currently {time}.</p>

    <img src="http://loremflickr.com/600/400">
    """.format(time=the_time)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def getFixtures():
    return requests.get('http://sport.trueid.net/worldcup/get_all_match')


def get_fixtures():
    url = wc_api + '/fixtures'
    return requests.get(url, headers=wc_api_headers)


def getTeam(team_name):
    detect = translator.detect(team_name)
    if detect.lang != 'en':
        translate = translator.translate(team_name)
        team_name = translate.text.title()
        for country in countries:
            if team_name in country['nationality']:
                team_name = country['en_short_name']
    
    print("team_name: {}".format(team_name))
    url = wc_api + '/teams'
    response = requests.get(url, headers=wc_api_headers)
    if response.status_code == 200: 
        json = response.json()
        for team in json['teams']:
            if team['name'].lower() == team_name.lower():
                return team['_links']['self']['href']
    return None            


def handle_worldcup_results():
    response = get_fixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            if fixture['status'] == 'FINISHED':
                result = fixture['result']
                home_team_emoji = get_country_emoji(fixture['homeTeamName'])
                away_team_emoji = get_country_emoji(fixture['awayTeamName'])
                text += '[FT] ' + home_team_emoji + ' ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName'] + ' ' + away_team_emoji
                text += '\n' 
        return text    
    return None


def handle_yesterday_results():
    response = get_fixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            yesterday = date.today() - timedelta(1)
            dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ').date()
            if fixture['status'] == 'FINISHED' and yesterday == dt:
                result = fixture['result']
                home_team_emoji = get_country_emoji(fixture['homeTeamName'])
                away_team_emoji = get_country_emoji(fixture['awayTeamName'])
                text += '[FT] ' + home_team_emoji + ' ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName'] + ' ' + away_team_emoji
                text += '\n'
        return text    
    return None


def handle_live_score():
    response = get_fifa_matches()
    text = ''
    bubble = {
        'type': 'bubble',
        'body': {
            'type': 'box',
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "sm",
                    "contents": [
                        {
                            "type": "image",
                            "url": "https://vectors.pro/wp-content/uploads/2017/10/fifa-world-cup-2018-logo-vector.png",
                            "size": "xxs",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": "ผลบอลสด",
                            "weight": "bold",
                            "color": "#ff2f00",
                            "size": "xl"
                        }
                    ]
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "sm",
                    "contents": []
                }
            ]
        }
    }
    if response.status_code == 200:
        matches_results = response.json()['Results']
        for match in matches_results:
            # if match['MatchStatus'] == MATCH_STATUS_PREMATCH:
            bubble_contents = bubble['body']['contents'][2]['contents']
            if match['MatchStatus'] == MATCH_STATUS_LIVE:
                match_id = match['IdMatch']
                match_stage_id = match['IdStage']
                home_team = match['Home']
                home_team_id = str(home_team['IdTeam'])
                home_score = str(home_team['Score'])
                home_name = home_team['TeamName'][0]['Description']
                home_emoji = get_country_emoji(home_name)
                away_team = match['Away']
                away_score = str(away_team['Score'])
                away_name = away_team['TeamName'][0]['Description']
                away_emoji = get_country_emoji(away_name)
                text += home_emoji + home_name + ' ' + home_score + ' - ' + away_score + ' ' + away_name + away_emoji + '\n'
                events = get_fifa_match_events(match_stage_id, match_id)
                print('match_stage: {}, id: {}'.format(match_stage_id, match_id))

                event_contents = []
                event_contents.append(
                    {
                        "type": "text",
                        "text": "{0} {1} {2} - {3} {4} {5}".format(home_emoji, home_name, home_score,
                                                                         away_score, away_name, away_emoji),
                        "color": "#555555",
                        "size": "xs"
                    }
                )
                if events is not None:
                    for event in events:
                        if event['Type'] == EVENT_GOAL or event['Type'] == EVENT_FREE_KICK_GOAL:
                            team_id = event['IdTeam']
                            player_id = event['IdPlayer']
                            match_min = str(event['MatchMinute']).replace("\"", "")
                            player_name = get_fifa_player_name(player_id)
                            if team_id == home_team_id:
                                text += home_emoji + match_min + ' ' + player_name + '\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(home_emoji, match_min, player_name),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )
                            else:
                                text += away_emoji + match_min + ' ' + player_name + '\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(away_emoji, match_min, player_name),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )
                        if event['Type'] == EVENT_PENALTY_GOAL:
                            team_id = event['IdTeam']
                            player_id = event['IdPlayer']
                            match_min = str(event['MatchMinute']).replace("\"", "")
                            player_name = get_fifa_player_name(player_id)
                            if team_id == home_team_id:
                                text += home_emoji + match_min + ' ' + player_name + '(Pen)\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(home_emoji, match_min, player_name + '(Pen)'),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )
                            else:
                                text += away_emoji + match_min + ' ' + player_name + '(Pen)\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(away_emoji, match_min, player_name + '(Pen)'),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )
                        if event['Type'] == EVENT_OWN_GOAL:
                            team_id = event['IdTeam']
                            player_id = event['IdPlayer']
                            match_min = str(event['MatchMinute']).replace("\"", "")
                            player_name = get_fifa_player_name(player_id)
                            if team_id == home_team_id:
                                text += home_emoji + match_min + ' ' + player_name + '(OG)\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(home_emoji, match_min, player_name + '(O.G.)'),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )
                            else:
                                text += away_emoji + match_min + ' ' + player_name + '(OG)\n'
                                event_contents.append(
                                    {
                                        'type': 'text',
                                        'text': '{0} {1}{2}'.format(away_emoji, match_min, player_name + '(O.G.)'),
                                        'color': '#6f7175',
                                        'size': 'xxs'
                                    }
                                )

                bubble_contents.append(
                    {
                        'type': 'box',
                        'layout': 'vertical',
                        'margin': 'sm',
                        'contents': event_contents
                    }
                )
                bubble_contents.append(
                    {
                        'type': 'separator',
                        'margin': 'sm'
                    }
                )
        print(text)
        return BubbleContainer.new_from_json_dict(bubble)
    return None


def handle_fixtures():
    response = getFixtures()
    if response.status_code == 200:
        matches = response.json()
        carousel_dict = {
            'type': 'carousel',
            'contents': []
        }
        data_bubble_dict = {}
        for match in matches:
            dt = datetime.strptime(match['match_start_date'], '%Y-%m-%d %H:%M:%S')
            dt_local = dt - timedelta(hours=7)
            bubble_dict = {
                'type': 'bubble',
                'direction': 'ltr',
                'body': {
                    'type': 'box',
                    'layout': 'vertical',
                    'contents': [
                        {
                            'type': 'box',
                            'layout': 'baseline',
                            'contents': [
                                {
                                    'type': 'icon',
                                    'url': wc_logo_url,
                                    'size': '3xl'
                                },
                                {
                                    'type': 'text',
                                    'weight': 'bold',
                                    'color': '#1DB446',
                                    'size': 'md',
                                    "text": dt_local.date().strftime('%A %d %B %Y')
                                }
                            ]
                        },
                        {
                            'type': 'separator',
                            'margin': 'sm'
                        },
                        {
                            'type': 'box',
                            'layout': 'vertical',
                            'margin': 'sm',
                            'spacing': 'sm',
                            'contents': []
                        }
                    ]
                }
            }
            home_team_name = match['team_home_en']
            home_team_emoji = get_country_emoji(home_team_name)
            away_team_name = match['team_away_en']
            away_team_emoji = get_country_emoji(away_team_name)
            team_match_text = home_team_emoji + match['team_home_th'] + ' vs ' + match['team_away_th'] + away_team_emoji
            if dt_local.date() not in data_bubble_dict:
                data_bubble_dict[dt_local.date()] = bubble_dict
                bubble = bubble_dict
            else:
                bubble = data_bubble_dict[dt_local.date()]

            bubble['body']['contents'][2]['contents'].append(
                {
                    'type': 'box',
                    'layout': 'horizontal',
                    'contents': [
                        {
                            'type': 'text',
                            'text': team_match_text,
                            'size': 'sm',
                            'color': '#555555',
                            'wrap': True,
                            'flex': 9
                        },
                        {
                            'type': 'text',
                            'text': dt.strftime('%H:%M'),
                            'size': 'sm',
                            'color': '#555555',
                            'flex': 0
                        },
                        {
                            'type': 'image',
                            'url': ch[match['channel_code']],
                            'size': 'md',
                            "margin": 'sm'
                        }
                    ]
                }
            )

        for key, value in data_bubble_dict.items():
            if len(carousel_dict['contents']) > 10:
                break
            carousel_dict['contents'].append(value)
        return CarouselContainer.new_from_json_dict(carousel_dict)

    return None


def handle_today_fixtures():
    response = getFixtures()
    found_fixtures = False
    if response.status_code == 200:
        matches = response.json()
        bubble_dict = {
            'type': 'bubble',
            'direction': 'ltr',
            'body': {
                'type': 'box',
                'layout': 'vertical',
                'contents': [
                    {
                        'type': 'box',
                        'layout': 'baseline',
                        'contents': [
                            {
                                'type': 'icon',
                                'url': wc_logo_url,
                                'size': '3xl'
                            },
                            {
                                'type': 'text',
                                'weight': 'bold',
                                'color': '#1DB446',
                                'size': 'xl',
                                "text": "โปรแกรมวันนี้"
                            }
                        ]
                    },
                    {
                        'type': 'text',
                        'text': date.today().strftime('%A %d %B %Y')
                    },
                    {
                        'type': 'separator',
                        'margin': 'sm'
                    },
                    {
                        'type': 'box',
                        'layout': 'vertical',
                        'margin': 'sm',
                        'spacing': 'sm',
                        'contents': []
                    }
                ]
            }
        }
        for match in matches:
            dt = datetime.strptime(match['match_start_date'], '%Y-%m-%d %H:%M:%S')
            dt_local = dt - timedelta(hours=7)
            if dt_local.date() == date.today():
                found_fixtures = True
                home_team_name = match['team_home_en']
                home_team_emoji = get_country_emoji(home_team_name)
                away_team_name = match['team_away_en']
                away_team_emoji = get_country_emoji(away_team_name)
                team_match_text = home_team_emoji + match['team_home_th'] + ' vs ' + match['team_away_th'] + away_team_emoji
                data_contents = bubble_dict['body']['contents'][3]['contents']
                data_contents.append(
                    {
                        'type': 'box',
                        'layout': 'horizontal',
                        'contents': [
                            {
                                'type': 'text',
                                'text': team_match_text,
                                'size': 'xs',
                                'color': '#555555',
                                'wrap': True,
                                'flex': 9
                            },
                            {
                                'type': 'text',
                                'text': dt.strftime('%H:%M'),
                                'size': 'xs',
                                'color': '#555555',
                                'flex': 0
                            },
                            {
                                'type': 'image',
                                'url': ch[match['channel_code']],
                                'size': 'sm',
                                "margin": 'sm'
                            }
                        ]
                    }
                )
        bubble = BubbleContainer.new_from_json_dict(bubble_dict)
        if found_fixtures is True:
            return bubble
        else:
            return "ไม่มีโปรแกรมสำหรับวันนี้ครับ"

    return None


def handle_today_results():
    response = get_fixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ')
            if dt.date() == date.today():
                if fixture['status'] == 'FINISHED':
                    result = fixture['result']
                    home_team_emoji = get_country_emoji(fixture['homeTeamName'])
                    away_team_emoji = get_country_emoji(fixture['awayTeamName'])
                    text += '[FT] ' + home_team_emoji + ' ' + fixture['homeTeamName'] + ' ' + str(
                        result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture[
                                'awayTeamName'] + ' ' + away_team_emoji
                    text += '\n'
        if text != "":
            return text
        else:
            return "ยังไม่มีผลบอลสำหรับวันนี้ครับ"  
    return None


def handle_team_fixture(team_str):
    team_link = getTeam(team_str)
    if team_link is not None:
        response = requests.get(team_link + '/fixtures', headers=wc_api_headers)
        if response.status_code == 200:
            text = ""
            json = response.json()
            for fixture in json['fixtures']:
                if fixture['status'] == 'TIMED':
                    dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=7)
                    text += dt.strftime("%A %d %B %Y") + "\n"
                    text += fixture['homeTeamName'] + ' vs. ' + fixture['awayTeamName'] + ' ' + dt.strftime("%H:%M") + "\n"
                    text += "================\n"    
        if text != "":
            return text
        else:
            return "ทีม {} ไม่มีโปรแกรมเตะแล้วครับ".format(team_str)        
    return "ทีม {} ไม่ได้เข้าร่วมในฟุตบอลโลกนะครับ".format(team_str)


def handle_team_players(team_str):
    team_link = getTeam(team_str)
    if team_link is not None:
        response_team = requests.get(team_link, headers=wc_api_headers)
        team = response_team.json()
        if response_team.status_code == 200:
            response = requests.get(team_link + '/players', headers=wc_api_headers)
            if response.status_code == 200:
                bubble = {
                    'type': 'bubble',
                    'body': {
                        'type': 'box',
                        'layout': 'vertical',
                        'contents': [
                            {
                                'type': 'box',
                                'layout': 'horizontal',
                                'margin': 'sm',
                                'spacing': 'sm',
                                'contents': [
                                    {
                                        'type': 'image',
                                        'url': team['crestUrl'],
                                        'size': 'xxs',
                                        'align': 'start',
                                        'flex': 0
                                    },
                                    {
                                        'type': 'text',
                                        'text': team['name'].upper(),
                                        'weight': 'bold',
                                        'size': 'xxl'
                                    }
                                ]
                            },
                            {
                                'type': 'separator',
                                'margin': 'xs'
                            },
                            {
                                'type': 'box',
                                'layout': 'vertical',
                                'contents': []
                            }
                        ]
                    }
                }
                json = response.json()
                for player in json['players']:
                    if player['jerseyNumber'] is None:
                        player['jerseyNumber'] = 0

                players_sorted = sorted(json['players'], key=lambda key: key['jerseyNumber'])
                player_contents = bubble['body']['contents'][2]['contents']
                for player in players_sorted:
                    player_info = player['name'] + ' (' + normalize_position_name(player['position']) + ')'
                    player_contents.append(
                        {
                            'type': 'box',
                            'layout': 'horizontal',
                            'margin': 'sm',
                            'spacing': 'sm',
                            'contents': [
                                {
                                    'type': 'text',
                                    'text': str(player['jerseyNumber']) + '.',
                                    'size': 'xs',
                                    'color': '#555555',
                                    'flex': 0
                                },
                                {
                                    'type': 'text',
                                    'text': player_info,
                                    'size': 'xs',
                                    'color': '#555555'
                                }
                            ]
                        }
                    )
                return BubbleContainer.new_from_json_dict(bubble)

    return "ทีม {} ไม่ได้เข้าร่วมในฟุตบอลโลกนะครับ".format(team_str)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    result = None
    if 'ผลบอล' in text:
        result = handle_worldcup_results()
    if 'ผลบอลเมื่อคืน' in text:
        result = handle_yesterday_results()
    if 'ผลบอลสด' in text:
        result = handle_live_score()
    if 'ผลบอลวันนี้' in text:
        result = handle_today_results()
    if 'โปรแกรม' in text:
        result = handle_fixtures()
    if 'โปรแกรมวันนี้' in text:
        result = handle_today_fixtures()
    if re.search('โปรแกรมของ([\w\W\s]+)', text):
        m = re.search('โปรแกรมของ([\w\W\s]+)', text)
        result = handle_team_fixture(m.group(1))
    if re.search('(นักเตะทีมชาติ|นักเตะของ)([\w\W\s]+)', text):
        m = re.search('(นักเตะทีมชาติ|นักเตะของ)([\w\W\s]+)', text)
        result = handle_team_players(m.group(2))
    if result is not None:
        if isinstance(result, BubbleContainer) or isinstance(result, CarouselContainer):
            message = FlexSendMessage(alt_text="รบกวนดูข้อความบนมือถือของท่านนะครับ", contents=result)
            line_bot_api.reply_message(
                event.reply_token,
                message
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result))
    

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
