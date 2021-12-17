import time
from basic_serial_instrument import BasicSerialInstrument
from argparse import ArgumentParser
import board
import neopixel



class SingleNeoPixel(BasicSerialInstrument):
    pixel_pin = board.D10
    num_pixels = 1
    ORDER = neopixel.GRB
    def __init__(self, *args, **kwargs):
        BasicSerialInstrument.__init__(self, *args, **kwargs)
        self.pixels =  neopixel.NeoPixel(
            self.pixel_pin, self.num_pixels, auto_write = False, pixel_order=self.ORDER, brightness=1)
        time.sleep(1)
        
    def set_rgb(self, r, g, b):
        """Set the RGB value of the NeoPixel, range 0-255.
        """
        self.pixels[0] = (r,g,b)
        self.pixels.show()
        #self.query("set_rgb {} {} {}\n".format(r,g,b))

class ManualIllumination():
    def set_rgb(self, r, g, b):
        input("Please set the illumination to {} {} {} and press enter".format(r,g,b))
        
    def __enter__(self):
        """When we use this in a with statement, it should be opened already"""
        return self

    def __exit__(self, type, value, traceback):
        """Close down the instrument.  This happens in __del__ though."""
        if type is not None:
            print("I don't know how to handle exceptions!")
            raise value
        

if __name__ == "__main__":
    parser = ArgumentParser(description="A simple utility to talk to an Arduino that controls a NeoPixel")
    parser.add_argument("rgb", nargs=3, default=[0,0,0], type=int, help="Give a sequence of 3 integers, to set the RGB value")
    parser.add_argument("--fade", action="store_true", help="smoothly fade between R,G,B until you terminate with ctrl+C")
    parser.add_argument("--cycle", action="store_true", help="cycle between red, green, blue, black and white")
    args = parser.parse_args()
    with SingleNeoPixel() as np:
        np.set_rgb(*args.rgb)
        
        if args.cycle:
            try:
                while True:
                    for rgb in [(255,255,255),(255,0,0),(0,255,0),(0,0,255),(0,0,0)]:
                        np.set_rgb(*rgb)
                        time.sleep(1)
            except KeyboardInterrupt:
                pass
        if args.fade:
            try:
                while True:
                    for i in range(3):
                        for j in range(255):
                            col = [0,0,0]
                            col[i] = 255-j
                            col[(i+1) % 3] = j
                            np.set_rgb(*col)
                            time.sleep(0.01)
            except KeyboardInterrupt:
                pass



