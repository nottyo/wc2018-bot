import os
from flask import Flask, request, abort
import requests
from datetime import datetime, date, timedelta
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
    response = requests.get(url, headers=wc_api_headers)
    return response

def handleWorldCupResult():
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

def handleYesterdayWCResult():
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

def handleLiveScore():
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

def handleFixtures(): 
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

def handleTodayFixtures(): 
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

def handleTodayResult():
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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    result = None
    if 'ผลบอล' in text:
        result = handleWorldCupResult()
    if 'ผลบอลเมื่อคืน' in text:
        result = handleYesterdayWCResult()
    if 'ผลบอลตอนนี้' in text:
        result = handleLiveScore()
    if 'ผลบอลวันนี้' in text:
        result = handleTodayResult()
    if 'โปรแกรม' in text:
        result = handleFixtures() 
    if 'โปรแกรมวันนี้' in text:
        result = handleTodayFixtures()
    if result is not None:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result))
    

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
