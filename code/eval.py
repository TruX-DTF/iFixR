from common.commons import *

ROOT_DIR = os.environ["ROOT_DIR"]
REPO_PATH = os.environ["REPO_PATH"]
# CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]

COMMIT_DFS = os.environ["COMMIT_DFS"]
BUG_POINT = os.environ["BUG_POINT"]
COMMIT_FOLDER = os.environ["COMMIT_FOLDER"]

FEATURE_DIR = os.environ["FEATURE_DIR"]
PREDICTION_DIR = os.environ["PREDICTION_DIR"]
DATASET_DIR = os.environ["DATASET_DIR"]
SINGLE_PRED = join(DATA_PATH, 'singlePred')
finalC = ['finalintersection',  'finalOnlyBRTracer', 'finalOnlyBugLocator','finalunion','finalOnlyBLUiR','finalBRTracer', 'finalBugLocator','finalBLUiR',
                           'finalAmaLgam', 'finalLocus', 'finalBLIA',
                           'finalOnlyAmaLgam', 'finalOnlyLocus', 'finalnTop', 'finalall', 'finalOnlyBLIA', 'finalmulti','finalmultic']

# finalC = ['finalmulti','finalmultic']
finalC = ['finalmultic']

multiC = ['multiunion', 'multiOnlyBLUiR', 'multiOnlyBRTracer', 'multiintersection', 'multiOnlyBugLocator',
                   'multiOnlyAmaLgam', 'multiOnlyLocus', 'multinTop', 'multiall', 'multiOnlyBLIA', 'multimulti','multimultic']

yearsList = ['2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016']
# yearsList = ['2016']


def evalResults(bid,isMulti =False):


    if isMulti:

        classifiers = multiC
    else:
        classifiers = finalC


    for classifier in classifiers:
        if classifier.startswith('finalmulti') or classifier.startswith('multimulti'):
            if isMulti:
                query = "select * from result where  bugId == '{param}';".format(
                param=bid)
            else:
                query = "select * from result where  bugId == '{param}' and  (  classifier like 'finalOnly%') ;".format(param=bid.strip()) # classifier like 'finalOnly%' or

        else:
            query = "select * from result where  bugId == '{param}' and classifier like '{classi}' ;".format(param=bid,
                                                                                                             classi=classifier + '%')

        l = []
        for year in yearsList:
            dbNAme = 'file:' + DATA_PATH + '/' + 'allResults'+year+'.db' + '?mode=ro'
            conn = sqlite3.connect(dbNAme, uri=True)
            pr = pd.read_sql_query(query, conn)

            l.append(pr)
            conn.close()
        if (len(l)) > 0:
            allRes = pd.concat(l)
            allRes.reset_index(inplace=True)

        if (allRes.empty):
            continue



        if classifier =='finalmultic' or classifier =='multimultic':
            df = evalMulti(allRes)
        else:

            pair = allRes.groupby(['bugId', 'file'])

            meanVal = pair['pred_prob_1'].mean()
            series = []
            idNames = [i for i, j in meanVal.index.values]
            fileNames = [j for i, j in meanVal.index.values]
            answer = pair['answer'].max()
            series.append(idNames)
            series.append(fileNames)
            series.append(meanVal.values.tolist())

            series.append(answer.values.tolist())
            df = pd.DataFrame(series)
            df = df.T


        df.columns = ['bugId', 'file', 'meanPred','answer']
        df['meanPred'] = pd.to_numeric(df['meanPred'], errors='coerce')
        df['meanRankF'] = df.groupby('bugId')['meanPred'].rank(method='first', ascending=0, na_option='keep')

        answer = df.sort_values(by=['meanRankF'])
        SINGLE_PRED = join(DATA_PATH,'singlePred')
        save_zipped_pickle(answer,join(SINGLE_PRED,classifier+"_"+bid))



def evalMulti(allRes):
    from sklearn.preprocessing import minmax_scale
    allRes['test'] = allRes.groupby(['classifier'])['pred_prob_1'].transform(
        lambda x: minmax_scale(x.values))
    pair = allRes.groupby(['bugId', 'file'])
    meanN = pair['test'].mean()
    series = []
    idNames = [i for i, j in meanN.index.values]
    fileNames = [j for i, j in meanN.index.values]
    answer = pair['answer'].max()
    series.append(idNames)
    series.append(fileNames)
    series.append(meanN.values.tolist())
    series.append(answer.values.tolist())
    df = pd.DataFrame(series)
    df = df.T

    return df


