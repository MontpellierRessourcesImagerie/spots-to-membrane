from ij import IJ, ImagePlus, ImageStack
from ij.plugin import Duplicator, ImageCalculator, RGBStackMerge
from inra.ijpb.label import LabelImages
from inra.ijpb.plugins import AnalyzeRegions
from ij.measure import ResultsTable
from inra.ijpb.watershed import ExtendedMinimaWatershed
from inra.ijpb.binary.distmap import ChamferMask3D
from inra.ijpb.binary import BinaryImages
from inra.ijpb.data.image import Images3D
from inra.ijpb.morphology import Strel3D
from ij.gui import PointRoi, WaitForUserDialog
from ij.plugin.frame import RoiManager

from spots_to_membrane.spotsToMembrane import getOptions, sandwichPad, makeIsotropic, getTargetPath


def fillHoles(imIn):
    _dp = Duplicator()
    ft = AnalyzeRegions.Features()
    ft.setAll(False)
    ft.area = True

    buffer = ImageStack(imIn.getWidth(), imIn.getHeight())
    cb = imIn.getCalibration()
    options = getOptions()
    min_size = options['sizeHoles']

    for s in range(1, imIn.getNSlices()+1):
        imWork = _dp.run(imIn, 1, 1, s, s, 1, 1)
        prc = imWork.getProcessor()
        prc.invert()
        imLbld = LabelImages.regionComponentsLabeling(imWork, 255, 4, 16)
        imWork.close()
        props = AnalyzeRegions.process(imLbld, ft)

        keep = []
        for i in range(props.size()):
            if props.getValue('Area', i) < min_size:
                keep.append(i+1)
                continue
            
        holes = LabelImages.keepLabels(imLbld, keep)
        imLbld.close()
        prc2 = holes.getProcessor()
        prc2.setThreshold(1, 65536)
        buffer.addSlice(prc2.createMask())
        holes.close()
    
    IJ.log("     | Holes map processed.")
    imPatches = ImagePlus("Patches", buffer)
    imOut = ImageCalculator().run("or stack create", imPatches, imIn)
    imPatches.close()
    imOut.setCalibration(cb)
    IJ.log("     | Holes of size < " + str(min_size) + " pixels removed on each slice.")

    return imOut


def findMainCell(imIn, spots):
    # 1. Splitting touching elements.
    kernel = ChamferMask3D.QUASI_EUCLIDEAN
    distStack = BinaryImages.distanceMap(imIn.getStack(), kernel, False, True)
    Images3D.invert(distStack)
    res = ExtendedMinimaWatershed.extendedMinimaWatershed(distStack, imIn.getStack(), 4, 6, 16, False)
    imSplit = ImagePlus("Split", res)
    IJ.log("     | Chamfer distance and extrema-seeded watershed done.")
    
    # 2. Keeping and merging all regions containing spots.
    keep = set()
    for i in range(spots.size()):
        s = int(spots.getValue("pZ", i))
        y = int(spots.getValue("pY", i))
        x = int(spots.getValue("pX", i))
        imSplit.setSlice(s)
        lbl = imSplit.getProcessor().get(x, y)
        keep.add(lbl)
    IJ.log("     | Fragments containing spots isolated.")
    
    interest = LabelImages.keepLabels(imSplit, list(keep))
    stackOut = ImageStack()

    for s in range(1, interest.getNSlices()+1):
        interest.setSlice(s)
        prc = interest.getProcessor()
        prc.setThreshold(1, 65535)
        stackOut.addSlice(prc.createMask())
    
    strel = Strel3D.Shape.CUBE.fromRadius(2)
    closed = strel.closing(stackOut)
    IJ.log("     | Fragments containing spots merged.")

    imOut = ImagePlus("Main cell", closed)
    imOut.setCalibration(imIn.getCalibration())
    imIn.close()
    interest.close()

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
        rm.select(i)
        rm.setPosition(z)
    
    IJ.log("     | Spots added to ROI Manager.")


def makeControlImage(mask, imgPath):
    # Getting option to find the membrane channel.
    options = getOptions()
    chIndex = options['chMembrane']

    # Isolating and padding the membrane channel.
    imOri      = IJ.openImage(imgPath)
    dp         = Duplicator()
    chMembrane = dp.run(imOri, chIndex, chIndex, 1, imOri.getNSlices(), 1, 1)
    # k1 = chMembrane.duplicate()
    # k1.setTitle("P1")
    # k1.show()
    imOri.close()
    chMembrane = sandwichPad(chMembrane)
    chMembrane, _ = makeIsotropic(chMembrane)
    # k2 = chMembrane.duplicate()
    # k2.setTitle("P2")
    # k2.show()

    # Assembling the control image.
    control = RGBStackMerge.mergeChannels(
        [mask, chMembrane], 
        False
    )

    IJ.log("     | Control image assembled.")
    control.setCalibration(mask.getCalibration())
    return control
        

def main():
    imIn = IJ.getImage()
    title = imIn.getTitle().replace("2-rough-mask-", "3-iso-mask-")
    ppt = imIn.getProperty("invalid-spots-path")
    spots = ResultsTable.getActiveTable()
    imgPath = getTargetPath()

    IJ.log("=======  Starting segmentation post-processing  ========")

    wfud = WaitForUserDialog("Watershed splitting", "Do you want to try a distance-transform watershed to separate touching elements?\n   [OK]. No\n   [Alt]+[OK]. Yes")
    wfud.show()
    useWatershed = IJ.altKeyDown()
    if useWatershed:
        IJ.log("  > Using watershed: YES")
    else:
        IJ.log("  > Using watershed: NO")
    
    if spots is None:
        IJ.log("No spots table found.")
        return 1
    
    mask = fillHoles(imIn)
    
    if useWatershed:
        IJ.log("  > Trying to isolate the main cell...")
        mask = findMainCell(mask, spots)
    
    control = makeControlImage(mask, imgPath)
    spotsToROIManager(control, spots)
    IJ.selectWindow("Results")
    IJ.run("Close") 
    control.setProperty("invalid-spots-path", ppt)
    control.setTitle(title)
    control.show()
    IJ.log("==> Segmentation refining DONE.")
    return 0


if __name__ == "__main__":
    main()