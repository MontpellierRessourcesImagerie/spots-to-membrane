import os
from random import shuffle

from ij import IJ, WindowManager, ImagePlus, ImageStack
from ij.plugin import Duplicator, Concatenator, ContrastEnhancer
from ij.plugin.filter import BackgroundSubtracter
from ij.process import ImageProcessor
from ij.gui import WaitForUserDialog
from ij.process import AutoThresholder

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


def background_correction(imIn, bg_roi=None, normalize=True):
    bs = BackgroundSubtracter()
    
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        bs.rollingBallBackground(prc, 50.0, False, False, True, True, True)
        if bg_roi is not None:
            prc.setRoi(bg_roi)
            stats = prc.getStats()
            prc.resetRoi()
            prc.subtract(stats.mean * (1.0 + stats.stdDev * 2.0))

    if normalize:
        ce = ContrastEnhancer()
        ce.setNormalize(True)
        ce.setProcessStack(True)
        ce.setUseStackHistogram(False)
        ce.stretchHistogram(imIn, 0.1)

    if bg_roi is None:
        return 
    
    for s in range(1, imIn.getNSlices()+1):
        imIn.setSlice(s)
        prc = imIn.getProcessor()
        prc.setRoi(bg_roi)
        stats = prc.getStats()
        prc.resetRoi()
        prc.subtract(stats.mean * (1.0 + stats.stdDev * 2.0))
        prc.min(0.0)


def isolate_labels(image, labels):
    for s in range(1, image.getNSlices()+1):
        image.setSlice(s)
        prc = image.getProcessor()
        for c in range(image.getWidth()):
            for l in range(image.getHeight()):
                val = int(prc.get(c, l))
                if val not in labels:
                    prc.set(c, l, 0)
                else:
                    prc.set(c, l, 255)
    return image


def segment_with_weka(imIn, classifier_path, labels=None, close_input=False):
    if not (os.path.isfile(classifier_path) and classifier_path.endswith(".classifier")):
        return None
    
    imgplus = ImagePlusAdapter.wrapImgPlus(imIn)
    sc = SegmentationTool()

    sc.openModel(classifier_path)
    result = sc.segment(imgplus)
    raw_seg_membrane = ImageJFunctions.wrap(result, "weka-result")
    temp = raw_seg_membrane.duplicate()
    raw_seg_membrane.close()
    raw_seg_membrane = temp
    raw_seg_membrane.setDimensions(imIn.getNChannels(), imIn.getNSlices(), imIn.getNFrames())

    if labels is None:
        return raw_seg_membrane

    raw_seg_membrane = isolate_labels(raw_seg_membrane, labels)

    if close_input:
        imIn.close()

    return raw_seg_membrane


def threshold(image, method):
    buffer = ImageStack(image.getWidth(), image.getHeight())
    at = AutoThresholder()

    image.setSlice(int((image.getNSlices()+1)/2))
    prc = image.getProcessor()
    stats = prc.getStats()
    histo = [int(i) for i in stats.getHistogram()]
    t = at.getThreshold(method, histo)
    val = stats.histMin + t * stats.binSize

    for s in range(1, image.getNSlices()+1):
        image.setSlice(s)
        prc = image.getProcessor()
        prc.setThreshold(val, 1e30)
        buffer.addSlice(prc.createMask())
    
    img = ImagePlus("cyto-mask", buffer)
    return img


