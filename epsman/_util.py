"""
ePSman utility functions
--------------------------------

Utility functions for use with ePSman.

27/12/19    v1

"""
import re
from pathlib import Path

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
        Result = self.c.run(f"ls {scanDir}/*.{fileType}", warn = True, hide = True)

    fileList = Result.stdout.split()

    if verbose:
        print(f'\n***File List (from {self.host}):')
        print(*fileList, sep='\n')

    return fileList


def checkLocalFiles(self, fileList, scanDir = None, verbose = False):
    """
    Check files on local machine. Use checkFiles() to check files on remote host.

    Very basic!

    Parameters
    ----------
    fileList : list of strs or Path objects
        Files to check on local machine.
        Names only, or full paths. Can optionally set directory with scanDir variable.

    scanDir : str or Path, optional, default = None
        Directory to scan, if not passed this is not set (so current working directory will be used unless full file paths are passed).

    verbose : bool, optional, default = False
        Print results to screen.

    Returns
    -------
    checkList : list
        List of Fabric results, bool.

    Note
    -----
    This uses path().exists(), so will only work for local machine.

    """
    # Set to list to avoid looping over chars for single file case.
    if type(fileList) is not list:
        fileList = [fileList]

    checkList = []

    for fileTest in fileList:

        if not hasattr(fileTest, 'exists'):
            fileTest = Path(fileTest)

        # Assume that scanDir should be used if not None, and that fileTest is a subdir or file (not full path).
        if scanDir is not None:
            Path(scanDir, fileTest)

        result = fileTest.exists()  # Test for destination file, will return True if exists
        checkList.append(result)

        if verbose:
            print(f"{fileTest}: {result}")

    return checkList



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

    Note
    -----
    This uses self.c.run(), as set at self.initConnection(), so will only work for self.host.

    """

    # Set to list to avoid looping over chars for single file case.
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

# pushFileDict - wrap pushFile for self.hostDefn[host] case.
def pushFileDict(self, fileKey, **kwargs):
    """
    Wraps self.pushFile([localhost][fileKey], [host][fileKey], **kwargs)
    """
    return self.pushFile(self.hostDefn['localhost'][fileKey], self.hostDefn[self.host][fileKey], **kwargs)


# Routine to check and push file to remote
# Follows basic method from genFile handling in createJobDirTree()
def pushFile(self, fileLocal, fileRemote, overwritePrompt = True):
    """
    Routine to check and push file to remote

    Follows basic method from genFile handling in createJobDirTree()
    (1) Test if file already exists on remote, prompt for overwrite if so (unless overwritePrompt is set to False or None).
    (2) Push file.
    (3) Check file on remote to verify.


    Parameters
    ----------
    fileLocal : Path object
        Local file to push. Full path, or file in working dir.

    fileRemote : Path object
        Remote location. Full path, with or without filename. (If missing, filename will be unchanged.)

    overwritePrompt : bool, default = True
        If set to True, prompt user for file overwrite.
        If set to False, overwrite existing files.
        If set to None, do not overwrite.

    Returns
    -------
    bool, True if sucessful.

    Fabric object with details if failed.

    """

    # Check fileRemote & set filename if not supplied
    # NOTE: this may not behave as expected, since .is_file() will usually fail for remote file not on local filesystem.
    if not fileRemote.is_file():
        fileRemote = fileRemote.joinpath(fileLocal.name)

    print(f"\n*** Pushing file: {fileLocal} to remote: {fileRemote}")

    # Test if exists on remote
    test = self.c.run('[ -f "' + fileRemote.as_posix() + '" ]', warn = True)
    if test.ok and overwritePrompt:
        wFlag = input(f"File {fileRemote} already exists, overwrite? (y/n) ")
    elif test.ok and (overwritePrompt is None):
        print(f"File {fileRemote} already exists, skipping push.")
        wFlag = 'n'
    elif test.ok and (not overwritePrompt):
        print(f"File {fileRemote} already exists, overwritting.")
        wFlag = 'y'
    else:
        wFlag = 'y'

    # Upload and test result.
    if wFlag == 'y':
        Result = self.c.put(fileLocal.as_posix(), remote = fileRemote.as_posix())
        test = self.c.run('[ -f "' + fileRemote.as_posix() + '" ]', warn = True)
        if test.ok:
            print("Uploaded \n{0.local}\n to \n{0.remote}".format(Result))
        else:
            print('Failed to push file to host.')
            return Result

    return True


# pushFileDict - wrap pushFile for self.hostDefn[host] case.
def pullFileDict(self, fileKey, **kwargs):
    """
    Wraps self.pullFile([localhost][fileKey], [host][fileKey], **kwargs)
    """
    return self.pullFile(self.hostDefn['localhost'][fileKey], self.hostDefn[self.host][fileKey], **kwargs)


# 22/02/21 - hacky pullFile, just modified from pushFile() above, but should consolidate methods here - lots of boilerplate!
def pullFile(self, fileLocal, fileRemote, overwritePrompt = True):
    """
    Routine to check and pull file from remote

    22/02/21 - implemented hacky pullFile(), just modified from pushFile() above, but should consolidate methods here - lots of boilerplate!

    Existing notes:

    Follows basic method from genFile handling in createJobDirTree()
    (1) Test if file already exists on remote, prompt for overwrite if so (unless overwritePrompt is set to False or None).
    (2) Push file.
    (3) Check file on remote to verify.


    Parameters
    ----------
    fileLocal : Path object
        Local file to push. Full path, or file in working dir.

    fileRemote : Path object
        Remote location. Full path, with or without filename. (If missing, filename will be unchanged.)

    overwritePrompt : bool, default = True
        If set to True, prompt user for file overwrite.
        If set to False, overwrite existing files.
        If set to None, do not overwrite.

    Returns
    -------
    bool, True if sucessful.

    Fabric object with details if failed.

    """

    # Check fileRemote & set filename if not supplied
    # NOTE: this may not behave as expected, since .is_file() will usually fail for remote file not on local filesystem.
    if not fileRemote.is_file():
        fileRemote = fileRemote.joinpath(fileLocal.name)

    print(f"\n*** Pulling file: {fileRemote} to local: {fileLocal}")

    # Test if exists on local machine
    # test = self.c.run('[ -f "' + fileRemote.as_posix() + '" ]', warn = True)
    test = self.checkLocalFiles(fileLocal)

    if test and overwritePrompt:
        wFlag = input(f"File {fileLocal} already exists, overwrite? (y/n) ")
    elif test and (overwritePrompt is None):
        print(f"File {fileLocal} already exists, skipping pull.")
        wFlag = 'n'
    elif test and (not overwritePrompt):
        print(f"File {fileLocal} already exists, overwritting.")
        wFlag = 'y'
    else:
        wFlag = 'y'

    # Upload and test result.
    if wFlag == 'y':
        Result = self.c.get(fileRemote.as_posix(), local = fileLocal.as_posix())
        # test = self.c.run('[ -f "' + fileRemote.as_posix() + '" ]', warn = True)
        test = self.checkLocalFiles(fileLocal)
        if test:
            print("Pulled \n{0.remote}\n to \n{0.local}".format(Result))
        else:
            print('Failed to pull file from host.')
            return Result

    return True


def setAttributesFromDict(self, itemsDict, overwriteFlag = False):

    [self.setAttribute(k, v, overwriteFlag = overwriteFlag) for k,v in itemsDict.items() if (k is not 'self') and (k is not 'overwriteFlag')]



def setAttribute(self, attrib, newVal = None, overwriteFlag = False):
    """
    Basic check & set attribute routine.

    Set self.attrib = newVal if:
        - attrib doesn't exist,
        - attrib exists
            - but is None,
            - if overwriteFlag = True is passed.

    TODO: consider attrs library here, https://www.attrs.org/en/stable/examples.html#validators
    """

    setFlag = False

    # Check if attrib exists, overwrite ONLY if None, or if overwriteFlag is set
    if hasattr(self, attrib):
        param = getattr(self, attrib)

        if (param is None) or overwriteFlag:
            setattr(self,attrib,newVal)

            if newVal is not None:
                setFlag = True  # Only set this if newVal != None to avoid lots of None echos for unset values.

    # Set attrib if missing
    else:
        setattr(self,attrib,newVal)
        setFlag = True

    if self.verbose and setFlag:
        print(f'Set {attrib} = {newVal}')


def syncFilesDict(self, fileKey, pushPrompt = True, **kwargs):
    """
    Synchronise file between local and host, including push/pull missing files.

    Sync for self.hostDefn[host][fileKey], between localhost and remote host (self.host).

    TODO:

    - Set for file lists?
    - adapt for multiple hosts? Probably easier to find existing/library code for this case however.
    - Check file paths exist. Currently just flags an error.
    - Methods for updating files, currently only handles missing files.

    """

    hostList = [self.host, 'localhost']  # Hardcoded for now, since only two hosts supported, and needs self.c to be set for host.

    if self.verbose:
        print(f'\n*** Syncing files {fileKey}')

    fCheckHost = {}
    for host in hostList:
        if fileKey in self.hostDefn[host].keys():

            if host == 'localhost':
                fCheckHost[host] = self.checkLocalFiles(self.hostDefn[host][fileKey])[0]  # use local Path file test.
            else:
                fCheckHost[host] = self.checkFiles(self.hostDefn[host][fileKey])[0]   # Use remote Fabric file test.

        else:
            fCheckHost[host] = None  # Set to None for unset cases - may want to flag a warning here?

        if self.verbose:
            print(f"\n\t{host}:  \t{self.hostDefn[host][fileKey]} \t{fCheckHost[host]}")


    # If file missing on host, push it
    result = None
    pushFlag = 'n'
    if (not fCheckHost[self.host]) and (fCheckHost['localhost']):
        if pushPrompt:
            pushFlag = input(f'\nPush missing file to host: {self.host}?  (y/n) ')
        else:
            pushFlag = 'y'

    if pushFlag == 'y':
        try:
            result = self.pushFileDict(fileKey, **kwargs)
        except FileNotFoundError:
            print(f'\n***WARNING: File not found error when pushing to host: {self.host}. Is the full path set? Run self.creatJobDirTree() if not.')


    # If file missing on localhost, pull it
    pullFlag = 'n'
    if (not fCheckHost['localhost']) and (fCheckHost[self.host]):
        if pushPrompt:
            pullFlag = input(f'\nPull missing file from host: {self.host}?  (y/n) ')
        else:
            pullFlag = 'y'

    if pullFlag == 'y':
        try:
            result = self.pullFileDict(fileKey, **kwargs)
        except FileNotFoundError:
            print(f'\n***WARNING: File not found error when pulling to local machine. Is the full path set? Run self.creatJobDirTree(localHost=True) if not.')

    if self.verbose:
        if result is not None:
            if result is True:
                print(f'\nSynced files {fileKey} OK.')
            else:
                print(f'\nFailed to sync {fileKey}.')
        else:
            print(f'\nNothing to sync for {fileKey}.')

    return [fCheckHost, result]
