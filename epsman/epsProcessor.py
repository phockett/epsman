"""
Class for ePolyScat job post-processing, inc. notebook generation & pushing repo to web.


19/02/21    v1, moved from previous uber-class to keep functionality cleaner and reflect usage.
            CURRENTLY: just set as per old base class, but should clean up with only used functions and/or inheritance.

"""

# Imports
# import numpy as np
# from fabric import Connection
from pathlib import Path
# import getpass
# import socket

# Import local functions
# from ._epsJobGen import multiEChunck
from .epsJob import epsJob

# Set master class
class epsProcessor(epsJob):
    """
    Class for ePolyScat job post-processing, inc. notebook generation & pushing repo to web.

    Main function is local and remote path management (via pathlib), job configuration set-up (manual), and local & remote file IO (via Fabric/Invoke).

    19/02/21    v1, moved from previous uber-class to keep functionality cleaner and reflect usage.
                CURRENTLY: just set as per old base class, but should clean up with only used functions and/or inheritance.
                UPDATE: set to inherit from epsJob class for comms & util methods.


    """

    # Import local functions
    # from ._paths import setScripts, setPaths, setJobPaths, setWrkDir
    # from ._epsJobGen import setHost, initConnection, setJob, setGenFile, createJobDirTree, writeGenFile, writeInp
    # from ._epsRun import runJobs, tidyJobs
    from ._epsProc import getNotebookJobList, getNotebookList, setNotebookTemplate, runNotebooks, tidyNotebooks, getNotebooks
    # from ._util import getFileList, checkFiles, pushFile
    from ._repo import nbWriteHeader, nbDetailsSummary, buildUploads, updateUploads, submitUploads, publishUploads,      \
                        buildArch, updateArch, getArchLogs, checkArchFiles,             \
                        setESFiles, cpESFiles, fileListCheck, pkgOverride,                                     \
                        initRepo, delRepoItem, uploadRepoFiles, searchRepo, publishRepoItem, checkRepoFiles,    \
                        writeNBdetailsJSON, readNBdetailsJSON, writeJobJSON
    from ._web import updateWebNotebookFiles, buildSite

    # def __init__(self, host = None, user = None, IP = None, password = None,
    #                 mol = None, orb = None, batch = None, genFile = None, verbose = 1):
    #     """
    #     Init job.
    #
    #     Parameters
    #     ----------
    #     host, user, IP : str, default = None
    #         Pass host settings for job. Currently used to set connection & look-up machine details.
    #         TODO: convert to connection only, and bootstrap paths.
    #
    #     """
    #     self.verbose = verbose
    #
    #     # Set hostDefns - NOW paths set at connection init stage, just set localhost here.
    #     # To set a given machine to be used locally, this will just need local IP setting.
    #     # TODO: set master dir list somewhere for reference.
    #     # TODO: sometimes have bugs due to presetting localhost here, should consolidate with other init codes.
    #     self.hostDefn = {
    #         'localhost':{'host':socket.gethostname(),
    #             'IP':'127.0.0.1',
    #             'home':Path.home(),
    #             'wrkdir':Path.cwd(),
    #             'webDir':Path(Path.home(), 'github/ePSdata')}
    #         }
    #
    #     # Settings for connection - init to None.
    #     # self.host = host
    #     # self.user = user
    #     # self.password = password
    #     # self.IP = IP
    #     self.setHost(host = host, user = user, IP = IP, password = password, overwriteHost = True)
    #
    #     # Settings for job - init to None.
    #     # self.mol = None
    #     # self.orb = None
    #     # self.batch = None
    #     # self.genFile = None
    #     # self.jobSettings = None
    #     self.setJob(mol = mol, orb = orb, batch = batch, genFile = genFile)
    #
    #     # Set default paths
    #     self.setScripts()