class SpotsToMembrane(object):
    
    def __init__(self):
        self.current = None # Image we are currently working on.
        self.is_batch = False # Are we processing a full folder?
        self.queue   = [] # Only used if 'is_batch' is set to True: List of images to process in the folder.
        self.dump    = True # Should we dump intermediate steps as files on the disk?

        self.spots_dir_path     = None # Path of the folder containing 
        self.current_spots_path = None
        self.current_title      = None # Clean title of the image we are currently working on.

        self.bg_roi = None # ROI used to characterize the background (not unifom across the slices).
        
        self.cyto_mask     = None # Mask of the cytoplasm.
        self.nucleus_mask  = None # Mask of the nucleus.
        self.membrane_mask = None # Mask of the membrane.
        
        self.membrane_classifier_path = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/03-splits-classifier/v1.classifier"
        self.csv_format = 'IMARIS'
        
        self.dump_path = "/home/benedetti/Desktop/dump/"
        self.no_spots = False

    
    def _clear_state(self):
        if self.current is not None:
            self.current.close()
            self.current = None
        
        if self.cyto_mask is not None:
            self.cyto_mask.close()
            self.cyto_mask = None

        if self.nucleus_mask is not None:
            self.nucleus_mask.close()
            self.nucleus_mask = None

        if self.membrane_mask is not None:
            self.membrane_mask.close()
            self.membrane_mask = None

        self.current_spots_path = None
        self.current_title = None
        self.bg_roi = None

    def set_spots_directory(self, folder):
        if not os.path.isdir(folder):
            print("The provided path is not an existing folder.")
            return False
        
        self.spots_dir_path = folder
        return True

    def _get_working_data(self, capture):
        if capture:
            self.current = IJ.getImage()

        if self.current is None:
            print("The active element is not an image.")
            return False
        
        self.current_title = ".".join(self.current.getTitle().split('.')[:-1])

        if self.is_batch:
            im2 = self.current.duplicate()
            im2.show()
            wfud = WaitForUserDialog("ROI required", "Draw an ROI over a patch of background.")
            wfud.show()
            self.bg_roi = im2.getRoi()
            im2.close()
        else:
            self.bg_roi = self.current.getRoi()

        if self.bg_roi is None:
            print("A ROI over a piece of background is required.")
            return False

        if self.no_spots:
            return True
        
        if not os.path.isdir(self.spots_dir_path):
            print("The directory supposed to contains spots doesn't exist")
            return False
        
        content = {f.lower(): f for f in os.listdir(self.spots_dir_path)}
        prefix = self.current_title.lower()
        target = None

        for key, value in content.items():
            if not key.startswith(prefix):
                continue
            target = value
            break

        if target is None:
            print("Impossible to find the spots associated with: " + self.current_title)
            return False

        self.current_spots_path = os.path.join(self.spots_dir_path, target)

        if not os.path.isfile(self.current_spots_path):
            print("Failed to fetch the file: " + self.current_spots_path)
            return False
        
        print("Found spots at: " + self.current_spots_path)
        
        return True

    def _preprocess_cyto(self):
        
        dp = Duplicator()
        
        ch1 = dp.run(
            self.current, 
            1,
            1,
            1, 
            self.current.getNSlices(), 
            1, 
            1
        )

        background_correction(ch1, self.bg_roi)
        
        self.cyto_mask = ch1

        if self.dump:
            IJ.saveAsTiff(ch1, os.path.join(self.dump_path, "preprocess-"+self.current_title+".tif"))

        return True
    
    def _segment_cyto(self):
        rough_mask = threshold(self.cyto_mask, AutoThresholder.Method.Huang)
        strel = Strel3D.Shape.OCTAGON.fromRadiusList(7, 7, 0)
        c_mask = ImagePlus("c_mask", strel.closing(rough_mask.getStack()))
        self.cyto_mask.close()
        self.cyto_mask = c_mask

        if self.dump:
            IJ.saveAsTiff(self.cyto_mask, os.path.join(self.dump_path, "cyto-preprocessmask-rough-"+self.current_title+".tif"))

        return True


    def _segment_membranes(self):
        dp = Duplicator()
        
        ch3 = dp.run(
            self.current, 
            3,
            3,
            1, 
            self.current.getNSlices(), 
            1, 
            1
        )

        background_correction(ch3)
        
        mask = segment_with_weka(ch3, self.membrane_classifier_path, [2, 4], True)
        self.membrane_mask = mask
        
        if self.dump:
            IJ.saveAsTiff(self.membrane_mask, os.path.join(self.dump_path, "raw-membranes-"+self.current_title+".tif"))
        
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

    def run(self, capture=True):

        if not self._get_working_data(capture):
            print("Failed to fetch some data required for processing.")
            return False
        
        if not self._preprocess_cyto():
            print("Failed to preprocess the input image.")
            return False
        
        if not self._segment_cyto():
            print("Failed to make the rough segmentation of cytoplasm.")
            return False
        
        if not self._segment_membranes():
            print("Failed to segment the stained membrane.")
            return False
        
        # if not self._postprocess():
        #     print("Failed to postprocess the segmented image.")
        #     return False

        return True
    
    def run_batch(self, folder, extension, rdq=False, earlyAbort=0):
        
        self.is_batch = True

        if not os.path.isdir(folder):
            print("The provided path is not a folder.")
            return False
        
        self.queue = []

        for f in os.listdir(folder):
            full_path = os.path.join(folder, f)

            if not os.path.isfile(full_path):
                continue

            if not f.lower().endswith(extension.lower()):
                continue

            self.queue.append(full_path)

        if rdq:
            shuffle(self.queue)

        self._clear_state()
        nChars = len(str(len(self.queue)))

        for index, target in enumerate(self.queue):
            self.dump_path = os.path.join(self.dump_path, "image_"+str(index).zfill(3))
            os.mkdir(self.dump_path)
            print("[" + str(index+1).zfill(nChars) + "/" + str(len(self.queue)) + "] Processing: " + target)
            self.current = IJ.openImage(target)
            self.run(False)
            self._clear_state()
            self.dump_path = os.path.dirname(self.dump_path)

            if earlyAbort > 0 and index+1 >= earlyAbort:
                break
        
        return True


def main():
    stm = SpotsToMembrane()

    if not stm.set_spots_directory("/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/positions-csv"):
        print("ERROR.")
        return 1
    
    if not stm.run_batch("/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/raw-files", ".ics", False, 1):
        print("ERROR.")
        return 1
    
    print("DONE.")
    return 0


if __name__ == "__main__":
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

""" TODO
Essayer de ne prendre le threshold qu'à partir de la slice du milieu
"""

""" TODO
Pouvoir donner un chemin pour des ROIs de background (ou les chercher dans le même dossier avec le nom).
"""

""" TODO
Essayer un UNet2D en slice par slice pour la segmentation de ce qui est du cyto ou non.
Tester avec soit C1 soit C3 comme donnée d'input pour voir lequel donne le meilleur résultat.
L'avantage de C1 est qu'on peut tenter de lui faire oublier les cellules non-marquées.
"""

"""TODO
Essayer de faire un UNet3D pour faire une segmentation des membranes ou des cellules.
On peut se baser sur la production de la random forest pour le training-set.
Si le résultat est meilleur, il faudra passer sur Napari plutôt qu'ImageJ.
"""