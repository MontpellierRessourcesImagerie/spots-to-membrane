from ij import IJ, ImagePlus
from ij.gui import PointRoi
from ij.plugin import Duplicator
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
from inra.ijpb.binary.distmap import ChamferMask3D
from ij.plugin import RGBStackMerge
from inra.ijpb.binary import BinaryImages
from inra.ijpb.data.image import Images3D
from ij.gui import Roi
import os


def getValuesFromLocations(imChamfer, rm):
    rois = rm.getRoisAsArray()
    if len(rois) > imChamfer.getNSlices():
        print("Too many ROIs available.")
        return 1

    rt = ResultsTable.getResultsTable()
    rt.reset()

    for s, roi in enumerate(rois):
        imChamfer.setSlice(s+1)
        proc = imChamfer.getProcessor()
        points = roi.getContainedPoints()
        for point in points:
            val = proc.getf(point.x, point.y)
            if val < 1e-6:
                continue
            rt.addRow()
            rt.addValue("Distance", val)
            rt.addValue("X", point.x)
            rt.addValue("Y", point.y)
            rt.updateResults()
            rt.show("Results")


def distanceTransform(imIn):
    """
    Takes as input the control image in which the first channel is the mask.
    Extracts the mask and computes the distance transform.
    The input image is supposed to be isotropic and calibrated.
    Scales the quasi-Euclidean distance transform to micrometers.
    """
    dp = Duplicator()
    mask = dp.run(imIn, 1, 1, 1, imIn.getNSlices(), 1, 1)
    factor = mask.getCalibration().pixelWidth
    kernel = ChamferMask3D.QUASI_EUCLIDEAN
    distStack = BinaryImages.distanceMap(mask.getStack(), kernel, True, False)
    imOut = ImagePlus("Distance map", distStack)
    for i in range(1, imOut.getNSlices()+1):
        imOut.setSlice(i)
        prc = imOut.getProcessor()
        prc.multiply(factor)
    mask.close()
    return imOut


def extractDistances(distMap, rm, threshold):
    rt = ResultsTable()
    rt.reset()
    index = 0

    for i in range(rm.getCount()):
        roi = rm.getRoi(i)
        z = roi.getZPosition()
        if not roi.isLineOrPoint():
            continue
        points = roi.getContainedPoints()
        if len(points) != 1:
            continue
        x, y = int(points[0].x), int(points[0].y)
        distMap.setSlice(z)
        val = distMap.getProcessor().getf(x, y)

        if val > threshold:
            continue
        
        rt.addRow()
        rt.setValue("ID", index, i)
        rt.setValue("Distance (um)", index, val)
        rt.setValue("X", index, x)
        rt.setValue("Y", index, y)
        rt.setValue("Z", index, z)
        index += 1
        rt.updateResults()
    
    
    rt.show("distances-" + distMap.getTitle().replace("3-iso-mask-", ""))


def updateControl(control, distMap):
    """
    Updates the control image with the distance map.
    """
    dp = Duplicator()
    mask8 = dp.run(control, 1, 1, 1, control.getNSlices(), 1, 1)
    mask32 = ImagePlus(mask8.getTitle()+"-32", mask8.getStack().convertToFloat())
    imOut = RGBStackMerge.mergeChannels([mask32, distMap], True)
    imOut.setCalibration(control.getCalibration())
    title = control.getTitle()
    control.close()
    mask32.close()
    distMap.close()
    imOut.setTitle(title)
    imOut.setC(2)
    IJ.run(imOut, "mpl-viridis", "")
    return imOut


def removeInvalidSpots(invalidPath):
    rm = RoiManager.getInstance()
    descr = open(invalidPath, "r")
    content = [k for k in descr.read().split("\n") if len(k) > 1 and k.strip()[0] != "#"]
    descr.close()
    invalids = set()
    for i in range(rm.getCount()):
        name = rm.getName(i)
        if name in content:
            invalids.add(i)
    if len(invalids) == 0:
        return 0
    rm.deselect()
    invalids = list(invalids)
    rm.setSelectedIndexes(invalids)
    rm.runCommand("Delete")


def main():
    distThreshold = IJ.getNumber("Distance threshold (um)", 99.9)

    rm = RoiManager.getInstance()
    if rm is None:
        print("Couldn't find a RoiManager.")
        return 1
    
    control = IJ.getImage()
    ppt = control.getProperty("invalid-spots-path")
    removeInvalidSpots(ppt)

    imName  = control.getTitle()
    distMap = distanceTransform(control)
    distMap.setTitle(imName)
    extractDistances(distMap, rm, distThreshold)
    control = updateControl(control, distMap)
    control.show()


if __name__ == "__main__":
    main()
    print("Distances extraction done.")
