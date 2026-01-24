# dark-adventure
This generates material to allow you to build a "real"-play table-top role playing podcast. 

## Change the .env_example file to .env
You will need API keys for both elevenlabs and anthropic. Once you have them, put them in the .env_example file and 
rename it to .env

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

## Customizing it for you

### generate_show_intro_and_outro.py
This requires you do to some setup work. This file generates intro and outro text. Modify game_types_to_focus_on 
and name_of_my_podcast for your case. Read these text files in your own voice and record them using e.g. audacity. 
Store these in /show_intro_and_outro as mp3 files (I called these green_static_intro.mp3 and green_static_outro.mp3 --
note these are imported in hardcoded form in generate_episode.py so you will have to change these there to whatever
you call them).

### generate_players.py
You usually just run this once. This generates human players. The results will be stored in /data/players.json. 
Feel free to edit that directly if something went wrong. Note elevenlabs recently changed their API return templates 
so the names might be messed up. Check.

### generate_characters.py
Also just run this once. This generates in-game characters. The results will be stored in 
/data/"characters_" + game_to_use + ".json" where you enter game_to_use based on what game you are using. 
Feel free to edit that json file directly if something went wrong.

### generate_player_introduction.py
Also just run this once. This generates introduction text and audio for the human players. text in 
/data/player_introductions.json and audio in /player_intro_audio/name.mp3. I didn't use this audio for 
Whispers in Green Static, but I probably would do an intro episode using this if I did it again.

### Generating Commercials
The one part of episode generation that isn't automated is the generation of the commercial jingles. 
You have to do some stuff manually. Blame Suno's lack of an API. To do this, first run generate_commercial.py. You set
the episode range manually in that script, remember to do that first. It will auto-generate 
/commercials/jingle_and_genreX.json and /commercials/commercial_text_read_episode_X.mp3 for episode X. 
You then need to do this for each episode:

1.  Go to suno.ai and generate songs with jingle text as lyrics and music genre as above; make sure to label them with episode #
2.  Download each song (usually just the first one generated for each), and then edit in audacity to cut down to appropriate length; use fade out effect at end of each; save as ./commercials/episode_#_commercial_jingle.mp3

### generate_episode_text_info.py
This is where your episode prompt and game options are. You probably want to go in there and modify these for your
case. This is called by generate_episode.py so don't run it directly (just if you are debugging or checking if the
generated episodes are good by reading them). It generates /data/episode_episode_number.json and /data/players_and_keeper_episode_number.json.

## Generating Episodes
Once you have the above done, you are ready to generate episodes -- just run generate_episode.py and everything 
should just work. If it doesn't, figure out why and fix it!!!

Once you have an episode, you need to upload it to transistor.fm. Manually extract the title and blurb from 
./data/episode_#.json and put them in the appropriate spots, and then drag and drop the actual full 
episode ./full_episodes/episode_#_full.mp3 into the upload audio slot.