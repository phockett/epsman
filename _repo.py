"""
ePSman repo interfacing
-----------------------

Code for:
- Scanning ePS results directories
- Scanning ePSproc notebooks
- Catalogue & sort
- Package and upload to repo

Aim to do this as a stand-alone task, so grab info from files rather than existing epsman job.

To do:
- Output details to database
- HTML page generation from packaged notebooks

10/12/19    Init... plan to test for OSF, Figshare and Zenodo.

For dev codes see notebooks:
- http://localhost:8888/notebooks/python/epsman/tests/Notebook_mod_testing_161219.ipynb
- http://localhost:8888/notebooks/python/epsman/tests/Repo_pkg_tests_181219.ipynb
- http://localhost:8888/notebooks/python/epsman/repo/Zenodo_API_tests_Dec2019.ipynb

"""
# Imports
import json
import datetime
import os
from pathlib import Path
import requests
import pprint  # For dict printing
from collections import Counter

# Local
from ._util import parseLineDigits
from .repo.nbHeaderPost import constructHeader
from .repo.pkgFiles import setJobRoot

# Import from /repo
# from repo.pkgFiles import

#*** Functions to package job for repo

def initZenodo(fileIn):
    """Get Zenodo settings from local file."""
    # Zenodo settings
    with open(fileIn) as f:
        ACCESS_TOKEN = f.read().strip()

    return ACCESS_TOKEN


# Zenodo API interface
def initRepo(self, key, manualVerify = True, dryRun = True, verbose = True):
    """
    Basic API calls for repo uploading

    Will implement repo record creation from item in nbDetails.

    CURRENTLY SET FOR ZENODO
    https://developers.zenodo.org/?python
    http://localhost:8888/notebooks/python/epsman/repo/Zenodo_API_tests_Dec2019.ipynb

    TODO

    """
    #*** Add metadata
    # For schema: https://developers.zenodo.org/#representation
    # MAY WANT TO SET TEMPLATE for this elsewhere...?
    # Some overlap with nbHeaderPost()
    # May want to pull from self.nbDetails[key]['jobText']

    # keyURL = 'test'
    # zenodoURL = f"https://zenodo.org/record/{doi.split('.')[-1]}"
    fileIn = Path(self.nbDetails[key]['file'])
    webURL = f"https://phockett.github.io/ePSdata/{fileIn.parts[-2]}/{fileIn.stem}.html"
    self.nbDetails[key]['webURL'] = webURL

    stringHTML = f"{self.nbDetails[key]['title']} - photoionization calculations with ePolyScat + ePSproc." + \
                 f"\n*Web version*: <a href={webURL}>{webURL}</a>" + \
                 "\nFor more details of the calculations, see: " + \
                 "<ul><li><a href=https://phockett.github.io/ePSdata/about.html>About the data</a>" + \
                 "<li><a href=http://epsproc.readthedocs.io>About the analysis</a></ul>"


    data = {
             'metadata': {
                 'title': f"ePSproc: {self.nbDetails[key]['title']}",
                 'upload_type': 'dataset',
                 'description': stringHTML,
                 'creators': [{'name': 'Hockett, Paul',
                               'affiliation': 'National Research Council of Canada',
                               'orcid': '0000-0001-9561-8433'}],
                 'access_right': 'open',
                 'license': 'CC-BY-4.0',
                 'prereserve_doi': True,  # May not be required?
                 'keywords':['Data','Photoionization','Scattering calculation']
    # ADDITIONAL fields that might be worthwhile.
    #              'related_identifiers'
    #              'references'
    #              'subjects'
    #              'version'
    #              'method'  # Supports HTML

                 }
             }

    # Info & verify - belt and braces approach at the moment.
    print(f"\n***Init repo for job: {self.nbDetails[key]['title']}, with {self.nbDetails[key]['repo']}")

    if manualVerify and self.nbDetails[key]['pkg'] and not dryRun:
        uploadFlag = input(f"Confirm repo init? (y/n) ")

        if uploadFlag == 'y':
            self.nbDetails[key]['repoVerify'] = True
        else:
            self.nbDetails[key]['repoVerify'] = False

    elif not manualVerify and self.nbDetails[key]['pkg'] and not dryRun:
        self.nbDetails[key]['repoVerify'] = True

    else:
        self.nbDetails[key]['repoVerify'] = False


    #*** Confirm job is set for packaging & upload, and init repo.
    # As it stands, this will create a deposition, and get info from Zenodo (doi etc.)
    # TODO: SET additional upload flag/checks here?
    if self.nbDetails[key]['repoVerify'] and self.nbDetails[key]['pkg'] and not dryRun:

        # Set new upload with metadata
        ACCESS_TOKEN = initZenodo(self.hostDefn['localhost']['localSettings']/'zenodoSettings.dat')
        record = None

        # Check record doesn't exist already
        r = requests.get('https://zenodo.org/api/deposit/depositions',
                        params={'q': self.nbDetails[key]['title'], 'access_token': ACCESS_TOKEN})

        record = None
        # if r.json():
        #     print(f"{self.nbDetails[key]['title']} repo already exists, repo details recovered.")
        #     if len(r.json()) > 1:
        #         print(f"***Warning: found {len(r.json())} matching repo records...")
        #         for n, item in enumerate(r.json()):
        #             print(f"Record {n}: {item['title']}, created {item['created']}")
        #
        #         record = input('Set record to use: ')
        #         # r.json() = r.json()[record]
        #     else:
        #         record = 0  #r.json() = r.json()[0]

        # BASIC search grabs also similar titles, so will need to check more carefully.
        record = None
        if r.json():
            print(f"Found {len(r.json())} possible repo matches...")

            for n, item in enumerate(r.json()):
                print(f"Item {n}: {item['title']}")

                # Confirm match based on str.rfind to match substring and ignore prefixing.
                # Should be more robust to future changes...?
                ind = item['title'].rfind(self.nbDetails[key]['title'])
                if item['title'][ind:] == self.nbDetails[key]['title']:
                      print(f"Confirm match: ID {item['id']}, created {item['created']}, selecting record.")
                      record = n
                      break
                else:
                      print('No match.')


        # If no matching record is found, init new.
        if record is None:
            headers = {"Content-Type": "application/json"}
            r = requests.post('https://zenodo.org/api/deposit/depositions',
                               params={'access_token': ACCESS_TOKEN}, json={}, data=json.dumps(data),
                               headers=headers)
            print(f"***{self.nbDetails[key]['title']} repo created.")

        # deposition_id = r.json()['id']

        # Confirm details returned and set in nbDetails.
        if r.ok:
            if record is None:
                self.nbDetails[key]['repoInfo'] = r.json()  # Returns metadata plus repo settings
            else:
                self.nbDetails[key]['repoInfo'] = r.json()[record]  # Case where multiple records are returned

            self.nbDetails[key]['doi'] = self.nbDetails[key]['repoInfo']['metadata']['prereserve_doi']['doi']
            print(f"Repo details set.")
            if verbose:
                pprint.pprint(self.nbDetails[key]['repoInfo'])
        else:
            self.nbDetails[key]['repoInfo'] = r.status_code  # Returns error code
            print(f"Repo comms failed, code: {r.status_code}")  # Should return 201

    else:
        print(f"\n***{self.nbDetails[key]['title']} skipped repo creation.")

    if dryRun:
        print('\n***Repo init dry run')
        if verbose:
            # print(stringHTML)
            pprint.pprint(data)

        self.nbDetails[key]['repoHeaderData'] = data


