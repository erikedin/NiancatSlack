import os
import os.path

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

def read_token(token_name):
    home_slack_path = os.path.expanduser("~/.slack")
    token_path = os.path.join(home_slack_path, token_name)
    with open(token_path, "r") as token_file:
        token_contents = token_file.read()
        return token_contents.strip()

bot_token = read_token(os.environ.get("SLACK_BOT_TOKEN_NAME", "niancat.token"))
app_token = read_token(os.environ.get("SLACK_APP_TOKEN_NAME", "niancat.app-token"))

app = App(token=bot_token)

@app.command("/hello-socket-mode")
def hello_command(ack, body):
    user_id = body["user_id"]
    ack(f"Hi, <@{user_id}>!")

@app.event("app_mention")
def event_test(say):
    say("Hi there!")

@app.message(":wave:")
def say_hello(message, say):
    user = message['user']
    say(f"Hi there, <@{user}>!")

@app.event("message")
def handle_message_events(body, logger):
    print(f"Message: {body}")
    logger.info(body)


if __name__ == "__main__":
    SocketModeHandler(app, app_token).start()