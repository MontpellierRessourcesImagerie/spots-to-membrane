import os, json, re
from ij import IJ, ImageStack, ImagePlus
from ij.plugin import ChannelSplitter, Scaler
from ij.process import ShortProcessor
from ij.measure import Calibration


def getTargetPath():
    """
    Reads the file 'spots_to_membrane.txt' located in the 'spots-to-membrane' folder.
    Extracts the absolute path of the target image from it.
    The 'target' is the original file on the disk.

    Returns:
        str: The absolute path of the target image. (or None if the file is not found)
    """
    ij_dir      = IJ.getDirectory('plugins')
    dir_mri_cia = "spots-to-membrane"
    f_name      = "spots_to_membrane.txt"
    settings_dir = os.path.join(ij_dir, dir_mri_cia)
    f_path = os.path.join(settings_dir, f_name)
    if not os.path.isfile(f_path):
        IJ.log("No target file found.")
        return None
    descr = open(f_path, 'r')
    imgPath = descr.read().strip()
    descr.close()
    IJ.log("     | Accessing target image: " + imgPath + ".")
    return imgPath


def getOptions():
    """
    Reads the file 'options.json' located in the 'spots-to-membrane' folder.
    Extracts the options from it, and produces a dictionary.
    The options are the channels to use for the spots and the membrane, and the minimal size of holes to fill.

    Returns:
        dict: The options extracted from the file. (or None if the file is not found)
    """
    chSpots = 1
    chMembrane = 3
    sizeHoles = 2000

    ij_dir       = IJ.getDirectory('plugins')
    dir_mri_cia  = "spots-to-membrane"
    settings_dir = os.path.join(ij_dir, dir_mri_cia)
    options_path = os.path.join(settings_dir, "options.json")

    if os.path.isfile(options_path):
        with open(options_path, 'r') as f:
            options = json.load(f)
            chSpots = options['chSpots']
            chMembrane = options['chMembrane']
            sizeHoles = options['sizeHoles']
    else:
        IJ.log("No options file found. Using default values.")
        return None

    return {'chSpots': chSpots, 'chMembrane': chMembrane, 'sizeHoles': sizeHoles}


def updateTargetImage(path, imIn):
    """
    Updates the file 'spots_to_membrane.txt' located in the 'spots-to-membrane' folder.
    Overwrites the path of the target image with the new one, which is the path of the current image.
    The file is created if it doesn't exist.
    It creates at the same time a file that will contain the invalid spots for that image.
    In that second file, the stored data is the name of the ROIs to remove from the ROI manager.

    Args:
        path (str): The absolute path of the new target image.
        imIn (ImagePlus): The current image.
    """
    ij_dir       = IJ.getDirectory('plugins')
    dir_mri_cia  = "spots-to-membrane"
    settings_dir = os.path.join(ij_dir, dir_mri_cia)
    f_name       = "spots_to_membrane.txt"
    f_path = os.path.join(settings_dir, f_name)
    descr  = open(f_path, 'w')
    descr.write(path)
    descr.close()
    descr = None
    
    invalid_path = os.path.join(settings_dir, imIn.getTitle() + ".txt")
    descr = open(invalid_path, 'w')
    descr.close()

    imIn.setProperty("invalid-spots-path", invalid_path)
    


def sandwichPad(imIn):
    """
    Adds a black slice at the beginning and at the end of the stack.
    Can be used with every bit depth.
    The original image is closed, the returned image is a new instance.
    The calibration is transferred to the new image.
    This function doesn't handle multi-channel images.

    Args:
        imIn (ImagePlus): The image to pad.

    Returns:
        ImagePlus: The padded image, with new empty slices at the beginning and at the end.
    """
    s1 = imIn.getProcessor().duplicate()
    s1.max(0)
    s2 = s1.duplicate()
    stack = ImageStack(imIn.getWidth(), imIn.getHeight())
    stack.addSlice(s1)
    for i in range(1, imIn.getNSlices()+1):
        imIn.setSlice(i)
        stack.addSlice(imIn.getProcessor())
    stack.addSlice(s2)
    title = imIn.getTitle()
    calib = imIn.getCalibration()
    imIn.close()
    imOut = ImagePlus(title, stack)
    imOut.setCalibration(calib)
    return imOut


