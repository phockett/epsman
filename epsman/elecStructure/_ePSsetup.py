"""
Methods for setting up ePS job info based on electronic structure data.

Note:

- First set of methods using ES file currently setup for use with ESclass.EShandler(), but may want to move into ESjob class...?
- Second set of methods for ePS job creation currently setup for use with ESclass.ESjob(), with an EShandler() object as an input. These need a bit more work, and should be properly wrapped to use class attributes.

10/06/21: initial version.

TODO:

- Possibly tidy up some of the naming to (a) Match ePS, (b) allow for easy dictionary-style looping.
- Consolidate and streamline/revisit methods and overall procedure.

"""
import numpy as np
import pandas as pd

import itertools
import collections

#************* Functions for setting ePS jobs based on orb info: these will likely want to go into main ESjob class, but initial versions (10/06/21) used in EShandler class.
def setChannel(self, channelInd, orbOcc = None):
    """
    Set ionizing channel (final state) in self.orbGrps, or reset orbOcc number.

    Parameters
    ----------
    channelInd : int
        Index matching OrbGrpOcc to remove electron from.

    orbOcc : int, optional, default = None
        If specified, set this occupation number.
        If None, new occ number = original - 1


    TODO:

    - Generalise for setting any orb occ sets.
    - Set/reset options? Currently ALWAYS resets final state.

    """

    self.orbGrps['OrbGrpOccFinal'] = self.orbGrps['OrbGrpOcc']  # Update table with final state

    if orbOcc is None:
        self.orbGrps.at[channelInd, 'OrbGrpOccFinal'] = self.orbGrps.at[channelInd, 'OrbGrpOccFinal'] - 1

    else:
        self.orbGrps.at[channelInd, 'OrbGrpOccFinal'] = orbOcc

    self.channel = self.orbGrps.loc[channelInd]  #  self.orbGrps.at[channelInd]  # Log ionizing channel for later

    if self.verbose:
        print(f"*** Set ionization from orbital/channel {channelInd}.")
        print("Updated orb table...")
        self.orbInfoSummary(showSummary=False, showFull=False)


def setePSinputs(self, PG=None, Ssym = None, Csym = None):
    """
    Create ePS input records from existing data (from electronic structure file).

    Set as dictionary of params that match input card keywords (cf. pygamess routines).

    NOTE: if PG is set, additionally run self.convertSymList() to convert to ePolyScat symmetry labels.


    Should generate output to match current file format, roughly:

    ___________

    # Symmetry pairs for ScatSym (==ion x electron symm) and ScatContSym (==electron symm), input file will loop through these
    Ssym=({' '.join([item[0] for item in symList])})
    Csym=({' '.join([item[1] for item in symList])})

    # Global symmetries & spin
    SpinDeg=1			# Spin degeneracy of the total scattering state (=1 singlet)
    TargSym='HG'		# Symmetry of the target state
    TargSpinDeg=2		# Target spin degeneracy
    InitSym='AG'		# Initial state symmetry
    InitSpinDeg=1		# Initial state spin degeneracy'
    ___________

    Notes/TODO:

    - Pretty basic sym handling to improve.
    - Test for open shell systems, likely logic currently fails here.
    - Currently set for existing output via .conf file > shell script, which is a bit messy and needs replacing.
    - These are set to handle a single job, with the exception of Eke and Syms, which might be split into separate files.
      For multiple jobs use multiple instances...?  BUT may need to modify job writing routines first...?

    """

    if not hasattr(self, 'ePSrecords'):
#         self.ePSrecords = {}  # As dict
        self.ePSrecords = collections.OrderedDict()  # As ordered dict, will maintain insertion order

    #*** Job metadata
    #*****************************************************************
    #***** TODO: these are currently set in em.epsJob(), but not in EShandler - need to finish subclassing, or push this code to parent class and use EShandler objects therein.
    #*****************************************************************
    # Job definitions, used for dir structure and output naming.
#     mol={job.mol}
#     orb={job.orb}
#     job={job.batch}
#     note=f"'{job.jobNote}'"

    #*** Electronic struture
    self.ePSrecords['elecStructure'] = self.moldenFile
    self.ePSrecords['IP'] = np.round(-self.channel['E'], decimals = 3)  # Set effective channel IP (but may want only 1st IP here?)


    #*** Orbitals
    orbInd = self.orbGrps.OrbGrpOcc > 0  # Set index by occupied orbs, and use for both. This may be an issue in some cases...? (E.g. if keeping some unoccupied orbs?)
    self.ePSrecords['OrbOccInit'] = self.orbGrps.OrbGrpOcc[orbInd].to_string(index=False, header=False).replace('\n',' ')
    self.ePSrecords['OrbOccTarget'] = self.orbGrps.OrbGrpOccFinal[orbInd].to_string(index=False, header=False).replace('\n',' ')

    #*** Spins - rough
    # Test for UPEs - this should be OK for single ionizing channel, but will probably fail for open-shell cases - maybe take union to test for this?
    initUPEs = self.orbGrps[self.orbGrps['OrbGrpOcc']%2 != 0]  #.values
    targetUPEs = self.orbGrps[self.orbGrps['OrbGrpOccFinal']%2 != 0] #.values

