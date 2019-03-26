import os, json, time, logging, logging.config, threading
from datetime import datetime
from flask import Flask, request
import requests
import yaml
from webexteamssdk import WebexTeamsAPI
from tinydb import TinyDB, Query, where
from tinydb.operations import delete, increment, decrement
import config
import psirt

this_folder = os.getcwd()

# create logfile if it does not yet exist
if os.path.exists(f"{this_folder}/logs/logfile.log"):
    pass
else:
    os.makedirs(os.path.dirname(f"{this_folder}/logs/logfile.log"), exist_ok=True)
    open(f"{this_folder}/logs/logfile.log", "a").close()

logging_config = yaml.load(open("./logging_config.yaml", "r"))
logging.config.dictConfig(logging_config)
logger = logging.getLogger("standard")

# initialize the database
db = TinyDB("db.json", indent=2, sort_keys=True)
db.table(name="_default", cache_size=0)
User = Query()

# Initialize the Bot in Webex Teams
api = WebexTeamsAPI(access_token=config.webex_teams_token)
bot_room_list = api.rooms.list()
registered_webhooks = api.webhooks.list()
webhook_listener = (
    config.webhook_listener_base_url + f":{config.webhook_port}/{config.bot_name}"
)


# initialize the db for users who do not yet exist
for room in bot_room_list:
    print(f"bot is spawning in {room.title}")


app = Flask(__name__)

help_message_group = f"## PSIRT Notifier\nThank you for adding me to your space.  I am here to alert you when new PSIRT alerts are announced by Cisco.  I will do this automatically unless you ask me not to.\n\n* If you want to stop receiving automatic updates simply @mention me and type `unsubscribe`.\n\n* If you want to opt back in simply @mention me and type `subscribe`\n\n* To get the last `x` alerts type `last 5` (for example)\n\n* If you want to see the latest (5) advisories, simply type `alerts`"
help_message_direct = f"## PSIRT Notifier\nThank you for adding me to your space.  I am here to alert you when new PSIRT alerts are announced by Cisco.  I will do this automatically unless you ask me not to.\n\n* If you want to stop receiving automatic updates simply type `unsubscribe`.\n\n* If you want to opt back in simply type `subscribe`\n\n* To get the last `x` alerts type `last 5` (for example)\n\n* If you want to know the latest (5) advisories, simply type `alerts`"


def register_webhook():
    # cleanout any old webhooks the bot created in the past when initializing
    for webhook in registered_webhooks:
        api.webhooks.delete(webhook.id)

    # Register the BOT webhook for new message notification
    webhook_reg = api.webhooks.create(
        name=config.bot_name, targetUrl=webhook_listener, resource="all", event="all"
    )
    logger.info(webhook_reg)


def update_room_in_database(json_data):
    """
    # Get Room details from room ID and update the DB if room does not exist
    """
    room_id = json_data["data"]["roomId"]
    room = api.rooms.get(roomId=room_id)
    print(f"webhook received from: {room.title}")

    room_type = json_data["data"]["roomType"]

    bot_user = db.search(User.room_id == room_id)
    if bot_user == [] or bot_user == None:
        print(f"{room.title} not in db")
        logger.info(f"{room.title} not in db")
        db.insert(
            {
                "room_id": room_id,
                "room_title": room.title,
                "room_type": room_type,
                "subscribed": True,
                "help_requests": {"general": 0},
                "last_access": str(datetime.now()),
                "createdAt": str(datetime.now()),
            }
        )
    else:
        bot_user[0]["last_access"] = str(datetime.now())
        bot_user[0]["room_title"] = room.title
        bot_user[0]["help_requests"]["general"] = (
            bot_user[0]["help_requests"]["general"] + 1
        )
        db.write_back(bot_user)


def unsubscribe_to_updates(room_id, reason="message"):
    """
    update the database subscription to false if the user types `unsubscribe`
    """
    bot_user = db.search(User.room_id == room_id)
    bot_user[0]["subscribed"] = False
    db.write_back(bot_user)
    logger.info(f"room has unsubscribed from updates: {room_id}")
    print(f"room has unsubscribed from updates: {room_id}")
    if reason == "message":
        api.messages.create(
            roomId=room_id,
            markdown=f"This room is now unsubscribed from announcements.",
        )


