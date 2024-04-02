import os, json
from random import shuffle
from ij import IJ, ImageStack, ImagePlus
from ij.plugin.filter import BackgroundSubtracter
from ij.plugin import GaussianBlur3D, Duplicator, ContrastEnhancer, RGBStackMerge, Concatenator, ChannelSplitter
from ij.process import StackStatistics, ShortProcessor
from ij.gui import WaitForUserDialog
from spots_to_membrane.spotsToMembrane import getOptions, padStack, sandwichPad, updateTargetImage


def gamma_correction(imIn, gamma=0.3333):
    """
    Applies a gamma correction to a whole stack, slice by slice.
    The original image is modified.

    Args:
        imIn (ImagePlus): The image to process.
        gamma (float): The gamma value to apply.
    """
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        prc.gamma(gamma)


def combine(imIn1, imIn2):
    """
    Combines two images into a multi-channel image.
    The calibration is taken from the first image.
    The title is taken from the first image and the word "spots" is replaced by "preprocessed".
    Input images are closed.

    Args:
        imIn1 (ImagePlus): The first image (future C1).
        imIn2 (ImagePlus): The second image (future C2).
    
    Returns:
        ImagePlus: A newly created multi-channel image.
    """
    if imIn1.getNSlices() != imIn2.getNSlices():
        raise ValueError("Images must have the same number of slices.")
    if imIn1.getNFrames() != imIn2.getNFrames():
        raise ValueError("Images must have the same number of frames.")
    if imIn1.getNChannels() != 1:
        raise ValueError("Images must have only one channel. (not the case of the first image)")
    if imIn2.getNChannels() != 1:
        raise ValueError("Images must have only one channel. (not the case of the second image)")
    
    calib = imIn1.getCalibration()
    imOut = RGBStackMerge.mergeChannels([imIn1, imIn2], False)
    imOut.setCalibration(calib)
    imIn1.close()
    imIn2.close()
    return imOut


def rollingBallBG(imIn, radius=20.0):
    """
    Applies a rolling ball background subtraction to the image, slice by slice.
    The original image is modified.

    Args:
        imIn (ImagePlus): The image to process.
        radius (float): The radius of the rolling ball (in calibrated pixels).
    """
    bs = BackgroundSubtracter()
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        bs.rollingBallBackground(prc, radius, False, False, True, True, True)


def stretchHistogram(imIn, eq):
    """
    Stretches the histogram of the image, slice by slice, according to the stack histogram.
    The original image is modified.

    Args:
        imIn (ImagePlus): The image to process.
        eq (bool): If True, the image is equalized after the stretching.
    """
    ce = ContrastEnhancer()
    ce.setNormalize(True)
    ce.setProcessStack(True)
    ce.setUseStackHistogram(True)
    ce.stretchHistogram(imIn, 0.35)
    if eq:
        ce.equalize(imIn)


def gaussianBlur3D(imIn, basis):
    """
    Tries to remove some noise with a gaussian blur.
    Also a cheap solution to 'build' some information from the sporadic staining.
    The original image is modified.
    The basis is used to compute the sigma in the z direction in case of anisotropic images.

    Args:
        imIn (ImagePlus): The image to process.
        basis (float): The basis for the sigma computation.
    """
    z_factor = imIn.getCalibration().pixelDepth / imIn.getCalibration().pixelWidth
    GaussianBlur3D.blur(imIn, basis, basis, z_factor*basis)


def preprocessChannel(imIn, blur, gamma, eq=False):
    # Subtract BG
    rollingBallBG(imIn)
    IJ.log("     | Background correction done.")
    # Enhance contrast + equalize + normalize
    stretchHistogram(imIn, eq)
    IJ.log("     | Values range fixed.")
    # Bluring to catch info around
    gaussianBlur3D(imIn, blur)
    IJ.log("     | Denoising done.")
    # Gamma correction
    gamma_correction(imIn, gamma)
    IJ.log("     | Gamma correction done.")
    # Adding black slices
    imOut = sandwichPad(imIn)
    IJ.log("     | Padding done.")
    return imOut


def removeBackground(imIn, roi):
    """
    Uses the maximal value found in an ROI to remove the background slice per slice.
    This is particularly useful when the background is not consistent from one slice to another.
    This is a simple background removal by value subtraction.
    """
    imIn.resetRoi()
    removed = []
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        prc.setRoi(roi)
        bg = prc.getStatistics().max
        removed.append(bg)
        prc.resetRoi()
        prc.subtract(bg)
    IJ.log("  > Background removed: " + str(removed))


def convertToIntegers(imIn):
    """
    Takes an image and returns it as an image using an integer representation.
    8  -> 8 bits
    16 -> 16 bits
    32 -> 16 bits
    24 -> error
    In the case of 8 or 16, the image itself is returned.
    For the 32 bits, it starts by scaling all the values between 0 and 1 and then, between 0 and 65535.
    Eventually, it returns a new 16-bits image.
    """
    if imIn.getBitDepth() in [8, 16]:
        return imIn
    
    if imIn.getBitDepth() == 24:
        raise ValueError("Can't handle RGB images.")
    
    ss = StackStatistics(imIn)
    st = ImageStack(imIn.getWidth(), imIn.getHeight())
    for i in range(1, imIn.getNSlices()+1):
        imIn.setSlice(i)
        prc = imIn.getProcessor()
        prc.subtract(ss.min)
        prc.multiply(1.0/(ss.max - ss.min))
        prc.multiply(65535.0)
        st.addSlice(prc.convertToShort(False))
    
    imOut = ImagePlus(imIn.getTitle(), st)
    imIn.close()
    return imOut
    

