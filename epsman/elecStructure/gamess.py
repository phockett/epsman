"""
Class for basic handling of Gamess jobs using pyGamess and RDKit as backend.

26/02/21

Libraries:

- `pygamess <https://github.com/kzfm/pygamess>`_ (also `on pypi <https://pypi.org/project/pygamess/>`_)
- `RDKit <https://rdkit.org/docs/index.html>`_

Aims here:

- Wrap pygamess functionality with Fabric for client-host architecture.
- Enable full ePS job pipeline, starting with a Gamess calculation.
- Provide methods for generating ePS jobs with multiple inputs, e.g. bond length scans.

"""

from pygamess import Gamess
from rdkit import Chem
from rdkit.Chem import AllChem


class ESgamess():
    """
    Class to wrap pygamess + epsman functionality.

    Basic Gamess job setup and handling from `pygamess docs <https://github.com/kzfm/pygamess#basic-usage>`_, with `RDKit <https://rdkit.org/docs/index.html>`_ on the backend.
    """


    def __init__(self, smiles = None):

        # Setup molecule
        self.smiles = smiles

        self.smilesMolecule()


    def smilesMolecule(self):
        """Generate molecule from smiles following pygames docs examples"""

        if self.smiles is not None:

            self.mol = Chem.MolFromSmiles(self.smiles)
            self.mol = Chem.AddHs(self.mol)

            self.mol_with_atom_index()

        else:
            pass


    def mol_with_atom_index(self):
        """
        Display molecule including atom indexes.

        Adapted from the RDKit cookbook: https://www.rdkit.org/docs/Cookbook.html
        """

        for atom in self.mol.GetAtoms():
            atom.SetAtomMapNum(atom.GetIdx())
        # return mol

        # TODO: add disply checking functionality.


    def setBondLength(self, bonds = None):
        """
        Basic wrapper for AllChem.SetBondLength

        Pass dictionary with items giving atom1, atom2 and the bond length to set.
        E.g. bonds = {'CCBond':{'a1':0, 'a2':1, 'l':10}}
        """

        if bonds is not None:
            for bond in bonds.items():
                AllChem.SetBondLength(self.mol.GetConformer(),bond['a1'],bond['a2'],bond['l'])
