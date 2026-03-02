# (c) Sujan
import os
import asyncio
import time
from collections import defaultdict, deque
from asyncio import TimeoutError
from Sujan.bot import StreamBot
from Sujan.utils.database import Database
from Sujan.utils.human_readable import humanbytes
from Sujan.vars import Var
from urllib.parse import quote_plus
from pyrogram import filters, Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from Sujan.utils.file_properties import get_name, get_hash, get_media_file_size

db = Database(Var.DATABASE_URL, Var.name)

MY_PASS = os.environ.get("MY_PASS", None)
pass_dict = {}
pass_db = Database(Var.DATABASE_URL, "ag_passwords")

# ✅ Simple flag
_channel_cached = False
FILE_RATE_LIMIT = 3
FILE_RATE_WINDOW_SECONDS = 60
_user_file_events = defaultdict(deque)

# Store active countdown tasks for users
_active_countdowns = {}


def _check_file_rate_limit(user_id: int):
    now = time.monotonic()
    window_start = now - FILE_RATE_WINDOW_SECONDS
    events = _user_file_events[user_id]
    while events and events[0] < window_start:
        events.popleft()
    if len(events) >= FILE_RATE_LIMIT:
        retry_after = max(0, int(FILE_RATE_WINDOW_SECONDS - (now - events[0])))
        return True, retry_after
    events.append(now)
    return False, 0


def _get_remaining_cooldown(user_id: int):
    """Get remaining cooldown time for a user"""
    now = time.monotonic()
    window_start = now - FILE_RATE_WINDOW_SECONDS
    events = _user_file_events[user_id]
    while events and events[0] < window_start:
        events.popleft()
    if len(events) >= FILE_RATE_LIMIT:
        return max(0, int(FILE_RATE_WINDOW_SECONDS - (now - events[0])))
    return 0


async def countdown_timer(c: Client, user_id: int, chat_id: int, file_message: Message):
    """Handle countdown timer and notify when cooldown finishes"""
    remaining = _get_remaining_cooldown(user_id)
    
    if remaining <= 0:
        return
    
    # Send initial countdown message as reply to the file (below the file)
    countdown_msg = await file_message.reply_text(
        f"⏳ **Cooldown Active**\n\n"
        f"Sᴏʀʀʏ ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ꜱᴇɴᴅ {FILE_RATE_LIMIT} ꜰɪʟᴇꜱ ᴘᴇʀ ᴍɪɴᴜᴛᴇ.\n"
        f"Sᴇɴᴅ ꜰɪʟᴇꜱ ᴀɢᴀɪɴ ɪɴ {remaining}s."
    )
    
    # Countdown loop - update every 5 seconds to avoid rate limits
    while remaining > 0:
        await asyncio.sleep(5)
        remaining = _get_remaining_cooldown(user_id)
        
        if remaining <= 0:
            break
            
        try:
            await countdown_msg.edit_text(
                f"⏳ **Cᴏᴏʟᴅᴏᴡɴ Aᴄᴛɪᴠᴇ**\n\n"
                f"Sᴏʀʀʏ ʏᴏᴜ ᴄᴀɴ ᴏɴʟʏ ꜱᴇɴᴅ {FILE_RATE_LIMIT} ꜰɪʟᴇꜱ ᴘᴇʀ ᴍɪɴᴜᴛᴇ.\n"
                f"Sᴇɴᴅ ꜰɪʟᴇꜱ ᴀɢᴀɪɴ ɪɴ {remaining}s."
            )
        except Exception:
            # Message might be deleted, stop countdown
            break
    
    # Cooldown finished - update message
    try:
        await countdown_msg.edit_text(
            f"🎉"
        )
    except Exception:
        pass
    
    # Send a new message to notify user they can send files again
    try:
        await c.send_message(
            chat_id=chat_id,
            text="🎉 **Cᴏᴏʟᴅᴏᴡɴ Fɪɴɪꜱʜᴇᴅ!**\n\n"
                 "✅ Yᴏᴜ ᴄᴀɴ ɴᴏᴡ ꜱᴇɴᴅ 3 ꜰɪʟᴇꜱ ᴀɢᴀɪɴ."
        )
    except Exception:
        pass
    
    # Remove from active countdowns
    if user_id in _active_countdowns:
        del _active_countdowns[user_id]


