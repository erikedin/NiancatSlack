import os
import os.path
import sys
import pprint

import requests
from dotenv import dotenv_values

from slack_bolt import App, Say
from slack_bolt.adapter.socket_mode import SocketModeHandler

def read_token(token_name):
    home_slack_path = os.path.expanduser("~/.slack")
    token_path = os.path.join(home_slack_path, token_name)
    with open(token_path, "r") as token_file:
        token_contents = token_file.read()
        return token_contents.strip()

config = dotenv_values(".env")
bot_token = read_token(config.get("SLACK_BOT_TOKEN_NAME", "niancat.token"))
app_token = read_token(config.get("SLACK_APP_TOKEN_NAME", "niancat.app-token"))

try:
    notification_channel = config["NIANCAT_NOTIFICATION_CHANNEL"]
except KeyError:
    print("Configuration variable NIANCAT_NOTIFICATION_CHANNEL not set in .env!")
    print("It must be set to the name of the channel to which notification messages should go.")
    print()
    sys.exit(1)

class NiancatAdapter:
    def __init__(self, url, team):
        self.url = url
        self.team = team
    
    def command_url(self):
        return os.path.join(self.url, "command")
    
    def post_command(self, user, command_text):
        payload = {"team": self.team, "user": user, "command": command_text}
        r = requests.post(self.command_url(), json=payload)
        r.raise_for_status()
        return r.text

app = App(token=bot_token)
niancat = NiancatAdapter("http://localhost:8000", "defaultteam")

# For debug printing of messages and such
pp = pprint.PrettyPrinter(indent=4)

@app.event("message")
def handle_message_events(body, logger, say: Say):
    pp.pprint(body)
    logger.info(body)
    try:
        user = body['event']['user']
        command = body['event']['text']
        response = niancat.post_command(user, command)
        say(response)
    except Exception as e:
        print(f"Message command exception: {e}")

if __name__ == "__main__":
    SocketModeHandler(app, app_token).start()