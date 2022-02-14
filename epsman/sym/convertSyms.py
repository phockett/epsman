"""
Functions for converting symmetry lists for various contexts.

08/02/22    v1  Implements ePS & Gamess symmetries.

TODO: add manual overrides for user-defined sym mapping.
        This will need to set a mapping dictionary as per dimMapPD.attrs['mappingDict'] output by convertSymsGamessePS().
        And propagte to main orb table as set by setOrbInfoPD(), `orbPD['ePS'] = orbPD['Gamess'].apply(lambda x: orbPD.attrs['PGmap'].attrs['mappingDict'][x]) `

"""
import pandas as pd
import numpy as np

from epsman._util import parseLineDigits
from epsman.sym.defineSyms import getePSsymmetries


# TODO: use passed PG dict or orbPD data?
def setePSPGlabel(PG):
    """
    Get and convert point group labels from Gamess inputs (via orbPD data) to ePS format.

    Parameters
    ----------

    PG : dictionary
        A dictionary defining the point group, as currently set in :py:func:`epsman.elecStructure._orbInfo.setOrbInfoPD` for Gamess input files.
        Minimally passing PG['Label'] = '<Gamess symmetry label>' will also work.
        For N-fold groups, PG['NAXIS'] = N also needs to be defined.

    Returns
    -------

    PG : dictionary, now includes PG['ePSLabel'] for converted label.

    """

    # Set N
    PG['ePSLabel'] = PG['Label']['Name']
    PG['gamessLabel'] = PG['Label']['Name']  # Set short-form Gamess label for display too
#     PG['ePSLabel'][-1] = PG['ePSLabel'][-1].swapcase()

    if 'N' in PG['Label']['Name']:
        PG['gamessLabel'] = PG['gamessLabel'] + ', ' + str(PG['Label']['NAXIS'])

        if int(PG['Label']['NAXIS']) < 8:
            PG['ePSLabel'] = PG['ePSLabel'].replace('N', str(PG['Label']['NAXIS']))

        else:
            PG['ePSLabel'] = PG['ePSLabel'].replace('N', 'A')

    PG['ePSLabel'] = PG['ePSLabel'][:-1] + PG['ePSLabel'][-1].lower()  # Set last char to lower case

    return PG



