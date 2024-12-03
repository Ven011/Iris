#!/usr/bin/python3

"""gets and sets the system settings"""

import json
import copy
from tkinter import DoubleVar, IntVar

class Settings:
    def __init__(self):
        # set to None initially and defined in main script since tk root instance is needed
        self.settings = None

    def get_setting(self, setting_name: str):
        """Reads and returns a setting from the settings json file

        Returns:
            any: the setting saved in the json file
        """
        with open("/home/datecounter/Iris/counter_settings.json", "r") as setting_file:
            return json.load(setting_file)[setting_name]
    
    # return setting from the class settings variable
    def return_setting(self, setting):
        if self.settings is not None:
            setting_dict = self.settings[setting]
            return setting_dict["value"].get() * setting_dict["factor"] if setting in self.settings else 0
        else:
            return 0
        
    # initialize settings from the settings json file
    def fetch_settings(self):
        if self.settings:
            for setting in self.settings:
                setting_value = self.get_setting(setting) / self.settings[setting]["factor"]
                self.settings[setting]["value"] = DoubleVar(value=setting_value)
        else:
            pass

    def save_settings(self):
        # convert setting values from tk variables to python variables
        temp_settings = dict()
        if self.settings:
            for setting in self.settings:
                temp_settings[setting] = self.settings[setting]["value"].get() * self.settings[setting]["factor"]

            with open("/home/datecounter/Iris/counter_settings.json", "w") as setting_file:
                json.dump(temp_settings, setting_file, indent=4)
        else:
            pass


settings = Settings()