def delRepoItem(self, key):
    """Delete item from repo (Zenodo) - for unpublished items only."""

    ACCESS_TOKEN = initZenodo(self.hostDefn['localhost']['localSettings']/'zenodoSettings.dat')
    r = requests.delete('https://zenodo.org/api/deposit/depositions/%s' % self.nbDetails[key]['repoInfo']['id'],
                        params={'access_token': ACCESS_TOKEN})
    if r.ok:
        print(f"Item {self.nbDetails[key]['title']} deleted from repo.")
        self.nbDetails[key]['repoInfo'] = None
        self.nbDetails[key]['doi'] = None
    else:
        print(f"Failed to remove item {self.nbDetails[key]['title']}, code: {r.status_code}")


def uploadRepoFiles(self, key):
    """Upload files to repo (from local machine)

    For remote run see repo/remoteUpload.py

    """

    ACCESS_TOKEN = initZenodo(self.hostDefn['localhost']['localSettings']/'zenodoSettings.dat')
    url = f"https://zenodo.org/api/deposit/depositions/{self.nbDetails[key]['repoInfo']['id']}/files?access_token={ACCESS_TOKEN}"

    outputs = []
    for fileIn in self.nbDetails[key]['repoFiles']:
        # Basic schema... will need to run on remote however.

        data = {'name': Path(fileIn).name}
        files = {'file': open(fileIn, 'rb')}
        r = requests.post(url, data=data, files=files)

        if r.ok:
            print(f"File upload OK: {fileIn}")
        else:
            print(f"File upload failed: {fileIn}")

        outputs.append([r.ok, r.json()])

    self.nbDetails[key]['repoFilesUpload'] = outputs

    return 'Not implemented'


#***************************************************************************
#*** ARCHIVE functions

