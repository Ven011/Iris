#!/usr/bin/python3

"""
    Class that handles the rectification of the camera tilt
    in order to mitigate its affects on the depth image
"""

import numpy as np
import pyrealsense2 as rs2
import cv2

from multiprocessing import Pool

class Rectifier:
    def __init__(self, crop_start_x, crop_end_x, crop_start_y, crop_end_y, surface_distance=0.475) -> None:
        self.surface_d = surface_distance * 1000

        # Define the crop region
        self.start_x = crop_start_x
        self.start_y = crop_start_y
        self.end_x = crop_end_x
        self.end_y = crop_end_y
    
    def rectify_patch(self, patch):
        # normalize the patch to a max of the value specified by surface depth
        patch = (patch * self.surface_d) / np.max(patch)

        # map the patch values from the depth in meters to a range between 0 and 255
        min = np.min(patch)
        max = np.max(patch)
        new_max = 255
        new_min = 0

        if (max - min > 0):
            new_patch = (((patch - min) * (new_max - new_min))/(max - min)) + new_min
        else:
            new_patch = (((patch - min) * (new_max - new_min))/(0.01)) + new_min

        # create a mask of the object edges
        if len(set(np.hstack(new_patch))) > 3:
            new_patch = np.ones_like(new_patch, dtype=np.uint8) * 255
        else:
            new_patch = np.zeros_like(new_patch, dtype=np.uint8) * 0
            
        return new_patch

    def process_patches(self, patches):
        with Pool(processes=4) as pool:
            processed_patches = pool.map(self.rectify_patch, patches)

        return processed_patches

    def get_rectified(self, depth_frame: rs2.depth_frame, patch_depth=2):
        # depth data as a numpy array
        depth_data = np.asanyarray(depth_frame.get_data())

        # define patches
        p_x = list(range(self.start_x, self.end_x+1, int((self.end_x - self.start_x)/patch_depth)))
        p_y = list(range(self.start_y, self.end_y+1, int((self.end_y - self.start_y)/patch_depth)))

        # prepare image patches for processing
        patches = [depth_data[p_x[x]:p_x[x+1], p_y[y]:p_y[y+1]] for x in range(patch_depth) for y in range(patch_depth)]

        # rectify patches
        new_patches = self.process_patches(patches)
        
        # create new depth image
        rows = [np.hstack(tuple(new_patches[(row * patch_depth):((row * patch_depth)+patch_depth)])) for row in range(patch_depth)]
        new_depth = np.vstack(tuple(rows[0:patch_depth]))

        # apply color map
        depth_colormap = cv2.applyColorMap(np.uint8(new_depth), cv2.COLORMAP_JET)

        return depth_colormap, new_depth

