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
                    text="Sorry, You Are Banned For Using This Bot. Contact @Sujan_Ch\n\n  **He Will Help You**",
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
             await StreamBot.send_photo(
                chat_id=m.chat.id,
                photo="https://ibb.co/nN1Ngf2N",
                caption="**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("Jᴏɪɴ Nᴏᴡ 🔓", url=f"https://t.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
                
            )
             return
        except Exception:
            await b.send_message(
                chat_id=m.chat.id,
                text="<i>Something Went Wrong</i> <b> <a href='https://t.me/sujan_ch'>Click Here</a></b>",
                
                disable_web_page_preview=True)
            return
    await StreamBot.send_photo(
    chat_id=m.chat.id,
    photo="https://ibb.co/x8JTcqTz",
    caption=f'''
Hey {m.from_user.mention(style="md")}! 🎉

**I Am File To Link Generator Bot.**! 

Send Me Any File And Get A Direct Download Link And Streaming Link.

Warning : Generating Link Of Adult Content Is Strictly Prohibited. If You Will Do, You Will Get Permanent Ban.

Bot Is Made By @Sujan_Ch
''',
    reply_markup=InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("⚡️ Updates", url="https://t.me/Sujan_Ch")],
            [InlineKeyboardButton("❓ Help", callback_data="help"),
             InlineKeyboardButton("ℹ️ About", callback_data="about")
            ]
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
                [InlineKeyboardButton("☁️ Support", url="https://t.me/Sujan_Ch")],
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
    text="""👋 **Hello There!**

🔹 **Bot Name:** [File Stream Bot](https://t.me/filetolinksroxbot)  
🔹 **Library:** [Pyrogram](https://docs.pyrogram.org)
🔹 **Language:** [Python3](https://python.org)  
🔹 **Database:** [MongoDB](https://mongodb.com)
""",
    disable_web_page_preview=True,
    reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]
    )
)


@StreamBot.on_callback_query(filters.regex('^back$'))
async def on_back_button(client, callback_query: CallbackQuery):
    # Return to the original message
    await callback_query.message.edit_text(
        text=f'''Hey 🎉

**I Am File To Link Generator Bot.**! 

Send Me Any File And Get A Direct Download Link And Streaming Link.

Warning : Generating Link Of Adult Content Is Strictly Prohibited. If You Will Do, You Will Get Permanent Ban.

Bot Is Made By @Sujan_Ch
''',
        reply_markup=InlineKeyboardMarkup(
            [[
            InlineKeyboardButton("⚡️ Updates", url="https://t.me/Sujan_Ch")],
            [InlineKeyboardButton("❓ Help", callback_data="help"),
             InlineKeyboardButton("ℹ️ About", callback_data="about")]
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
                    text="<i>Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ From Using ᴍᴇ. Cᴏɴᴛᴀᴄᴛ @Sujan_Ch</i>",
                    
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
            await StreamBot.send_photo(
                chat_id=message.chat.id,
                photo="https://ibb.co/nN1Ngf2N",
                Caption="**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs Cʜᴀɴɴᴇʟ To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!",
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
                text="__Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ Wʀᴏɴɢ. Cᴏɴᴛᴀᴄᴛ ᴍᴇ__ [Support](https://t.me/Sujan_Ch).",
                disable_web_page_preview=True)
            return
    await message.reply_text(
        text="""<b> Send me any file or video i will give you streamable link and download link.</b>\n
<b> I also support Channels, add me to you Channel and send any media files and see miracle✨ also send /list to know all commands""",
        
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💁‍♂️ Updates", url="https://t.me/Sujan_Ch")]
            ]
        )
    )
            
@StreamBot.on_message(filters.command('ban') & filters.user(Var.OWNER_ID))
async def do_ban(bot ,  message):
    userid = message.text.split(" ", 2)[1] if len(message.text.split(" ", 1)) > 1 else None
    reason = message.text.split(" ", 2)[2] if len(message.text.split(" ", 2)) > 2 else None
    if not userid:
        return await message.reply('<b>ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴀ ᴠᴀʟɪᴅ ᴜsᴇʀ/ᴄʜᴀɴɴᴇʟ ɪᴅ ᴡɪᴛʜ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ\n\nᴇx : /ban (user/channel_id) (banning reason[Optional]) \nʀᴇᴀʟ ᴇx : <code>/ban 1234567899</code>\nᴡɪᴛʜ ʀᴇᴀsᴏɴ ᴇx:<code>/ban 1234567899 seding adult links to bot</code>\nᴛᴏ ʙᴀɴ ᴀ ᴄʜᴀɴɴᴇʟ :\n<code>/ban CHANEL_ID</code>\nᴇx : <code>/ban -1001234567899</code></b>')
    text = await message.reply("<b>ʟᴇᴛ ᴍᴇ ᴄʜᴇᴄᴋ 👀</b>")
    banSts = await db.ban_user(userid)
    if banSts == True:
        await text.edit(
    text=f"<b><code>{userid}</code> ʜᴀs ʙᴇᴇɴ ʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ\n\nSʜᴏᴜʟᴅ I sᴇɴᴅ ᴀɴ ᴀʟᴇʀᴛ ᴛᴏ ᴛʜᴇ ʙᴀɴɴᴇᴅ ᴜsᴇʀ?</b>",
    reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʏᴇs ✅", callback_data=f"sendAlert_{userid}_{reason if reason else 'no reason provided'}"),
                InlineKeyboardButton("ɴᴏ ❌", callback_data=f"noAlert_{userid}"),
            ],
        ]
    ),
)
    else:
        await text.edit(f"<b>Cᴏɴᴛʀᴏʟʟ ʏᴏᴜʀ ᴀɴɢᴇʀ ʙʀᴏ...\n<code>{userid}</code> ɪs ᴀʟʀᴇᴀᴅʏ ʙᴀɴɴᴇᴅ !!</b>")
    return


