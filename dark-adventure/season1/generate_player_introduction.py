""" generates audio files introducing each character. text generated and stored in
/player_intro_audio/player_introductions.json. audio stored in /player_intro_audio/'human_name + ".mp3"' """
import sys
import os
import json
from utils.claude_completion import get_claude_completion
from utils.elevenlabs_voices import text_to_speech_file
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv


def generate_player_introduction(player_dict):

    player_introduction = """You are the person described here: \n\n""" + str(player_dict) + """\n\n You are introducing yourself to a group before beginning a table-top roleplaying game. Describe yourself concisely in the first-person view. """

    return player_introduction


def main():

    load_existing_file = True

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

    client_to_use = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    available_voices = client_to_use.voices.get_all()

    with open(os.path.join(os.getcwd(), "data", "players.json"), "r") as file:
        player_dict = json.load(file)

    voice_dict = {}
    for k, v in player_dict.items():
        human_first_name = v["Full Name"].split(" ")[0].lower()
        voice_dict[human_first_name] = v["Voice ID"].lower()

    if load_existing_file:
        with open(os.path.join(os.getcwd(), 'data', "player_introductions.json"), "r") as file_out:
            intro_text_response = json.load(file_out)
    else:
        intro_text = {}
        intro_text_response = {}

        for k, v in player_dict.items():
            del v["Voice ID"]
            intro_text[k] = generate_player_introduction(v)

            try:
                response = get_claude_completion(prompt=intro_text[k], api_key=CLAUDE_API_KEY)
                print(f"Claude's response: {response}")
                intro_text_response[k] = response
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        with open(os.path.join(os.getcwd(), 'data', "player_introductions.json"), "w") as file_out:
            json.dump(intro_text_response, file_out, indent=4)  # `indent=4` makes it more readable

    for k, v in intro_text_response.items():
        human_name = player_dict[k]['Full Name'].split(" ")[0].lower()
        for voice in available_voices.voices:
            if voice.name.lower() == voice_dict[human_name]:
                voice_id = voice.voice_id
        if not os.path.exists(os.path.join(os.getcwd(), "player_intro_audio", human_name + ".mp3")):
            text_to_speech_file(client_to_use, voice_id, v, os.path.join(os.getcwd(), 'player_intro_audio'), human_name + ".mp3")


if __name__ == "__main__":
    sys.exit(main())
