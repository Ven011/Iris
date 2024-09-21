#!/usr/bin/python3

"""gets and sets the system settings"""

import json

def get_setting(setting_name: str):
    """Reads and returns a setting from the settings json file

    Returns:
        any: the setting saved in the json file
    """
    with open("/media/raspberrypi/7CF9-874A/settings.json") as setting_file:
        return json.load(setting_file)[setting_name]