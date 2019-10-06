# -*- coding: utf-8 -*-
r"""
ePSman Generation functions
---------------------------

03/10/19    Converting to class-based version to allow for  transparent param settings.

02/10/19    First development version, based on old shell scripts (circa 2010, 2015).
            Dev on Bemo, see
                http://localhost:8889/notebooks/python/remote/N2_tests/ePS_input_write_file_tests_290919.ipynb
                http://localhost:8889/notebooks/python/remote/N2_tests/ePSman_dev_021019.ipynb

TODO:           convert to class.
                Set dict of local and remote connections.

"""

# Import for functions
import numpy as np
from fabric import Connection
import getpass
from pathlib import Path

def initConnection(self, host = None, user = None, IP = None):
    """Init connection to selected machine & test."""

    # Set values if passed (but don't overwrite set values)
    if self.host is None and host is not None:
        self.host = host
    if self.user is None and user is not None:
        self.user = user
    if self.IP is None and IP is not None:
        self.IP = IP

    # Check if host definitions are already set, set if missing
    if self.host in self.hostDefn.keys():
        if 'IP' not in self.hostDefn[self.host].keys() and self.IP is None:
            self.IP = input('Host IP required for connection: ')
        if 'IP' not in self.hostDefn[self.host].keys():
            self.hostDefn[self.host]['IP'] = self.IP
    else:
        self.hostDefn[self.host] = {'host':self.host, 'IP':self.IP}


    # print(f'Connecting to machine: {self.host}') # at {self.hostDefn[self.host]['IP']}')  # Multi-level indexing not allowed here.
    print('Connecting to machine: {} at {}'.format(self.host, self.hostDefn[self.host]['IP']))

    if self.user is None and self.host == 'localhost':
        self.user = getpass.getuser()
    elif self.user is None:
        self.user = input("User name for machine? ")

    if self.password is None:
        self.password = getpass.getpass("Password for machine? ")

    print('Testing connection...')

    # Connect to remote
    # With password passed explicitly (should also pick up keys from default location ~/.ssh/)
    self.c = Connection(
        host = self.hostDefn[self.host]['IP'],
        user = self.user,
        connect_kwargs = {
            "password": self.password,
            "allow_agent": False,       # Added to force new SSH session.
                                        # http://docs.fabfile.org/en/2.5/concepts/authentication.html#ssh-agents
        },
    )

    test = self.c.run('hostname')
    # c.is_connected    # Another basic check.

    if test.return_code == 0:
        print('Connected OK')
        print(test)
    else:
        print('Connection failed')
        print(test)

    # Build dir list if not already set
    if 'home' not in self.hostDefn[self.host].keys():
        print('\n\nSetting host dir tree.')
        self.hostDefn[self.host]['home'] = Path(self.c.run('echo ~', hide = True).stdout.strip())
        testwrkdir = self.c.run('ls -d eP*', hide = True).stdout.split()
        if len(testwrkdir) > 1:
            print('Found multiple ePS directories, please select working dir:')
            # print(testwrkdir)
            for n, item in enumerate(testwrkdir):
                print(f'{n}: {item}')

            N = int(input('List item #: '))
            self.hostDefn[self.host]['wrkdir'] = Path(self.hostDefn[self.host]['home'], testwrkdir[N])
        else:
            self.hostDefn[self.host]['wrkdir'] = Path(self.hostDefn[self.host]['home'], testwrkdir)

        print('Set remote wrkdir: ' + self.hostDefn[self.host]['wrkdir'].as_posix())

        # TODO: finish this... should add looping over necessary paths, functionalised and with more searching. Sigh.
        # FOR NOW - set know paths based on above.
        self.hostDefn[self.host]['scpdir'] = Path(self.hostDefn[self.host]['wrkdir'], 'scripts2019')
        self.hostDefn[self.host]['jobPath'] = Path(self.hostDefn[self.host]['wrkdir'], 'jobs')
        self.hostDefn[self.host]['jobComplete'] = Path(self.hostDefn[self.host]['jobPath'], 'completed')



