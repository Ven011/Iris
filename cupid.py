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
from settings import settings
from multiprocessing import Pool

# initialize image rectifier
start_x = 0
start_y = 0
end_x = 720
end_y = 1280
# ^ for image cropping

# initialize camera
pipe = rs2.pipeline()
cfg = rs2.config()
cfg.enable_stream(rs2.stream.color, 1280, 720, rs2.format.bgr8, 30)
profile = None
camera_connected = True

try:
    profile = pipe.start(cfg)
except RuntimeError as e:
    print(e)
    camera_connected = False

class Date_Profile:
    def __init__(self, id=None, appx_area=None, est_weight=None, position=None):
        self.id = id
        self.appx_area = appx_area
        self.est_weight = est_weight
        self.position = position
        self.matched = False
        self.patch = None
        self.mask = None

def refine(profile):
    # define range of non-date pixels
    low = np.array([0, 0, 100])
    high = np.array([179, 255, 255])

    # convert profile image patch to hsv
    patch_hsv = cv2.cvtColor(profile.patch, cv2.COLOR_BGR2HSV)

    # create mask
    mask = cv2.inRange(patch_hsv, low, high)

    """ 
    Calculate number of non date in the (mxn) mask
    by multiplying the normalized mask with (mx1) vector of ones,
    obtain a vector who's elements represent the # of non date pixels in each 
    row of the mask. Find the sum of that vector's elements to obtain the # of
    non date pixels in the mask
    """

    # normalize the mask
    mask = mask/255
    # obtain the shape of the mask
    rows, cols = mask.shape
    # if mask is not square, place it in a square matrix (highly likely not square)
    size = np.max([rows, cols])
    square_mask = np.zeros((size, size), int)
    square_mask[0:rows, 0:cols] = mask
    # create multiplier
    multiplier = np.ones((size, 1), int)
    # calculate number of non date pixels
    num_non_date = int(sum(np.dot(square_mask, multiplier)))

    # calculate weight of non-date pixels and substract from profile weight
    non_date_weight = (settings.return_counter_setting("weight_estimation_m") * num_non_date) + settings.return_counter_setting("weight_estimation_b")
    profile.est_weight = profile.est_weight - non_date_weight

    return profile

