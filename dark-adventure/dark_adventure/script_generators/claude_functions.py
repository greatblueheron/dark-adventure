import os
import sys
import anthropic
import json
import random
from elevenlabs.client import ElevenLabs
from typing import Optional
from dotenv import load_dotenv


def get_claude_completion(
        prompt: str,
        api_key: str,
        max_tokens: Optional[int] = 30000,      # 15000
        temperature: Optional[float] = 0.8,     # 0.7
        # model: str = "claude-haiku-4-5-20251001"
        model: str = "claude-opus-4-5-20251101"
        # model: str = "claude-3-7-sonnet-20250219"
        # model: str = "claude-3-5-haiku-20241022"
) -> str:
    """
    Get a completion from Claude using the Anthropic API.

    Args:
        prompt (str): The input prompt to send to Claude
        api_key (str): Your Anthropic API key
        max_tokens (int, optional): Maximum number of tokens in the response. Defaults to 1000
        temperature (float): higher = more creative, try range 0.2..1.0
        model (str, optional): The Claude model to use.

    Returns:
        str: Claude's response text

    Raises:
        anthropic.APIError: If there's an error communicating with the API
    """
    # Initialize the Anthropic client
    client = anthropic.Client(api_key=api_key)

    try:
        # Create a streaming message with the prompt
        with client.messages.stream(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system="You are a script generator that delivers complete responses without interrupting to ask if the user wants you to continue. Always provide the entire requested content without breaking for confirmation.",
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            response = stream.get_final_message()

        # Return the response text
        return response.content[0].text

    except anthropic.APIError as e:
        print(f"Error calling Claude API: {str(e)}")
        raise


def generate_character_prompt(current_characters, game_to_use):

    if "Call_of_Cthulhu" in game_to_use:
        occ_string = "A traditional Call of Cthulhu profession (academic, doctor, journalist, detective, etc.)"
    elif "Delta_Green" in game_to_use:
        occ_string = "A modern profession suitable for Delta Green (FBI agent, CDC researcher, military specialist, tech industry worker, etc.)"
    elif "Trail_of_Cthulhu" in game_to_use:
        occ_string = "A traditional Trail of Cthulhu profession (academic, doctor, journalist, detective, etc.)"
    elif "The_Laundry_RPG" in game_to_use:
        occ_string = "A typical The Laundry RPG profession (academic, bureaucrat, doctor, journalist, detective, etc.)"
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


def get_characters(number_of_new_characters_to_add, game_to_use, API_KEY):

    try:
        with open(os.path.join(os.getcwd(), 'data', "characters_" + game_to_use + ".json"), "r") as file_out:
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
        for player_idx in range(len(players_here), number_of_new_players_to_add+len(players_here)):
            prompt_to_use = generate_player_prompt(current_players=players_here)

            try:
                response = get_claude_completion(prompt=prompt_to_use, api_key=API_KEY)
                print(f"Claude's response: {response}")
                players_here[player_idx] = json.loads(response)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        with open(player_directory, "w") as file_out:
            json.dump(players_here, file_out, indent=4)    # `indent=4` makes it more readable

    return players_here


def generate_episode_prompt(players_to_use, characters_to_use, keeper_to_use, game_to_use):

    countries = [
        "Afghanistan", "Albania", "Algeria", "Andorra", "Angola",
        "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria",
        "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh", "Barbados",
        "Belarus", "Belgium", "Belize", "Benin", "Bhutan",
        "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei",
        "Bulgaria", "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia",
        "Cameroon", "Canada", "Central African Republic", "Chad", "Chile",
        "China", "Colombia", "Comoros", "Congo (Congo-Brazzaville)", "Costa Rica",
        "Croatia", "Cuba", "Cyprus", "Czechia (Czech Republic)", "Democratic Republic of the Congo",
        "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador",
        "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia",
        "Eswatini", "Ethiopia", "Fiji", "Finland", "France",
        "Gabon", "Gambia", "Georgia", "Germany", "Ghana",
        "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau",
        "Guyana", "Haiti", "Holy See", "Honduras", "Hungary",
        "Iceland", "India", "Indonesia", "Iran", "Iraq",
        "Ireland", "Israel", "Italy", "Jamaica", "Japan",
        "Jordan", "Kazakhstan", "Kenya", "Kiribati", "Kosovo",
        "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon",
        "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania",
        "Luxembourg", "Madagascar", "Malawi", "Malaysia", "Maldives",
        "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius",
        "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia",
        "Montenegro", "Morocco", "Mozambique", "Myanmar", "Namibia",
        "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua",
        "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
        "Oman", "Pakistan", "Palau", "Palestine", "Panama",
        "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland",
        "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
        "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino",
        "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles",
        "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands",
        "Somalia", "South Africa", "South Korea", "South Sudan", "Spain",
        "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland",
        "Syria", "Taiwan", "Tajikistan", "Tanzania", "Thailand",
        "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia",
        "Turkey", "Turkmenistan", "Tuvalu", "Uganda", "Ukraine",
        "United Arab Emirates", "United Kingdom", "United States of America", "Uruguay", "Uzbekistan",
        "Vanuatu", "Venezuela", "Vietnam", "Yemen", "Zambia",
        "Zimbabwe",
        "The Kuiper Belt", "The Planet Mercury", "The Planet Venus", "The Planet Mars", "The Planet Uranus",
        "The Planet Saturn", "The Planet Jupiter", "The Planet Pluto", "One of Jupiter's Moons", "One of Saturn's Moons",
        "One of Uranus's Moons", "Deimos, a moon of Mars", "Phobos, a moon of Mars",
        "The Event Horizon Spaceship",
        "A Mining Colony in the 26-Draconis System",
        "A Prison Ship Heading for the moon Europa",
        "A science mission orbiting a strange black hole",
        "a planet being pulled into the supermassive black hole at the center of the Milky Way"
    ]

    country_to_use = random.choice(countries)
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
- Generate a title, time period, and set the story in """ + country_to_use + """ with 3 terrifying locations
- Include a Lovecraftian threat, a novel made-up Lovecraftian entity, and/or strange phenomena
- Ensure the story contains several interesting facts about """ + country_to_use + """ to create a sense of gritty reality
- Structure: Introduction (3 min), Scene 1 (7 min), Scene 2 (7 min), Scene 3 (7 min), Conclusion (3 min)
- Include 3-5 NPCs, 2-3 clues, 1-2 red herrings, and 3-4 skill checks
- Select a tone (Investigative/Action/Psychological/Cosmic Horror)
- Emphasize the horror, and make it scary; make it likely that characters die or go insane
- Include aspects of a random r/nosleep reddit story
- Include 3-5 """ + game_to_use + """ mechanics
- DO NOT use "whisper" or "whispers" in the title

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


def generate_episode_text(episode_number):
    load_dotenv()
    API_KEY = os.getenv("CLAUDE_API_KEY")

    options = ["Delta_Green", "Call_of_Cthulhu", "Delta_Green", "Call_of_Cthulhu", "Trail_of_Cthulhu", "The_Laundry_RPG"]

    game_to_use = random.choice(options)

    all_characters = get_characters(number_of_new_characters_to_add=0, game_to_use=game_to_use, API_KEY=API_KEY)
    all_players = get_players(number_of_new_players_to_add=0, API_KEY=API_KEY)

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

    temperature = 1.0
    full_episode = get_claude_completion(prompt=episode_prompt, api_key=API_KEY, max_tokens=15000, temperature=temperature)

    with open(os.path.join(os.getcwd(), 'data', "episode_" + str(episode_number) + ".json"), "w") as file:
        json.dump(full_episode, file)

    player_first_names = [each["Full Name"].split(" ")[0].lower() for each in players]
    keeper_and_players = {'keeper': keeper["Full Name"].split(" ")[0].lower(), 'players': player_first_names}

    with open(os.path.join(os.getcwd(), 'data', "players_and_keeper_" + str(episode_number) + ".json"), "w") as file:
        json.dump(keeper_and_players, file)


def main():
    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    options = ["Delta_Green", "Call_of_Cthulhu", "Trail_of_Cthulhu", "The_Laundry_RPG"]
    characters = get_characters(number_of_new_characters_to_add=8,
                                game_to_use="The_Laundry_RPG",
                                API_KEY=CLAUDE_API_KEY)


if __name__ == "__main__":
    sys.exit(main())
