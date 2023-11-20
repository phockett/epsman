"""
ESmulti class - builds on ESgamess for multiple electronic structure cases, e.g. geometry scans.

24/02/22    Revisiting & wrapping for epsman.

29/03/21    Dev work, see ESgamess_tests_dev_290321_inc_ESmulti-dev.ipynb

TODO:

- Incorporate/wrap ePS job writing here too - may just want to set & build via ESjob with multiple input file cases rather than wrap whole class?
- Alternatively, make generic multi-job wrapper in a similar manner, i.e. take ref class object and loop over specified vars?

"""

from copy import deepcopy
import numpy as np
from epsman.elecStructure.gamess import ESgamess
    

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
                 use_rungms = False, fileBase = None):
        """
        Set geometry & run Gamess calculation for a set of atom positions or bond length settings.

        Notes
        -----

        - This uses self.ESbase as the reference job, so set global options there first via self.setGamess()
        - Currently only supports one of positions or bonds.
        - NEED TO WORK OUT BEST METHOD HERE!!!

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

        for k, geom in geomDict.items():

            self.geomScan[k] = {}
            self.geomScan[k]['mol'] = deepcopy(self.ESbase)  # Copy ref case

            # Update job note & file
            self.geomScan[k]['mol'].params['extra']['job'] += f', geom scan item {k}'
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

        self.geomScan['summary'] = {'fileList':fileOut,
                                    'E':Eout,
                                    'geom':geomDict}
