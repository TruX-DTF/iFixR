from common.commons import *

CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
ROOT_DIR = os.environ["ROOT_DIR"]
DEFECTS4J = os.environ["DEFECTS4J"]
jdk8 = os.environ["JDK8"]


def locationsCore(t,filter=50):
    try:
        res, defects4jbug = t
        columns = ['bugReport', 'filename', 'methodName', 'prob', 'locations']
        locations = pd.DataFrame(columns=columns)
        ind = 0
        predictionResults = load_zipped_pickle(join(DATA_PATH, 'singlePred', res))
        bugID = res.replace('finalmultic_', '')

        prs = predictionResults.head(filter)[['file', 'meanPred']].values.tolist()
        subject = bugID.split('-')[0]
        for pr in prs:
            fileName, pred = pr
            # fileName = 'src/java/org/apache/commons/lang/enum/ValuedEnum.java'
            a = load_zipped_pickle(join(DATA_PATH, subject + 'bugReportsComplete.pickle'))
            a = a.query("bid == '{0}'".format(bugID))

            path = DEFECTS4J + defects4jbug + '/'

            cmd = "git -C " + path + " checkout -- ."
            output, err = shellGitCheckout(cmd)

            cmd = "JAVA_HOME='"+jdk8+"' java -jar " + join(
                CODE_PATH,
                'JavaCodeParserWithRanges.jar ') + join(path,
                                                        fileName)
            output = shellCallTemplate(cmd)
            parseDict = eval(output)
            names = list(parseDict.keys())

            a['summaryDescription'] = a[['summary', 'description']].apply(lambda x: ' '.join(x), axis=1)
            corpusBug = a['summaryDescription'].values.tolist()
            from common.preprocessing import preprocessingCodeElementsList
            preCorpusBug = list(map(preprocessingCodeElementsList, corpusBug))
            preCorpusBug

            preCorpusSource = list(map(preprocessingCodeElementsList, names))
            if (len(preCorpusBug) > 0 and len(preCorpusSource) > 0):
                from common.preprocessing import calculateTfIdfNLList
                v = calculateTfIdfNLList(preCorpusSource)
                sourceDTM = v.transform(preCorpusSource)
                bugDTM = v.transform(preCorpusBug)
                from sklearn.metrics.pairwise import cosine_similarity
                res = cosine_similarity(bugDTM, sourceDTM)
                methodPredictions = res[0] * pred
                ranks = np.argsort(-methodPredictions)
                for rank in ranks:
                    if methodPredictions[rank] > 0:
                        locations.loc[ind] = [bugID, fileName, names[rank], methodPredictions[rank],
                                              parseDict[names[rank]]]
                        ind += 1

        locs = locations.sort_values(['prob'], ascending=False)
        locs.reset_index(inplace=True)
        locs[['bugReport', 'filename', 'prob', 'locations']].to_csv(join(DATA_PATH, 'stmtLoc', defects4jbug))
    except Exception as e:
        print(t)
        logging.error(e)

def getStmtLevelBL(filter = 50):

    if not os.path.exists(join(DATA_PATH, 'stmtLoc')):
        os.mkdir(join(DATA_PATH, 'stmtLoc'))

    if not os.path.exists(DEFECTS4J):
        os.mkdir(DEFECTS4J)

        cmd = 'bash ' + join(ROOT_DIR,'createProjects.sh') + ' ' + DEFECTS4J
        logging.info('Checking out defects4j bugs')
        o = shellCallTemplate(cmd)

    projects = [('Math', 106), ('Lang', 65)]  # , ('Closure', 133)]
    results = [i for i in listdir(join(DATA_PATH, 'singlePred')) if i.startswith('finalmultic_')]
    workList = []
    for p in projects:
        pjName, iterSize = p

        for idx in range(iterSize):
            idx = idx + 1
            c = load_zipped_pickle(join(CODE_PATH, 'bugReportFiles.pickle'))
            subject = pjName.upper()
            issue = c.query("pj == '{0}' & bug == {1}".format(pjName, idx)).iloc[0].issue
            if subject == 'CLOSURE':
                issue = subject + "-" + str(issue)

            if 'finalmultic_' + str(issue) in results:
                t = 'finalmultic_' + str(issue), pjName + '_' + str(idx)
                workList.append(t)
    # workList = [('finalmultic_LANG-59', 'Lang_65')]

    parallelRun(locationsCore, workList,filter)

