# Taken from megadlbot_oss <https://github.com/eyaadh/megadlbot_oss/blob/master/mega/webserver/routes.py>
# Thanks to Eyaadh <https://github.com/eyaadh>

import re
import time
import math
import logging
import secrets
import mimetypes
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from Sujan.bot import multi_clients, work_loads, StreamBot
from Sujan.server.exceptions import FIleNotFound, InvalidHash
from Sujan import StartTime, __version__
from ..utils.time_format import get_readable_time
from ..utils.custom_dl import ByteStreamer
from Sujan.utils.render_template import render_page
from Sujan.utils.audio_tracks import get_audio_tracks, ffprobe_available
from Sujan.vars import Var
import asyncio
import urllib.parse


routes = web.RouteTableDef()

class_cache = {}

@routes.get("/", allow_head=True)
async def root_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + StreamBot.username,
            "connected_bots": len(multi_clients),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": __version__,
        }
    )


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]

        # Ignore favicon.ico
        if path.lower() == "favicon.ico":
            return web.Response(status=204)

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            # fallback pattern
            match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not match:
                logging.warning(f"Invalid path format: {path}")
                raise web.HTTPBadRequest(text="Invalid URL format")
            id = int(match.group(1))
            secure_hash = request.rel_url.query.get("hash")

        # Optional manually supplied extra audio sources: ?audio=Label|https://...
        audio_sources = [a for a in request.rel_url.query.getall("audio", []) if a]

        html = await render_page(id, secure_hash, audio_sources=audio_sources)
        return web.Response(text=html, content_type='text/html')
    
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError) as e:
        logging.warning(f"Connection error: {e}")
        return web.Response(text="Connection error while rendering page", status=500)
    except Exception as e:
        logging.critical(e.with_traceback(None))
        return web.Response(text=f"Internal server error: {e}", status=500)


async def _resolve_file(id: int, secure_hash: str):
    """Validate the hash and return (file_id_obj, direct_stream_url)."""
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect

    file_id = await tg_connect.get_file_properties(id)
    if file_id.unique_id[:6] != secure_hash:
        raise InvalidHash

    stream_url = urllib.parse.urljoin(Var.URL, f"{secure_hash}{id}")
    return file_id, stream_url


@routes.get(r"/api/audio/{id:\d+}", allow_head=True)
async def audio_tracks_handler(request: web.Request):
    """Auto-detected audio tracks (Japanese / Hindi / English / Tamil / Telugu / Kannada / Malayalam ...)."""
    try:
        id = int(request.match_info["id"])
        secure_hash = request.rel_url.query.get("hash", "")

        file_id, stream_url = await _resolve_file(id, secure_hash)

        tracks = await get_audio_tracks(
            stream_url,
            file_name=getattr(file_id, "file_name", "") or "",
            cache_key=(id, secure_hash),
        )

        for track in tracks:
            track["src"] = f"{Var.URL}track/{track['index']}/{secure_hash}{id}"

        return web.json_response({
            "ok": True,
            "file_name": getattr(file_id, "file_name", "") or "",
            "multi_audio": len(tracks) > 1,
            "count": len(tracks),
            "ffprobe": ffprobe_available(),
            "tracks": tracks,
        })
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except Exception as e:
        logging.warning(f"Audio detection failed: {e}")
        return web.json_response({"ok": False, "tracks": [], "error": str(e)}, status=200)


@routes.get(r"/track/{track:\d+}/{path:\S+}", allow_head=True)
async def audio_track_stream_handler(request: web.Request):
    """
    Re-mux the file on the fly with only the selected audio track.
    Used by browsers that cannot switch embedded audio tracks themselves.
    """
    ffmpeg_proc = None
    try:
        track_index = int(request.match_info["track"])
        path = request.match_info["path"]

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash, id = match.group(1), int(match.group(2))
        else:
            match = re.search(r"(\d+)", path)
            if not match:
                raise web.HTTPBadRequest(text="Invalid URL format")
            id = int(match.group(1))
            secure_hash = request.rel_url.query.get("hash", "")

        file_id, stream_url = await _resolve_file(id, secure_hash)

        if not ffprobe_available():
            raise web.HTTPServiceUnavailable(text="ffmpeg/ffprobe is not installed on the server")

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", stream_url,
            "-map", "0:v:0?", "-map", f"0:a:{track_index}?",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4", "pipe:1",
        ]

        ffmpeg_proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "video/mp4",
                "Cache-Control": "no-store",
                "Content-Disposition": f'inline; filename="track{track_index}.mp4"',
            },
        )
        await response.prepare(request)

        while True:
            chunk = await ffmpeg_proc.stdout.read(256 * 1024)
            if not chunk:
                break
            await response.write(chunk)

        await response.write_eof()
        return response

    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (ConnectionResetError, asyncio.CancelledError):
        logging.debug("Audio track stream closed by client")
        return web.Response(status=499)
    except web.HTTPException:
        raise
    except Exception as e:
        logging.warning(f"Audio track stream error: {e}")
        return web.Response(text=f"Audio track error: {e}", status=500)
    finally:
        if ffmpeg_proc and ffmpeg_proc.returncode is None:
            try:
                ffmpeg_proc.kill()
            except Exception:
                pass


@routes.get(r"/{path:\S+}", allow_head=True)
async def generic_stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]

        # Ignore favicon.ico
        if path.lower() == "favicon.ico":
            return web.Response(status=204)

        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            match = re.search(r"(\d+)(?:\/\S+)?", path)
            if not match:
                logging.warning(f"Invalid path format: {path}")
                raise web.HTTPBadRequest(text="Invalid URL format")
            id = int(match.group(1))
            secure_hash = request.rel_url.query.get("hash")

        return await media_streamer(request, id, secure_hash)

    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError) as e:
        logging.warning(f"Connection error: {e}")
        return web.Response(text="Connection error while streaming media", status=500)
    except Exception as e:
        logging.critical(e.with_traceback(None))
        return web.Response(text=f"Internal server error: {e}", status=500)

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if Var.MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )
