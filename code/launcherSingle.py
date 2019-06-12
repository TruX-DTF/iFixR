from common.commons import *


if __name__ == '__main__':


    try:
        args = getRun()
        setLogg()


        setEnv(args)

        job = args.job
        ROOT_DIR = os.environ["ROOT_DIR"]
        REPO_PATH = os.environ["REPO_PATH"]
        CODE_PATH = os.environ["CODE_PATH"]
        DATA_PATH = os.environ["DATA_PATH"]
        COMMIT_DFS = os.environ["COMMIT_DFS"]
        BUG_POINT = os.environ["BUG_POINT"]
        COMMIT_FOLDER = os.environ["COMMIT_FOLDER"]
        FEATURE_DIR = os.environ["FEATURE_DIR"]
        DATASET_DIR = os.environ["DATASET_DIR"]

        pd.options.mode.chained_assignment = None



        sourceColumns = ['packageName', 'className', 'methodNames', 'formalParameter',
                         'methodInvocation', 'memberReference', 'documentation', 'literal', 'rawSource', 'hunks',
                         'commitLogs', 'classNameExt']


        bugColumns = ['summary', 'description', 'summaryHints',
                      'descHints', 'codeElements', 'stackTraces', 'summaryDescription']

        fields = itertools.product(bugColumns, sourceColumns)

        features = [f[0] + '2' + f[1] for f in fields]


        simiOrderColumns = ['bugID', 'file'] +features+['answer']



        if job == 'clone':
            from commitCollector import *
            caseClone(args.subject)
        elif job =='collect':
            from commitCollector import *
            caseCollect(args.subject)
        elif job =='fix':
            from filterBugFixingCommits import caseFix
            caseFix(args.subject)
        elif job =='bugPoints':
            from filterBugFixingCommits import getLasts
            getLasts(args.subject,True)
            
        elif job == 'brDownload':
            from bugReportDownloader import caseBRDownload
            caseBRDownload(args.subject)

        elif job == 'brParser':
            from bugReportParser import caseBRParser
            caseBRParser(args.subject)

        elif job == 'brFeatures':
            from bugReportFeatures import getFeatures
            getFeatures(args.subject)
            
        elif job == 'brStats':
            from bugReportParser import step3
            step3(args.subject)
            
         #TODO ground truth of bug linkage

        elif job =='verify':
            
            from checkoutBugFix import caseVerify
            caseVerify(args.subject,True)

        elif job=='simi':
            from simiNew import caseSimiNew
            caseSimiNew(args.subject,bugColumns,sourceColumns)

        elif job == 'features':
            from simiNew import caseSimi2Feature
            caseSimi2Feature(args.subject, bugColumns, sourceColumns, simiOrderColumns)

        elif job =='predict':
            from train import casePredict

            if not os.path.exists(DATASET_DIR):
                os.mkdir(DATASET_DIR)
            else:
                shutil.rmtree(DATASET_DIR)
                os.mkdir(DATASET_DIR)

            yearList = ['2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016']
            for year in yearList:
                casePredict(features,year)

        elif job=='eval':
            from eval import caseEval
            caseEval('validationFinal')

        elif job=='merge':
            from eval import caseMerge
            caseMerge('validationFinal')

        elif job == 'stmt':
            from stmtBL import getStmtLevelBL
            getStmtLevelBL(10)

        elif job =='evalStmt':
            from stmtBL import evalStmtBL
            evalStmtBL()
                
        elif job =='stats':
            from stmtBL import getStats
            getStats()

        elif job == 'box':
            from stmtBL import plotBox
            plotBox()

        elif job =='gv':
            from generateValidate import launchGV
            launchGV()



    except Exception as e:
        logging.error(e)