def subscribe_to_updates(room_id, reason="message"):
    """
    update the database subscription to True if the user types `subscribe`
    """
    bot_user = db.search(User.room_id == room_id)
    bot_user[0]["subscribed"] = True

    logger.info(f"room has subscribed to updates: {room_id}")
    print(f"room has subscribed to updates: {room_id}")
    if reason == "message":
        api.messages.create(
            roomId=room_id, markdown=f"This room is now subscribed to announcements."
        )
    else:
        if bot_user[0]["room_type"] == "group":
            api.messages.create(roomId=room_id, markdown=help_message_group)

        else:
            api.messages.create(roomId=room_id, markdown=help_message_direct)
    db.write_back(bot_user)


def handle_commands(received_message, email, room_id):
    """
    Handle all non help commands
    """
    print(received_message)
    if "alerts" in received_message:
        psirt.get_advisories(room_id=room_id)
    elif "last" in received_message:
        psirt.get_advisories(room_id=room_id, count=received_message[1])


def respond_to_message(json_data):
    """
    """
    message_id = json_data["data"]["id"]
    user_id = json_data["data"]["personId"]
    email = json_data["data"]["personEmail"]
    room_id = json_data["data"]["roomId"]
    room_type = json_data["data"]["roomType"]
    input_file = json_data["data"].get("files")
    received_message = api.messages.get(messageId=message_id)

    # Only respond to messages not from the Bot account to avoid infinite loops...
    if email == config.bot_email:
        return  # break out of this function

    # print(received_message)
    if "unsubscribe" in received_message.text.lower():
        unsubscribe_to_updates(room_id, reason="message")
    elif "subscribe" in received_message.text.lower():
        subscribe_to_updates(room_id)
    elif "help" in received_message.text.lower() and room_type == "direct":
        api.messages.create(roomId=room_id, markdown=help_message_direct)
    elif "help" in received_message.text.lower() and room_type == "group":
        api.messages.create(roomId=room_id, markdown=help_message_group)
    else:
        if room_type == "direct":
            received_message = received_message.text.lower().split()
        elif room_type == "group":
            received_message = received_message.text.lower().split()[1::]
        handle_commands(received_message, email, room_id)


@app.route(f"/{config.bot_name}", methods=["POST"])
def webhook_receiver():
    """
    Listen for incoming webhooks.  Webex Teams will send a POST for each message directed to the BOT.
    For a group space, @mention of the BOT must occur.
    For a 1-1, @mentions are not allowed and the bot will respond to any message directed to it.
    """
    json_data = request.json
    # logger.debug(json_data)
    # update database with room info if it does not exist yet
    if json_data["data"]["personEmail"] != config.bot_email:
        update_room_in_database(json_data)

    # print(json_data)
    if json_data["resource"] == "memberships" and json_data["event"] == "created":
        update_room_in_database(json_data)
        subscribe_to_updates(
            room_id=json_data["data"]["roomId"], reason="deleted_membership"
        )

    if json_data["resource"] == "memberships" and json_data["event"] == "deleted":
        # disable subscription for room
        unsubscribe_to_updates(
            room_id=json_data["data"]["roomId"], reason="deleted_membership"
        )

    if json_data["resource"] == "messages" and json_data["event"] == "created":
        respond_to_message(json_data)

    return "200"


def periodic_psirt_check():
    """ 
    This function will run inside a loop and check if versions have changed every 30 minutes.
    """
    interval = 3600  # frequency of checks
    time.sleep(interval / 2)

    logger.debug(f"checking psirt for updates")
    new_update = True  # TODO: function to check timedelta

    if not new_update:
        logger.debug(f"no change since last interval")
        pass
    else:
        # update_messages = construct_version_update_messages(version_changed)
        # alert_subscribers of change and send update messages
        # alert_subscribers(update_messages)
        # update_version_cache(latest_versions)
        pass
    threading.Timer(interval / 2, periodic_version_check).start()


if __name__ == "__main__":
    register_webhook()

    # t = threading.Thread(target=periodic_psirt_check)
    # t.start()

    print(f"bot is running")
    app.run(debug=True, host="0.0.0.0", port=config.webhook_port, use_reloader=False)