def evalStmtBL():
    bugPositions = pd.read_csv(join(CODE_PATH, 'BugPositions.txt'), sep='@', header=None)
    bugPositions.rename(columns={0: 'bid', 1: 'file', 2: 'position'}, inplace=True)

    def range_overlapping(x, y):
        return ((x.start <= y.stop and x.stop >= y.start) or
                (x.stop >= y.start and y.stop >= x.start))

    def checkGT(x, localizationPerformance):
        bid = x['bid']
        file = x['file']
        positions = x['position']
        positions = positions.split(',')
        positions = [i for i in positions if not i is '']

        for position in positions:
            if isfile(join(DATA_PATH, 'stmtLoc', bid)):
                res = pd.read_csv(join(DATA_PATH, 'stmtLoc', bid), index_col=0)
                # if isfile(join(resultPath,bid)):
                #     res = pd.read_csv(join(resultPath,bid),index_col=0)
                localization = res.query("filename =='{0}'".format(file))
                if '-' in position:  # range
                    pR = [int(i) for i in re.findall(r'\d+', position)]
                    positionRange = range(pR[0], pR[1])
                else:
                    positionRange = range(int(position), int(position))

                if not localization.empty:
                    localization.locations = localization.locations.apply(lambda x: eval(x))

                    localization['ranges'] = localization.locations.apply(
                        lambda x: [range(int(j[0]), int(j[1])) for j in [re.findall(r'\d+', i) for i in x]])

                    localization['answer'] = localization.ranges.apply(
                        lambda x: [range_overlapping(positionRange, i) for i in x])
                    localization['answerCum'] = localization.answer.apply(lambda x: np.any(x))
                    localization['position'] = localization.answer.str.len()

                    answer = localization[localization.answerCum == True]
                    if not answer.empty:
                        res = res[~res.locations.isna()]
                        res['localization'] = res.locations.apply(lambda x: eval(x))
                        res['position'] = res.localization.str.len()
                        answerPosition = res.loc[:(answer.index.values[0] - 1)].position.sum()
                    else:
                        answerPosition = ''
                    localizationPerformance.write(bid + ',' + str(answerPosition) + '\n')


            else:
                0

    bugPositions = bugPositions[bugPositions.bid.apply(lambda x: x.startswith('Lang') or x.startswith('Math'))]
    with open('localizationPerformanceStatements', 'w') as localizationPerformance:
        bugPositions.apply(lambda x: checkGT(x, localizationPerformance), axis=1)
        
def getStats():
    res = pd.read_csv(join(ROOT_DIR, 'localizationPerformanceStatements'), names=list(range(100)))
    res.rename(columns={0: 'bugID'}, inplace=True)
    res.rename(columns={1: 'bestPost'}, inplace=True)
    res = res[res.bugID.apply(lambda x: x.startswith('Lang') or x.startswith('Math'))]
    print(len(res.bugID.unique()))
    print(len(res[res.bestPost < 1].bugID.unique()),
          len(res[res.bestPost < 10].bugID.unique()),
          len(res[res.bestPost < 50].bugID.unique()),
          len(res[res.bestPost < 100].bugID.unique()),
          len(res[res.bestPost < 200].bugID.unique()),
          len(res[res.bestPost < 500000].bugID.unique()))
    res
    
