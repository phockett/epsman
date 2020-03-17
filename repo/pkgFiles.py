"""
epsman

Local python script for job packaging.

Can be called from Fabric for remote run case, only requires standard libs.

May be a better way to do this?

15/01/20    Change file type pattern matching from globPat to rePat - fixes bug with some files being ignored erroneously.

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


# Basic bytes to KB/Mb... conversion, from https://stackoverflow.com/questions/2104080/how-to-check-file-size-in-python
def convert_bytes(num):
    """
    This function will convert bytes to MB.... GB... etc
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
#             return "%3.1f %s" % (num, x)
            return [num, x]
        num /= 1024.0


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
        - '2016sub' Jobs defined by eV, with subdirs, as mol/*_XX-XXeV/jName
        - '2019' Jobs defined as mol/jName/
        For 2019 schema, energies are interleaved, while for 2016 schema they are treated independently with different jobs.
    """

    nbFileName = Path(nbFileName)

    if jobSchema == '2016':
        jRoot = nbFileName.stem.rsplit(sep='_', maxsplit=3)
        return f"{jRoot[1]}_{jRoot[2]}_{jRoot[3]}"
    elif (jobSchema == '2016sub') or (jobSchema == '2016sub-r'):  # 17/03/20 added l/r options, kept original for back-compatibility.
        jRoot = nbFileName.stem.rsplit(sep='_', maxsplit=3)
        # return f"{jRoot[1]}/.*{jRoot[2]}_{jRoot[3]}"
        # return f"{jRoot[1]}/{jRoot[2]}_{jRoot[3]}"
        return f"{jRoot[1]}.*{jRoot[2]}_{jRoot[3]}"
    elif jobSchema == '2016sub-l':
        jRoot = nbFileName.stem.split(sep='_', maxsplit=3)
        # return f"{jRoot[1]}/.*{jRoot[2]}_{jRoot[3]}"
        # return f"{jRoot[1]}/{jRoot[2]}_{jRoot[3]}"
        return f"{jRoot[1]}.*{jRoot[2]}_{jRoot[3]}"
    elif jobSchema == '2019':
        jRoot = nbFileName.stem.rsplit(sep='_', maxsplit=2)
        return f"{jRoot[1]}_{jRoot[2]}"
    else:
        return None # "Not supported"


#*** FOLLOWING COMMANDS TO RUN LOCALLY on host


# Build file list as local call - use OS calls.
# fileList = !shopt -s globstar; ls -d -1 '{nbProcDir.as_posix()}/'**/*[!zip]  | grep {jRoot}
# fileList = os.system(f"shopt -s globstar; ls -d -1 '{nbProcDir.as_posix()}/'**/*[!zip]  | grep {jRoot}")

# Python version

