import os
import sys
import anthropic
import json
import random
import re
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path


def get_claude_completion(
        prompt: str,
        api_key: str,
        max_tokens: Optional[int] = 15000,
        temperature: Optional[float] = 0.7,
        model: str = "claude-3-7-sonnet-20250219"
) -> str:
    """
    Get a completion from Claude using the Anthropic API.

    Args:
        prompt (str): The input prompt to send to Claude
        api_key (str): Your Anthropic API key
        max_tokens (int, optional): Maximum number of tokens in the response. Defaults to 1000
        temperature (float): higher = more creative, try range 0.2..1.0
        model (str, optional): The Claude model to use. Defaults to claude-3-sonnet-20240229

    Returns:
        str: Claude's response text

    Raises:
        anthropic.APIError: If there's an error communicating with the API
    """
    # Initialize the Anthropic client
    client = anthropic.Client(api_key=api_key)

    try:
        # Create a message with the prompt
        message = client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system="You are a script generator that delivers complete responses without interrupting to ask if the user wants you to continue. Always provide the entire requested content without breaking for confirmation.",
            messages=[{"role": "user", "content": prompt}]
        )

        # Return the response text
        return message.content[0].text

    except anthropic.APIError as e:
        print(f"Error calling Claude API: {str(e)}")
        raise


def generate_character_prompt(current_characters, game_to_use):

    if "Call_of_Cthulhu" in game_to_use:
        occ_string = "A traditional CoC profession (academic, doctor, journalist, detective, etc.)"
    elif "Delta_Green" in game_to_use:
        occ_string = "A modern profession suitable for Delta Green (FBI agent, CDC researcher, military specialist, tech industry worker, etc.)"
    else:
        occ_string = ""

    current_name_string = ""
    for k, v in current_characters.items():
        current_name_string += v["Full Name"] + ", "

    gen_character_prompt = """Generate a detailed character suitable for a """ + game_to_use + """ campaign with the following elements:
                
                1. Full Name: [Create a name appropriate for the setting's time period, and only include the name here; ensure the chosen name is different in both first and last names from all the names in this list: """ + current_name_string + """]
                
                2. Occupation: [Generate one of the following:
                   - """ + occ_string + """
                   - An unusual or specialized profession that would bring unique skills]
                
                3. Background: [Generate a brief history including:
                   - Where they're from
                   - Formative experiences
                   - Education or training
                   - A personal connection to the supernatural/strange (optional)]
                
                4. Personality Traits: [Generate 3-4 distinct personality traits that would influence roleplay]
                
                5. Motivations: [Generate 1-2 primary motivations for investigating the unknown]
                
                6. Personal Quirk: [Generate an interesting habit, belief, or quirk]
                
                7. Key Relationships: [Generate 1-2 important relationships that could be relevant during play]
                
                8. Special Knowledge or Skills: [Generate 1-2 unusual areas of expertise beyond their obvious professional skills]
                
                9. Vulnerabilities: [Generate a psychological vulnerability or fear]
                
                10. Starter Equipment: [Generate 3-5 items they would likely carry]
                
                Respond with a string in the format of a python dictionary, where the keys are the ten text string categories above.
                
                Do not include docstring quotes. """

    return gen_character_prompt


def get_characters(number_of_new_characters_to_add, game_to_use):

    try:
        with open(os.path.join(os.getcwd(), '..', 'data', "characters_" + game_to_use + ".json"), "r") as file_out:
            characters_here = json.load(file_out)
    except FileNotFoundError:
        print('No characters file found, generating one...')
        if number_of_new_characters_to_add == 0:
            sys.exit(print('you set number_of_new_characters_to_add to zero without an existing file, exiting...'))
        characters_here = {}

    if number_of_new_characters_to_add > 0:
        for character_idx in range(len(characters_here), number_of_new_characters_to_add + len(characters_here)):
            prompt_to_use = generate_character_prompt(game_to_use=game_to_use, current_characters=characters_here)

            try:
                response = get_claude_completion(prompt=prompt_to_use, api_key=API_KEY)
                print(f"Claude's response: {response}")
                characters_here[character_idx] = json.loads(response)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        with open(os.path.join(os.getcwd(), '..', 'data', "characters_" + game_to_use + ".json"), "w") as file_out:
            json.dump(characters_here, file_out, indent=4)    # `indent=4` makes it more readable

    return characters_here


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

    gen_player_prompt = """Generate a modern person who would be a player in a Call of Cthulhu tabletop roleplaying game with:

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
                
                7. Voice ID: [Select a name from this list: """ + str(voice_names) + """; ensure the chosen name is different from all the names in this list: """ + current_name_string + """]
                
                Respond with a string in the format of a python dictionary, where the keys are the six text string categories above."""

    return gen_player_prompt


