# Simple script to turn on NeoPixel LED from within OpenFlexure GUI
# Eli Silver 2021
#
# Adapted from Adafruit Industries rPi Neopixel Example 
#
# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import board
import neopixel

#NeoPixel signal pin must be cononected to D10, D12, D18, D21
pixel_pin = board.D10

num_pixels = 1

# LED Used: WS2812b
# This led uses GRB rather than RGB color definition. Setting ORDER
#   allows future commands to use normal (R,G,B) color definitions.
ORDER = neopixel.GRB

# Create pixel object
pixel = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=1, auto_write=False, pixel_order=ORDER
)
# Turn pixel on, color set to WHITE, brightness 20%
pixel[0] = (0,0,0)
print("=== LED OFF ===" )
pixel.show()