async def cache_channel(c: Client):
    """Cache BIN_CHANNEL by loading all dialogs"""
    global _channel_cached
    
    if _channel_cached:
        return
    
    try:
        async for dialog in c.get_dialogs():
            if dialog.chat.id == Var.BIN_CHANNEL:
                print(f"BIN_CHANNEL cached: {dialog.chat.title}")
                break
        _channel_cached = True
    except Exception as e:
        print(f"Cache error: {e}")
        _channel_cached = True


async def check_user_in_update_channels(c: Client, user_id: int):
    """
    Check if user is a member of all required update channels.
    Returns: (is_member: bool, not_joined_channels: list, is_banned: bool)
    """
    update_channels = Var.get_update_channels()
    
    # If no update channels configured, allow access
    if not update_channels:
        return True, [], False
    
    not_joined = []
    is_banned = False
    
    for channel in update_channels:
        try:
            user = await c.get_chat_member(channel, user_id)
            if user.status == "kicked":
                is_banned = True
                break
        except UserNotParticipant:
            not_joined.append(channel)
        except Exception as e:
            print(f"Error checking channel {channel}: {e}")
            not_joined.append(channel)
    
    is_member = not is_banned and len(not_joined) == 0
    return is_member, not_joined, is_banned


def get_join_channels_markup(not_joined_channels):
    """Generate inline keyboard markup for channels user needs to join"""
    buttons = []

    for channel in not_joined_channels:
        clean_channel = channel.lstrip('@')
        buttons.append([
            InlineKeyboardButton(
                f"Jᴏɪɴ {clean_channel} 🔓",
                url=f"https://t.me/{clean_channel}"
            )
        ])

    # Add "I've Joined" / "Refresh" button
    buttons.append([
        InlineKeyboardButton(
            "✅ I've Joined",
            callback_data="check_join"
        )
    ])

    return InlineKeyboardMarkup(buttons)


@StreamBot.on_message((filters.regex("login🔑") | filters.command("login")), group=4)
async def login_handler(c: Client, m: Message):
    try:
        try:
            ag = await m.reply_text(
                "Now send me password.\n\n If You don't know check the MY_PASS Variable in heroku \n\n(You can use /cancel command to cancel the process)"
            )
            _text = await c.listen(m.chat.id, filters=filters.text, timeout=90)
            if _text.text:
                textp = _text.text
                if textp == "/cancel":
                    await ag.edit("Process Cancelled Successfully")
                    return
            else:
                return
        except TimeoutError:
            await ag.edit("I can't wait more for password, try again")
            return

        if textp == MY_PASS:
            await pass_db.add_user_pass(m.chat.id, textp)
            ag_text = "yeah! you entered the password correctly"
        else:
            ag_text = "Wrong password, try again"

        await ag.edit(ag_text)
    except Exception as e:
        print(e)


