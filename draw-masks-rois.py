from ij import IJ, ImagePlus, ImageStack
from ij.plugin.frame import RoiManager
from ij.process import ByteProcessor
from java.awt import Color
from ij.gui import Roi

def main():
	rm = RoiManager.getInstance()
	imIn = IJ.getImage()
	if rm is None:
		print("No ROI manager found")
		return
	
	all_rois = rm.getRoisAsArray()
	print(str(len(all_rois)) + " ROIs found")
	buffer = ImageStack(imIn.getWidth(), imIn.getHeight())
	
	for s in range(imIn.getNFrames()):
		bp = ByteProcessor(imIn.getWidth(), imIn.getHeight())
		if all_rois[s].getType() != Roi.POINT:
			bp.setColor(Color.WHITE)
			bp.fill(all_rois[s])
		buffer.addSlice(bp)
	
	imOut = ImagePlus("masks", buffer)
	imOut.show()
	
main()
		
	
		