import json
import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
from pytubefix import YouTube

from utils.cookie import filter_cookies_to_query_string
from common.http_wrapper import session
from core.config import settings

logger = logging.getLogger()


class Video:

    def __init__(self, url, base_info):
        self.id = None
        self.url = url
        self.title = None
        self.description = None
        self.tags = None
        self.duration = None
        self.thumbnail = None
        self.upload_date = None
        self.uploader = None
        self.base_info = base_info
        self.season = None

    def get_url(self):
        return self.url

    def get_uploader(self):
        if self.uploader is None:
            self.uploader = UploaderFactory.create_uploader(self.url)
        return self.uploader

    def get_title(self):
        if self.title is None:
            self.title = self.base_info.get("title")
        return self.title

    def get_description(self):
        if self.description is None:
            self.description = self.base_info.get("description")
        return self.description

    def get_thumbnail(self):
        if self.thumbnail is None:
            self.thumbnail = self.base_info.get("thumbnail")
        return self.thumbnail

    def get_upload_date(self):
        if self.upload_date is None:
            self.upload_date = self.base_info.get("upload_date")
        return self.upload_date

    def get_tags(self):
        if self.tags is None:
            self.tags = self.base_info.get("tags")
        return self.tags

    def get_duration(self):
        if self.duration is None:
            self.duration = self.base_info.get("duration")
        return self.duration

    def get_season(self):
        if self.season is None:
            self.season = self.get_upload_date()[0:4]
        return self.season

    def get_tv_show_root_path(self):
        root_path = settings.get_download_root_path()
        uploader_name = self.get_valid_uploader_name()
        return os.path.join(root_path, uploader_name)

    def get_download_full_path(self):
        root_path = settings.get_download_root_path()
        uploader_name = self.get_valid_uploader_name()
        season = self.get_season()

        return os.path.join(root_path, uploader_name, f"Season {season}")

    def get_valid_uploader_name(self):
        uploader_name = self.get_uploader().get_name()
        return sanitize_filename(uploader_name)

    def get_valid_filename(self):
        title = self.get_title()
        return sanitize_filename(title)

    def video_exists(self):
        return True


class BilibiliVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    def video_exists(self):
        cookies = filter_cookies_to_query_string(self.url)
        headers = {
            'Referer': self.url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Cookie': cookies
        }
        response = requests.get(self.url, headers=headers)
        return '视频去哪了' not in response.text


class YoutubeVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)


class PornhubVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

class JavVideo(Video):

    def __init__(self, url, base_info):
        super().__init__(url, base_info)


class Uploader:
    def __init__(self, url):
        self.url = url
        self.id = None
        self.name = None
        self.avatar = None
        self.tags = None
        self.actors = []

    def get_id(self):
        return self.id

    def get_url(self):
        return self.url

    def get_name(self):
        return self.name

    def get_avatar(self):
        return self.avatar

    def get_tags(self):
        return self.tags

    def get_actors(self):
        return self.actors


class BilibiliUploader(Uploader):
    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/58.0.3029.110 Safari/537.3',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }

        # 发送带有请求头的HTTP GET请求
        response = session.get(self.url, headers=headers, timeout=20)
        response.raise_for_status()  # 检查请求是否成功

        match = re.search(r'window\.__INITIAL_STATE__=(\{.*?\});', response.text)

        if match:
            json_str = match.group(1)  # 提取 JSON 字符串
            data = json.loads(json_str)

            if 'videoStaffs' in data:
                logger.info(f"Not a normal video. url: {self.url}")
                return

            if data.get('upData') is None:
                logger.info(f"Failed to extract data from the response. url: {self.url}")
                return

            self.id = data.get('upData').get('mid')
            self.name = data.get('upData').get('name')
            self.avatar = data.get('upData').get('face')
            self.tags = []

            tags = data.get('tags')
            for tag in tags:
                self.tags.append(tag.get('tag_name'))


class YoutubeUploader(Uploader):
    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        video = YouTube(self.url, use_oauth=False, allow_oauth_cache=False)
        self.id = video.channel_id
        self.name = video.author
        self.avatar = video.thumbnail_url
        self.tags = []


class VideoFactory:

    @staticmethod
    def create_video(url, video_info):
        if 'bilibili.com' in url:
            return BilibiliVideo(url, video_info)
        elif 'youtube.com' in url:
            return YoutubeVideo(url, video_info)
        elif 'pornhub.com' in url:
            return PornhubVideo(url, video_info)
        elif 'javdb.com' in url:
            return JavVideo(url, video_info)


class PornhubUploader(Uploader):
    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        # cookies = filter_cookies_to_query_string(self.url)

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            # 'Cookie': cookies
        }
        req_url = self.url.replace('www', 'cn')
        response = session.get(req_url, headers=headers, timeout=20)
        response.raise_for_status()  # 检查请求是否成功
        bs4 = BeautifulSoup(response.text, 'html.parser')
        username_el = bs4.select('.userInfoBlock .usernameWrap')[0]
        if username_el is not None:
            self.name = bs4.select('.userInfoBlock .usernameWrap a')[0].text.strip()
            user_type = bs4.select('.userInfoBlock .usernameWrap')[0].get('data-type')
            if user_type == 'user':
                self.id = bs4.select('.userInfoBlock .usernameWrap')[0].get('data-userid')
            elif user_type == 'channel':
                self.id = bs4.select('.userInfoBlock .usernameWrap')[0].get('data-channelid')
            else:
                raise Exception('Unknown user type')
            self.avatar = bs4.select('.userInfoBlock .userAvatar img')[0].get('src')
            self.tags = []
        actors = bs4.select('.pornstarsWrapper a.pstar-list-btn')
        if len(actors) > 0:
            base_url = self.url.split('/')[2]
            for actor in actors:
                self.actors.append(f'https://{base_url}{actor.get("href")}')


class JavUploader(Uploader):
    def __init__(self, url):
        super().__init__(url)
        self.init()

    def init(self):
        cookies = filter_cookies_to_query_string(self.url)

        headers = {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/124.0.0.0 Safari/537.36',
            'Cookie': cookies
        }
        response = session.get(self.url, headers=headers, timeout=20)
        response.raise_for_status()
        bs4 = BeautifulSoup(response.text, 'html.parser')

        if 'javdb.com/v/' in self.url:
            els = bs4.select('.movie-panel-info .panel-block')
            for el in els:
                if '演员' in el.text or '演員' in el.text:
                    self.url = 'https://javdb.com' + el.select('a:nth-of-type(1)')[0].get('href')
                    response = session.get(self.url, headers=headers, timeout=20)
                    response.raise_for_status()
                    bs4 = BeautifulSoup(response.text, 'html.parser')
                    break

        username_el = bs4.select('.actor-section-name')
        if len(username_el) > 0:
            self.name = username_el[0].text.strip().split(',')[0]
            avatar_el = bs4.select('.avatar')[0]
            style = avatar_el['style']
            self.avatar = re.search(r'url\((.*?)\)', style).group(1)
            self.id = self.url.split('/')[-1]
            self.tags = []
        time.sleep(1)


class UploaderFactory:

    @staticmethod
    def create_uploader(url):
        if 'bilibili.com' in url:
            return BilibiliUploader(url)
        elif 'youtube.com' in url:
            return YoutubeUploader(url)
        elif 'pornhub.com' in url:
            return PornhubUploader(url)
        elif 'javdb.com' in url:
            return JavUploader(url)
