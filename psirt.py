import config
from openVulnQuery import query_client
from webexteamssdk import WebexTeamsAPI

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


def get_advisories(room_id, product="cisco", count=5):
    advisories = query_client.get_by_latest(adv_format="default", latest=count)

    for advisory in advisories:
        full_message = construct_message_alert(advisory)
        # TODO: if last_update is more recent that now, send the alert
        api.messages.create(roomId=room_id, markdown=full_message)

    return True


if __name__ == "__main__":
    check_alerts = get_advisories()
