""" as much as possible, auto-generates a Whispers in Green Static episode """
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
from utils.utils import find_highest_episode
from generate_commercial import run_commercial_generation


# structure of episode:
# 1. canned intro from ./show_intro_and_outro/green_static_intro.mp3 -- done
# 2. commercial text spoken by random voice
# 3. suno song with jingle lyrics
# 4. main body adventure
# 5. canned outro from ./show_intro_and_outro/green_static_outro.mp3
#
# 6. Auto-post to transistor.fm?

def generate_audio_from_script(episode_number):
    # this assumes the episode text has already been generated and stored as ./data/episode_str(episode_number).json
    load_dotenv()
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    client_to_use = ElevenLabs(api_key=API_KEY)

    with open(os.path.join(os.getcwd(), "data", "players.json"), "r") as file:
        player_dict = json.load(file)

    voice_dict = {}
    for k, v in player_dict.items():
        human_first_name = v["Full Name"].split(" ")[0].lower()
        voice_dict[human_first_name] = v["Voice ID"].lower()

    with open(os.path.join(os.getcwd(), "data", "episode_" + str(episode_number) + ".json"), "r") as file:
        full_script = json.load(file)

    split_full_script = full_script.split('\n\n')
    filtered_split_full_list = [item for item in split_full_script if not item.startswith('#')]

    explicitly_filtered_split_full_list = [each.split(":", 1) for each in filtered_split_full_list]

    available_voices = client_to_use.voices.get_all()

    player_names = []

    voice_id = {}

    # todo how do we get the keeper name?
    for voice in available_voices.voices:
        if voice.name.lower() == "laura":   # need to get somehow
            voice_id[0] = voice.voice_id

    # this uses the text to extract player names
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

    # probably create new directory
    dir_name = "episode_" + str(episode_number) + "_audio"
    if not os.path.exists(directory):
        os.makedirs(directory)  # Creates the directory (and parents if needed)
    else:
        answer = input('In generate_audio_from_script, episode_current_episode_audio exists; proceed (y/n?')
        if answer != 'y':
            sys.exit()

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

        text_to_speech_file(client_to_use,
                            voice_id=speaker,
                            text=each[1],
                            directory=dir_name,
                            file_name="output_" + str(idx) + ".mp3")
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

    # we have to know which episode number this is. the way I'm proposing to do this is to keep the episode text from
    # all previous episodes in the /data directory for now (maybe change later, but I think this is fine) and determine
    # what the episode number is from this.
    current_episode_number = find_highest_episode(os.path.join(os.getcwd(), 'data')) + 1

    user_input = input('Producing Episode #' + str(current_episode_number) + '. Proceed (y/n)?')

    if user_input != 'y':
        sys.exit()

    # load canned intro and outro mp3 files
    intro_and_outro_directory = os.path.join(os.getcwd(), 'show_intro_and_outro')
    intro_audio = AudioSegment.from_mp3(os.path.join(intro_and_outro_directory, 'green_static_intro.mp3'))
    outro_audio = AudioSegment.from_mp3(os.path.join(intro_and_outro_directory, 'green_static_outro.mp3'))

    # generate audio file for spoken commercial text; return all the generated text
    product, features, commercial, jingle, song_genre = run_commercial_generation(episode_number=current_episode_number)

    commercial_directory = os.path.join(os.getcwd(), 'commercials')
    commercial_text_audio = AudioSegment.from_mp3(os.path.join(commercial_directory, 'commercial_text_read_episode_' + str(episode_number) + '.mp3'))

    print('until we have a suno API... here is the jingle and the song genre:')
    print('******************************************************************')
    print(jingle)
    print(song_genre)
    print('******************************************************************')

    # generate audio file for main adventure body text
    generate_audio_from_script()

    stitch_audio_files(os.path.join(os.getcwd(), "episode_1_audio"))


if __name__ == "__main__":
    sys.exit(main())
