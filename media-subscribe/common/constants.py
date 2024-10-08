QUEUE_DOWNLOAD_TASK = 'video:download:queue'
QUEUE_SUBSCRIBE_TASK = 'video:subscribe:queue'
QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD = 'channel:video:extract:download'

MESSAGE_TYPE_DOWNLOAD = 'download'
MESSAGE_TYPE_SUBSCRIBE = 'subscribe'

REDIS_KEY_UPDATE_CHANNEL_VIDEO_TASK = 'update_channel_video_task'
REDIS_KEY_VIDEO_DOWNLOAD_PROGRESS = 'video:download:progress'
REDIS_KEY_VIDEO_DOWNLOAD_STATUS = 'video:download:status'
REDIS_KEY_VIDEO_DOWNLOAD_CACHE = 'video:download:cache'

REDIS_KEY_TASK_STATUS = 'video:task:status'

UNSUBSCRIBED_CHANNELS_SET = "unsubscribed_channels"
UNSUBSCRIBE_EXPIRATION = 60 * 60 * 24  # 24 hours in seconds
