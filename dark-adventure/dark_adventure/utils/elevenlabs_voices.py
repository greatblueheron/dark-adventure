import os
# import uuid
# from elevenlabs import VoiceSettings, play, voices
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv


def text_to_speech_file(client,
                        voice_id,
                        text: str,
                        directory: str,
                        file_name: str) -> str:
    # Calling the text_to_speech conversion API with detailed parameters
    response = client.text_to_speech.convert(voice_id=voice_id,
                                             output_format="mp3_44100_128",
                                             text=text,
                                             model_id="eleven_multilingual_v2")

    # Writing the audio to a file
    if not os.path.exists(directory):
        os.makedirs(directory)  # Creates the directory (and parents if needed)

    with open(os.path.join(directory, file_name), "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)


if __name__ == "__main__":
    load_dotenv()
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    client_to_use = ElevenLabs(api_key=API_KEY)

    # Fetch the list of available voices
    available_voices = client_to_use.voices.get_all()

    # Print the details of each voice
    for voice in available_voices.voices:
        print(f"Voice ID: {voice.voice_id}, Name: {voice.name}, Category: {voice.category}")
        # if voice.name.lower() == "daniel":
        #     daniel_voice_id = voice.voice_id
        #     break

    # text_to_speech_file(client_to_use, voice_id=daniel_voice_id, text="minimalist goat extravaganza")
