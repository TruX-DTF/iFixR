# from common.parseJava import *
from common.commons import *
import itertools
from multiprocessing.pool import Pool

ROOT_DIR = os.environ["ROOT_DIR"]
REPO_PATH = os.environ["REPO_PATH"]
CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
COMMIT_DFS = os.environ["COMMIT_DFS"]
# SIMI_DIR = os.environ["SIMI_DIR"]
BUG_POINT = os.environ["BUG_POINT"]
PARSED_DIR = os.environ["PARSED_DIR"]
COMMIT_FOLDER = os.environ["COMMIT_FOLDER"]
# DTM_PATH = os.environ["DTM_PATH"]
PARSED = os.environ["PARSED"]
jdk8 = os.environ["JDK8"]

def checkout(repo,timestamp):

    # timestamp = '2015-07-15 07:47'
    cmd = 'git -C ' + repo + ' checkout `git rev-list -n 1 --before="'+timestamp+'" master`'
    output = shellCallTemplate(cmd)
    output


def get_filepaths(directory):

    file_paths = []  # List which will store all of the full filepaths.\n,
    exclude = '.git'
    # Walk the tree.\n,
    for root, directories, files in os.walk(directory):
        directories[:] = [d for d in directories if d not in exclude]
        java = [i for i in files if i.endswith('.java')]

        for filename in java:
            # Join the two strings in order to form the full filepath.\n,
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)  # Add it to the list.\n,

    return file_paths  # Self-explanatory.\n,


def load_textfile( _file):
    try:
        with open(_file, 'r', encoding='latin-1') as f:
            text = f.read()

    except IOError as e:

        raise
        return ''
    return text

def readFirstTextfile( _file):
    try:
        with open(_file, 'r', encoding='latin-1') as f:
            text = f.readline()

    except IOError as e:
        # logging.exception(e)
        raise
        return ''
    return text

def parserCore(f):
    try:
        # text = load_textfile(f)
        # parseDict = parse(text)
        cmd = "JAVA_HOME='"+jdk8+"' java -jar "+join(CODE_PATH, 'JavaCodeParser.jar ')  + f
        output = shellCallTemplate(cmd)
        parseDict = eval(output)

        parseDict['rawSource'] = load_textfile(f)
        parseDict['file'] =f


    except Exception as e:
        # logging.error(e)
        raise
    return parseDict

def getSourceCodeAsText(x):

        logging.info(len(x))
        parsed = []


        with concurrent.futures.ProcessPoolExecutor() as executor:
            try:
                futures = {executor.submit(parserCore, l ): l for l in x }
                for future in concurrent.futures.as_completed(futures):
                    url = futures[future]
                    try:
                        data = future.result()
                        parsed.append(data)
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
        return parsed



def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def cleanIndexOf(x):
    hunk = []
    for i in x:
        indexOf = '^index [0-9a-f]{4,10}..[0-9a-f]{4,10}'
        patternMinusDiscard = re.compile(r'^\-{3}')
        patternPlusDiscard = re.compile(r'^\+{3}')
        patternAt = re.compile(r'^\@{2}')
        patternNewFileMode = re.compile('^new file mode ')
        endPattern = '^diff --git'

        isIndexOf = re.search(indexOf, i)
        isMinus3 = re.search(patternMinusDiscard, i)
        isPlus3 = re.search(patternPlusDiscard, i)
        isAt = re.search(patternAt, i)
        isNewFileMode = re.search(patternNewFileMode, i)
        isEnd = re.search(endPattern,i)
        if not (isEnd or isIndexOf or isMinus3 or isPlus3 or isAt or isNewFileMode):
            hunk.append(i)

        # if not (isIndexOf):
        #     hunk.append(i)
    return hunk

def splitCommits(x):
    commitPattern = '^\*\*\*\* '
    # cp = re.compile(commitPattern)
    endPattern = '^diff --git'
    commitDates =[]

    logs = []
    hunks = []

    commitStartIndexes = []
    commitEndIndexes = []
    for index, value in enumerate(x):
        isCommit = re.search(commitPattern, value, re.I)
        if isCommit:
            #sha = value.split('commit')[1].strip()
            commitStartIndexes.append(index+1)
            commitDates.append(value.replace('**** ',''))

        isEnd = re.search(endPattern,value,re.I)
        if isEnd:
            commitEndIndexes.append(index)

    for i, j in pairwise(zip(commitStartIndexes,commitEndIndexes)):
        a,b = i
        c,d = j
        logs.append(x[a:b])
        hunks.append(x[b:c])
    logs.append(x[commitStartIndexes[-1]:commitEndIndexes[-1]])
    hunks.append(x[commitEndIndexes[-1]:])
    hunks = ['\n'.join(cleanIndexOf(h)) for h in hunks]
    logs = ['\n'.join(l) for l in logs]
    return logs,hunks,commitDates