def evalBaska(isMulti,ids):
    try:

        if isMulti:

            classifiers = multiC
        else:
            classifiers = finalC

        for classifier in classifiers:
            
            l = []
            for f in [i for i in listdir(SINGLE_PRED) if i.startswith(classifier) and i.replace(classifier+'_','') in ids]:
                pr = load_zipped_pickle(join(SINGLE_PRED,f))
                pr = pr[pr.answer == True]
                l.append(pr)
            if(len(l))>0:
                answer = pd.concat(l)
                answer.reset_index(inplace=True)
            else:
                continue


            answer['AnsOrderF'] = answer.groupby('bugId')['meanRankF'].rank(method='first', ascending=1, na_option='keep')
            answer['APF'] = answer.apply(lambda x: (x['AnsOrderF']) / (x['meanRankF']), axis=1)
            answer['RRF'] = answer.apply(lambda x: RR_XGB(x,'AnsOrderF', 'meanRankF'), axis=1)

            answer['Top1F'] = answer.meanRankF.apply(lambda x: x < 2).astype(int)
            answer['Top10F'] = answer.meanRankF.apply(lambda x: x < 11).astype(int)
            answer['Top50F'] = answer.meanRankF.apply(lambda x: x < 51).astype(int)
            answer['Top100F'] = answer.meanRankF.apply(lambda x: x < 101).astype(int)
            answer['Top200F'] = answer.meanRankF.apply(lambda x: x < 201).astype(int)
            answer['TopAllF'] = answer.meanRankF.apply(lambda x: x < 1001).astype(int)


            TopAllF = answer.groupby('bugId').agg({'TopAllF': 'max'})
            Top200F = answer.groupby('bugId').agg({'Top200F': 'max'})
            Top100F = answer.groupby('bugId').agg({'Top100F': 'max'})
            Top50F = answer.groupby('bugId').agg({'Top50F': 'max'})
            Top10F = answer.groupby('bugId').agg({'Top10F': 'max'})
            Top1F = answer.groupby('bugId').agg({'Top1F': 'max'})

            valMAPF = answer.groupby('bugId')['APF'].mean()
            valMRRF = answer.groupby('bugId')['RRF'].max()
            series = []
            series.append(valMAPF.values)
            series.append(valMRRF.values)
            series.append(Top1F.values)
            series.append(Top10F.values)
            series.append(Top50F.values)
            series.append(Top100F.values)
            series.append(Top200F.values)
            series.append(TopAllF.values)

            idx = valMAPF.index.values
            series.insert(0, idx)
            a = pd.DataFrame(series)
            a = a.T
            a.columns = ['bugID', 'MAP', 'MRR', 'Top1', 'Top10', 'Top50', 'Top100', 'Top200', 'TopAll']
            logging.info("%20s %d %5s %.3f %.3f %d %d %d %d %d %d" % (
                classifier, len(a.bugID.unique()), 'MEANF', a.MAP.mean(), a.MRR.mean(), a.Top1.sum(), a.Top10.sum(),
                a.Top50.sum(), a.Top100.sum(), a.Top200.sum(), a.TopAll.sum()))
    except Exception as err:
        logging.exception()


def newEval(listOfPred):
    CODE_PATH = os.environ["CODE_PATH"]
    validation = load_zipped_pickle(join(CODE_PATH, 'validationDATA_byDate'))

    validation
    newRes = []

    from functools import reduce
    df_merged = reduce(lambda left, right: pd.merge(left, right, on=['bugId', 'file','answer'],
                                                    how='outer'), listOfPred)

    for bid in validation:
        print(bid)
        initMax = None
        best = ''
        bestRes = None

        tem = df_merged.query("bugId == '{0}'".format(bid))

        newRes.append(tem)

    evalResults(newRes)


import sqlite3


def caseMerge(subject):
    print(subject)
    if subject == 'baselineDATA':
        print('nouse')

    else:
        bids = []
        years = yearsList
        for year in years:
            bid = load_zipped_pickle(join(DATASET_DIR, subject+year))
            bids.extend(bid)
            isMulti = False
        logging.info(len(bids))
        evalBaska(isMulti, bids)



def caseEval(subject):

    if not os.path.exists(SINGLE_PRED):
        os.mkdir(SINGLE_PRED)

    if subject == 'baselineDATA':
        # bids = load_zipped_pickle(join(CODE_PATH,subject))
        isMulti = True
    else:

        # years = yearsList
        # for year in years:
        #     logging.info(year)
        bids = load_zipped_pickle(join(DATASET_DIR, subject+yearsList[0]))
        isMulti =False
        parallelRun(evalResults,bids,isMulti)
