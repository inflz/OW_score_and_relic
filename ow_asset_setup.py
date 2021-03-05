import os
import glob


def setup_assets():
    current_path = grab_current_path()
    obs_friendly_path = flip_slashes(current_path)
    psb_ow_json_files = grab_json_files()
    for file in psb_ow_json_files:
        modify_paths_in_file(file, obs_friendly_path)


def modify_paths_in_file(json_file_name, obs_friendly_path):
    """Iterates through the supplied files and replaces the desired text"""
    with open(json_file_name) as f:
        lines = f.readlines()
    for line in lines:
        line = line.replace('C:/PSB OW Stream Assets', obs_friendly_path)
        with open(provide_altered_filename(json_file_name), 'a') as f:
            f.write(line)


def provide_altered_filename(current_filename) -> str:
    """Grabs the part before .json and replaces it with below"""
    new_name = current_filename[:-5]
    return new_name + '_relative.json'


def grab_json_files() -> [str]:
    """
    Makes it that it only returns a list that starts with PSB_OW and ends with .json
    Just a small failsafe in case someone runs this file anywhere else.
    """
    return glob.glob("PSB_OW*.json")


def grab_current_path() -> str:
    return os.path.dirname(os.path.realpath(__file__))


def flip_slashes(path) -> str:
    """Flips slashes for OBS as it prefers forwards slashes"""
    return path.replace('\\', '/')


setup_assets()
