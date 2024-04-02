# Spots-to-Membrane

## Introduction

This ImageJ script bundle is designed to assist users in determining the closest distance between specific spots and the cell membrane. The images provided feature individual cells, which may be adjacent to one another, stained to highlight both the membrane and various spots within the cells. The staining of the membrane is inconsistent across the membrane itself and also marks other parts within the cells. This inconsistency makes it impractical to simply create a hull around the cell for analysis.

## Requirements
- LabKit
- MorphoLibJ (IJPB-plugins)
- FeatureJ (ImageScience)
- CLIJ
- CLIJ2

## Installation

This GitHub repository is organized following the same directory hierarchy as Fiji on your computer. To install this plugin, please follow these steps:

- Download the repository ZIP file.
- Unzip it in your desired location.
- Select all the contents from the unzipped folder and drag-and-drop them into your Fiji.app folder.
- Restart Fiji if it was open during this process.

## User Manual

This script bundle is accessible through a toolbar in ImageJ. If installed successfully, you will find a "Spots to Membrane" entry by clicking the ">>" button at the right end of ImageJ's window. The buttons are arranged in the order of the intended workflow.

### 1. Settings
- Channel spots: Index of the channel with the densest spots.
- Channel membrane: Index of the channel with the membrane staining.
- Size holes: The initial segmentation might not be perfect and could contain holes. These can be filled, but this setting limits the maximum size of a hole that can be filled. Setting this number too high may result in filling gaps between "tentacles" of the cell, which is undesirable.

### 2. Preprocess [f1]:
- Open the image you wish to analyze.
- Each button, except for the settings, is assigned a keyboard shortcut (f1 -> f6).
- This feature preprocesses the image according to the pixel classifier's requirements.
- You will be prompted to select an ROI in the background. Choose an area with the most noise but without any bright spots. Ensure no bright spots are present in this ROI on any slice.

### 3. Rough Segmentation [f2]:
- This function utilizes a pixel classifier to categorize each voxel.
- It then creates a rough mask that includes every pixel identified as part of a cell.

### 4. Import Spots [f3]:
- Imports the coordinates of spots (both calibrated and raw) into an ImageJ table.

### 5. Refine Segmentation [f4]:
- Uses the rough mask and the list of points to generate a more refined mask.
Employing watershed splitting may extend the process duration but can result in isolating only the cell of interest in your image.

### 6. Dump Spot [f5]:
- Spots are now listed in the ROI manager, but some may be invalid. For instance, they might be too close to another cell (resulting in incorrect distance measurements) or located in the background.
- To exclude these spots, navigate through the ROI manager using the keyboard's up and down arrows, and press 'f5' for each invalid spot you identify. These spots will remain visible in your ROI manager but will be disregarded in the subsequent phase.

### 7. Export Distance [f6]:
- Generates a table and a control image showing the distance from each spot to the membrane.
- The results can be exported as a CSV file.
- By default, the file is named after the image's name.
