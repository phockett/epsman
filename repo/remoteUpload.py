"""
epsman

Local python script for job upload to repo.

Can be called from Fabric for remote run case, only requires standard libs + local nbDetails file defining uploads.

Currently duplicates some functions in _repo.py, in stripped-down form.

09/01/20    v1

"""

from pathlib import Path
import json


def readNBdetailsJSON(jsonProcFile):
    """Read previously written nbDetails dictionary from JSON file.

    See _repo.readNBdetailsJSON() for local version.

    """

    print(f"***Reading local JSON file {jsonProcFile}")

    if Path(jsonProcFile).is_file():

        # Read local JSON file.
        with open(jsonProcFile, 'r') as f:
            nbDetails = json.load(f)

        return nbDetails

    else:
        print('File not found.')
        return None


def uploadRepoFiles(nbDetails, key, ACCESS_TOKEN):
    """Upload files to repo (from local machine)

    See _repo.uploadRepoFiles() for local version.

    """

    url = f"https://zenodo.org/api/deposit/depositions/{nbDetails[key]['repoInfo']['id']}/files?access_token={ACCESS_TOKEN}"

    outputs = []
    for fileIn in nbDetails[key]['repoFiles']:
        data = {'name': Path(fileIn).name}
        files = {'file': open(fileIn, 'rb')}
        r = requests.post(url, data=data, files=files)

        if r.ok:
            print(f"File upload OK: {fileIn}")
        else:
            print(f"File upload failed: {fileIn}")

        outputs.append([r.ok, r.json()])

    # nbDetails[key]['repoFilesUpload'] = outputs
    # return nbDetails
    return outputs

def writeNBdetailsJSON(jsonProcFile, nbDetails):
    """Write nbDetails dictionary to JSON file."""

    # Write to json file
    # Write to JSON.  Note Path() objects won't serialize.
    with open(jsonProcFile, 'w') as f:
        json.dump(nbDetails, f, indent=2)

    print(f'\n***nbDetails written to local JSON file: {jsonProcFile}')


# If running as main, take passed args and run functions.
if __name__ == "__main__":
    # Passed args
    jsonProcFile = sys.argv[1]
    ACCESS_TOKEN = sys.argv[2]

    print("***Running uploads to repo.")

    # Get details from file
    nbDetails = readNBdetailsJSON(jsonProcFile)

    # Upload files & log result.
    for key in nbDetails:
        if key!='proc' and nbDetails[key]['pkg'] and self.nbDetails[key]['archFilesOK']:
            nbDetails[key]['repoFilesUpload'] = uploadRepoFiles(nbDetails, key, ACCESS_TOKEN)
        else:
            print(f"***Skipping item {key} upload")

    # Write to new JSON file
    writeNBdetailsJSON(jsonProcFile + '.upload', nbDetails)