def getFilesPkg(pkgDir, globPat = r"/**/*", rePat = None, recursive=True):
    """
    Glob pkgDir with globPat, and optional re matching with rePat.

    Used for getting file lists for packaging ePS job dirs.

    Parameters
    ----------
    pkgDir : str or Path object
        Directory to search.

    globPat : str, optional, default = r"/**/*"
        Default pattern for globbing, will search dir for all files.
        Supports basic pattern matching, e.g. r"/**/*[!zip], but note glob matches chars - use re for more control.

    rePat : str, optional, default = None
        Regular expression for filtering glob output.
        E.g. rePat = ".*substring.*"  to search for 'substring' in glob output.
        rePat = ".*substring.*$(?<zip)" to exclude zip files.

    recursive : bool, optional, default = True
        Recursive glob: if True, search subdirs too (with ** pattern).

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

# THIS IS NOT REQUIRED - just call this script with single file.
# See _repo.updateArch()
#
# def addArchFile(archName, fileIn, cType = zipfile.ZIP_LZMA):
#     """Add single file to an archive"""
#     # Open archive & write files
#     with ZipFile(archName, 'w', compression=cType) as pkgZip:
#         # Write file, set also arcname to fix relative paths
#         pkgZip.write(fileIn, arcname = Path(fileIn).relative_to(pkgDir))
#
#         # Check file is OK
#         if pkgZip.testzip() is None:
#             # zipList.append(archName)
#             print(f'Written {archName} OK')
#             return True
#         else:
#             # failList.append(archName)
#             print(f'*** Archive {archName} failed')
#             return False


def buildPkg(archName, fileList, pkgDir, archMode = 'w', cType = zipfile.ZIP_LZMA):
    """Build pkg zip from fileList

    Parameters
    ----------
    archName : str or Path object
        Archive to write.

    fileList : list of strings or Path objects
        Files to include (full paths)

    pkgDir : str or Path object
        Directory to use as root in archive

    archMode : char, optional, default = 'w'
        Set to 'w'rite or 'a'ppend to existing archive.

    cType : int, default = zipfile.ZIP_LZMA (=14)
        Compression level.

    TODO:
    - Check if arch exists for 'w' case?
    - File size checks to add?
    - Summary for files & dirs, and verbosity level.

    """
    # Set variable for file additions
    dupList = []

    # Create archive & write files
    with ZipFile(archName, archMode, compression=cType) as pkgZip:
        for fileIn in fileList:
            dupPath = None

            # Test & set relative paths for file in archive - may fail in some cases if path root is different.
            try:
                arcFile = Path(fileIn).relative_to(pkgDir)
            except ValueError:
                arcFile = Path(fileIn).name  # In this case just take file name, will go in archive root

            # Add file to existing arch, check file exists first.
            if archMode == 'a':
                # Check all files in arch, names only.
                for fileName in pkgZip.namelist():
                    # if Path(fileName).name == Path(fileIn).name:  # May want to use Path(fileIn).relative_to(pkgDir) here for consistency and to allow subdirs with same files?
                    # if Path(fileIn).relative_to(pkgDir) == Path(fileName):
                    if arcFile == Path(fileName):
                        dupPath = fileName
                        dupList.append([fileIn, fileName])
                #
                # if (fileIn[1:] in pkgZip.namelist()):  # FILE MISSING initial / in .namelist(). This only works if full paths preserved/identical
                if dupPath is not None:
                    print(f'File: {fileIn} already in archive as {fileName}.')
                else:
                    pkgZip.write(fileIn, arcname = arcFile)

            else:
                # Write file, set also arcname to fix relative paths
                pkgZip.write(fileIn, arcname = arcFile)

        # Check file is OK
        if (pkgZip.testzip() is None) and (not dupList):
            # zipList.append(archName)
            print(f'Written {archName} OK')
            fSize = convert_bytes(Path(archName).stat().st_size)
            print(f"{round(fSize[0],2)} {fSize[1]}")
            if (fSize[1] == 'GB') or (fSize[1] == 'TB'):
                print("***LARGE FILE")
            return True
        elif dupList:
            print(f'Skipped duplicate files (new, in arch):')
            print(*dupList, sep='\n')
            return False
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
# If jRoot is a file, then add this to archive, otherwise search for files based on jRoot.
# For jRoot case jobSchema is not used, but currently setting method by len(sys.argv), so required.
# TODO: better logic here!
# TODO: consolidate rePat for standard file inclusion
# TODO: white list for pkg file inclusion?  rePat is getting silly now.
# NOTE: for no jRoot case, rePat = f".*{jobSchema def}.*$(?<!zip)(?<!ipynb)"
#        Otherwise rePat = f".*{jRoot}.*" for basic substring match.
if __name__ == "__main__":

    # Passed args - this is root dir containing notebooks + ePS output subdirs.
    pkgDir = Path(sys.argv[1])
    jobSchema = sys.argv[4]
    # print(len(sys.argv))
    # print((sys.argv))

    # Set for dryRun - this will only display pkgs to be built.
    if sys.argv[2] == 'True':
        dryRun = True
        print("\n***Archive dry run")
    else:
        dryRun = False
        # Print header lines for job, will be in log file.
        print("\n***Writing archives")
        print(f"nbProcDir: {pkgDir}")
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + '\n')

    # print(sys.argv)
    # print(len(sys.argv))

    # Set default to write/overwrite archive
    archMode = 'w'

    # If args are passed, build archive for single job
    if len(sys.argv) > 5:
        jRoot = sys.argv[5]
        archName = Path(sys.argv[3])

        if Path(jRoot).is_file():
            # If a single file is passed, set for this file only.
            fileList = [jRoot]
            rePat = None
            archMode = 'a'  # Set to append to existing archive
            print(f'Appending file: {jRoot}')
        elif Path(jRoot).is_dir():
            print(f'Skipping dir: {jRoot}')
        else:
            # If a pattern is passed, create file list for pkg
            # NOTE: currently set to ignore zip and ipynb files for later inclusion via single-file calls.
            # Also skips files of type .zNN, which are multipart zip files.
            rePat = f".*{jRoot}.*$(?<!zip)(?<!z[0-9][0-9])(?<!ipynb)(?<!sh)(?<!sh~)"
            fileList = getFilesPkg(pkgDir, rePat = rePat)
            # fileList

        # Write zip
        if not dryRun:
            buildPkg(archName, fileList, pkgDir, archMode = archMode)
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
        nbFileList = getFilesPkg(pkgDir, globPat = r"/**/*", rePat = rePat)

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
            # rePat = f".*{jRoot}.*"
            # rePat = f".*{jRoot}.*$(?<!zip)(?<!ipynb)"  # Use this for file end exclusion, rather than glob, from https://stackoverflow.com/a/10055688
            # Also skips files of type .zNN, which are multipart zip files.
            rePat = f".*{jRoot}.*$(?<!zip)(?<!z[0-9][0-9])(?<!ipynb)(?<!sh)(?<!sh~)"
            fileList = getFilesPkg(pkgDir, rePat = rePat)

            # Write zip
            if not dryRun:
                test = buildPkg(archName, fileList, pkgDir, archMode = archMode)

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
