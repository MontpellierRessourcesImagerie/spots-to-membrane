from ij import IJ, ImagePlus, ImageStack
from ij.plugin import Duplicator
from ij.process import AutoThresholder
from inra.ijpb.label.conncomp import FloodFillRegionComponentsLabeling
from ij.plugin import ContrastEnhancer
from inra.ijpb.label import LabelImages
from inra.ijpb.morphology.filter import Closing
from inra.ijpb.morphology import Strel
from inra.ijpb.morphology import Reconstruction

###########  INIT AND SETTINGS #############

_dp      = Duplicator()
_channel = 3
_ffrcl   = FloodFillRegionComponentsLabeling(4, 16)
_ce      = ContrastEnhancer()
_strel   = Strel.Shape.DISK.fromRadius(5)
_strel2  = Strel.Shape.DISK.fromRadius(21)
_cls     = Closing(_strel)
_cls2    = Closing(_strel2)

_ce.setNormalize(True)

############################################

# imIn = IJ.getImage()
# cellImg = _dp.run(imIn, _channel, _channel, 1, imIn.getNSlices(), 1, 1)
# imIn.close()

cellImg = IJ.getImage()
imgStk  = ImageStack(cellImg.getWidth(), cellImg.getHeight())

for sliceIdx in range(1, 1+cellImg.getNSlices()):
    # Isolate slice of interest
    cellSlice = _dp.run(cellImg, 1, 1, sliceIdx, sliceIdx, 1, 1)
    
    # Normalize image
    _ce.stretchHistogram(cellSlice, 0.35)
    
    # Threshold the image
    threshold_method = AutoThresholder.Method.Yen
    thresholder = AutoThresholder()
    stats = cellSlice.getProcessor().getStatistics()
    long_histogram = stats.getHistogram()
    histogram = [int(value) for value in long_histogram]
    thresholdBin = thresholder.getThreshold(threshold_method, histogram)

    hMin = stats.histMin
    hMax = stats.histMax
    threshold = hMin + stats.binSize * thresholdBin
    IJ.log("Thresholding at " + str(threshold))
    
    ip = cellSlice.getProcessor()
    ip.setThreshold(threshold, 1e30)
    nip = ip.createMask()
    
    lbld = _ffrcl.computeLabels(nip, 255)
    contour = LabelImages.keepLargestLabel(lbld)
    contour = _cls.process(contour)
    
    contour.invert()
    contour = Reconstruction.killBorders(contour)

    lbld = _ffrcl.computeLabels(contour, 255)
    contour = LabelImages.keepLargestLabel(lbld)
    contour = _cls.process(contour)

    lbld = _ffrcl.computeLabels(contour, 255)
    hollow = LabelImages.keepLargestLabel(lbld)
    cleaned = _cls2.process(contour)

    imgStk.addSlice(cleaned)

imOut = ImagePlus("final", imgStk)
imOut.show()

    
    
    