"""Probe and extract audio tracks from a validated Telegram stream URL.

Requires ffprobe and ffmpeg on PATH. No user-supplied URL is passed to either tool.
"""
import asyncio
import json
import logging
import time
from urllib.parse import urljoin

from aiohttp import web

from Sujan.vars import Var

logger = logging.getLogger(__name__)
_probe_cache = {}
_probe_locks = {}
CACHE_SECONDS = 3600


def media_url(file_id, secure_hash):
    return urljoin(Var.URL, f"{secure_hash}{file_id}")


async def probe_audio_tracks(file_id, secure_hash):
    """Return ordered audio stream metadata; cache by validated file identity."""
    key = (file_id, secure_hash)
    cached = _probe_cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]
    lock = _probe_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _probe_cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            return cached[1]
        try:
            process = await asyncio.create_subprocess_exec(
                'ffprobe', '-v', 'error', '-probesize', '10000000',
                '-analyzeduration', '10000000', '-show_entries',
                'stream=index,codec_type,codec_name:stream_tags=language,title',
                '-of', 'json', media_url(file_id, secure_hash),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                output, errors = await asyncio.wait_for(process.communicate(), timeout=35)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                raise RuntimeError('Audio track detection timed out')
            if process.returncode != 0:
                raise RuntimeError(errors.decode(errors='replace')[:500])
            streams = json.loads(output).get('streams', [])
            tracks = []
            for stream in streams:
                if stream.get('codec_type') != 'audio':
                    continue
                tags = {k.lower(): v for k, v in stream.get('tags', {}).items()}
                tracks.append({
                    'index': len(tracks),
                    'language': str(tags.get('language', 'und'))[:32],
                    'title': str(tags.get('title', ''))[:100],
                    'codec': str(stream.get('codec_name', ''))[:32],
                })
            _probe_cache[key] = (time.monotonic(), tracks)
            if len(_probe_cache) > 256:
                oldest = min(_probe_cache, key=lambda k: _probe_cache[k][0])
                _probe_cache.pop(oldest, None)
            return tracks
        except FileNotFoundError:
            logger.warning('ffprobe is not installed; embedded audio detection unavailable')
            raise RuntimeError('Audio track detection requires ffprobe')
        finally:
            _probe_locks.pop(key, None)


async def stream_audio_track(request, file_id, secure_hash, track_count):
    """Transcode only a validated embedded audio stream to browser-playable MP3."""
    try:
        track = int(request.query.get('track', ''))
        start = float(request.query.get('start', '0'))
    except (ValueError, TypeError):
        raise web.HTTPBadRequest(text='Invalid track or start time')
    if track < 0 or track >= track_count or not 0 <= start <= 86400:
        raise web.HTTPBadRequest(text='Track or start time out of range')
    try:
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
            '-i', media_url(file_id, secure_hash), '-ss', str(start),
            '-map', f'0:a:{track}', '-vn', '-sn', '-dn',
            '-c:a', 'libmp3lame', '-b:a', '160k', '-f', 'mp3', 'pipe:1',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise web.HTTPServiceUnavailable(text='Audio switching requires ffmpeg')
    response = web.StreamResponse(status=200, headers={
        'Content-Type': 'audio/mpeg', 'Cache-Control': 'no-store',
        'Content-Disposition': 'inline',
    })
    try:
        await response.prepare(request)
        while True:
            chunk = await process.stdout.read(64 * 1024)
            if not chunk:
                break
            await response.write(chunk)
        await response.write_eof()
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()
    return response
