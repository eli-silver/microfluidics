from setuptools import setup, find_packages
from distutils.extension import Extension
from os import path

setup(
  name = 'picam_raw_analysis',
  version = '0.1',
  description = "Scripts to extract, manipulate, and characterise raw Picamera images",
  url = "https://gitlab.com/bath_open_instrumentation_group/picamera_cra_compensation/",
  author = "Richard Bowman",
  packages = find_packages(),
  ext_modules = [],
  install_requires = [
      "numpy",
      "scipy",
      "pyyaml",
      "pillow",
      "opencv-python",
  ]

)
