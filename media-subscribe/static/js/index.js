var currentPage = 1; // 当前页码
var itemsPerPage = 10; // 每页显示的项目数

const statusMap = {
    'PENDING': '待处理',
    'WAITING': '等待下载',
    'UNSUPPORTED': '不支持',
    'DOWNLOADING': '下载中',
    'PAUSED': '暂停',
    'COMPLETED': '已完成',
    'FAILED': '失败'
};


let intervalId = null;

function navigate(section) {
    // 隐藏所有内容区域
    document.querySelectorAll('#content > div').forEach(div => div.style.display = 'none');

    // 显示对应的内容区域
    document.getElementById(`${section}-content`).style.display = 'block';

    // 更新导航激活状态
    document.querySelectorAll('#nav li').forEach(li => li.classList.remove('active'));
    document.getElementById(`nav-${section}`).classList.add('active');

    // 根据导航项重新加载数据或执行相应操作
    currentPage = 1;
    itemsPerPage = 10;
    if (section === 'download') {
        fetchDownloadTaskData();
        startDownloadTaskInterval()
    } else if (section === 'subscribe') {
        clearInterval(intervalId)
        fetchSubscribeChannelData();
    } else if (section === 'subscribe-update') {
        clearInterval(intervalId)
        fetchSubscribeChannelVideoData();
    }
}

function fetchDownloadTaskData() {
    const status = document.querySelector('input[name="download-task-status"]:checked').value;
    fetch(`/api/task/list?status=${status}&page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateDownloadTaskList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelData() {
    fetch(`/api/channel/list?page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelList)
        .catch(error => console.error('Error fetching data:', error));
}

function fetchSubscribeChannelVideoData() {
    const title = document.getElementById('titleSearchInput').value.trim();
    const channel_name = document.getElementById('channelSearchInput').value.trim();
    const video_id = document.getElementById('videoIdSearchInput').value.trim();
    fetch(`/api/channel-video/list?title=${title}&channel_name=${channel_name}&video_id=${video_id}&page=${currentPage}&pageSize=${itemsPerPage}`)
        .then(response => response.json())
        .then(updateSubscribeChannelVideoList)
        .catch(error => console.error('Error fetching data:', error));
}

function handleChannelSearchResetClick() {
    document.getElementById('titleSearchInput').value = '';
    document.getElementById('channelSearchInput').value = '';
    fetchSubscribeChannelVideoData();
}

function markReadChannelVideo(channelId, videoId) {
    fetch('/api/channel-video/mark-read/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            channel_id: channelId,
            video_id: videoId
        })
    })
        .then(response => response.json())
        .then(data => {
            fetchSubscribeChannelVideoData();
        });
}

