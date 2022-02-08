"""
Functions for defining symmetry lists for various contexts.

08/02/22    v1  Implements ePS & Gamess symmetries.

"""

import re
from urllib.request import urlopen

from epsman._util import parseLineTokens

def getePSsymmetries(url = 'https://epolyscat.droppages.com/SymmetryLabels'):
    """
    Pull symmetries from the ePS manual and set to local data structure.

    TODO: may want to store this locally and just update from web periodically (generally won't change).

    """

    # Get ePS manual & parse
    with urlopen(url) as response:
       html = response.read()

    # Basic parsing using known tags
    df = html.decode("utf-8")  # Force bytes > utf8

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
