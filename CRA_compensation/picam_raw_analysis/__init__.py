"""
This module contains utilities for manipulating raw images from the Raspberry Pi
Camera Module, version 2.

If you use it with images taken with other cameras, including version 1, it will
most likely fail.

You can use this module on the command line to extract raw data from a JPEG file:

.. code-block:: bash

    python -m picam_raw_analysis.extract_raw_image image.jpg


There is a script provided that will convert a white image into a lens shading
table, in YAML format.  To run this, use:

.. code-block:: bash

    python -m picam_raw_analysis.lst_from_raw_white_image path/to/white/image.jpg --output lens_shading.yaml

There is also a script to completely compensate an image, using the raw data in that image
together with red, green, blue, and white calibration images.  This can be run with:

.. code-block:: bash

    python -m picam_raw_analysis.unmix_image path/to/calibration/folder image.jpg

Most of the functionality lives in submodules, but ``load_raw_image`` and ``extract_file``
are available at the top level as well as in the ``extract_raw_image`` submodule.

Finally, this module does not depend on ``picamera`` and should run (in Python 3) on any 
platform.  To achieve this, ``picamera_array`` has been copied into this module, and 
``mo_stub`` provides a dummy MMAL import.  I'm not the author of ``picamera.array`` and
it is copied here (in modified form) under the GPL.

This module has been written with the intention of it working in Python 2 or 3, but it has
mostly been tested in Python 3.

(c) Richard Bowman 2019, released under GNU GPL v3
"""

from .extract_raw_image import load_raw_image, extract_file
