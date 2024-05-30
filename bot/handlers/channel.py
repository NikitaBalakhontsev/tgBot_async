import logging
from aiogram import Bot, types, Router
from aiogram.filters import Command

from bot.filters import ChatTypeFilter

channel_router = Router()
channel_router.edited_message.filter(ChatTypeFilter(["channel"]))

logger = logging.getLogger(__name__)

@channel_router.channel_post(Command("get_admins"))
async def get_admins(channel_post: types.Message, bot: Bot):
    chat_id = channel_post.chat.id
    admins_list = await bot.get_chat_administrators(chat_id)
    admins_list = [
        member.user.id
        for member in admins_list
        if member.status == "creator" or member.status == "administrator"
    ]
    bot.my_admins_list = admins_list
    await channel_post.delete()
    logger.info(admins_list)