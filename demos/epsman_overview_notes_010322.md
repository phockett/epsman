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

# ePSman Overview

ePSman provides tools for setting up, running & packaging ePolyScat (ePS) jobs. For a general overview of the ecosystem, see [the ePSdata intro page](https://phockett.github.io/ePSdata/about.html).

ePSman is designed for:

- Client - host architecture, with the remote host machine running the jobs & storing most of the files. 
   - [Fabric](https://docs.fabfile.org/en/2.5/index.html) provides the framework for this.
   - Jobs are setup and managed from the client machine, with some basic file management also implemented.
   - The host machine runs ePS, as well as some other local tasks such as archive building.

- To be run from a Jupyter Notebook, which provides an easy interface for interactive parts, and for keeping notes on progress & results.

Docs: https://epsman.readthedocs.io

## Features

- Manage electronic structure files
  - Basics implemented for Gamess & Molden file handling, built [on CCLIB](http://cclib.github.io/), in ESjob class.
  - To do: 
     - Gamess setup & run using [pyGamess](https://github.com/kzfm/pygamess), see [the class demo "ePSman ESgamess class notes & demos: molecule and Gamess job handling class"](https://epsman.readthedocs.io/en/latest/demos/ESgamess_class_demo_300321.html).
     - Handling for multiple input files, e.g. bond-length scans. (See, e.g. http://jake/jupyter/user/paul/doc/tree/notebooks/epsman_tests/gamess-dev/ESgamess_tests_dev_290321.ipynb, and probably other places.)
- Manage input files & directory structure.
- Create ePS jobs (most recent example http://jake/jupyter/user/paul/doc/tree/ePS/OCS/epsman2021/OCS_ePS_ePSman_dev_HOMO_Jake_010621-v5-HOMOrun.ipynb ?)
  - Molecule & batch job structure.
     - Output files stored in `base/mol/batch`, where `base` is the defined working directory (defaults to ~/ePS).
     - Supplementary output to `base/mol/batch/output`, where `output` is per file type (`idy`, `wavefn` etc).
  - Multi-E job chuncking for large runs.
  - Basic or wavefunction job creation.
  - To do:
     - Machine-specific defaults via settings file (paritally implemented).
     - Better/automated symmetry handling (currently set manually).
     - More versatile job structure (?).
     - Checkpoint files.
     - Template notebooks.
   
   
## TODO

---
- Run ePS jobs. NEEDS FIXING.
- Post-processing
  - Batch processing of jobs via ePSproc + template notebooks.
  - Package repo & upload to repository (Zenodo).
  - Upload notebooks to web (ePSdata).

---

+++

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
