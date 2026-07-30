""" generates game characters, stores as "characters_" + game_to_use + ".json" """
import os
import sys
import json
from dotenv import load_dotenv
from utils.claude_completion import get_claude_completion


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
        occ_string = f"""A typical {game_to_use} profession."""  # modify this for your specific game

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
            json.dump(characters_here, file_out, indent=4)  # `indent=4` makes it more readable

    return characters_here


def main():

    game_to_use = "Delta_Green"             # change to whatever you want, will be in path name so use _ etc
    number_of_new_characters_to_add = 10    # change if you want!

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

    characters = get_characters(number_of_new_characters_to_add=number_of_new_characters_to_add,
                                game_to_use=game_to_use,
                                API_KEY=CLAUDE_API_KEY)


if __name__ == "__main__":
    sys.exit(main())
