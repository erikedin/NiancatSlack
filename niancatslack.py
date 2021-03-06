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

try:
    notification_endpoint = config["NIANCAT_NOTIFICATION_ENDPOINT"]
except KeyError:
    print("Configuration variable NIANCAT_NOTIFICATION_ENDPOINT not set in .env!")
    print("It must be set to the URL where this bot receives notifications")
    print()
    sys.exit(1)

class NiancatAdapter:
    def __init__(self, url, team):
        self.url = url
        self.team = team
    
    def command_url(self):
        return os.path.join(self.url, "command")

    def endpoint_url(self):
        return os.path.join(self.url, "team", self.team, "endpoint")

    def user_url(self, user_id: str) -> str:
        return os.path.join(self.url, "user", self.team, user_id)

    def post_command(self, user, command_text):
        payload = {"team": self.team, "user": user, "command": command_text}
        r = requests.post(self.command_url(), json=payload)
        r.raise_for_status()
        return r.text

    def update_endpoint(self, endpoint):
        payload = {"uri": endpoint}
        r = requests.put(self.endpoint_url(), json=payload)
        r.raise_for_status()

    def update_displayname(self, user_id: str, display_name: str):
        payload = {"display_name": display_name}
        r = requests.put(self.user_url(user_id), json=payload)

    def update_displayname_from_slack(self, user: dict):
        user_id = user["id"]
        display_name = user["profile"]["display_name"]

        # Display names are empty by default, so use real_name instead.
        if display_name == "":
            display_name = user["profile"]["real_name"]

        print(f"User {user} with {user_id} and {display_name}")
        self.update_displayname(user_id, display_name)


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
        logger.info(f"## RESPONSE: {response}")
        say(response)
    except Exception as e:
        print(f"Message command exception: {e}")


@app.event("team_join")
def team_join(event):
    logging.info(f"Team join event: {event}")
    user = event["user"]
    niancat.update_displayname_from_slack(user)


@app.event("user_change")
def user_change(event):
    logging.info(f"User change event: {event}")
    user = event["user"]
    niancat.update_displayname_from_slack(user)


def list_users():
    results = app.client.users_list()
    if not results["ok"]:
        logging.error(f"User list failed: {results}")
        return

    users = results["members"]
    for user in users:
        niancat.update_displayname_from_slack(user)

socket_mode_handler = SocketModeHandler(app, app_token)

#
# FastAPI notification handler
#

from fastapi import FastAPI, Request

api = FastAPI()

@api.get("/")
async def root():
    return {"message": "Hello World"}

@api.post("/notification")
async def post_notification(request: Request):
    print("### NOTIFICATION:")
    binarybody = await request.body()
    body = binarybody.decode("UTF-8")
    print(body)
    print("### END NOTIFICATION")
    app.client.chat_postMessage(channel=notification_channel, text=body)
    return ""

@api.on_event("startup")
def startup_event():
    print("### APPLICATION STARTUP EVENT")
    niancat.update_endpoint(notification_endpoint)
    socket_mode_handler.connect()
    list_users()

@api.on_event("shutdown")
def shutdown_event():
    print("### APPLICATION SHUTDOWN EVENT")
    socket_mode_handler.close()