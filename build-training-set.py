import os
from random import randint, shuffle

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

###########  INIT, GLOBALS AND SETTINGS #############

_dp      = Duplicator()
_channel = 2 # Channel of interest
_ext     = ".ics" # Extension of images in the folder.
_s_size  = 5 # Size (in slices) of a chunk from an image
_dcm_f   = 1 # Decimation factor
_cct     = Concatenator()
_ce      = ContrastEnhancer()
_m       = Mirror()
_bs      = BackgroundSubtracter()
_paths   = [
    # "/home/benedetti/Documents/projects/22-felipe-membrane-spots/imgs-felipe",
    "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/raw-files"
]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_cct.setIm5D(True)
_ce.setNormalize(True)
_ce.setProcessStack(True)
_ce.setUseStackHistogram(False)

############################################

def getContent():
    content = []
    for path in _paths:
        ext = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(_ext)]
        content += ext
    
    shuffle(content)
    target_length = int(len(content) * _dcm_f)

    return content[:target_length]


############################################

content = getContent() # All files used in the training set
buffer  = [] # Buffer of stacks
nFrames = 0

for n, c in enumerate(content):
    full_path = c
    print("[" + str(n+1) + "/" + str(len(content)) + "]." + " Processing " + c)
    imIn      = IJ.openImage(full_path)
    channel   = _dp.run(imIn, _channel, _channel, 1, imIn.getNSlices(), 1, 1)
    imIn.close()

    # Background correction of every slice
    for s in range(channel.getNSlices()):
        channel.setSlice(s)
        _bs.rollingBallBackground(channel.getProcessor(), 50.0, False, False, True, True, True)

    # Normalization of images
    _ce.stretchHistogram(channel, 0.1)

    for i in range(1, channel.getNSlices()+1, _s_size):
        start = i
        end   = start+_s_size-1
        if (end > channel.getNSlices()):
            break
        
        chunk = _dp.run(channel, 1, 1, start, end, 1, 1)
        img = Image.wrap(chunk)
        a = Axes(
            False, # randint(0, 1) != 0, 
            False, # randint(0, 1) != 0, 
            False # randint(0, 1) != 0
        )
        _m.run(img, a)
        out = img.imageplus()
        chunk.close()

        buffer.append(out)
        nFrames += 1
    channel.close()

imOut = _cct.concatenate(buffer, False)
imOut.setDimensions(1, _s_size, nFrames)
imOut.show()
print("DONE.")