function updateDownloadTaskList(taskInfo) {
    var tbody = document.querySelector('#download-content table tbody');
    var tasks = taskInfo.data.data;

    const existingRows = {};
    tbody.querySelectorAll('tr').forEach(function (row) {
        existingRows[row.getAttribute('data-task-id')] = row;
    })

    let prevRow = null;

    tasks.forEach(function (task) {
        const taskId = task.id;

        if (!existingRows[taskId]) {
            // 如果这个taskId对应的行不存在，创建一个新的行
            var row = document.createElement('tr');
            row.setAttribute('data-task-id', taskId);

            // 创建并填充列元素
            var columns = [
                document.createElement('td'), // 任务ID
                document.createElement('td'), // 频道封面
                document.createElement('td'), // 频道名称
                document.createElement('td'), // 封面
                document.createElement('td'), // 任务名称
                document.createElement('td'), // 状态
                document.createElement('td'), // 重试次数
                document.createElement('td'), // 文件大小
                document.createElement('td'), // 进度
                document.createElement('td'), // 下载速度
                document.createElement('td'), // 剩余时间
                document.createElement('td'), // 备注
                document.createElement('td'), // 创建时间
                document.createElement('td'), // 更新时间
                document.createElement('td')  // 操作
            ];

            // 填充列内容
            columns[0].textContent = task.id;
            columns[1].classList.add('avatar-box');
            columns[1].innerHTML = `<img src="${task.channel_avatar}" referrerpolicy="no-referrer">`;
            columns[2].textContent = task.channel_name;
            columns[3].classList.add('img-box');
            columns[3].innerHTML = `<img src="${task.thumbnail}" referrerpolicy="no-referrer">`;
            columns[4].textContent = task.title;
            columns[5].textContent = statusMap[task.status] || '未知状态';
            columns[6].textContent = task.retry;
            columns[7].textContent = formatBytes(task.total_size);
            columns[8].textContent = task.percent;
            columns[9].textContent = task.speed;
            columns[10].textContent = task.eta;
            columns[11].textContent = task.error_message ? task.error_message : '';
            columns[11].style.width = '300px';
            columns[12].textContent = task.created_at;
            columns[13].textContent = task.updated_at;
            columns[14].classList.add('action-buttons');
            if (task.status === 'COMPLETED') {
                columns[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handlePlayClick(${task.id})">播放</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else if (task.status === 'DOWNLOADING') {
                columns[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handlePauseClick(event, ${task.id})">暂停</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else if (task.status === 'FAILED' || task.status === 'PENDING' || task.status === 'PAUSED') {
                columns[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handleRetryClick(event, ${task.id})">重试</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else {
                columns[14].innerHTML = `                
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            }

            // 将列元素添加到行中
            columns.forEach(column => row.appendChild(column));
            if (prevRow) {
                prevRow.insertAdjacentElement('afterend', row)
            } else {
                tbody.insertBefore(row, tbody.firstChild);
            }
            prevRow = row;

        } else {
            // 否则，更新已存在的行
            var row = existingRows[taskId];
            row.children[5].textContent = statusMap[task.status] || '未知状态';
            row.children[6].textContent = task.retry;
            row.children[7].textContent = formatBytes(task.total_size);
            row.children[8].textContent = task.percent;
            row.children[9].textContent = task.speed;
            row.children[10].textContent = task.eta;
            row.children[11].textContent = task.error_message ? task.error_message : '';
            row.children[11].style.width = '300px';
            row.children[13].textContent = task.updated_at;
            if (task.status === 'COMPLETED') {
                row.children[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handlePlayClick(${task.id})">播放</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else if (task.status === 'DOWNLOADING') {
                row.children[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handlePauseClick(event, ${task.id})">暂停</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else if (task.status === 'FAILED' || task.status === 'PENDING' || task.status === 'PAUSED') {
                row.children[14].innerHTML = `                
                    <a href="#" class="button play-button" onclick="handleRetryClick(event, ${task.id})">重试</a>
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            } else {
                row.children[14].innerHTML = `                
                    <a href="#" class="button delete-button" onclick="handleDeleteClick(${task.id})">删除</a>
                `;
            }
            delete existingRows[taskId];
            prevRow = row;
        }
    });

    // 移除那些不再存在的行
    Object.keys(existingRows).forEach(taskId => {
        const row = existingRows[taskId];
        tbody.removeChild(row);
    });

    generateDownloadTaskPaginationButtons(taskInfo.data.total);
}

function updateSubscribeChannelList(subscribeInfo) {
    var tbody = document.querySelector('#subscribe-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var channels = subscribeInfo.data.data;
    channels.forEach(function (channel) {
        var row = `<tr>
            <td>${channel.id}</td>
            <td  class="avatar-box"><img src="${channel.avatar}" referrerpolicy="no-referrer"></td>
            <td>${channel.name}</td>
            <td>${channel.total_videos}</td>
            <td>${channel.total_extract}</td>
            <td>${channel.if_enable ? '启用' : '暂停'}</td>
            <td>${channel.if_auto_download ? '是' : '否'}</td>
            <td>${channel.if_download_all ? '是' : '否'}</td>
            <td>${channel.if_extract_all ? '是' : '否'}</td>
            <td><a target="_blank" href="${channel.url}">${channel.url}</a></td>
            <td>${channel.created_at}</td>
            <td class="action-buttons">
                <a href="#" class="button" onclick="handleChannelDetailClick(${channel.id})">详情</a>
                <a href="#" class="button delete-button" onclick="handleChannelDeleteClick(${channel.id})">删除</a>
            </td>
        </tr>`;
        tbody.insertAdjacentHTML('beforeend', row);
    });

    generateSubscribeChannelPaginationButtons(subscribeInfo.data.total);
}

function updateSubscribeChannelVideoList(subscribeChannelVideoInfo) {
    var tbody = document.querySelector('#subscribe-update-content table tbody');
    tbody.innerHTML = ''; // 清空现有内容以准备更新
    var channelVideos = subscribeChannelVideoInfo.data.data;
    channelVideos.forEach(function (channelVideo) {

        var row = document.createElement('tr');
        var columns = [
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
            document.createElement('td'),
        ];

        columns[0].innerHTML = `<img src="${channelVideo.channel_avatar}" referrerpolicy="no-referrer">`;
        columns[0].classList.add('avatar-box');
        columns[1].textContent = channelVideo.channel_name;
        columns[2].innerHTML = `<img src="${channelVideo.thumbnail}" referrerpolicy="no-referrer">`;
        columns[2].classList.add('img-box');
        columns[3].textContent = channelVideo.title;
        columns[4].innerHTML = `<a target="_blank" href="${channelVideo.url}">${channelVideo.url}</a>`
        columns[5].textContent = channelVideo.uploaded_at;
        columns[6].textContent = channelVideo.if_downloaded ? '是' : '否';
        columns[7].textContent = channelVideo.if_read ? '是' : '否';

        if (channelVideo.if_downloaded) {
            columns[8].innerHTML = `<a href="#" class="button download-button" onclick="handleChannelVideoPlayClick('${channelVideo.channel_id}', '${channelVideo.video_id}')">播放</a>
                                    <a href="#" class="button delete-button" onclick="markReadChannelVideo('${channelVideo.channel_id}', '${channelVideo.video_id}')">标记</a>`;
        } else {
            columns[8].innerHTML = `<a href="#" class="button download-button" onclick="handleDownloadClick('${channelVideo.channel_id}', '${channelVideo.video_id}')">下载</a>
                                <a href="#" class="button delete-button" onclick="markReadChannelVideo('${channelVideo.channel_id}', '${channelVideo.video_id}')">标记</a>`;
        }
        columns.forEach(column => row.appendChild(column));
        tbody.appendChild(row);
    });

    generateSubscribeChannelVideoPaginationButtons(subscribeChannelVideoInfo.data.total);
}

function handleChannelDetailClick(subscribe_id) {
    fetch(`/api/channel/detail?id=${subscribe_id}`)
        .then(response => response.json())
        .then(response => openChannelDetailModal(response.data))
        .catch(error => console.error('Error fetching data:', error));
}


function handleChannelDeleteClick(subscribe_id) {
    const requestBody = {
        id: subscribe_id
    };
    fetch(`/api/channel/delete`, {
        method: 'POST', // Specify the method as POST
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
    })
        .then(response => {
            if (response.status === 200) {
                fetchSubscribeChannelData();
                openMessageModal('订阅已删除！')
            } else {
                openMessageModal('订阅删除失败！')
            }
        })
        .catch(error => console.error('Error fetching data:', error));
}


function openChannelDetailModal(channelDetail) {
    console.log(channelDetail)
    document.getElementById('channelInfoModal').style.display = 'block';
    document.getElementById('modalSubscribeId').innerText = channelDetail.id;
    document.getElementById('modalChannelId').innerText = channelDetail.channel_id;
    document.getElementById('modalChannelName').innerText = channelDetail.name;
    document.getElementById('modalChannelUrl').innerText = channelDetail.url;
    document.getElementById('modalChannelSubscribeTime').innerText = channelDetail.created_at;
    const enableRadios = document.querySelectorAll('input[name="modalChannelIfEnable"]');
    if (channelDetail.if_enable) {
        enableRadios[0].checked = true;
    } else {
        enableRadios[1].checked = true;
    }
    const autoDownloadRadios = document.querySelectorAll('input[name="modalChannelIfAutoDownload"]');
    if (channelDetail.if_auto_download) {
        autoDownloadRadios[0].checked = true;
    } else {
        autoDownloadRadios[1].checked = true;
    }
    const downloadAllRadios = document.querySelectorAll('input[name="modalChannelIfDownloadAll"]');
    if (channelDetail.if_download_all) {
        downloadAllRadios[0].checked = true;
    } else {
        downloadAllRadios[1].checked = true;
    }
    const extractAllRadios = document.querySelectorAll('input[name="modalChannelIfExtractAll"]');
    if (channelDetail.if_extract_all) {
        extractAllRadios[0].checked = true;
    } else {
        extractAllRadios[1].checked = true;
    }
}

function handleChannelSaveClick(event) {
    var subscribeId = document.getElementById('modalSubscribeId').innerText.trim();
    var ifEnable = document.querySelector('input[name="modalChannelIfEnable"]:checked').value;
    var ifAutoDownload = document.querySelector('input[name="modalChannelIfAutoDownload"]:checked').value;
    var ifDownloadAll = document.querySelector('input[name="modalChannelIfDownloadAll"]:checked').value;
    var ifExtractAll = document.querySelector('input[name="modalChannelIfExtractAll"]:checked').value;

    // Construct the request body as JSON
    var requestBody = {
        id: subscribeId,
        if_enable: ifEnable, // Assuming values are strings like 'true'/'false', convert to boolean if needed
        if_auto_download: ifAutoDownload,
        if_download_all: ifDownloadAll,
        if_extract_all: ifExtractAll
    };

    fetch(`/api/channel/update`, {
        method: 'POST', // Specify the method as POST
        headers: {
            'Content-Type': 'application/json', // Set the content type header
        },
        body: JSON.stringify(requestBody), // Convert the request body to a JSON string
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            handleChannelDetailCloseClick();
            fetchSubscribeChannelData();
        })
        .catch(error => console.error('Error updating channel:', error));
}

function handleChannelDetailCloseClick(event) {
    document.getElementById('channelInfoModal').style.display = 'none';
}

function handleDownloadClick(channelId, videoId) {
    fetch('/api/channel-video/download/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            channel_id: channelId,
            video_id: videoId
        })
    })
        .then(response => response.json())
        .then(data => {
            fetchSubscribeChannelVideoData();
            openMessageModal('视频下载任务已成功创建！')
        })
        .catch(error => console.error('Error:', error));
}

function handleDownloadTaskStatusClick() {
    currentPage = 1;
}

function handlePlayClick(taskId) {
    showVideoModal(`/api/task/video/play/${taskId}`)
}

function handleChannelVideoPlayClick(channelId, taskId) {
    showVideoModal(`/api/channel/video/play/${channelId}/${taskId}`)
}


function handlePauseClick(event, taskId) {
    fetch('/api/task/pause', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: taskId,
        })
    })
        .then(response => {
            event.target.textContent = '开始';
        });
}


