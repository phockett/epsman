"""
ePSman Generation functions
---------------------------

03/10/19    Converting to class-based version to allow for  transparent param settings.
            Imports moved to __init__.py

02/10/19    First development version, based on old shell scripts (circa 2010, 2015).
            Dev on Bemo, see
                http://localhost:8889/notebooks/python/remote/N2_tests/ePS_input_write_file_tests_290919.ipynb
                http://localhost:8889/notebooks/python/remote/N2_tests/ePSman_dev_021019.ipynb

"""

# Imports
# import numpy as np
# from fabric import Connection
from pathlib import Path
# import getpass
import socket

# Import local functions
from ._epsJobGen import multiEChunck

# Import master class
# from epsman._epsJobGen import epsJob

# Set master class
class epsJob():
    """
    Class for ePolyScat job generation, including file IO and multi-E generation.

    Main function is local and remote path management (via pathlib), job configuration set-up (manual), and local & remote file IO (via Fabric/Invoke).

    """

    # Import local functions
    from ._epsJobGen import initConnection, createJobDirTree, writeInp
    from ._epsRun import runJobs, tidyJobs
    from ._epsProc import getNotebookJobList, getNotebookList, setNotebookTemplate, runNotebooks, tidyNotebooks, getNotebooks
    from ._util import getFileList, checkFiles, pushFile
    from ._paths import setScripts, setPaths
    from ._repo import nbWriteHeader, nbDetailsSummary, buildUploads, updateUploads, submitUploads,       \
                        buildArch, updateArch, getArchLogs, checkArchFiles,             \
                        setESFiles, cpESFiles, fileListCheck,                                     \
                        initRepo, delRepoItem, uploadRepoFiles,                         \
                        writeNBdetailsJSON, readNBdetailsJSON, writeJobJSON

    def __init__(self, host = None, user = None, IP = None, password = None):
        """
        Init job.

        Parameters
        ----------
        host, user, IP : str, default = None
            Pass host settings for job. Currently used to set connection & look-up machine details.
            TODO: convert to connection only, and bootstrap paths.

        """
        # Set hostDefns - NOW paths set at connection init stage, just set localhost here.
        # To set a given machine to be used locally, this will just need local IP setting.
        # TODO: set master dir list somewhere for reference.
        self.hostDefn = {
            'localhost':{'host':socket.gethostname(),
                'IP':'127.0.0.1',
                'home':Path.home(),
                'wrkdir':Path.cwd()}
            }

        # Settings for connection - init to None.
        self.host = host
        self.user = user
        self.password = password
        self.IP = IP

        # Settings for job
        self.mol = None
        self.orb = None
        self.batch = None
        self.genFile = None
        self.jobSettings = None

        # Set default paths
        self.setScripts()


    def setGenFile(self, genFile = None):
        # Default setting
        if self.genFile is None and genFile is None:
            # self.genFile = Path(f'{self.mol}_{self.orb}.conf')
            self.genFile = Path(f'{self.batch}.{self.orb}.conf')
        elif self.genFile is None and genFile is not None:
            self.genFile = Path(genFile)
        # else:
        #     print('*** Generator filename not defined.')

        print(f'Generator file set: {self.genFile}')

        # Set in hostDefn
        for host in self.hostDefn:
            self.hostDefn[host]['systemDir'] = Path(self.hostDefn[host]['wrkdir'], self.mol)
            self.hostDefn[host]['elecDir'] = Path(self.hostDefn[host]['systemDir'], 'electronic_structure')
            self.hostDefn[host]['genDir'] = Path(self.hostDefn[host]['systemDir'], 'generators')
            self.hostDefn[host]['genFile'] = Path(self.hostDefn[host]['genDir'], self.genFile)
            # self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], self.genFile.stem)
            self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], Path(self.genFile.stem).stem) # This form will work for X.Y.conf and X.conf styles.
            # self.hostDefn[host]['jobRoot'] = Path(self.hostDefn[host]['systemDir'], self.batch)  # Use job type (batch) here
            self.hostDefn[host]['jobDir'] = Path(self.hostDefn[host]['jobRoot'], self.orb)  # Definition here to match shell script. Possibly a bit redundant, but allows for multiple orbs per base job settings.

        # Write file locally (working dir).
        if self.jobSettings is not None:
            with open(self.genFile,'w') as f:
                f.write(self.jobSettings)
                print('Written local job conf file (working dir): ' + str(Path(self.hostDefn['localhost']['wrkdir'], self.genFile)))