def getHunksAndCommits(file,repo):
    try:
        fileName = file.split(join(REPO_PATH, repo) + '/')[-1]
        cmd = 'git -C ' + join(REPO_PATH, repo) + '/ ' + "log --pretty=format:'**** %B' -p --follow " + fileName

        output = shellCallTemplate(cmd,'latin-1')
        content = output.splitlines()
        if len(content)>0:
            commitLogs,hunks  = splitCommits(content)
        else:
            hunks =[]
            commitLogs =[]
        return hunks,commitLogs

    except Exception as e:
        # logging.exception(e)
        raise

def isFileInList(file,checkList):
    for f in checkList:
        if f in file:
            return True
    return False

def parseCore(commit,repo,subject,files,timestamp,ansFiles):
    try:
        bugID = commit.split('.')[0]
        if isfile(join(PARSED_DIR, bugID + ".pickle")):
            return
        else:

            if isfile(join(PARSED, bugID)):
                parsed = load_zipped_pickle(join(PARSED, bugID))
                logging.info('Loaded parsed files %d' % len(parsed))
            else:
                parsed = getSourceCodeAsText(files)

                save_zipped_pickle(parsed, join(PARSED, bugID))


            preFixFiles= pd.DataFrame(parsed)
            preFixFiles['repo'] = repo
            preFixFiles['bugID'] = bugID
            preFixFiles['subject'] = subject


            if isfile(join(PARSED, bugID+ 'hunksAndCommits')):
                hunksAndCommitsDF = load_zipped_pickle(join(PARSED, bugID+ 'hunksAndCommits'))
            else:
                hunksAndCommitsDF =retrieveHunksAndCommits(repo,files,bugID)

            preFixFiles['file'] = preFixFiles.file.apply(lambda x:x.split(join(REPO_PATH, repo) + '/')[-1])
            preFixFiles['answer'] = preFixFiles.file.apply(lambda x: isFileInList(x, ansFiles))
            selectedFiles = hunksAndCommitsDF[hunksAndCommitsDF.file.isin(preFixFiles.file)]
            selectedHunks = selectedFiles.query("commitDates < '{0}'".format(timestamp))
            a = selectedHunks.groupby('file', as_index=False).agg(
                {'commitLogs': lambda x: list(x), 'hunks': lambda x: list(x)})
            res = pd.merge(preFixFiles, a, on=['file'])

            save_zipped_pickle(res, join(PARSED_DIR, bugID + ".pickle"))

    except Exception as e:
        logging.error(bugID)
        raise

def verifyCheckoutAndParse(bugPoint):

    bugID = bugPoint.split('.')[0]
    subject = bugID.split('-')[0]
    subjects = pd.read_csv(join(CODE_PATH, 'subjects.csv'))

    if isfile(join(PARSED_DIR, bugID + ".pickle")):
        return
    else:
        logging.info("Starting verification of bug report %s",bugID)
        bf = load_zipped_pickle(join(BUG_POINT, bugPoint))
        if not (bf.empty):

            try:
                timestamp = bf.iloc[0].dateCheck
                repo = subjects.query("Subject == '{0}'".format(subject)).iloc[0].Repo
                cmd = 'git -C ' +join(REPO_PATH, repo)+' rev-list -n1 --before="'+str(timestamp)+ '" origin | xargs git -C '+join(REPO_PATH, repo)+' checkout -f'
                output,err = shellGitCheckout(cmd,enc='latin1')
                m = re.search('HEAD',err)

                while not m:
                    time.sleep(10)
                    logging.info('Waiting for checkout')

                brFiles = load_zipped_pickle(join(CODE_PATH, 'bugReportFiles.pickle'))
                files = get_filepaths(join(REPO_PATH, repo))

                if subject == 'MATH' or subject =='LANG':
                    fileQuery = brFiles.query("issue == '{0}'".format(bugID))
                    if len(fileQuery) == 1:
                        fileList = fileQuery.iloc[0].files
                    else:
                        import itertools
                        fileList = list(itertools.chain.from_iterable(fileQuery.files.tolist()))
                    fileList = [i for i in fileList if i.startswith('/src/main/java/') or i.startswith('/src/java/')]
                    files = [i for i in files if i.startswith(join(REPO_PATH, repo, 'src','main','java')) or i.startswith(join(REPO_PATH, repo, 'src','java'))]

                verifyM = list(map(lambda x: [i for i in files if x in i], fileList))
                haveAll = list(map(lambda x: len(x) == 1, verifyM))
                if (np.all(haveAll)):
                    ansFiles = [i[1:] for i in fileList]
                    parseCore(bugPoint, repo, subject,files,timestamp,ansFiles)
                else:
                    raise Exception("Bug id %s did not validate all the files", bugID)


            except Exception as e:
                logging.error(e)
                logging.error("Bug id %s did not validate all the files", bugID)

                if not os.path.exists(join(DATA_PATH,'bugPointsNV')):
                    os.mkdir(join(DATA_PATH,'bugPointsNV'))

                shutil.move(join(BUG_POINT, bugPoint),join(DATA_PATH,'bugPointsNV', bugPoint))