# Basic routine to create dir tree for new system (molecule)
def createJobDirTree(self):
    """"
    Basic routine to create dir tree for new system (molecule)

    Parameters
    ----------
    self : epsJob structure
        Contains path and job settings:

        Molecule/system/job name for dir structure
        Subdirs wrkdir/mol/electronic_structure
                wrkdir/mol/generators
        Will be created if not present.

        c : fabric connection object
            Fabric connection used to run commands (over ssh).
            For local use, set to use local machine, e.g. c = Connection('user@localhost')

        genFile : str, optional, default = None
            Generator file, will be uploaded to wrkdir/mol/generators if passed.

    """


    # Check if (remote) dir exists
    test = self.c.run('[ -d "' + self.hostDefn[self.host]['systemDir'].as_posix() + '" ]', warn = True)  # Run remote command and return exit value without raising exit errors if dir doesn't exist

    # Alternatively can skip checking here and just use 'mkdir -p' below.

    # Build dir tree
    if test.ok == False:
        self.c.run('mkdir ' + self.hostDefn[self.host]['systemDir'].as_posix())
        self.c.run('mkdir ' + self.hostDefn[self.host]['genDir'].as_posix())
        self.c.run('mkdir ' + self.hostDefn[self.host]['elecDir'].as_posix())
        print('Dir tree built, ', self.hostDefn[self.host]['systemDir'].as_posix())
    else:
        print('Dir tree already exists, ', self.hostDefn[self.host]['systemDir'].as_posix())

    # Upload genFile
    if self.genFile is not None:
        print('Pushing job generator file: ' + str(self.genFile))

        # Test if exists
        test = self.c.run('[ -f "' + self.hostDefn[self.host]['genFile'].as_posix() + '" ]', warn = True)
        if test.ok:
            wFlag = input(f"File {self.genFile} already exists, overwrite? (y/n) ")
        else:
            wFlag = 'y'

        # Upload and test result.
        if wFlag == 'y':
            genResult = self.c.put(self.genFile, remote = self.hostDefn[self.host]['genDir'].as_posix())
            test = self.c.run('[ -f "' + self.hostDefn[self.host]['genFile'].as_posix() + '" ]', warn = True)  # As written will work only for genFile name (not if full local path supplied)
            if test.ok:
                # print(f'Generator file {genFile}, put to {genDir}')
                print("Uploaded \n{0.local}\n to \n{0.remote}".format(genResult))
            else:
                print('Failed to put generator file to host.')

            return genResult

    return True

# Functionalise with adaptive job number.
def multiEChunck(Estart = 0.1, Estop = 30.1, dE = 2.5, EJob = None):
    """
    Basic multi-E job set-up, with adaptive chunking into sub-jobs.

    Parameters
    ----------
    Estart : int, float, optional, default = 0.1
    Estop : int, float, optional, default = 30.1
    dE : int, float, optional, default = 2.5
        Overall energy ranges (eV) for job. Defaults for basic survey-scan. Jobs will be chunked into sub-jobs with EJob elements if possible.

    EJob : int, optional, default = None
        Number of energy points per input file (sub-jobs).
        If set to None, this will be set automatically.
        If set to an int, this will determine job chunck size, but may be overriden in some cases to nearest common divisor.

    Returns
    -------
    Elsit : np.array, 2D
        Final energy list, corresponding to one row per input file.

    """

    # Generate initial Elist
    Elist = np.round(np.arange(Estart,Estop+dE,dE), decimals = 2)

    if EJob is None:
        # With adaptive job chunking - select max GCD from a range of values.
        EJobRange = [5,21] # Set [min,max] chunck size to test

    else:
        EJobRange = [EJob-3, EJob+3]  # If set explicitly, aim for close-ish value.

    EJobtest = np.gcd(Elist.size, np.arange(EJobRange[0],EJobRange[1])).max()  # Check greatest common divisor

    # Check that divisor is reasonable - if not, expand the job range by one step and repeat.
    while (EJobtest < EJobRange[0]) or (EJobtest > EJobRange[1]):
        Elist = np.append(Elist, Elist[-1]+dE)
        EJobtest = np.gcd(Elist.size, np.arange(EJobRange[0],EJobRange[1])).max()  # Check greatest common divisor


    Elist.shape = EJobtest, -1
    print('E = {0}:{1}:{2}, {3} points total, {4}/{5} = {6} job files will be written.'.format(Elist[0,0],dE,Elist[-1,-1],Elist.size,Elist.size,EJobtest, Elist.shape[1]))

    return Elist


# Function to write ePS input files, multi-E chunks
# Loop over chuncks, here set to run shell script with passing of E values and job title.
def writeInp(self, scrType = 'basic'):
    """Write ePS input files from job structure, in multi-E chunks."""

    dp = 2  # Set for output name formatting for round(%f, dp)

    writeLog = []
    for n in np.arange(0, self.Elist.shape[1]):
        # Set ranges separately for readability
        E1 = str(round(self.Elist[0,n], dp))
        E2 = str(round(self.Elist[-1,n], dp))
        dE = str(round(self.Elist[1,n]-self.Elist[0,n], dp))

        # Run shell script for E chunk.
        result = self.c.run(Path(self.hostDefn[self.host]['scpdir'], self.scrDefn[scrType]).as_posix() +
            f' {E1} {E2} {dE} ' + self.hostDefn[self.host]['genFile'].as_posix())
        writeLog.append(result)

    self.writeLog = writeLog
