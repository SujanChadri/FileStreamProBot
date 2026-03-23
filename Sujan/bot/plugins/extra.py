from Sujan.bot import StreamBot
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters
import time
import shutil, psutil
from utils_bot import *
from Sujan import StartTime
from Sujan.utils.database import Database
from Sujan.vars import Var

db = Database(Var.DATABASE_URL, Var.name)

START_TEXT = """ Your Telegram DC Is : `{}`  """

async def deny_if_banned(b, m):
    if await db.is_user_banned(m.from_user.id):
        await b.send_message(
            chat_id=m.chat.id,
            text="You are banned from using this bot. Contact support if you believe this is a mistake.",
            disable_web_page_preview=True
        )
        return True
    return False

@StreamBot.on_message(filters.command("maintainers"))
async def maintainers(b, m):
    if await deny_if_banned(b, m):
        return
    try:
        await b.send_message(chat_id=m.chat.id, text="HELLO", quote=True)
    except Exception as e:
        await b.send_message(
            chat_id=m.chat.id,
            text="I am made by [@Sujan_Ch](https://t.me/Sujan_BotZ)",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("👨‍💻 Owner", url="https://t.me/Sujan_Ch")
                    ]
                ]
            ),
            disable_web_page_preview=True
        )

            
         
@StreamBot.on_message(filters.command("subscribe"))
async def follow_user(b,m):
    if await deny_if_banned(b, m):
        return
    try:
       await b.send_message(chat_id=m.chat.id,text="HELLO",quote=True)
    except Exception:
                await b.send_message(
                    chat_id=m.chat.id,
                    text="<B>HERE'S THE SUBSCRIBE LINK</B>",
                    
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("Subscribe ❤️", url=f"https://t.me/Sujan_Ch")
                            ]
                        ]
                    ),
                    
                    disable_web_page_preview=True)
        

@StreamBot.on_message(filters.command("dc"))
async def start(bot, update):
    if await deny_if_banned(bot, update):
        return
    text = START_TEXT.format(update.from_user.dc_id)
    await update.reply_text(
        text=text,
        disable_web_page_preview=True,
        quote=True
    )
    
@StreamBot.on_message(filters.command("list"))
async def list(l, m):
    if await deny_if_banned(l, m):
        return
    LIST_MSG = "Hi! {} Here is a list of all my commands \n \n 1 . `start⚡️` \n 2. `help📚` \n 3. `login🔑` \n 4.`Subscribe ❤️` \n 5. `ping📡` \n 6. `status📊` \n 7. `DC` this tells your telegram dc \n 8. `maintainers😎` "
    await l.send_message(chat_id = m.chat.id,
        text = LIST_MSG.format(m.from_user.mention(style="md"))
        
    )
    
    
@StreamBot.on_message(filters.command("ping"))
async def ping(b, m):
    if await deny_if_banned(b, m):
        return
    start_t = time.time()
    ag = await m.reply_text("....")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await ag.edit(f"Pong!\n{time_taken_s:.3f} ms")
    
    
    
    
@StreamBot.on_message(filters.private & filters.command("status"))
async def stats(bot, update):
  if await deny_if_banned(bot, update):
    return
  currentTime = readable_time((time.time() - StartTime))
  total, used, free = shutil.disk_usage('.')
  total = get_readable_file_size(total)
  used = get_readable_file_size(used)
  free = get_readable_file_size(free)
  sent = get_readable_file_size(psutil.net_io_counters().bytes_sent)
  recv = get_readable_file_size(psutil.net_io_counters().bytes_recv)
  cpuUsage = psutil.cpu_percent(interval=0.5)
  memory = psutil.virtual_memory().percent
  disk = psutil.disk_usage('/').percent
  botstats = f'<b>Bot Uptime:</b> {currentTime}\n' \
            f'<b>Total disk space:</b> {total}\n' \
            f'<b>Used:</b> {used}  ' \
            f'<b>Free:</b> {free}\n\n' \
            f'📊Data Usage📊\n<b>Upload:</b> {sent}\n' \
            f'<b>Down:</b> {recv}\n\n' \
            f'<b>CPU:</b> {cpuUsage}% ' \
            f'<b>RAM:</b> {memory}% ' \
            f'<b>Disk:</b> {disk}%'
  await update.reply_text(botstats)
