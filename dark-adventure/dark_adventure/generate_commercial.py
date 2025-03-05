import sys
import os
import random
from script_generators.claude_functions import get_claude_completion
from voice_generators.elevenlabs_voices import text_to_speech_file
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings, play, voices


def create_random_product(api_key):
    prompt = "You are a product designer. Please make up a random company name and a random product name in the format product name from company name."
    return get_claude_completion(prompt, api_key)


def generate_features(product, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product. Please list three ridiculous features it would have if it was real. Be concise. Do not describe each feature."
    return get_claude_completion(prompt, api_key)


def generate_commercial(product, features, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product including these features " + features + '. In less than 30 seconds, convince me to buy it.'
    return get_claude_completion(prompt, api_key)


def generate_jingle(product, api_key):
    prompt = "You are a professional advertising agent. " + product + " is a hypothetical product. Please create memorable lyrics for exactly one verse of a commercial jingle for this product."
    return get_claude_completion(prompt, api_key)


def generate_song_genre(api_key):
    prompt = "You are a professional musician and artist. Name a random genre of music. Be as specific as possible."
    return get_claude_completion(prompt, api_key)


def main():
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

    text_to_speech_file(client_to_use, voice_id, commercial, output_file_name='commercial_2.mp3')
    print(jingle)
    print(song_genre)


# "Tired of ordinary clothes? SkyWeave from Lumeon Labs isn’t just fabric—it’s future-wear. Stay the perfect temperature instantly, feel lighter than air, and even record your dreams for later. This isn’t fashion—it’s technology woven into reality. Ready to upgrade your existence? SkyWeave is waiting."
if __name__ == "__main__":
    sys.exit(main())
