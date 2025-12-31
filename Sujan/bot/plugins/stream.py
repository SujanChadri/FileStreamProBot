# (c) Sujan
import os
import asyncio
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


async def cache_channel(c: Client):
    """Cache BIN_CHANNEL by loading all dialogs"""
    global _channel_cached
    
    if _channel_cached:
        return
    
    try:
        # This loads all chats into Pyrogram's cache
        async for dialog in c.get_dialogs():
            if dialog.chat.id == Var.BIN_CHANNEL:
                print(f"✅ BIN_CHANNEL cached: {dialog.chat.title}")
                break
        _channel_cached = True
    except Exception as e:
        print(f"Cache error: {e}")
        _channel_cached = True  # Don't retry on error


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
    if MY_PASS:
        check_pass = await pass_db.get_user_pass(m.chat.id)
        if check_pass == None:
            await m.reply_text("Login first using /login cmd \n don't know the pass? request it from the Developer")
            return
        if check_pass != MY_PASS:
            await pass_db.delete_user(m.chat.id)
            return

    # ✅ Cache channel on first use
    await cache_channel(c)

    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await c.send_message(
            Var.BIN_CHANNEL,
            f"New User Joined! : \n\n Name : [{m.from_user.first_name}](tg://user?id={m.from_user.id}) Started Your Bot!!"
        )

    if Var.UPDATES_CHANNEL != "None":
        try:
            user = await c.get_chat_member(Var.UPDATES_CHANNEL, m.chat.id)
            if user.status == "kicked":
                await c.send_message(
                    chat_id=m.chat.id,
                    text="You are banned!\n\n  **Cᴏɴᴛᴀᴄᴛ Support [Support](https://t.me/Sujan_Ch) They Wɪʟʟ Hᴇʟᴘ Yᴏᴜ**",
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
            await c.send_message(
                chat_id=m.chat.id,
                text="""**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!""",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("Jᴏɪɴ ɴᴏᴡ 🔓", url=f"https://t.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
            )
            return
        except Exception as e:
            await m.reply_text(e)
            await c.send_message(
                chat_id=m.chat.id,
                text="**Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ Wʀᴏɴɢ. Cᴏɴᴛᴀᴄᴛ ᴍʏ Support** [Support](https://t.me/Sujan_Ch)",
                disable_web_page_preview=True
            )
            return
    ban_chk = await db.is_banned(int(m.from_user.id))
    if ban_chk == True:
        return await m.reply(Var.BAN_ALERT)
    try:
        log_msg = await m.forward(chat_id=Var.BIN_CHANNEL)
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
    
    ban_chk = await db.is_banned(int(broadcast.chat.id))
    if (int(broadcast.chat.id) in Var.BANNED_CHANNELS) or (ban_chk == True):
        await bot.leave_chat(broadcast.chat.id)
        return
    
    try:
        # ✅ Cache channel
        await cache_channel(bot)
        
        log_msg = await broadcast.forward(chat_id=Var.BIN_CHANNEL)
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
