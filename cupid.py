#!/usr/bin/python3

"""
    Class that handles matching contour profiles from consecutive
    frames
"""

import pyrealsense2 as rs2
import cv2
import numpy as np
import inference
import supervision as sv

from time import time
from rectifier import Rectifier
from settings import settings

# initialize image rectifier
start_x = 0
start_y = 0
end_x = 720
end_y = 1280
# ^ for image cropping
# rect = Rectifier(start_x, end_x, start_y, end_y, surface_distance=SURFACE_DISTANCE)

# initialize camera
pipe = rs2.pipeline()
cfg = rs2.config()
cfg.enable_stream(rs2.stream.depth, 1280, 720, rs2.format.z16, 30)
cfg.enable_stream(rs2.stream.color, 1280, 720, rs2.format.bgr8, 30)
profile = None
camera_connected = True

try:
    profile = pipe.start(cfg)
except RuntimeError as e:
    print(e)
    camera_connected = False

# user variables

# PATCH_DEPTH = settings.get_setting("date_counting_settings")["patch_depth"]
# MIN_AREA = settings.get_setting("date_counting_settings")["min_date_area"]
# MAX_AREA = settings.get_setting("date_counting_settings")["max_date_area"]

# MATCH_DISTANCE_THRESHOLD = settings.get_setting("date_counting_settings")["match_distance_threshold"]
# MATCH_PERCENT_THRESHOLD = settings.get_setting("date_counting_settings")["match_percent_threshold"]
# BASE_PROFILE_TRANSLATION = settings.get_setting("date_counting_settings")["base_profile_translation"]
# MAX_MATCH_ATTEMPTS = settings.get_setting("date_counting_settings")["max_match_attempts"]
# freeze_line_offset = settings.settings["count_line_offset"]["value"]
# FREEZE_LINE = (end_x - start_x) - freeze_line_offset

# # area to weight equation
# CONVERSION_M = settings.get_setting("date_counting_settings")["conversion_m"]
# CONVERSION_B = settings.get_setting("date_counting_settings")["conversion_b"]

class Date_Profile:
    def __init__(self, id=None, appx_area=None, est_weight=None, position=None):
        self.id = id
        self.appx_area = appx_area
        self.est_weight = est_weight
        self.position = position
        self.matched = False

