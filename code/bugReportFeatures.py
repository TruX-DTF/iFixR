from common.commons import *

import copy

CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
BUG_REPORT_FEATURES = os.environ["BUG_REPORT_FEATURES"]


def extractFeatures(x,pjName):
    desc = x['description']
    id = x['bid']


    with open(join(BUG_REPORT_FEATURES,pjName,'desc',str(id)+'.out'), 'w') as f:
        f.write(desc)

    cmd = "JAVA_HOME='/Library/Java/JavaVirtualMachines/jdk1.8.0_181.jdk/Contents/Home' java -jar " +join(CODE_PATH,"infozilla-1.0-SNAPSHOT-jar-with-dependencies.jar")+" -i " +join(BUG_REPORT_FEATURES,pjName,'desc',str(id)+'.out') + ' -o ' + join(BUG_REPORT_FEATURES,pjName,'info',str(id)+'.out') #'bugReportFeatures/'+pjName+'/'+str(id)+'.out'
    shellCallTemplate(cmd)
    cmd

def saveFeatures(id,pjName,key):
    # id = x['bugReport']

    with open(join(BUG_REPORT_FEATURES, pjName, 'info', str(id) + '.out'), 'r') as f:
        text = f.read()
        featureDict = eval(text)
        return  featureDict[key]


def getHintTexts(_text):
    '''
    get Hint texts: package name, camel case, etc.
    ex) org.apache.abc, calculateCorpus, etc.
    (This also find filename)
    :param _text:
    :return:
    '''
    text = copy.copy(_text)

    items = set([])
    patternPkg = re.compile(r'([A-Za-z]\w+\.)+[A-Za-z]\w+')
    pos = 0
    while True:
        result = patternPkg.search(text, pos=pos)
        if result is None: break
        if len(result.group()) > 5:
            items.add(result.group())
            sp = result.regs[0][0]
            ep = result.regs[0][1]
            text = text[:sp] + text[ep:]
            pos = result.regs[0][0]
        else:
            pos = result.regs[0][1]

    patternCamel = re.compile(r'(\w+[a-z]+[A-Z]+\w+)+')
    pos = 0
    while True:
        result = patternCamel.search(text, pos=pos)
        if result is None: break
        items.add(result.group())
        sp = result.regs[0][0]
        ep = result.regs[0][1]
        text = text[:sp] + text[ep:]
        pos = result.regs[0][0]  # this group's positions
    return list(items)



def getFeatures(subject):
    # br = load_zipped_pickle('bugReports/'+pjName+'BugReports.pickle')

    if not os.path.exists(BUG_REPORT_FEATURES):
        os.mkdir(BUG_REPORT_FEATURES)

    if not os.path.exists(join(BUG_REPORT_FEATURES,subject)):
        os.mkdir(join(BUG_REPORT_FEATURES,subject))

    if not os.path.exists(join(BUG_REPORT_FEATURES,subject,'info')):
        os.mkdir(join(BUG_REPORT_FEATURES,subject,'info'))

    if not os.path.exists(join(BUG_REPORT_FEATURES,subject,'desc')):
        os.mkdir(join(BUG_REPORT_FEATURES,subject,'desc'))

    br = load_zipped_pickle(join(DATA_PATH, subject + "bugReportsComplete.pickle"))

    br.apply(lambda x:extractFeatures(x,subject),axis=1)
    # for id in br.bugReport.values.tolist():
    #     res =  saveFeatures(id,pjName)
    # parallelRun(extractFeatures,br.bid.unique(),subject)
    br['codeElements'] = br.bid.apply(lambda x:saveFeatures(x,subject,'source'))
    br['stackTraces'] = br.bid.apply(lambda x: saveFeatures(x, subject, 'traces'))
    br['summaryHints'] = br.summary.apply(lambda x: getHintTexts(x))
    br['descHints'] = br.description.apply(lambda x: getHintTexts(x))
    br
    save_zipped_pickle(br,join(DATA_PATH,subject+'bugReportsComplete.pickle'))



