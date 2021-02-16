#!/bin/sh

# Basic script to run full ePSdata site build & upload.
# Pass webDir at command line, corresponds to root epsdata dir (with Sphinx makefile)

# Run python code for RST build.

# Run Sphinx
# *** FULL REBUILD, run from webDir root
# Will make docs in buildTmp, then copy HTML to docs
# webDir = $1
# cd webDir
# conda activate webDev
echo Building web in $1
cd $1

make clean
make html

# Rebuild docs
rm docs -r
cp buildTmp/html/ docs -r
cp source/_figs docs/_figs -r  # May not be necessary...?
touch docs/.nojekyll  # For Github pages

#
# <Copy _files dir?>

# Upload to Github
git add -A
git commit -m "Rebuilt HTML"
# git push
# Currently working OK on Bemo at command line, but may need to set up ssh etc. on other machines.
# See https://kbroman.org/github_tutorial/pages/first_time.html
# git push fails with permissions error from Fabric.
