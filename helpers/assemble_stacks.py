from ij import IJ, ImagePlus, ImageStack
from ij import WindowManager
from ij.process import ImageProcessor, FloatProcessor, ByteProcessor
from ij.plugin import Concatenator
from ij.plugin import ChannelSplitter
import os
from random import shuffle

# Picking the sources.
folder = IJ.getDirectory("Choose a folder")
keep = 0.8
content = os.listdir(folder)
shuffle(content)
content = content[:int(len(content)*keep)]

images = [IJ.openImage(os.path.join(folder, f)) for f in content]
# images = [WindowManager.getImage(i) for i in WindowManager.getImageTitles() if not i.startswith("uniform")]
print("Working with images:")
for t in images:
	print("   - " + t.getTitle() + " > (" + str(t.getNChannels()) + ", " + str(t.getNSlices()) + ", " + str(t.getNFrames()) + ")")
maxSize = 0
cct = Concatenator()

for img in images:
	if img.getNSlices() > maxSize:
		maxSize = img.getNSlices()
	nc = img.getNChannels()
		
print("Biggest stack: " + str(maxSize))

frames = []
for img in images:
	# Adding black slice at the begining:
	bu_out = ImageStack(img.getWidth(), img.getHeight())
	channels = ChannelSplitter.split(img)
	# for _ in range(nc):
	# 	prc    = ByteProcessor(img.getWidth(), img.getHeight())
	# 	bu_out.addSlice(prc)
	
	# Copying slices:
	for i in range(1, img.getNSlices()+1):
		for j in range(nc):
			img = channels[j]
			img.setSlice(i)
			bu_out.addSlice(img.getProcessor())
	
	# Adding black slices to reach target size:
	for i in range(maxSize - img.getNSlices()):
		for _ in range(nc):
			prc = ByteProcessor(img.getWidth(), img.getHeight())
			bu_out.addSlice(prc)

	for c in channels:
		c.close()
		
	# Add a last slice of each channel
	# for _ in range(nc):
	# 	prc = ByteProcessor(img.getWidth(), img.getHeight())
	# 	bu_out.addSlice(prc)
	
	# Encapsulate in an image
	imOut = ImagePlus("uniform-"+img.getTitle(), bu_out)
	imOut.setDimensions(nc, maxSize, 1)
	frames.append(imOut)
	img.close()

ts = cct.concatenate(frames, False)
ns = maxSize
nf = len(frames)
print("Final stack: (" + str(nc) + ", " + str(ns) + ", " + str(nf) + ")")
ts.setDimensions(nc, ns, nf)
ts.show()