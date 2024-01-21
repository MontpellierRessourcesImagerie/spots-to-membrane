from ij import IJ, ImagePlus, ImageStack
from ij.plugin.frame import RoiManager
from ij.process import ByteProcessor
from java.awt import Color
from ij.gui import Roi
from ij import WindowManager
from ij.plugin import Duplicator
import os

def main(root_path):
	inputs = None
	masks = None
	dp = Duplicator()
	
	input_dir = os.path.join(root_path, "inputs")
	mask_dir  = os.path.join(root_path, "masks")
	
	ids = WindowManager.getIDList()
	for w in ids:
		img = WindowManager.getImage(w)
		if img.getTitle().lower().startswith("mask"):
			masks = img
		if img.getTitle().lower().startswith("input"):
			inputs = img
	
	if (inputs is None) or (masks is None):
		print("Inputs or masks is missing")
		return
	
	if inputs.getNFrames() != masks.getNFrames():
		print("Both images are not the same size")
		return
		
	for f in range(1, inputs.getNFrames()+1):
		unique_input = dp.run(inputs, 1, 1, 1, 1, f, f)
		unique_mask  = dp.run(masks, 1, 1, 1, 1, f, f)
		input_path = os.path.join(input_dir, "item_" + str(f).zfill(3) + ".tif")
		mask_path = os.path.join(mask_dir, "item_" + str(f).zfill(3) + ".tif")
		IJ.saveAsTiff(unique_input, input_path)
		IJ.saveAsTiff(unique_mask, mask_path)


main("/home/benedetti/Desktop/dl-celia")