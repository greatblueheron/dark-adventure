import sys
import os
import random
import json
from script_generators.claude_functions import get_claude_completion
from voice_generators.elevenlabs_voices import text_to_speech_file
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def create_random_product(api_key):
    prompt = "You are a product designer. Please make up a random company name and a random product name in the format product name from company name."
    return get_claude_completion(prompt, api_key, temperature=1.0)


def generate_features(product, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product. Please list three ridiculous features it would have if it was real. Be concise. Do not describe each feature."
    return get_claude_completion(prompt, api_key)


def generate_commercial(product, features, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product including these features " + features + '. In less than 30 seconds, convince me to buy it. Include only the text to be spoken and nothing else.'
    return get_claude_completion(prompt, api_key)


def generate_jingle(product, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product. Please create memorable lyrics for exactly one verse of a commercial jingle for this product. Return only the lyrics."
    return get_claude_completion(prompt, api_key)


def generate_song_genre(api_key):
    prompt = "You are a professional musician and artist. Name a random genre of music. Be as specific as possible. Only respond with the song genre."
    return get_claude_completion(prompt, api_key)


def run_commercial_generation(episode_number):
    # generates product, features, commercial, jingle, song_genre text files and spoken commercial audio file
    # writes audio file to ./commercials/commercial_text_read_episode + str(episode_number) + .mp3

    load_dotenv()
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

    client_to_use = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    available_voices = client_to_use.voices.get_all()
    voice_id = random.choice(available_voices.voices).voice_id

    product = create_random_product(api_key=CLAUDE_API_KEY)
    features = generate_features(product, api_key=CLAUDE_API_KEY)
    commercial = generate_commercial(product, features, api_key=CLAUDE_API_KEY)
    jingle = generate_jingle(product, api_key=CLAUDE_API_KEY)
    song_genre = generate_song_genre(api_key=CLAUDE_API_KEY)

    file_name = 'commercial_text_read_episode_' + str(episode_number) + '.mp3'

    commercial_directory = os.path.join(os.getcwd(), 'commercials')

    if not os.path.exists(commercial_directory):
        os.makedirs(commercial_directory)

    text_to_speech_file(client_to_use, voice_id, commercial, directory=commercial_directory, file_name=file_name)

    file_path = os.path.join(commercial_directory, 'jingle_and_genre' + str(episode_number) + '.json')
    jingle_and_genre = {'jingle': jingle, 'genre': song_genre}

    with open(file_path, "w") as file_out:
        json.dump(jingle_and_genre, file_out, indent=4)  # `indent=4` makes it more readable

    return product, features, commercial, jingle, song_genre


def main():
    for episode_number in range(10, 21):
        product, features, commercial, jingle, song_genre = run_commercial_generation(episode_number)
        print('episode:', episode_number)
        print('*********************')
        print('jingle:', jingle)
        print('genre:', song_genre)
        print()
        # suno output should be ./commercials/'episode_' + str(current_episode_number) + '_commercial_jingle.mp3'


if __name__ == "__main__":
    sys.exit(main())
