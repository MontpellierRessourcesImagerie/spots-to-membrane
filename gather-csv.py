import os
import shutil

def copy_csv_to_parent(parent_directory):
    for root, dirs, files in os.walk(parent_directory):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                shutil.copy(file_path, parent_directory)
                print(f"Copied {file} to {parent_directory}")

# Utilisez le chemin du dossier parent ici
parent_directory = "/home/benedetti/Documents/projects/22-felipe-membrane-spots/images-felipe-no-tentacle/FL120-cells/positions-csv"
copy_csv_to_parent(parent_directory)
