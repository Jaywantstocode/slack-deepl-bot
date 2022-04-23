from flask import abort, Flask, jsonify, make_response, request, Response
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import logging, os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
import deepl
from slack_bolt.adapter.flask import SlackRequestHandler

logging.basicConfig(level=logging.DEBUG)

slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

SCOPES = [
	'https://www.googleapis.com/auth/spreadsheets',
	'https://www.googleapis.com/auth/drive'
]

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

app_react = App(token=slack_token)
handler = SlackRequestHandler(app_react)
# Create a Translator object providing your DeepL API authentication key.
# To avoid writing your key in source code, you can set it in an environment
# variable DEEPL_AUTH_KEY, then read the variable in your Python code:
translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"])

FLAGS = {"de": "DE", "gb": "EN-GB", "fr": "FR", "flag-england": "EN-GB",
         "flag-cp": "FR", "it": "IT", "jp": "JA", "es": "ES",
         "flag-nl": "NL", "flag-pl": "PL", "ru": "RU", "cn": "ZH"}


@app.route("/events", methods=["POST"])
def slack_events():
	request_json = request.get_json(silent=True, force=True)
	print(request_json)

	# for verification
	# if request_json.get("challenge") is not None:
	# 	headers = { "Content-Type": "plain/text" }
	# 	return make_response(request_json.get("challenge"), 200, headers)

	return handler.handle(request)


@app_react.event("reaction_added")
def reaction_added(event, say):
	emoji = event["reaction"]
	if emoji not in FLAGS:
		# if the emoji is not a registered flag, early return
		return
	language = FLAGS[emoji]
	channel = event["item"]["channel"]
	ts = event["item"]["ts"]
	conversations_history = client.conversations_history(
		channel=channel, oldest=ts, latest=ts
	)
	messages = conversations_history.data["messages"]

	# get the message from the thread, if you cant find from the messages.
	if not messages:
		group_history = client.conversations_replies(channel=channel, ts=ts)
		messages = group_history.data["messages"]
	original_text = messages[0]["text"]
	translated_text = translator.translate_text(original_text,
	                                            target_lang=language)
	try:
		response = client.chat_postMessage(
			channel=channel,
			thread_ts=ts,
			text="translated language: " + emoji + "\n" + translated_text.text,
		)
	except SlackApiError as e:
		# You will get a SlackApiError if "ok" is False
		assert e.response["error"]


def getGoogleService():
	scope = ['https://www.googleapis.com/auth/spreadsheets',
	         'https://www.googleapis.com/auth/drive.file',
	         "https://www.googleapis.com/auth/drive"]
	keyFile = 'your-json-file'
	credentials = ServiceAccountCredentials.from_json_keyfile_name(keyFile,
	                                                               scopes=scope)
	return build("sheets", "v4", credentials=credentials)


def is_request_valid(req):
	is_token_valid = req.form['token'] == os.environ[
		'SLACK_VERIFICATION_TOKEN']
	is_team_id_valid = req.form['team_id'] == os.environ['SLACK_TEAM_ID']

	return is_token_valid and is_team_id_valid


@app.route('/translate', methods=['POST'])
def translate():
	if not is_request_valid(request):
		abort(400)
	user_data = request.form
	user_id = user_data.get("user_id")
	text = user_data.get("text")
	# Translate text into a target language, in this case, French
	result = translator.translate_text(text, target_lang="ja")
	# Note: printing or converting the result to a string uses the output text
	return jsonify({
		"response_type": 'in_channel',
		"text": result.text
	})



if __name__ == "__main__":
	print("hi")
	translator = deepl.Translator(os.environ["DEEPL_AUTH_KEY"])
	result = translator.translate_text("testing", target_lang="ja")
	print(result.text)
# data = \
# 	get_list(RECORD_ANSWER, "A" + str(2) + ":L" + str(2))["valueRanges"][0][
# 		"values"][0]
# correct_answer = data[1]
# print(has_answered("user", data[4:]))
# print(correct_answer)
# print(data)
# print(convert_choice("1"))
