#!/bin/bash

# Attempt at writing a shell script for ePS input, based on RLL's example job, scripting for CZB's alignment code, and some interwebbing
# Standardize ePS input by looping over energies & symmetry groups, and dumping matrix elements to file.
# For each job need to set:
#	(a) Energies
#	(b) Enviromental settings
#	(c) Specific molecule & ionization settings
#
# Remaining code loops over energies & symmetries and builds input.
#
# 30/09/19  Updated version for use with separate job defn. files.
# 29/09/19	EDCS test version. Crude replication of ePS test13, plus multi-E assignment from command line.
#						Running via python scipt for E list generation.
#
# 19/08/15	_decimal version, uses gc to allow for decimal calculations for energy loop
# 13/08/15

# Template file details
template='Basic photoionization template, 30/09/19'

#*******************************************************************************************
# (a) Set E range (also used for job title, so set first)
#
Emin=$1		# Set from passed variables.
Emax=$2
Estep=$3


#*******************************************************************************************
# (b) Environment settings
#

# Machine-specific settings.
# Note script location hard-coded here to allow for use of source (otherwise needs to be in working dir)
scrdir=/home/paul/ePS_stuff/scripts2019
source $scrdir/machine.conf

# (c) Molecule (job) settings
# Load molecule & job defns. from file.
# Again, not sure how to do this without setting path first... easiest just to pass conf file path here (relative to working dir)?
jobConfFile=$4
#source $wrkdir/$jobConfFile  # Relative to wrkdir
source $jobConfFile   # Full path - maybe better to aviod ambiguities on remote runs.

# file=$job\_E$Emin\-$Emax\eV\_$orb
# file=$job\_E$Emin\-$Emax\_$Estep\eV
# file=$job\_E$Emin\_$Estep\_$Emax\eV
file=$job.$orb\_E$Emin\_$Estep\_$Emax\eV

# Echo to screen
echo %%%%%%%%
echo Job: $job
echo File: $file
echo Orb: $orb
echo Note: $note
#echo %%%%%%%%

dirBase=$wrkdir/$mol/$job
jobDir=$dirBase/$orb
idyDir=$jobDir/idy

runDate=$(date)

# Make working directories
echo %%%%%%%%
echo Base directory: $dirBase
echo Job dir: $jobDir
echo MatE dir: $idyDir
#echo %%%%%%%%

mkdir $dirBase
mkdir $jobDir
mkdir $idyDir

#*******************************************************************************************
# BUILD INPUT
#

# Loop over energies, set in an array for use later
Earray=$Emin
En=1
imax=$(bc<<<"($Emax-$Emin)/$Estep+1")	# Add 1 to ensure Emin gets used (for single energy runs)
for ((i=1; $i<$imax; i++));	# Use bc for decimals
do
	c=$(bc<<<"$Emin+$i*$Estep")
	Earray+=" $c"
	En=$((En+1))
done

echo %%%%%%%%
echo Writing $En energies to job file:
echo $file
echo %%%%%%%%

# Loop over symmetries & construct output
m=0
SymmString=$'\n'
DumpIdyString=$'\n'
GetCroString="GetCro "

for item in "${Ssym[@]}"
do
	SymmString+="# Symmetries set $((m+1)), S${Ssym[m]}C${Csym[m]}"$'\n'
	SymmString+="ScatSym '${Ssym[m]}' # Scattering symmetry of total final state"$'\n'
	SymmString+="ScatContSym '${Csym[m]}' # Scattering symmetry of continuum electron"$'\n'
	SymmString+="FileName 'MatrixElements' '$idyDir/${mol}S${Ssym[m]}C${Csym[m]}.idy' 'REWIND'"$'\n'$'\n'
	SymmString+="GenFormPhIon"$'\n'
	SymmString+="DipoleOp"$'\n'
	SymmString+="GetPot"$'\n'
	SymmString+="PhIon"$'\n'
	SymmString+="GetCro"$'\n\n\n'

	GetCroString+=$'\n'"'$idyDir/${mol}S${Ssym[m]}C${Csym[m]}.idy'"

	DumpIdyString+="# S${Ssym[m]}C${Csym[m]}"$'\n'
	for ((i=0; $i<$imax; i++));	# Use bc for decimals
	do
		c=$(bc<<<"$Emin+$i*$Estep")
		DumpIdyString+="DumpIdy '$idyDir/${mol}S${Ssym[m]}C${Csym[m]}.idy' $c "$'\n'
	done
	DumpIdyString+=$'\n\n\n'

	m=$((m+1))
done

# Heredoc, use to create direct output stream to file - thought this would be easier than printf, although maybe not considering looping...
cat > $jobDir/$file.inp <<eoi

# ePS $mol, batch $job, orbital $orb
# $note
# E=$Emin:$Estep:$Emax ($En points)
#
# File date: $runDate
# Running on: $machine
#
# Configuration: $jobConfFile
# Template: $template

LMax  30     # maximum l to be used for wave functions
LMaxA 12
EMax  50.    # EMax, maximum asymptotic energy in eV
IPot $IP
FegeEng $IP   # Energy correction used in the fege potential

# ECenter $ECenter  # Optional command for single-centre expansion

VCorr 'PZ'

# Set initial and final orbital occupations
OrbOccInit
  $OrbOccInit
OrbOcc        # occupation of the orbital groups of target
  $OrbOccTarget
$CnvOrbSel

# Set electronic structure to read in
Convert '$elecStructure' 'molden2006'
GetBlms
ExpOrb

# Set global symmetries & spins
SpinDeg $SpinDeg        	# Spin degeneracy of the total scattering state (=1 singlet)
TargSym '$TargSym'      		# Symmetry of the target state
TargSpinDeg $TargSpinDeg    # Target spin degeneracy
InitSym '$InitSym'      		# Initial state symmetry
InitSpinDeg $InitSpinDeg    # Initial state spin degeneracy'

# Set energies
ScatEng $Earray

#*** Scat - set final state symmetries & do scattering calc. for each set

${SymmString}

#*** Final GetCro (all symmetries)

${GetCroString}

#*** DumpIdy, all symmetries

${DumpIdyString}

#*** END OF JOB

eoi

cp $jobDir/$file.inp $wrkdir/jobs		# Copy to jobs folder ready to run