class Cupid:
    def __init__(self):
        # drop first few camera frames
        pipe.wait_for_frames() if camera_connected else 0

        self.base_profiles = list()
        self.compare_profiles = list()
        self.compare_frame = None

        # date counting variables
        self.counted = [] # list of date IDs that have been counted
        self.counted_last_empty_time = time()
        self.count = 0
        self.weight = 0
        self.profile_counter = 0
        self.match_attempts = 0

        # roboflow model for date detection
        self.model = inference.get_model("dates-1vpyl/3")
        self.bounding_box_annotator = sv.BoundingBoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()

    def detect_dates(self):
        if camera_connected:
            # get and process depth frame
            frame_set = pipe.wait_for_frames()
            # depth_frame = frame_set.get_depth_frame()
            color_frame = frame_set.get_color_frame()
            color = np.asanyarray(color_frame.get_data())
            
            # rectify camera angle/tilt effects 
            # rect_depth_colormap, _ = rect.get_rectified(depth_frame, patch_depth=PATCH_DEPTH)

            # run inference on the color and depth images
            color_results = self.model.infer(color)[0]
            # depth_results = self.model.infer(rect_depth_colormap)[0]

            # load results into the supervision detections API
            color_detections = sv.Detections.from_inference(color_results)
            # depth_detections = sv.Detections.from_inference(depth_results)

            # extract bounding boxes
            color_bounding_boxes = color_detections.xyxy # (x_min, y_min, x_max, y_max)
            # depth_bounding_boxes = depth_detections.xyxy

            # draw bounding boxes
            color_annotated_frame = self.bounding_box_annotator.annotate(scene=color, detections=color_detections)
            # depth_annotated_frame = self.bounding_box_annotator.annotate(scene=rect_depth_colormap, detections=depth_detections)

            # create date profiles
            profiles = []
            for box in color_bounding_boxes:
                profile = Date_Profile()
                # assign profile number
                # profile.id = self.profile_counter

                # calculate approximate area and estimated weight
                profile.appx_area = (box[2] - box[0]) * (box[3] - box[1])
                profile.est_weight = (settings.return_setting("weight_estimation_m") * profile.appx_area) + settings.return_setting("weight_estimation_b")

                # calculate the box centroid/ position
                cx = int((box[2] + box[0])/2)
                cy = int((box[3] + box[1])/2)
                profile.position = np.array([cx, cy])

                profiles.append(profile)

            return profiles, color_annotated_frame
        else:
            return None, None

    def get_base_profiles(self):
        self.base_profiles, _ = self.detect_dates()

    def get_compare_profiles(self):
        self.compare_profiles, self.compare_frame = self.detect_dates()

    def find_matches(self):
        matches = 0
        self.match_attempts += 1
        # find distance between frame one profiles and frame two profiles
        for base_profile in self.base_profiles:
            for compare_profile in self.compare_profiles:
                distance = np.linalg.norm(base_profile.position - compare_profile.position)
                # match found?
                if distance <= settings.return_setting("match_distance"): # yes
                    # transfer profile id 
                    compare_profile.id = base_profile.id
                    # stop updating the weight if the compare profile is past the "count line"
                    count_line = (end_x - start_x) - settings.return_setting("count_line_offset")
                    compare_profile.est_weight = base_profile.est_weight if compare_profile.position[1] > count_line else compare_profile.est_weight
                    base_profile.matched = True
                    matches += 1
                    break

        if matches <= len(self.base_profiles) * settings.return_setting("match_percent"): # not successful, increment base profile position
            for base_profile in self.base_profiles:
                base_profile.position[1] += settings.return_setting("base_profile_translation")
            # attempt to find match again if within allowed iterations
            if self.match_attempts <= settings.return_setting("match_attempts"):
                # clear compare profile ids and reset variables
                for profile in self.compare_profiles: profile.id = None
                for profile in self.base_profiles: profile.matched = False
                self.find_matches()
            else:
                # print(f"Could not find matches within {settings.return_setting("match_attempts")} iterations")
                return False
        else: # successful! create new profiles
            # print(f"Matches found in {self.match_attempts} iterations")
            return True

    def handle_matches(self):
        count_line = (end_x - start_x) - settings.return_setting("count_line_offset")

        # take care of profiles that have left the frame
        for profile in self.base_profiles:
            if profile.position[1] > count_line and profile.id is not None and profile.id not in self.counted:
                self.counted.append(profile.id)
                self.count+=1
                self.weight+=profile.est_weight
                # reflect that athe profile has been counted in the compare profiles
                for c_profile in self.compare_profiles:
                    if c_profile.id == profile.id:
                        c_profile.id = None

        self.base_profiles = list()
        # assign ids to matched profiles in the compare list
        for profile in self.compare_profiles:
            if profile.id == None and profile.position[1] < count_line:
                profile.id = self.profile_counter
                self.profile_counter+=1
            
            self.base_profiles.append(profile)

    def work(self):
        if len(self.base_profiles) == 0:
            self.get_base_profiles()
        self.get_compare_profiles()
        matches_found = self.find_matches()
        
        # empty counted after some time
        if time() - self.counted_last_empty_time > 10:
                self.counted_last_empty_time = time()
                self.counted = []

        if matches_found:
            self.handle_matches()
        else:
            # reset profiles by defining new base profiles
            self.base_profiles, _ = self.detect_dates()

        #cv2.putText(self.compare_frame, str(self.weight), (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        for profile in self.base_profiles:
            cv2.putText(self.compare_frame, str(round(profile.est_weight, 1)), tuple(profile.position), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        # print(self.compare_frame.shape)
        count_line = int((end_x - start_x) - settings.return_setting("count_line_offset"))
        cv2.line(self.compare_frame, (0, count_line), (end_y, count_line), (255, 255, 255), thickness=1)
        #cv2.circle(self.compare_frame, (1000, 300), 10, (255), thickness=1)

        # reset variables
        self.match_attempts = 0
        self.compare_profiles = list()

        return self.count, self.weight, self.compare_frame
    
    def camera_connected(self):
        return camera_connected

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
        pipe.stop() if camera_connected else 0
    

        



        