def get_players(number_of_new_players_to_add):

    try:
        with open(os.path.join(os.getcwd(), '..', 'data', "players.json"), "r") as file_out:
            players_here = json.load(file_out)
    except FileNotFoundError:
        print('No player file found, generating one...')
        if number_of_new_players_to_add == 0:
            sys.exit(print('you set number_of_new_players_to_add to zero without an existing file, exiting...'))
        players_here = {}

    if number_of_new_players_to_add > 0:
        for player_idx in range(len(players_here), number_of_new_players_to_add+len(players_here)):
            prompt_to_use = generate_player_prompt(current_players=players_here)

            try:
                response = get_claude_completion(prompt=prompt_to_use, api_key=API_KEY)
                print(f"Claude's response: {response}")
                players_here[player_idx] = json.loads(response)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        with open(os.path.join(os.getcwd(), '..', 'data', "players.json"), "w") as file_out:
            json.dump(players_here, file_out, indent=4)    # `indent=4` makes it more readable

    return players_here


def generate_episode_prompt(players_to_use, characters_to_use, keeper_to_use, game_to_use):

    player_string = ""
    idx = 1
    for each in players_to_use:
        player_string += "- Player " + str(idx) + ": " + each["Full Name"] + " (Plays " + characters_to_use[idx-1]["Full Name"] + ", " + characters_to_use[idx-1]["Occupation"] +")\n"
        idx += 1

    player_string += "- Keeper: " + keeper_to_use["Full Name"] + "\n"

    prompt = """COMPLETE SCRIPT REQUEST: Generate a full 30-minute """ + game_to_use + """ actual play script without any questions or meta-commentary. The script must follow this exact format throughout:

KEEPER (NAME): [Narration or dialogue]
PLAYER 1 (NAME): [Dialogue]
PLAYER 2 (NAME): [Dialogue]
PLAYER 3 (NAME): [Dialogue]

Use these characters and elements:

HUMAN PLAYERS:""" + "\n" + player_string + """
                
SCRIPT REQUIREMENTS:
- Generate a title, time period, and setting with 3 locations
- Include a Lovecraftian threat and strange phenomena
- Structure: Introduction (3 min), Scene 1 (7 min), Scene 2 (7 min), Scene 3 (7 min), Conclusion (3 min)
- Include 3-5 NPCs, 2-3 clues, 1-2 red herrings, and 3-4 skill checks
- Select a tone (Investigative/Action/Psychological/Cosmic Horror)
- Include 3-5 """ + game_to_use + """ mechanics

Fill in the complete template below to create a full 30-minute script. Do not deviate from this structure and do not stop until the entire script is complete:

TITLE: [Generate title]

INTRODUCTION (3 minutes):
KEEPER: [Generate keeper intro]
[Generate character introductions]

SCENE 1 (7 minutes):
KEEPER: [Generate scene description]
[Generate dialogue and narration]

SCENE 2 (7 minutes):
KEEPER: [Generate scene description]
[Generate dialogue and narration]

SCENE 3 (7 minutes):
KEEPER: [Generate scene description]
[Generate dialogue and narration]

CONCLUSION (3 minutes):
KEEPER: [Generate conclusion]
[Generate final dialogue]
  
BEGIN THE COMPLETE SCRIPT DIRECTLY. DO NOT LIST ELEMENTS BEFORE STARTING THE SCRIPT.

FINAL INSTRUCTION: Deliver the ENTIRE script in one continuous response. DO NOT ask if I want you to continue. DO NOT include phrases like "Would you like me to continue?" or "Content continues but truncated due to length limit." """

    return prompt


if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("CLAUDE_API_KEY")

    options = ["Delta_Green"]
    game_to_use = random.choice(options)

    all_characters = get_characters(number_of_new_characters_to_add=0, game_to_use=game_to_use)
    all_players = get_players(number_of_new_players_to_add=0)

    # Number of players in the game
    n_players = random.randint(2, 5)

    # Randomly select n_players+1 keys (last key will be keeper)
    random_player_keys = random.sample(list(all_players.keys()), n_players + 1)
    random_character_keys = random.sample(list(all_characters.keys()), n_players)

    players = [all_players[each_key] for each_key in random_player_keys[:-1]]

    # one character for each player; player plays character in same list order
    characters = [all_characters[each_key] for each_key in random_character_keys]

    keeper = all_players[random_player_keys[-1]]

    episode_prompt = generate_episode_prompt(players, characters, keeper, game_to_use)

    full_episode = get_claude_completion(prompt=episode_prompt, api_key=API_KEY, max_tokens=15000)

    # Get all episode files in the directory
    files = Path(os.path.join(os.getcwd(), '..', 'data')).glob("episode_*.json")

    # Extract episode numbers and find the max
    max_episode = max(
        (int(match.group(1)) for file in files if (match := re.search(r"episode_(\d+)\.json", file.name))),
        default=None  # Handle empty case
    )

    if max_episode is None:
        episode_number = 0
    else:
        episode_number = max_episode + 1

    with open(os.path.join(os.getcwd(), '..', 'data', "episode_" + str(episode_number) + ".json"), "w") as file:
        json.dump(full_episode, file)

    print()
