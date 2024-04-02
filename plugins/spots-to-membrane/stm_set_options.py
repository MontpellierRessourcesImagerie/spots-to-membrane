import os
from ij import IJ
import json
from ij.gui import GenericDialog


def joinAll(pieces):
    start = pieces[0]
    for p in pieces[1:]:
        start = os.path.join(start, p)
    return start


def setOptions(path):
    options_path = os.path.join(path, "options.json")
    chSpots = 1
    chMembrane = 3
    sizeHoles = 2000

    if os.path.isfile(options_path):
        with open(options_path, 'r') as f:
            options = json.load(f)
            chSpots = options['chSpots']
            chMembrane = options['chMembrane']
            sizeHoles = options['sizeHoles']

    gd = GenericDialog("Set options")
    gd.addNumericField("Channel spots", chSpots, 0)
    gd.addNumericField("Channel membrane", chMembrane, 0)
    gd.addNumericField("Size holes", sizeHoles, 0)
    gd.showDialog()
    if (gd.wasCanceled()):
        return
    chSpots = int(gd.getNextNumber())
    chMembrane = int(gd.getNextNumber())
    sizeHoles = int(gd.getNextNumber())
    options = {
        "chSpots": chSpots,
        "chMembrane": chMembrane,
        "sizeHoles": sizeHoles
    }
    with open(options_path, 'w') as f:
        json.dump(options, f)


def main():
    ij_dir      = IJ.getDirectory('plugins')
    dir_mri_cia = "spots-to-membrane"
    settings_dir = os.path.join(ij_dir, dir_mri_cia)
    setOptions(settings_dir)


if __name__ == "__main__":
    main()
    print("Settings updated.")
