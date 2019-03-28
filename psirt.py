import os, logging, logging.config, json
import pytz
from datetime import datetime, timedelta, timezone
from openVulnQuery import query_client
from webexteamssdk import WebexTeamsAPI
from tinydb import TinyDB, Query, where
import yaml
import config

this_folder = os.getcwd()

# initialize the database
db = TinyDB("db.json", indent=2, sort_keys=True)
db.table(name="_default", cache_size=0)
User = Query()

if os.path.exists(f"{this_folder}/logs/logfile.log"):
    pass
else:
    os.makedirs(os.path.dirname(f"{this_folder}/logs/logfile.log"), exist_ok=True)
    open(f"{this_folder}/logs/logfile.log", "a").close()

logging_config = yaml.load(open("./logging_config.yaml", "r"))
logging.config.dictConfig(logging_config)
logger = logging.getLogger("standard")


api = WebexTeamsAPI(access_token=config.webex_teams_token)

psirt_query = query_client.OpenVulnQueryClient(
    client_id=config.credentials.get("CLIENT_ID"),
    client_secret=config.credentials.get("CLIENT_SECRET"),
)


def format_severity(sev_level):
    if sev_level == "High":
        alert_icon = f"🔒"
        alert_color = "danger"
        return alert_icon, alert_color
    elif sev_level == "Medium":
        alert_icon = f"🔒"
        alert_color = "warning"
        return alert_icon, alert_color
    elif sev_level == "Critical":
        alert_icon = f"💀"
        alert_color = "dark"
        return alert_icon, alert_color
    else:
        alert_icon = f"🔒"
        alert_color = "info"
        return alert_icon, alert_color


def construct_message_alert(advisory):
    alert_icon, alert_color = format_severity(advisory.sir)
    if advisory.bug_ids:
        message_bugid = "<hr>"
        for bug in advisory.bug_ids:
            message_bugid = message_bugid + f"bug_id: {bug}<br>"

    message_id = f"<h1>{alert_icon} {advisory.advisory_title}</h1><br>"
    message_title = (
        f"<blockquote class={alert_color}><strong>{advisory.advisory_id}</strong><br>"
    )
    message_heading = f"cvss_base_score: {advisory.cvss_base_score}<br>sir: {advisory.sir}<br>first_published: {advisory.first_published}<br>last_updated: {advisory.last_updated}<br>"
    message_body = f"<br><strong>summary:</strong><br>{advisory.summary}"

    full_message = (
        message_id + message_title + message_heading + message_body + message_bugid
    )

    return full_message


def date_from_string(s):
    # d = dateutil.parser.parse(s)
    d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    return d.replace(tzinfo=timezone.utc).replace(tzinfo=None)


def get_advisories_by_product(room_id, product="cisco", count=5):
    product = " ".join(product)
    api.messages.create(
        roomId=room_id,
        markdown=f"One moment please while I retrieve the last {count} alerts for product: {product}",
    )
    advisories = psirt_query.get_by_product(adv_format="default", product_name=product)

    for advisory in advisories[0:4]:
        full_message = construct_message_alert(advisory)
        api.messages.create(roomId=room_id, markdown=full_message)

    return True


def get_latest_advisories(room_id, product="cisco", count=5):
    api.messages.create(
        roomId=room_id,
        markdown=f"One moment please while I retrieve the last {count} alerts",
    )
    advisories = psirt_query.get_by_latest(adv_format="default", latest=count)

    for advisory in advisories:
        full_message = construct_message_alert(advisory)
        api.messages.create(roomId=room_id, markdown=full_message)

    return True


def alert_subscribers(message):
    """
    Alert subscribers that a version has changed
    """
    subscribers = db.search(User.subscribed == True)

    for user in subscribers:
        print(f"sending message to {user['room_title']}")
        # api.messages.create(user["room_id"], markdown=message)


def notification_cache(advisory):
    """
    cache the last advisory details for future comparison of date stamps
    """
    last_update = {"last_updated": advisory.last_updated, "advisory_id": advisory.advisory_id}

    with open("notification_cache.json", "w") as outfile:
        json.dump(last_update, outfile, indent=2)
    return True


def periodic_check():
    """ 
    This function will run inside a loop and check if psirt database has changed at an interval defined by background scheduler
    """
    logger.debug(f"checking psirt for updates")

    # check timedelta of most recent 5 alerts and send alert if newer than last 1hr
    advisories = psirt_query.get_by_latest(adv_format="default", latest=20)
    
    for advisory in advisories:
        logger.debug(f"advisory last_updated: {advisory.last_updated}")
        advisory_date = date_from_string(advisory.last_updated)

        print("advisory date: ", advisory_date)
        print("now      date: ", datetime.now(pytz.timezone("US/Pacific")))

        advisory_time_delta = (datetime.now() - advisory_date).total_seconds()
        if advisory_time_delta <= 3600:
            logger.info(
                f"timedelta is less than 1 hr: {advisory_time_delta} - sending alert"
            )
            full_message = construct_message_alert(advisory)
            alert_subscribers(full_message)
        else:
            logger.debug(
                f"timedelta is greater than 1 hr since last_update: {advisory_time_delta}"
            )

    # update the cache after peridoic check
    notification_cache(advisories[0])

if __name__ == "__main__":
    check_alerts = get_advisories()
