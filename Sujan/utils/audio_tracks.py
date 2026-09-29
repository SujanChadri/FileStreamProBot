# (c) Sujan
"""
Dual / Multi-Audio auto-detection.

Detects every audio track inside a media file that is being served by this
bot and maps its language tag to a friendly name (Japanese, Hindi, English,
Tamil, Telugu, Kannada, Malayalam, ...).

Detection order:
  1. ffprobe over the bot's own HTTP stream URL (reads only the header bytes)
  2. Filename heuristics  (e.g. "Dual Audio [Hindi+English]", "Tam Tel Hin")

Everything degrades gracefully: if ffprobe is missing or the probe fails,
the filename parser is used, and if that finds nothing we simply report a
single default track.
"""

import re
import json
import shutil
import asyncio
import logging

logger = logging.getLogger(__name__)

PROBE_TIMEOUT = 45          # seconds
_CACHE: dict = {}           # {(id, hash): [tracks]}
_CACHE_LIMIT = 512


# --------------------------------------------------------------------------
# Language tables
# --------------------------------------------------------------------------

# ISO-639-1 / 639-2 / 639-3 codes -> (Display name, flag)
LANGUAGE_CODES = {
    # Indian languages
    "hin": ("Hindi", "🇮🇳"), "hi": ("Hindi", "🇮🇳"),
    "tam": ("Tamil", "🇮🇳"), "ta": ("Tamil", "🇮🇳"),
    "tel": ("Telugu", "🇮🇳"), "te": ("Telugu", "🇮🇳"),
    "kan": ("Kannada", "🇮🇳"), "kn": ("Kannada", "🇮🇳"),
    "mal": ("Malayalam", "🇮🇳"), "ml": ("Malayalam", "🇮🇳"),
    "ben": ("Bengali", "🇮🇳"), "bn": ("Bengali", "🇮🇳"),
    "mar": ("Marathi", "🇮🇳"), "mr": ("Marathi", "🇮🇳"),
    "guj": ("Gujarati", "🇮🇳"), "gu": ("Gujarati", "🇮🇳"),
    "pan": ("Punjabi", "🇮🇳"), "pa": ("Punjabi", "🇮🇳"),
    "ori": ("Odia", "🇮🇳"), "ory": ("Odia", "🇮🇳"),
    "asm": ("Assamese", "🇮🇳"), "as": ("Assamese", "🇮🇳"),
    "urd": ("Urdu", "🇵🇰"), "ur": ("Urdu", "🇵🇰"),
    "nep": ("Nepali", "🇳🇵"), "ne": ("Nepali", "🇳🇵"),
    "sin": ("Sinhala", "🇱🇰"), "si": ("Sinhala", "🇱🇰"),
    # Asian
    "jpn": ("Japanese", "🇯🇵"), "ja": ("Japanese", "🇯🇵"), "jp": ("Japanese", "🇯🇵"),
    "kor": ("Korean", "🇰🇷"), "ko": ("Korean", "🇰🇷"),
    "zho": ("Chinese", "🇨🇳"), "chi": ("Chinese", "🇨🇳"), "zh": ("Chinese", "🇨🇳"),
    "cmn": ("Mandarin", "🇨🇳"), "yue": ("Cantonese", "🇭🇰"),
    "tha": ("Thai", "🇹🇭"), "th": ("Thai", "🇹🇭"),
    "vie": ("Vietnamese", "🇻🇳"), "vi": ("Vietnamese", "🇻🇳"),
    "ind": ("Indonesian", "🇮🇩"), "id": ("Indonesian", "🇮🇩"),
    "msa": ("Malay", "🇲🇾"), "may": ("Malay", "🇲🇾"), "ms": ("Malay", "🇲🇾"),
    "fil": ("Filipino", "🇵🇭"), "tgl": ("Tagalog", "🇵🇭"),
    # Western / others
    "eng": ("English", "🇬🇧"), "en": ("English", "🇬🇧"),
    "spa": ("Spanish", "🇪🇸"), "es": ("Spanish", "🇪🇸"),
    "fra": ("French", "🇫🇷"), "fre": ("French", "🇫🇷"), "fr": ("French", "🇫🇷"),
    "deu": ("German", "🇩🇪"), "ger": ("German", "🇩🇪"), "de": ("German", "🇩🇪"),
    "ita": ("Italian", "🇮🇹"), "it": ("Italian", "🇮🇹"),
    "por": ("Portuguese", "🇵🇹"), "pt": ("Portuguese", "🇵🇹"),
    "rus": ("Russian", "🇷🇺"), "ru": ("Russian", "🇷🇺"),
    "ara": ("Arabic", "🇸🇦"), "ar": ("Arabic", "🇸🇦"),
    "tur": ("Turkish", "🇹🇷"), "tr": ("Turkish", "🇹🇷"),
    "fas": ("Persian", "🇮🇷"), "per": ("Persian", "🇮🇷"), "fa": ("Persian", "🇮🇷"),
    "pol": ("Polish", "🇵🇱"), "nld": ("Dutch", "🇳🇱"), "dut": ("Dutch", "🇳🇱"),
    "ukr": ("Ukrainian", "🇺🇦"), "heb": ("Hebrew", "🇮🇱"),
    "swe": ("Swedish", "🇸🇪"), "nor": ("Norwegian", "🇳🇴"), "dan": ("Danish", "🇩🇰"),
    "fin": ("Finnish", "🇫🇮"), "ces": ("Czech", "🇨🇿"), "cze": ("Czech", "🇨🇿"),
    "hun": ("Hungarian", "🇭🇺"), "ell": ("Greek", "🇬🇷"), "gre": ("Greek", "🇬🇷"),
    "ron": ("Romanian", "🇷🇴"), "rum": ("Romanian", "🇷🇴"),
    "und": ("Unknown", "🎧"), "unk": ("Unknown", "🎧"), "mul": ("Multi", "🎧"),
}

