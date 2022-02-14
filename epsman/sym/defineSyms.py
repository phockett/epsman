"""
Functions for defining symmetry lists for various contexts.

08/02/22    v1  Implements ePS & Gamess symmetries.

"""

import re
from urllib.request import urlopen
from pathlib import Path

from epsman._util import parseLineTokens

def getePSsymmetries(url = 'https://epolyscat.droppages.com/SymmetryLabels', localCopy = 'ePS_manual_SymmetryLabels_Feb2022.html'):
    """
    Pull symmetries from the ePS manual and set to local data structure.

    TODO: may want to store this locally and just update from web periodically (generally won't change).

    14/02/22: failing today with `ConnectionResetError: [Errno 104] Connection reset by peer`
    Good argument for keeping a local copy!

    TODO: fix file path, should use inspect? This currently only works if the full path is set explicitly.

    """

    # Get ePS manual & parse
    try:
        with urlopen(url) as response:
           html = response.read()

        df = html.decode("utf-8")  # Force bytes > utf8

    # Get a local copy
    except:
        print(f"***Failed to get {url}, setting symmetry labels from local file.")

        localCopy = Path(localCopy)

        # Try module path if file is missing
        if not localCopy.is_file():
            srcPath = Path(__file__).resolve()
            localCopy = srcPath.parent/localCopy

        if localCopy.is_file():
            with open(localCopy, "r", encoding='utf-8') as f:
                df = f.read()
        else:
            print(f"***Couldn't find local copy at {localCopy}")
            return {}

    # Basic parsing using known tags
    PGs = re.findall(r'<dt>(.*?)</dt>',str(df))  # Get PGs OK, just need to strip outputs
#     syms = re.findall(r'<dd>(.*?)\n',str(df))  # Get PG members - OK except for DAh
    syms = re.findall(r'<dd>(.*?)</dd>',str(df),flags=re.DOTALL)  # Returns empty, UNLESS `flags=re.DOTALL` set to include newlines

    # Build dictionary...
    # Just list & strip re outputs
    symDict = {}
    for n,k in enumerate(PGs):
        # Extract tokens from string.
        # Note additional split to allow for cases with extra () labels.
        symDict[k.strip()] = {}
        symDict[k.strip()]['ePSlabels'] = parseLineTokens(syms[n].split(')')[-1])

        if syms[n].startswith('('):
            symDict[k.strip()]['ePSnote'] = parseLineTokens(syms[n].split(')')[0])
        else:
            symDict[k.strip()]['ePSnote'] = ''

    return symDict


def getGamessSymmetries():
    """
    Return Gamess point group list, currently hard-coded from the manual, see https://www.spec.org/hpc96/docs/RelatedPublications/gamess/input.html

    ```

      GROUP is the Schoenflies symbol of the symmetry group,
      you may choose from
          C1, CS, CI, CN, S2N, CNH, CNV, DN, DNH, DND,
          T, TH, TD, O, OH.

      NAXIS is the order of the highest rotation axis, and
      must be given when the name of the group contains an N.
      For example, "CNV 2" is C2v.

      For linear molecules, choose either CNV or DNH, and enter
      NAXIS as 4.

    ```

    """

    return parseLineTokens("C1, CS, CI, CN, S2N, CNH, CNV, DN, DNH, DND,T, TH, TD, O, OH")