# Package job files for repo
# May need to do this as a separate local function for Fabric calls?
# TODO:
# - Add optional elec structure file to pkg.
# - Check if arch exists before running
# - Consider moving main loop to remote code - what are the dependecies here?  Should just be able to pass a dir path, or maybe write list to file and push to host?
def buildArch(self, localLoop = True, dryRun = True, hide = True):
    """
    Build archives/packages for job.

    Wrapper for repo/pkgFiles.py, which runs on host machine.

    Parameters
    ----------
    localLoop : bool, default = True
        Run version of code with job loop on local machine - one Fabric call per job to pkg.
        This is useful for dryRun, but not for packaging large dirs on remote.
        If false, run all code on remote.

    dryRun : bool, default = True
        Get fileLists to be archived, but don't build.
        Most useful for localLoop = True case.

    hide : bool, default = True
        If false, print all Fabric output to screen (localLoop = True case only)
        If true, only summary data is printed.

    To do
    -----
    - Search logic for electronic structure files.
    - Call

    """

    # make pkg dir on host
    print(f"\n***Building archives for {self.hostDefn[self.host]['nbProcDir']}")
    if dryRun:
        print("***DryRun only")
    else:
        self.c.run('mkdir -p ' + self.hostDefn[self.host]['pkgDir'].as_posix())

    print(f"Pkg dir: {self.hostDefn[self.host]['pkgDir']}")

    # Loop over Notebooks locally and package corresponding files.
    # Useful for testing, but not good for large jobs.
    if localLoop:
        zipList = []
        failList = []

        # for item in self.nbFileList:  # Local file list, from nbFileList
        for key in self.nbDetails:
            # Skip metadata key if present
            if key!='proc':
                # Job keys
                item = Path(self.nbDetails[key]['file'])
                # dirBase = Path(self.nbDetails[key]['file']).parent  # Could set dirBase here instead of nbProcDir

                # if self.hostDefn[self.host]['jobSchema'] == '2016':
                #     jRoot = item.stem.rsplit(sep='_', maxsplit=3)
                #     self.nbDetails[key]['jRoot'] = f"{jRoot[1]}_{jRoot[2]}_{jRoot[3]}"
                # elif self.hostDefn[self.host]['jobSchema'] == '2019':
                #     jRoot = item.stem.rsplit(sep='_', maxsplit=2)
                #     self.nbDetails[key]['jRoot'] = f"{jRoot[1]}_{jRoot[2]}"

                # Define using function  in pkgFiles.py
                jRoot = setJobRoot(item, self.hostDefn[self.host]['jobSchema'])
                self.nbDetails[key]['jRoot'] = jRoot

                archName = Path(self.hostDefn[self.host]['pkgDir'], item.stem + '.zip')

                # Check if archive exists & get file list

                # Generate filelist - based on code in getNotebookJobList()
                # Glob for files matching job, inc. subdirs, skip any zip files found.
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/* | grep --include=${jRoot[1]}_{jRoot[2]} --exclude=pkg", warn = True, hide = True)
            #     Result = job.c.run(f"shopt -s globstar; ls -d -1 '{job.hostDefn[job.host]['nbProcDir'].as_posix()}/'**/*[!zip] | grep {jRoot[1]}_{jRoot[2]}", warn = True, hide = True)
            #     fileOut = shutil.make_archive('/home/femtolab/temp/shutiltest', 'zip', '/home/femtolab/python/epsman/repo/')

                # For remote run, call python code on host machine,
                # Do this once per item in nbFileList, and grab output.
                with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
                    # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
                    # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
                    # result = job.c.run('python /home/femtolab/python/epsman/repo/pkgFiles.py' + f" {job.hostDefn[job.host]['pkgDir'].as_posix()} {jRoot[1]}_{jRoot[2]} {archName}")
                    result = self.c.run(f"python {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} \
                                        {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {archName} {self.hostDefn[self.host]['jobSchema']} {jRoot}", hide = hide)

                if dryRun:
                    # self.nbDetails[key]['result'] = result
                    output = result.stdout.splitlines()
                    self.nbDetails[key]['pkgInfo'] = output[:5]
                    self.nbDetails[key]['pkgFileList'] = output[5:]
                    self.nbDetails[key]['archName'] = archName.as_posix()
                    # print(f"Found {len(self.nbDetails[key]['pkgFileList'][5:])} items.")
                    self.fileListCheck(key)  # Print info to screen & basic error checking.

                else:
                    self.nbDetails[key]['archName'] = archName.as_posix()
                    self.nbDetails[key]['archBuilt'] = result.stdout

    else:
        # For remote run, call python code on host machine,
        # In this case, do this for full build dir, and loop on remote machine.
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            # Vanilla version - will wait for script execution
            # result = self.c.run(f"python {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {self.hostDefn[self.host]['pkgDir'].as_posix()}")

            # Nohup version to allow for lengthy remote
            result = self.c.run(f"{Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkgNohup']).as_posix()} {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} \
                                        {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {self.hostDefn[self.host]['pkgDir'].as_posix()} {self.hostDefn[self.host]['jobSchema']} \
                                        {self.nbDetails['proc']['archLog']}",
                                        warn = True, timeout = 10)

        # TODO: Logic for handling stdout here.
        # May want to change to writing to remote file for nohup use.
        # NOW set in pkgRemoteNohup.sh, writes to local log file. self.hostDefn[self.host]['nbProcDir']/archLog_nohup.log
        # Use getArchLogs() to retrieve

        return result

# Update archive with new file(s)
def updateArch(self, fileIn, archName, dryRun = True):
    """
    Add file to existing archive.

    NOTE: if file exists in archive it will be skipped, not be updated, since python ZipFile does not support this.
    NOTE: if file path root is different from archive root path (as set in call below) it will be addded to the archive root, otherwise relative path will be preserved.

    Parameters
    ----------
    fileIn : str or Path
        File to add to archive.

    archName : str or Path
        Archive to add file to.

    """
    with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
        result = self.c.run(f"python {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['pkg']).as_posix()} \
                            {self.hostDefn[self.host]['nbProcDir'].as_posix()} {dryRun} {archName} {self.hostDefn[self.host]['jobSchema']} {fileIn}")

    return result


