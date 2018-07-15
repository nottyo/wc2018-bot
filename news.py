# coding=utf-8
import requests
import uuid
import re

from linebot.models import (
    BubbleContainer, CarouselContainer
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

    def _get_latest_news_api(self, limit, offset):
        access_token = self._get_access_token()
        url = base_url + '/latestnews'
        payload = {
            'limit': limit,
            'offset': offset,
            'access_token': access_token
        }
        return requests.post(url, data=payload)

    def _check_image_url(self, image_url):
        default_url = "https://is3-ssl.mzstatic.com/image/thumb/Purple118/v4/5a/06/" \
                   "49/5a06491d-2fe1-4805-8474-f3ebdc610266/source/512x512bb.jpg"
        try:
            if str(image_url.startswith('http:')):
                image_url = image_url.replace('http:', 'https:')
            if '[' in image_url or ']' in image_url:
                return default_url
            r = requests.get(image_url)
            if r.status_code == 200:
                return image_url
            else:
                print("can not get image url: {0}".format(image_url))
                return default_url
        except Exception:
            print("can not get image url: {0}".format(image_url))
            return default_url

    def _create_latest_news_bubble(self, limit, offset):
        response = self._get_latest_news_api(limit, offset)
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
                data['image'] = self._check_image_url(data['image'])


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
                                            "wrap": True,
                                            "action": {
                                                "type": "uri",
                                                "uri": uri_action_base + '/' + data["id"]
                                            }
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
                            "spacing": "md",
                            "contents": [
                                {
                                    "type": "image",
                                    "url": data["image"],
                                    "aspectMode": "cover",
                                    "aspectRatio": "4:3",
                                    "margin": "md",
                                    "size": "sm",
                                    "gravity": "top",
                                    "flex": 1,
                                    "action": {
                                        "type": "uri",
                                        "uri": uri_action_base + '/' + data["id"]
                                    }
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
            return bubble

    def get_latest_news(self, limit):
            bubble = self._create_latest_news_bubble(limit, 0)
            bubble["footer"] = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "size": "md",
                        "action": {
                            "type": "postback",
                            "label": "More News",
                            "data": "scheme=more_news"
                        }
                    }
                ]
            }
            bubble_container = BubbleContainer.new_from_json_dict(bubble)
            return bubble_container

    def get_more_news(self, page_limit=4, page_count=5):
        carousel = {
            "type": "carousel",
            "contents": []
        }
        count = 0
        for page in range(0, page_count):
            bubble = self._create_latest_news_bubble(page_limit, count)
            carousel["contents"].append(bubble)
            count += page_limit
        carousel_container = CarouselContainer.new_from_json_dict(carousel)
        return carousel_container







