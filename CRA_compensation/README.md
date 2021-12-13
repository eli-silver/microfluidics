# Python code for analysing images to characterise the sensor and optics

## Contents
In this folder, you will find:
* Scripts to extract the raw data from Raspberry Pi camera images, and to generate correction tables.  It is packaged as a Python module ``picam_raw_analysis``.
* An iPython notebook that performs the analysis and generates the figures used in the manuscript.  This is ``comparing_calibrations.ipynb``.
* An ipython notebook dealing with fitting various different functions to the extracted corrections, ``modelling.ipynb``.

## Raw image module
The ``picam_raw_analysis`` module contains the code for loading raw images, separated from the notebook for clarity.  It does, however, duplicate some of the calibration code presented in the notebook for convenience.  You can perform colour calibration by running a submodule.  This accepts a folder of images (from which the calibration can be generated) and an image or images to calibrate.  The module can be run with ``python -m picam_raw_analysis.unmix_image --help`` (the ``--help`` option prints instructions).  As a significant fraction of the computation time is spent upsampling the colour calibration matrix, it's efficient to specify multiple images on the command line for conversion.  You can run the submodule ``picam_raw_analysis.unmixing_matrices`` to generate the unmixing matrix and save it to a file, but this is done at low resolution so it doesn't save all that much time.

### Installation
To install the module, clone this repository, then ``cd`` to this directory (``analysis/``).  You may then install the module with ``python setup.py install`` or ``pip install .``.

### Module documentation
Module documentation may be found on [readthedocs](https://picamera-raw-analysis.readthedocs.io/en/latest/).

## Difference between notebooks and command line scripts
The one difference between the unmixing method used in the command-line scripts and those used in the manuscript is that the command-line scripts work at full resolution.  Matrices are generated at lower resolution, but are then upsampled (using bilinear interpolation) before being applied to the images.  Additionally, we do not currently make any effort to copy over EXIF metadata from the source JPEG files to the output TIFF files.  This should be possible in a future revision of the module.
