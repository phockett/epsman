"""
ePSman utility functions
--------------------------------

Utility functions for use with ePSman.

27/12/19    v1

"""
import re
from pathlib import Path

import logging

#****** FILE PARSING

# Parse digits from a line using re
# https://stackoverflow.com/questions/4289331/how-to-extract-numbers-from-a-string-in-python
def parseLineDigits(testLine):
    """
    Use regular expressions to extract digits from a string.
    https://stackoverflow.com/questions/4289331/how-to-extract-numbers-from-a-string-in-python

    """
    return re.findall("[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", testLine)

def parseLineTokens(testLine):
    """
    Use regular expressions to extract alpha-numeric tokens from a sting.

    """
    return re.findall("[A-Za-z0-9]+", testLine)

# FILEPARSE from epsproc
# Should just import... but included directly here for now!

# File parsing function - scan file for keywords & read segments
#   Following above idiomatic solution, with full IO
#   https://stackoverflow.com/questions/3961265/get-line-number-of-certain-phrase-in-file-python
def fileParse(fileName, startPhrase = None, endPhrase = None, comment = None, verbose = 0):
    """
    Parse a file, return segment(s) from startPhrase:endPhase, excluding comments.

    Parameters
    ----------
    fileName : str
        File to read (file in working dir, or full path)
    startPhrase : str, optional
        Phrase denoting start of section to read. Default = None
    endPhase : str, optional
        Phrase denoting end of section to read. Default = None
    comment : str, optional
        Phrase denoting comment lines, which are skipped. Default = None

    Returns
    -------
    list
        [lineStart, lineStop], ints for line #s found from start and end phrases.
    list
        segments, list of lines read from file.

    All lists can contain multiple entries, if more than one segment matches the search criteria.

    """

    lineStart = []    # Create empty list to hold line #s
    lineStop = []     # Create empty list to hold line #s
    segments = [[]]   # Possible to create empty multi-dim array here without knowing # of segments? Otherwise might be easier to use np textscan functions
    readFlag = False
    n = 0

    # Force list to ensure endPhase is used correctly for single phase case (otherwise will test chars)
    if type(endPhrase) is str:
        endPhrase = [endPhrase]

    # Open file & scan each line.
    with open(fileName,'r') as f:
        for (i, line) in enumerate(f):  # Note enumerate() here gives lines with numbers, e.g. fullFile=enumerate(f) will read in file with numbers
            i = i + 1  # Offset for file line numbers (1 indexed)
            # If line matches startPhrase, print line & append to list.
            # Note use of lstrip to skip any leading whitespace.
            # if startPhrase in line:
            if line.lstrip().startswith(startPhrase):
                if verbose>2:
                    print('Found "', startPhrase, '" at line: ', i)

                lineStart.append(i)

                readFlag = True

            # Read lines into segment[] until endPhrase found
            if readFlag:
                # Check for end of segment (start of next Command sequence)
                if endPhrase and ([line.lstrip().startswith(endP) for endP in endPhrase].count(True) > 0):  # This allows for multiple endPhases
                                                                                                    # NOTE: this will iterate over all chars in a phrase if a single str is passed.
                    # Log stop line and list
                    lineStop.append(i)
                    readFlag = False

                    # Log segment and create next
                    segments.append([])
                    n += 1

                    continue            # Continue will skip rest of loop

                 # Check for comments, skip line but keep reading
                elif comment and line.lstrip().startswith(comment):
                    continue            # Continue will skip rest of loop

                segments[n].append([n, i, line])    # Store line if part  of defined segment

    if verbose:
        print('Found {0} segments.'.format(n))

    return ([lineStart, lineStop], segments) # [:-1])


#****** FILE CHECKS

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
            fileTest = Path(scanDir, fileTest)

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


#****** FILE PUSH & PULL

# pushFileDict - wrap pushFile for self.hostDefn[host] case.
def pushFileDict(self, fileKey, **kwargs):
    """
    Wraps self.pushFile([localhost][fileKey], [host][fileKey], **kwargs)
    """
    return self.pushFile(self.hostDefn['localhost'][fileKey], self.hostDefn[self.host][fileKey], **kwargs)


