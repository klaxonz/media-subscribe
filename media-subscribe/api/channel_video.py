import asyncio
import logging
import os
import re
import stat
from email.utils import formatdate
from mimetypes import guess_type
from urllib.parse import urljoin

import httpx
from fastapi import Query, APIRouter, Request, HTTPException, Body, Depends
from pydantic.json_schema import model_json_schema
from sqlalchemy import and_
from starlette.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel

import common.response as response
from core.database import get_session
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.channel import ChannelVideo
from schemas.channel_video import MarkReadRequest, MarkReadBatchRequest, DownloadChannelVideoRequest, DislikeRequest, \
    SortBy, ToggleLikeRequest
from services.channel_video_service import ChannelVideoService

logger = logging.getLogger()

router = APIRouter(
    tags=['频道视频接口']
)


@router.get("/api/channel-video/video/url")
def get_video_url(
        channel_id: str = Query(None, description="频道名称"),
        video_id: str = Query(None, description="视频ID")
):
    channel_video_service = ChannelVideoService()
    video_urls = channel_video_service.get_video_url(channel_id, video_id)
    return response.success(video_urls)

@router.get("/api/channel-video/video")
def get_video(
        channel_id: str = Query(None, description="频道名称"),
        video_id: str = Query(None, description="视频ID")
):
    channel_video_service = ChannelVideoService()
    video = channel_video_service.get_video(channel_id, video_id)

    return response.success(video)


@router.get("/api/channel-video/list")
def get_channel_videos(
        query: str = Query(None, description="搜索关键字"),
        channel_id: str = Query(None, description="频道ID"),
        read_status: str = Query(None, description="阅读状态: all, read, unread, preview"),
        sort_by: SortBy = Query(SortBy.UPLOADED_AT, description="排序字段"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, alias="pageSize", description="每页数量"),
):
    channel_video_service = ChannelVideoService()
    videos, counts = channel_video_service.list_channel_videos(query, channel_id, read_status, sort_by, page, page_size)
    return response.success({
        "total": len(videos),
        "page": page,
        "pageSize": page_size,
        "data": videos,
        "counts": counts
    })


@router.post("/api/channel-video/mark-read")
def mark_video_read(req: MarkReadRequest):
    channel_video_service = ChannelVideoService()
    channel_video_service.mark_video_read(req.channel_id, req.video_id, req.is_read)
    return response.success()


@router.post("/api/channel-video/mark-read-batch")
def mark_videos_read_batch(req: MarkReadBatchRequest):
    channel_video_service = ChannelVideoService()
    channel_video_service.mark_videos_read_batch(req.channel_id, req.direction, req.uploaded_at, req.is_read)
    return response.success()


@router.post("/api/channel-video/download")
def download_channel_video(req: DownloadChannelVideoRequest):
    channel_video_service = ChannelVideoService()
    channel_video_service.download_channel_video(req.channel_id, req.video_id)
    return response.success()


@router.post("/api/channel-video/toggle-like")
def toggle_like_video(
    req: ToggleLikeRequest,
):

    channel_video_service = ChannelVideoService()
    channel_video_service.toggle_like_video(channel_id=req.channel_id, video_id=req.video_id, is_liked=req.is_liked)
    return response.success()


@router.get("/api/channel/video/play/{channel_id}/{video_id}")
def play_video(request: Request, channel_id: str, video_id: str):
    with get_session() as s:
        channel_video = s.query(ChannelVideo).filter(
            and_(
                ChannelVideo.channel_id == channel_id,
                ChannelVideo.video_id == video_id
            )
        ).first()
        if channel_video:
            s.expunge(channel_video)
        else:
            raise HTTPException(status_code=404, detail="Video not found")

    base_info = Downloader.get_video_info(channel_video.url)
    video = VideoFactory.create_video(channel_video.url, base_info)
    output_dir = video.get_download_full_path()
    filename = video.get_valid_filename() + ".mp4"
    video_path = os.path.join(output_dir, filename)

    stat_result = os.stat(video_path)
    content_type, encoding = guess_type(video_path)
    content_type = content_type or 'application/octet-stream'
    range_str = request.headers.get('range', '')
    range_match = re.search(r'bytes=(\d+)-(\d+)', range_str, re.S) or re.search(r'bytes=(\d+)-', range_str, re.S)
    if range_match:
        start_bytes = int(range_match.group(1))
        end_bytes = int(range_match.group(2)) if range_match.lastindex == 2 else stat_result.st_size - 1
    else:
        start_bytes = 0
        end_bytes = stat_result.st_size - 1

    content_length = stat_result.st_size - start_bytes if stat.S_ISREG(stat_result.st_mode) else stat_result.st_size
    # 打开文件从起始位置开始分片读取文件
    return StreamingResponse(
        file_iterator(video_path, start_bytes, 1024 * 1024 * 1),  # 每次读取 1M
        media_type=content_type,
        headers={
            'accept-ranges': 'bytes',
            'connection': 'keep-alive',
            'content-length': str(content_length),
            'content-range': f'bytes {start_bytes}-{end_bytes}/{stat_result.st_size}',
            'last-modified': formatdate(stat_result.st_mtime, usegmt=True),
        },
        status_code=206 if start_bytes > 0 else 200
    )


