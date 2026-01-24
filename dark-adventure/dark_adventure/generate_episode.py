""" as much as possible, auto-generates a Whispers in Green Static episode """
import os
import sys
import json
import glob
import re
import time
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from pydub import AudioSegment
from utils.elevenlabs_voices import text_to_speech_file
from utils.utils import find_highest_episode
from generate_episode_text_info import generate_episode_text


# structure of episode:
# 1. canned intro from ./show_intro_and_outro/green_static_intro.mp3 -- done
# 2. commercial text spoken by random voice
# 3. suno song with jingle lyrics
# 4. main body adventure
# 5. canned outro from ./show_intro_and_outro/green_static_outro.mp3
#
# 6. Auto-post to transistor.fm?

def generate_audio_from_script(episode_number, start_from=0):
    # this assumes the episode text has already been generated and stored as ./data/episode_str(episode_number).json
    # this creates a new directory called "episode_" + str(episode_number) + "_audio" and then writes spoken audio
    # files of the form "output_" + str(idx) + ".mp3" for idx from 0 to the last spoken part (typically about 150?)

    load_dotenv()
    API_KEY = os.getenv("ELEVENLABS_API_KEY")
    client_to_use = ElevenLabs(api_key=API_KEY)

    with open(os.path.join(os.getcwd(), "data", "players.json"), "r") as file:
        player_dict = json.load(file)

    with open(os.path.join(os.getcwd(), "data",  "players_and_keeper_" + str(episode_number) + ".json"), "r") as file:
        players_and_keeper = json.load(file)

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

    voice_id = {}

    for voice in available_voices.voices:
        if voice_dict[players_and_keeper['keeper']].lower() in voice.name.lower():
            voice_id[0] = voice.voice_id
        for idx, each_player in enumerate(players_and_keeper['players']):
            if voice_dict[each_player].lower() in voice.name.lower():
                voice_id[idx + 1] = voice.voice_id

    # probably create new directory
    directory = "episode_" + str(episode_number) + "_audio"
    if not os.path.exists(directory):
        os.makedirs(directory)  # Creates the directory (and parents if needed)
    else:
        answer = input('In generate_audio_from_script, episode_current_episode_audio exists; proceed (y/n)?')
        if answer != 'y':
            sys.exit()

    idx = start_from

    for idx_no, each in enumerate(explicitly_filtered_split_full_list):

        if idx_no>=idx:
            if len(each) == 1:
                # in this case, it's the keeper speaking, and text_to_speak will be the zeroth list element
                speaker = voice_id[0]
                text_to_speak = each[0]
            else:
                if len(each) == 2:
                    # this is what's supposed to happen!
                    speaker = None
                    if 'keeper' in each[0].lower():
                        speaker = voice_id[0]
                    else:
                        match = re.search(r"\d+", each[0].lower())
                        try:
                            number = int(match.group())
                            try:
                                if str(number) in each[0].lower():
                                    speaker = voice_id[number]
                            except Exception as e:
                                # Catch any other exceptions
                                print(f"An unexpected error occurred, defaulting to keeper: {e}")
                        except AttributeError:
                            speaker = voice_id[0]

                    if speaker is None:
                        speaker = voice_id[0]

                    text_to_speak = each[1]
                else:
                    print('something is weird... the length of this element is:', len(each))
                    speaker = voice_id[0]
                    text_to_speak = ""

            text_to_speech_file(client_to_use,
                                voice_id=speaker,
                                text=text_to_speak,
                                directory=directory,
                                file_name="output_" + str(idx) + ".mp3")
            idx += 1


def stitch_audio_files(episode_number):
    """ Stitches together audio files named output_j.mp3 in numerical order with pauses. """

    directory = os.path.join(os.getcwd(), "episode_" + str(episode_number) + "_audio")
    # Get list of all output_j.mp3 files
    pattern = os.path.join(directory, "output_*.mp3")
    files = glob.glob(pattern)

    # Sort files numerically (output_0.mp3, output_1.mp3, ...)
    files.sort(key=lambda x: int(x.split('output_')[1].split('.mp3')[0]))

    # Check if any files were found
    if not files:
        print(f"No files matching the pattern were found in {directory}")
        return

    print(f"Found {len(files)} files to combine")

    # Create a silence segment for the pause
    pause = AudioSegment.silent(duration=500)

    # Initialize with the first file
    combined = AudioSegment.from_mp3(files[0])

    # Add the rest of the files with pauses in between
    for file in files[1:]:
        print(f"Adding {file}")
        audio = AudioSegment.from_mp3(file)
        combined = combined + pause + audio

    # Export the combined audio
    output_path = os.path.join(directory, "combined_audio.mp3")
    combined.export(output_path, format="mp3")
    print(f"Combined audio saved to {output_path}")