@StreamBot.on_message((filters.private) & (filters.document | filters.video | filters.audio | filters.photo), group=4)
async def private_receive_handler(c: Client, m: Message):
    if await db.is_user_banned(m.from_user.id):
        await m.reply_text(
            "You are banned from using this bot. Contact support if you believe this is a mistake."
        )
        return
    if MY_PASS:
        check_pass = await pass_db.get_user_pass(m.chat.id)
        if check_pass == None:
            await m.reply_text("Login first using /login cmd \n don't know the pass? request it from the Developer")
            return
        if check_pass != MY_PASS:
            await pass_db.delete_user(m.chat.id)
            return

    await cache_channel(c)

    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await c.send_message(
            Var.BIN_CHANNEL,
            f"New User Joined! : \n\n Name : [{m.from_user.first_name}](tg://user?id={m.from_user.id}) Started Your Bot!!"
        )

    # Check multiple update channels
    update_channels = Var.get_update_channels()
    if update_channels:
        is_member, not_joined, is_banned = await check_user_in_update_channels(c, m.chat.id)
        
        if is_banned:
            await c.send_message(
                chat_id=m.chat.id,
                text="You are banned!\n\n  **Cᴏɴᴛᴀᴄᴛ Support [Support](https://t.me/Sujan_Ch) They Wɪʟʟ Hᴇʟᴘ Yᴏᴜ**",
                disable_web_page_preview=True
            )
            return
        
        if not_joined:
            channel_text = "Cʜᴀɴɴᴇʟs" if len(not_joined) > 1 else "Cʜᴀɴɴᴇʟ"
            await c.send_message(
                chat_id=m.chat.id,
                text=f"**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs {channel_text} To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!\n\n**Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ:**",
                reply_markup=get_join_channels_markup(not_joined),
            )
            return
    
    # Check rate limit
    limited, retry_after = _check_file_rate_limit(m.from_user.id)
    if limited:
        # Cancel any existing countdown for this user
        if m.from_user.id in _active_countdowns:
            try:
                await _active_countdowns[m.from_user.id].delete()
            except Exception:
                pass
        
        # Start countdown timer - message will be below the file (as reply)
        task = asyncio.create_task(countdown_timer(c, m.from_user.id, m.chat.id, m))
        _active_countdowns[m.from_user.id] = task
        return
    
    # Cancel any active countdown if user is now allowed
    if m.from_user.id in _active_countdowns:
        try:
            del _active_countdowns[m.from_user.id]
        except Exception:
            pass
    
    try:
        log_msg = await m.copy(chat_id=Var.BIN_CHANNEL)
        stream_link = f"{Var.URL}watch/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        online_link = f"{Var.URL}dl/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        
        msg_text = """<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n\n<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <code>{}</code>\n\n<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n\n<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n\n<b> 🖥WATCH  :</b> <code>{}</code>\n\n<b>🚸 Nᴏᴛᴇ : Link Will Expire In 24 Hours</b>"""
        
        await log_msg.reply_text(
            text=f"**RᴇQᴜᴇꜱᴛᴇᴅ ʙʏ :** [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n**Uꜱᴇʀ ɪᴅ :** `{m.from_user.id}`\n**Stream ʟɪɴᴋ :** {stream_link}",
            disable_web_page_preview=True,
            quote=True
        )
        await m.reply_text(
            text=msg_text.format(get_name(log_msg), humanbytes(get_media_file_size(m)), online_link, stream_link),
            quote=True,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Stream 🖥", url=stream_link),
                        InlineKeyboardButton('Download 📥', url=online_link)
                    ]
                ]
            )
        )
    except FloodWait as e:
        print(f"Sleeping for {str(e.x)}s")
        await asyncio.sleep(e.x)
        await c.send_message(
            chat_id=Var.BIN_CHANNEL,
            text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.x)}s from [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(m.from_user.id)}`",
            disable_web_page_preview=True
        )


@StreamBot.on_message(filters.channel & ~filters.group & (filters.document | filters.video | filters.photo) & ~filters.forwarded, group=-1)
async def channel_receive_handler(bot, broadcast):
    if MY_PASS:
        check_pass = await pass_db.get_user_pass(broadcast.chat.id)
        if check_pass == None:
            await broadcast.reply_text("Login first using /login cmd \n don't know the pass? request it from developer!")
            return
        if check_pass != MY_PASS:
            await broadcast.reply_text("Wrong password, login again")
            await pass_db.delete_user(broadcast.chat.id)
            return
    
    if int(broadcast.chat.id) in Var.BANNED_CHANNELS:
        await bot.leave_chat(broadcast.chat.id)
        return
    
    try:
        await cache_channel(bot)
        
        log_msg = await broadcast.copy(chat_id=Var.BIN_CHANNEL)
        stream_link = f"{Var.URL}watch/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        online_link = f"{Var.URL}dl/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        
        await log_msg.reply_text(
            text=f"**Channel Name:** `{broadcast.chat.title}`\n**CHANNEL ID:** `{broadcast.chat.id}`\n**Rᴇǫᴜᴇsᴛ ᴜʀʟ:** {stream_link}",
            quote=True
        )
        await bot.edit_message_reply_markup(
            chat_id=broadcast.chat.id,
            message_id=broadcast.id,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🖥 Stream ", url=stream_link),
                        InlineKeyboardButton('Download 📥', url=online_link)
                    ]
                ]
            )
        )
    except FloodWait as w:
        print(f"Sleeping for {str(w.x)}s")
        await asyncio.sleep(w.x)
        await bot.send_message(
            chat_id=Var.BIN_CHANNEL,
            text=f"GOT FLOODWAIT OF {str(w.x)}s FROM {broadcast.chat.title}\n\n**CHANNEL ID:** `{str(broadcast.chat.id)}`",
            disable_web_page_preview=True
        )
    except Exception as e:
        await bot.send_message(
            chat_id=Var.BIN_CHANNEL,
            text=f"**#ERROR_TRACKEBACK:** `{e}`",
            disable_web_page_preview=True
        )
        print(f"Can't Edit Broadcast Message!\nError: {e}")