def padStack(imIn, targetSize):
    """
    Pads the stack with black slices to reach the target size.
    All new slices are added at the end of the stack, not in "sandwich" mode.
    This function can handle multi-channel images.
    The original image is closed, the returned image is a new instance.

    Args:
        imIn (ImagePlus): The image to pad.
        targetSize (int): The target number of slices.

    Returns:
        ImagePlus: The padded image containing 'targetSize' slices.
    """
    calib = imIn.getCalibration()
    stack16 = ImageStack(imIn.getWidth(), imIn.getHeight())
    ch = ChannelSplitter.split(imIn)
    title = imIn.getTitle()
    nslices = imIn.getNSlices()
    nchannels = len(ch)
    imIn.close()

    for i in range(1, nslices+1):
        for j in range(nchannels):
            ch[j].setSlice(i)
            prc = ch[j].getProcessor()
            stack16.addSlice(prc)

    for i in range(nslices+1, targetSize+1):
        for j in range(nchannels):
            prc = ShortProcessor(imIn.getWidth(), imIn.getHeight())
            stack16.addSlice(prc)

    imShort = ImagePlus("padded", stack16)
    imShort.setCalibration(calib)
    imIn.close()
    imShort.setTitle(title)
    
    imShort.setDimensions(nchannels, targetSize, 1)

    return imShort


def lastClassifierVersion(folder):
    """
    Classifiers are saved as 'vXXX.classifier', where XXX is a number padded with zeros.
    They are located in the 'spots-to-membrane' folder.
    This function searches for the most recent classifier (in case several are present due to updates).

    Args:
        folder (str): The folder where the classifiers are stored.

    Returns:
        str: The name of the most recent classifier file. (not the path)
    """
    regex = re.compile(r'^v(\d{3})\.classifier$')
    max_num = -1
    most_recent = None

    for file_name in os.listdir(folder):
        match = regex.match(file_name)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
                most_recent = file_name

    return most_recent


def getClassifierPath():
    """
    Attempts to build the absolute path to the most recent classifier file.
    Searches for it in the 'spots-to-membrane' folder, which is located in the 'plugins' directory of ImageJ.

    Returns:
        str: The absolute path to the most recent classifier file. None if no classifier file is found.
    """
    plugins_dir = IJ.getDirectory('plugins')
    dir_stm = "spots-to-membrane"
    pgPath = os.path.join(plugins_dir, dir_stm)

    f_name = lastClassifierVersion(pgPath)
    classif_path = os.path.join(pgPath, f_name)

    return classif_path if os.path.isfile(classif_path) else None


def makeIsotropic(imIn):
    """
    Rescales the input image to make it isotropic.
    The original image is closed, and a new ImagePlus is returned.
    The conversion is artificial, and the image is not interpolated.

    Args:
        imIn (ImagePlus): The image to rescale.
    
    Returns:
        ImagePlus: The rescaled image.
        float: The factor used to rescale the image on the Z axis.
    """
    title = imIn.getTitle()
    calib = imIn.getCalibration()
    xy = calib.pixelWidth
    z = calib.pixelDepth
    factor = z/xy
    width = imIn.getWidth()
    height = imIn.getHeight()
    nslices = imIn.getNSlices()
    depth = int(nslices * factor)
    IJ.log("  > Rescaling to isotropic: " + str((width, height, nslices)) + " -> " + str((width, height, depth)))

    rescaled = Scaler.resize(imIn, width, height, depth, "none")
    imIn.close()

    iso_calib = Calibration()
    iso_calib.pixelWidth = xy
    iso_calib.pixelHeight = xy
    iso_calib.pixelDepth = xy
    iso_calib.setUnit(calib.getUnit())
    rescaled.setCalibration(iso_calib)
    rescaled.setTitle("iso-"+title)

    return rescaled, factor