#     targetUPEs = pd.concat([initUPEs,targetUPEs])  # Union to check & fix any problems for open-shell cases? May need join="inner"
    intersection = pd.merge(initUPEs,targetUPEs, how="inner")  # Intersection - will only return items in BOTH groups

    # Set spin degens
    self.ePSrecords['InitSpinDeg'] = (initUPEs['OrbGrpOcc']%2).sum()+1
    self.ePSrecords['TargSpinDeg'] = (targetUPEs['OrbGrpOccFinal']%2).sum()+1
    self.ePSrecords['SpinDeg'] = self.ePSrecords['InitSpinDeg']   # This will usually/always (?) be the case...?

    #*** Symmetries
    # For the moment guess some things from the orbitals, but should do this properly. https://trello.com/c/UZuip2yt/181-symmetry-direct-products-etc
    totSym = self.orbGrps['syms'][self.orbGrps['Occ']].mode().to_string(index = False)  # Assume most common case is totally symmetric, and use as InitSym
    self.ePSrecords['InitSym'] = totSym
    self.ePSrecords['TargSym'] = targetUPEs['syms'].to_string(index = False, header=False)  # OK for single ionizing channel, should also check intersection case above.


    # Symmetry pairs for ScatSym (==ion x electron symm) and ScatContSym (==electron symm), input file will loop through these
    if not hasattr(self,'symList'):
        print("self.symList not set, running for defaults")
        self.genSymList(Ssym=Ssym, Csym=Csym)

#     if PG is not None:
#         self.convertSymList(PG)
    if hasattr(self, 'PG'):   # This is currently problematic, since it will overwrite back to defaults SHIT CODE
        self.convertSymList(Ssym=Ssym, Csym=Csym)  # NOW FIXED WITH SHIT HACK - pass through symms to allow for sym gen at job writing case. FUCKING UGLY SHITTTY SHIT

    # TODO: move to separate fn, see symTest code below.
    self.ePSrecords['Ssym']=f"({' '.join([item[0] for item in self.symList])})"   # Current format for looping script input writer... but ugly!
    self.ePSrecords['Csym']=f"({' '.join([item[1] for item in self.symList])})"


def genSymList(self, Ssym = None, Csym = None):
    """
    Generate symmetry paris - crude version.

    Pass lists for Ssym and Csym, or set to None for full set generation (brute force).
    """

    # Set defaults from input symmetries - although this may not be == full point group
#     for item in [Ssym, Csym]:  # LOOP OVER THESE CLEARLY
    if Ssym is None:
        Ssym = self.orbPD['syms'].unique()

    if not isinstance(Ssym,list):
        Ssym = [Ssym]

    if Csym is None:
        Csym = self.orbPD['syms'].unique()

    if not isinstance(Csym,list):
        Csym = [Csym]


    # Product is good - gives all pairs from both lists
    self.symList = list(itertools.product(Ssym, Csym))


def convertSymList(self, Ssym = None, Csym = None):
    """
    Quick conversion from Gamess to ePS symmetry labels by point group.

    NOTE:

    - Manually adding at the moment, may want to automate with web look-up?
    - CCLIB doesn't seem to pull point group from Gamess file, so may want to do this too.

    HORRIBLE CODE: bodged this to allow passed args from setePSInputs() method, now rather circular.

    """
    if hasattr(self, 'PG'):
        PG = self.PG

    else:
        PG = None

    # Linear molecule, CNV8 in Gamess, CAv in ePS
#     CAv, (C-infinity-v) 'S', 'A2', 'B1', 'B2', 'P', 'D', 'F', 'G'
    if (PG == 'CNV8') or (PG == 'CAv'):
        convDict = {'A1':'S', 'E1':'P'}  # Lookup table... could be problematic, since there may not be one-to-one correspondence! Should be OK for orbitals?

        ePSsyms = ['S', 'A2', 'B1', 'B2', 'P', 'D', 'F', 'G']  # Full sym list from https://epolyscat.droppages.com/SymmetryLabels

        if Ssym is None:
            Ssym = ePSsyms

        if Csym is None:
            Csym = ePSsyms

        self.genSymList(Ssym=Ssym, Csym=Csym)  # Regenerate full sym list with ePS labels

        # Set init and final syms from dict

        # Basic version - will fail if these ARE ALREADY SET TO ePS SYMS.
#         self.ePSrecords['InitSym'] = convDict[self.ePSrecords['InitSym']]
#         self.ePSrecords['TargSym'] = convDict[self.ePSrecords['TargSym']]

        for item in ['InitSym', 'TargSym']:

            try:
                self.ePSrecords[item] = convDict[self.ePSrecords[item]]

            except KeyError as k:
                print(f"Didn't find symmetry {k} in self.ePSrecords[{item}], left as {self.ePSrecords[item]}")


    else:
        print(f"*** Couldn't find ePS labels for PG={PG}, please check point group & symmetry labels.")


