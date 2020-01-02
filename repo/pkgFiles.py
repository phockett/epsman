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



if __name__ == "__main__":

    dryRun = True

    # Passed args - this is root dir containing notebooks + ePS output subdirs.
    pkgDir = Path(sys.argv[1])
    # print(sys.argv)
    # print(len(sys.argv))


    # If args are passed, build archive for single job
    if len(sys.argv) > 3:
        jRoot = sys.argv[2]
        archName = Path(sys.argv[3])

        # Create file list for pkg
        rePat = f".*{jRoot}.*"
        fileList = getFilesPkg(pkgDir, rePat = rePat)
        # fileList

        # Write zip
        buildPkg(archName, fileList, pkgDir)

    # Otherwise package full dir based on notebooks in root.
    else:
        archDir = Path(sys.argv[2])

        # Create notebook file list for pkg
        rePat = ".ipynb$"
        nbFileList = getFilesPkg(pkgDir, rePat = rePat)
        print(nbFileList)

        zipList = []
        failList = []
        for item in nbFileList:  # Local file list

            # Job keys
            item = Path(item)
            jRoot = item.stem.rsplit(sep='_', maxsplit=2)
            archName = Path(archDir, item.stem + '.zip')

            # Create file list for pkg
            rePat = f".*{jRoot[1]}_{jRoot[2]}.*"
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

            # TODO: print/pass/write results here?