function handleRetryClick(event, taskId) {
    fetch('/api/task/retry', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: taskId,
        })
    })
        .then(response => {
            event.target.textContent = '开始';
        });
}

function handleDeleteClick(taskId) {
    fetch('/api/task/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            task_id: taskId,
        })
    })
}

function startDownloadTaskInterval() {
    intervalId = setInterval(() => {
        fetchDownloadTaskData();
    }, 1000)
}


function generatePaginationButtons(selector, total_records, fetchDataFunction) {
    var itemsPerPage = 10; // 假设每页显示10条记录
    var pages = Math.ceil(total_records / itemsPerPage);
    var paginationDiv = document.getElementById(selector);
    paginationDiv.innerHTML = ''; // 清空现有分页按钮

    // 添加总记录数显示
    var totalRecordsSpan = document.createElement('span');
    totalRecordsSpan.textContent = `总共: ${total_records}  `;
    paginationDiv.appendChild(totalRecordsSpan);

    // 定义显示的页码范围
    var visiblePages = 5; // 每边显示2个页码，加上当前页共5个页码
    var startPage = Math.max(1, currentPage - Math.floor(visiblePages / 2));
    var endPage = Math.min(pages, startPage + visiblePages - 1);

    // 添加首页按钮
    if (startPage > 1) {
        var firstButton = document.createElement('button');
        firstButton.textContent = '<<';
        firstButton.onclick = () => {
            currentPage = 1;
            fetchDownloadTaskData();
        };
        paginationDiv.appendChild(firstButton);

        // 添加省略号
        var ellipsisStart = document.createElement('span');
        ellipsisStart.textContent = '...';
        paginationDiv.appendChild(ellipsisStart);
    }

    // 添加页码按钮
    for (let i = startPage; i <= endPage; i++) {
        var button = document.createElement('button');
        button.textContent = i;
        button.onclick = (function (page) {
            return function () {
                currentPage = page;
                fetchDataFunction();
            };
        })(i);
        if (i === currentPage) button.classList.add('active');
        paginationDiv.appendChild(button);
    }

    // 添加末页按钮
    if (endPage < pages) {
        // 添加省略号
        var ellipsisEnd = document.createElement('span');
        ellipsisEnd.textContent = '...';
        paginationDiv.appendChild(ellipsisEnd);

        var lastButton = document.createElement('button');
        lastButton.textContent = '>>';
        lastButton.onclick = () => {
            currentPage = pages;
            fetchDownloadTaskData();
        };
        paginationDiv.appendChild(lastButton);
    }
}

