"""
Generate a lens shading table based on previously-measured images and test it on the camera.

This script uses a raw white image to correct the lens shading table of a Raspberry Pi camera module.
The revised lens shading table is uploaded to the camera, and images are acquired with it to 
test it's working properly.

It can be run from the command line:

.. code-block:: bash

    python -m picam_raw_analysis.lst_from_raw_white_image path/to/white/image.jpg --output lens_shading.yaml

Use the ``--help`` flag to obtain a usage message.

Copyright 2019 Richard Bowman, released under GNU GPL v3

"""

import numpy as np
from contextlib import closing
import time
import os
import argparse
import yaml
from .extract_raw_image import load_raw_image

def channels_from_bayer_array(bayer_array):
    """Given the 'array' from a PiBayerArray, return the 4 channels."""
    bayer_pattern = [(i//2, i%2) for i in range(4)]
    channels = np.zeros((4, bayer_array.shape[0]//2, bayer_array.shape[1]//2), dtype=bayer_array.dtype)
    for i, offset in enumerate(bayer_pattern):
        # We simplify life by dealing with only one channel at a time.
        channels[i, :, :]  = np.sum(bayer_array[offset[0]::2, offset[1]::2, :], axis=2)

    return channels

def lst_from_channels(channels):
    """Given the 4 Bayer colour channels from a white image, generate a LST."""
    full_resolution = np.array(channels.shape[1:]) * 2 # channels have been binned
    #lst_resolution = list(np.ceil(full_resolution / 64.0).astype(int))
    lst_resolution = [(r // 64) + 1 for r in full_resolution]
    # NB the size of the LST is 1/64th of the image, but rounded UP.
    print("Generating a lens shading table at {}x{}".format(*lst_resolution))
    lens_shading = np.zeros([channels.shape[0]] + lst_resolution, dtype=np.float)
    for i in range(lens_shading.shape[0]):
        image_channel = channels[i, :, :]
        iw, ih = image_channel.shape
        ls_channel = lens_shading[i,:,:]
        lw, lh = ls_channel.shape
        # The lens shading table is rounded **up** in size to 1/64th of the size of
        # the image.  Rather than handle edge images separately, I'm just going to
        # pad the image by copying edge pixels, so that it is exactly 32 times the
        # size of the lens shading table (NB 32 not 64 because each channel is only
        # half the size of the full image - remember the Bayer pattern...  This
        # should give results very close to 6by9's solution, albeit considerably 
        # less computationally efficient!
        padded_image_channel = np.pad(image_channel, 
                                      [(0, lw*32 - iw), (0, lh*32 - ih)],
                                      mode="edge") # Pad image to the right and bottom
        print("Channel shape: {}x{}, shading table shape: {}x{}, after padding {}".format(iw,ih,lw*32,lh*32,padded_image_channel.shape))
        # Next, fill the shading table (except edge pixels).  Please excuse the
        # for loop - I know it's not fast but this code needn't be!
        box = 3 # We average together a square of this side length for each pixel.
        # NB this isn't quite what 6by9's program does - it averages 3 pixels
        # horizontally, but not vertically.
        for dx in np.arange(box) - box//2:
            for dy in np.arange(box) - box//2:
                ls_channel[:,:] += padded_image_channel[16+dx::32,16+dy::32] - 64
        ls_channel /= box**2
        # The original C code written by 6by9 normalises to the central 64 pixels in each channel.
        #ls_channel /= np.mean(image_channel[iw//2-4:iw//2+4, ih//2-4:ih//2+4])
        # I have had better results just normalising to the maximum:
        ls_channel /= np.max(ls_channel)
        # NB the central pixel should now be *approximately* 1.0 (may not be exactly
        # due to different averaging widths between the normalisation & shading table)
        # For most sensible lenses I'd expect that 1.0 is the maximum value.
        # NB ls_channel should be a "view" of the whole lens shading array, so we don't
        # need to update the big array here.
     
    # What we actually want to calculate is the gains needed to compensate for the 
    # lens shading - that's 1/lens_shading_table_float as we currently have it.
    gains = 32.0/lens_shading # 32 is unity gain
    gains[gains > 255] = 255 # clip at 255, maximum gain is 255/32
    gains[gains < 32] = 32 # clip at 32, minimum gain is 1 (is this necessary?)
    lens_shading_table = gains.astype(np.uint8)
    return lens_shading_table[::-1,:,:].copy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Construct and evaluate a lens shading table from a white image")
    parser.add_argument("white_image")
    parser.add_argument("--output", default="microscope_settings_with_lst.yaml", help="Output filename for microscope settings file to save the lens shading table into.  Will be overwritten if it exists.")
    parser.add_argument("--settings_file", default=None, help="Optionally supply a settings file into which the lens shading table will be inserted.  Other settings are not changed.")
    args = parser.parse_args()

    if args.settings_file is not None:
        with open(args.settings_file, "r") as infile:
            camera_settings = yaml.load(infile)
    else:
        camera_settings = {}


    # Use the calibration image if specified
    calibration_image = args.white_image
    assert os.path.isfile(calibration_image)
    print("Using {} as the reference image".format(calibration_image))
    raw_image = load_raw_image(calibration_image).array

    # Now we need to calculate a lens shading table that would make this flat.
    # raw_image is a 3D array, with full resolution and 3 colour channels.  No
    # demosaicing has been done, so 2/3 of the values are zero (3/4 for R and B
    # channels, 1/2 for green because there's twize as many green pixels).
    channels = channels_from_bayer_array(raw_image) 
    lens_shading_table = lst_from_channels(channels)
    
    camera_settings['lens_shading_table'] = lens_shading_table
    with open(args.output, "w") as outfile:
        yaml.dump(camera_settings, outfile)

