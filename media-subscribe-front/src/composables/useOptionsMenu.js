import { ref, onMounted, onUnmounted, inject } from 'vue';
import axios from '../utils/axios';
import useToast from './useToast';

export default function useOptionsMenu(videos, refreshContent) {
  const displayToast = inject('toast');
  const activeOptions = ref(null);
  const optionsPosition = ref({ top: 0, left: 0 });
  const activeVideo = ref(null);

  const toggleOptions = (event, videoId) => {
    event.stopPropagation();
    if (activeOptions.value === videoId) {
      closeOptions();
    } else {
      activeOptions.value = videoId;
      activeVideo.value = Object.values(videos.value).flat().find(v => v.id === videoId);
      updateOptionsPosition(event);
    }
  };

  const updateOptionsPosition = (event) => {
    const button = event.target.closest('button');
    const rect = button.getBoundingClientRect();
    const containerRect = document.querySelector('.video-container').getBoundingClientRect();

    const menuWidth = 160;
    const menuHeight = 200;

    let left = rect.left;
    if (left + menuWidth > containerRect.right) {
      left = containerRect.right - menuWidth;
    }
    left = Math.max(containerRect.left, left);

    let top = rect.bottom + window.scrollY;
    if (top + menuHeight > window.innerHeight) {
      top = rect.top + window.scrollY - menuHeight;
    }

    optionsPosition.value = { top, left };
  };

  const closeOptions = () => {
    activeOptions.value = null;
    activeVideo.value = null;
  };

  // Add this new function
  const handleScrollOrClickOutside = () => {
    closeOptions();
  };

  const toggleReadStatus = async (isRead) => {
    if (activeVideo.value) {
      try {
        console.log('Marking video as read:', activeVideo.value);
        await axios.post('/api/channel-video/mark-read', {
          channel_id: activeVideo.value.channel_id,
          video_id: activeVideo.value.video_id,
          is_read: isRead
        });
        displayToast(`视频已标记为${isRead ? '已读' : '未读'}`);
        // 这里可能需要刷新视频列表
        await refreshContent();
      } catch (error) {
        console.error('更新阅读状态失败:', error);
        displayToast('更新阅读状态失败', true);
      }
    }
    closeOptions();
  };

  const markReadBatch = async (isChannel, isRead, direction) => {
    if (activeVideo.value) {
      try {
        const channelId = isChannel ? activeVideo.value.channel_id : null;
        const response = await axios.post('/api/channel-video/mark-read-batch', {
          is_read: isRead,
          channel_id: channelId,
          direction: direction,
          uploaded_at: activeVideo.value.uploaded_at
        });

        if (response.data.code === 0) {
          displayToast(`已将${direction === 'above' ? '以上' : '以下'}视频标记为${isRead ? '已读' : '未读'}`);

          // 刷新内容以获取更新后的视频列表和计数
          await refreshContent();
        } else {
          throw new Error(response.data.msg || '批量更新阅读状态失败');
        }
      } catch (error) {
        console.error('批量更新阅读状态失败:', error);
        displayToast('批量更新阅读状态失败', true);
      }
    }
    closeOptions();
  };

  const downloadVideo = async () => {
    if (activeVideo.value) {
      try {
        const response = await axios.post('/api/channel-video/download', {
          channel_id: activeVideo.value.channel_id,
          video_id: activeVideo.value.video_id
        });

        if (response.data.code === 0) {
          displayToast('视频下载已开始，请查看下载列表');
          activeVideo.value.if_downloaded = true;
        } else {
          displayToast('视频下载已开始，请查看下载列表');
        }
      } catch (error) {
        console.error('下载视频失败:', error);
        displayToast('下载视频失败: ' + (error.message || '未知错误'), true);
      }
    }
    closeOptions();
  };

  const copyVideoLink = () => {
    if (activeVideo.value) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(activeVideo.value.url)
          .then(() => {
            displayToast('视频链接已复制到剪贴板');
          })
          .catch(err => {
            console.error('复制链接失败: ', err);
            fallbackCopyTextToClipboard(activeVideo.value.url);
          });
      } else {
        fallbackCopyTextToClipboard(activeVideo.value.url);
      }
    }
    closeOptions();
  };

  const fallbackCopyTextToClipboard = (text) => {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      const successful = document.execCommand('copy');
      const msg = successful ? '视频链接已复制到剪贴板' : '复制失败，请手动复制';
      displayToast(msg);
    } catch (err) {
      console.error('Fallback: Oops, unable to copy', err);
      displayToast('复制失败，请手动复制');
    }

    document.body.removeChild(textArea);
  };

  onMounted(() => {
    document.addEventListener('scroll', handleScrollOrClickOutside, true);
    document.addEventListener('click', handleScrollOrClickOutside);
  });

  onUnmounted(() => {
    document.removeEventListener('scroll', handleScrollOrClickOutside, true);
    document.removeEventListener('click', handleScrollOrClickOutside);
  });

  return {
    activeOptions,
    optionsPosition,
    toggleOptions,
    closeOptions,
    toggleReadStatus,
    markReadBatch,
    downloadVideo,
    copyVideoLink,
  };
}