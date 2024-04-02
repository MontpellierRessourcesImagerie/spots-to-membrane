from ij import IJ
from ij.measure import ResultsTable
import os
from spots_to_membrane.spotsToMembrane import getTargetPath


def loadPoints(pointsPath, imIn):
    """
    Load points from a CSV file and invert the Y and Z axes.
    Coordinates are in calibrated units here.
    """
    factor = imIn.getProperty("anisotropy-factor")
    if factor is None:
        raise ValueError("Anisotropy factor not found in the image properties.")
    
    factor = float(factor)
    descr  = open(pointsPath, 'r')
    
    # Skip lines corresponding to useless data from Imaris.
    for _ in range(4): 
        descr.readline()
    
    calibration = imIn.getCalibration()
    Z = calibration.pixelDepth * imIn.getNSlices() # Total depth of the stack
    Y = calibration.pixelHeight * imIn.getHeight() # Total height (and width) of the stack.

    buffer = []
    while True:
        line = descr.readline()
        if len(line) == 0:
            break
        vals = [float(f) for f in line.split(',')[0:3]] # X, Y, Z coords
        vals[1] = Y - vals[1] # Inverting Y axis
        vals[2] = Z - vals[2] + (calibration.pixelDepth / factor) # Invert Z axis + accounting for the padding
        buffer.append(vals)
    descr.close()

    IJ.log("     | Found " + str(len(buffer)) + " spots.")
    IJ.log("     | Starting Z: " + str(calibration.pixelDepth / factor))
    
    return sorted(buffer, key=lambda x: x[2]) # Points sorted by Z axis


def uncalibrate(points, imIn):
    """
    Convert the points from calibrated to uncalibrated units.
    Process based on the calibration of the input image.
    """
    calibration = imIn.getCalibration()
    sx, sy, sz = calibration.pixelWidth, calibration.pixelHeight, calibration.pixelDepth
    IJ.log("     | Uncalibrated positions processed.")
    return [(int(x/sx), int((y/sy)), int(z/sz)+1) for (x, y, z) in points]


def getSpotsPath(imgPath):
    """
    Attempt to find the spots file.
    It can be located either in the same folder as the image or in a subfolder of which the name starts with "spots".

    Args:
        imgPath (str): The path to the image.

    Returns:
        str: The path to the spots file. None if no spots file is found.
    """
    imgName = os.path.basename(imgPath)
    imgDir  = os.path.dirname(imgPath)
    spotsL  = [f for f in os.listdir(imgDir) if f.lower().startswith("spots") and os.path.isdir(os.path.join(imgDir, f))]
    spotsN  = None if len(spotsL) == 0 else spotsL[0]
    noExt   = ".".join(imgName.split('.')[:-1])

    if spotsN is not None:
        IJ.log("     | Found spots in a subfolder.")
        spotsDir = os.path.join(imgDir, spotsN)
    else:
        IJ.log("     | Found spots in the same folder.")
        spotsDir = imgDir
    
    targetL  = [f for f in os.listdir(spotsDir) if f.startswith(noExt) and f.lower().endswith('.csv')]
    IJ.log("     | Found spots file: " + str(targetL) + ".")
    return None if len(targetL) == 0 else os.path.join(spotsDir, targetL[0])


def makeTableFromPoints(points, uncalibrated):
    t = ResultsTable.getResultsTable()
    t.reset()

    for index in range(len(points)):
        t.addRow()
        t.setValue('X', index, points[index][0])
        t.setValue('Y', index, points[index][1])
        t.setValue('Z', index, points[index][2])
        t.setValue('pX', index, uncalibrated[index][0])
        t.setValue('pY', index, uncalibrated[index][1])
        t.setValue('pZ', index, uncalibrated[index][2])
        t.updateResults()
    
    t.show("Results")
    return t


def main():

    IJ.log("=======  Starting spots extraction  ========")

    imIn = IJ.getImage()
    imgPath = getTargetPath()

    if not os.path.isfile(imgPath):
        IJ.log("Couldn't find the target image.")
        return 1

    pointsPath = getSpotsPath(imgPath)

    if pointsPath is None:
        IJ.log("Couldn't find the spots for current image.")
        return 1
    
    IJ.log("  > Loading spots from: " + pointsPath)
    IJ.log("  > Filling results table with coordinates.")

    raw_points = loadPoints(pointsPath, imIn)
    points     = uncalibrate(raw_points, imIn)
    _ = makeTableFromPoints(raw_points, points)

    IJ.log("==> Spots import DONE.")
    return 0


if __name__ == "__main__":
    main()