@StreamBot.on_message(filters.command('unban') & filters.user(Var.OWNER_ID))
async def do_unban(bot ,  message):
    userid = message.text.split(" ", 2)[1] if len(message.text.split(" ", 1)) > 1 else None
    if not userid:
        return await message.reply('ɢɪᴠᴇ ᴍᴇ ᴀɴ ɪᴅ\nᴇx : <code>/unban 1234567899<code>')
    text = await message.reply("<b>ʟᴇᴛ ᴍᴇ ᴄʜᴇᴄᴋ 🥱</b>")
    unban_chk = await db.is_unbanned(userid)
    if  unban_chk == True:
        await text.edit(text=f'<b><code>{userid}</code> ɪs ᴜɴʙᴀɴɴᴇᴅ\nSʜᴏᴜʟᴅ I sᴇɴᴅ ᴛʜᴇ ʜᴀᴘᴘʏ ɴᴇᴡs ᴀʟᴇʀᴛ ᴛᴏ ᴛʜᴇ ᴜɴʙᴀɴɴᴇᴅ ᴜsᴇʀ?</b>',
        reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʏᴇs ✅", callback_data=f"sendUnbanAlert_{userid}"),
                InlineKeyboardButton("ɴᴏ ❌", callback_data=f"NoUnbanAlert_{userid}"),
            ],
        ]
    ),
)

    elif unban_chk==False:
        await text.edit('<b>ᴜsᴇʀ ɪs ɴᴏᴛ ʙᴀɴɴᴇᴅ ʏᴇᴛ.</b>')
    else :
        await text.edit(f"<b>ғᴀɪʟᴇᴅ ᴛᴏ ᴜɴʙᴀɴ ᴜsᴇʀ/ᴄʜᴀɴɴᴇʟ.\nʀᴇᴀsᴏɴ : {unban_chk}</b>")

@StreamBot.on_callback_query()
async def admin_callback_handler(client, query: CallbackQuery):
    data = query.data

    # -------- SEND BAN ALERT --------
    if data.startswith("sendAlert_"):
        _, user_id, reason = data.split("_", 2)
        user_id = int(user_id)

        try:
            await client.send_message(
                user_id,
                f"<b>You have been banned by admin.\nReason: {reason}</b>"
            )
            await query.message.edit(
                f"<b>Alert sent to <code>{user_id}</code>\nReason: {reason}</b>"
            )
        except Exception as e:
            await query.message.edit(f"<b>Failed to send alert beacuse the user id is not valid:\n{e}</b>")

    # -------- NO BAN ALERT --------
    elif data.startswith("noAlert_"):
        user_id = int(data.split("_")[1])
        await query.message.edit(
            f"<b>User <code>{user_id}</code> banned silently.</b>"
        )

    # -------- SEND UNBAN ALERT --------
    elif data.startswith("sendUnbanAlert_"):
        user_id = int(data.split("_")[1])

        try:
            text = "<b>Good news! You have been unbanned by admin.</b>"
            await client.send_message(user_id, text)
            await query.message.edit(
                f"<b>Unban alert sent to <code>{user_id}</code></b>"
            )
        except Exception as e:
            await query.message.edit(f"<b>Error:\n{e}</b>")

    # -------- NO UNBAN ALERT --------
    elif data.startswith("NoUnbanAlert_"):
        user_id = int(data.split("_")[1])
        await query.message.edit(
            f"<b>Unban executed silently for <code>{user_id}</code>.</b>"
        )

    
