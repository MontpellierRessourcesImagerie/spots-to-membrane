from ij import IJ, ImagePlus
from ij.gui import PointRoi
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable
from inra.ijpb.binary.distmap import ChamferMask3D
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
    kernel = ChamferMask3D.QUASI_EUCLIDEAN
    distStack = BinaryImages.distanceMap(imIn.getStack(), kernel, True, False)
    imOut = ImagePlus("Distance map", distStack)
    imOut.setCalibration(imIn.getCalibration())
    imIn.close()
    return imOut


def extractDistances(imIn, rm, rt, threshold):
    all_rois = rm.getRoisAsArray()
    current = 0
    print("Number of ROIs: ", len(all_rois))
    print("Number of measures: ", rt.size())

    # Each measure will have to be added to the results table.
    lines = {}
    for i in range(rt.size()):
        _ = rt.getValue("pX", i)
        y = rt.getValue("pY", i)
        z = rt.getValue("pZ", i)
        id = (z, z, y)
        lines[id] = i

    measures = ResultsTable()

    for i, roi in enumerate(all_rois):
        name = rm.getName(i)
        indices = tuple([int(k) for k in name.split('-')])
        p = roi.getContainedPoints()[0]
        imIn.setSlice(indices[0])
        prc = imIn.getProcessor()
        val = prc.getf(p.x, p.y)
        print(val)

        if val > threshold:
            continue

        measures.addRow()
        measures.setValue("X", current, rt.getValue('X', lines[indices]))
        measures.setValue("Y", current, rt.getValue('Y', lines[indices]))
        measures.setValue("Z", current, rt.getValue('Z', lines[indices]))
        measures.setValue("d", current, val)
        measures.updateResults()
        current += 1

    measures.show("Measures-"+imIn.getTitle())


def main():
    distThreshold = IJ.getNumber("Distance threshold (um)", 99.9)

    rm = RoiManager.getInstance()
    if rm is None:
        print("Couldn't find a RoiManager.")
        return 1
    
    rt = ResultsTable.getResultsTable()
    if rt is None:
        print("Couldn't find a ResultsTable.")
        return 1
    
    mask = IJ.getImage()
    name = mask.getTitle()
    cb   = mask.getCalibration()
    dist = distanceTransform(mask)
    dist.setTitle(name)
    dist.setCalibration(cb)
    extractDistances(dist, rm, rt, distThreshold)
    

if __name__ == "__main__":
    main()
    print("Distances extraction done.")
