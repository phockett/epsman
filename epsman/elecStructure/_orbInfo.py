"""
Methods for converting electronic structure (ES) file info <> ePS job info.

For use with ESclass.EShandler()

10/06/21: initial version.

"""


import pandas as pd
import numpy as np

from epsman._util import fileParse, parseLineTokens

#************* Functions for getting orb info: these will likely want to go into EShandler class.
def setOrbInfoPD(self, groups = ['E','syms'], zeroInd = False):
    """
    Set info to self.orbPD, from electronic structure file (via CCLIB).

    See also ep.jobSummary() and ep.getOrbInfo() for similar case from ePS output files.

    Parameters
    ----------

    groups : str or list of strs, optional, default = ['E','syms']
        Groups to use when determining degeneracies.
        If using 'E' only, some cases may produce incorrect results if there are multiple symmetry states with same E.

    zeroInd : bool, optional, default = False
        If true use start index at 0 for orbitals/states.
        Otherwise start index at 1.

    Notes
    -----

    For point-group, CCLIB metadata[symmetry_detected] and metadata[symmetry_used], see https://cclib.github.io/data_notes.html#metadata
    Not set for Gamess file import?

    02/02/22    Added additional symmetry handling routines for Gamess case.
                Note this requies self.fullPath for the input file to be set.

    25/01/22    Added groups and zeroInd parameters, and updates & debugged code.

    """

    # 25/01/22 test code & updates http://jake/jupyter/user/paul/doc/tree/ePS/butadiene_2022/epsman_2022/butadiene_rescattering_epsman_1st-attempt_240122.ipynb

    # (1) Stack basic info to dataframe
    orbPD = pd.DataFrame({'syms':self.data.mosyms[0], 'E':self.data.moenergies[0]})  #.index.rename('Orb')  # This is OK with [0] items, but not sure this is general? Might be spin groups here?

    if not zeroInd:
        orbPD.index += 1 # NOTE +1 to start at 1 (not 0)

    orbPD = orbPD.assign(Occ=lambda x: x['E']<0).assign(OccN=lambda x: x['Occ']*2)  # Crude!
    orbPD['OrbN'] = orbPD.index # Set index as col to ensure it's kept later!

    # (2) Set degen & groups
    fullOcc = orbPD.groupby(groups).sum()['OccN']  # Gives degen occ numbers
    degens = orbPD.groupby(groups).size() # Gives degen directly (as a series), but not sure how to restack to the original...?

    # degens
    if zeroInd:
        orbGrp = np.arange(0,degens.size)
    else:
        orbGrp = np.arange(1,degens.size+1)
    # orbGrp = testStackMI.groupby('E').ngroup()  # This should be good, but only keeps index, not N - more thought required here

    degenDF = pd.DataFrame({'degen':degens, 'iOrbGrp':orbGrp, 'OrbGrpOcc':fullOcc}) # Restack to frame including group indexes - works OK with simple range orbGrp, but missing E indexer?
    orbPD = orbPD.merge(degenDF, on=groups)  # OK, with full DataFrame, flat index

    # (3) Set to multi-index
    orbPD.set_index(['E','iOrbGrp','OrbN'], inplace=True)

    # (4) Summary data - propagate from CCLIB structure for now
    for key in ['metadata', 'nelectrons', 'nmo', 'atomcoords','homos']:
        orbPD.attrs[key] = getattr(self.data, key)

    # (5) Check for point-group, try reading directly from file if missing.
    # 02/02/22 added this functionality.

    if 'symmetry_detected' in orbPD.attrs['metadata'].items():
        orbPD.attrs['PointGroup'] = orbPD.attrs['metadata']['symmetry_detected']

        if 'symmetry_used' in orbPD.attrs['metadata'].items():
            if orbPD.attrs['metadata']['symmetry_used'] is not orbPD.attrs['metadata']['symmetry_detected']:
                print(f"*** Warning (setOrbInfoPD): found two point groups: {orbPD.attrs['metadata']['symmetry_detected']} and {orbPD.attrs['metadata']['symmetry_used']}")
                print(f"*** Setting for 'used' case: {orbPD.attrs['metadata']['symmetry_used']}, set self.orbPD.attrs['PointGroup'] manually to override.")
                orbPD.attrs['PointGroup'] = orbPD.attrs['metadata']['symmetry_used']

    #
    # if 'PointGroup' not in orbPD.attrs.items():
    #     self.fullPath.as_posix()

    # Read PG & subspaces from Gamess file - MAY WANT TO MOVE TO SEPARATE PARSING FUNCTION?
    if orbPD.attrs['metadata']['package'] is 'GAMESS':
        # This will get PG info from the setup section - probably better & includes subspace... this should map directly to ePS labels?
        startPhrase = 'THE POINT GROUP IS'
        endPhrase = '..... DONE SETTING UP THE RUN .....' # 'ATOMIC BASIS SET\n'  # SHOULD NOW BE FIXED WITH lstrip
        # verbose = 2

        (lineList, dumpSegs) = fileParse(self.fullPath.as_posix(), startPhrase, endPhrase, verbose = False)  # self.verbose) # For testing only?

        # Parse PG info from 1st line of output
        segs = dumpSegs[0][0][2].strip().split(',')

        PG = {}  # Set dict to handle all PG info
        PG['Label'] = {}
        for n, line in enumerate(segs):
            # Get PG label from 1st item
            if n == 0:
                PG['Label']['Name'] = parseLineTokens(segs[0])[-1]   # PG label, e.g. DNH

            # Get any other PG attribs
            else:
                item = parseLineTokens(segs[n])
                PG['Label'][item[0]]=item[1]

        # Parse additional group info
        # In particular subspace dimensions, e.g. ' A1G =   13     A1U =    0     B1G =    0     B1U =    0     A2G =    0\n'

        # Reset data to avoid extra lines
        startPhrase = 'DIMENSIONS OF THE SYMMETRY SUBSPACES'
        (lineList, dumpSegs) = fileParse(self.fullPath.as_posix(), startPhrase, endPhrase, verbose = self.verbose)

        PG['Dimensions'] = {}
        PG['Members'] = []

        for item in dumpSegs[0][1:]:
            lineList = parseLineTokens(item[-1].strip())

            if lineList:
                PG['Dimensions'].update({k:lineList[2*n+1] for n,k in enumerate(lineList[0:-1:2])})

                PG['Members'].extend(lineList[0:-1:2])

        orbPD.attrs['PG'] = PG


    # Check OccN & HOMO OK
    if orbPD['OccN'].sum() != orbPD.attrs['nelectrons']:
        print(f"*** Warning (setOrbInfoPD): assigned {orbPD['OccN'].sum()} electrons but should be {orbPD.attrs['nelectrons']} - check and set in self.orbPD.")

    # Set to self
    self.orbPD = orbPD

    # 22/01/22 update - just reformat orbPD instead of col setting? Am I missing something now...?
    orbGrps =  orbPD.reset_index().set_index('iOrbGrp')  # .drop_duplicates(keep='first')  # Note drop_duplicates not for index values - this may keep multiple entries per iOrbGrp
    self.orbGrps = orbGrps[~orbGrps.index.duplicated()]   # Drop duplicates by INDEX

    if self.verbose:
        print("*** Set orbPD data to self.orbPD, set group data to self.orbGrps\n")
        self.orbInfoSummary()




