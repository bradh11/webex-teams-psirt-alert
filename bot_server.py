import threading
from waitress import serve
from config import webhook_port
import bot
import psirt
from apscheduler.schedulers.background import BackgroundScheduler


bot.register_webhook()

scheduler = BackgroundScheduler()
job = scheduler.add_job(psirt.periodic_check, "interval", minutes=60)
scheduler.start()

serve(bot.app, host="0.0.0.0", port=webhook_port)
