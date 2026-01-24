""" generates episode text... you probably want to modify some things, like prompt and options, for your case
creates data/episode_" + str(episode_number) + ".json" and data/players_and_keeper_" + str(episode_number) + ".json" """
import os
import sys
import json
import random
from dotenv import load_dotenv
from generate_players import get_players
from generate_characters import get_characters
from claude_completion import get_claude_completion


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

    full_episode = get_claude_completion(prompt=episode_prompt, api_key=API_KEY)

    with open(os.path.join(os.getcwd(), 'data', "episode_" + str(episode_number) + ".json"), "w") as file:
        json.dump(full_episode, file)

    player_first_names = [each["Full Name"].split(" ")[0].lower() for each in players]
    keeper_and_players = {'keeper': keeper["Full Name"].split(" ")[0].lower(), 'players': player_first_names}

    with open(os.path.join(os.getcwd(), 'data', "players_and_keeper_" + str(episode_number) + ".json"), "w") as file:
        json.dump(keeper_and_players, file)


def main():

    episode_number = 0

    generate_episode_text(episode_number=episode_number)


if __name__ == "__main__":
    sys.exit(main())
