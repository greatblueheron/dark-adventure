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
Copyffmpeg -version

You should see version information if installed correctly

