import slack  # Import the slack module to interact with the Slack API
import os  # Import os module to interact with the operating system
from pathlib import Path  # Import Path class from pathlib module for path manipulations
from dotenv import load_dotenv  # Import load_dotenv function from dotenv module to load environment variables
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import string
from datetime import datetime, timedelta
import pprint

printer = pprint.PrettyPrinter()

load_dotenv()  # Load environment variables from a .env file located in the current directory

SLACK_TOKEN = os.environ.get('SLACK_TOKEN')  # Retrieve the SLACK_TOKEN environment variable

env_path = Path('.') / '.env'  # Define the path to the .env file
load_dotenv(dotenv_path=env_path)  # Load environment variables from the specified .env file

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])  # Create a Slack client using the token from environment variables
BOT_ID = client.api_call("auth.test")['user_id']

message_counts = {}
welcome_messages = {}

BAD_WORDS = ['fuck','no', 'damn']

SCHEDULED_MESSAGES = [
    {'text': 'First message', 'post_at': (datetime.now() + timedelta(seconds=20,days=1)).timestamp(), 'channel': 'C06VDNB4L6B'},
    {'text': 'second message!', 'post_at': (datetime.now() + timedelta(seconds=30)).timestamp(), 'channel': 'C06VDNB4L6B'}
]

class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text': {
             'type': 'mrkdwn',
             'text': (
                 'welcome to this awesome channel! \n\n'
                 '*Get started by completing the tasks!*'
             )
        }
    }

DIVIDER = {'type': 'divider'}

def __init__(self, channel, user) -> None:
        self.channel = channel
        self.user = user
        self.icon_emoji = ':robot_face:'
        self.timestamp = ''
        self.completed = False

def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'username': 'Welcome Robot!',
            'icon_emoji': self.icon_emoji,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }

def _get_reaction_task(self):
        checkmark = ':white_check_mark:'
        if not self.completed:
            checkmark = ':white_large_square:'
        
        text = f'{checkmark} *React to this message!*'

        return [{'type': 'section', 'text': {'type': 'mrdwn', 'text': text}}]
    
def send_welcome_message(channel, user):
    if channel not in welcome_messages:
        welcome_messages[channel] = {} 

    if user in welcome_messages[channel]:
        return
    
    welcome = WelcomeMessage(channel, user)
    message = welcome.get_message()
    response = client.chat_postMessage(**message)
    welcome.timestamp = response['ts']

        
    welcome_messages[channel][user] = welcome

def schedule_message(messages):
    ids = []
    for msg in messages:
        response = client.chat_scheduleMessage(channel=msg['channel'], text=msg['text'], post_at=msg['post_at']).data
        id_ = response.get('scheduled_message_id')
        ids.append(id_)

    return ids    

def delete_scheduled_messages(ids, channel):
    for _id in ids:
        client.chat_deleteScheduledMessage(channel=channel, scheduled_message_id = _id)

def check_if_bad_words(message):
    msg = message.lower()
    msg = msg.translate(str.maketrans('','', string.punctuation))

    return any(word in msg for word in BAD_WORDS)

@slack_event_adapter.on('message')
def message(payload):
        event = payload.get('event',{})
        channel_id = event.get('channel')
        user_id = event.get('user')
        text = event.get('text')

        if user_id != None and BOT_ID != user_id:
            if user_id in message_counts:
                message_counts['user_id'] += 1 
            else:
                message_counts['user_id'] = 1    
        
            if text.lower() == 'start':
                send_welcome_message(f'@{user_id}', user_id)
            elif check_if_bad_words(text):
                ts = event.get('ts') 
                client.chat_postMessage(channel=channel_id, thread_ts=ts, text="THAT IS A BAD WORD!")
            
@slack_event_adapter.on('reaction_added')
def reaction(payload):
    event = payload.get('event',{})
    channel_id = event.get('item', {}).get('channel')
    user_id = event.get('user')

    if f'@{user_id}' not in welcome_messages: 
        return 
    
    welcome = welcome_messages[f'@{user_id}'][user_id]
    welcome.completed = True
    welcome.channel = channel_id
    message = welcome.get_message()
    updated_message = client.chat_update(**message)
    welcome.timestamp = updated_message['ts']

@app.route('/message-count', methods=['POST'])
def message_count():
   data = request.form
   user_id = data.get('user_id')
   channel_id = data.get('channel_id')
   message_count = message_counts.get(user_id, 0)

   client.chat_postMessage(channel=channel_id, text=f"Message: {message_count}" )

   return Response(), 200

if __name__ == "__main__":
    app.run(debug=True)