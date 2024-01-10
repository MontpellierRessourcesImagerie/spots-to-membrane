import os
from random import randint

from ij import IJ, ImagePlus
from ij.plugin import Duplicator, Concatenator
from ij.plugin import ContrastEnhancer
from ij.plugin.filter import BackgroundSubtracter

from imagescience.image import Axes, Image, FloatImage
from imagescience.transform import Mirror

"""
Script: Build trainig set
Project: Distance spots-membrane (Felipe)
Description: Build a training set from a batch of images meant to be used with LabKit. 
             The only relevant channel is the 3rd one, which is the membrane staining.
             All stacks have a different size, so they can't be assembled as frames.
             In this script, images will be opened sequentially. 
             Several chunks of 5 slices will be picked and added to a buffer.
             The final buffer will be the training set.

             Note: - Images are normalized before being splitted.
                   - We should also add some randomness (rotations, mirrors, ...)
"""

###########  INIT AND SETTINGS #############

_dp      = Duplicator()
_channel = 3 # Channel of interest
_ext     = ".ics" # Extension of images in the folder.
_path    = "/home/benedetti/Desktop/imgs-felipe"
_s_size  = 5 # Size (in slices) of a chunk from an image
_cct     = Concatenator()
_ce      = ContrastEnhancer()
_m       = Mirror()
_bs      = BackgroundSubtracter()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_cct.setIm5D(True)
_ce.setNormalize(True)
_ce.setProcessStack(True)
_ce.setUseStackHistogram(False)

############################################

content = [f for f in os.listdir(_path) if f.endswith(_ext)]
buffer  = []
nFrames = 0

for c in content:
    full_path = os.path.join(_path, c)
    imIn = IJ.openImage(full_path)

    # Background correction of every slice
    for s in range(imIn.getNSlices()):
        imIn.setSlice(s)
        _bs.rollingBallBackground(imIn.getProcessor(), 50.0, False, False, True, True, True)

    # Normalization of images
    _ce.stretchHistogram(imIn, 0.1)

    for i in range(1, imIn.getNSlices()+1, _s_size):
        start = i
        end   = start+_s_size-1
        if (end > imIn.getNSlices()):
            break
        chunk = _dp.run(imIn, _channel, _channel, start, end, 1, 1)
        
        img = Image.wrap(chunk)
        a = Axes(
            randint(0, 1) != 0, 
            randint(0, 1) != 0, 
            randint(0, 1) != 0
        )
        _m.run(img, a)
        out = img.imageplus()
        chunk.close()

        buffer.append(out)
        nFrames += 1
    imIn.close()

imOut = _cct.concatenate(buffer, False)
imOut.setDimensions(1, _s_size, nFrames)
imOut.show()






