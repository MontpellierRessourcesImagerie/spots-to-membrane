from ij import IJ, ImagePlus, ImageStack
from ij.process import ImageProcessor
from ij.gui import PointRoi
import os

####################  DECLARATIONS  ####################

_points_path = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-membrane/points"

########################################################

def loadPoints(pointsPath):
    descr = open(pointsPath, 'r')
    # Skip lines corresponding to useless data.
    for _ in range(4):
        descr.readline()
    buffer = []
    line = ""
    while True:
        line = descr.readline()
        if len(line) == 0:
            break
        buffer.append([float(k) for k in line.split(',')[0:3]])
    
    return buffer

def uncalibrate(points, calibration):
    sx, sy, sz = calibration.pixelWidth, calibration.pixelHeight, calibration.pixelDepth
    return [(int(x/sx), int(y/sy), int(z/sz)) for (x, y, z) in points]

def makeMarkers(points, imIn):
    imOut = IJ.createImage(
        "markers-"+imIn.getTitle(),
        imIn.getWidth(),
        imIn.getHeight(),
        imIn.getNSlices(),
        8
    )
    stack = imOut.getStack()

    for point in points:
        stack.setVoxel(point[0], point[1], point[2]+1, 255)
    
    return imOut

def main():
    imIn = IJ.getImage()
    pointsPath = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-membrane/points/MLV-nc + CytD + WGA-01_0_cmle_Detailed.csv"
    points = uncalibrate(loadPoints(pointsPath), imIn.getCalibration())
    imOut = makeMarkers(points, imIn)
    imOut.show()
    print("DONE.")
    return 0

main()