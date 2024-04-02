from ij import IJ
from ij.plugin.frame import RoiManager
from spots_to_membrane.spotsToMembrane import getOptions, padStack, sandwichPad, updateTargetImage
import os

def addToDump(imIn):
    """
    A dump is attached to an image and contains the names of the ROIs to remove from the ROI manager.
    The file must be reseted when we open a new image, even if it is the same one.
    The easiest way would be to use the image's image from ImageJ.
    """
    rm = RoiManager.getInstance()
    path = imIn.getProperty("invalid-spots-path")
    if path is None:
        IJ.log("No path found in the image properties.")
        return
    descr = open(path, 'r')
    content = descr.read()
    descr.close()
    index = rm.getSelectedIndex()
    name = rm.getName(index)

    if content == "":
        content = name
    else:
        content += "\n" + name

    IJ.log("--- Added " + name + " to the dump " + str(content.count('\n')) + " ---")
    
    descr = open(path, 'w')
    descr.write(content)
    descr.close()


if __name__ == "__main__":
    imIn = IJ.getImage()
    addToDump(imIn)