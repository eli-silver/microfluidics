"""
This module handles the extraction of raw data from JPEG + RAW files saved by the Raspberry Pi
camera module, v2.  It has not been tested with v1, and most likely will fail; there is no 
logic included for determining the sensor version from the EXIF metadata.

It can be run from the command line:

.. code-block:: bash

    python -m picam_raw_analysis.extract_raw_image image.jpg

Multiple filenames may be specified, and the output images will be saved with the same
filenames plus plus a suffix for each output type.  All three output types will be generated
for each input file:

    ``_raw16.tif``:
        16-bit TIFF image with the full dynamic range of the 10-bit raw image.  Each pixel
        will have a value ranging from 0 to 1024.

    ``_raw8.tif``:
        8-bit TIFF image containing the top 8 bits of the 10-bit raw image.

    ``_exif.txt``:
        Extracted metadata from the JPEG file, in plain text format.

All of these functions are also accessible through the member functions of the module.

Copyright 2019 Richard Bowman, released under GNU GPL v3

"""

from __future__ import print_function
import numpy as np
import time
from . import picamera_array # NB this is NOT part of picamera - it's been extracted and hacked slightly
import cv2
import PIL.Image
import PIL.ExifTags
from .dump_exif import exif_data_as_string
import sys

full_resolution=(3280,2464)

class DummyCam(object):
    # This is a dummy PiCamera-like object that allows us to read raw images.
    # NB this will only work for version 2 of the camera at present.
    resolution = full_resolution
    revision = 'IMX219'
    sensor_mode = 0
    
def load_raw_image(filename, ArrayType=picamera_array.PiSharpBayerArray, open_jpeg=False):
    """Load the raw image data (and optionally the processed image data and EXIF metadata) from a file"""
    with open(filename, mode="rb") as file:
        jpeg = file.read()
    cam = DummyCam()
    bayer_array = ArrayType(cam)
    bayer_array.write(jpeg)
    bayer_array.flush()
    
    if open_jpeg:
        jpeg = PIL.Image.open(filename)
        # with thanks to https://stackoverflow.com/questions/4764932/in-python-how-do-i-read-the-exif-data-for-an-image
        exif_data = jpeg._getexif()
        return bayer_array, jpeg, exif_data
    return bayer_array
    
def extract_file(filename):
    """Extract metadata and raw image from a file, saving it as a text file and 8 and 16-bit TIFF images."""
    print("converting {}...".format(filename))
    bayer_array, jpeg, exif_data = load_raw_image(filename, open_jpeg=True)
    
    # extract EXIF metadata from the image
    root_fname, junk = filename.rsplit(".j", 2) #get rid of the .jpeg extension
    with open(root_fname + "_exif.txt", "w") as f:
        f.write(exif_data_as_string(jpeg))
    
    # extract raw bayer data
    cv2.imwrite(root_fname + "_raw16.tif", bayer_array.demosaic()*64)
    cv2.imwrite(root_fname + "_raw8.png", (bayer_array.demosaic()//4).astype(np.uint8))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {} <filename.jpg> ...".format(sys.argv[0]))
        print("Specify one or more filenames corresponding to Raspberry Pi JPEGs including raw Bayer data.")
        print("Each file will be processed, to produce three new files:")
        print("<filename>_raw16.tif will contain the full raw data as a 16-bit TIFF file (the lower 6 bits are empty).")
        print("<filename>_raw8.png will contain the top 8 bits of the raw data, in an easier-to-handle file.")
        print("<filename>_exif.txt will contain the EXIF metadata extracted as a text file - this includes analogue gain.")
        sys.exit(0)
        
    for filename in sys.argv[1:]:
        extract_file(filename)