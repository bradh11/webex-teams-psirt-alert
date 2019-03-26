import threading
from waitress import serve
from config import webhook_port
import bot


bot.register_webhook()
t = threading.Thread(target=bot.periodic_psirt_check)
t.start()

serve(bot.app, host="0.0.0.0", port=webhook_port)
