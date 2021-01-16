import os as _os
import re as _re
import datetime as _datetime

import tabulate as _tabulate


sizeList = ("o", "k", "m", "g", "t")


def sizeToInt(sizeUnit, size):
    try:
        return size * 1024**sizeList.index(sizeUnit)
    except ValueError:
        raise ValueError("sizeUnit must be one of the following: " + str(sizeList))


class _SizeFormater():
    def __init__(self, sizeUnit, numbersAfterDecimal):
        try:
            self.conversionNumber = 1024**sizeList.index(sizeUnit)
        except ValueError:
            raise ValueError("sizeUnit must be one of the following: " + str(sizeList))
        if self.conversionNumber != 1:
            self.sizeUnit = sizeUnit + "B"
        else:
            self.sizeUnit = "B"
        self.numbersAfterDecimal = numbersAfterDecimal

    def formatSize(self, size):
        return str(round(size / self.conversionNumber, self.numbersAfterDecimal)) + " " + self.sizeUnit


class _DirInfo():
    def __init__(self, path, fileCount, size, depth, nbrOfErrDir, nbrOfErrFile, sizeFormater):
        self.path = path
        self.fileCount = fileCount
        self.size = size
        self.depth = depth
        self.nbrOfErrDir = nbrOfErrDir
        self.nbrOfErrFile = nbrOfErrFile
        self.sizeFormater = sizeFormater
        self.printableFields = ["path", "size", "fileCount", "depth", "nbrOfErrDir", "nbrOfErrFile"]
        self.printFieldFormat = {"size": self.sizeFormater.formatSize}

    def __iter__(self):  # kinda yolo
        for field in self.printableFields:
            try:
                yield self.printFieldFormat[field](self.__getattribute__(field))
            except KeyError:
                yield self.__getattribute__(field)

    def __str__(self):
        return "; ".join([fieldName + " " + str(fieldValue) for fieldName, fieldValue in zip(self.printableFields, self)])

    def __repr__(self):
        return self.__str__()


class _DirInfoList():
    def __init__(self, dirList, errList, numberOfResultToDisplay, filterFunction=None, sortOrder=None):
        self.dirList = dirList
        self.errList = errList
        self.numberOfResultToDisplay = numberOfResultToDisplay
        self.filterFunction = filterFunction
        self.sortOrder = sortOrder

    def __str__(self):
        returnStr = ""
        if len(self.dirList) > 0:
            returnStr += "Dir List\n"
            if self.filterFunction is not None:
                printableData = filter(self.filterFunction, self.dirList)
            else:
                printableData = self.dirList[0:self.numberOfResultToDisplay]
            if self.sortOrder is not None:
                printableData = sorted(self.dirList[0:self.numberOfResultToDisplay], key=self.sortOrder)
            returnStr += _tabulate.tabulate(printableData, headers=self.dirList[0].printableFields) + "\n"
        if len(self.errList) > 0:
            returnStr += "\nError List\n"
            returnStr += "filepath\n"
            returnStr += "\n".join(self.errList[0:self.numberOfResultToDisplay])
        return returnStr

    def __repr__(self):
        return self.__str__()


def _walkError(permissionErr, errList):
    errList.append(permissionErr.filename)


def getDirsSizes(rootDir, sizeUnit="g", numberOfResultToDisplay=100, convertRootDirToAbsolutePath=True, numbersAfterDecimal=1, filterDirInfoList=lambda x: x.size >= sizeToInt("g", 1), debug=True):
    if debug: print(str(_datetime.datetime.now()) + " start of getDirsSizes function")  # noqa: E701
    rootDir = str(rootDir)
    if type(convertRootDirToAbsolutePath) is str:
        convertRootDirToAbsolutePath = convertRootDirToAbsolutePath.lower() in ("yes", "y", "true", "1")
    numbersAfterDecimal = int(numbersAfterDecimal)
    sizeUnit = str(sizeUnit)
    numberOfResultToDisplay = int(numberOfResultToDisplay)

    sizeFormater = _SizeFormater(sizeUnit, numbersAfterDecimal)
    if convertRootDirToAbsolutePath:
        rootDir = _os.path.abspath(rootDir)
    errList = []
    dirInfoDict = {}

    if _re.search(r"^([A-Za-z]:\\|/)$", rootDir):
        rootDirDepth = 0
    else:
        rootDirDepth = rootDir.count(_os.path.sep)
    dirInfoDict[rootDir] = _DirInfo(rootDir, 0, 0, 0, 0, 0, sizeFormater)

    if debug: print(str(_datetime.datetime.now()) + " beginning of file browsing")  # noqa: E701
    for root, dirs, files in _os.walk(
            rootDir, topdown=True,
            onerror=lambda err: _walkError(err, errList)):  # catches the errors on dir level
        for name in dirs:
            dirFullpath = _os.path.join(root, name)
            dirInfoDict[dirFullpath] = _DirInfo(dirFullpath, 0, 0, dirFullpath.count(_os.path.sep) - rootDirDepth, 0, 0, sizeFormater)
        for name in files:
            fileFullpath = _os.path.join(root, name)
            dirInfoObj = dirInfoDict[_os.path.dirname(fileFullpath)]
            try:
                dirInfoObj.size += _os.path.getsize(fileFullpath)
                dirInfoObj.fileCount += 1
            except (PermissionError):  # permission err
                dirInfoObj.nbrOfErrFile += 1
            except (OSError):  # file does not exists anymore, no need to report the error
                pass

    if debug: print(str(_datetime.datetime.now()) + " adding the remaining errors")  # noqa: E701
    for filePath in errList:
        if filePath == rootDir:
            dirInfoDict[filePath].nbrOfErrDir += 1
        else:
            dirInfoDict[_os.path.dirname(filePath)].nbrOfErrDir += 1

    if debug: print(str(_datetime.datetime.now()) + " updating the infos from child to parent")  # noqa: E701
    for key, currentDirInfo in sorted(dirInfoDict.items(),
                                      reverse=True,
                                      key=lambda x: x[1].depth):
        try:
            parentDirInfo = dirInfoDict[_os.path.dirname(key)]
            parentDirInfo.fileCount += currentDirInfo.fileCount
            parentDirInfo.size += currentDirInfo.size
            parentDirInfo.nbrOfErrDir += currentDirInfo.nbrOfErrDir
            parentDirInfo.nbrOfErrFile += currentDirInfo.nbrOfErrFile
        except KeyError:
            pass

    return _DirInfoList(sorted(dirInfoDict.values(), reverse=True, key=lambda x: x.size),
                        errList, numberOfResultToDisplay, filterFunction=filterDirInfoList)
