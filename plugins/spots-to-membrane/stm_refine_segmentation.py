from ij import IJ, ImagePlus, ImageStack
from ij.plugin import Duplicator, ImageCalculator
from inra.ijpb.label import LabelImages
from inra.ijpb.plugins import AnalyzeRegions
from ij.measure import ResultsTable
from inra.ijpb.watershed import ExtendedMinimaWatershed
from inra.ijpb.binary.distmap import ChamferMask3D
from inra.ijpb.binary import BinaryImages
from inra.ijpb.data.image import Images3D
from inra.ijpb.morphology import Strel3D
from ij.gui import PointRoi
from ij.plugin.frame import RoiManager

# Takes the output of labkit with a threshold, fill circular and small holes. 
# Then separate the main cell with a distance transform watershed.

# Pour boucher les trous, il va falloir inverser l'image et faire du labeling par connected components sur chaque slice.


_min_size = 2000
_circ_size = 4000


def fillHoles(imIn):
    _dp = Duplicator()
    ft = AnalyzeRegions.Features()
    ft.setAll(False)
    ft.area = True
    ft.circularity = True
    buffer = ImageStack(imIn.getWidth(), imIn.getHeight())
    cb = imIn.getCalibration()

    for s in range(1, imIn.getNSlices()+1):
        imWork = _dp.run(imIn, 1, 1, s, s, 1, 1)
        prc = imWork.getProcessor()
        prc.invert()
        imLbld = LabelImages.regionComponentsLabeling(imWork, 255, 8, 16)
        imWork.close()
        props = AnalyzeRegions.process(imLbld, ft)
        keep = []
        for i in range(props.size()):
            if props.getValue('Area', i) < _min_size:
                keep.append(i+1)
                continue
            if props.getValue('Area', i) < _circ_size and props.getValue('Circularity', i) > 0.5:
                keep.append(i+1)
                continue
            
        holes = LabelImages.keepLabels(imLbld, keep)
        imLbld.close()
        prc2 = holes.getProcessor()
        prc2.setThreshold(1, 255)
        buffer.addSlice(prc2.createMask())
        holes.close()
    
    imPatches = ImagePlus("Patches", buffer)
    imOut = ImageCalculator().run("or stack create", imPatches, imIn)
    imPatches.close()
    imOut.setCalibration(cb)
    
    return imOut


def findMainCell(imIn, spots):
    # 1. Splitting touching elements.
    kernel = ChamferMask3D.QUASI_EUCLIDEAN
    distStack = BinaryImages.distanceMap(imIn.getStack(), kernel, False, True)
    Images3D.invert(distStack)
    res = ExtendedMinimaWatershed.extendedMinimaWatershed(distStack, imIn.getStack(), 4, 6, 16, False)
    imSplit = ImagePlus("Split", res)
    
    # 2. Keeping and merging all regions containing spots.
    keep = set()
    for i in range(spots.size()):
        s = int(spots.getValue("pZ", i))
        y = int(spots.getValue("pY", i))
        x = int(spots.getValue("pX", i))
        imSplit.setSlice(s)
        lbl = imSplit.getProcessor().get(x, y)
        keep.add(lbl)
    
    interest = LabelImages.keepLabels(imSplit, list(keep))
    stackOut = ImageStack()

    for s in range(1, interest.getNSlices()+1):
        interest.setSlice(s)
        prc = interest.getProcessor()
        prc.setThreshold(1, 65535)
        stackOut.addSlice(prc.createMask())
    
    strel = Strel3D.Shape.CUBE.fromRadius(2)
    closed = strel.closing(stackOut)

    imOut = ImagePlus("Main cell", closed)
    imOut.setCalibration(imIn.getCalibration())
    imIn.close()
    return imOut


def spotsToROIManager(imIn, spots):
    rm = RoiManager()
    rm.reset()

    for i in range(spots.size()):
        x = int(spots.getValue("pX", i))
        y = int(spots.getValue("pY", i))
        z = int(spots.getValue("pZ", i))
        roi = PointRoi(x, y)
        imIn.setSlice(z)
        rm.add(imIn, roi, z)
        

def main():
    imIn = IJ.getImage()
    spots = ResultsTable.getActiveTable()
    name = imIn.getTitle()
    
    if spots is None:
        print("No spots table found.")
        return 1
    
    filled = fillHoles(imIn)
    mainCell = findMainCell(filled, spots)
    mainCell.setTitle(name)
    mainCell.show()
    spotsToROIManager(mainCell, spots)

    return 0


if __name__ == "__main__":
    main()