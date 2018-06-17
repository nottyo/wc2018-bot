import os, re, json
from datetime import datetime, date, timedelta
from flask import Flask, request, abort
from googletrans import Translator
import requests
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)
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
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            if fixture['status'] == 'FINISHED':
                result = fixture['result']
                text += '[FT] ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName']
                text += '\n' 
        return text    
    return None

def handle_yesterday_results():
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            yesterday = date.today() - timedelta(1)
            dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ').date()
            if fixture['status'] == 'FINISHED' and yesterday == dt:
                result = fixture['result']
                text += '[FT] ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName']
                text += '\n' 
        return text    
    return None

def handle_live_score():
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            if fixture['status'] == 'IN_PLAY':
                result = fixture['result']
                text += '[LIVE] ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName']
                text += '\n' 
        if text != "":
            return text
        else:
            return "ไม่มีบอลเตะตอนนี้นะครับ"
    return None

def handle_fixtures(): 
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        data = {}
        for fixture in json['fixtures']:
            if fixture['status'] == 'TIMED':
                dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ')
                play_time = dt + timedelta(hours=7)
                matches_text = fixture['homeTeamName'] + ' vs. ' + fixture['awayTeamName'] + " " + play_time.strftime("%H:%M")
                if dt.date() not in data:
                    data[dt.date()] = [matches_text]
                else:
                    data[dt.date()].append(matches_text)
        for key, values in data.items():
            text += key.strftime("%A %d %B %Y") + "\n"
            for value in values:
                text += value + "\n"
            text += "=========================\n\n"
        return text        
    return None    

def handle_today_fixtures(): 
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        data = {}
        for fixture in json['fixtures']:
            if fixture['status'] == 'TIMED':
                dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ')
                if dt.date() == date.today():
                    play_time = dt + timedelta(hours=7)
                    matches_text = fixture['homeTeamName'] + ' vs. ' + fixture['awayTeamName'] + " " + play_time.strftime("%H:%M")
                    if dt.date() not in data:
                        data[dt.date()] = [matches_text]
                    else:
                        data[dt.date()].append(matches_text)
                
        for key, values in data.items():
            text += key.strftime("%A %d %B %Y") + "\n"
            for value in values:
                text += value + "\n"
        if text != "":
            return text
        else:
            return "ไม่มีโปรแกรมเตะสำหรับวันนี้ครับ พิมพ์ \"โปรแกรม\" เพื่อดูโปรแกรมการแข่งขันในวันอื่นๆ"      
    return None    

def handle_today_results():
    response = getFixtures()
    if response.status_code == 200:
        json = response.json()
        text = ""
        for fixture in json['fixtures']:
            dt=datetime.strptime(fixture['date'],'%Y-%m-%dT%H:%M:%SZ')
            if dt.date() == date.today():
                if fixture['status'] == 'FINISHED':
                    result = fixture['result']
                    text += '[FT] ' + fixture['homeTeamName'] + ' ' + str(result['goalsHomeTeam']) + ' - ' + str(result['goalsAwayTeam']) + ' ' + fixture['awayTeamName']
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
        response = requests.get(team_link + '/players', headers=wc_api_headers)
        if response.status_code == 200:
            text = ""
            json = response.json()
            for player in json['players']:
                text += player['name'] + '   | ' + player['position'] + ' | เบอร์ ' + str(player['jerseyNumber']) + "\n" 
            return text
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
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result))
    

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