def orbInfoSummary(self, showSummary = True, showFull = True, showGrouped = True):
    """
    Print info from self.orbPD (via CCLIB). If not set, run self.setOrbInfoPD() first.

    See also ep.jobSummary() and ep.getOrbInfo() for similar case from ePS output files.

    """
    if showSummary:
        print(f"Found Point Group: {self.orbPD.attrs['PG']['Label']}.")
        print(f"Found {self.orbPD.index.get_level_values('OrbN').nunique()} orbitals, in {self.orbPD.index.get_level_values('iOrbGrp').nunique()} groups.")
        print(f"Found {self.orbPD['syms'].nunique()} orb symmetries: {self.orbPD['syms'].unique()}")
        print(f"Assigned {self.orbPD['OccN'].sum()} electrons to {self.orbPD[self.orbPD['Occ']].index.get_level_values('OrbN').nunique()} orbitals/{self.orbPD[self.orbPD['Occ']].index.get_level_values('iOrbGrp').nunique()} orbital groups.")

    if showFull:
        print("\nOccupied orbitals table:")
        display(self.orbPD[self.orbPD['Occ']])  # Should add notebook check routine here.

    if showGrouped:
        print("\nOccupied orbitals by group:")
        display(self.orbGrps[self.orbGrps['Occ']])  # Should add notebook check routine here.
