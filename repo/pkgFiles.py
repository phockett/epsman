"""
epsman

Local python script for job packaging.

Can be called from Fabric for remote run case, only requires standard libs.

May be a better way to do this?

01/01/20    v1

"""

from zipfile import ZipFile
import zipfile
import os
import sys
from pathlib import Path
import glob
import re
import datetime


# Define job root schema for file sorting
# Set here to allow for local function access & keep single set of definitions
def setJobRoot(nbFileName, jobSchema):
    """
    Define job dir schema from processed notebook filename.

    Parameters
    ----------
    nbFileName : str or Path
        Notebook file defining job.

    jobSchema : str
        - '2016' Jobs defined as mol/jName_XX-XXeV/
        - '2019' Jobs defined as mol/jName/
        For 2019 schema, energies are interleaved, while for 2016 schema they are treated independently with different jobs.
    """

    nbFileName = Path(nbFileName)

    if jobSchema == '2016':
        jRoot = nbFileName.stem.rsplit(sep='_', maxsplit=3)
        return f"{jRoot[1]}_{jRoot[2]}_{jRoot[3]}"
    elif jobSchema == '2019':
        jRoot = nbFileName.stem.rsplit(sep='_', maxsplit=2)
        return f"{jRoot[1]}_{jRoot[2]}"
    else:
        return "Not supported"


#*** FOLLOWING COMMANDS TO RUN LOCALLY on host


# Build file list as local call - use OS calls.
# fileList = !shopt -s globstar; ls -d -1 '{nbProcDir.as_posix()}/'**/*[!zip]  | grep {jRoot}
# fileList = os.system(f"shopt -s globstar; ls -d -1 '{nbProcDir.as_posix()}/'**/*[!zip]  | grep {jRoot}")

# Python version

def getFilesPkg(pkgDir, globPat = r"/**/*[!zip]", rePat = None, recursive=True):
    """Glob pkgDir with globPat, and optional re matching with rePat.

       Used for getting file lists for packaging ePS job dirs.
    """
    # Get file list using recursive glob and supplied pattern
    fileList = glob.glob(f"{pkgDir}{globPat}", recursive=recursive)

    # If supplied, process with re
    if rePat is not None:
        fileListRe = []
        for item in fileList:
            if re.search(rePat, item):
                fileListRe.append(item)

    else:
        fileListRe = fileList

    return fileListRe


def buildPkg(archName, fileList, pkgDir, cType = zipfile.ZIP_LZMA):
    """Build pkg zip from fileList

    Parameters
    ----------
    archName : str or Path object
        Archive to write.

    fileList : list of strings or Path objects
        Files to include (full paths)

    pkgDir : str or Path object
        Directory to use as root in archive

    cType : int, default = zipfile.ZIP_LZMA (=14)
        Compression level.

    """

    # Create archive & write files
    with ZipFile(archName, 'w', compression=cType) as pkgZip:
        for fileIn in fileList:
            # Write file, set also arcname to fix relative paths
            pkgZip.write(fileIn, arcname = Path(fileIn).relative_to(pkgDir))

        # Check file is OK
        if pkgZip.testzip() is None:
            # zipList.append(archName)
            print(f'Written {archName} OK')
            return True
        else:
            # failList.append(archName)
            print(f'*** Archive {archName} failed')
            return False

# Additional code for checking archives.
def checkArch(archName):
    """Test archive & return info if OK"""

    infoList = None
    nameList = None

    with ZipFile(archName, 'r') as checkZip:
        if checkZip.testzip() is None:
            infoList = checkZip.infolist()  # Get info & file list
            nameList = checkZip.namelist()

    return infoList, nameList


# Code for CLI call from Fabric
# Args: pkgDir, dryRun, archName, jobSchema, jRoot
# If jRoot is not passed, pkg a directory, otherwise pkg single job as defined.
# For jRoot case jobSchema is not used, but currently setting method by len(sys.argv), so required.
# TODO: better logic here!
if __name__ == "__main__":

    # Passed args - this is root dir containing notebooks + ePS output subdirs.
    pkgDir = Path(sys.argv[1])
    jobSchema = sys.argv[4]
    # print(jobSchema)

    # Set for dryRun - this will only display pkgs to be built.
    if sys.argv[2] == 'True':
        dryRun = True
    else:
        dryRun = False
        # Print header lines for job, will be in log file.
        print("***Writing archives")
        print(f"nbProcDir: {pkgDir}")
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + '\n')

    # print(sys.argv)
    # print(len(sys.argv))


    # If args are passed, build archive for single job
    if len(sys.argv) > 5:
        jRoot = sys.argv[5]
        archName = Path(sys.argv[3])

        # Create file list for pkg
        rePat = f".*{jRoot}.*"
        fileList = getFilesPkg(pkgDir, rePat = rePat)
        # fileList

        # Write zip
        if not dryRun:
            buildPkg(archName, fileList, pkgDir)
        else:
            print('\n***Pkg dry run')
            # print(f"Job: {item}")
            print(f"Arch: {archName}")
            print(f"jRoot: {jRoot}")
            print(f"rePat: {rePat}")
            print(*fileList, sep='\n')

    # Otherwise package full dir based on notebooks in root.
    else:
        archDir = Path(sys.argv[3])

        # Create notebook file list for pkg
        rePat = ".ipynb$"
        nbFileList = getFilesPkg(pkgDir, rePat = rePat)

        if dryRun:
            print("\n***Notebook file list:")
            print(*nbFileList, sep='\n')

        zipList = []
        failList = []
        for item in nbFileList:  # Local file list

            # Job keys
            item = Path(item)
            # jRoot = item.stem.rsplit(sep='_', maxsplit=2)
            jRoot = setJobRoot(item, jobSchema)
            archName = Path(archDir, item.stem + '.zip')

            # Create file list for pkg
            rePat = f".*{jRoot}.*"
            fileList = getFilesPkg(pkgDir, rePat = rePat)

            # Write zip
            if not dryRun:
                test = buildPkg(archName, fileList, pkgDir)

                if test:
                    zipList.append(archName)
                else:
                    failList.append(archName)

            else:
                print('\n***Pkg dry run')
                print(f"Job: {item}")
                print(f"Arch: {archName}")
                print(f"jRoot: {jRoot}")
                print(f"rePat: {rePat}")
                print(*fileList, sep='\n')



        if not dryRun:
            print(f'\nArchives completed at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
            # TODO: Additional print/pass/write results here?
            # Currently included print() statements from buildPkg()
