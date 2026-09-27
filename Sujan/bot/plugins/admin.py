import os
import time
import string
import random
import asyncio
import aiofiles
import datetime
from Sujan.utils.broadcast_helper import send_msg
from Sujan.utils.database import Database
from Sujan.bot import StreamBot
from Sujan.vars import Var
from pyrogram import filters, Client
from pyrogram.types import Message

db = Database(Var.DATABASE_URL, Var.name)
Broadcast_IDs = {}

async def resolve_target_user_id(c: Client, m: Message):
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user.id
    if len(m.command) < 2:
        return None
    token = m.command[1].strip()
    if token.isdigit():
        return int(token)
    if token.startswith("@"):
        token = token[1:]
    try:
        user = await c.get_users(token)
    except Exception:
        return None
    return user.id

def is_owner(user_id: int) -> bool:
    return user_id in Var.OWNER_ID

@StreamBot.on_message(filters.command("users") & filters.private )
async def sts(c: Client, m: Message):
    user_id = m.from_user.id
    if user_id in Var.OWNER_ID:
        total_users = await db.total_users_count()
        await m.reply_text(text=f"Total Users in DB: {total_users}", quote=True)

@StreamBot.on_message(filters.command("broadcast") & filters.private & filters.user(list(Var.OWNER_ID)))
async def broadcast_(c, m):
    user_id = m.from_user.id
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message to broadcast it.")
    
    out = await m.reply_text(
        text=f"Broadcast initiated! You will be notified with log file when all the users are notified."
    )
    all_users = await db.get_all_users()
    broadcast_msg = m.reply_to_message
    while True:
        broadcast_id = ''.join([random.choice(string.ascii_letters) for i in range(3)])
        if not Broadcast_IDs.get(broadcast_id):
            break
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    failed = 0
    success = 0
    Broadcast_IDs[broadcast_id] = dict(
        total=total_users,
        current=done,
        failed=failed,
        success=success
    )
    async with aiofiles.open('broadcast.txt', 'w') as broadcast_log_file:
        async for user in all_users:
            sts, msg = await send_msg(
                user_id=int(user['id']),
                message=broadcast_msg
            )
            if msg is not None:
                await broadcast_log_file.write(msg)
            if sts == 200:
                success += 1
            else:
                failed += 1
            if sts == 400:
                await db.delete_user(user['id'])
            done += 1
            if Broadcast_IDs.get(broadcast_id) is None:
                break
            else:
                Broadcast_IDs[broadcast_id].update(
                    dict(
                        current=done,
                        failed=failed,
                        success=success
                    )
                )
    if Broadcast_IDs.get(broadcast_id):
        Broadcast_IDs.pop(broadcast_id)
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await asyncio.sleep(3)
    await out.delete()
    if failed == 0:
        await m.reply_text(
            text=f"broadcast completed in `{completed_in}`\n\nTotal users {total_users}.\nTotal done {done}, {success} success and {failed} failed.",
            quote=True
        )
    else:
        await m.reply_document(
            document='broadcast.txt',
            caption=f"broadcast completed in `{completed_in}`\n\nTotal users {total_users}.\nTotal done {done}, {success} success and {failed} failed.",
            quote=True
        )
    os.remove('broadcast.txt')


@StreamBot.on_message(filters.command("ban") & filters.private & filters.user(list(Var.OWNER_ID)))
async def ban_user(c: Client, m: Message):
    target_id = await resolve_target_user_id(c, m)
    if target_id is None:
        await m.reply_text("Usage: /ban <user_id> or reply to a user message.", quote=True)
        return
    if is_owner(target_id):
        await m.reply_text("You cannot ban an owner.", quote=True)
        return
    await db.ban_user(target_id)
    await m.reply_text(f"User `{target_id}` has been banned.", quote=True)
    try:
        await c.send_message(
            chat_id=target_id,
            text="🚫 Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ʙᴀɴɴᴇᴅ ꜰʀᴏᴍ ᴜꜱɪɴɢ ᴛʜɪꜱ ʙᴏᴛ.\n\n🔞 Tʜɪꜱ ᴀᴄᴛɪᴏɴ ᴡᴀꜱ ᴛᴀᴋᴇɴ ʙᴇᴄᴀᴜꜱᴇ ʏᴏᴜ ɢᴇɴᴇʀᴀᴛᴇᴅ ᴏʀ ᴀᴛᴛᴇᴍᴘᴛᴇᴅ ᴛᴏ ɢᴇɴᴇʀᴀᴛᴇ 18+ ᴄᴏɴᴛᴇɴᴛ ᴜꜱɪɴɢ ᴛʜᴇ ʙᴏᴛ.\n\n📩 Iꜰ ʏᴏᴜ ʙᴇʟɪᴇᴠᴇ ᴛʜɪꜱ ʙᴀɴ ᴡᴀꜱ ɪꜱꜱᴜᴇᴅ ʙʏ ᴍɪꜱᴛᴀᴋᴇ, ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ᴛᴇᴀᴍ ꜰᴏʀ ᴀꜱꜱɪꜱᴛᴀɴᴄᴇ @Sujan_Ch."
        )
    except Exception:
        pass


@StreamBot.on_message(filters.command("unban") & filters.private & filters.user(list(Var.OWNER_ID)))
async def unban_user(c: Client, m: Message):
    target_id = await resolve_target_user_id(c, m)
    if target_id is None:
        await m.reply_text("Usage: /unban <user_id> or reply to a user message.", quote=True)
        return
    await db.unban_user(target_id)
    await m.reply_text(f"User `{target_id}` has been unbanned.", quote=True)
    try:
        await c.send_message(
            chat_id=target_id,
            text="✅ Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴜɴʙᴀɴɴᴇᴅ!\n\n🎉 Yᴏᴜʀ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴛʜᴇ ʙᴏᴛ ʜᴀꜱ ʙᴇᴇɴ ʀᴇꜱᴛᴏʀᴇᴅ, ᴀɴᴅ ʏᴏᴜ ᴄᴀɴ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ ᴀɢᴀɪɴ."
        )
    except Exception:
        pass