def preprocessImage(imIn, options):
    """
    Produces an image as it is expected by the random-forest classifier.
    The input image is kept opened as it was opened by the user.
    The process is based on the 'dense spots' and the membrane channels.
    The result is padded with black slices to avoid errors when applying the distance transform.
    """
    dp         = Duplicator()
    chSpots    = dp.run(imIn, options['chSpots'], options['chSpots'], 1, imIn.getNSlices(), 1, 1)
    chMembrane = dp.run(imIn, options['chMembrane'], options['chMembrane'], 1, imIn.getNSlices(), 1, 1)

    blur = 1.0
    roi = imIn.getRoi()
    if roi is None:
        wfs = WaitForUserDialog("ROI required", "Draw an ROI in an empty area.")
        wfs.show()
        roi = imIn.getRoi()

    if roi is None:
        raise ValueError("ROI is required to remove the background.")
    IJ.log("  > Converting first channel")
    chSpots    = convertToIntegers(chSpots)
    IJ.log("  > Converting second channel")
    chMembrane = convertToIntegers(chMembrane)

    IJ.log("  > Cleaning first channel")
    chSpots    = preprocessChannel(chSpots, blur, 0.25, True)
    IJ.log("  > Cleaning second channel")
    chMembrane = preprocessChannel(chMembrane, blur, 1.0, False)

    IJ.log("  > Removing background in first channel")
    removeBackground(chSpots, roi)
    IJ.log("  > Removing background in second channel")
    removeBackground(chMembrane, roi)
    
    imOut = combine(chSpots, chMembrane)
    return imOut


def msi(stacksInfo):
    """
    Returns the maximal stack info.
    """
    maxStack = 0
    maxPos = 0
    for i, s in enumerate(stacksInfo):
        if s[1] > maxStack:
            maxStack = s[1]
            maxPos = i
    return maxPos


def make_training_set(percents=0.6):
    path = IJ.getFilePath("Select a 'sources.txt' file")
    out_path = IJ.getDirectory("Select a folder to save the training set")
    IJ.run("Close All")
    files_list = [os.path.join(out_path, f) for f in os.listdir(out_path) if f.endswith('.tif')]

    if len(files_list) == 0:
        descr = open(path, 'r')
        content = [c for c in descr.read().split('\n') if len(c) > 1 and c.strip()[0] != "#"]
        descr.close()
        shuffle(content)
        content = content[:int(len(content)*percents)]
        produced = []

        for i, c in enumerate(content):
            if c == "":
                continue
            if not os.path.isfile(c):
                IJ.log("File not found: " + c)
                continue
            imIn = IJ.openImage(c)
            imIn.show()

            IJ.log("Processing " + imIn.getTitle() + " (" + str(i+1) + "/" + str(len(content)) + ")")
            
            imOut = preprocessImage(imIn, {
                'chSpots': 1,
                'chMembrane': 3,
                'sizeHoles': 2000
            })

            imOut.setTitle(imIn.getTitle())
            imOut.setCalibration(imIn.getCalibration())
            imIn.close()
            prod = os.path.join(out_path, imOut.getTitle()+".tif")
            IJ.saveAs(imOut, "Tiff", prod)
            produced.append(prod)
            imOut.close()
    else:
        produced = [p for p in files_list if os.path.isfile(p)]

    IJ.log("Processing done. Assembling...")
    IJ.run("Close All")
    production = [IJ.openImage(p) for p in produced]
    stacksInfo = [(p.getTitle(), p.getNSlices()) for p in production]

    i = msi(stacksInfo)
    maxStack = stacksInfo[i][1]
    maxTitle = stacksInfo[i][0]
    IJ.log("Biggest stack: " + str(maxStack) + " for: " + maxTitle)

    calib = production[0].getCalibration()
    padded = [padStack(p, maxStack) for p in production]
    ts = Concatenator().concatenate(padded, False)
    ts.setCalibration(calib)
    ts.setDimensions(2, maxStack, len(padded))
    ts.setTitle("training-set")
    IJ.saveAs(ts, "Tiff", os.path.join(out_path, "training-set.tif"))
    IJ.run("Close All")
    IJ.log("Training set done and saved.")


def main():
    # Get the image path and save it to a file.
    imIn = IJ.getImage()
    fi   = imIn.getOriginalFileInfo()
    path = fi.getFilePath()
    clb  = imIn.getCalibration()
    IJ.log("Image location: " + path)
    IJ.log("=======  Starting preprocessing  ========")

    # Set target and read the options file
    updateTargetImage(path, imIn)
    options = getOptions()
    ppt = imIn.getProperty("invalid-spots-path")

    title = imIn.getTitle()
    imOut = preprocessImage(imIn, options)
    imOut.setCalibration(clb)
    imOut.setProperty("invalid-spots-path", ppt)
    imOut.setTitle("1-preprocessed-" + title)
    imOut.show()
    IJ.log("==> Preprocessing DONE.")


if __name__ == "__main__":
    if IJ.altKeyDown():
        make_training_set()
        IJ.log("Training set done.")
    else:
        main()
    