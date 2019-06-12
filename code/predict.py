from common.commons import *
import lightgbm as light
from sklearn.metrics import confusion_matrix,accuracy_score, roc_curve, auc
from sklearn import metrics
FEATURE_DIR = os.environ["FEATURE_DIR"]
CLASSIFIER_DIR = os.environ["CLASSIFIER_DIR"]
PREDICTION_DIR = os.environ["PREDICTION_DIR"]
DATASET_DIR = os.environ["DATASET_DIR"]
CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]

import pickle

def convert2FeaturesForValidation(bids,features,dataType,valDF):
    with dask.config.set(scheduler='processes'):
        if(isfile(join(DATASET_DIR,dataType))):
            bids = load_zipped_pickle(join(DATASET_DIR,dataType))

        else:
            save_zipped_pickle(bids, join(DATASET_DIR, dataType))

        aDF = valDF[valDF.bugID.isin(bids)]
        logging.info('end compute')
        aDF.reset_index(inplace=True,drop=True)
        X = aDF[features]
        y, _ = pd.factorize(aDF['answer'], sort=True)
        logging.info('False %d' % Counter(y)[0] )
        logging.info('True %d' % Counter(y)[1])
        bugIDS = aDF['bugID']
        files = aDF['file']
        return X,y,bugIDS,files

def corePredict(Xt,yt,bugIDs,files,mdl,year,model=None,bugName = None):

    try:

        dataTest = Xt
        labelTest = yt

        bugIds = bugIDs
        files = files

        logging.info(len(labelTest))


        logging.info('Load model to predict')
        if model is None:
            model = light.Booster(model_file=join(CLASSIFIER_DIR,mdl))


        logging.info('Start predicting')
        pred_prob = model.predict(dataTest, num_iteration=model.best_iteration)

        false_positive_rate, recall, thresholds = roc_curve(labelTest, pred_prob)
        roc_auc = auc(false_positive_rate, recall)

        print('AUC score:', roc_auc)
        predictBg(pred_prob,model, labelTest,mdl,bugIds,files,year,bugName)


    except Exception as e:
        logging.error(e)
        raise e

import sqlite3
def predictBg(pred_prob,model, labelTest,mdl,bugIds,files,year, bugName):
        """ Method that runs forever """
        from sklearn.metrics import mean_squared_error
        print(mdl)
        print('The rmse of loaded model\'s prediction is:', mean_squared_error(labelTest, pred_prob) ** 0.5)

        series = [bugIds, files, pd.Series(pred_prob), pd.Series(labelTest)]
        ddf = dd.concat([dd.from_array(c) for c in series], axis=1)
        # name columns
        ddf.columns = ['bugId', 'file', 'pred_prob_1', 'answer']

        df = ddf.compute()
        df['classifier'] = mdl

        print('DF ready start writing to db')

        if not bugName is None:
            mdl = mdl + "_" + bugName

        conn = sqlite3.connect(DATA_PATH + '/' + "allResults"+year+".db")
        curs = conn.cursor()

        # curs.execute("PRAGMA synchronous = OFF")
        # curs.execute("BEGIN TRANSACTION")
        df.to_sql("result", conn, if_exists="append", index=False)
        # conn.commit()
        conn.close()


def printResults(y_pred, y_test, mdl):
    logging.info(82 * '_')
    predictions = [round(value) for value in y_pred]#[:,1]]
    # evaluate predictions
    line0 = '# Predictions(90%-10%): ' + str(len(predictions))
    accuracy = accuracy_score(y_test, predictions)
    line1 = ("Accuracy: %.2f%%" % (accuracy * 100.0))
    line2 = (pd.crosstab(index=y_test, columns=np.asarray(predictions), rownames=['actual'], colnames=['predicted']))
    line3 = (metrics.classification_report(predictions, y_test))
    with open(join(CODE_PATH, "config.json"), "r") as paramsFile:
        params = paramsFile.read()


    with open(join(PREDICTION_DIR,'metrics_'+mdl),'a') as f:
        f.write('\n')
        f.write(str(82 * '_'))
        f.write('\n')
        f.write(params)
        f.write('\n')
        f.write(line0)
        f.write('\n')
        f.write(str(line1))
        f.write('\n')
        f.write(str(line2))
        f.write('\n')
        f.write(str(line3))


