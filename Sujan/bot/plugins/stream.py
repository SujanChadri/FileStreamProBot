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

# Store messages to delete after cooldown
_cooldown_messages = {}

# Queue for sequential processing per user
_user_queues = {}
_user_locks = {}

# Store queue messages to delete after processing
_user_queue_messages = {}


def _check_file_rate_limit(user_id: int):
    """Check if user has exceeded rate limit and add current event if not"""
    now = time.monotonic()
    window_start = now - FILE_RATE_WINDOW_SECONDS
    events = _user_file_events[user_id]
    
    # Clean old events
    while events and events[0] < window_start:
        events.popleft()
    
    # Check if limit exceeded
    if len(events) >= FILE_RATE_LIMIT:
        retry_after = max(0, int(FILE_RATE_WINDOW_SECONDS - (now - events[0])))
        return True, retry_after
    
    # Add current event
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


async def countdown_timer(c: Client, user_id: int, chat_id: int, alert_message: Message, user_file_message: Message = None, initial_retry_after: int = 0):
    """Handle countdown timer with live updates and delete messages when cooldown finishes"""
    remaining = initial_retry_after
    
    # Countdown loop - update every 5 seconds
    while remaining > 0:
        await asyncio.sleep(5)
        remaining = _get_remaining_cooldown(user_id)
        
        if remaining <= 0:
            break
        
        # Update the alert message with remaining time
        try:
            await alert_message.edit_text(
                f"⚠️ **Rᴀᴛᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!**\n\n"
                f"Oɴʟʏ {FILE_RATE_LIMIT} ꜰɪʟᴇꜱ ᴄᴀɴ ʙᴇ ꜱᴇɴᴛ ᴘᴇʀ ᴍɪɴᴜᴛᴇ.\n\n"
                f"Pʟᴇᴀꜱᴇ ᴡᴀɪᴛ **{remaining} ꜱᴇᴄᴏɴᴅꜱ** ᴛᴏ ꜱᴇɴᴅ ᴀɴᴏᴛʜᴇʀ ꜰɪʟᴇ."
            )
        except Exception:
            # Message might be deleted, stop countdown
            break
    
    # Cooldown finished - delete the alert message first
    try:
        await alert_message.delete()
    except Exception:
        pass
    
    # Delete the user's file message
    try:
        if user_file_message:
            await user_file_message.delete()
    except Exception:
        pass
    
    # ✅ Send new completion message below (not edit)
    try:
        await c.send_message(
            chat_id=chat_id,
            text=f"✅ **Rᴀᴛᴇ ʟɪᴍɪᴛ ꜰɪɴɪꜱʜᴇᴅ!**\n\n"
                 f"Yᴏᴜ ᴄᴀɴ ɴᴏᴡ ꜱᴇɴᴅ ꜰɪʟᴇꜱ ᴀɢᴀɪɴ. 😊"
        )
    except Exception:
        pass
    
    # Clean up stored messages
    if user_id in _cooldown_messages:
        del _cooldown_messages[user_id]
    
    # Remove from active countdowns
    if user_id in _active_countdowns:
        del _active_countdowns[user_id]


async def cache_channel(c: Client):
    """Cache BIN_CHANNEL - simplified for bots (get_dialogs not available)"""
    global _channel_cached
    
    if _channel_cached:
        return
    
    # Bots can't use get_dialogs(), just verify BIN_CHANNEL is accessible
    try:
        chat = await c.get_chat(Var.BIN_CHANNEL)
        print(f"BIN_CHANNEL verified: {chat.title if chat else 'Unknown'}")
        _channel_cached = True
    except Exception as e:
        print(f"Cache warning: {e}")
        _channel_cached = True  # Set anyway to prevent repeated attempts


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


