import os
from random import randint

from ij import IJ, WindowManager, ImagePlus, ImageStack
from ij.plugin import Duplicator, Concatenator, ContrastEnhancer
from ij.plugin.filter import BackgroundSubtracter
from ij.process import ImageProcessor

from imagescience.image import Axes, Image, FloatImage
from imagescience.transform import Mirror

from net.imglib2.img import ImagePlusAdapter
from net.imagej import ImgPlus
from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imglib2.img.display.imagej import ImageJFunctions

from inra.ijpb.label import LabelImages
from inra.ijpb.label.conncomp import FloodFillRegionComponentsLabeling3D
from inra.ijpb.morphology import Strel3D
from inra.ijpb.binary.distmap import ChamferMask3D


def imaris_csv_loader(path):
    raw = ""
    with open(path, 'r') as descr:
        raw = descr.read()
    lines = raw.split('\n')
    headers = lines[3].split(',')
    xyz = [0, 1, 2]

    for idx, header in enumerate(headers):
        if header == "Position X":
            xyz[0] = idx
        if header == "Position Y":
            xyz[1] = idx
        if header == "Position Z":
            xyz[2] = idx

    for line in lines[4:]:
        items = line.split(',')
        co = (float(items[xyz[0]]), float(items[xyz[1]]), float(items[xyz[2]]))


