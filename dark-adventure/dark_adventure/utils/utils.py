import os
import re


def find_highest_episode(directory):
    # Pattern to match episode files and extract the number
    pattern = re.compile(r'episode_(\d+)\.json')

    highest_episode = 0

    # Loop through all files in the directory
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            # Extract the episode number and convert to integer
            episode_num = int(match.group(1))
            # Update the highest episode if this one is larger
            highest_episode = max(highest_episode, episode_num)

    return highest_episode