def normalize_audio_files(list_of_audio_files, target_dBFS=-20):
    """
    Normalize multiple audio files to the same volume level

    Args:
        list_of_audio_files: List of AudioSegment audio files
        target_dBFS: Target dB Full Scale level (default: -20 dBFS)

    Returns:
        List of normalized AudioSegment objects
    """
    normalized_segments = []

    for audio in list_of_audio_files:

        # Calculate the change needed to reach target level
        change_in_dBFS = target_dBFS - audio.dBFS

        # Apply gain to normalize
        normalized_audio = audio.apply_gain(change_in_dBFS)

        normalized_segments.append(normalized_audio)

    return normalized_segments


def combine_audio_files(normalized_segments, output_path):
    """
    Combine multiple normalized audio segments into one file

    Args:
        normalized_segments: List of AudioSegment objects
        output_path: Path to save the combined audio
    """
    # Start with the first segment
    combined = normalized_segments[0]

    # Add each subsequent segment
    for segment in normalized_segments[1:]:
        combined += segment

    # Export the combined audio
    combined.export(output_path, format="mp3")


def main():

    # we have to know which episode number this is. the way I'm proposing to do this is to keep the episode text from
    # all previous episodes in the /data directory for now (maybe change later, but I think this is fine) and determine
    # what the episode number is from this.

    current_episode_number = find_highest_episode(os.path.join(os.getcwd(), 'data')) + 1

    user_input = input('Producing Episode #' + str(current_episode_number) + '. Proceed (y/n)?')

    if user_input != 'y':
        sys.exit()

    ######################################################
    # steps 1 and 5: load canned intro and outro mp3 files
    ######################################################
    print('loading intro and outro audio...')
    intro_and_outro_directory = os.path.join(os.getcwd(), 'show_intro_and_outro')
    intro_audio = AudioSegment.from_mp3(os.path.join(intro_and_outro_directory, 'green_static_intro.mp3'))
    outro_audio = AudioSegment.from_mp3(os.path.join(intro_and_outro_directory, 'green_static_outro.mp3'))
    print('Done!')

    ##############################
    # load step 2 commercial audio
    ##############################
    # # generate audio file for spoken commercial text; return all the generated text
    # product, features, commercial, jingle, song_genre = run_commercial_generation(episode_number=current_episode_number)
    print('loading commercial text audio...')
    commercial_directory = os.path.join(os.getcwd(), 'commercials')
    commercial_text_audio = AudioSegment.from_mp3(
        os.path.join(commercial_directory,
                     'commercial_text_read_episode_' + str(current_episode_number) + '.mp3'))
    print('Done!')

    #########################################################################
    # generate step 3 audio -- right now you have to do this manually in suno
    #########################################################################

    # file_path = os.path.join(commercial_directory, 'jingle_and_genre' + str(current_episode_number) + '.json')
    # with open(file_path, "r") as file_out:
    #     jingle_and_genre = json.load(file_out)
    #
    # print('until we have a suno API... here is the jingle and the song genre:')
    # print('******************************************************************')
    # print(jingle_and_genre)
    # print('******************************************************************')

    print('loading commercial jingle audio...')
    commercial_jingle_audio = AudioSegment.from_mp3(os.path.join(commercial_directory, 'episode_' + str(current_episode_number) + '_commercial_jingle.mp3'))
    print('Done!')
    # generate episode text and player/keeper name file

    print('generating new episode text...')
    start = time.time()
    generate_episode_text(current_episode_number)
    print('Done... took', time.time() - start, 'seconds...')

    # generate audio files for main adventure body text
    print('generating audio from script...')
    start = time.time()
    generate_audio_from_script(current_episode_number, start_from=0)
    print('Done... took', time.time() - start, 'seconds...')

    #############################################
    # step 4 audio: combine main body audio files
    #############################################

    print('stitching audio files together for main body...')
    stitch_audio_files(current_episode_number)
    print('Done...')

    main_body_audio = AudioSegment.from_mp3(
        os.path.join(os.path.join(os.getcwd(), "episode_" + str(current_episode_number) + "_audio"),
                     "combined_audio.mp3"))

    # at this point we have autogenerated everything except step 3, which requires a suno API and the
    # jingle_and_genre dict

    # Once we have all the audio files we normalize their volumes and combine them

    print('normalizing and combining audio files...')
    list_of_audio_files = [intro_audio, commercial_text_audio, commercial_jingle_audio, main_body_audio, outro_audio]
    normalized_segments = normalize_audio_files(list_of_audio_files)

    file_path = os.path.join(os.getcwd(), 'full_episodes')
    if not os.path.exists(file_path):
        os.mkdir(file_path)

    combine_audio_files(normalized_segments, os.path.join(file_path, "episode_" + str(current_episode_number) + "_full.mp3"))
    print('Done!!!')

if __name__ == "__main__":
    sys.exit(main())
