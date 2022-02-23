---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.6
kernelspec:
  display_name: Python [conda env:.conda-epsman-demo]
  language: python
  name: conda-env-.conda-epsman-demo-py
---

# ESjob class - electronic structure file handling & ePS job creation
12/02/22

Demo for basic electronic structure file IO and creation of ePS jobs based on inputs.

- Currently tested for Gamess and Molden IO only.
- Uses [CCLIB on the backend](http://cclib.github.io/), so should be easily extendable to other CCLIB-supported cases.

+++

## Imports

```{code-cell} ipython3
# Import main package
# import epsman as em

# For ePS job creation with electronic structure handling, use elecStructure.ESjob
from epsman.elecStructure.ESjob import ESjob
```

```{code-cell} ipython3
# For testing, set the module path and test file.
import inspect
from pathlib import Path

modDir = Path(inspect.getfile(ESjob)).parent
testFilePath = modDir/'fileTest'  # Default module test files, these are included with Github repo.
```

## Class creation

+++

Basic file handling for Gamess Log files is implemented.

- Setup minimally via ESjob(fileName = electronic structure file).
- If job settings are already set, they will be used, otherwise set full paths here with fileBase = full path.
- This creates an empty base object too, but this can be ignored for electronic structure file handling only.

Further details:

- The file is handled via the an EShandler class object.
- All methods are available as self.esData.method()
- File parsing and conversion is via [CCLIB](https://cclib.github.io), a full list of compatible electronic structure packages & data IO can [be found in the CCLIB docs](https://cclib.github.io/data.html).
- Only [Gamess (US)](https://www.msg.chem.iastate.edu/gamess/) files have been tested so far, which are further converted to [Molden format](https://www.theochem.ru.nl/molden/) for ePS (although recent versions of ePS can also read Gamess files directly).

```{code-cell} ipython3
# Basic file handling for Gamess Log files is implemented.
job = ESjob(fileName = 'xe_SPKrATZP_rel.log', fileBase = testFilePath)

# Note an empty object can also be created.
# job = ESjob()
```

Note the outputs here: 

- `OrbN` is the orbital numbering from the electronic structure file, usually corresponding to doubly-occupied orbitals as given by `OccN`.
- `iOrbGrp` renumbers including degereacies, which matches the internal ordering in ePolyScat. Occupation is given by `OrbGrpOcc`.
- Energies in eV.
- `degen` is the orbital degeneracy.
- `syms` lists the symmetries returned by CCLIB.
- If reading a Gamess file, `Gamess` lists the symmteries in the usual format.
- If a point group was found, `ePS` lists the equivalent ePS symmetry label for the group; the full list can be found at https://epolyscat.droppages.com/SymmetryLabels. Note that this mapping is set by `epsman.sym.convertSyms.convertSymsGamessePS()`, and can be set manually if incorrect. (TO TEST)

Attribs are also stored in the class...

```{code-cell} ipython3
job.elecStructure
```

```{code-cell} ipython3
# The ESclass.EShandler class is used on the backend, and can be accessed as .esData
job.esData
```

```{code-cell} ipython3
# Point group set
job.esData.PG
```

```{code-cell} ipython3
# Point group info - this lists the members with ePolyScat labels
job.esData.PGinfo
```

```{code-cell} ipython3
# Full symmetry mapping details - this lists input symmetries and mapping to ePS labels (currently only Gamess > ePS mapping supported)
job.esData.orbPD.attrs['PGmap']
```

```{code-cell} ipython3
# CCLIB data object is also accessible as .data
job.esData.data
```

+++ {"tags": []}

### Update/change master file

Just set a new file name and/or path.

This may also be required if the `ESjob` class is initialised without a file set.

```{code-cell} ipython3
# If the file doesn't exist an error will be printed.
job.setMasterESfile(fileName = 'xe_SPKrATZP_rel_copy.log')
```

## Molden file creation demo

- This is set by `self.checkLocalESfiles()` 
   - This will check for a Molden version of the file and sync to host (if set).
- A call to `self.esData.writeMoldenFile2006()` directly will write a new Molden file from the Gamess .log file.

```{code-cell} ipython3
:tags: []

# If a Gamess file is set, the molden version will be checked & can be created if missing
# For testing use <github repo>/tests (set in .gitignore)
testPath = modDir.parent.parent/'tests'
testPath.mkdir(exist_ok=True)

# Reset master file to use for testing
job.setMasterESfile(fileName = 'xe_SPKrATZP_rel.log')
```

```{code-cell} ipython3
:tags: []

# Make a copy & test
import shutil
shutil.copy(job.esData.fullPath.as_posix(), (testPath/job.elecStructure).as_posix())

# Set & read new file - note this does not create Molden file
job.setMasterESfile(fileName = job.elecStructure, fileBase = testPath)
```

```{code-cell} ipython3
# self.checkLocalESfiles() will check for Molden file and also sync to host (if set)
job.checkLocalESfiles()
```

```{code-cell} ipython3
# self.esData.write* methods can also be called
job.esData.writeMoldenFile2006()
```

## Create ePolyScat input from Gamess source

The main routine `self.buildePSjob` will attempt to execute all the build steps and, hopefully, produce useful output if it fails.

Minimally this needs an ionization channel defined (this is set according to the `iOrbGrp` numbers defined in the tables above), which will allow local job creation. However, if a host machine is not set, the final steps will fail.

```{code-cell} ipython3
# Test with host not set...
job.buildePSjob(channel = 18)
```

In this example the build fails at file IO, since there is no host or paths defined. The ePSrecords generated can be found in two dictionaries, defining the calculation parameters and molecule settings. (For more on these settings, see the [ePolyScat manual and sample jobs.](https://epolyscat.droppages.com/))

```{code-cell} ipython3
# Global calculation settings
job.esData.ePSglobals
```

```{code-cell} ipython3
# Job settings
job.esData.ePSrecords
```

**Note that the default case sets all possible scattering and continuum symmetries for the point group set, which is not usually what one wants... setting self.symList directly will bypass the automatic setting.**

To override this manually, `self.esData.genSymList()` can be used to generate pairs, or simply pass a list to `job.esData.symList` directly.

```{code-cell} ipython3
# symList holds all (Scattering, Continuum) pairs as tuples.
# This can be set from lists with genSymList

# TODO: fix self.setSyms for this!
# TODO: add Ssym,Csym options to buildePSjob() method.

job.esData.genSymList(Ssym=['SG','A2G'],Csym=['SG','DG'])
job.esData.symList
```

## Versions

```{code-cell} ipython3
import scooby
scooby.Report(additional=['epsman', 'fabric', 'cclib'])
```

```{code-cell} ipython3
# Check current Git commit for local ePSproc version
from pathlib import Path
import epsman as em

!git -C {Path(em.__file__).parent} branch
!git -C {Path(em.__file__).parent} log --format="%H" -n 1
```

```{code-cell} ipython3
# Check current remote commits
!git ls-remote --heads git://github.com/phockett/epsman
```

```{code-cell} ipython3

```
