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
from Sujan.vars import Var
from Sujan.server.audio_tracks import probe_audio_tracks, stream_audio_track


routes = web.RouteTableDef()

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
        audio_sources = []
        query_audio = request.rel_url.query.getall("audio", [])
        for entry in query_audio:
            if entry:
                audio_sources.append(entry)

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


@routes.get(r"/audio-tracks/{path:[a-zA-Z0-9_-]{6}\d+}")
async def audio_tracks_handler(request: web.Request):
    match = re.fullmatch(r"([a-zA-Z0-9_-]{6})(\d+)", request.match_info['path'])
    if not match:
        raise web.HTTPBadRequest(text='Invalid stream link')
    secure_hash, file_id = match.group(1), int(match.group(2))
    file_data = await get_audio_file(file_id, secure_hash)
    if not (file_data.mime_type or '').startswith('video/'):
        return web.json_response({'tracks': []})
    try:
        tracks = await probe_audio_tracks(file_id, secure_hash)
    except RuntimeError as error:
        logger_message = str(error)
        logging.warning('Audio detection failed: %s', logger_message)
        raise web.HTTPServiceUnavailable(text='Audio tracks could not be detected')
    return web.json_response({'tracks': tracks})


@routes.get(r"/audio-stream/{path:[a-zA-Z0-9_-]{6}\d+}")
async def audio_stream_handler(request: web.Request):
    match = re.fullmatch(r"([a-zA-Z0-9_-]{6})(\d+)", request.match_info['path'])
    if not match:
        raise web.HTTPBadRequest(text='Invalid stream link')
    secure_hash, file_id = match.group(1), int(match.group(2))
    file_data = await get_audio_file(file_id, secure_hash)
    if not (file_data.mime_type or '').startswith('video/'):
        raise web.HTTPBadRequest(text='Not a video')
    try:
        tracks = await probe_audio_tracks(file_id, secure_hash)
    except RuntimeError:
        raise web.HTTPServiceUnavailable(text='Audio tracks could not be detected')
    return await stream_audio_track(request, file_id, secure_hash, len(tracks))


async def get_audio_file(file_id, secure_hash):
    from Sujan.utils.file_properties import get_file_ids
    file_data = await get_file_ids(StreamBot, int(Var.BIN_CHANNEL), file_id)
    if not file_data or file_data.unique_id[:6] != secure_hash:
        raise web.HTTPNotFound(text='Stream not found')
    return file_data


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

class_cache = {}

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
