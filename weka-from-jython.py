from ij import IJ, ImagePlus
from net.imglib2.img import ImagePlusAdapter
from net.imagej import ImgPlus
from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imglib2.img.display.imagej import ImageJFunctions

def main():
    # 1. Get current image to segment it.
    image = IJ.getImage()

    # 2. Wrap the image in an ImgPlus object
    imgplus = ImagePlusAdapter.wrapImgPlus(image)
    #imgplus = ImgPlus(img)

    # 3. Segment the image
    sc = SegmentationTool()
    sc.openModel("/home/benedetti/Documents/projects/22-felipe-membrane-spots/01-classifier-cells/v4.classifier")
    # sc.setUseGpu(True)
    result = sc.segment(imgplus)

    # 4. Cast the result into an ImagePlus object.
    output = ImageJFunctions.wrap(result, "segmented") # wraps the ImgPlus as an ImagePlus
    output.show()

    # ImgPlus<UnsignedByteType> SegmentationTool::segment(ImgPlus<?> image)

main()
print("DONE.")