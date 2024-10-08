import { ref, computed, watch } from 'vue';
import axios from '../utils/axios';

export default function useLatestVideos(channelId) {
  const videoContainer = ref(null);
  const videos = ref({
    all: [],
    unread: [],
    read: []
  });
  const loading = ref(false);
  const allLoaded = ref(false);
  const error = ref(null);
  const activeTab = ref('all');
  const tabContents = ref({ all: null, unread: null, read: null });
  const tabs = [
    { label: '全部', value: 'all' },
    { label: '未读', value: 'unread' },
    { label: '已读', value: 'read' },
  ];
  const videoCounts = ref({ all: 0, unread: 0, read: 0 });
  const observers = ref({});
  const videoRefs = ref({});
  const loadTrigger = ref(null);
  const currentPage = ref(1);
  const searchQuery = ref('');
  const isResetting = ref(false);

  const tabsWithCounts = computed(() => {
    return tabs.map(tab => ({
      ...tab,
      count: videoCounts.value[tab.value]
    }));
  });

  const isReadPage = computed(() => activeTab.value === 'read');

  const handleSearch = (query) => {
    searchQuery.value = query;
    resetAndReload();
  };

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return;

    loading.value = true;
    try {
      const pageSize = currentPage.value === 1 ? 30 : 10; // Load 30 items on first page, 10 on subsequent pages
      const response = await axios.get('/api/channel-video/list', {
        params: {
          page: currentPage.value,
          pageSize: pageSize,
          query: searchQuery.value,
          channel_id: channelId,
          read_status: activeTab.value === 'all' ? null : activeTab.value
        }
      });

      if (response.data.code === 0) {
        const newVideos = response.data.data.data.map(video => ({
          ...video,
          isPlaying: false,
          video_url: null
        }));
        videos.value[activeTab.value] = [...videos.value[activeTab.value], ...newVideos];
        currentPage.value++;
        allLoaded.value = newVideos.length < pageSize;
        videoCounts.value = response.data.data.counts;
      } else {
        throw new Error(response.data.msg || '获取视频列表失败');
      }
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value = false;
    }
  };

  const handleScroll = (event, channelId) => {
    const scrollContent = event.target;
    const scrollPosition = scrollContent.scrollTop + scrollContent.clientHeight;
    const scrollHeight = scrollContent.scrollHeight;

    if (scrollHeight - scrollPosition <= 300 && !loading.value && !allLoaded.value) {
      loadMore(channelId);
    }
  };

  const resetAndReload = () => {
    isResetting.value = true;
    videos.value[activeTab.value] = [];
    currentPage.value = 1;
    allLoaded.value = false;
    error.value = null;
    loadMore().then(() => {
      isResetting.value = false;
    });
  };

  const setLoadTrigger = (el) => {
    if (el) loadTrigger.value = el;
  };

  watch(activeTab, () => {
    resetAndReload();
  });

  return {
    videoContainer,
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    tabContents,
    tabs,
    videoCounts,
    tabsWithCounts,
    isReadPage,
    observers,
    videoRefs,
    loadTrigger,
    handleSearch,
    loadMore,
    handleScroll,
    setLoadTrigger,
    isResetting,
  };
}