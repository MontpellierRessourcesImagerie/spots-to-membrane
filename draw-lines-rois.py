from ij import IJ, ImagePlus, ImageStack
from ij.plugin.frame import RoiManager
from ij.process import ByteProcessor
from java.awt import Color
from ij.gui import Roi
from inra.ijpb.morphology import Strel

def main():
	rm = RoiManager.getInstance()
	imIn = IJ.getImage()
	if rm is None:
		print("No ROI manager found")
		return
	
	all_rois = rm.getRoisAsArray()
	print(str(len(all_rois)) + " ROIs found")
	buffer = ImageStack(imIn.getWidth(), imIn.getHeight())
	inputs = ImageStack(imIn.getWidth(), imIn.getHeight())
	
	idRoi = 0
	canvas = {}
	strel = Strel.Shape.SQUARE.fromRadius(5)
	
	for idRoi in range(len(all_rois)):
		sliceIdx = int(rm.getName(idRoi).split('-')[0])
		bp = canvas.get(sliceIdx, ByteProcessor(imIn.getWidth(), imIn.getHeight()))
		bp.setColor(Color.WHITE)
		bp.draw(all_rois[idRoi])
		canvas[sliceIdx] = bp
	
	for key, value in canvas.items():
		buffer.addSlice(strel.dilation(value))
		imIn.setSlice(key)
		inputs.addSlice(imIn.getProcessor())
		
	imOut = ImagePlus("masks", buffer)
	imTrn = ImagePlus("inputs", inputs)
	imOut.show()
	imTrn.show()
	
main()
		
	
		