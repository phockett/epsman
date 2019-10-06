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

    def __init__(self, host = None, user = None, IP = None):
        """
        Init job.

        Parameters
        ----------
        host, user, IP : str, default = None
            Pass host settings for job. Currently used to set connection & look-up machine details.
            TODO: convert to connection only, and bootstrap paths.

        """
        # Set hostDefns - NOW paths set at connection init stage.
        # To set a given machine to be used locally, this will just need local IP setting.
        # TODO: set master dir list somewhere for reference.
        self.hostDefn = {'AntonJr':{
                'host':'AntonJr',
                'ePSpath':Path('/opt/ePolyScat.E3/bin/ePolyScat')},
            'localhost':{'host':socket.gethostname(),
                'IP':'127.0.0.1',
                'home':Path.home(),
                'wrkdir':Path.cwd()}
            }

        # Set dictionary of Shell scripts for .inp file generation.
        self.scrDefn = {'basic':'ePS_input_write_template_basic.sh',
                        'wf-sph':'ePS_input_write_template_wf_sph.sh'}

        # Settings for connection - init to None.
        self.host = host
        self.user = user
        self.password = None
        self.IP = IP

        # Settings for job
        self.genFile = None
        self.jobSettings = None


    def setGenFile(self, genFile = None):
        # Default setting
        if self.genFile is None and genFile is None:
            self.genFile = Path(f'{self.mol}_{self.orb}.conf')
        elif self.genFile is None and genFile is not None:
            self.genFile = genFile
        # else:
        #     print('*** Generator filename not defined.')

        print(f'Generator file set: {self.genFile}')

        # Set in hostDefn
        for host in self.hostDefn:
            self.hostDefn[host]['systemDir'] = Path(self.hostDefn[host]['wrkdir'], self.mol)
            self.hostDefn[host]['elecDir'] = Path(self.hostDefn[host]['systemDir'], 'electronic_structure')
            self.hostDefn[host]['genDir'] = Path(self.hostDefn[host]['systemDir'], 'generators')
            self.hostDefn[host]['genFile'] = Path(self.hostDefn[host]['genDir'], self.genFile)
            self.hostDefn[host]['jobDir'] = Path(self.hostDefn[host]['systemDir'], self.genFile.stem)

        # Write file locally (working dir).
        if self.jobSettings is not None:
            with open(self.genFile,'w') as f:
                f.write(self.jobSettings)
                print('Written local job conf file (working dir): ' + str(Path(self.hostDefn['localhost']['wrkdir'], self.genFile)))