# Words found in filenames / stream titles -> canonical language name
NAME_HINTS = {
    "hindi": "Hindi", "hin": "Hindi", "hnd": "Hindi",
    "tamil": "Tamil", "tam": "Tamil",
    "telugu": "Telugu", "tel": "Telugu", "tlg": "Telugu",
    "kannada": "Kannada", "kan": "Kannada", "kann": "Kannada",
    "malayalam": "Malayalam", "mal": "Malayalam", "mala": "Malayalam",
    "bengali": "Bengali", "beng": "Bengali",
    "marathi": "Marathi", "gujarati": "Gujarati", "punjabi": "Punjabi",
    "odia": "Odia", "assamese": "Assamese", "bhojpuri": "Bhojpuri",
    "urdu": "Urdu", "nepali": "Nepali", "sinhala": "Sinhala",
    "japanese": "Japanese", "jap": "Japanese", "jpn": "Japanese", "jp": "Japanese",
    "korean": "Korean", "kor": "Korean",
    "chinese": "Chinese", "mandarin": "Mandarin", "cantonese": "Cantonese",
    "thai": "Thai", "vietnamese": "Vietnamese", "indonesian": "Indonesian",
    "english": "English", "eng": "English",
    "spanish": "Spanish", "french": "French", "german": "German",
    "italian": "Italian", "portuguese": "Portuguese", "russian": "Russian",
    "arabic": "Arabic", "turkish": "Turkish", "persian": "Persian",
}

FLAG_BY_NAME = {name: flag for (name, flag) in LANGUAGE_CODES.values()}
FLAG_BY_NAME.setdefault("Bhojpuri", "🇮🇳")


def _friendly(code: str, title: str = "", index: int = 0):
    """Resolve a display name + flag from an ffprobe language code / title."""
    code = (code or "").strip().lower()
    if code in LANGUAGE_CODES:
        name, flag = LANGUAGE_CODES[code]
        if name != "Unknown":
            return name, flag

    blob = f"{title} {code}".lower()
    for word in re.findall(r"[a-z]+", blob):
        if word in NAME_HINTS:
            name = NAME_HINTS[word]
            return name, FLAG_BY_NAME.get(name, "🎧")

    if title.strip():
        return title.strip()[:40], "🎧"
    return f"Audio {index + 1}", "🎧"


# --------------------------------------------------------------------------
# Filename based detection (fallback)
# --------------------------------------------------------------------------

