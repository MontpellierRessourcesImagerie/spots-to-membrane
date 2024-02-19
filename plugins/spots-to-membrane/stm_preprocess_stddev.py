import os
from math import log
from ij import IJ
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


def joinAll(pieces):
    start = pieces[0]
    for p in pieces[1:]:
        start = os.path.join(start, p)
    return start


def main():
    imIn = IJ.getImage()
    fi   = imIn.getOriginalFileInfo()
    path = fi.getFilePath()
    clb  = imIn.getCalibration()

    ij_dir      = IJ.getDirectory('imagej')
    dir_mri_cia = "cnrs_mri_cia"
    dir_stm     = "spots_to_membrane"
    f_name      = "mri_cia_spots_to_membrane.txt"
    
    print("File located at: " + path)
    settings_dir = joinAll([
        ij_dir,
        dir_mri_cia,
        dir_stm
    ])

    try:
        os.makedirs(settings_dir)
    except:
        print(settings_dir + " already exists.")

    f_path = os.path.join(settings_dir, f_name)
    descr  = open(f_path, 'w')

    descr.write(path)
    descr.close()

    imOut = preprocessImage(imIn)
    imOut.setCalibration(clb)
    imOut.show()


if __name__ == "__main__":
    main()
    print("Preprocessing done.")
