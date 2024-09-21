#!/usr/bin/python3

"""
    Class that handles matching contour profiles from consecutive
    frames
"""

import pyrealsense2 as rs2
import cv2
import numpy as np 

from time import time
from rectifier import Rectifier
from settings import get_setting

# initialize image rectifier
start_x = 96
start_y = 96
end_x = 480
end_y = 480

SURFACE_DISTANCE = get_setting("date_counting_settings")["surface_distance"]

rect = Rectifier(start_x, end_x, start_y, end_y, surface_distance=SURFACE_DISTANCE)

# initialize camera
pipe = rs2.pipeline()
cfg = rs2.config()
cfg.enable_stream(rs2.stream.depth, 640, 480, rs2.format.z16, 30)
profile = pipe.start(cfg)

# user variables
PATCH_DEPTH = get_setting("date_counting_settings")["patch_depth"]
MIN_AREA = get_setting("date_counting_settings")["min_date_area"]
MAX_AREA = get_setting("date_counting_settings")["max_date_area"]

MATCH_DISTANCE_THRESHOLD = get_setting("date_counting_settings")["match_distance_threshold"]
MATCH_PERCENT_THRESHOLD = get_setting("date_counting_settings")["match_percent_threshold"]
BASE_PROFILE_TRANSLATION = get_setting("date_counting_settings")["base_profile_translation"]
MAX_MATCH_ATTEMPTS = get_setting("date_counting_settings")["max_match_attempts"]
FREEZE_LINE_OFFSET = get_setting("date_counting_settings")["freeze_profile_line_offset"]
FREEZE_LINE = (end_y - start_y) - FREEZE_LINE_OFFSET

# area to weight equation
CONVERSION_M = get_setting("date_counting_settings")["conversion_m"]
CONVERSION_B = get_setting("date_counting_settings")["conversion_b"]

class Date_Profile:
    def __init__(self, id, appx_area, est_weight, position):
        self.id = id
        self.appx_area = appx_area
        self.est_weight = est_weight
        self.position = position
        self.matched = False

class Cupid:
    def __init__(self):
        # drop first few camera frames
        pipe.wait_for_frames()

        self.base_profiles = list()
        self.compare_profiles = list()
        self.compare_frame = None

        # date counting variables
        self.count = 0
        self.weight = 0
        self.profile_counter = 0
        self.match_attempts = 0

    def get_base_profiles(self):
        # get and process frame
        frame_set = pipe.wait_for_frames()
        depth_frame = frame_set.get_depth_frame()
        
        # rectify camera angle/tilt effects 
        _, rect_depth_binary = rect.get_rectified(depth_frame, patch_depth=PATCH_DEPTH)

        # get depth image contours
        contours, _ = cv2.findContours(rect_depth_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # create base profiles
        for contour in contours:
            area = cv2.contourArea(contour)
            if MIN_AREA<area<MAX_AREA:
                x, y, w, h = cv2.boundingRect(contour)
                est_area = w*h
                position = np.array([x+(w//2), y+(h//2)]) # bounding box centroid
                est_weight = (CONVERSION_M * est_area) + CONVERSION_B
                self.base_profiles.append(Date_Profile(id=self.profile_counter, 
                                                       appx_area=est_area, 
                                                       est_weight=est_weight, 
                                                       position=position))
                self.profile_counter += 1

    def get_compare_profiles(self):
        # get and process frame
        frame_set = pipe.wait_for_frames()
        depth_frame = frame_set.get_depth_frame()
        
        # rectify camera angle/tilt effects 
        rect_depth, rect_depth_binary = rect.get_rectified(depth_frame, patch_depth=PATCH_DEPTH)

        # get depth image contours
        contours, _ = cv2.findContours(rect_depth_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self.compare_frame = rect_depth

        # create compare profiles
        for contour in contours:
            area = cv2.contourArea(contour)
            if MIN_AREA<area<MAX_AREA:
                x, y, w, h = cv2.boundingRect(contour)
                est_area = w*h
                position = np.array([(x+(w//2)), (y+(h//2))]) # bounding box centroid
                est_weight = (CONVERSION_M * est_area) + CONVERSION_B
                self.compare_profiles.append(Date_Profile(id=None, 
                                                       appx_area=est_area, 
                                                       est_weight=est_weight, 
                                                       position=position))

    def find_matches(self):
        matches = 0
        self.match_attempts += 1
        # find distance between frame one profiles and frame two profiles
        for base_profile in self.base_profiles:
            for compare_profile in self.compare_profiles:
                distance = np.linalg.norm(base_profile.position - compare_profile.position)
                # match found?
                if distance <= MATCH_DISTANCE_THRESHOLD: # yes
                    # acknowledge
                    compare_profile.id = base_profile.id
                    # stop updating the weight if the compare profile is past the "Freeze line"
                    compare_profile.est_weight = base_profile.est_weight if compare_profile.position[1] > FREEZE_LINE else compare_profile.est_weight
                    base_profile.matched = True
                    matches += 1
                    break

        if matches <= len(self.base_profiles) * MATCH_PERCENT_THRESHOLD: # not successful, increment base profile position
            for base_profile in self.base_profiles:
                base_profile.position[1] += BASE_PROFILE_TRANSLATION
            # attempt to find match again if within allowed iterations
            if self.match_attempts <= MAX_MATCH_ATTEMPTS:
                # clear compare profile ids and reset variables
                for profile in self.compare_profiles: profile.id = None
                for profile in self.base_profiles: profile.matched = False
                self.find_matches()
            else:
                print(f"Could not find matches within {MAX_MATCH_ATTEMPTS} iterations")
                return False
        else: # successful! create new profiles
            print(f"Matches found in {self.match_attempts} iterations")
            return True

    def handle_matches(self):
        # take care of profiles that have left the frame
        for profile in self.base_profiles:
            if not profile.matched:
                self.count+=1
                self.weight+=profile.est_weight

        self.base_profiles = list()
        # assign ids to matched profiles in the compare list
        for profile in self.compare_profiles:
            if profile.id == None:
                profile.id = self.profile_counter
                self.profile_counter+=1
            
            self.base_profiles.append(profile)

    def work(self):
        if len(self.base_profiles) == 0:
            self.get_base_profiles()
        self.get_compare_profiles()
        matches_found = self.find_matches()

        if matches_found:
            self.handle_matches()
        else:
            pass

        cv2.putText(self.compare_frame, str(self.weight), (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        for profile in self.base_profiles:
            cv2.putText(self.compare_frame, str(profile.id), tuple(profile.position), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.line(self.compare_frame, (0, FREEZE_LINE), (end_x, FREEZE_LINE), (255, 255, 255))

        # reset variables
        self.match_attempts = 0
        self.compare_profiles = list()

        return self.count, self.weight, self.compare_frame

    def reset(self):
        self.base_profiles = list()
        self.compare_profiles = list()
        self.compare_frame = None

        # date counting variables
        self.count = 0
        self.weight = 0
        self.profile_counter = 0
        self.match_attempts = 0

    def stop(self):
        pipe.stop()
    

        



        
