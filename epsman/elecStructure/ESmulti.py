"""
ESmulti class - builds on ESgamess for multiple electronic structure cases, e.g. geometry scans.

24/01/24    And revisiting again!
            Added basic plotE() method.

24/02/22    Revisiting & wrapping for epsman.

29/03/21    Dev work, see ESgamess_tests_dev_290321_inc_ESmulti-dev.ipynb

TODO:

- Incorporate/wrap ePS job writing here too - may just want to set & build via ESjob with multiple input file cases rather than wrap whole class?
- Alternatively, make generic multi-job wrapper in a similar manner, i.e. take ref class object and loop over specified vars?

"""

from copy import deepcopy
import numpy as np
from epsman.elecStructure.gamess import ESgamess

pdFlag=False
try:
    import pandas as pd
    pdFlag=True
except ImportError:
    print("*** Pandas not available, fancy tabulated data display will not be available.")


import matplotlib.pyplot as plt
import numpy as np


class ESmulti():
    """
    Class to wrap multiple ESgamess objects for, e.g., bond scans etc.

    24/02/22    Initial commit from 2021 dev work - currently still very basic/in progress.

    """

#     from epsman.elecStructure.gamess import ESgamess

    # Init as per single ESgamess instance
    # Default to building job
    def __init__(self, ESbase = None, buildES = True, **kwargs):

        # Set from existing class object, or init.
        if ESbase is None:
            self.ESbase = ESgamess(buildES = buildES, **kwargs)
        else:
            self.ESbase = ESbase

        # Set jobs as a dict?
#         self.ESdict = {0: ESgamess(**kwargs)}

        # Additional setup
#         self.ESbase.rotateFrame()

    def setGamess(self, **kwargs):
        """Set ref case options in self.ESbase"""

        self.ESbase.setGamess(**kwargs)


    def runGeomScan(self, positionsList = None, positionsDict = None, bondDict = None,
                 use_rungms = False, fileBase = None, zeroFill=True):
        """
        Set geometry & run Gamess calculation for a set of atom positions or bond length settings.

        Notes
        -----

        - This uses self.ESbase as the reference job, so set global options there first via self.setGamess()
        - Currently only supports one of positions or bonds.
        - NEED TO WORK OUT BEST METHOD HERE!!!
        - zeroFill for E=0 results? Now implement to set as np.nan.

        """

        #*** Check inputs
        posFlag = False
        bondFlag = False

        if positionsDict is not None:
            posFlag = True
            geomDict = positionsDict

        if bondDict is not None:
            bondFlag = True
            geomDict = bondDict

        # TODO: combined case with itertools?

        # Set output
        # TODO: set proper temp file handling here
        if fileBase is None:
            fileBase = '/tmp/geomScan'


        #*** Loop over specified geometries
        self.geomScan = {}
        fileOut =[]
        Eout = []
        Ezeros = []
        
        Npoints = len(geomDict)
        print(f"*** Running geometry scan for {Npoints} points.")
        Ngeom = 0
        for k, geom in geomDict.items():
            Ngeom += 1
            print(f"\n*** Running geom {Ngeom}/{Npoints}.")
            
            self.geomScan[k] = {}
            self.geomScan[k]['mol'] = deepcopy(self.ESbase)  # Copy ref case

            # Update job note & file
            if self.geomScan[k]['mol'].params['extra']['job'] is not None:
                self.geomScan[k]['mol'].params['extra']['job'] += f', geom scan item {k}'
            else:
                self.geomScan[k]['mol'].params['extra']['job'] = f'Geom scan item {k}'
                
            self.geomScan[k]['fileOut'] = f'{fileBase}_{k}.out'
            fileOut.append(self.geomScan[k]['fileOut'])

            if posFlag:
                self.geomScan[k]['mol'].setCoords(geom)

            if bondFlag:
                self.geomScan[k]['mol'].setBondLength({k:geom})

#             self.geomScan[k]['mol'].setGamess()
#  For use_rungms option need to set mol.g.rungms = mol.g.gamess_path + '/rungms'
#             self.geomScan[k]['mol'].runGamess(runType = 'energy', fileOut = fileOut[-1], use_rungms=True)
            self.geomScan[k]['mol'].runGamess(runType = 'energy', fileOut = fileOut[-1], use_rungms=use_rungms)
            Eout.append(self.geomScan[k]['mol'].mol.GetDoubleProp("total_energy")) # Log energy
            
            # Basic handling for E=0 case, set to np.nan if required
            if Eout[-1] == 0:
                Ezeros.append(True)
                
                if zeroFill:
                    Eout[-1] = np.nan
                    
            else:
                Ezeros.append(False)
        
        self.geomScan['summary'] = {'fileList':fileOut,
                                    'E':Eout,
                                    'Ezeros':Ezeros,
                                    'geom':geomDict}
        
        print("\n*** Geom scan completed.")
        
        if sum(Ezeros):
            print(f"*** Warning: found E=0 for {sum(Ezeros)} case(s), calculations may be unconverged. Check self.geomScan['summary']['Ezeros'] for details.")

        if pdFlag:
            pdSummary = pd.DataFrame.from_dict(self.geomScan['summary']['geom']).T
            pdSummary['E']= self.geomScan['summary']['E'] 
            
            self.geomScan['summary']['pd']=pdSummary
            
            if self.ESbase.__notebook__ and self.ESbase.verbose:
                display(self.geomScan['summary']['pd'])
        
        
        self.plotE()
            
        
        
    def plotE(self):
        """Plot E from bondscan (1D only) - very basic."""
        
        plt.plot(self.geomScan['summary']['E'])
        plt.xlabel("Bond setting")
        plt.ylabel("E")