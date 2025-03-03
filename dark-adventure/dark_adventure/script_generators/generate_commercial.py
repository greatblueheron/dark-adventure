import sys
import os
from claude_functions import get_claude_completion
from dotenv import load_dotenv


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
    API_KEY = os.getenv("CLAUDE_API_KEY")
    product = create_random_product(api_key=API_KEY)
    features = generate_features(product, api_key=API_KEY)
    commercial = generate_commercial(product, features, api_key=API_KEY)
    jingle = generate_jingle(product, api_key=API_KEY)
    song_genre = generate_song_genre(api_key=API_KEY)

    print()


if __name__ == "__main__":
    sys.exit(main())
