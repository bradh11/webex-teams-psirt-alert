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


def get_collab_advisories():
    collab_advisories = query_client.get_by_product(
        adv_format="default",
        product_name="unified communications manager",
        a_filter="Medium",
    )

    for advisory in collab_advisories:
        print(f"advisory_id: {advisory.advisory_id}")
        print(f"advisory_title: {advisory.advisory_title}")
        print(f"cvss_base_score: {advisory.cvss_base_score}")
        print(f"sir: {advisory.sir}")
        alert_icon, alert_color = format_severity(advisory.sir)

        print(f"first_published: {advisory.first_published}")
        print(f"last_updated: {advisory.last_updated}")
        print(f"summary: {advisory.summary}")
        if advisory.bug_ids:
            message_bugid = "<hr>"
            for bug in advisory.bug_ids:
                print(f"bug_id: {bug}")
                message_bugid = message_bugid + f"bug_id: {bug}<br>"
        print(f"-" * 60)
        message_id = f"<h1>{alert_icon} {advisory.advisory_title}</h1><br>"
        message_title = f"<blockquote class={alert_color}><strong>{advisory.advisory_id}</strong><br>"
        message_heading = f"cvss_base_score: {advisory.cvss_base_score}<br>sir: {advisory.sir}<br>first_published: {advisory.first_published}<br>last_updated: {advisory.last_updated}<br>"
        message_body = f"<br><strong>summary:</strong><br>{advisory.summary}"
        full_message = (
            message_id + message_title + message_heading + message_body + message_bugid
        )

        api.messages.create(
            roomId="Y2lzY29zcGFyazovL3VzL1JPT00vYzVmNGI2NzAtNGNjOC0xMWU5LTgxOTgtMGRjNzA4NzFhNzZh",
            markdown=full_message,
        )


roomlist = api.rooms.list()
for room in roomlist:
    print(room.title)
    print(room.id)
# print(collab_advisories)

collab_results = get_collab_advisories()
