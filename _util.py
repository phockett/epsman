"""
ePSman utility functions
--------------------------------

Utility functions for use with ePSman.

27/12/19    v1

"""
import re

# Parse digits from a line using re
# https://stackoverflow.com/questions/4289331/how-to-extract-numbers-from-a-string-in-python
def parseLineDigits(testLine):
    """
    Use regular expressions to extract digits from a string.
    https://stackoverflow.com/questions/4289331/how-to-extract-numbers-from-a-string-in-python

    """
    return re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", testLine)



def getFileList(self, scanDir, fileType = 'out', subDirs = True, verbose = True):
    """Get a file list from host - scan directory=dir for files of fileType.

    Parameters
    ----------
    scanDir : string
        Directory to scan.

    fileType : string, default = 'out'
        File ending to match.

    subDirs : bool, optional, default = True
        Include subDirs in processing.

    verbose : bool, optional, default = True
        Print jobList to screen.

    """
    # Check passed dir OK, convert to string if Path object.
    if type(scanDir) is not str:
        if hasattr(scanDir, 'as_posix'):
            scanDir = scanDir.as_posix()
        else:
            print('***Dir object type note recognised, must be string of Path object.')
            scanDir = None


    # Use remote shell commands to get dir lists
    if subDirs:
        # From https://stackoverflow.com/questions/3528460/how-to-list-specific-type-of-files-in-recursive-directories-in-shell
        # Will be recursive if globstar active - now included in command.
        # Globstar: shopt -s globstar
        Result = self.c.run(f"shopt -s globstar; ls -d -1 '{scanDir}/'**/* | grep \.{fileType}$", warn = True, hide = True)
    else:
        Result = self.c.run('ls ' + self.hostDefn[self.host]['nbProcDir'].as_posix() + '*.{fileType}', warn = True, hide = True)

    fileList = Result.stdout.split()

    if verbose:
        print(f'\n***File List (from {self.host}):')
        print(*fileList, sep='\n')

    return fileList


def checkFiles(self, fileList, scanDir = '', verbose = False):
    """Check files exist on host.

    Parameters
    ----------
    fileList : list of strs or Path objects
        Files to check on host.
        Names only, or full paths. Can optionally set directory with scanDir variable.

    scanDir : str or Path, optional, default = ''
        Directory to scan, defaults to Fabric default (home dir).

    verbose : bool, optional, default = False
        Print results to screen.

    Returns
    -------
    checkList : list
        List of Fabric results, bool.

    """

    if type(fileList) is not list:
        fileList = [fileList]

    checkList = []

    for fileTest in fileList:

        if hasattr(fileTest, 'as_posix'):
            fileTest = fileTest.as_posix()

        # Use cd here... although just as robust to set full path...?
        with self.c.cd(scanDir):
            result = self.c.run('[ -f "' + fileTest + '" ]', warn = True, hide = True)  # Test for destination file, will return True if exists
            checkList.append(result.ok)

            if verbose:
                print(f"{fileTest}: {result.ok}")

    return checkList
