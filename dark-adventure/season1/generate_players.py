""" generates human players, stores as /data/players.json """
import os
import sys
import json
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from utils.claude_completion import get_claude_completion


def generate_player_prompt(current_players):
    load_dotenv()
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    client_to_use = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    available_voices = client_to_use.voices.get_all()
    voice_names = [each.name for each in available_voices.voices]

    current_name_string = ""
    player_name_string = ""

    for k, v in current_players.items():
        current_name_string += v["Full Name"] + ", "
        player_name_string += v["Voice ID"] + ", "

    gen_player_prompt = """Generate a modern person who would be a player in a tabletop roleplaying game with:

                1. Full Name: [Generate a contemporary name that feels realistic for someone who might play TTRPGs, and only include the name here; ensure the chosen name is different in both first and last names from all the names in this list: """ + current_name_string + """]

                2. Occupation: [Generate an unusual and/or unlikely sounding profession]

                3. Gaming Experience: [Generate their level of experience with TTRPGs and specifically with Call of Cthulhu]

                4. Personality at the Gaming Table: [Generate 2-3 traits describing how they behave during game sessions, such as:
                   - How they approach roleplaying
                   - Their comfort with horror elements
                   - Their play style (strategic, dramatic, comedic, etc.)
                   - How they interact with other players]

                5. Motivation: [Generate why they enjoy playing table top role playing games]

                6. Gaming Quirk: [Generate an interesting habit or tendency they have during gameplay]

                7. Voice ID: [Select a name from this list: """ + str(
        voice_names) + """; ensure the chosen name is different from all the names in this list: """ + current_name_string + """]

                Respond with a string in the format of a python dictionary, where the keys are the six text string categories above."""

    return gen_player_prompt


def get_players(number_of_new_players_to_add, API_KEY):
    player_directory = os.path.join(os.getcwd(), 'data', "players.json")

    try:
        with open(player_directory, "r") as file_out:
            players_here = json.load(file_out)
    except FileNotFoundError:
        print('No player file found, generating one...')
        if number_of_new_players_to_add == 0:
            sys.exit(print('you set number_of_new_players_to_add to zero without an existing file, exiting...'))
        players_here = {}

    if number_of_new_players_to_add > 0:
        for player_idx in range(len(players_here), number_of_new_players_to_add + len(players_here)):
            prompt_to_use = generate_player_prompt(current_players=players_here)

            try:
                response = get_claude_completion(prompt=prompt_to_use, api_key=API_KEY)
                print(f"Claude's response: {response}")
                players_here[player_idx] = json.loads(response)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        with open(player_directory, "w") as file_out:
            json.dump(players_here, file_out, indent=4)  # `indent=4` makes it more readable

    return players_here


def main():

    number_of_new_players_to_add = 10   # modify to set number of new players to add

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

    characters = get_players(number_of_new_players_to_add=number_of_new_players_to_add, API_KEY=CLAUDE_API_KEY)


if __name__ == "__main__":
    sys.exit(main())
