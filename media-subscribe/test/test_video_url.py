import requests

# from model.channel import Channel

# yt = YouTube('https://youtube.com/watch?v=GxQC3pqoA9Y', use_oauth=True, allow_oauth_cache=True,)
# print(yt.title)
# print(yt.streaming_data)

# c = YouTubeChannel('https://www.youtube.com/@clark_ash')
# for url in c.video_urls:
#     print(url.watch_url)
# for url in c.shorts:
#     print(url.watch_url)


# url = 'https://www.bilibili.com/video/BV1nBWeeEEiB'
# cookies = filter_cookies_to_query_string(url)
# headers = {
#     'Referer': url,
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
#                   'Chrome/58.0.3029.110 Safari/537.3',
#     'Cookie': cookies
# }
#
# response = requests.get(url, headers=headers)
# print(response.text)

# url = 'https://space.bilibili.com/416878454'
# subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
# channel_info = subscribe_channel.get_channel_info()
#
# channel = Channel()
# channel.channel_id = channel_info.id
# channel.name = channel_info.name
# channel.url = channel_info.url
# channel.avatar = channel_info.avatar
# channel.if_extract_all = 1
# videos = subscribe_channel.get_channel_videos(channel, update_all=True)
# channel.total_videos = len(videos)
# print(videos)
#
# from yt_dlp import YoutubeDL
#
# url = 'https://www.youtube.com/@LucyThomasMusic/videos'
#
# ydl_opts = {
#     'playlist_items': '-1',
#     'extract_flat': 'in_playlist',
# }
#
# with YoutubeDL(ydl_opts) as ydl:
#     info = ydl.extract_info(url, download=False)
#
#     print(json.dumps(info))


resp = requests.get(
    '')

print(resp.status_code)