def convertSymsGamessePS(gamessPGDict, symDict = None, verbose = True):
    """
    Convert from Gamess defined labels to ePS symmetry labels.

    Parameters
    ----------
    gamessPGDict : dict
       Dictionary containing PG info from a Gamess file.
       Currently set at file IO, via :py:func:`epsman.elecStructure._orbInfo.setOrbInfoPD`.
       In that case accessible as `orbPD.attrs['PG']`

    symDict : dict, default = None
        Dictionary contining ePS symmetry definitions.
        If not passed will be created via :py:func:`epsman.sym.defineSyms.getePSsymmetries`.
        (Which uses https://epolyscat.droppages.com/SymmetryLabels)

    Returns
    -------
    dimMapPD : Pandas dataframe
        Dataframe with all dim mappings.

    TODO:

    - Return basic dict form too, needs to be updated with missing vals.
    - Push converted labels back to orbPD?

    """

    # Lookup ePS symmtery list
    if symDict is None:
        symDict = getePSsymmetries()

    # Basic error checks & warnings
    try:
        ePSPG = gamessPGDict['ePSLabel']

    # May want to also try running convertSyms.setePSPGlabel again here? Although already set in setOrbInfoPD.
    except KeyError as e:
        print("***Couldn't find `gamessPGDict['ePSLabel']`, can't convert symmetries to ePS labels.")
        return 0

    try:
        ePSdims = symDict[ePSPG]['ePSlabels']

    except KeyError as e:
        print(f"***Couldn't find PG {ePSPG} in ePS symDict, can't convert symmetries to ePS labels.")
        return 0

    # Dim checks
    # Borrowed from ePSproc.util.misc.checkDims(), may just want to use that directly?
    gamessDims = gamessPGDict['Members']

    sharedDims = list({*ePSdims}&{*gamessDims})  # Intersection, no remapping required for these.

    # Remap missing dims Gamess > ePS labels
    remapDims = list({*gamessDims} - {*sharedDims})

    # This is pretty much manual at this point...
    # Should also be able to generate with libmsym or pull from character tables...?
    dimMap = {}
    Edims = ['P','D','F','G']  # Mappings for EN cases (only for linear cases, e.g. DAh ?)

    if 'A' in ePSPG:
        for item in remapDims:
            if item.startswith('A1'):
                dimMap[item] = item.replace('A1','S')
            elif item.startswith('E'):
                N = parseLineDigits(item)[0]
                dimMap[item] = item.replace('E' + N, str(Edims[int(N)-1]))
    #         elif item.startswith('E2'):
    #             dimMap[item] = item.replace('E2','D')

    # Add existing mappings
    dimMap.update({k:k for k in sharedDims})

    # Check for any remaining unmapped dims
    ePSextras = list({*ePSdims} - {*dimMap.values()})
    gamessExtras = list({*gamessDims} - {*dimMap.keys()})

    # Push to PD tables for display... and final list/checks

    # 07/02/22 - mostly in place, needs tidying up and consolidate set logic as separate function?

    # pd.DataFrame(pd.Series(dimMap), dtype="category").sort_values(by = 0)  # Sort by data
    dimMapPD = pd.DataFrame(pd.Series(dimMap), dtype="category", columns=['ePS']).sort_index()   #index.sort_values()  #.sort_values(by = 0)  # Sort by data
    dimMapPD = dimMapPD.reset_index().rename(columns = {'index':'Gamess'})
    # dimMapPD = dimMapPD.reset_index().reindex(list(range(1,len(dimMap.keys())+1)))  # NEED to remember how to reset this - this just chops current axis! NOW set below.

    # Update with any missing dims from either input list
    # dimMapPD.append([[' ', item] for item in list({*ePSdims} - {*dimMap.values()})], ignore_index = True)
    if ePSextras:
        dimMapPD = dimMapPD.append(pd.DataFrame([[' ', item] for item in ePSextras], columns=['Gamess','ePS']), ignore_index = True)

    if gamessExtras:
        dimMapPD = dimMapPD.append(pd.DataFrame([[item, ' '] for item in gamessExtras], columns=['Gamess','ePS']), ignore_index = True)

    # Update with Gamess dim sizes for reference (== used dims)
    # May be easier to add above, but this form allows for additional columns later too
    pdDims = pd.DataFrame(pd.Series(gamessPGDict['Dimensions'], name = 'GDims', dtype=int))
    pdDims.index.name = 'Gamess'
    dimMapPD = dimMapPD.merge(pdDims, on = 'Gamess', how='outer')

    # TODO:
    # Check Dims consistent (all initial dims remapped?) and add additional data?

    dimSum = np.array(list(gamessPGDict['Dimensions'].values()), dtype=int).sum()

    if dimSum > int(dimMapPD['GDims'].sum()):
        print(f"***Warning: inconsistent dim sum, some Gamess input dims missing.")

    if len(gamessPGDict['Members']) != len(dimMapPD):
        print(f"***Warning: inconsistent dim mapping, some Gamess or ePS dims unmapped. Check PD table for details.")
        # Just warning, or list dims here...?
        # Should just print values as set earlier?
        # TODO: should also check ePSextras and gamessExtras lists directly?


    dimMapPD.index = dimMapPD.index+1  # Fix index, OK

    # Keep inputs
    dimMapPD.name = 'Sym table'
    dimMapPD.attrs['notes'] = f"Gamess ({gamessPGDict['gamessLabel']})  > ePS ({ePSPG}) dim mapping."
    dimMapPD.attrs['gamessPGDict'] = gamessPGDict
    dimMapPD.attrs['ePSdims'] = ePSdims
    dimMapPD.attrs['PG'] = ePSPG
    dimMapPD.attrs['mappingDict'] = dimMap

    # Set caption for display - this seems to remove attrs? Also breaks DataFrame in some cases.
    # TODO: more style settings, see https://pandas.pydata.org/pandas-docs/stable/user_guide/style.html#Table-Styles
    # attrs = dimMapPD.attrs.copy()
    # dimMapPD = dimMapPD.style.set_caption(dimMapPD.attrs['notes'])
    # dimMapPD.attrs = attrs

    return dimMapPD
