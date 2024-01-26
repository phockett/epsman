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


    def runGeomScan(self, positionsList = None, positionsDict = None,
                    bondDict = None, keys = None,
                    use_rungms = False, fileBase = None, zeroFill=True):
        """
        Set geometry & run Gamess calculation for a set of atom positions or bond length settings.
        
        Note either `positionsDict` or `bondDict` must be passed.
        
        Parameters
        ----------
        positionsList : NOT IMPLEMENTED
        
        positionsDict : optional, default = None
            Dictionary of geometries to use, (x,y,z) form.
            Format is as per self.setCoords(), i.e. `{name:{atomInd1:[x,y,z], atomInd2:[x,y,z]...}` (see https://epsman.readthedocs.io/en/latest/demos/ESgamess_class_demo_221123-tidy.html#Manual-coords).
            Where "name" is an arbitrary key, and atomInds correspond to existing atoms in the system. Any atoms not specified will retain their current coords.
            E.g. `coords={0:[0,0,0], 1:[0.7,0,1.0]}` will set positions for atoms 1 and 2.
            
        bondDict : optional, default = None
            Dictionary of geometries to use, bond form.
            Format is as per self.setBondLength(), i.e. `{'Name':{'a1':atomInd1,'a2':atomInd2,'l':bondLength}}` where `a1` and `a2` give the atom indices for atoms defining the bond, and "name" is an arbitrary key.
            E.g. `{'set1':{'a1':0, 'a2':1, 'l':5}, 'set2':{'a1':1, 'a2':2, 'l':2}}`
            
        keys : optional, default = None
            List of keys to use from `positionsDict` or `bondDict`.
            If set, run for only this subset of geometries.
           
        use_rungms : optional, default = False
            Run setting for Gamess wrapper.
            (See https://epsman.readthedocs.io/en/latest/demos/ESgamess_class_demo_221123-tidy.html#pyGamess-wrapper.)
            
        fileBase : optional, default = None
            Base file name stub for Gamess output files.
            If not set, Gamess outputs will not be saved.
            (See https://epsman.readthedocs.io/en/latest/demos/ESgamess_class_demo_221123-tidy.html#Gamess-full-output-and-log-files.)
            
        zeroFill : optional, default = True
            If True, set Eout=np.nan for cases where Eout=0.
            This generally indicates an unconverged Gamess calculation.
            
        

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
            
            if 'details' in positionsDict.keys():
                # Set inputs from file scan, as set by util.readMoldenGeoms()
                # In this case have both 'pd' and 'positionsDict' per item.
                # Use presence of 'details' key to determine format here.
                geomDict = {k:v['positionsDict'] for k,v in positionsDict.items() if k!='details'}
            else:
                geomDict = positionsDict

        elif bondDict is not None:
            bondFlag = True
            geomDict = bondDict

        else:
            print("*** No geoms defined for scan: Either `positionsDict` or `bondDict` must be passed.")
            return 0
            
        # TODO: combined case with itertools?

        # Set output
        # TODO: set proper temp file handling here
        if fileBase is None:
            fileBase = '/tmp/geomScan'

        # If a list of keys is set, subselect from full geomDict
        if keys is not None:
            geomDict = {k:v for k,v in geomDict.items() if k in keys}
            

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
        
        xaxis = list(self.geomScan['summary']['geom'].keys())
        
        plt.plot(xaxis,self.geomScan['summary']['E'],'x--')
        plt.xlabel("Geom setting")
        plt.ylabel("Eh")
        plt.title("Geom scan E outputs")
        
        # For int case force axis ticks & labels
        if type(xaxis[0]) is int:
            plt.gca().axes.set_xticks(xaxis)
            plt.gca().axes.set_xticklabels(xaxis)