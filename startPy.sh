#!/usr/bin/env bash
source activate fse19
python3 -m spacy download en_core_web_lg
PYTHONPATH=$1 python3 -u code/launcherSingle.py -root $1 -job $2 -subject $3
# ln -s /Volumes/RAMDisk/gitrepo/ gitrepo
#python -m spacy download en_core_web_lg