# Routine to check and push file to remote
# Follows basic method from genFile handling in createJobDirTree()
def pushFile(self, fileLocal, fileRemote, overwritePrompt = True, mkdir = 'prompt'):
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

    mkdir : bool or str, default = 'prompt'
        If set to True, create remote dir (and parents) if missing.
        If set to 'prompt', prompt user for remote dir creation.
        If set to False, don't create remote dir.

    Returns
    -------
    bool, True if sucessful.

    Fabric object with details if failed.

    TODO: fix fileRemote.is_file() part - this currently appends filename regardless, but OK if dir only passed.
    TODO: add mkdir stage? Or option for this at least.

    """

    # Check local file exists
    if not fileLocal.is_file():
        print(f"\n*** Can't push {fileLocal} to remote, local file does not exist.")
        return False


    # Check fileRemote & set filename if not supplied
    # NOTE: this may not behave as expected, since .is_file() will usually fail for remote file not on local filesystem.
    # if not fileRemote.is_file():
    #     fileRemote = fileRemote.joinpath(fileLocal.name)

    # Use Fabric for proper remote files checks...
    # test = self.c.run('[ -f "' + fileRemote.as_posix() + '" ]', warn = True)
    #
    # if not test.ok:

    # (1) check if passed fileRemote is a directory
    testDir = self.c.run('[ -d "' + fileRemote.as_posix() + '" ]', warn = True)

    # (2) if it is a directory, append the filename
    if testDir.ok:
        fileRemote = fileRemote.joinpath(fileLocal.name)

    # (3) if not a directory, assume it's a filename and check parent dir is OK
    else:
        testDirP = self.c.run('[ -d "' + fileRemote.parent.as_posix() + '" ]', warn = True)

        # If dir missing just exit
        # TODO: dir creation. 14/02/22 in place, needs testing.
        if not testDirP.ok:
            dirFlag = 'n'

            if mkdir:
                dirFlag = 'y'
                if mkdir is 'prompt':
                    dirFlag = input(f"Remote dir {fileRemote.parent} doesn't exist, create? (y/n) ")

                if dirFlag == 'y':
                    self.c.run('mkdir -p ' + fileRemote.parent.as_posix())

            if dirFlag == 'n':
                print(f"\n*** Remote directory {fileRemote.parent} does not exist, can't push file {fileLocal} to remote.")
                return False


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


    fCheckHost = {}

    # 26/02/21 Lazy wrap in try/except to catch errors in self.host, e.g. if not set or set to None
    # Probably could do better.
    try:
        if self.verbose:
            print(f'\n*** Syncing files {self.hostDefn[self.host][fileKey]}')

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

    except KeyError:
        print(f"\n*** Can't sync files, self.host or self.hostDefn[host][{fileKey}] not set.")
        result = None

    return [fCheckHost, result]


#****** ATTRIBUTE METHODS

def setAttributesFromDict(self, itemsDict, overwriteFlag = False):

    [self.setAttribute(k, v, overwriteFlag = overwriteFlag) for k,v in itemsDict.items() if (k is not 'self') and (k is not 'overwriteFlag')]



def setAttribute(self, attrib, newVal = None, overwriteFlag = False, printFlag = True):
    """
    Basic check & set attribute routine.

    Set self.attrib = newVal if:
        - attrib doesn't exist,
        - attrib exists
            - but is None,
            - if overwriteFlag = True is passed.

    printFlag: if True, print values, otherwise just confirm value set. (Only if self.verbose and setFlag.)

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
        if printFlag:
            print(f'Set {attrib} = {newVal}')
        else:
            if newVal is None:
                print(f'Set {attrib} = {newVal}')   # Keep this for None case?
            else:
                print(f'Set {attrib} from passed values.')


#****** ENV

def isnotebook():
    """
    Check if code is running in Jupyter Notebook.

    Taken verbatim from https://exceptionshub.com/how-can-i-check-if-code-is-executed-in-the-ipython-notebook.html
    Might be a better/more robust way to do this?

    This can be deployed for display use for plotters, e.g.
        try:
            if self.__notebook__:
                display(hv.Curve(d0))  # If notebook, use display to push plot.
            else:
                # return hv.Curve(d0)  # Otherwise return hv object.
                pass
        except:
            pass

    """

    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter


#****** LOGGING

# Test grabbing log output...
# https://stackoverflow.com/questions/59345532/error-log-count-and-error-log-messages-as-list-from-logger
# This is used in ESgamess class to grab logger messages from pyGamess for Error checking - there's likely a slicker way however.
class CustomStreamHandler(logging.StreamHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_logs = []

    def emit(self, record):
        if record.levelno == logging.ERROR:
            self.error_logs.append(record)
        super().emit(record)