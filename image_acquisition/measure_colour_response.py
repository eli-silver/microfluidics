"""
Measuring the colour response of a Raspberry Pi camera

This script uses an RGB LED (via an Arduino) to find the response
of the Raspberry Pi camera to red, green, and blue light.  This
goes further than the lens shading correction, as it measures the
off-diagonal terms (i.e. crosstalk between colour channels).  NB
the assumption that we can produce a valid correction based on raw
images isn't necessarily correct; in general it is probably 
necessary to use some sort of closed-loop process to get something
that works reliably with processed images.

(c) Richard Bowman 2018, released under GPL v3

"""
import numpy as np
from picamera import PiCamera
import neopixel
from picamera.array import PiRGBArray
import matplotlib
matplotlib.use('Agg') # Don't use X in case we're running headless
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from set_colour import SingleNeoPixel, ManualIllumination
from contextlib import closing
import os.path 
import time
import threading
import yaml
import argparse

def rgb_image(camera, resize=None, **kwargs):
    """Capture an image and return an RGB numpy array"""
    with PiRGBArray(camera, size=resize) as output:
        camera.capture(output, format='rgb', resize=resize, **kwargs) 
        return output.array

def flat_lens_shading_table(camera):
    """Return a flat (i.e. unity gain) lens shading table.
    
    This is mostly useful because it makes it easy to get the size
    of the array correct.  NB if you are not using the forked picamera
    library (with lens shading table support) it will raise an error.
    """
    print("Checking for lens shading support...", end="")
    if not hasattr(PiCamera, "lens_shading_table"):
        print("not present.")
        raise ImportError("This program requires the forked picamera library with lens shading support")
    else:
        print("present")

    print("Generating a flat lens shading table")
    
    lens_shading_table = np.zeros(camera._lens_shading_table_shape(), dtype=np.uint8) + 32
    return lens_shading_table

def auto_expose_to_white(camera, led):
    """Freeze the settings after auto-exposing to white illumination"""
    print("Turning on the LED and letting the camera auto-expose", end="")
    led.set_rgb(255,255,255)
    camera.start_preview()
    for i in range(6):
        print(".", end="")
        time.sleep(0.5)
    print("done")

    print("Freezing the camera settings...")
    camera.shutter_speed = camera.exposure_speed
    print("Shutter speed = {}".format(camera.shutter_speed))
    camera.exposure_mode = "off"
    print("Exposure Mode 'off'")
    g = camera.awb_gains
    camera.awb_mode = "off"
    camera.awb_gains = g
    print("Auto white balance 'off', AWB gains are {}".format(g))
    print("Analogue gain: {}, Digital gain: {}".format(camera.analog_gain, camera.digital_gain))
    print("Camera iso value: {}".format(camera.iso))

    print("Adjusting shutter speed to avoid saturation", end="")
    for i in range(3):
        print(".", end="")
        camera.shutter_speed = int(camera.shutter_speed * 230.0 / np.max(rgb_image(camera)))
        time.sleep(1)
    print("done")

def save_settings(camera, output="output/camera_settings.yaml"):
    """Save the camera settings to a YAML file"""
    camera_settings = {k: getattr(camera, k) for k in ['iso', 'analog_gain', 'digital_gain', 'shutter_speed', 'awb_gains', 'awb_mode', 'exposure_mode']}
    #camera_settings['lens_shading_table'] = np.array(camera.lens_shading_table) # We can't serialise the memoryview object directly
    with open(output, "w") as outfile:
        yaml.dump(camera_settings, outfile)

def restore_settings(camera, filename, ignore=[]):
    """Load camera settings from a YAML file"""
    print("Turning on camera", end="")
    camera.start_preview()
    for i in range(6):
        print(".", end="")
        time.sleep(0.5)
    print("done")
    print("Loading settings from file")

    with open(filename, "r") as infile:
        settings = yaml.load(infile, Loader=yaml.UnsafeLoader)
        for k, v in settings.items():
            print(k)
            print(v)
            if k not in ignore:
                setattr(camera, k, v)      
    for i in range(6):
        print(".", end="")
        time.sleep(0.5)
    print("done")
    print("Shutter speed = {}".format(camera.shutter_speed))
    print("Exposure Mode: {}".format(camera.exposure_mode))
    g = camera.awb_gains
    print("AWB Mode: {}".format(camera.awb_mode))
    camera.awb_gains = g
    print("AWB gains: {}".format(g))
    print("Analogue gain: {}, Digital gain: {}".format(camera.analog_gain, camera.digital_gain))
    print("Camera iso value: {}".format(camera.iso))
    print("after iso, Analog gain: {}, Digital gain: {}".format(camera.analog_gain, camera.digital_gain))

