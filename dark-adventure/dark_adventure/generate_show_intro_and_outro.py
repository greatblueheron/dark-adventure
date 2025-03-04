import sys
import os
import json
from script_generators.claude_functions import get_claude_completion, get_players
from voice_generators.elevenlabs_voices import text_to_speech_file
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings, play, voices
from dotenv import load_dotenv


def generate_show_introduction():

    show_introduction = """Generate a brief intro script meant to be read before every episode of "Whispers in Green Static", a real-play table table role playing game focusing on Call of Cthulhu and Delta Green. 
    End the script with the phrase "and now a word from today's sponsor." """

    return show_introduction


def generate_show_outro():

    show_outro = """Generate a very short outro script meant to be read after every episode of "Whispers in Green Static", a real-play table table role playing game focusing on Call of Cthulhu and Delta Green. """

    return show_outro


def main():

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

    try:
        response = get_claude_completion(prompt=generate_show_introduction(), api_key=CLAUDE_API_KEY)
        print(f"Claude's response: {response}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    try:
        response = get_claude_completion(prompt=generate_show_outro(), api_key=CLAUDE_API_KEY)
        print(f"Claude's response: {response}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    sys.exit(main())
