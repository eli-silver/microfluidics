# Image acquisition scripts
The Python scripts in this folder will acquire the red, green, blue, black, white, and test images used in the rest of this work.  There are three scripts, of which you probably only need to worry about one, which is ``measure_colour_response.py``.  It uses ``argparse`` to deal with command-line arguments, so try running ``python measure_colour_response.py --help`` to get more information on the options.

## Installing
These Python scripts are deliberately not provided as a pip-installable module, as they depend on a fork of ``picamera`` which we have added features to.  Distributing this code on pip would therefore be counterproductive, because it won't work properly with the upstream version of ``picamera``.  Instead, simply run the script by copying this folder (or cloning the repository).  You will, however, need to install the dependencies before it will run.  These should be fairly standard packages if you do any amount of scientific or image processing work - but installing them from scratch on a new Raspberry Pi can take a while.  We strongly recommend using a recent Raspbian build, and Python 3.  Recent builds of Raspbian will download pre-built wheels for numpy, for example, which saves several hours of compilation time.  If you try installing the dependencies and it takes a very long time or failes, most likely you need to enable installation from piwheels.

This code should work on Python 2 or Python 3.

The dependencies are:
* ``numpy``
* ``matplotlib``
* ``pyyaml``
* ``pyserial``
* A forked version of ``picamera`` from [this wheel](https://github.com/rwb27/picamera/releases/download/v1.13.1b0/picamera-1.13.1b0-py3-none-any.whl)

To obtain the forked version of ``picamera``, you can find a pre-compiled wheel on the [release page](https://github.com/rwb27/picamera/releases/tag/v1.13.1b0).  There is a [direct link to the wheel](https://github.com/rwb27/picamera/releases/download/v1.13.1b0/picamera-1.13.1b0-py3-none-any.whl) for convenience.  Visit the relevant [branch on github](https://github.com/rwb27/picamera/tree/lens-shading) to see the source.  We hope these features will be incorporated upstream in the future, once we have adapted our changes to fit with the upstream codebase.

## Usage
Run the ``measure_colour_response.py`` script - and use ``--help`` to see a full list of options.  The basic version of the experiment, where you change the illumination manually, can be run with:
```
python measure_colour_response.py --manual_illumination --output <data/your/directory/>
```
This will prompt you manually to change the illumination.  If you would like to save an additional test image (e.g. the colour wheels), you can do so:
```
python measure_colour_response.py --manual_illumination --output <data/your/directory/> --additional_images colour_wheels
```
You may add as many additional images as you like.

To use the NeoPixel and acquire all five images automatically, do:
```
python measure_colour_response.py --output <data/your/directory/>
```
It's probably tricky to combine this with ``--additional_images``.

## Disclaimer
We have refactored the code in this repository for clarity.  Previously, all the Python scripts were in one file, with no module structure.  If there are import-related issues, it may be that some of the files in the ``analysis/picam_raw_analysis`` folder need to be copied in to this folder.