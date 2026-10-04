"""Unedited X11 screen capture, using Pillow's XCB backend."""
from PIL import ImageGrab
import sys,os
ImageGrab.grab(xdisplay=os.environ.get('DISPLAY',':97')).save(sys.argv[1])
