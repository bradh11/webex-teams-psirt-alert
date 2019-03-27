import config
from openVulnQuery import query_client
from webexteamssdk import WebexTeamsAPI
from datetime import datetime, timedelta
import dateutil.parser

api = WebexTeamsAPI(access_token=config.webex_teams_token)

query_client = query_client.OpenVulnQueryClient(
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
    d = dateutil.parser.parse(s)
    return d.replace(tzinfo=None)


def get_advisories_by_product(room_id, product="cisco", count=5):
    product = " ".join(product)
    api.messages.create(
        roomId=room_id,
        markdown=f"One moment please while I retrieve the last {count} alerts for product: {product}",
    )
    advisories = query_client.get_by_product(adv_format="default", product_name=product)

    for advisory in advisories[0:4]:
        full_message = construct_message_alert(advisory)
        api.messages.create(roomId=room_id, markdown=full_message)

    return True


def get_latest_advisories(room_id, product="cisco", count=5):
    api.messages.create(
        roomId=room_id,
        markdown=f"One moment please while I retrieve the last {count} alerts",
    )
    advisories = query_client.get_by_latest(adv_format="default", latest=count)

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
        print(f"sending {messages} to {user['room_title']}")
        api.messages.create(user["room_id"], markdown=message)


def periodic_check():
    """ 
    This function will run inside a loop and check if psirt database has changed at an interval defined by background scheduler
    """
    logger.debug(f"checking psirt for updates")

    # check timedelta of most recent 5 alerts and send alert if newer than last 1hr
    advisories = query_client.get_by_latest(adv_format="default", latest=5)

    for advisory in advisories:
        logging.debug(f"advisory last_updated: {advisory.last_updated}")
        advisory_date = date_from_string(advisory.last_updated)
        advisory_time_delta = (datetime.now() - advisory_date).total_seconds()

        if advisory_time_delta <= 3600:
            logging.info(
                f"timedelta is less than 1 hr: {advisory_time_delta} - sending alert"
            )
            full_message = construct_message_alert(advisory)
            alert_subscribers(full_message)
        else:
            logging.debug(
                f"timedelta is greater than 1 hr since last_update: {advisory_time_delta}"
            )


if __name__ == "__main__":
    check_alerts = get_advisories()
