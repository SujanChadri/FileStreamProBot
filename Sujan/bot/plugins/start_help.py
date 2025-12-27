# (c) Sujan
from Sujan.bot import StreamBot
from Sujan.vars import Var
import logging
logger = logging.getLogger(__name__)
from Sujan.bot.plugins.stream import MY_PASS
from Sujan.utils.human_readable import humanbytes
from Sujan.utils.database import Database
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from Sujan.utils.file_properties import get_name, get_hash, get_media_file_size
db = Database(Var.DATABASE_URL, Var.name)
from pyrogram.types import ReplyKeyboardMarkup

if MY_PASS:
            buttonz=ReplyKeyboardMarkup(
            [
                ["start⚡️","help📚","login🔑","DC"],
                ["Subscribe ❤️","ping📡","status📊","maintainers😎"]
                        
            ],
            resize_keyboard=True
        )
else:
            buttonz=ReplyKeyboardMarkup(
            [
                ["start⚡️","help📚","DC"],
                ["Subscribe ❤️","ping📡","status📊","maintainers😎"]
                        
            ],
            resize_keyboard=True
        )

            
            
@StreamBot.on_message((filters.command("start") | filters.regex('start⚡️')) & filters.private )
async def start(b, m):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await b.send_message(
            Var.BIN_CHANNEL,
            f"**Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ:** \n\n__Mʏ Nᴇᴡ Fʀɪᴇɴᴅ__ [{m.from_user.first_name}](tg://user?id={m.from_user.id}) __Sᴛᴀʀᴛᴇᴅ Yᴏᴜʀ Bᴏᴛ !!__"
        )
    if Var.UPDATES_CHANNEL != "None":
        try:
            user = await b.get_chat_member(Var.UPDATES_CHANNEL, m.chat.id)
            if user.status == "kicked":
                await b.send_message(
                    chat_id=m.chat.id,
                    text="__𝓢𝓞𝓡𝓡𝓨, 𝓨𝓞𝓤 𝓐𝓡𝓔 𝓐𝓡𝓔 𝓑𝓐𝓝𝓝𝓔𝓓 𝓕𝓡𝓞𝓜 𝓤𝓢𝓘𝓝𝓖 𝓜𝓔. 𝓒ᴏɴᴛᴀᴄᴛ ᴛʜᴇ 𝓓ᴇᴠᴇʟᴏᴘᴇʀ__\n\n  **𝙃𝙚 𝙬𝙞𝙡𝙡 𝙝𝙚𝙡𝙥 𝙮𝙤𝙪**",
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
             await StreamBot.send_photo(
                chat_id=m.chat.id,
                photo="https://graph.org/file/366530995fd47a006743e-4b4d613a61e1feb9ce.jpgg",
                caption="<i>𝙹𝙾𝙸𝙽 CHANNEL 𝚃𝙾 𝚄𝚂𝙴 𝙼𝙴🔐</i>",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("Jᴏɪɴ ɴᴏᴡ 🔓", url=f"https://t.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
                
            )
             return
        except Exception:
            await b.send_message(
                chat_id=m.chat.id,
                text="<i>𝓢𝓸𝓶𝓮𝓽𝓱𝓲𝓷𝓰 𝔀𝓮𝓷𝓽 𝔀𝓻𝓸𝓷𝓰</i> <b> <a href='https://t.me/innoshiv'>CLICK HERE FOR SUPPORT </a></b>",
                
                disable_web_page_preview=True)
            return
    await StreamBot.send_photo(
    chat_id=m.chat.id,
    photo="https://images3.alphacoders.com/127/1279039.jpg",
    caption=f'''
Hi {m.from_user.mention(style="md")}! 🎉

👋 **Welcome to the Telegram File-to-Link Generator Bot**!  
I help you turn any file into a **direct download link** and **streamable link** in a flash! 🚀

📥 **Just send me any file**, and let me do the magic!  
I even support channels for effortless sharing. 📡
''',
    reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("☁️ Support", url="https://t.me/innoshiv"),
             InlineKeyboardButton("⚡️ Updates", url="https://t.me/innoshiv")],
            [InlineKeyboardButton("❓ Help", callback_data="help"),
             InlineKeyboardButton("ℹ️ About", callback_data="about")],
            [InlineKeyboardButton("🧑‍💻 Developer", url="https://t.me/Sujan")]
        ]
    )
)

