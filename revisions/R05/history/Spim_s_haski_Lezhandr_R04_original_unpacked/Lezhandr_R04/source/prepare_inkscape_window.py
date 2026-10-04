"""Resize the actual X11 Inkscape window and send the real '5' (page zoom) key."""
import ctypes,time
from ctypes.util import find_library
X=ctypes.CDLL(find_library('X11'));T=ctypes.CDLL(find_library('Xtst'))
D=ctypes.c_void_p;W=ctypes.c_ulong
X.XOpenDisplay.argtypes=[ctypes.c_char_p];X.XOpenDisplay.restype=D
d=X.XOpenDisplay(None)
X.XDefaultRootWindow.argtypes=[D];X.XDefaultRootWindow.restype=W
root=X.XDefaultRootWindow(d)
X.XQueryTree.argtypes=[D,W,ctypes.POINTER(W),ctypes.POINTER(W),ctypes.POINTER(ctypes.POINTER(W)),ctypes.POINTER(ctypes.c_uint)]
X.XFetchName.argtypes=[D,W,ctypes.POINTER(ctypes.c_char_p)]
rr=W();pp=W();children=ctypes.POINTER(W)();n=ctypes.c_uint()
X.XQueryTree(d,root,ctypes.byref(rr),ctypes.byref(pp),ctypes.byref(children),ctypes.byref(n))
for i in range(n.value):
    w=children[i];name=ctypes.c_char_p();X.XFetchName(d,w,ctypes.byref(name));s=(name.value or b'').decode(errors='replace')
    print(w,s,flush=True)
    if 'HC_OUTER' in s:
        X.XMoveResizeWindow.argtypes=[D,W,ctypes.c_int,ctypes.c_int,ctypes.c_uint,ctypes.c_uint];X.XMoveResizeWindow(d,w,0,0,1600,1060)
        X.XSetInputFocus.argtypes=[D,W,ctypes.c_int,W];X.XSetInputFocus(d,w,1,0)
        X.XFlush.argtypes=[D];X.XFlush(d);time.sleep(2)
        X.XKeysymToKeycode.argtypes=[D,W];X.XKeysymToKeycode.restype=ctypes.c_uint
        code=X.XKeysymToKeycode(d,0x35)
        T.XTestFakeKeyEvent.argtypes=[D,ctypes.c_uint,ctypes.c_int,W]
        T.XTestFakeKeyEvent(d,code,1,0);T.XTestFakeKeyEvent(d,code,0,0);X.XFlush(d)
        break
