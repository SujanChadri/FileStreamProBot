import html
import json
import urllib.parse
import aiofiles
import aiohttp
import logging
from string import Template
from Sujan.vars import Var
from Sujan.bot import StreamBot
from Sujan.utils.human_readable import humanbytes
from Sujan.utils.file_properties import get_file_ids
from Sujan.server.exceptions import InvalidHash

async def render_page(id, secure_hash, audio_sources=None):
    try:
        file_data = await get_file_ids(StreamBot, int(Var.BIN_CHANNEL), int(id))

        if file_data.unique_id[:6] != secure_hash:
            logging.debug(f'link hash: {secure_hash} - {file_data.unique_id[:6]}')
            raise InvalidHash

        src = urllib.parse.urljoin(Var.URL, f'{secure_hash}{id}')
        tag = (file_data.mime_type or 'application/octet-stream').split('/')[0].strip()

        audio_sources = audio_sources or []
        audio_tracks = []
        for idx, entry in enumerate(audio_sources, start=1):
            if "|" in entry:
                label, audio_src = entry.split("|", 1)
                label = label.strip() or f"Alt Track {idx}"
                audio_src = audio_src.strip()
            else:
                label = f"Alt Track {idx}"
                audio_src = entry.strip()
            if audio_src:
                audio_tracks.append({"label": label, "src": audio_src})

        audio_sources_json = html.escape(json.dumps(audio_tracks))

        if tag in ('video', 'audio'):
            async with aiofiles.open('Sujan/template/req.html') as f:
                template = Template(await f.read())
            heading = f"{'Watch' if tag=='video' else 'Listen'} {file_data.file_name}"

            # Use safe_substitute instead of substitute
            # MX Player and VLC Player intent URLs are constructed dynamically in JavaScript
            # to prevent users from copying the direct video URL
            html_content = template.safe_substitute(
                heading=heading,
                filename=file_data.file_name,
                tag=tag,
                src=src,
                audio_sources=audio_sources_json,
                stream_key=f"{secure_hash}{id}"
            )

        else:
            async with aiofiles.open('Sujan/template/dl.html') as f:
                template = Template(await f.read())
            async with aiohttp.ClientSession() as session:
                async with session.get(src) as resp:
                    heading = f"Download {file_data.file_name}"
                    file_size = humanbytes(int(resp.headers.get('Content-Length', 0)))

                    html_content = template.safe_substitute(
                        heading=heading,
                        filename=file_data.file_name,
                        src=src,
                        filesize=file_size
                    )

        return html_content

    except Exception as e:
        logging.critical(f"Render error: {e}")
        return f"<h1>Internal Error while rendering page</h1><pre>{e}</pre>"
