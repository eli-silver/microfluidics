"""
This module takes in red, green, blue, white images, and calculates the
colour crosstalk that's happening.  We then invert this matrix to
undo the mixing.

(c) Richard Bowman 2019, released under GNU GPL v3 or later
"""
from __future__ import print_function
import numpy as np
from .extract_raw_image import load_raw_image
import sys
import os
import scipy.ndimage as ndimage
import yaml
import argparse

DOWNSAMPLING = 16

def bin(image, b=2):
    """Bin bxb squares of an image together"""
    w,h = image.shape[:2]
    new_shape = (w//b, b, h//b, b)
    if len(image.shape) > 2:
        new_shape += image.shape[2:]
    if w % b != 0 or h % b != 0:
        print("Warning: pixels are being dropped from the binned image!")
        image = image[:w - (w%b), :h - (h%b), ...]
    return image.reshape(new_shape).mean(axis=1).mean(axis=2)

def load_raw_image_and_bin(filename):
    """Load an image from the raw data in a jpeg file, and return a binned version."""
    pi_bayer_array = load_raw_image(filename)
    image = bin(pi_bayer_array.array, DOWNSAMPLING)
    # NB only 1/4 pixels are red or blue, and 2/4 are green.  Boost the values here to compensate for this:
    image *= np.array([4,2,4])[np.newaxis,np.newaxis,:] # correct for the black pixels
    image -= 64 # correct for the zero offset in the raw data
    return image

def load_run(folder, illuminations):
    """Load the R,G,B,W calibration images"""
    # and any additional images."""
    output = {}
    for k, rgb in illuminations.items():
        image_path = os.path.join(folder, "capture_r{}_g{}_b{}.jpg".format(*rgb))
        try:
            output[k] = load_raw_image_and_bin(image_path)
        except:
            raise IOError("Could not open {}".format(image_path))
    #for f in os.listdir(folder):
    #    if f.startswith("additional_image_"):
    #        output[f[17:-4]] = load_raw_image_and_bin(os.path.join(folder, f))
    return output

def crosstalk_matrices(run):
    """Construct a 4d array of colour crosstalk information.
    
    This function returns a 3x3 matrix at each pixel of the calibration images.
    Inverting this matrix """
    return np.stack([run[k] for k in ['R', 'G', 'B']], axis=3)/run['W'][:,:,:,np.newaxis]

def central_colour(image):
    # Find the colour of the central portion of an image
    w,h = image.shape[:2]
    return np.mean(np.mean(image[w*4//9:w//2+w*5//9, h*4//9:h*5//9, ...], axis=0), axis=0)

def colour_unmixing_matrices(cal, colour_target="rgb", smoothing=None):
    """Return a matrix that turns the camera's recorded colour back into "perfect" colour
    
    cal should be a calibration run (dictionary) with, as a minimum, W, R, G, and B images.
    
    calibration : dict 
        a dictionary with (at least) R, G, B, and W images
    colour_target: string
        "rgb" (default) or "centre".  "rgb" will unmix to fully saturated colours,
        while "centre" will unmix so the edges of the image match the centre of the image.
    smoothing: None or float
        (default) for no smoothing, or a number (in pixels) to apply a Gaussian
        blur to the compensation matrices.
    
    returns:
        an NxMx3x3 unmixing matrix
    """
    crosstalk = crosstalk_matrices(cal)
    compensation_matrices = np.empty_like(crosstalk)
    # Doing this with a massive for loop is inefficient, but easy to read!
    for i in range(crosstalk.shape[0]):
        for j in range(crosstalk.shape[1]):
            compensation_matrices[i,j,:,:] = np.linalg.inv(crosstalk[i,j,:,:])
    if colour_target == "centre" or colour_target == "center":
        central_response = np.array([central_colour(cal[k]/cal['W']) for k in ['R', 'G', 'B']])
        print("Adding up the R/G/B images, we get:", np.sum(central_response, axis=0))
        compensation_matrices = np.sum(compensation_matrices[:,:,:,np.newaxis,:]
                              *central_response[np.newaxis,np.newaxis,:,:,np.newaxis], 
                              axis=-3)
    if smoothing is not None:
        compensation_matrices = ndimage.gaussian_filter(compensation_matrices, (smoothing,smoothing,0,0), order=0)
    return compensation_matrices

def colour_unmix_image(image, calibration, **kwargs):
    """Take a test image, and a set of W/R/G/B calibration images, and unmix the test image.
    
    Arguments:
    image: NxNx3 image as a numpy.ndarray
    calibration: a dictionary with (at least) R, G, B, and W images
    keyword arguments are passed to colour_unmixing_matrices
    
    Returns:
    an NxMx3 ndarray containing the unmixed image
    """
    compensation = colour_unmixing_matrices(calibration, **kwargs)
    # This is a 3x3 matrix multiplication for each pixel.  It's written as a sum here because
    # that is significantly more efficient, and results in me spending less time thinking
    # about how matrix indices and array indices may or may not be the same way round!
    return np.sum(compensation * image[:,:,np.newaxis,:], axis=-1)

def add_unmixing_args(parser):
    """Add the arguments for colour unmixing to an argparse.ArgumentParser"""
    parser.add_argument("calibration", help="Path to a folder containing"
                        " the red, green, blue, and white images, or to a YAML file "
                        "containing a previously-calculated unmixing matrix.  If a "
                        "folder is specified, files should be named capture_r%d"
                        "_g%d_b%d.jpg, where each %d is either 0 or 255.")
    parser.add_argument("--colour_target", default="centre", choices=["center", "centre", "rgb"],
                        help="Whether to normalise colour response relative to the centre"
                        "of the sensor (default), or unmix to fully-saturated colours.")
    parser.add_argument("--smoothing", type=float, help="Smoothing to apply to the "
                        "unmixing matrices, in units of 16-pixel blocks.  The default "
                        "is not to apply any smoothing.")
    return parser

def calculate_calibration(args):
    """Based on the command-line args supplied, calculate unmixing and vignetting corrections"""
    # If we supplied a pre-calculated yaml file, just use that!
    if args.calibration.endswith(".yaml"):
        with open(args.calibration, "r") as infile:
            return yaml.unsafe_load(infile) # NB this is not robust to malicious YAML!
    
    # Otherwise, load a folder of images.
    illuminations = {"W":(255,255,255), "R":(255,0,0), "G":(0,255,0), "B":(0,0,255), } #"K":(0,0,0)} #K is currently unused
    cal = load_run(args.calibration, illuminations)
    
    compensation_matrices = colour_unmixing_matrices(cal, colour_target=args.colour_target, smoothing=args.smoothing)
    return {"unmixing_matrices": compensation_matrices, "white_image": cal['W']}


    


def main():
    """Construct a colour unmixing matrix and save it to a YAML file"""
    parser = argparse.ArgumentParser(description="Calculate a colour unmixing matrix from"
                                     " a folder of RGBW images.")
    add_unmixing_args(parser)
    parser.add_argument("--output", help="Colour unmixing matrices will be saved to "
                        "this file, in YAML format", default="unmixing_matrices.yaml")
    args = parser.parse_args()

    calibration = calculate_calibration(args)
    with open(args.output, "w") as outfile:
        yaml.dump(calibration, outfile)
    print("Saved calibration matrices to {}".format(args.output))

if __name__ == "__main__":
    main()