async def process_file(c: Client, m: Message, queue_msg: Message = None):
    """Process a single file - generate links and send to user"""
    try:
        log_msg = await m.copy(chat_id=Var.BIN_CHANNEL)
        #stream_link = f"{Var.URL}watch/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        stream_link = f"https://movies4u.hubstream.site/?url={Var.URL}dl/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        online_link = f"{Var.URL}dl/{str(log_msg.id)}?hash={get_hash(log_msg)}"
        
        msg_text = """<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n\n<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <code>{}</code>\n\n<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <code>{}</code>\n\n<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n\n<b> 🖥WATCH  :</b> <code>{}</code>\n\n<b>🚸 Nᴏᴛᴇ : Link Will Expire In 24 Hours</b>"""
        
        await log_msg.reply_text(
            text=f"**RᴇQᴜᴇꜱᴛᴇᴅ ʙʏ :** [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n**Uꜱᴇʀ ɪᴅ :** `{m.from_user.id}`\n**Stream ʟɪɴᴋ :** {stream_link}",
            disable_web_page_preview=True,
            quote=True
        )
        
        # Send the generated link message
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
        
        # ✅ Delete the original file message after links are generated
        try:
            await m.delete()
        except Exception as e:
            print(f"Could not delete file message: {e}")
        
        # ✅ Delete queue message if exists
        if queue_msg:
            try:
                await queue_msg.delete()
            except Exception:
                pass
        
    except FloodWait as e:
        print(f"Sleeping for {str(e.x)}s")
        await asyncio.sleep(e.x)
        await c.send_message(
            chat_id=Var.BIN_CHANNEL,
            text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.x)}s from [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(m.from_user.id)}`",
            disable_web_page_preview=True
        )


async def queue_processor(c: Client, user_id: int):
    """Background task to process files sequentially for a specific user"""
    while True:
        queue_msg = None
        m = None
        
        try:
            # Get next file from queue
            m, queue_msg = await _user_queues[user_id].get()
            
            try:
                # Process the file
                await process_file(c, m, queue_msg)
            except Exception as e:
                print(f"Error processing file for user {user_id}: {e}")
            finally:
                # Mark task as done
                _user_queues[user_id].task_done()
                
                # Small delay between processing files to avoid flooding
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Queue processor error for user {user_id}: {e}")
            await asyncio.sleep(1)
        
        # If queue is empty, clean up
        if _user_queues[user_id].empty():
            del _user_queues[user_id]
            if user_id in _user_locks:
                del _user_locks[user_id]
            # Clean up queue messages dict
            if user_id in _user_queue_messages:
                del _user_queue_messages[user_id]
            break


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
    user_id = m.from_user.id
    
    if await db.is_user_banned(user_id):
        await m.reply_text(
            "🚫 Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴜꜱɪɴɢ ᴛʜɪꜱ ʙᴏᴛ.\n\n🔞 Tʜɪꜱ ᴀᴄᴛɪᴏɴ ᴡᴀꜱ ᴛᴀᴋᴇɴ ʙᴇᴄᴀᴜꜱᴇ ʏᴏᴜ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴏʀ ᴀᴛᴛᴇᴍᴘᴛᴇᴅ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ 18+ ᴄᴏɴᴛᴇɴᴛ ᴜꜱɪɴɢ ᴛʜᴇ ʙᴏᴛ.\n\n📩 Iꜰ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪꜱ ʙᴀɴ ᴡᴀꜱ ɪꜱꜱᴜᴇᴅ ʙʏ ᴍɪꜱᴛᴀᴋᴇ, ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ᴛᴇᴀᴍ ꜰᴏʀ ᴀꜱꜱɪꜱᴛᴀɴᴄᴇ @Sujan_Ch."
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

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id)
        await c.send_message(
            Var.BIN_CHANNEL,
            f"New User Joined! : \n\n Name : [{m.from_user.first_name}](tg://user?id={user_id}) Started Your Bot!!"
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
    
    # ✅ Check rate limit BEFORE adding to queue
    limited, retry_after = _check_file_rate_limit(user_id)
    
    if limited:
        # Cancel any existing countdown for this user
        if user_id in _active_countdowns:
            try:
                _active_countdowns[user_id].cancel()
            except Exception:
                pass
        
        # Send alert message with initial retry_after
        alert_msg = await m.reply_text(
            f"⚠️ **Rᴀᴛᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ!**\n\n"
            f"Oɴʟʏ {FILE_RATE_LIMIT} ꜰɪʟᴇꜱ ᴄᴀɴ ʙᴇ ꜱᴇɴᴛ ᴘᴇʀ ᴍɪɴᴜᴛᴇ.\n\n"
            f"Pʟᴇᴀꜱᴇ ᴡᴀɪᴛ **{retry_after} ꜱᴇᴄᴏɴᴅꜱ** ᴛᴏ ꜱᴇɴᴅ ᴀɴᴏᴛʜᴇʀ ꜰɪʟᴇ.",
            quote=True
        )
        
        # Store messages for deletion after cooldown
        _cooldown_messages[user_id] = {
            'alert': alert_msg,
            'file': m
        }
        
        # Start countdown timer with live updates
        task = asyncio.create_task(countdown_timer(c, user_id, m.chat.id, alert_msg, m, retry_after))
        _active_countdowns[user_id] = task
        return
    
    # Cancel any existing countdown since user is now allowed to send
    if user_id in _active_countdowns:
        try:
            _active_countdowns[user_id].cancel()
        except Exception:
            pass
        del _active_countdowns[user_id]
    
    # Clean up any stored cooldown messages
    if user_id in _cooldown_messages:
        del _cooldown_messages[user_id]
    
    # ✅ Add file to user's queue for sequential processing
    if user_id not in _user_queues:
        _user_queues[user_id] = asyncio.Queue()
        # Start queue processor for this user
        asyncio.create_task(queue_processor(c, user_id))
    
    # Send queue position if there's more than 1 file pending
    queue_size = _user_queues[user_id].qsize()
    queue_msg = None
    
    if queue_size > 0:  # If there are pending files, show queue position
        try:
            queue_msg = await m.reply_text(
                f"⏳ **Qᴜᴇᴜᴇᴅ!**\n\n"
                f"Yᴏᴜʀ ꜰɪʟᴇ ɪꜱ #{queue_size + 1} ɪɴ Qᴜᴇᴜᴇ.\n\n"
                f"Pʀᴏᴄᴇꜱꜱɪɴɢ ꜰɪʟᴇꜱ ꜱᴇQᴜᴇɴᴛɪᴀʟʟʏ...",
                quote=True
            )
        except Exception:
            pass
    
    # Add file to queue (store both message and queue_msg)
    await _user_queues[user_id].put((m, queue_msg))


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
