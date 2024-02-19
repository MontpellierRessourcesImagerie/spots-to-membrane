from ij import IJ, ImagePlus, ImageStack
from ij.process import ImageProcessor
from ij.gui import PointRoi
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
import os


def loadPoints(pointsPath, imIn):
    descr = open(pointsPath, 'r')
    # Skip lines corresponding to useless data.
    for _ in range(4):
        descr.readline()
    
    calibration = imIn.getCalibration()
    Z = calibration.pixelDepth * imIn.getNSlices()
    Y = calibration.pixelHeight * imIn.getHeight()

    buffer = []
    line = ""
    while True:
        line = descr.readline()
        if len(line) == 0:
            break
        vals = [float(f) for f in line.split(',')[0:3]]
        vals[1] = Y - vals[1]
        vals[2] = Z - vals[2] + calibration.pixelDepth
        buffer.append(vals)
    
    return sorted(buffer, key=lambda x: x[2])


def uncalibrate(points, imIn):
    calibration = imIn.getCalibration()
    sx, sy, sz = calibration.pixelWidth, calibration.pixelHeight, calibration.pixelDepth
    return [(int(x/sx), int((y/sy)), int(z/sz)) for (x, y, z) in points]


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


def makeRoi(points, imIn):
    rm = RoiManager()
    rm.reset()
    for sliceIndex in range(2, imIn.getNSlices()):
        sPoints = [p for p in points if p[2]+1 == sliceIndex-1]
        ox = [float(p[0]) for p in sPoints]
        oy = [float(p[1]) for p in sPoints]
        roi = PointRoi(ox, oy)
        imIn.setSlice(sliceIndex)
        # imIn.getProcessor().setRoi(roi)
        rm.add(imIn, roi, sliceIndex)
    
    return rm


def joinAll(pieces):
    start = pieces[0]
    for p in pieces[1:]:
        start = os.path.join(start, p)
    return start


def getSpotsPath(imgPath):
    imgName = os.path.basename(imgPath)
    imgDir  = os.path.dirname(imgPath)
    spotsL  = [f for f in os.listdir(imgDir) if f.lower().startswith("spots") and os.path.isdir(os.path.join(imgDir, f))]
    spotsN  = None if len(spotsL) == 0 else spotsL[0]
    noExt   = ".".join(imgName.split('.')[:-1])

    if spotsN is not None:
        print("Spots in subfolder.")
        spotsDir = os.path.join(imgDir, spotsN)
    else:
        print("Spots in same folder.")
        spotsDir = imgDir
    
    targetL  = [f for f in os.listdir(spotsDir) if f.startswith(noExt) and f.lower().endswith('.csv')]
    return None if len(targetL) == 0 else os.path.join(spotsDir, targetL[0])


def makeTableFromPoints(points, uncalibrated, name):
    t = ResultsTable.getResultsTable()
    t.reset()

    for index in range(len(points)):
        t.addRow()
        t.setValue('X', index, points[index][0])
        t.setValue('Y', index, points[index][1])
        t.setValue('Z', index, points[index][2])
        t.setValue('pX', index, uncalibrated[index][0])
        t.setValue('pY', index, uncalibrated[index][1])
        t.setValue('pZ', index, uncalibrated[index][2]-1)
        t.updateResults()
    
    t.show("Results")


def main():
    imIn = IJ.getImage()
    ij_dir      = IJ.getDirectory('imagej')
    dir_mri_cia = "cnrs_mri_cia"
    dir_stm     = "spots_to_membrane"
    f_name      = "mri_cia_spots_to_membrane.txt"
    
    settings_dir = joinAll([
        ij_dir,
        dir_mri_cia,
        dir_stm
    ])

    f_path = os.path.join(settings_dir, f_name)
    descr  = open(f_path, 'r')
    imgPath = descr.read().strip()
    descr.close()


    pointsPath = getSpotsPath(imgPath)

    if pointsPath is None:
        print("Couldn't find the spots for current image.")
        return 1

    raw_points = loadPoints(pointsPath, imIn)
    points = uncalibrate(raw_points, imIn)
    makeTableFromPoints(raw_points, points, imIn.getTitle())
    # rm = makeRoi(points, imIn)
    print("DONE.")
    return 0


if __name__ == "__main__":
    main()
    print("Spots import done.")