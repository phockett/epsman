"""
ESjob clas - combines EShandler electronic structure file functionality + epsJob class functionality.

22/02/21    Basics working for file setting & epsJob functionatliy (including backend method dev)

19/02/21    Started dev.

"""

from pathlib import Path

import epsman as em  # For base class
import epsman.elecStructure.ESclass as ESclass  # Electronic structure methods

# With EShandler as base
# class ESjob(ESclass.EShandler, em.epsJob):

# Without EShandler - run, instead, on a per-host basis
class ESjob(em.epsJob):
    """
    Class to wrap epsJob + EShandler functionality.

    19/02/21: now init with epsman.epsJob class as parent, so can implement existing file IO methods.
    """

    def __init__(self, fileName = None, fileBase = None, outFile = None, **kwargs):

        # Job creation init
        em.epsJob.__init__(self, **kwargs)


    def setESfiles(self, fileName = None, fileBase = None, pushPrompt = True, overwriteFlag = False):
        """
        Set electronic structure files for all self.hostDefn[host] and sync files.
        """

        # Set values in epsJob class format (if not already set)
        # self.setAttribute('elecDir', fileBase)  # This will set self.elecDir, which is generally not used - need to pass/check to self.hostDefn[host]['elecDir'], or just ignore here.
        self.setAttribute('elecStructure', fileName, overwriteFlag = overwriteFlag)

        # If fileBase not passed, check for currently set paths
        # TODO!

        # Set in master host list
        if self.elecStructure is not None:
            # Set in hostDefn
            for host in self.hostDefn:
                self.hostDefn[host]['elecFile'] = Path(self.hostDefn[host]['elecDir'], self.elecStructure)

            # # Check file exists (local + host only)
            # if self.verbose:
            #     print(f'Electronic structure file {self.elecStructure} host checks:')
            #
            # fCheckHost = {}
            # for host in [self.host, 'localhost']:
            #     if host == 'localhost':
            #         fCheckHost[host] = self.checkLocalFiles(self.hostDefn[host]['elecFile'])  # use local Path file test.
            #     else:
            #         fCheckHost[host] = self.checkFiles(self.hostDefn[host]['elecFile'])   # Use remote Fabric file test.
            #
            #     if self.verbose:
            #         print(f"\n\t{host}:  \t{self.hostDefn[host]['elecFile']} \t{fCheckHost[host]}")
            #
            # pushFlag = 'n'
            # if (not fCheckHost[self.host]) and (fCheckHost['localhost']):
            #     if pushPrompt:
            #         pushFlag = print(f'Push missing file to {self.host}?  (y/n) ')
            #     else:
            #         pushFlag = 'y'
            #
            # if pushFlag == 'y':
            #     self.pushFileDict('elecFile')

            # Sync files
            self.syncFilesDict('elecFile', pushPrompt = pushPrompt)


    def checkLocalESfiles(self, master = 'localhost', pushPrompt = True):
        """
        Check local ES files, convert to Molden & sync.


        """

        # With EShandler as parent class
        # EShandler init
        # EShandler.__init__(self, fileName = fileName, fileBase = fileBase, outFile = outFile)

        # Run base init routine for job settings
        # super().__init__(**kwargs)

        # With EShandler per host - CURRENTLY ASSUMED TO BE LOCAL HOST ONLY, set as master
        # NOW SET as passed arg
        # for master in ['localhost']:

        # Set object & read file
        self.esData = ESclass.EShandler(self.hostDefn[master]['elecFile'], self.hostDefn[master]['elecDir'])

        # If file is not a Molden file, read & convert
        if self.esData.data is not None:
            self.esData.writeMoldenFile2006()

            # # Update master file
            # self.elecStructure = self.esData.moldenFile.name
            #
            # # Update host paths (all hosts)
            # for host in self.hostDefn:
            #     self.hostDefn[host]['elecFileGamess'] = self.hostDefn[host]['elecFile']
            #     self.hostDefn[host]['elecFile'] = self.hostDefn[host]['elecDir'] self.esData.moldenFile  # self.hostDefn[host]['elecFile'].with_name
            #
            # # Sync files
            # self.syncFilesDict('elecFile', pushPrompt = pushPrompt)

            # Preserve Gamess file in new key
            for host in self.hostDefn:
                self.hostDefn[host]['elecFileGamess'] = self.hostDefn[host]['elecFile']

            # Update with existing functionality.
            self.setESfiles(fileName = self.esData.moldenFile.name, overwriteFlag = True, pushPrompt = pushPrompt)
