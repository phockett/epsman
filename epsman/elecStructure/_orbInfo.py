"""
Methods for converting electronic structure (ES) file info <> ePS job info.

For use with ESclass.EShandler()

10/06/21: initial version.

"""


import pandas as pd
import numpy as np

#************* Functions for getting orb info: these will likely want to go into EShandler class.
def setOrbInfoPD(self):
    """
    Set info to self.orbPD, from electronic structure file (via CCLIB).

    See also ep.jobSummary() and ep.getOrbInfo() for similar case from ePS output files.

    """


    # (1) Stack basic info to dataframe
    orbPD = pd.DataFrame({'syms':self.data.mosyms[0], 'E':self.data.moenergies[0]})  #.index.rename('Orb')  # This is OK with [0] items, but not sure this is general? Might be spin groups here?
    orbPD = orbPD.assign(Occ=lambda x: x['E']<0).assign(OccN=lambda x: x['Occ']*2)  # Crude!
    # testStack['OccN'] = testStack.where(testStack['Occ']==True,2,0)
    # testStack = testStack.index.rename('Orb')
    # testStack.index.rename('OrbN', inplace=True)
    orbPD['OrbN'] = orbPD.index  # Set index as col to ensure it's kept later!

    # (2) Set degen & groups

    fullOcc = orbPD.groupby('E').sum()['OccN']  # Gives degen occ numbers
    degens = orbPD.groupby('E').size() # Gives degen directly (as a series), but not sure how to restack to the original...?
    # degens
    orbGrp = np.arange(0,degens.size)
    # orbGrp = testStackMI.groupby('E').ngroup()  # This should be good, but only keeps index, not N - more thought required here

    degenDF = pd.DataFrame({'degen':degens, 'iOrbGrp':orbGrp, 'OrbGrpOcc':fullOcc}) # Restack to frame including group indexes - works OK with simple range orbGrp, but missing E indexer?
    degenDF.index.rename('E', inplace=True)

    # .groupby("B").filter(lambda x: len(x) > 2, dropna=False)

    # testStackMI['iOrbGrp'] = testStackMI.groupby('E').sum()['OccN']
    # testStackMI['iOrbGrp'] =

    # testStackMI['degens'] = degens  # Just sets as NaNs, not picking up index?
    # testStackMI.merge(degens.rename('degens'), on='E')  # This is OK with degens as a Series, and duplicates data correctly. Seems to drop multi-index though? Just do that later instead!
    orbPD = orbPD.merge(degenDF, on='E')  # OK, with full DataFrame, flat index
    # testStackMI.merge(degenDF, on='E', how='left')[0:20]


    # (3) Set to multi-index
    orbPD.set_index(['E','iOrbGrp','OrbN'], inplace=True)


    # (4) Summary data - propagate from CCLIB structure for now
    for key in ['metadata', 'nelectrons', 'nmo', 'atomcoords','homos']:
        orbPD.attrs[key] = getattr(self.data, key)


    # Check OccN & HOMO OK
    if orbPD['OccN'].sum() != orbPD.attrs['nelectrons']:
        print(f"*** Warning: assigned {orbPD['OccN'].sum()} electrons but should be {orbPD.attrs['nelectrons']} - check and set in self.orbPD.")

    # Set to self
    self.orbPD = orbPD

#     degenDF['syms'] = orbPD.groupby('E')['syms']  # This currently fails - need to use some filter/droplevel logic here?
    indsUn = ~orbPD.index.get_level_values('E').duplicated(keep='first')  # Set indexer to unique sets
    degenDF['syms'] = orbPD[indsUn]['syms'].droplevel(['OrbN','iOrbGrp'])  # Bit circular, but works OK
    degenDF['Occ'] = orbPD[indsUn]['Occ'].droplevel(['OrbN','iOrbGrp'])  # Bit circular, but works OK
    self.orbGrps = degenDF.set_index(['iOrbGrp'], append=True).reset_index(level='E')  # Set separate degen table for more direct use for ePS inputs, reindex to orbGrp index only.

    if self.verbose:
        print("*** Set orbPD data to self.orbPD, set group data to self.orbGrps\n")
        self.orbInfoSummary()




def orbInfoSummary(self, showSummary = True, showFull = True, showGrouped = True):
    """
    Print info from self.orbPD (via CCLIB). If not set, run self.setOrbInfoPD() first.

    See also ep.jobSummary() and ep.getOrbInfo() for similar case from ePS output files.

    """
    if showSummary:
        print(f"Found {self.orbPD.index.get_level_values('OrbN').nunique()} orbitals, in {self.orbPD.index.get_level_values('iOrbGrp').nunique()} groups.")
        print(f"Found {self.orbPD['syms'].nunique()} orb symmetries: {self.orbPD['syms'].unique()}")
        print(f"Assigned {self.orbPD['OccN'].sum()} electrons to {self.orbPD[self.orbPD['Occ']].index.get_level_values('OrbN').nunique()} orbitals/{self.orbPD[self.orbPD['Occ']].index.get_level_values('iOrbGrp').nunique()} orbital groups.")

    if showFull:
        print("\nOccupied orbitals table:")
        display(self.orbPD[self.orbPD['Occ']])  # Should add notebook check routine here.

    if showGrouped:
        print("\nOccupied orbitals by group:")
        display(self.orbGrps[self.orbGrps['Occ']])  # Should add notebook check routine here.
