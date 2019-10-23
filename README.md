# PSIRT Alert BOT

This is a Webex Teams Bot that will allow users to subscribe and query Cisco's PSIRT alert API. It will also actively alert a direct or group space when a new alert has been posted. The background task checks for new alerts every 60 minutes.

### Pre-requisites

- Python 3.6 or later (thank you f-strings)
- install the dependencies `pip install -r requirements.txt`
- rename config.py.example to config.py
- create a bot account at developer.webex.com and add the token to the config.py (or better yet, leverage environment variables...)
- get your psirt api CLIENT_ID and CLIENT_SECRET from Cisco API console. https://apiconsole.cisco.com/

### Run the BOT

1. Launch the bot `python bot_server.py`
2. expose your webhook listener (open a port to your bot server webhook listener, or leverage a cloud service provider)
3. invite the bot to a 1-1 space or a group space in webex teams and ask for help. The rest should be self evident.

This code was built as a personal project for myself to stay up to date with Cisco issues. That said, the bot service code itself may have some bugs, feel free to help me squash `em. Open an issue and a PR and I will gladly roll in any fixes.
