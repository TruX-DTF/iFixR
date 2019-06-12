
import logging
import sys
import gzip
import numpy as np
from tqdm import tqdm
import shutil
import itertools

# COMMIT_FOLDER = 'commits/'
from os import listdir
import re
import pandas as pd
from os.path import isfile, join, isdir
import pickle as p
from subprocess import Popen, PIPE
from subprocess import CalledProcessError
import pickle as p
import os
import concurrent.futures

import time
import math
import dask.dataframe as dd
from sklearn.model_selection import KFold
import dask
from collections import Counter



sourceCodeColumns = ['packageName', 'className', 'methodNames', 'formalParameter',
                       'methodInvocation', 'memberReference', 'documentation', 'literal', 'rawSource', 'hunks',
                       'commitLogs', 'classNameExt']


def nap():
    time.sleep(1)

def setLogg():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(filename)s:%(funcName)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

def setEnv(args):
    # env = args.env

    # logging.info('Environment: %s',env)

    os.environ["ROOT_DIR"] = args.root
    sys.path.append(args.root)

    import yaml

    with open(join(os.environ["ROOT_DIR"],"config.yml"), 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # for section in cfg:
    #     print(section)
    # print(cfg['mysql'])
    # print(cfg['other'])

    os.environ["JDK7"] = cfg['java']['7home']
    os.environ["JDK8"] = cfg['java']['8home']
    os.environ["D4JHOME"] = cfg['defects4j']['home']


    os.environ["CODE_PATH"] = join(os.environ["ROOT_DIR"],'code/')
    os.environ["DATA_PATH"] = join(os.environ["ROOT_DIR"],'data/')
    os.environ["REPO_PATH"] = join(os.environ["DATA_PATH"], 'gitrepo/')
    os.environ["COMMIT_DFS"]= join(os.environ["DATA_PATH"],'commitsDF/')
    os.environ["SIMI_DIR"]= join(os.environ["DATA_PATH"],'simi/')
    os.environ["DTM_PATH"] = join(os.environ["DATA_PATH"], 'dtm/')
    os.environ["SIMI_SINGLE"] = join(os.environ["DATA_PATH"], 'simiSingle/')
    os.environ["FEATURE_DIR"] = join(os.environ["DATA_PATH"],'features/')
    
    os.environ["BUG_POINT"] = join(os.environ["DATA_PATH"], 'bugPoints/')
    os.environ["DEFECTS4J"] = join(os.environ["DATA_PATH"], 'defects4jdata/')

    os.environ["BUG_REPORT"] = join(os.environ["DATA_PATH"], 'bugReports/')
    os.environ["BUG_REPORT_FEATURES"] = join(os.environ["DATA_PATH"], 'bugReportFeatures/')
    # os.environ["PARSED_DIR"] = join(os.environ["CODE_PATH"], 'parsedFilesSingle/')
    # os.environ["PARSED_M_DIR"] = join(os.environ["CODE_PATH"], 'parsedFilesMulti/')

    os.environ["PARSED"] = join(os.environ["DATA_PATH"], 'parsedPj/')
    os.environ["PARSED_DIR"] = join(os.environ["DATA_PATH"], 'parsedFilesSingle/')
    os.environ["COMMIT_FOLDER"] = join(os.environ["DATA_PATH"], 'commits/')
    os.environ["CLASSIFIER_DIR"] = join(os.environ["DATA_PATH"], 'classifiers/')
    os.environ["PREDICTION_DIR"] = join(os.environ["DATA_PATH"], 'predictions/')
    os.environ["DATASET_DIR"] = join(os.environ["DATA_PATH"], 'datasets/')
    os.environ["REMOTE_PATH"] = '/Volumes/Samsung_T5/data'





    logging.info('ROOT_DIR : %s', os.environ["ROOT_DIR"])
    logging.info('REPO_PATH : %s', os.environ["REPO_PATH"])
    logging.info('CODE_PATH : %s', os.environ["CODE_PATH"])
    logging.info('COMMIT_DFS : %s', os.environ["COMMIT_DFS"])
    # logging.info('SIMI_DIR : %s', os.environ["SIMI_DIR"])
    logging.info('BUG_POINT : %s', os.environ["BUG_POINT"])
    # logging.info('PARSED_DIR : %s', os.environ["PARSED_DIR"])
    logging.info('COMMIT_FOLDER : %s', os.environ["COMMIT_FOLDER"])
    # logging.info('DTM_PATH : %s', os.environ["DTM_PATH"])
    # logging.info('SIMI_SINGLE : %s', os.environ["SIMI_SINGLE"])
    logging.info('FEATURE_DIR : %s', os.environ["FEATURE_DIR"])
    logging.info('CLASSIFIER_DIR : %s', os.environ["CLASSIFIER_DIR"])
    logging.info('PREDICTION_DIR : %s', os.environ["PREDICTION_DIR"])
    logging.info('DATASET_DIR : %s', os.environ["DATASET_DIR"])



def getRun():
    import argparse
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-subject', dest='subject', help='Environment')
    parser.add_argument('-root', dest='root', help='root folder')
    parser.add_argument('-job',dest='job',help='job name')


    args = parser.parse_args()

    if args.root is None or args.job is None:
        parser.print_help()
        raise AttributeError
    return args


def shellCallTemplate(cmd,enc='utf-8'):
    try:
        with Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True,encoding=enc) as p:
            output, errors = p.communicate()
            # print(output)
            if errors:
                m = re.search('unknown revision or path not in the working tree', errors)
                if not m:
                    raise CalledProcessError(errors, '-1')
            output
    except CalledProcessError as e:
        logging.error(errors)
    return output

