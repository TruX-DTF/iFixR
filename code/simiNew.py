
from common.commons import *

from common.preprocessing import *

CODE_PATH = os.environ["CODE_PATH"]
SIMI_SINGLE = os.environ["SIMI_SINGLE"]
SIMI_DIR = os.environ["SIMI_DIR"]
PARSED_DIR = os.environ["PARSED_DIR"]
COMMIT_FOLDER = os.environ["COMMIT_FOLDER"]
DTM_PATH = os.environ["DTM_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
FEATURE_DIR = os.environ["FEATURE_DIR"]


def getBugDTM(bug,source,bugField, sourceField,bugID):

    dataBug = bug[bug[bugField].str.len() > 0]
    dataBug.reset_index(inplace=True)
    corpusBug = dataBug[bugField].values.tolist()

    dataSource = source[source[sourceField].str.len() > 0]
    dataSource.reset_index(inplace=True)
    dataSource = dataSource[['file', sourceField]]
    corpusSource = dataSource[sourceField].values.tolist()

    if(len(dataSource) > 0 and len(dataBug)> 0):

        if(isfile(join(DTM_PATH, bugID, bugID + '_' + sourceField + '.dtm')) and isfile(join(DTM_PATH, bugID, bugID + '_' + sourceField + '.vector'))):
            v = load_zipped_pickle(join(DTM_PATH, bugID, bugID + '_' + sourceField + '.vector'))
            sourceDTM = load_zipped_pickle(join(DTM_PATH, bugID, bugID + '_' + sourceField + '.dtm'))
        else:
            if sourceField == 'documentation' or sourceField == 'rawSource' or sourceField == 'commitLogs':
                preCorpusSource = list(map(preprocessingNL, corpusSource))
                v = calculateTfIdfNLList(preCorpusSource)
                sourceDTM = v.transform(preCorpusSource)
                # dataField[field + 'DTM'] = dataField.apply(getDTMNL, args=(v, preCorpus), axis=1)
            else:
                preCorpusSource = list(map(preprocessingCodeElementsList, corpusSource))
                v = calculateTfIdfNLList(preCorpusSource)
                sourceDTM = v.transform(preCorpusSource)

            save_zipped_pickle(sourceDTM, join(DTM_PATH, bugID, bugID + '_' + sourceField + '.dtm'))
            save_zipped_pickle(v, join(DTM_PATH, bugID, bugID + '_' + sourceField + '.vector'))

        if bugField in ['summary', 'description', 'summaryDescription']:
            preCorpusBug = list(map(preprocessingNL,corpusBug)) #[preprocessingNL(i) for i in corpusBug]
            bugDTM = v.transform(preCorpusBug)
        else:
            preCorpusBug = list(map(preprocessingCodeElementsList,corpusBug))#[preprocessingCodeElementsList(i) for i in corpusBug]
            bugDTM = v.transform(preCorpusBug)

        sourceDTM
        min = sourceDTM.data.min()
        max = sourceDTM.data.max()
        gs = []
        for i in range(sourceDTM.shape[0]):
            gs.append(g(sourceDTM.getrow(i).nnz, min, max))


        series=[]

        series.append(dataSource.file.values.tolist())
        # if sourceField == 'rawSource':
        #     series.append((cosine_similarity(bugDTM, sourceDTM)[0]*gs).tolist())
        # else:
        #     series.append((cosine_similarity(bugDTM, sourceDTM)[0]).tolist())
        series.append((cosine_similarity(bugDTM, sourceDTM)[0]*gs).tolist())
        df = pd.DataFrame(series)
        df = df.T

        df.columns = ['file', bugField + '2' + sourceField]
        df['bugID'] = bugID
        save_zipped_pickle(df, join(SIMI_DIR, bugID,bugField + '2' + sourceField))

def g(x, min, max):
    if  x == 0:
        return np.nan
    elif min == max:
        return np.nan
    else:
        Nx = ( x-min) / (max - min)
        ex = math.exp(-Nx)
        g = 1 / (1 + ex)
        return g


def coreBugReportDTM(sc,bugColumns, sourceColumns):
    bugID = sc.replace('.pickle', '')
    if isfile(join(SIMI_SINGLE, bugID)):
        logging.info('Return %s' % bugID)
    else:

        if 'MATH-' in sc or 'CLOSURE-' in sc or 'LANG-' in sc:
            # bugIDS = load_zipped_pickle(join(CODE_PATH, sc.split('-')[0] + 'BugReportsExport.pickle'))
            bugIDS = load_zipped_pickle(join(DATA_PATH,sc.split('-')[0]+'bugReportsComplete.pickle'))
        else:
            bugIDS = pd.read_pickle(join(CODE_PATH, 'bugReportsNew.pickle'))


        bid = bugIDS.query("bid == '{0}'".format(bugID))

        bid['summaryDescription'] = bid[['summary', 'description']].apply(lambda x: ' '.join(x), axis=1)

        fields = list(itertools.product(bugColumns, sourceColumns))

        dataset = bid.head(1)
        pc = load_zipped_pickle(join(PARSED_DIR, sc))
        if not os.path.exists(join(DTM_PATH, bugID)):
            os.mkdir(join(DTM_PATH, bugID))
        if not os.path.exists(join(SIMI_DIR, bugID)):
            os.mkdir(join(SIMI_DIR, bugID))


        # split2executors(dataset,pc, fields, bugID)

        for field in fields:
            getBugDTM(dataset[['bid',field[0]]],pc[['file',field[1]]], field[0],field[1],bugID)

        simis = listdir(join(SIMI_DIR, bugID))
        simis

        simisLoaded = []
        for df in simis:
            simisLoaded.append(load_zipped_pickle(join(SIMI_DIR, bugID, df)))
        from functools import reduce
        df_merged = reduce(lambda left, right: pd.merge(left, right, on=['bugID', 'file'],
                                                        how='outer'), simisLoaded)

        save_zipped_pickle(df_merged, join(SIMI_SINGLE, bugID))

    # dtm = getBugDTM(dataset[['bugID', 'summary']], pc[['file', 'packageName']], 'summary', 'packageName', bugID)


def caseSimiNew(subject,bugColumns,sourceColumns):
    # if subject in 'MATH-' or subject in 'CLOSURE-' or subject in 'LANG-':
    #     bugIDS = load_zipped_pickle(join(CODE_PATH, subject.replace('-','')+'BugReportsExport.pickle'))
    # else:
    #     bugIDS = pd.read_pickle(join(CODE_PATH, 'bugReportsNew.pickle'))
    
    if not os.path.exists(DTM_PATH):
        os.mkdir(DTM_PATH)
    if not os.path.exists(SIMI_DIR):
        os.mkdir(SIMI_DIR)
    if not os.path.exists(SIMI_SINGLE):
        os.mkdir(SIMI_SINGLE)


        

    if subject == 'ALL':
        sourceCodeDTMs = listdir(PARSED_DIR)
    else:
        sourceCodeDTMs = [f for f in listdir(PARSED_DIR) if f.startswith(subject)]

    # for sc in sourceCodeDTMs:
    #     coreBugReportDTM(sc,bugIDS,bugColumns, sourceColumns)
    parallelRun(coreBugReportDTM,sourceCodeDTMs,bugColumns, sourceColumns)


def simi2Feature(bugID, allFeatures, simiOrderColumns):
    aSIMI = load_zipped_pickle(join(SIMI_SINGLE, bugID))
    logging.info("%s, simi len %d" % (bugID, len(aSIMI)))

    a = load_zipped_pickle(join(DATA_PATH, 'parsedFilesSingle', bugID + '.pickle'))
    answer = a[['file', 'answer']]
    mergedDF = pd.merge(aSIMI, answer, on=['file'])
    if (len(mergedDF[mergedDF['answer'] == True]) > 0):
        logging.info('Saving feature %s', bugID)
        missingColums = set(allFeatures).difference(mergedDF.columns)
        for missingColum in missingColums:
            mergedDF[missingColum] = np.nan
        orderedSIMI = mergedDF[simiOrderColumns]
        save_zipped_pickle(orderedSIMI, join(FEATURE_DIR, bugID))
    else:
        logging.error('Miss match in the answer %s', bugID)


def caseSimi2Feature(subject, bugColumns, sourceColumns, simiOrderColumns):
    if not os.path.exists(FEATURE_DIR):
        os.mkdir(FEATURE_DIR)

    fields = itertools.product(bugColumns, sourceColumns)

    allFeatures = [f[0] + '2' + f[1] for f in fields]

    if subject == 'ALL':
        simis = listdir(SIMI_SINGLE)
    else:
        simis = [f for f in listdir(SIMI_SINGLE) if f.startswith(subject)]

    parallelRun(simi2Feature, simis, allFeatures, simiOrderColumns)