def checkArchFiles(self, key = None, archName = None, verbose = False):
    """
    Check archive file contents on remote and compare with local contents list

    Parameters
    -----------
    key : int or str
        Item key in self.nbDetails

    archName : str or Path object
        If supplied, use instead of self.nbDetails[key]['archName']

    Either key or archName must be supplied.

    Returns
    --------
    localListRel, archFiles : list
        Local files with relative paths & archive file list.

    fileComp : list
        Difference between lists.

    result : Fabric object
        Full return from remote, .stdout includes archFiles and file details.

    """

    # Set archive from passed args.
    if key is not None and archName is None:
        archName = self.nbDetails[key]['archName']
    elif key is None and archName is None:
        print('Skipping archive checks, no archive supplied.')
        return None

    # Check if file exists on remote
    # Note this returns a list
    archExists = self.checkFiles(archName)

    if archExists[0]:
        # Get arch contents from remote via Fabric.
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            result = self.c.run(f"python -m zipfile -l {archName}", hide = True)

        # Compare with local lsit
        # archFiles = result.stdout.splitlines()
        # localList = self.nbDetails[key]['pkgFileList'][5:]
        # fileComp = list(set(localList) - set(archFiles))  # Compare lists as sets
        archFiles = [(line.split()[0]) for line in result.stdout.splitlines()[1:]]  # Keep file names only (drop header, and file properties)
        localList = self.nbDetails[key]['pkgFileList']

        # Test & set relative paths for local files in archive
        localListRel = []
        for fileIn in localList:
            try:
                localListRel.append(Path(fileIn).relative_to(self.hostDefn[self.host]['nbProcDir']).as_posix())
            except ValueError:
                localListRel.append(Path(fileIn).name)  # In this case just take file name, will go in archive root

        fileComp = list(set(localListRel) - set(archFiles))  # Compare lists as sets

        # Results
        print(f"\n***Checking archive: {archName}")
        print(f"Found {len(archFiles)} on remote. Local list length {len(localList)}.")

        # This will run if fileComp is not an empty list
        if fileComp:
            print(f"Difference: {len(archFiles) - len(localList)}")
            print("File differences:")
            print(*fileComp, sep = '\n')

        else:
            print("Local and remote file lists match.")


    else:
        print(f"***Missing archive: {archName}")
        fileComp = None

    # Set fileComp
    # Either empty, None or list of differences.
    self.nbDetails[key]['archFileCheck'] = fileComp
    if fileComp:
        self.nbDetails[key]['archFilesOK'] = False
    elif fileComp is None:
        self.nbDetails[key]['archFilesOK'] = False
    else:
        self.nbDetails[key]['archFilesOK'] = True

    if verbose:
        print("\n***Local file list:")
        print(*localListRel, sep='\n')
        print("\n***Archive file list:")
        print(*archFiles, sep='\n')

    return localListRel, archFiles, fileComp, result


