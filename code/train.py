import lightgbm as light

thread = 8

from common.commons import *
import pickle

FEATURE_DIR = os.environ["FEATURE_DIR"]
CLASSIFIER_DIR = os.environ["CLASSIFIER_DIR"]
DATASET_DIR = os.environ["DATASET_DIR"]
CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
PARSED = os.environ["PARSED"]


def casePredict(features,year):
    if(isfile(join(DATA_PATH,'allResults'+year+'.db'))):
        os.remove(join(DATA_PATH ,'allResults'+year+'.db'))

       
    
    validation = listdir(FEATURE_DIR)#load_zipped_pickle(join(CODE_PATH, 'validationDATA_byDate_NoFuture'))

    framesV = []
    for bid in validation:
        # tDF = dd.read_parquet(join(FEATURE_DIR, bid))
        tDF = load_zipped_pickle(join(FEATURE_DIR, bid))
        for f in [features]:
            tDF[f] = tDF[f].astype(float)
        framesV.append(tDF)

    valDF = pd.concat(framesV)

    from predict import convert2FeaturesForValidation
    Xt, yt, bugIDs, files = convert2FeaturesForValidation(validation, features, "validationFinal" + year,valDF)

    from predict import corePredict

    # Xt.fillna(0,inplace=True)
    i = 0
    models = [f for f in listdir(CLASSIFIER_DIR) if f.startswith('final') and f.endswith(year + str(i) + '.model')]
    for model in models:
        logging.info(model)
        corePredict(Xt, yt, bugIDs, files, model, year)  # ,None,validationId)

    import sqlite3
    dbNAme = 'file:' + DATA_PATH + '/' + 'allResults' + year + '.db'  # + '?mode=ro'
    conn = sqlite3.connect(dbNAme, uri=True)
    query = "CREATE INDEX result_bid ON result (bugID);"
    conn.execute(query)
    conn.close()
