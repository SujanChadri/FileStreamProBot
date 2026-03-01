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


async def check_user_in_update_channels(b, user_id: int):
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
            user = await b.get_chat_member(channel, user_id)
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

            
@StreamBot.on_message((filters.command("start") | filters.regex('start⚡️')) & filters.private )
async def start(b, m):
    if await db.is_user_banned(m.from_user.id):
        await b.send_message(
            chat_id=m.chat.id,
            text="You are banned from using this bot. Contact support if you believe this is a mistake.",
            disable_web_page_preview=True
        )
        return
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await b.send_message(
            Var.BIN_CHANNEL,
            f"**Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ:** \n\n__Mʏ Nᴇᴡ Fʀɪᴇɴᴅ__ [{m.from_user.first_name}](tg://user?id={m.from_user.id}) __Sᴛᴀʀᴛᴇᴅ Yᴏᴜʀ Bᴏᴛ !!__"
        )
    
    # Check multiple update channels
    update_channels = Var.get_update_channels()
    if update_channels:
        is_member, not_joined, is_banned = await check_user_in_update_channels(b, m.chat.id)
        
        if is_banned:
            await b.send_message(
                chat_id=m.chat.id,
                text="Sorry, You Are Banned For Using This Bot. Contact @Sujan_Ch\n\n  **He Will Help You**",
                disable_web_page_preview=True
            )
            return
        
        if not_joined:
            channel_text = "Cʜᴀɴɴᴇʟs" if len(not_joined) > 1 else "Cʜᴀɴɴᴇʟ"
            await StreamBot.send_photo(
                chat_id=m.chat.id,
                photo="https://ibb.co/nN1Ngf2N",
                caption=f"**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs {channel_text} To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!",
                reply_markup=get_join_channels_markup(not_joined),
            )
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
    await callback_query.answer()

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
    await callback_query.answer()

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
    if await db.is_user_banned(message.from_user.id):
        await bot.send_message(
            chat_id=message.chat.id,
            text="You are banned from using this bot. Contact support if you believe this is a mistake.",
            disable_web_page_preview=True
        )
        return
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id)
        await bot.send_message(
            Var.BIN_CHANNEL,
            f"**Nᴇᴡ Usᴇʀ Jᴏɪɴᴇᴅ **\n\n__Mʏ Nᴇᴡ Fʀɪᴇɴᴅ__ [{message.from_user.first_name}](tg://user?id={message.from_user.id}) __Started Your Bot !!__"
        )
    
    # Check multiple update channels
    update_channels = Var.get_update_channels()
    if update_channels:
        is_member, not_joined, is_banned = await check_user_in_update_channels(bot, message.chat.id)
        
        if is_banned:
            await bot.send_message(
                chat_id=message.chat.id,
                text="<i>Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ From Using ᴍᴇ. Cᴏɴᴛᴀᴄᴛ @Sujan_Ch</i>",
                disable_web_page_preview=True
            )
            return
        
        if not_joined:
            channel_text = "Cʜᴀɴɴᴇʟs" if len(not_joined) > 1 else "Cʜᴀɴɴᴇʟ"
            await StreamBot.send_photo(
                chat_id=message.chat.id,
                photo="https://ibb.co/nN1Ngf2N",
                caption=f"**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs {channel_text} To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!",
                reply_markup=get_join_channels_markup(not_joined),
            )
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


@StreamBot.on_callback_query(filters.regex('^check_join$'))
async def on_check_join_button(client, callback_query: CallbackQuery):
    """Handle the 'I've Joined / Refresh' button click"""
    await callback_query.answer("Please Wait...")

    user_id = callback_query.from_user.id

    # Check if user is now a member of all required channels
    is_member, not_joined, is_banned = await check_user_in_update_channels(client, user_id)

    if is_banned:
        await callback_query.message.edit_text(
            text="Sorry, You Are Banned For Using This Bot. Contact @Sujan_Ch\n\n  **He Will Help You**",
            disable_web_page_preview=True
        )
        return

    if not_joined:
        # User still hasn't joined all channels
        channel_text = "Cʜᴀɴɴᴇʟs" if len(not_joined) > 1 else "Cʜᴀɴɴᴇʟ"
        await callback_query.message.edit_text(
            text=f"**J𝙾𝙸𝙽 Uᴘᴅᴀᴛᴇs {channel_text} To U𝚂𝙴 Tʜɪs Bᴏᴛ!**\n\nDᴜᴇ Tᴏ Oᴠᴇʀʟᴏᴀᴅ, Oɴʟʏ Cʜᴀɴɴᴇʟ Sᴜʙsᴄʀɪʙᴇʀs Cᴀɴ Usᴇ Tʜᴇ Bᴏᴛ!\n\n**Yᴏᴜ sᴛɪʟʟ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ:**",
            reply_markup=get_join_channels_markup(not_joined),
        )
    else:
        # User has joined all channels - show welcome message
        await callback_query.message.edit_text(
            text=f"""Hey {callback_query.from_user.mention(style="md")}! 🎉

**I Am File To Link Generator Bot.**!

Send Me Any File And Get A Direct Download Link And Streaming Link.

Warning : Generating Link Of Adult Content Is Strictly Prohibited. If You Will Do, You Will Get Permanent Ban.

Bot Is Made By @Sujan_Ch
""",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("⚡️ Updates", url="https://t.me/Sujan_Ch")],
                    [InlineKeyboardButton("❓ Help", callback_data="help"),
                     InlineKeyboardButton("ℹ️ About", callback_data="about")
                    ]
                ]
            )
        )
