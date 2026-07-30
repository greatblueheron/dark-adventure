""" generates text for intro and outro for your podcast... I recommend you read this in your own voice and record it"""

import sys
import os
from utils.claude_completion import get_claude_completion
from dotenv import load_dotenv


def generate_show_introduction(game_types_to_focus_on, name_of_my_podcast):

    show_introduction = f"""Generate a brief intro script meant to be read before every episode of "{name_of_my_podcast}", a real-play table table role playing game focusing on {game_types_to_focus_on}. 
    End the script with the phrase "and now a word from today's sponsor." """

    return show_introduction


def generate_show_outro(game_types_to_focus_on, name_of_my_podcast):

    show_outro = f"""Generate a very short outro script meant to be read after every episode of "{name_of_my_podcast}", a real-play table table role playing game focusing on {game_types_to_focus_on}. """

    return show_outro


def main():

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

    # MODIFY THESE FOR YOUR CASE
    game_types_to_focus_on = "Call of Cthulhu and Delta Green"
    name_of_my_podcast = "Whispers in Green Static"

    try:
        response = get_claude_completion(prompt=generate_show_introduction(game_types_to_focus_on, name_of_my_podcast), api_key=CLAUDE_API_KEY)
        print(f"Claude's response: {response}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

    try:
        response = get_claude_completion(prompt=generate_show_outro(game_types_to_focus_on, name_of_my_podcast), api_key=CLAUDE_API_KEY)
        print(f"Claude's response: {response}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    sys.exit(main())
