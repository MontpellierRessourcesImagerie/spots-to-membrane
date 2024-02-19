import os
from random import randint, shuffle

from ij import IJ, ImagePlus
from ij.plugin import Duplicator, Concatenator


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
_channel = 1
_s_size  = 9
_ext     = ".tif" # Extension of images in the folder.
_cct     = Concatenator()
_dec_fac = 0.8
_paths   = [
    "/home/benedetti/Documents/projects/22-spots-to-membrane/data/FL120-cells-no-tentacles/preprocessed-c1-c3/",
    "/home/benedetti/Documents/projects/22-spots-to-membrane/data/FL120-cells-no-tentacles/preprocessed-c1-c2-c3/"
]
_n_out = [
    "c1-c3.tif",
    "c1-c2-c3.tif"
]
_path_out = "/home/benedetti/Documents/projects/22-spots-to-membrane/data/FL120-cells-no-tentacles/training-sets/"


############################################

def getContent():
    content =  [f for f in os.listdir(_paths[0]) if f.endswith(_ext)]
    shuffle(content)
    target_length = int(_dec_fac * len(content))
    return content[:target_length]


############################################

content = getContent() # All files used in the training set
buffer  = [] # Buffer of stacks
nFrames = 0


for k, source_dir in enumerate(_paths):
    for n, c in enumerate(content):
        print("[" + str(n+1) + "/" + str(len(content)) + "]." + " Processing " + c)
        full_path = os.path.join(source_dir, c)
        imIn      = IJ.openImage(full_path)
    
        for i in range(1, imIn.getNSlices()+1, _s_size):
            start = i
            end   = start+_s_size-1
            if (end > imIn.getNSlices()):
                break
            
            chunk = _dp.run(imIn, 1, 1, start, end, 1, 1)
            """
            img = Image.wrap(chunk)
            a = Axes(
                False, # randint(0, 1) != 0, 
                False, # randint(0, 1) != 0, 
                False # randint(0, 1) != 0
            )
            _m.run(img, a)
            out = img.imageplus()
            """
            buffer.append(chunk)
            nFrames += 1
        imIn.close()

    imOut = _cct.concatenate(buffer, False)
    imOut.setDimensions(1, _s_size, nFrames)
    IJ.save(imOut, os.path.join(_path_out, _n_out[k]))
    imOut.close()
print("DONE.")