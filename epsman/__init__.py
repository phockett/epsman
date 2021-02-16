"""
ePSman Generation functions
---------------------------

16/02/21    Updating packaging and structure.
            - Converted to proper package structure + setup.py.
            - Restrucutred main class.

03/10/19    Converting to class-based version to allow for  transparent param settings.
            Imports moved to __init__.py

02/10/19    First development version, based on old shell scripts (circa 2010, 2015).
            Dev on Bemo, see
                http://localhost:8889/notebooks/python/remote/N2_tests/ePS_input_write_file_tests_290919.ipynb
                http://localhost:8889/notebooks/python/remote/N2_tests/ePSman_dev_021019.ipynb

"""

__version__ = '0.0.1'

# Import master class
from epsman.epsJob import epsJob