def measure_response(camera, led, output_prefix, 
                     rgb_values=[(255,255,255), (255,0,0), (0,255,0), (0,0,255), (0,0,0)]):
    """Measure the camera's response to different illuminations"""
    fig, ax = plt.subplots(4, len(rgb_values), figsize=(8,4))
    for i, rgb in enumerate(rgb_values):
        print("Setting illumination to {}".format(rgb))
        led.set_rgb(*rgb)
        time.sleep(1)
        print("Capturing raw image")
        camera.capture(output_prefix + "_r{}_g{}_b{}.jpg".format(*rgb), bayer=True)
        rgb = rgb_image(camera)
        channels = ["red", "green", "blue"]
        for j, channel in enumerate(channels):
            cm = LinearSegmentedColormap(channel+"map",
                    {c: [(0,0,0),(1,1,1)] if c==channel 
                        else [(0,0,0),(0.95,0,1),(1,1,1)] 
                        for c in channels})
            ax[j,i].imshow(rgb[:,:,j], vmin=0, vmax=255, cmap=cm)
        ax[3,i].imshow(rgb[:,:,:], vmin=0, vmax=255)
    led.set_rgb(255,255,255)
    return fig, ax

def timed_image_capture(camera, output, tDelta, tTotal, imCount):
    """Captures a series of images at regular interval"""
    # tDelta is the interval of image capture#
    # tTotal is the time period over which images are captured
    nextPictureTime = time.time()
    fileNames = []
    
    lastPictureTime = float(time.time())
    currPictureTime = float(time.time())
    collectData = True
    numPictures = int(np.ceil(tTotal/tDelta))
    while collectData:
        if imCount <= numPictures:
            if time.time() >= nextPictureTime:
                nextPictureTime += tDelta
                imCount+=1
                ct = time.ctime()
                lastPictureTime = currPictureTime
                currPictureTime = float(time.time())
                print ("Image captured at : %s" % ct)
                timeStr = str(time.time())
                print( currPictureTime-lastPictureTime )
                timeStr_connected = timeStr.replace(".", "_")
                fileName = str(imCount) + "_" + timeStr_connected + ".jpg"
                fileNames.append(fileName)
                camera.capture(output + str(imCount)+"_"+ timeStr_connected + ".jpg", bayer=True)
        else:
            collectData = False
    
    filepath = os.path.join(output, 'file_names.txt')
    f = open(filepath, "a")
    for name in fileNames:
        f.writelines(name + "\n")
    f.close()

def main():
    parser = argparse.ArgumentParser(description="Measure the response of the Raspberry Pi camera to different illuminations")
    parser.add_argument("--output", help="path to the output directory (must not exist)", default="output/measure_colour_response")
    parser.add_argument("--additional_images", nargs="*", help="After running the experiment, prompt you with these names to take some additional images (with the same frozen settings and flat LST).", default=[])
    parser.add_argument("--manual_illumination", action="store_true", help="Don't attempt to use a NeoPixel, instead just prompt you to change the illumination manually")
    parser.add_argument("--skip_autoexpose", action="store_true", help="Don't run an auto-expose/freeze when the camera starts up - mostly useful with a settings file.  NB the auto-expose runs **after** loading the settings.")
    parser.add_argument("--settings_file", help="Load settings from a file", default=None)
    parser.add_argument("--skip_calibration", action="store_true", help="Skips the WRGB calibration sequence and auto_expose. Use this after a calibration run in conjunction with saved settings.")
    parser.add_argument("--timed_data", nargs="*", type=float, help="Requires two arguments 'x y'. Takes an image with static camera settings every 'x' seconds for 'y' seconds and saves raw data.", default = [])
    args = parser.parse_args()

    # First turn off lens shading correction
    with PiCamera() as cam:
        flat_lens_shading = flat_lens_shading_table(cam)
    # Loading this lens shading table requires restarting the camera
    with PiCamera(lens_shading_table=flat_lens_shading, resolution=(640,480)) as camera, \
         (ManualIllumination() if args.manual_illumination else SingleNeoPixel()) as led:
        # Load settings from a file
        if args.settings_file is not None:
            time.sleep(1)
            restore_settings(camera, args.settings_file)
            

        # Set the camera up so white illumination doesn't saturate
        if not args.skip_autoexpose:
            #if not args.skip_calibration:
            auto_expose_to_white(camera, led)
        # Save the settings we're currently using
        save_settings(camera, args.output + "camera_settings.yaml")
        
        # Acquire images under red, green, and blue illumination
        if not args.skip_calibration:
            print("Taking measurement")
            fig, ax = measure_response(camera, led, args.output + "capture")
            plt.savefig(args.output + "preview.pdf")

        if len(args.additional_images) > 0:
            print("Taking additional images")
            for name in args.additional_images:
                input("Please set up for image '{}' and press enter.".format(name))
                camera.capture(args.output + "additional_image_" + name + ".jpg", bayer=True)
                
        
        if len(args.timed_data)==2:
            tDelta = args.timed_data[0]    #time between images in nilliseconds
            tTotal = args.timed_data[1]    #durration of data collection
            input("Preparing to take images every '{}' seconds for '{}' seconds. Press enter to begin".format(tDelta,tTotal) )
            print ("Data collection begun at : %s" % time.ctime())
            
            timed_image_capture(camera, args.output, tDelta, tTotal,0)
               
            
            print ("Data collection completed at : %s" % time.ctime())

            

if __name__ == "__main__":
    main()

  
