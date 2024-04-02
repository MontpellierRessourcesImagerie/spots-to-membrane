import os

def remove_dup_prefix(folder_path):
  """
  This function takes a folder path and renames all files starting with "DUP_"
  by removing the prefix.

  Args:
      folder_path (str): The path to the folder containing the files.
  """
  for filename in os.listdir(folder_path):
    if filename.startswith("DUP_"):
      new_filename = filename[4:]  # Remove the first 4 characters ("DUP_")
      old_path = os.path.join(folder_path, filename)
      new_path = os.path.join(folder_path, new_filename)
      # Check if the new filename already exists before renaming
      if not os.path.exists(new_path):
        os.rename(old_path, new_path)
      else:
        print(f"Warning: Skipping {filename} as {new_filename} already exists.")


def find_sources(folder_path, sources):
    """
    Function searching for the folder each element comes from.
    """

    # Build a dictionary with the source of each file.
    folders = {}
    for source in sources:
        content = [f for f in os.listdir(source) if f.endswith('.ics')]
        for c in content:
            folders[c] = source

    # Finds every single file in the folder.
    source_files = []
    targets = [f for f in os.listdir(folder_path) if f.endswith('.tif')]
    for target in targets:
        t_file = ".".join(target.split('.')[:-1]) + ".ics"
        if t_file in folders:
            source_files.append((folders[t_file], t_file))

    # Assessments.
    print(f"{len(source_files)}/{len(targets)} files found.")
    return source_files


sources = find_sources(
     '/home/benedetti/Documents/projects/22-spots-to-membrane/data/training-set/training-set-v1',
     (
        '/home/benedetti/Documents/projects/22-spots-to-membrane/data/001-FL120-cells-no-tentacles/raw-files',
        '/home/benedetti/Documents/projects/22-spots-to-membrane/data/002-other-staining',
        '/home/benedetti/Documents/projects/22-spots-to-membrane/data/003-imgs-tentacles'
     )
)

with open('/home/benedetti/Documents/projects/22-spots-to-membrane/data/training-set/sources.txt', 'w') as f:
    for source in sources:
        f.write(f"{os.path.join(source[0],source[1])}\n")
from pprint import pprint
pprint(sources)