def writeInputConf(self):
    """Basic dictionary > ePS job conf template"""

    ePSstring = ''
    for k, v in self.ePSrecords.items():
#         ePSstring.join(f'{k}={v}\n')
        if isinstance(v, str) and not (k in ['Ssym', 'Csym']):
            ePSstring += f"{k}='{v}'\n"   # May need to debug here - some fields with ' ' delims, some not.
        else:
            ePSstring += f"{k}={v}\n"  # No additional delims for numeric values

    self.ePSjobConf = ePSstring



#**************************** ADDITIONAL job creation functions. Initial versions (10/06/21) set for ESjob class (NOT EShandler as per methods above!).
# THIS IS ALL VERY UGLY CODE!@

# MULTI-JOB CASE - set as dict in job.[jobs], based on jobES inputs...?
# TODO: need to consider function order here, looping over settings & saving params.
# EITHER: wrap existing class + methods & copy to new items, or keep dictionary of changes...?

from itertools import compress

def setJobInputConfig(self, jobES):
    """Write job.jobSetting configuration string from jobES and other params."""
    self.jobSettings = f"""

# Job definitions, used for dir structure and output naming.
mol={self.mol}
orb={self.orb}
job={self.batch}
note='{self.jobNote}'


#*******************************************************************************************
# (c) Molecule (job) settings
#

{jobES.ePSjobConf}

"""

#     print()

def symTest(self, jobES):
    """
    Loop over symmetry pairs for symmetry testing case.

    Note this currently uses Eke value as a way to write one file per symmetry pair, with all other parameters unchanged. Bit ugly... but works with current codebase, including file checks.
    """

#     jobES.genSymList()  # Generate full sym list (all allowed pair)

    fullSyms = jobES.symList.copy()
    self.fullSyms = fullSyms
    # Loop over symmetry sets for job & write outputs
    nTot = len(fullSyms)
    n = 1

    print(f"Writing test symmetry jobs for {nTot} items.")

    # Quick hack for Eke settings == n, ugh
#     Estart = n
    dE = 0.5

    for item in fullSyms:

        # Set for new symmetry pair
#         jobES.genSymList(Ssym = item[0], Csym = item[1])
        jobES.setePSinputs(Ssym = item[0], Csym = item[1])
        jobES.writeInputConf()

        self.setJobInputConfig(jobES)

        self.writeGenFile()

        # Note - need pushFile even for localhost case, otherwise paths not set correctly.
        self.pushFile(self.genFile, self.hostDefn[self.host]['genDir'], overwritePrompt=False)  # OK for file in wrkdir, force overwrite - currently not working!!!

        # Set Elist as n.
        # TODO: do this better, set single E job writer IDIOT!!!!!
        # PROBABLY THIS IS ALREADY DONE IN BASE CODE, just not class version.
        self.Elist = em.multiEChunck(Estart=n, Estop = n+dE, dE = dE, EJob=1)  # WITHOUT Estop this currently hangs!
        # job.Elist = np.array([1.0, 2.0], ndmin=2).T   # For single E case have to set manually...? With current code will ALWAYS be 2 Eke minimum, since self.writeInp() uses this for file name! Should have another version for single E test cases?

        self.writeInp(scrType = 'basic', wLog = False)  #  'basic', 'wf-sph')
        n = n+1

# This works, but note it's ONE WAY - rerunning will mess things up.
# NEED SOME MORE ROBUST METHODS HERE, everything is OK for single runs only.
# NO THIS DOESN'T WORK - INCORRECT SYMS AS LIST ORDERING DIFFERENT YOU FUCKING MORON
def setSymsFromFiles(self, jobES):    #, symTest = False):   #, Ssym=None, Csym=None):  # May want to set explicitly here too? Or set as separate fn.
    """Set/update self.symList from fileList or passed inputs."""

#     # Get from set of jobs
# #     if symTest:
    fTest = [fLine.endswith("Finalize") for fLine in self.fTails]  # Current code
    fGood = list(compress(job.fileList, np.array(fTest)))  # Good files only

#     self.fullSyms = jobES.symList.copy()
#     jobES.symList = list(compress(self.fullSyms, np.array(fTest)))  # Good syms


    # PULL N BACK FROM SYMTEST
    fGoodN = [int(item.split('_E')[1].split('.')[0])-1 for item in fGood]  # Pull N in a very ugly manner
    jobES.symList = [jobES.symList[N] for N in fGoodN]

    # Update sym list with only good items
    jobES.ePSrecords['Ssym']=f"({' '.join([item[0] for item in jobES.symList])})"   # Current format for looping script input writer... but ugly!
    jobES.ePSrecords['Csym']=f"({' '.join([item[1] for item in jobES.symList])})"

    jobES.writeInputConf()
