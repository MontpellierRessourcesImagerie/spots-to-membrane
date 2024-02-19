from ij import IJ, ImagePlus, ImageStack
from net.imglib2.img import ImagePlusAdapter
from net.imagej import ImgPlus
from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imglib2.img.display.imagej import ImageJFunctions
from inra.ijpb.label.LabelImages import keepLabels
from ij.plugin import Thresholder
from ij.process import ByteProcessor
import os


def joinAll(pieces):
    start = pieces[0]
    for p in pieces[1:]:
        start = os.path.join(start, p)
    return start


def getClassifierPath():
    plugins_dir = IJ.getDirectory('plugins')
    dir_stm = "spots_to_membrane"
    f_name = "current.classifier"

    settings_dir = joinAll([
        plugins_dir,
        dir_stm
    ])

    classif_path = os.path.join(settings_dir, f_name)

    # TEMP
    return "/home/benedetti/Documents/projects/22-spots-to-membrane/spots-to-membrane/plugins/spots-to-membrane/current.classifier"

    if not os.path.isfile(classif_path):
        return None
    else:
        return classif_path
    

def padResults(imIn):
    stackOut = ImageStack()
    first = ByteProcessor(imIn.getWidth(), imIn.getHeight())
    last = ByteProcessor(imIn.getWidth(), imIn.getHeight())
    stackOut.addSlice(first)

    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        stackOut.addSlice(imIn.getProcessor())

    stackOut.addSlice(last)
    title = imIn.getTitle()
    imIn.close()

    return ImagePlus(title, stackOut)


def main():
    image = IJ.getImage()
    imgplus = ImagePlusAdapter.wrapImgPlus(image)
    clb = image.getCalibration()
    title = image.getTitle()

    sc = SegmentationTool()
    c_path = getClassifierPath()
    sc.openModel(c_path)
    sc.setUseGpu(True)
    result = sc.segment(imgplus)

    output = ImageJFunctions.wrap(result, "segmented") # wraps the ImgPlus as an ImagePlus
    raw_seg = output.duplicate()
    output.close()
    
    interest_labels = [2, 3]
    labelsOut = keepLabels(raw_seg, interest_labels)
    raw_seg.close()

    stackOut = ImageStack()

    for s in range(1, labelsOut.getNSlices()+1):
        labelsOut.setSlice(s)
        prc = labelsOut.getProcessor()
        prc.setThreshold(1, max(interest_labels))
        stackOut.addSlice(prc.createMask())

    maskOut = ImagePlus("mask-"+title, stackOut)
    labelsOut.close()
    imOut = padResults(maskOut)
    imOut.setCalibration(clb)
    imOut.show()


if __name__ == "__main__":
    main()
    print("Rough segmentation done.")