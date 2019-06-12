from common.commons import *

CODE_PATH = os.environ["CODE_PATH"]
DATA_PATH = os.environ["DATA_PATH"]
ROOT_DIR = os.environ["ROOT_DIR"]
DEFECTS4J = os.environ["DEFECTS4J"]
jdk7 = os.environ["JDK7"]
D4JHOME = os.environ["D4JHOME"]



def launchGV():
    projects = [('Math', 106), ('Lang', 65)]

    workList = []
    for p in projects:
        pjName, iterSize = p

        for idx in range(iterSize):
            idx = idx + 1
            workList.append(pjName + '_' + str(idx))

    parallelRun(gvCore,workList)
    # print(workList[0])
    # gvCore('Math_34')


def gvCore(pj):

    cmd = "java -jar "+join(DATA_PATH,'mimicGV.jar') \
          + " "+ join(DATA_PATH,'defects4jFailedTestCases/') \
          + " " + join(DATA_PATH,'stmtLoc') \
          +" " + join(DEFECTS4J)\
          + " "+ D4JHOME \
          + " "+ pj \
          +" " + 'TB' \
          +" " + "JAVA_HOME="+ jdk7

    print(cmd)
    out,err = shellGitCheckout(cmd)
    print(out,err)
    # cmd