@StreamBot.on_callback_query(filters.regex('^help$'))
async def on_help_button(client, callback_query: CallbackQuery):
    # Acknowledge the callback by answering the query
    await callback_query.answer()

    # Update the original message with the help text
    await callback_query.message.edit_text(
        text="""<b>Send me any file or video and I will give you streamable and download links.</b>\n
<b> I also support Channels, add me to your Channel, send any media files and see the magic✨\n\nAlso send /list to know all commands.</b>""",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("☁️ Support", url="https://t.me/innoshiv")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]
        )
    )

@StreamBot.on_callback_query(filters.regex('^about$'))
async def on_about_button(client, callback_query: CallbackQuery):
    # Acknowledge the callback by answering the query
    await callback_query.answer()

    # Update the original message with the about text
    await callback_query.message.edit_text(
    text="""👋 **Hello there!**

🔹 **Bot Name:** [File Stream Bot](https://t.me/filestream_iibot)  
🔹 **Library:** [Pyrogram](https://docs.pyrogram.org)  
🔹 **Server:** [Hivabytes](https://hivabytes)  
🔹 **Language:** [Python3](https://python.org)  
🔹 **Database:** [MongoDB](https://mongodb.com)  
👨‍💻 **Developer:** [Sujan](https://t.me/Sujan)
""",
    disable_web_page_preview=True,
    reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🧑‍💻 Developer", url="https://t.me/Sujan"), InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
    )
)


@StreamBot.on_callback_query(filters.regex('^back$'))
async def on_back_button(client, callback_query: CallbackQuery):
    # Return to the original message
    await callback_query.message.edit_text(
        text=f'''
        Hi there! 🎉

👋 **Welcome to the Telegram File-to-Link Generator Bot**!  
I help you turn any file into a **direct download link** and **streamable link** in a flash! 🚀

📥 **Just send me any file**, and let me do the magic!  
I even support channels for effortless sharing. 📡
''',
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("☁️ Support", url="https://t.me/Innoshiv"),
                 InlineKeyboardButton("⚡️ Updates", url="https://t.me/innoshiv")],
                [InlineKeyboardButton("❓ Help", callback_data="help"),
                 InlineKeyboardButton("ℹ️ About", callback_data="about")],
                [InlineKeyboardButton("🧑‍💻 Developer", url="https://t.me/Sujan")]
            ]
        )
    )



@StreamBot.on_message((filters.command("help") | filters.regex('help📚')) & filters.private )
async def help_handler(bot, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
        await bot.send_message(
            Var.BIN_CHANNEL,
            f"**Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ **\n\n__Mʏ Nᴇᴡ Fʀɪᴇɴᴅ__ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) __Started Your Bot !!__"
        )
    if Var.UPDATES_CHANNEL != "None":
        try:
            user = await bot.get_chat_member(Var.UPDATES_CHANNEL, message.chat.id)
            if user.status == "kicked":
                await bot.send_message(
                    chat_id=message.chat.id,
                    text="<i>Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ FROM USING ᴍᴇ. Cᴏɴᴛᴀᴄᴛ ᴛʜᴇ Dᴇᴠᴇʟᴏᴘᴇʀ</i>",
                    
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
            await StreamBot.send_photo(
                chat_id=message.chat.id,
                photo="https://graph.org/file/721cd57c154c7f2a2b992-2bb665f9732ff027af.jpg",
                Caption="**𝙹𝙾𝙸𝙽 𝚂𝚄𝙿𝙿𝙾𝚁𝚃 𝙶𝚁𝙾𝚄𝙿 𝚃𝙾 𝚄𝚂𝙴 ᴛʜɪs Bᴏᴛ!**\n\n__Dᴜᴇ ᴛᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜᴇ Bᴏᴛ!__",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("🤖 Jᴏɪɴ Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ", url=f"https://t.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
                
            )
            return
        except Exception:
            await bot.send_message(
                chat_id=message.chat.id,
                text="__Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ Wʀᴏɴɢ. Cᴏɴᴛᴀᴄᴛ ᴍᴇ__ [Support](https://t.me/innoshiv).",
                disable_web_page_preview=True)
            return
    await message.reply_text(
        text="""<b> Send me any file or video i will give you streamable link and download link.</b>\n
<b> I also support Channels, add me to you Channel and send any media files and see miracle✨ also send /list to know all commands""",
        
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💁‍♂️ Owner", url="https://t.me/Sujan")],
                [InlineKeyboardButton("💥 Source Code", url="https://t.me/innoshiv")]
            ]
        )
    )
