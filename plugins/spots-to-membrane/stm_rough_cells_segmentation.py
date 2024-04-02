from ij import IJ, ImagePlus, ImageStack
from net.imglib2.img import ImagePlusAdapter
from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imglib2.img.display.imagej import ImageJFunctions
from inra.ijpb.label.LabelImages import keepLabels
from spots_to_membrane.spotsToMembrane import getClassifierPath, makeIsotropic


def main():
    image = IJ.getImage()
    ppt = image.getProperty("invalid-spots-path")
    imgplus = ImagePlusAdapter.wrapImgPlus(image)
    clb = image.getCalibration()
    title = image.getTitle().replace("1-preprocessed-", "2-rough-mask-")
    tryGPU = True
    result = None

    IJ.log("=======  Starting pixels classification  ========")

    try:
        IJ.log("  > Attempting segmentation on GPU.")
        sc = SegmentationTool()
        c_path = getClassifierPath()
        sc.openModel(c_path)
        sc.setUseGpu(True)
        result = sc.segment(imgplus)
    except Exception as e:
        IJ.log("  > Failed to run on GPU, trying on CPU.")
        tryGPU = False
    
    if not tryGPU:
        try:
            sc = SegmentationTool()
            sc.openModel(c_path)
            sc.setUseGpu(False)
            result = sc.segment(imgplus)
        except Exception as e:
            IJ.log("  > Error: ", e)
            IJ.log("  > Segmentation failed on CPU.")
            return 1

    output = ImageJFunctions.wrap(result, "segmented") # wraps the ImgPlus as an ImagePlus
    raw_seg = output.duplicate()
    output.close()
    
    IJ.log("  > Isolating labels of interest")
    interest_labels = [1, 2, 3, 6]
    labelsOut = keepLabels(raw_seg, interest_labels)
    raw_seg.close()

    IJ.log("  > Creating a mask from labels")
    stackOut = ImageStack()
    for s in range(1, labelsOut.getNSlices()+1):
        labelsOut.setSlice(s)
        prc = labelsOut.getProcessor()
        prc.setThreshold(1, max(interest_labels))
        stackOut.addSlice(prc.createMask())

    mask = ImagePlus("mask-"+title, stackOut)

    # Clearing first and last slice to recover padding.
    mask.setCalibration(clb)
    mask.setSlice(1)
    mask.getProcessor().max(0)
    mask.setSlice(mask.getNSlices())
    mask.getProcessor().max(0)
    labelsOut.close()

    imOut, f = makeIsotropic(mask)
    IJ.log("  > Transform mask into pseudo-isotropic stack.")
    imOut.setProperty("anisotropy-factor", str(f))
    imOut.setProperty("invalid-spots-path", ppt)
    IJ.log("     | Anisotropy factor: " + str(f))
    imOut.setTitle(title)
    imOut.show()
    IJ.log("==> Rough segmentation DONE.")


if __name__ == "__main__":
    main()