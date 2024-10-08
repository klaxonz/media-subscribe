import concurrent.futures
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import List, Type

from PyCookieCloud import PyCookieCloud
from sqlalchemy import text

from common import constants
from core.cache import RedisClient
from utils.cookie import json_cookie_to_netscape
from core.database import get_session
from core.config import settings
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from services.download_service import start
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)


class BaseTask:
    interval: int = 60  # Default interval in seconds
    unit: str = 'seconds'
    start_immediately: bool = True

    @classmethod
    def run(cls):
        raise NotImplementedError("Subclasses must implement run method")


class TaskRegistry:
    tasks: List[Type[BaseTask]] = []

    @classmethod
    def register(cls, interval: int, unit: str = 'seconds', start_immediately: bool = True):
        def decorator(task_class):
            task_class.interval = interval
            task_class.unit = unit
            task_class.start_immediately = start_immediately
            cls.tasks.append(task_class)
            return task_class

        return decorator


@TaskRegistry.register(interval=60, unit='minutes')
class SyncCookies(BaseTask):
    @classmethod
    def run(cls):
        try:
            cookie_cloud = PyCookieCloud(settings.COOKIE_CLOUD_URL, settings.COOKIE_CLOUD_UUID,
                                         settings.COOKIE_CLOUD_PASSWORD())
            the_key = cookie_cloud.get_the_key()
            if not the_key:
                logger.info('Failed to get the key')
                return
            encrypted_data = cookie_cloud.get_encrypted_data()
            if not encrypted_data:
                logger.info('Failed to get encrypted data')
                return
            decrypted_data = cookie_cloud.get_decrypted_data()
            if not decrypted_data:
                logger.info('Failed to get decrypted data')
                return
            domains = settings.COOKIE_CLOUD_DOMAIN
            if domains:
                expect_domains = domains.split(',')
            else:
                expect_domains = []

            json_cookie_to_netscape(decrypted_data, expect_domains, settings.get_cookies_file_path())
            json_cookie_to_netscape(decrypted_data, expect_domains, settings.get_cookies_http_file_path())

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class RetryFailedTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            five_minutes_ago = datetime.now() - timedelta(minutes=5)
            with get_session() as session:
                tasks = session.query(DownloadTask).filter(
                    text(
                        "(status = 'FAILED' and retry < 5) or (status in ('DOWNLOADING', 'PENDING', 'WAITING') and retry < 5 and updated_at < :update_time)")
                    .params(update_time=five_minutes_ago)
                )

                for task in tasks:
                    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
                    downloading_tasks = session.query(DownloadTask).filter(
                        (DownloadTask.status == 'DOWNLOADING') &
                        (DownloadTask.updated_at <= ten_minutes_ago)
                    ).all()

                    if (task.status == 'PENDING' or task.status == 'WAITING') and len(downloading_tasks) > 0:
                        continue

                    task.error_message = ''
                    task.status = 'PENDING'
                    task.retry = task.retry + 1
                    session.commit()

                    channel = session.query(Channel).filter(Channel.channel_id == task.channel_id).first()
                    if_subscribe = channel is not None
                    start(task.url, if_only_extract=False, if_subscribe=if_subscribe, if_retry=True)

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=1, unit='minutes')
class ChangeStatusTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                tasks = session.query(DownloadTask).filter(DownloadTask.status == 'PENDING', DownloadTask.retry >= 5)

                for task in tasks:
                    task.status = 'FAILED'
                    session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=2, unit='minutes')