function generateDownloadTaskPaginationButtons(total_records) {
    generatePaginationButtons('download-task-pagination', total_records, fetchDownloadTaskData)
}

function generateSubscribeChannelPaginationButtons(total_records) {
    generatePaginationButtons('subscribe-channel-pagination', total_records, fetchSubscribeChannelData)
}


function generateSubscribeChannelVideoPaginationButtons(total_records) {
    generatePaginationButtons('subscribe-channel-update-pagination', total_records, fetchSubscribeChannelVideoData)
}

function openMessageModal(message) {
    document.getElementById('modalMessage').innerText = message;
    document.getElementById('customModal').style.display = 'block';
    // 添加点击关闭按钮的事件监听器
    document.querySelector('.close').addEventListener('click', function () {
        document.getElementById('customModal').style.display = 'none';
    });
}

// 确保此函数在其他脚本执行后运行，或者将其放在所有其他脚本之后
function showVideoModal(videoUrl) {
    var videoPlayer = document.getElementById('videoPlayer');
    var videoSource = document.getElementById('videoSource');

    // 设置视频源URL
    videoSource.src = videoUrl;
    // 开启自动播放
    videoPlayer.autoplay = true;
    // 重置视频源，以便重新加载
    videoPlayer.load();

    // 显示模态框
    document.getElementById('videoPlayerModal').style.display = 'block';

    // 可选：尝试播放视频，增强兼容性
    videoPlayer.addEventListener('canplay', function () {
        videoPlayer.play().catch(function (error) {
            console.error("自动播放失败:", error);
        });
    });
}

function closeVideoModal() {
    // 获取video元素
    var videoPlayer = document.getElementById('videoPlayer');
    // 暂停视频播放
    videoPlayer.pause();
    // 隐藏视频播放模态框
    document.getElementById('videoPlayerModal').style.display = 'none';
}


function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

window.onload = function () {

    document.getElementById('nav-download').classList.add('active');

    fetchDownloadTaskData();
    startDownloadTaskInterval()

    document.addEventListener('keydown', function (event) {
        // 检查用户是否按下了Esc键（其键码为27）
        if (event.keyCode === 27 && document.getElementById('videoPlayerModal').style.display === 'block') {
            closeVideoModal();
        }
    });
};