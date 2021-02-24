"""
Class for ePolyScat job generation, including file IO and multi-E generation.

Main function is local and remote path management (via pathlib), job configuration set-up (manual), and local & remote file IO (via Fabric/Invoke).

19/02/21    Removed _repo, _web and _epsProc methods, these to be set as a separate post-processing class.

16/02/21    Tidying up...
            - Added setHost() and setJob() methods to handle set & reset of parameters. Pretty basic, may need work, also quite a lot of boilerplate in current implementation.
            - Moved job-specific paths functionality to setJobPaths() method.
            - Tidied up setGenFile() and rationalised methods.

"""

# Imports
# import numpy as np
# from fabric import Connection
from pathlib import Path
# import getpass
import socket

# Import local functions
from ._epsJobGen import multiEChunck


# Set master class
class epsJob():
    """
    Class for ePolyScat job generation, including file IO and multi-E generation.

    Main function is local and remote path management (via pathlib), job configuration set-up (manual), and local & remote file IO (via Fabric/Invoke).

    19/02/21: removed _repo, _web and _epsProc methods, these to be set as a separate post-processing class.

    """

    # Import local functions
    from ._paths import setScripts, setPaths, setJobPaths, setWrkDir, setHostDefns
    from ._epsJobGen import setHost, initConnection, setJob, setGenFile, createJobDirTree, writeGenFile, writeInp
    from ._epsRun import runJobs, tidyJobs
    # from ._epsProc import getNotebookJobList, getNotebookList, setNotebookTemplate, runNotebooks, tidyNotebooks, getNotebooks
    from ._util import getFileList, checkLocalFiles, checkFiles, pullFileDict, pullFile, pushFileDict,  pushFile,  setAttribute, setAttributesFromDict, syncFilesDict
    # from ._repo import nbWriteHeader, nbDetailsSummary, buildUploads, updateUploads, submitUploads, publishUploads,      \
    #                     buildArch, updateArch, getArchLogs, checkArchFiles,             \
    #                     setESFiles, cpESFiles, fileListCheck, pkgOverride,                                     \
    #                     initRepo, delRepoItem, uploadRepoFiles, searchRepo, publishRepoItem, checkRepoFiles,    \
    #                     writeNBdetailsJSON, readNBdetailsJSON, writeJobJSON
    # from ._web import updateWebNotebookFiles, buildSite

    def __init__(self, host = None, user = None, IP = None, password = None,
                    mol = None, orb = None, batch = None, genFile = None, verbose = 1):
        """
        Init job.

        Parameters
        ----------
        host, user, IP : str, default = None
            Pass host settings for job. Currently used to set connection & look-up machine details.
            TODO: convert to connection only, and bootstrap paths.

        """
        self.verbose = verbose

        # Set hostDefns - NOW paths set at connection init stage, just set localhost here.
        # To set a given machine to be used locally, this will just need local IP setting.
        # TODO: set master dir list somewhere for reference.
        # TODO: sometimes have bugs due to presetting localhost here, should consolidate with other init codes.
        self.hostDefn = {
            'localhost':{'host':socket.gethostname(),
                'IP':'127.0.0.1',
                'home':Path.home(),
                'wrkdir':Path.cwd(),
                'webDir':Path(Path.home(), 'github/ePSdata')}
            }

        # Settings for connection - init to None.
        # self.host = host
        # self.user = user
        # self.password = password
        # self.IP = IP
        self.setHost(host = host, user = user, IP = IP, password = password, overwriteFlag = True)

        # Settings for job - init to None.
        # self.mol = None
        # self.orb = None
        # self.batch = None
        # self.genFile = None
        # self.jobSettings = None
        self.setJob(mol = mol, orb = orb, batch = batch, genFile = genFile)

        # Set default paths
        self.setScripts()