def computeHunksAndCommits(x,repo):
    try:
        file = x
        fileName = file.split(join(REPO_PATH, repo) + '/')[-1]

        cmd = 'git -C ' + join(REPO_PATH, repo) + '/ ' + 'log ' + " --pretty=format:'**** %ci%n%B' -p --follow " + fileName

        output = shellCallTemplate(cmd,'latin-1')
        content = output.splitlines()
        if len(content)>0:
            commitLogs,hunks,commitDates  = splitCommits(content)
        else:
            hunks =[]
            commitLogs =[]
            commitDates = []

        series = []
        series.append(hunks)
        series.append(commitLogs)
        series.append(commitDates)
        df = pd.DataFrame(series)
        df = df.T
        df.columns = ['hunks','commitLogs','commitDates']
        df['file'] = fileName
        # df['fileNames'] = fileNames

        df['commitDates'] = df['commitDates'].apply(lambda x: pd.to_datetime(x))
        return df

    except Exception as e:
        # logging.exception(e)
        raise

def retrieveHunksAndCommits(repo,files,bugID):
    hunksAndCommits = []
    #
    with concurrent.futures.ThreadPoolExecutor() as executor:
        try:
            futures = {executor.submit(computeHunksAndCommits, l, repo): l for l in files}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    ds = future.result()

                    hunksAndCommits.append(ds)
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

    hunksAndCommitsDF = pd.concat(hunksAndCommits)
    hunksAndCommitsDF
    save_zipped_pickle(hunksAndCommitsDF, join(PARSED, bugID + 'hunksAndCommits'))
    return hunksAndCommitsDF




def caseVerify(subject,predict=False):
    logging.info('PARSED_DIR : %s', PARSED_DIR)
    bugPoints = os.listdir(BUG_POINT)


    if not os.path.exists(PARSED_DIR):
        os.mkdir(PARSED_DIR)
    if not os.path.exists(PARSED):
        os.mkdir(PARSED)


    if predict:
        a = load_zipped_pickle(join(DATA_PATH, subject + "bugReportsComplete.pickle"))
        bids = a.bid.unique()
        bugPoints = [i for i in bugPoints if i.split('.')[0] in (bids)]
    else: #not (subject in 'MATH-' or subject in 'LANG-' or subject in 'CLOSURE-'):
        # a = pd.read_pickle(join(CODE_PATH, 'bugReportsComplete.pickle'))
        #TODO change path
        a = load_zipped_pickle(join(CODE_PATH, subject+"bugReportsComplete.pickle"))
        g2 = load_zipped_pickle(join(CODE_PATH, 'groundTruth2.pickle'))
        bids = g2[g2.BugID.isin(a.bid.unique())].BugID.unique()
        bugPoints = [i for i in bugPoints if i.split('.')[0] in (bids)]

    if subject == 'ALL':
        for bugPoint in bugPoints:
            verifyCheckoutAndParse(bugPoint)
    else:
        for bugPoint in [f for f in bugPoints if f.startswith(subject)]:
            verifyCheckoutAndParse(bugPoint)





