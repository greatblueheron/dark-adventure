# dark-adventure
experimental real-play role playing podcast

## Dependencies
Python 3.10

conda --> python-dotenv, anthropic, pydub
pip --> elevenlabs, ffmpeg-python

make sure you have ffmpeg -- do this, seems to work:

Step 1: Download FFmpeg Binaries

Go to gyan.dev FFmpeg builds
Download the "ffmpeg-release-essentials" build (look for the .zip or .7z file)

Step 2: Extract and Set Up FFmpeg

Extract the downloaded archive to a permanent location (e.g., C:\ffmpeg)
Inside the extracted folder, find the bin directory which contains ffmpeg.exe

Step 3: Add FFmpeg to PATH

Press Win+X and select "System"
Click "Advanced system settings" on the right
Click "Environment Variables" at the bottom
Under "System variables", find and select "Path", then click "Edit"
Click "New" and add the full path to the bin directory (e.g., C:\ffmpeg\bin)
Click "OK" on all dialogs to save

Step 4: Verify Installation

IMPORTANT: Close and reopen any Command Prompt/PowerShell windows
Open a new Command Prompt and type:
ffmpeg -version

You should see version information if installed correctly

## Generating Commercials Audio

Suno doesn't have an API yet, so you have to do this manually. 

1. Run generate_commercial.py (choose episode range); this will create reading of episode (stored as 
./commercials/commercial_text_read_episode_#.mp3), jingle text, and music genre text
2. Go to suno.ai and generate songs with jingle text as lyrics and music genre as above; make sure to label them with 
episode #
3. Download each song (usually just the first one generated for each), and then edit in audacity to cut down to 
appropriate length; use fade out effect at end of each; save as ./commercials/episode_#_commercial_jingle.mp3

## Generating Episodes

Once you have the above done, you are ready to generate an episode -- just run generate_episode.py and everything 
should just work. If it doesn't, figure out why and fix it!!!

Once you have an episode, you need to upload it to transistor.fm. Extract the title and blurb from 
./data/episode_#.json and put them in the appropriate spots, and then drag and drop the actual full 
episode ./full_episodes/episode_#_full.mp3 into the upload audio slot.