class Cupid:
    def __init__(self):
        # drop first few camera frames
        pipe.wait_for_frames() if camera_connected else 0

        self.base_profiles = list()
        self.compare_profiles = list()
        self.compare_frame = None

        # date matching variables
        self.match_profile = None
        self.match_profile_angle = None
        self.match_profile_distance = None

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

    def refine_weights(self, profiles):
        refined_profiles = None

        with Pool(processes=1) as pool:
            refined_profiles = pool.map(refine, profiles)

        return refined_profiles

    def detect_dates(self):
        global camera_connected

        if camera_connected:
            # get and process depth frame
            try:
                frame_set = pipe.wait_for_frames()
            except RuntimeError as e:
                if not self.camera_connected():
                    camera_connected = False
                print(e)
            # depth_frame = frame_set.get_depth_frame()
            color_frame = frame_set.get_color_frame()
            color = np.asanyarray(color_frame.get_data())

            # run inference on the color and depth images
            color_results = self.model.infer(color)[0]

            # load results into the supervision detections API
            color_detections = sv.Detections.from_inference(color_results)

            # extract bounding boxes
            color_bounding_boxes = color_detections.xyxy # (x_min, y_min, x_max, y_max)

            # draw bounding boxes
            color_annotated_frame = self.bounding_box_annotator.annotate(scene=color, detections=color_detections)

            # create date profiles
            profiles = []
            for box in color_bounding_boxes:
                profile = Date_Profile()

                # save the profile patch from the frame
                int_box = [int(e) for e in box]
                profile.patch = color[int_box[1]:int_box[3], int_box[0]:int_box[2]]

                # calculate approximate area and estimated weight
                profile.appx_area = (box[2] - box[0]) * (box[3] - box[1])
                profile.est_weight = (settings.return_counter_setting("weight_estimation_m") * profile.appx_area) + settings.return_counter_setting("weight_estimation_b")

                # calculate the box centroid/ position
                cx = int((box[2] + box[0])/2)
                cy = int((box[3] + box[1])/2)
                profile.position = np.array([cx, cy])

                profiles.append(profile)

            # refine profile weight estimates by removing weight non-date pixels
            profiles = self.refine_weights(profiles) if len(profiles) > 0 else profiles

            return profiles, color_annotated_frame
        else:
            return None, None

    def get_base_profiles(self):
        self.base_profiles, _ = self.detect_dates()

    def get_compare_profiles(self):
        self.compare_profiles, self.compare_frame = self.detect_dates()

    def get_angle_and_distance(self, base_profile, compare_profile):
        # create a vector that represents the ideal direction of the date's movement
        base_position = base_profile.position
        ideal_date_position = np.array([base_position[0], base_position[1]+10])
        ideal_vector = ideal_date_position - base_position
        ideal_vector_mag = np.linalg.norm(ideal_vector)

        # create a vector between the base profile and the current compare profile
        compare_vector = compare_profile.position - base_position
        compare_vector_mag = np.linalg.norm(compare_vector)

        # calculate the angle between the ideal vector and the compare vector
        compare_angle = np.arccos((np.dot(ideal_vector, compare_vector)) / (ideal_vector_mag * compare_vector_mag))

        return compare_angle, compare_vector_mag

    def find_matches(self):
        matches = 0
        self.match_attempts += 1
        for base_profile in self.base_profiles:
            for compare_profile in self.compare_profiles:
                distance = np.linalg.norm(base_profile.position - compare_profile.position)
                # match found?
                if distance <= settings.return_counter_setting("match_distance"): # yes
                    # transfer profile id 
                    compare_profile.id = base_profile.id
                    # stop updating the weight if the compare profile is past the "count line"
                    count_line = (end_x - start_x) - settings.return_counter_setting("count_line_offset")
                    compare_profile.est_weight = base_profile.est_weight if compare_profile.position[1] > count_line else compare_profile.est_weight
                    base_profile.matched = True
                    matches += 1
                    break

        if matches <= len(self.base_profiles) * settings.return_counter_setting("match_percent"): # not successful
            return False
        else: # successful! create new profiles
            return True

    def handle_matches(self):
        count_line = (end_x - start_x) - settings.return_counter_setting("count_line_offset")

        # take care of profiles that have passed the count line
        for profile in self.compare_profiles:
            if profile.position[1] > count_line and profile.id is not None and profile.id not in self.counted:
                self.counted.append(profile.id)
                self.count+=1
                self.weight+=profile.est_weight
                # reflect that the profile has been counted in the compare profiles
                for c_profile in self.compare_profiles:
                    if c_profile.id == profile.id:
                        c_profile.id = None

        self.base_profiles = list()
        # assign ids to unmatched profiles in the compare list
        for profile in self.compare_profiles:
            if profile.id == None and profile.position[1] < count_line:
                profile.id = self.profile_counter
                self.profile_counter+=1
            
            self.base_profiles.append(profile)

    def work_tasks(self):
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

        for profile in self.base_profiles:
            cv2.putText(self.compare_frame, str(profile.id), tuple(profile.position), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        count_line = int((end_x - start_x) - settings.return_counter_setting("count_line_offset"))
        cv2.line(self.compare_frame, (0, count_line), (end_y, count_line), (255, 255, 255), thickness=1)

        # reset variables
        self.match_attempts = 0
        self.compare_profiles = list()

        return self.count, self.weight, self.compare_frame

    def work(self):
        global camera_connected
        try:
            return self.work_tasks()
        except Exception as e:
            if not self.camera_connected():
                camera_connected = False
            print(e)

    
    def camera_connected(self):
        global profile, camera_connected

        # Create a context object
        context = rs2.context()
        # Get a list of connected devices
        devices = context.query_devices()
        # Check if there are any connected devices
        if len(devices) > 0:
            self.attempt_camera_reconnect() if profile is None else 0
            camera_connected = True
            return True
        else:
            camera_connected = False
            return False
    
    def attempt_camera_reconnect(self):
        global profile
        try:
            profile = pipe.start(cfg)
        except RuntimeError as e:
            print(e)

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
    

        



        