# Set electronic structure file
def setESFiles(self, eSourceDir = None, verbose = False):
    """
    Set electronic structure file from job info.

    Use alternative path eSourceDir if passed.

    Check also if file exists.

    """

    print('\n***Setting electronic structure files')
    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc':
            # Check and set electronic structure file for packaging.
            if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
                self.nbDetails[key]['elecStructure'] = None
            else:
                if eSourceDir is not None:
                    # Copy electronic structure files to package using supplied path
                     fileName = Path(self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'"))
                     self.nbDetails[key]['elecStructure'] = Path(eSourceDir, fileName.name).as_posix()

                else:
                    # Copy electronic structure files to package, based on full path from original job
                    self.nbDetails[key]['elecStructure'] = self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'")

                checkList = self.checkFiles(self.nbDetails[key]['elecStructure'])

                # If file is missing, set to "missing"
                if not checkList[0]:
                    self.nbDetails[key]['elecStructure'] = f"***Missing file: {self.nbDetails[key]['elecStructure']}"

            if verbose:
                print(f"Job {key}: {self.nbDetails[key]['title']}")
                print(f"Set file: {self.nbDetails[key]['elecStructure']}")


# Basic function to copy files from original job electronic_structure to repo.
# Generally better to just add file directly to pkg?
# TODO: add some search logic here for related files?
# TODO: Deprecated, remove or repurpose.  File info now set by setESFiles()
def cpESFiles(self, dryRun = True, eSourceDir = None):
    print('\n***Copying electronic structure files')
    if dryRun:
        print('***Dry run only')

    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc':
            # Check and set electronic structure file for packaging.
            if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
                pass
            else:
                if eSourceDir is not None:
                    # Copy electronic structure files to package using supplied path
                     fileName = Path(self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'"))
                     self.nbDetails[key]['elecStructure'] = Path(eSourceDir, fileName.name).as_posix()

                else:
                    # Copy electronic structure files to package, based on full path from original job
                    self.nbDetails[key]['elecStructure'] = self.nbDetails[key]['jobInfo'][-1].split()[-1].strip("'")

                checkList = self.checkFiles(self.nbDetails[key]['elecStructure'])

                # Make job dir and copy file(s)
                eDir = Path(self.hostDefn[self.host]['nbProcDir'], f"{self.nbDetails[key]['jRoot']}_elec_struc")

                # If file exists, copy to job dir
                if checkList[0] and not dryRun:
                    result = self.c.run('mkdir -p ' + eDir.as_posix())
                    result = self.c.run(f"cp {self.nbDetails[key]['elecStructure']} {eDir}")
                    if result.ok:
                        print(f"cp {self.nbDetails[key]['elecStructure']} {eDir} OK")
                    else:
                        print(f"*** cp {self.nbDetails[key]['elecStructure']} {eDir} failed")

                else:
                    print(f"Skipping command: cp {self.nbDetails[key]['elecStructure']} {eDir}")
                # Path(job.nbDetails[2]['elecStructure'][0]).with_suffix('.inp')


# Get arch logs
# Use this for cases where large pkg jobs were left running on remote.
# May also want to run archive checks independently here?
def getArchLogs(self):
    """Get archive logs from host (for remote run with nohup)"""

    # Implement checkFiles() for archs?

    # Pull log file
    if self.nbDetails['proc']['archLog'] is not None:
        result = self.c.get(self.nbDetails['proc']['archLog'])
        print(f"Pulled archive creation log {result.remote} to {result.local}")
    else:
        print(f"Archives not yet written.")

#*********************************************
#***  Additional utility functions

# Get E points from jobInfo
def getEpoints(jobInfo):
    """Parse notebook header text for energy points"""
    for line in jobInfo:
        if line.strip().startswith("E="):
            print(line)
            P=line

    return parseLineDigits(P)

# Summary info from nbDetails dict.
def nbDetailsSummary(self):
    """Print notebook stats."""

    # Get totals
    nbTotal = len(self.nbDetails.keys()) - 1
    pkgTotal = sum([1 for key in self.nbDetails.keys() if key!='proc' and self.nbDetails[key]['pkg']])
    pkgList = [Path(self.nbDetails[key]['file']).relative_to(self.hostDefn[self.host]['nbProcDir']).as_posix() \
                for key in self.nbDetails.keys() if key!='proc' and self.nbDetails[key]['pkg']];

    print("\n***nbDetails summary")
    print(f"Found {nbTotal} notebooks, {pkgTotal} marked for packaging:")
    print(*pkgList, sep='\n')


# Parse and sort pkg file list and related info.
def fileListCheck(self, key = None, verbose = True, errorCheck = True):
    """
    Pkg job filelist sorting & summary

    Parse pkg file list (nbDetails[key]['pkgFileList']) for details:
    - Dirs
    - Files and types
    - Check against expected numbers

    NOTE: this is currently done based on path formats, since os or path methods only work on local machine.
    This may not be robust.

    """

    # if key is not None:

    fileListTest = self.nbDetails[key]['pkgFileList']

    # Count file suffixes
    suffixList = [Path(item).suffix for item in fileListTest]
    c = Counter(suffixList)

    # Check for dirs & log
    dirList = []
    fileList = []
    for n, item in enumerate(suffixList):
        # if Path(item).is_dir():       # Checking with Path OK for local files, but not for a list from another machine.
        if item == '':
            dirList.append(fileListTest[n])
        else:
            fileList.append(fileListTest[n])

    self.nbDetails[key]['pkgRootDir'] = os.path.commonpath(fileListTest)
    self.nbDetails[key]['pkgDirList'] = dirList
    self.nbDetails[key]['pkgSuffixCount'] = c

    # Print details
    if verbose:
        print('\n***Pkg job summary')
        print(f"Job {key}, title: {self.nbDetails[key]['title']}")
        print(f"Notebook file: {self.nbDetails[key]['file']}")
        print(*self.nbDetails[key]['pkgInfo'][2:], sep='\n')
        print(f"Root dir: {self.nbDetails[key]['pkgRootDir']}")
        print(f"Found {len(fileListTest)} items, with file types:")
        # Throw out full dictionary here, may want to switch to formatted list.
        # Set small width to force vertical format
        pprint.pprint(c, width=50)

        if dirList:
            print("SubDirs:")
            print(*dirList, sep='\n')


    # Check if wavefunction job, and if files are present.
    # TODO: propagate this issue!!! For init self.nbDetails[key]['pkg'] is not yet set... may need to move this check to later?
    self.nbDetails[key]['wf'] = any(['waveFn' in item for item in self.nbDetails[key]['pkgDirList']])|any(['wf' in item for item in self.nbDetails[key]['pkgDirList']])
    # if self.nbDetails[key]['wf']:
    #     print(f"Wavefunction job, with {c['.dat']} dat files, expected {self.nbDetails[key]['E'][2]*5}")

    # Error checking based on file types
    # Set pass/fail in self.nbDetails[key]['fileListCheck']
    if errorCheck:
        self.nbDetails[key]['fileListCheck'] = True

        if c['.out'] > 1:
            print(f"***Warning: found {c['.out']} ePS output files.")
            self.nbDetails[key]['fileListCheck'] = False

        if c['.idy'] != 3:
            # TODO: change to checking by number of symmetries
            print(f"***Warning: found {c['.idy']} ePS idy files.")
            self.nbDetails[key]['fileListCheck'] = False

        if self.nbDetails[key]['wf']:
            # if (c['.dat'] is None):
            #     print("***Warning: No .dat files found")
            # elif (c['.dat'] != self.nbDetails[key]['E'][2]*5):
            #     print(f"***Warning: found {c['.dat']} dat files, expected {self.nbDetails[key]['E'][2]*5} for wavefunction job.")
            fPerE = 5 # Set files per energy point for numerical checks
            if self.nbDetails[key]['E'] is None:
                En = 0
            else:
                En = int(self.nbDetails[key]['E'][3])*fPerE

            if En == 0:
                print(f"***Warning: found {c['.dat']} dat files, missing job E details for wavefunction job.")
                self.nbDetails[key]['fileListCheck'] = False
            elif (c['.dat'] is None) or (c['.dat'] < En):
                print(f"***Warning: found {c['.dat']} dat files, expected {En}*syms for wavefunction job.")
                self.nbDetails[key]['fileListCheck'] = False
            else:
                # Check symmetries...
                # SnTest = [En%Sn for Sn in range(1,6)]
                Sn = c['.dat']/En
                if c['.dat']%En == 0:
                    print(f"Wavefunction job, with {c['.dat']} dat files OK (for {Sn} syms)")
                else:
                    print(f"***Warning: Wavefunction job, with {c['.dat']} dat files indeterminate symmetries {Sn}")
                    self.nbDetails[key]['fileListCheck'] = False

        if c['.nc'] != 2:
            # TODO: change to checking by number of symmetries
            print(f"***Warning: found {c['.nc']} ePSproc nc files, expected 2.")
            self.nbDetails[key]['fileListCheck'] = False


#***********************************************************************************************
#***High-level functions for building and updating uploads (packages)

# Build notebook list & info
def buildUploads(self, Emin = 3, repo = 'Zenodo', repoDryRun = True, verbose = False, dryRun = True, eStructCp = True, eSourceDir = None, nbSubDirs = False, schema = '2016', writeDict = None):
    """
    Build notebook file list + details + archives.

    Note this will process & package all jobs in nbProcDir.

    Parameters
    ----------
    Emin : int, optional, default = 3
        Minimum number of E points for job packaging.

    repo : str, default = 'Zenodo'
        Set repo for uploading. Currenly only supports Zenodo.

    repoDryRun : bool, default = True
        Set to False to initiate job with repo (passed to initRepo(dryRun = repoDryRun)).
        If True, details will be printed to screen only.

    verbose : bool, default = False
        If True, print repo details.

    dryRun : bool, default = True
        Set to True to get file info etc, but skip writing archives.

    eStructCp : bool, default = True
        Copy electronic structure file(s) to job dirs.
        Currently only set for single file, should add search logic here.

    eSourceDir : str or path object, optional, default = None
        If supplied, use this as the source path for electronic structure files instead of original job definition.

    nbSubDirs : bool, default = False
        Search for notebooks in subdirs.
        Default is to search in root dir only, as set in self.hostDefn[self.host]['nbProcDir']
        Note this is only used if reconstructing nbFileList.

    writeDict : bool, default = None
        Set to overwrite ndDetails() dictionary.
        If not set, user will be prompted to overwrite if dict exists.


    TODO:
    - Fix inconsistent handling of subDirs. Currently set for getNotebookList(), but not remote glob functions.
    - move repo stuff to separate function, this will be called *after* archives are built.
        Repo will only need files as set, plus job details.

    """

    # Check if notebook file list is set, set if missing.
    # if not hasattr(self, 'nbFileList'):
    self.getNotebookList(subDirs = nbSubDirs)
    # else:
    #     nbReplace = input('***Use existing notebook list, or overwrite? (y/n): ')
    #     if nbReplace == 'y':
    #         self.getNotebookList(subDirs = nbSubDirs)

    # Get header info and build dictionary
    # Currently using nbWriteHeader for this, will skip file writing if DOI not set.
    self.nbWriteHeader()

    # Pkg dry run - use this to create file list etc.
    # This will be called again later to build archives for upload.
    self.buildArch()

    # If eStructCp = True this will copy electronic structure files to job dirs.
    # If dryRun = True will just display commands.
    # MAY BE CLEANER just add file to archive from original path later....?
    # if eStructCp:
    #     self.cpESFiles(dryRun = dryRun, eSourceDir =  eSourceDir)
    # SKIP THIS... just add files in updateArch()

    # Reformat header data (as per notebook header) & set additional info.
    # This is written to file, and used for repo.
    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc':
            # Set var for packaging - set to True below for completed jobs.
            self.nbDetails[key]['pkg'] = False

            if '***Missing' in self.nbDetails[key]['jobInfo'][2]:
                self.nbDetails[key]['jobText'] = None

            else:
                # Use function from nbHeaderWrite.py for consistency with notebook IO code.
                # Note that jobInfo here has additional lines from version in nbHeaderWrite.py, so drop start.
                self.nbDetails[key]['jobText'] = constructHeader(self.nbDetails[key]['jobInfo'][2:], self.nbDetails[key]['file'], self.nbDetails[key]['doi'])

                # Currently set to skip pkg if test job (<Emin) or info missing, or failed error checking in fileListCheck()
                if (int(self.nbDetails[key]['E'][-1]) > Emin) and self.nbDetails[key]['fileListCheck']:
                    self.nbDetails[key]['pkg'] = True
                    self.nbDetails[key]['repo'] = repo
                    self.initRepo(key, dryRun = repoDryRun, verbose = verbose)  # This will init comms with repo (Zenodo) and get doi etc.


    # Set dir metadata
    self.nbDetails['proc'] = {'host':self.host,
                              'nbProcDir':self.hostDefn[self.host]['nbProcDir'].as_posix(),
                              'date':datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                              'archLog':None
                              }

    # Pkg files - build archives for all jobs on remote
    if not dryRun:
        print('\n***Running archive creation on remote.')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        self.nbDetails['proc']['archLog'] = Path(self.hostDefn[self.host]['nbProcDir'],
                                            f"{self.hostDefn[self.host]['nbProcDir'].name}_{self.host}_archLog_nohup_{timestamp}.log").as_posix()
        result = self.buildArch(localLoop = False, dryRun = dryRun)


    # Write nbDetials to JSON file
    self.writeNBdetailsJSON()

    self.nbDetailsSummary()


def updateUploads(self, dryRun = True, verbose = False):

    # UPDATE NOTEBOOKS & ARCHIVES with DOI.
    # PLUS add missing files to archives.
    # Should init repo here too? Keep it separate from archive build. ACTUALLY OK to set above, since DOI remains reserved for at least 24hrs.
    #

    # Check repo is initialized - may not be in some cases of manual arch build.
    # May also want to check for self.nbDetails[key]['repoInfo'] here.
    for key in self.nbDetails:
        if key!='proc' and self.nbDetails[key]['pkg']:
            if self.nbDetails[key]['doi'] is None:
                self.initRepo(key, dryRun = dryRun, verbose = verbose)

    # Rerun nbWriteHeader() to set DOIs correctly in notebooks flagged for repo - don't overwrite nbDetails.
    # TODO: pull info here on notebook writing...?  Currently will be printed to screen only.
    self.nbWriteHeader(writeDict = False, hide = (not verbose))

    # Update archives
    for key in self.nbDetails:
        # Skip metadata key if present
        if key!='proc' and self.nbDetails[key]['pkg']:

            # Set file list for adding to archive
            # TODO: decide on electronic structure file(s) - see cpESFiles()
            # NOW: SET VIA setESFiles() and added here instead.
            fileList = []
            if not (self.nbDetails[key]['file'] in self.nbDetails[key]['pkgFileList']):
                fileList.append(self.nbDetails[key]['file'])
            if not (self.nbDetails[key]['elecStructure'] in self.nbDetails[key]['pkgFileList']):
                fileList.append(self.nbDetails[key]['elecStructure'])

            if (self.nbDetails[key]['doi'] is None) and not dryRun:
                print(f"***Skipping archive updates, repo not yet initialized (DOI not set) and not dryRun.")
            else:
                for fileIn in fileList:
                    result = self.updateArch(fileIn, self.nbDetails[key]['archName'], dryRun = dryRun)

                    if result.ok:
                        self.nbDetails[key]['pkgFileList'].append(fileIn)  # Update pkg filelist


            # Check archives.
            # NOTE: if the above code is rerun it will append the same files repeatedly, but they won't be added to the archive.
            # TODO: additional error checking above!
            # TODO: Update arch files with any missing items?
            self.checkArchFiles(key);


            # TODO: consider filesize, might be upload limit (100Mb per file on Zenodo...?)

            # Set file list for repo upload
            self.nbDetails[key]['repoFiles'] = [self.nbDetails[key]['file'], self.nbDetails[key]['archName']]

    # Update nbDetials JSON file
    self.writeNBdetailsJSON()


def submitUploads(self, local = False):

    # Set and upload files to repo using uploadRepoFiles()
    if local:
        for key in self.nbDetails:
            # Skip metadata key if present
            if key!='proc' and self.nbDetails[key]['pkg'] and self.nbDetails[key]['archFilesOK']:
                self.uploadRepoFiles(key)

    else:
    # Upload on remote machine.
        ACCESS_TOKEN = initZenodo(self.hostDefn['localhost']['localSettings']/'zenodoSettings.dat')
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            result = self.c.run(f"{Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['uploadNohup']).as_posix()} \
                                {Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['upload']).as_posix()} \
                                {self.hostDefn[self.host]['nbProcDir']/self.jsonProcFile.name} {ACCESS_TOKEN}",
                                warn = True, timeout = 10)

        print(f"Log file set: {self.hostDefn[self.host]['nbProcDir']/self.jsonProcFile.name}")
    # Remote upload set to run via nohup... will need to pull logs later.

    # Publish

    # return 'Not implemented'


#***************************************************************************************
#*** Read/write functions for job metadata & notebooks.

def writeNBdetailsJSON(self):
    """Write nbDetails dictionary to JSON file and push to host."""

    # Write to json file
    # Follow previous file IO scheme: set locally, and push to host

    # Set filename if not already set.
    if not hasattr(self, 'jsonProcFile'):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        jsonProcFile = self.hostDefn[self.host]['nbProcDir'].name + '_' + self.host + '_nbProc_' + timestamp + '.json'
        self.jsonProcFile = Path(self.hostDefn['localhost']['wrkdir'], jsonProcFile)

    # Write to JSON.  Note Path() objects won't serialize.
    with open(self.jsonProcFile.as_posix(), 'w') as f:
        json.dump(self.nbDetails, f, indent=2)

    print(f'\n***nbDetails written to local JSON file: {self.jsonProcFile}')

    # Push to host
    pushResult = self.pushFile(self.jsonProcFile, self.hostDefn[self.host]['nbProcDir'])


def readNBdetailsJSON(self, overwrite = None):
    """Read previously written nbDetails dictionary from JSON file.

    If overwrite = None, prompt for overwrite if details exist.

    """

    print("***Reading local JSON file for nbDetails.")

    # Get filename if not already set.
    if not hasattr(self, 'jsonProcFile'):
        print("nbDetails JSON filename not set.")
        fileIn = input('Filename?: ')
        if Path(fileIn).is_file():
            self.jsonProcFile = Path(fileIn)
        else:
            print('File not found.')
            return False

    # Check for existing data
    if not hasattr(self, 'nbDetails') and (overwrite is None):
        owInput = input("nbDetails already exists, overwrite? (y/n): ")
        if owInput == 'y':
            overwrite = True
        else:
            print('Skipping nbDetails.')
            return False

    # Read local JSON file.
    with open(self.jsonProcFile.as_posix(), 'r') as f:
        self.nbDetails = json.load(f)



# Processed job file header creation
def nbWriteHeader(self, writeDict = None, hide = False):
    """
    Read job info and set header cell for ePSproc Notebooks for repo upload.
    """
    # Init empty dictionary if not set, or use existing details.
    # This logic seems to fail in some cases... not sure why!
    # Added manual override in function call.
    # Also overridden in case that key is missing.
    if not hasattr(self, 'nbDetails') or writeDict:
        self.nbDetails = {}
        writeDict = True
    elif hasattr(self, 'nbDetails') and (writeDict is None):
        writeFlag = input('nbDetails already exists, reinit and overwrite? (y/n): ')
        if writeFlag == 'y':
            self.nbDetails = {}  # Reinit dict in this case, otherwise may retain some old entries
            writeDict = True
        else:
            writeDict = False
    elif writeDict is None:
        writeDict = False

    # Load notebook, write header & save
    # NOTE - this requires doi to be preset.
    for n, nb in enumerate(self.nbFileList):
        # Register job with repo - NOW DONE LATER in buildUploads() and initRepo()
        # For now just check for doi setting here, pass None if not set (to read header only).
        if n in self.nbDetails.keys():
            if 'doi' in self.nbDetails[n]:
                doi = self.nbDetails[n]['doi']
        else:
            doi = None

        # Run python script for notebook post-process, with Anaconda env set (requires python3 and nbformat)
        # See https://stackoverflow.com/questions/54268390/how-to-deploy-my-conda-env-to-a-vps-using-fabric-or-othervise
        with self.c.prefix(f"source {self.hostDefn[self.host]['condaPath']} {self.hostDefn[self.host]['condaEnv']}"):
            # job.c.run('/home/femtolab/python/epsman/shell/conda_test.sh')  # Still have issues here, due to code in script
            # result = job.c.run('python /home/femtolab/python/epsman/nbHeaderPost.py ' + f'{fileIn} {doi}')
            result = self.c.run('python ' + Path(self.hostDefn[self.host]['repoScpPath'], self.scpDefnRepo['nb-post-doi']).as_posix() + f' {nb} {doi}', hide = hide)

        # Store job info locally
        # If key is missing ignore writeDict setting and add to dict
        if writeDict or (n not in self.nbDetails.keys()):
            jobInfo = result.stdout.splitlines()

            if '***Missing' in jobInfo[2]:
                Elist = None
                title = None
            else:
                Elist = getEpoints(jobInfo)
                title = jobInfo[3].split(',')[0].strip()

            self.nbDetails.update({n:{'file':nb,  # Path(nb),  # Setting Path object here gives issues with json seralization later!
                                     'doi':doi,
                                     'title':title,
                                     'jobInfo':jobInfo,
                                     'E':Elist,
                                     'pkg':False  # Set pkg default = False, used later to check for arch creation & repo upload.
                                    }})


#*** Repo uploader

# Upload package
