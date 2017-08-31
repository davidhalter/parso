#!/usr/bin/env bash
# The script creates a separate folder in build/ and creates tags there, pushes
# them and then uploads the package to PyPI.

set -eu -o pipefail

cd CORRECT_FOLDER

PROJECT_NAME=parso
PROJECT=git-clone
BRANCH=master
FOLDER=build/$PROJECT

cd $FOLDER
git checkout $BRANCH

# Create tag
tag=v$(python -c "import $PROJECT_NAME; print($PROJECT_NAME.__version__)")

master_ref=$(git show-ref -s $BRANCH)
tag_ref=$(git show-ref -s $tag | true)
if [ $tag_ref ]; then
    if [ $tag_ref != $master_ref ]; then
        echo 'Cannot tag something that has already been tagged with another commit.'
        exit 1
    fi
else
    git tag $BRANCH
    git push --tags
fi

# Package and upload to PyPI
rm -rf dist/
python setup.py sdist bdist_wheel
# Maybe do a pip install twine before.
twine upload dist/*
