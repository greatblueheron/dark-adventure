import os
import sys
import json
import glob
import re
from elevenlabs import VoiceSettings, play, voices
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from pydub import AudioSegment
from voice_generators.elevenlabs_voices import text_to_speech_file


def generate_audio_from_script():

    load_dotenv()
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    client_to_use = ElevenLabs(api_key=API_KEY)

    with open(os.path.join(os.getcwd(), "data", "players.json"), "r") as file:
        player_dict = json.load(file)

    voice_dict = {}
    for k, v in player_dict.items():
        human_first_name = v["Full Name"].split(" ")[0].lower()
        voice_dict[human_first_name] = v["Voice ID"].lower()

    with open(os.path.join(os.getcwd(), "data", "episode_1.json"), "r") as file:
        full_script = json.load(file)

    split_full_script = full_script.split('\n\n')
    filtered_split_full_list = [item for item in split_full_script if not item.startswith('#')]

    explicitly_filtered_split_full_list = [each.split(":", 1) for each in filtered_split_full_list]

    available_voices = client_to_use.voices.get_all()

    player_names = []

    voice_id = {}

    for voice in available_voices.voices:
        if voice.name.lower() == "laura":   # need to get somehow
            voice_id[0] = voice.voice_id

    for each in explicitly_filtered_split_full_list:
        match = re.search(r"\((.*?)\)", each[0].lower())
        if match:
            player_name = match.group(1)
            if player_name not in player_names:
                player_names.append(player_name)
                match = re.search(r"\d+", each[0].lower())
                number = int(match.group())
                for voice in available_voices.voices:
                    if voice.name.lower() == voice_dict[player_name]:
                        voice_id[number] = voice.voice_id

    idx = 0

    for each in explicitly_filtered_split_full_list:
        if 'keeper' in each[0].lower():
            speaker = voice_id[0]
        else:
            match = re.search(r"\d+", each[0].lower())
            number = int(match.group())
            try:
                if str(number) in each[0].lower():
                    speaker = voice_id[number]
            except TypeError:
                print()

        text_to_speech_file(client_to_use, voice_id=speaker, text=each[1], output_file_name="output_" + str(idx) + ".mp3")
        idx += 1


def stitch_audio_files(directory_path, output_filename="combined_output.mp3", pause_duration=500):
    """
    Stitches together audio files named output_j.mp3 in numerical order with pauses.

    Parameters:
    - directory_path: Path to directory containing the audio files
    - output_filename: Name of the output file
    - pause_duration: Duration of pause in milliseconds (default: 500ms)
    """
    # Get list of all output_j.mp3 files
    pattern = os.path.join(directory_path, "output_*.mp3")
    files = glob.glob(pattern)

    # Sort files numerically (output_0.mp3, output_1.mp3, ...)
    files.sort(key=lambda x: int(x.split('output_')[1].split('.mp3')[0]))

    # Check if any files were found
    if not files:
        print(f"No files matching the pattern were found in {directory_path}")
        return

    print(f"Found {len(files)} files to combine")

    # Create a silence segment for the pause
    pause = AudioSegment.silent(duration=pause_duration)

    # Initialize with the first file
    combined = AudioSegment.from_mp3(files[0])

    # Add the rest of the files with pauses in between
    for file in files[1:]:
        print(f"Adding {file}")
        audio = AudioSegment.from_mp3(file)
        combined = combined + pause + audio

    # Export the combined audio
    output_path = os.path.join(directory_path, output_filename)
    combined.export(output_path, format="mp3")
    print(f"Combined audio saved to {output_path}")


def main():
    generate_audio_from_script()

    stitch_audio_files(os.path.join(os.getcwd(), "episode_1_audio"))


if __name__ == "__main__":
    sys.exit(main())