class SpotsToMembrane(object):
    
    def __init__(self):
        self.current = None # Current image we have to work on.
        self.image_path = None
        self.spots_path = None
        self.membrane_channel = 3
        self.membrane_label = 1
        self.raw_seg_membrane = None
        self.membrane_image = None
        self.isBatch = False
        self.queue = []
        self.classifier_path = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/01-classifier-cells/v4.classifier"
        self.format = 'IMARIS'
        self.exportIntermediates = True
        self.tempDump = "/home/benedetti/Desktop/dump/"
        self.noSpots = True

    def nextImage(self):
        pass

    def _background_correction(self, imIn):
        bs = BackgroundSubtracter()
        for s in range(imIn.getNSlices()):
            imIn.setSlice(s)
            bs.rollingBallBackground(imIn.getProcessor(), 50.0, False, False, True, True, True)

    def _preprocess(self):
        if self.current.getNChannels() < self.membrane_channel:
            print("Not enough channels in input image.")
            return False
        
        dp = Duplicator()

        ce = ContrastEnhancer()
        ce.setNormalize(True)
        ce.setProcessStack(True)
        ce.setUseStackHistogram(False)
        
        membrane = dp.run(
            self.current, 
            self.membrane_channel, 
            self.membrane_channel, 
            1, 
            self.current.getNSlices(), 
            1, 
            1
        )

        self._background_correction(membrane)
        ce.stretchHistogram(membrane, 0.1)
        self.membrane_image = membrane

        if self.exportIntermediates:
            IJ.saveAsTiff(self.membrane_image, os.path.join(self.tempDump, "preprocess-"+self.current.getTitle()))

        return True

    def _segment(self):
        imgplus = ImagePlusAdapter.wrapImgPlus(self.membrane_image)
        sc = SegmentationTool()

        if not os.path.isfile(self.classifier_path) or not self.classifier_path.endswith(".classifier"):
            print("Classifier not found.")
            return False
    
        sc.openModel(self.classifier_path)
        result = sc.segment(imgplus)
        self.raw_seg_membrane = ImageJFunctions.wrap(result, "raw-segmentation-"+self.membrane_image.getTitle())
        
        if self.exportIntermediates:
            IJ.saveAsTiff(self.raw_seg_membrane, os.path.join(self.tempDump, "raw-seg-"+self.current.getTitle()))

        self.membrane_image.close()
        self.membrane_image = None

        temp = LabelImages.keepLabels(self.raw_seg_membrane, [self.membrane_label])
        self.raw_seg_membrane.close()
        self.raw_seg_membrane = temp

        IJ.setRawThreshold(self.raw_seg_membrane, 1, 65535)
        IJ.run(self.raw_seg_membrane, "Convert to Mask", "background=Dark black")

        if self.exportIntermediates:
            IJ.saveAsTiff(self.raw_seg_membrane, os.path.join(self.tempDump, "seg-mask-"+self.current.getTitle()))

        return True

    def _postprocess(self):
        # - Remove debris left over after pixels classification
        ffrcl = FloodFillRegionComponentsLabeling3D(26, 16)
        labeled_stack = ffrcl.computeLabels(self.raw_seg_membrane.getStack(), 255)
        labeled_stack = LabelImages.volumeOpening(labeled_stack, 2000)
        
        # - Faire un gros closing.
        strel = Strel3D.Shape.BALL.fromRadiusList(13, 13, 1)
        labeled_stack = strel.closing(labeled_stack)

        # - Quelques érosions.
        strel = Strel3D.Shape.CUBE.fromRadiusList(6, 6, 1)
        labeled_stack = strel.erosion(labeled_stack)
        labeled = ImagePlus("labeled", labeled_stack)

        # - Boucher les trous slice par slice.
        IJ.run(labeled, "Fill Holes", "stack")
    
        # - Chamfer distance 3D.
        ch = ChamferMask3D.QUASI_EUCLIDEAN
        distMapStack = LabelImages.distanceMap(labeled.getStack(), ch, True, True)
        labeled.close()
        distMap = ImagePlus("dist-map-3d", distMapStack)

        # - Trouver les extended maxima en 3D.
        # - Trouver les maximas en 3D.
        # - Lancer un marker-controled watershed.
        # - Ne garder que le plus gros élément (ou demander une intervention user).

        if self.exportIntermediates:
            IJ.saveAsTiff(distMap, os.path.join(self.tempDump, "final-mask-"+self.current.getTitle()))

        return True

    def _parse_spots(self):
        if self.format == 'IMARIS':
            self.spots = imaris_csv_loader(self.spots_path)
            return self.spots is not None
        
        return False

    def _clear_state(self):
        if self.current is not None:
            self.current.close()
            self.current = None

    def _get_image_path(self):
        current_image = self.current
        if current_image is None:
            print("No image found.")
            return None

        file_info = current_image.getOriginalFileInfo()
        if file_info is None:
            print("The current image doesn't own file info.")
            return None
        
        return os.path.join(file_info.directory, file_info.fileName)
    
    def _fetch_paths(self):
        i_path = self._get_image_path()
        if (i_path is None) or (not os.path.isfile(i_path)):
            print("The image path doesn't correspond to any file.")
            return False
        
        if self.noSpots:
            print("The spots will be skipped.")
            return True
        
        directory = os.path.dirname(i_path)
        if not os.path.isdir(directory):
            print("Failed to find the parent directory.")
            return False
        
        # For files transfered from Windows to Linux:
        name = os.path.basename(i_path)
        csv_name_low = ".".join(name.split(".")[:-1]) + ".csv"
        content = {n.lower(): n for n in os.listdir(directory)}
        csv_name = content.get(csv_name_low, None)
        if csv_name is None:
            print("The spots associated to: " + name + " could not be found.")
            return False
        
        self.image_path = i_path
        self.spots_path = os.path.join(directory, csv_name)
        return True

    def run(self, capture=True):
        if capture:
            try:
                IJ.getImage()
            except:
                print("No image to work on.")
                return False
            self.current = IJ.getImage() # WindowManager.getCurrentImage()
            print("Working on image: " + self.current.getTitle())
        
        if not self._fetch_paths():
            print("Failed to fetch necessary paths.")
            return False
        
        if not self._preprocess():
            print("Failed to preprocess the input image.")
            return False
        
        if not self._segment():
            print("Failed to segment the stained membrane.")
            return False
        
        if not self._postprocess():
            print("Failed to postprocess the segmented image.")
            return False

        return True

    def runBatch(self):
        self.run(False)


def main():
    stm = SpotsToMembrane()
    if not stm.run():
        print("An error occured. END.")
        return 1
    return 0


main()



""" NOTE
Dans la mesure où séparer les cellules qui se touchent est très complexe et source d'erreurs.
Pour les spots, on va donc uniquement garder un masque qui correspond à ce qui est de la cellule.
Une erreur va être introduite pour les spots qui se trouvent proche de la zone de contact.
À voir si statistiquement, cela représente beaucoup de spots.
"""

""" TODO
Refaire un export sous forme d'image de tous les CSV de spots qui ont été fournis.
Intégrer cela comme une méthode dans la classe.
"""

"""TODO
Essayer de faire un UNet3D pour faire une segmentation des membranes ou des cellules.
On peut se baser sur la production de la random forest pour le training-set.
Si le résultat est meilleur, il faudra passer sur Napari plutôt qu'ImageJ.
"""