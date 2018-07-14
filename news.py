# coding=utf-8
import requests
import uuid
import re

from linebot.models import (
    BubbleContainer
)

base_url = 'http://www.soccersuck.com/api'
uri_action_base = 'http://www.soccersuck.com/boards/topic'


class News:

    def _get_access_token(self):
        url = base_url + '/accessToken'
        payload = {
            'secret_key': 'devtab',
            'device_name': 'Xiaomi Mi Pad',
            'device_version': '4.4.4',
            'device_os': 'android',
            'unique_id': str(uuid.uuid4()).split('-')[0]
        }
        response = requests.post(url, data=payload)
        return response.json()['data']['access_token']

    def get_latest_news(self, limit):
        access_token = self._get_access_token()
        url = base_url + '/latestnews'
        payload = {
            'limit': limit*2,
            'offset': '120',
            'access_token': access_token
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            json = response.json()
            data_list = json['data']['data']
            if len(data_list) == 0:
                return "Can't Find Data"
            count = 0
            add_bubble_header = False
            for data in data_list:
                if count == limit:
                    break
                if re.search('^https', data['image']):
                    if add_bubble_header is False:
                        bubble = {
                            'type': 'bubble',
                            "header": {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "margin": "sm",
                                        "contents": [
                                            {
                                                "type": "text",
                                                "text": "LATEST FOOTBALL NEWS",
                                                "weight": "bold",
                                                "color": "#27aa00",
                                                "size": "md"
                                            },
                                            {
                                                "type": "text",
                                                "text": data['title'],
                                                "size": "sm",
                                                "wrap": True
                                            }
                                        ]
                                    }
                                ]
                            },
                            "hero": {
                                "type": "image",
                                "url": data['image'],
                                "aspectMode": "cover",
                                "aspectRatio": "20:13",
                                "size": "full",
                                "action": {
                                    "type": "uri",
                                    "uri": uri_action_base + '/' + data["id"]
                                }
                            },
                            "body": {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "spacing": "md",
                                        "contents": []
                                    }
                                ]
                            }
                        }
                        add_bubble_header = True
                    else:
                        # add image, title
                        bubble["body"]["contents"][0]["contents"].append(
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "image",
                                        "url": data["image"],
                                        "aspectMode": "cover",
                                        "aspectRatio": "4:3",
                                        "margin": "md",
                                        "size": "sm",
                                        "gravity": "top",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": data["title"],
                                        "gravity": "top",
                                        "size": "xs",
                                        "wrap": True,
                                        "flex": 2,
                                        "action": {
                                            "type": "uri",
                                            "uri": uri_action_base + '/' + data["id"]
                                        }
                                    }
                                ]
                            }
                        )
                        bubble["body"]["contents"][0]["contents"].append(
                            {
                                "type": "separator"
                            }
                        )
                        count += 1
                else:
                    continue
            bubble_container = BubbleContainer.new_from_json_dict(bubble)
            return bubble_container