class AutoUpdateChannelVideoTask(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                channels = session.query(Channel).filter(Channel.if_enable == 1).all()
                for channel in channels:
                    session.expunge(channel)

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                [executor.submit(cls.update_channel_video, channel) for channel in channels]

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)

    @classmethod
    def update_channel_video(cls, channel):
        redis_client = RedisClient.get_instance().client

        # Check if the channel is in the unsubscribed set
        if redis_client.sismember(constants.UNSUBSCRIBED_CHANNELS_SET, channel.channel_id):
            logger.info(f"Skipping update for recently unsubscribed channel: {channel.name}")
            return

        logger.debug(f"update {channel.name} channel video start")
        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
        if channel.avatar is None:
            with get_session() as session:
                channel = session.query(Channel).filter(Channel.channel_id == channel.channel_id).first()
                channel.avatar = subscribe_channel.get_channel_info().avatar
                session.commit()
        # 下载全部的
        update_all = channel.if_download_all or channel.if_extract_all
        video_list = subscribe_channel.get_channel_videos(channel=channel, update_all=update_all)
        extract_video_list = []
        extract_download_video_list = []
        if channel.if_extract_all:
            if channel.if_auto_download:
                if channel.if_download_all:
                    extract_download_video_list = video_list
                else:
                    extract_video_list = video_list[settings.CHANNEL_UPDATE_DEFAULT_SIZE:]
                    extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list

        else:
            if channel.if_auto_download:
                extract_download_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]
            else:
                extract_video_list = video_list[:settings.CHANNEL_UPDATE_DEFAULT_SIZE]

        for video in extract_video_list:
            start(video, if_subscribe=True)
        for video in extract_download_video_list:
            start(video, if_only_extract=False, if_subscribe=True)
        logger.debug(f"update {channel.name} channel video end")


@TaskRegistry.register(interval=60, unit='minutes')
class RepairDownloadTaskInfo(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                download_tasks = session.query(DownloadTask).filter(DownloadTask.channel_name.is_(None)).all()
                for download_task in download_tasks:
                    if download_task.channel_name is not None:
                        continue

                    base_info = Downloader.get_video_info(download_task.url)
                    video = VideoFactory.create_video(download_task.url, base_info)
                    download_task.channel_id = video.get_uploader().id
                    download_task.channel_url = video.get_uploader().url
                    download_task.channel_name = video.get_uploader().name
                    download_task.channel_avatar = video.get_uploader().avatar
                    session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=10, unit='minutes')
class RepairChanelInfoForTotalVideos(BaseTask):
    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                channels = session.query(Channel).all()
                for channel in channels:
                    extract_count = session.query(ChannelVideo).filter(
                        ChannelVideo.channel_id == channel.channel_id).count()
                    if channel.total_videos >= extract_count:
                        continue
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(channel.url)
                    videos = subscribe_channel.get_channel_videos(channel, update_all=True)
                    channel.total_videos = len(videos)
                    session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}", exc_info=True)


@TaskRegistry.register(interval=120, unit='minutes')
class RepairChannelVideoDuration(BaseTask):
    @classmethod
    def run(cls):
        url = ''
        with get_session() as session:
            channel_videos = session.query(ChannelVideo).filter(ChannelVideo.duration is None).order_by(
                ChannelVideo.created_at.desc()).all()
            for channel_video in channel_videos:
                try:
                    if channel_video.duration is not None:
                        continue
                    url = channel_video.url
                    video = VideoFactory.create_video(url, None)
                    if not video.video_exists():
                        logger.info(f"video not exists: {url}")
                        continue

                    base_info = Downloader.get_video_info(url)
                    video = VideoFactory.create_video(url, base_info)
                    time.sleep(random.randint(1, 2))

                    if base_info is None or video.get_duration() is None:
                        continue
                    channel_video.duration = video.get_duration()
                    session.commit()
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"An unexpected error occurred: url: {url}, {e}", url, exc_info=True)


@TaskRegistry.register(interval=60, unit='minutes')
class CleanUnsubscribedChannelsTask(BaseTask):
    @classmethod
    def run(cls):
        redis_client = RedisClient.get_instance().client

        unsubscribed_channels = redis_client.smembers(constants.UNSUBSCRIBED_CHANNELS_SET)

        if unsubscribed_channels:
            with get_session() as session:
                session.query(ChannelVideo).filter(
                    ChannelVideo.channel_id.in_(unsubscribed_channels)
                ).delete(synchronize_session='fetch')

                session.query(DownloadTask).filter(
                    DownloadTask.channel_id.in_(unsubscribed_channels)
                ).delete(synchronize_session='fetch')

                session.commit()

            logger.info(f"Cleaned up videos and download tasks for {len(unsubscribed_channels)} unsubscribed channels")

        redis_client.expire(constants.UNSUBSCRIBED_CHANNELS_SET, constants.UNSUBSCRIBE_EXPIRATION)
        logger.info("Reset expiration for unsubscribed channels set")