def plotBox():
    a = load_zipped_pickle(join(CODE_PATH, 'LANGBugReportsExport.pickle'))
    b = load_zipped_pickle(join(CODE_PATH, 'MATHBugReportsExport.pickle'))
    stats = pd.concat([a, b], ignore_index=True)
    stats['created'] = stats['created'].apply(lambda x: pd.to_datetime(x))
    stats['resolved'] = stats['resolved'].apply(lambda x: pd.to_datetime(x))
    stats
    stats['tDiff'] = stats['resolved'] - stats['created']
    stats['tDiff'] = stats['tDiff'].astype('timedelta64[m]') / 60 / 24
    top10Loc = ['LANG-1', 'LANG-4', 'LANG-5', 'LANG-7', 'LANG-13', 'LANG-14',
                'LANG-15',
                'LANG-16',
                'LANG-17',
                'LANG-19',
                'LANG-24',
                'LANG-27',
                'LANG-36',
                'LANG-37',
                'LANG-41',
                'LANG-43',
                'LANG-45',
                'LANG-46',
                'LANG-47',
                'LANG-48',
                'LANG-50',
                'LANG-53',
                'LANG-55',
                'LANG-57',
                'LANG-58',
                'LANG-59',
                'LANG-62',
                'LANG-64',
                'MATH-1',
                'MATH-2',
                'MATH-5',
                'MATH-6',
                'MATH-7',
                'MATH-8',
                'MATH-9',
                'MATH-15',
                'MATH-16',
                'MATH-26',
                'MATH-27',
                'MATH-28',
                'MATH-34',
                'MATH-35',
                'MATH-40',
                'MATH-52',
                'MATH-55',
                'MATH-56',
                'MATH-57',
                'MATH-58',
                'MATH-59',
                'MATH-60',
                'MATH-61',
                'MATH-64',
                'MATH-65',
                'MATH-66',
                'MATH-67',
                'MATH-68',
                'MATH-69',
                'MATH-70',
                'MATH-74',
                'MATH-75',
                'MATH-76',
                'MATH-78',
                'MATH-86',
                'MATH-91',
                'MATH-92',
                'MATH-93',
                'MATH-94',
                'MATH-95',
                'MATH-97',
                'MATH-98',
                'MATH-100',
                'MATH-101',
                'MATH-103',
                'MATH-106']
    c = load_zipped_pickle(join(CODE_PATH, 'bugReportFiles.pickle'))
    c['defects4jID'] = c.apply(lambda x: x['pj'].upper() + '-' + str(x['bug']), axis=1)
    t = [c.query("defects4jID == '{0}'".format(i)).iloc[0][['issue']].values[0] for i in top10Loc]
    locBug = stats[stats.bugID.isin(t)]

    import matplotlib

    # matplotlib.use('PS')
    import matplotlib.pyplot as plt

    meanpointprops = dict(markeredgecolor='black',
                          markerfacecolor='black')

    yValues = []
    yValues.append(locBug['tDiff'].values.tolist())
    yValues.append(stats['tDiff'].values.tolist())
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ys = [locBug['tDiff'].values.tolist()]  # ,stats['tDiff'].values.tolist()]
    # for ax,y in zip(axes.flat,yValues):
    # box = ax.boxplot(ys,showmeans=True, vert=False,)
    plt.setp(ax.get_yticklabels(), visible=False)
    # ax.set_ylabel(label, rotation=45,ha='right')
    plt.setp(ax.get_xticklabels(), visible=False)

    box = ax.boxplot(ys, 0, '', showmeans=True, vert=False, widths=0.5,
                     meanprops=meanpointprops)  # autorange=True  whis=2
    # ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=11)
    # ax.set_yticks([0, 0.5, 1])
    # ax.yaxis.set_label_coords(-0.1, 0.5)
    ax.set_xticks([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50])
    # img = ax.imshow(im, vmin=0, vmax=1,cmap='binary')
    for line in box['medians']:
        # get position data for median line
        x, y = line.get_xydata()[1]  # top of median line
        line.set(linewidth=2)
        line.set_color('black')
        # overlay median value
        # ax.text(x+.06, y-.03 , '%.2f' % x, horizontalalignment='right',verticalalignment = 'bottom',  fontsize=12)  # draw above, centered
    for line in box['means']:
        # get position data for median line\n"
        x, y = line.get_xydata()[0]  # bottom of left line\n"
        # line.set(color='black')#, linewidth=5)
        # plt.setp(box['means'], color='black')
        # line.set(facecolor='black')
        # line.set_color('black')≥
        # overlay median value\n"
        # ax.text(x+.04, y+.05 , '%.2f' % x, horizontalalignment='right',verticalalignment = 'bottom',  fontsize=12)  # draw above, centered\n"
    ax.set_aspect('auto')
    ax.set_xlim(left=0.05, right=50.05)

    plt.setp(ax.get_xticklabels(), visible=True)
    ax.tick_params(left="off")

    # ax.set_ylabel('Gain')
    ax.set_xlabel('Days')

    plt.subplots_adjust(wspace=0, hspace=0)
    plt.ion()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)
    fig = plt.gcf()
    fig.set_size_inches(3.5, 0.6, forward=True)
    fig.savefig('gain.pdf', dpi=100, bbox_inches='tight')