import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, date
from bot.handlers.user_private import send_forecast_message, notify_admins_general
from bot.utils.json_store import load_user_data
from bot.config import ADMINS

async def send_daily_forecasts(bot):
    job = bot.scheduler.get_job("daily_forecast_job")
    user_data = load_user_data()
    today_str = date.today().isoformat()

    file = bot.file_system.get_image(sign="general_queue", kind="0")
    if not file:
        job.pause()
        logging.warning("Очередь общего гороскопа пуста. Рассылка остановлена.")
        await notify_admins_general(bot=bot, text=f"⚠️ В очереди нет общего гороскопа. Рассылка остановлена.")
        return

    for user_id, data in user_data.items():
        first_date = data.get("first_forecast_date")
        zodiac = data.get("zodiac_sign")

        # Пропускаем, если нет знака или сегодня уже был первый прогноз
        if not zodiac or first_date == today_str:
            continue

        try:
            await send_forecast_message(user_id=int(user_id), zodiac_sign=zodiac, bot=bot)
            logging.info(f"Гороскоп отправлен пользователю {user_id} ({zodiac})")
        except Exception as e:
            logging.warning(f"Не удалось отправить гороскоп {user_id} ({zodiac}): {e}")

    await notify_admins_general(bot=bot,
                                text=f"✅ Рассылка завершена.")
    bot.file_system.shift_general_queue()

    file = bot.file_system.get_image(sign="general_queue", kind="0")
    if not file:
        job.pause()
        logging.warning("Очередь общего гороскопа пуста. Рассылка остановлена.")
        await notify_admins_general(bot=bot, text=f"⚠️ После успешной рассылки в очереди нет общего гороскопа. Следующая рассылка остановлена.")


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_forecasts,
        id="daily_forecast_job",
        trigger="cron",
        hour=0,
        minute=58,
        args=[bot]
    )
    bot.scheduler = scheduler
    scheduler.start()


def update_scheduler_time(scheduler: AsyncIOScheduler, hour: int, minute: int):
    job = scheduler.get_job("daily_forecast_job")
    if job:
        job.reschedule(trigger="cron", hour=hour, minute=minute)
