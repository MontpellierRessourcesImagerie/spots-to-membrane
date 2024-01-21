import os
from math import log

from ij import IJ, ImagePlus, ImageStack
from ij.plugin.filter import BackgroundSubtracter
from ij.plugin import ImageCalculator, GaussianBlur3D, Duplicator, ContrastEnhancer


def subtractBGandNormalize(imIn):
    bs = BackgroundSubtracter()

    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        bs.rollingBallBackground(prc, 20.0, False, False, True, True, True)
    
    ce = ContrastEnhancer()
    ce.setNormalize(True)
    ce.setProcessStack(True)
    ce.setUseStackHistogram(True)

    ce.stretchHistogram(imIn, 0.1)


def scaleByStandardDeviation(imIn):
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        stats = prc.getStats()
        coef = log(1.71828 * (1.0 - stats.stdDev) + 1.0)
        prc.multiply(coef)


def gamma_correction(imIn, gamma=1.0):
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        prc.gamma(0.3333)
    
    ce = ContrastEnhancer()
    ce.setNormalize(True)
    ce.setProcessStack(True)
    ce.setUseStackHistogram(True)
    ce.stretchHistogram(imIn, 0.1)

    imTemp = imIn.duplicate()
    IJ.saveAsTiff(imTemp, "/home/benedetti/Desktop/dump/"+imIn.getTitle())
    imTemp.close()


def preprocess(imIn, blur=False):
    subtractBGandNormalize(imIn)
    scaleByStandardDeviation(imIn)
    if blur:
        GaussianBlur3D.blur(imIn, 7.0, 7.0, 1.0)


def combine(imIn1, imIn2):
    imOut = ImageCalculator.run(imIn1, imIn2, "stack multiply create 32-bit")
    imIn1.close()
    imIn2.close()
    return imOut


def preprocessImage(imIn):
    dp  = Duplicator()
    ch1 = dp.run(imIn, 1, 1, 1, imIn.getNSlices(), 1, 1)
    ch3 = dp.run(imIn, 3, 3, 1, imIn.getNSlices(), 1, 1)
    preprocess(ch1, True)
    gamma_correction(ch1, 0.25)
    preprocess(ch3, True)
    gamma_correction(ch3, 1.5)
    imOut = combine(ch1, ch3)

    ce = ContrastEnhancer()
    ce.setNormalize(True)
    ce.setProcessStack(True)
    ce.setUseStackHistogram(True)
    ce.stretchHistogram(imOut, 0.1)

    return imOut


def main():
    inputDir = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/raw-files"
    outputDir = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/preprocess-assembled"
    inputExt = ".ics"
    inputImg = [f for f in os.listdir(inputDir) if f.lower().endswith(inputExt)]

    for index, imInName in enumerate(inputImg):
        print("[" + str(index+1).zfill(len(str(len(inputImg)))) + "/" + str(len(inputImg)) + "]" + "Processing: " + imInName)
        fullPath = os.path.join(inputDir, imInName)
        imIn = IJ.openImage(fullPath)
        imOut = preprocessImage(imIn)
        imIn.close()
        outPath = os.path.join(outputDir, imInName)
        IJ.saveAsTiff(imOut, outPath)
    
    print("DONE.")

# =========================
        
main()


""" TODO

- [ ] Essayer de faire une ROI de background pour chaque image plutôt que de prendre la slice entière.
- [ ] Prendre le log de l'image de spots plutôt que l'image elle-même.

"""