def shellGitCheckout(cmd,enc='utf-8'):
    try:
        with Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True,encoding=enc) as p:
            output, errors = p.communicate()
            # print(output)
            if errors:
                raise CalledProcessError(errors, '-1')
            output
    except CalledProcessError as e:
        logging.error(errors)
    return output,errors

def save_zipped_pickle(obj, filename, protocol=-1):
    with gzip.open(filename, 'wb') as f:
        p.dump(obj, f, protocol)

def load_zipped_pickle(filename):
    with gzip.open(filename, 'rb') as f:
        loaded_object = p.load(f)
        return loaded_object

def file2path(file):
    count = file.count(".") - 1
    file = file.replace('.', '/', count)
    return file

def isFileInList(file,checkList):
    for f in checkList:
        if f in file:
            return True
    return False
    # [i for i in ansFiles if 'org/fusesource/esb/itests/basic/fabric/EsbFeatureTest.java' in i]

def get_venn_sections(sets):
    """
    Given a list of sets, return a new list of sets with all the possible
    mutually exclusive overlapping combinations of those sets.  Another way
    to think of this is the mutually exclusive sections of a venn diagram
    of the sets.  If the original list has N sets, the returned list will
    have (2**N)-1 sets.

    Parameters
    ----------
    sets : list of set

    Returns
    -------
    combinations : list of tuple
        tag : str
            Binary string representing which sets are included / excluded in
            the combination.
        set : set
            The set formed by the overlapping input sets.
    """
    num_combinations = 2 ** len(sets)
    bit_flags = [2 ** n for n in range(len(sets))]
    flags_zip_sets = [z for z in zip(bit_flags, sets)]

    #combo_sets = []
    combo_sets = dict()
    for bits in range(num_combinations - 1, 0, -1):
        include_sets = [s for flag, s in flags_zip_sets if bits & flag]
        exclude_sets = [s for flag, s in flags_zip_sets if not bits & flag]
        combo = set.intersection(*include_sets)
        combo = set.difference(combo, *exclude_sets)
        tag = ''.join([str(int((bits & flag) > 0)) for flag in bit_flags])
        #combo_sets.append((tag, combo))
        combo_sets[tag] = combo
    return combo_sets

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def RR_XGB(x,ao,column):
    if x[ao] == 1:
        return (1.0 / (x[column]))
    elif pd.isnull(x[ao]):
        return None
    else:
        return 0

def parallelRunNo(coreFun,elements,*args):
    with concurrent.futures.ProcessPoolExecutor(max_workers=int(os.cpu_count()/2)) as executor:
        try:
            futures = {executor.submit(coreFun, l,*args): l for l in elements}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    data = future.result()

                except Exception as exc:
                    logging.error('%r generated an exception: %s' % (url, exc))
                    raise
                # else:
                #     print('%r page is %d bytes' % (url, len(data)))
                kwargs = {
                    'total': len(futures),
                    'unit': 'files',
                    'unit_scale': True,
                    'leave': False
                }
                # Print out the progress as tasks complete
                for f in tqdm(concurrent.futures.as_completed(futures), **kwargs):
                    pass
        except Exception as e:
            # logging.error(e)
            executor.shutdown()
            raise

def parallelRun(coreFun,elements,*args):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        try:
            futures = {executor.submit(coreFun, l,*args): l for l in elements}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    data = future.result()

                except Exception as exc:
                    logging.error('%r generated an exception: %s' % (url, exc))
                    raise
                # else:
                #     print('%r page is %d bytes' % (url, len(data)))
                kwargs = {
                    'total': len(futures),
                    'unit': 'files',
                    'unit_scale': True,
                    'leave': False
                }
                # Print out the progress as tasks complete
                for f in tqdm(concurrent.futures.as_completed(futures), **kwargs):
                    pass
        except Exception as e:
            # logging.error(e)
            executor.shutdown()
            raise

def get_class_weights(y):
    counter = Counter(y)
    majority = max(counter.values())
    return  {cls: round(float(majority)/float(count), 2) for cls, count in counter.items()}

import threading
class BackgroundTask(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, model,PATH, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval
        self.model = model
        self.path = PATH

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def run(self):
        """ Method that runs forever """
        self.model.save_model(self.path,
                     num_iteration=self.model.best_iteration)