def detect_from_filename(file_name: str):
    """Guess audio languages from a release filename."""
    if not file_name:
        return []

    blob = re.sub(r"[\._\-\[\]\(\)\{\}\+,]", " ", file_name).lower()
    words = blob.split()

    found = []
    for word in words:
        name = NAME_HINTS.get(word)
        if name and name not in found:
            found.append(name)

    # Ignore false positives like "English Subs" only files
    if len(found) < 2 and not re.search(r"dual\s*audio|multi\s*audio", blob):
        return []

    tracks = []
    for idx, name in enumerate(found):
        tracks.append({
            "index": idx,
            "language": name,
            "label": f"{FLAG_BY_NAME.get(name, '🎧')} {name}",
            "codec": "",
            "channels": "",
            "default": idx == 0,
            "source": "filename",
        })
    return tracks


# --------------------------------------------------------------------------
# ffprobe based detection (accurate)
# --------------------------------------------------------------------------

def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


async def probe_audio_streams(url: str):
    """Run ffprobe against the stream URL and return the audio stream list."""
    if not ffprobe_available():
        logger.warning("ffprobe not installed - falling back to filename detection")
        return []

    cmd = [
        "ffprobe", "-hide_banner", "-loglevel", "error",
        "-analyzeduration", "12000000", "-probesize", "12000000",
        "-select_streams", "a",
        "-show_entries", "stream=index,codec_name,channels,disposition:stream_tags=language,title",
        "-print_format", "json",
        url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=PROBE_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            logger.warning("ffprobe timed out for %s", url)
            return []

        if proc.returncode != 0:
            logger.warning("ffprobe failed: %s", (stderr or b"").decode()[:300])
            return []

        data = json.loads(stdout.decode() or "{}")
        return data.get("streams", []) or []
    except Exception as exc:  # pragma: no cover
        logger.warning("ffprobe error: %s", exc)
        return []


def _build_tracks(streams):
    tracks = []
    for idx, stream in enumerate(streams):
        tags = stream.get("tags", {}) or {}
        language = tags.get("language") or tags.get("LANGUAGE") or ""
        title = tags.get("title") or tags.get("TITLE") or ""
        name, flag = _friendly(language, title, idx)

        channels = stream.get("channels")
        channel_txt = ""
        if channels == 1:
            channel_txt = "Mono"
        elif channels == 2:
            channel_txt = "Stereo"
        elif channels:
            channel_txt = f"{channels}ch"

        codec = (stream.get("codec_name") or "").upper()
        extra = " • ".join(x for x in (codec, channel_txt) if x)
        label = f"{flag} {name}" + (f"  ({extra})" if extra else "")

        tracks.append({
            "index": idx,
            "language": name,
            "label": label,
            "codec": codec,
            "channels": channel_txt,
            "title": title,
            "default": bool((stream.get("disposition") or {}).get("default")) or idx == 0,
            "source": "ffprobe",
        })
    return tracks


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

async def get_audio_tracks(stream_url: str, file_name: str = "", cache_key=None):
    """
    Return the detected audio tracks for a file.

    [] or a single item  -> normal single-audio file
    2+ items             -> dual / multi-audio file
    """
    if cache_key is not None and cache_key in _CACHE:
        return _CACHE[cache_key]

    tracks = _build_tracks(await probe_audio_streams(stream_url))

    if len(tracks) < 2:
        guessed = detect_from_filename(file_name)
        if len(guessed) > len(tracks):
            tracks = guessed

    if cache_key is not None:
        if len(_CACHE) > _CACHE_LIMIT:
            _CACHE.clear()
        _CACHE[cache_key] = tracks

    return tracks


def summarize(tracks):
    """Short human line for the Telegram message, e.g. 'Dual Audio: Hindi, English'."""
    if not tracks:
        return ""
    names = []
    for track in tracks:
        name = track.get("language") or "Audio"
        if name not in names:
            names.append(name)
    if len(tracks) == 1:
        return f"🔊 Aᴜᴅɪᴏ : {names[0]}"
    prefix = "Dᴜᴀʟ Aᴜᴅɪᴏ" if len(tracks) == 2 else "Mᴜʟᴛɪ Aᴜᴅɪᴏ"
    return f"🔊 {prefix} ({len(tracks)}) : " + ", ".join(names)
