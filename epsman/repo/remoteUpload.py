"""
epsman

Local python script for job upload to repo.

Can be called from Fabric for remote run case, only requires standard libs + local nbDetails file defining uploads.

Currently duplicates some functions in _repo.py, in stripped-down form.

20/01/20    Testing for Zenodo uploads.  Issue with files >100Mb... drops out with errors, but not messages.

09/01/20    v1

"""

from pathlib import Path
import json
import sys
import pprint
import requests
import os
import glob

#from epsman.repo.pkgFiles import convert_bytes
# Basic bytes to KB/Mb... conversion, from https://stackoverflow.com/questions/2104080/how-to-check-file-size-in-python
def convert_bytes(num):
    """
    This function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB']:  # , 'GB', 'TB']:  Keep to MB in this case.
        if num < 1024.0:
#             return "%3.1f %s" % (num, x)
            return [num, x]
        num /= 1024.0


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


def splitArchFiles(nbDetails, key, dryRun = True, chunk = 90, verbose = True):
    """
    Basic routine to split existing archive files into chunks for upload.

    Split existing archives into size = chunk (MB) files using system zip package.
    See, e.g., https://serverfault.com/questions/760337/how-to-zip-files-with-a-size-limit/760341

    TODO: replace with better logic...?  Package files for E sets to avoid large archives? Use Tar?

    """

    arch = Path(nbDetails[key]['archName'])
    archSize = convert_bytes(os.stat(arch).st_size)

    if ('MB' in archSize[1]) and (archSize[0] > chunk):
        print(f"***File greater than {chunk}Mb: {arch}")
        print(f"Splitting into chunks...")

        # Set new file name for chunked arch
        fileOut = arch.with_name(arch.stem + '_multiPart.zip')

        # Just need to run this at command line on remote (Linux)
        # TODO: add some checking logic here, at the moment can fail if fileOut already exists.
        # Note -j for junking the path, see http://manpages.ubuntu.com/manpages/precise/man1/zip.1.html
        os.system(f"zip -j -s {chunk}m {fileOut} {arch}")

        # TO REBUILD:
        # zip -s 0 testMultipart.zip --out testRecon.zip

        # Get filelist of archive parts
        fileList = glob.glob(Path(fileOut.parent, fileOut.stem).as_posix() + '*')

        # THEN - update repoFile list with parts
#        updatedList = [item for item in nbDetails[key]['repoFiles'] if (item not in arch.as_posix())]
        updatedList = [item for item in nbDetails[key]['repoFiles'] if (item != arch.as_posix())]

        for item in fileList:
            if not (item in updatedList):
                updatedList.append(item)

        nbDetails[key]['repoFiles'] = updatedList

        if verbose or dryRun:
            print("Updated repoFiles list with multipart archive.")
            print(*updatedList, sep="\n")


def uploadRepoFiles(nbDetails, key, ACCESS_TOKEN, dryRun = True):
    """Upload files to repo (from local machine)

    See _repo.uploadRepoFiles() for local version.

    """

    url = f"https://zenodo.org/api/deposit/depositions/{nbDetails[key]['repoInfo']['id']}/files?access_token={ACCESS_TOKEN}"

    outputs = []
    for fileIn in nbDetails[key]['repoFiles']:
        data = {'name': Path(fileIn).name}
        files = {'file': open(fileIn, 'rb')}

        if not dryRun:
            r = requests.post(url, data=data, files=files)

            if r.ok:
                print(f"File upload OK: {fileIn}")
            elif r.json()['status'] == 400:
                print(f"File already on server: : {fileIn}")
            else:
                print(f"File upload failed: {fileIn}")
                # print(r.json())

            outputs.append([r.ok, r.json()])

        else:
            print("Dry run only...")
            print(f"URL: {url}")
            print(f"data: {data}")
            print(f"File: {fileIn}")
            outputs.append([url, data, files])

    # nbDetails[key]['repoFilesUpload'] = outputs
    # return nbDetails
    return outputs

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
    ACCESS_TOKEN = sys.argv[2]
    verbose = True
    dryRun = False

    print("***Uploading to repo.")

    # Get details from file
    nbDetails = readNBdetailsJSON(jsonProcFile)

    if verbose:
        pprint.pprint(nbDetails)

    # Upload files & log result.
    for key in nbDetails:
        if key!='proc' and nbDetails[key]['pkg'] and nbDetails[key]['archFilesOK']:
            splitArchFiles(nbDetails, key, dryRun = dryRun, verbose = verbose)
            nbDetails[key]['repoFilesUpload'] = uploadRepoFiles(nbDetails, key, ACCESS_TOKEN, dryRun=dryRun)
        else:
            print(f"***Skipping item {key} upload")

    # Write to new JSON file
    if not dryRun:
        print(f"\nWriting log file {jsonProcFile + '.upload'}")
        writeNBdetailsJSON(jsonProcFile + '.upload', nbDetails)

    print("***Uploads completed.")