def file_iterator(file_path, offset, chunk_size):
    """
    文件生成器
    :param file_path: 文件绝对路径
    :param offset: 文件读取的起始位置
    :param chunk_size: 文件读取的块大小
    :return: yield
    """
    with open(file_path, 'rb') as f:
        f.seek(offset, os.SEEK_SET)
        while True:
            data = f.read(chunk_size)
            if data:
                yield data
            else:
                break


@router.get("/api/channel-video/proxy")
async def proxy_video(domain: str, url: str, request: Request):
    """
    代理视频文件，用于解决跨域问题
    """
    if domain == "bilibili.com":
        max_retries = 3
        chunk_size = 256  # 减小 chunk size

        headers = {
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        if "range" in request.headers:
            headers["Range"] = request.headers["range"]

        async def stream_with_retry():
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                        async with client.stream("GET", url, headers=headers) as resp:
                            resp.raise_for_status()
                            async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                                yield chunk
                    return  # 如果成功完成，就退出函数
                except (httpx.NetworkError, httpx.TimeoutException, httpx.StreamClosed) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying: {str(e)}")
                    await asyncio.sleep(1)  # 在重试之前等待一秒

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    content_type = resp.headers.get('Content-Type', 'application/octet-stream')
                    resp_headers = {
                        "Accept-Ranges": "bytes",
                        "Content-Type": content_type,
                    }
                    if 'Content-Range' in resp.headers:
                        resp_headers['Content-Range'] = resp.headers['Content-Range']
                    if 'Content-Length' in resp.headers:
                        resp_headers['Content-Length'] = resp.headers['Content-Length']

                    return StreamingResponse(
                        stream_with_retry(),
                        status_code=resp.status_code,
                        headers=resp_headers
                    )
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error occurred: {exc.response.status_code} {exc.response.reason_phrase}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.reason_phrase)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    if domain == "javdb.com":
        try:
            async with httpx.AsyncClient() as client:
                # 设置请求头
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': 'https://missav.com/',
                    'Origin': 'https://missav.com'
                }

                # 获取内容
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get('content-type', '')

                # 如果是 m3u8 文件
                if url.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                    content_text = content.decode()
                    base_url = url.rsplit('/', 1)[0]

                    # 处理 m3u8 内容中的 URL
                    def replace_url(match):
                        path = match.group(1)
                        if path.startswith('http'):
                            full_url = path
                        else:
                            full_url = urljoin(base_url + '/', path)
                        return f"/api/channel-video/proxy?domain=javdb.com&url={full_url}"

                    # 替换所有视频分片文件路径（包括.ts和.jpeg）
                    content_text = re.sub(
                        r'([^"\n]+\.(ts|jpeg|jpg|m3u8)[^"\n]*)',
                        replace_url,
                        content_text
                    )

                    # 不再需要单独处理m3u8，因为上面的正则已经包含了
                    
                    return StreamingResponse(
                        iter([content_text.encode()]),
                        media_type='application/vnd.apple.mpegurl',
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'no-cache',
                        }
                    )

                # 修改处理视频分片的部分
                return StreamingResponse(
                    iter([content]),
                    media_type=content_type or 'application/octet-stream',  # 确��始终有content-type
                    headers={
                        'Access-Control-Allow-Origin': '*',
                        'Cache-Control': 'public, max-age=31536000',
                    }
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")




