"""
epsman

Local python script for job JSON file writing.

Can be called from Fabric for remote run case, only requires standard libs + local nbDetails file defining jobs.

Currently duplicates some functions in _repo.py and remoteUploads.py in stripped-down form.

22/01/20

"""

from pathlib import Path
import json
import sys

def readNBdetailsJSON(jsonProcFile):
    """Read previously written nbDetails dictionary from JSON file.

    See _repo.readNBdetailsJSON() for local version.

    """

    print(f"***Reading master JSON file {jsonProcFile}")

    if Path(jsonProcFile).is_file():

        # Read local JSON file.
        with open(jsonProcFile, 'r') as f:
            nbDetails = json.load(f)

        return nbDetails

    else:
        print('File not found.')
        return None


def writeNBdetailsJSON(jsonProcFile, nbDetails):
    """Write nbDetails dictionary to JSON file.

    See _repo.writeNBdetailsJSON() for local version.
    """

    # Write to json file
    # Write to JSON.  Note Path() objects won't serialize.
    with open(jsonProcFile, 'w') as f:
        json.dump(nbDetails, f, indent=2)

    print(f'\n***nbDetails written to local JSON file: {jsonProcFile}')



# If running as main, take passed args and run functions.
# TODO: add log file per job writing here?
if __name__ == "__main__":
    # Passed args
    jsonProcFile = sys.argv[1]

    # Get details from file
    nbDetails = readNBdetailsJSON(jsonProcFile)

    # Write JSON files per job
    for key in nbDetails:
        if key!='proc':
            writeNBdetailsJSON(Path(nbDetails[key]['file']).with_suffix('.json'), nbDetails[key])

    print("JSON writing complete.")
