# -*- coding: utf-8 -*-
r"""
ePSman Generation functions
---------------------------

02/10/19    First development version, based on old shell scripts (circa 2010, 2015).
            Dev on Bemo, see
                http://localhost:8889/notebooks/python/remote/N2_tests/ePS_input_write_file_tests_290919.ipynb
                http://localhost:8889/notebooks/python/remote/N2_tests/ePSman_dev_021019.ipynb

TODO:           convert to class.
                Set dict of local and remote connections.

"""

import numpy as np
from fabric import Connection

# Basic routine to create dir tree for new system (molecule)
def createJobDirTree(wrkdir, mol, c, genFile = None):
    """"
    Basic routine to create dir tree for new system (molecule)

    Parameters
    ----------
    wrkdir : str
        Base dir for files.

    mol : str
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

    # Check if remote dir exists
    systemDir = wrkdir + '/' + mol
    test = c.run('[ -d "' + systemDir + '" ]', warn = True)  # Run remote command and return exit value without raising exit errors if dir doesn't exist

    # Alternatively can skip checking here and just use 'mkdir -p' below.

    # Set generator
    genDir = systemDir + '/generators'

    # Build dir tree
    if test.ok == False:
        c.run('mkdir ' + systemDir)
        c.run('mkdir ' + genDir)
        c.run('mkdir ' + systemDir + '/electronic_structure')
        print('Dir tree built, ', systemDir)
    else:
        print('Dir tree already exists, ', systemDir)

    # Upload genFile
    if genFile is not None:
        # Test if exists
        test = c.run('[ -f "' + genDir + '/' + genFile + '" ]', warn = True)  # As written will work only for genFile name (not if full local path supplied)
        if test.ok:
            wFlag = input("File already exists, overwrite? (y/n) ")
        else:
            wFlag = 'y'

        # Upload and test result.
        if wFlag == 'y':
            genResult = c.put(genFile, remote=genDir)
            test = c.run('[ -f "' + genDir + '/' + genFile + '" ]', warn = True)  # As written will work only for genFile name (not if full local path supplied)
            if test.ok:
                # print(f'Generator file {genFile}, put to {genDir}')
                print("Uploaded {0.local} to {0.remote}".format(genResult))
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
