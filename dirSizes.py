"""
script used to display nicely dir sizes :)

requirements
tabulate==0.9.0

if run from command line
typed-argument-parser==1.8.0

if run from command line and with debug flag
debugpy==1.6.3
"""

import logging
import os as _os
import re as _re
from enum import Enum as _Enum
from typing import Callable

import tabulate as _tabulate

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
logger = logging.getLogger()


class Size(_Enum):
    o = 0
    k = 1
    m = 2
    g = 3
    t = 4


def sizeToInt(sizeUnit: Size, size: int):
    return size * 1024**sizeUnit.value


class _SizeFormater:
    def __init__(self, sizeUnit: Size, numbersAfterDecimal: int):
        self.conversionNumber = 1024**sizeUnit.value
        if self.conversionNumber != 1:
            self.sizeUnit = sizeUnit.name + "B"
        else:
            self.sizeUnit = "B"
        self.numbersAfterDecimal = numbersAfterDecimal

    def formatSize(self, size: int):
        return str(round(size / self.conversionNumber, self.numbersAfterDecimal)) + " " + self.sizeUnit


class _DirInfo:
    def __init__(self, path: str, fileCount: int, size: int, depth: int, nbrOfErrDir: int, nbrOfErrFile: int, sizeFormater: _SizeFormater):
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


class _DirInfoList:
    def __init__(
        self,
        dirList: list[_DirInfo],
        errList: list[str],
        numberOfResultToDisplay,
        filterFunction: Callable[[_DirInfo], int] | None = None,
        sortOrder: Callable[[_DirInfo], bool] | None = None,
    ):
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
                printableData = self.dirList[0 : self.numberOfResultToDisplay]  # noqa E203
            if self.sortOrder is not None:
                printableData = sorted(self.dirList[0 : self.numberOfResultToDisplay], key=self.sortOrder)  # noqa E203
            returnStr += _tabulate.tabulate(printableData, headers=self.dirList[0].printableFields) + "\n"
        if len(self.errList) > 0:
            returnStr += "\nError List\n"
            returnStr += "filepath\n"
            returnStr += "\n".join(self.errList[0 : self.numberOfResultToDisplay])  # noqa E203
        return returnStr

    def __repr__(self):
        return self.__str__()


def _walkError(permissionErr: OSError, errList: list[str]):
    errList.append(permissionErr.filename)


def getDirsSizes(
    rootDir: str,
    sizeUnit: Size,
    numberOfResultToDisplay: int,
    convertRootDirToAbsolutePath: bool,
    numbersAfterDecimal: int,
    filterDirInfoList: Callable[[_DirInfo], int] = lambda x: x.size >= sizeToInt(Size.m, 1),
):
    logger.info("start of getDirsSizes function")

    sizeFormater = _SizeFormater(sizeUnit, numbersAfterDecimal)
    if convertRootDirToAbsolutePath:
        rootDir = _os.path.abspath(rootDir)
    errList: list[str] = []
    dirInfoDict: dict[str, _DirInfo] = {}

    if _re.search(r"^([A-Za-z]:\\|/)$", rootDir):
        rootDirDepth = 0
    else:
        rootDirDepth = rootDir.count(_os.path.sep)
    dirInfoDict[rootDir] = _DirInfo(rootDir, 0, 0, 0, 0, 0, sizeFormater)

    logger.info("beginning of file browsing")
    for root, dirs, files in _os.walk(rootDir, topdown=True, onerror=lambda err: _walkError(err, errList)):  # catches the errors on dir level
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

    logger.info("adding the remaining errors")
    for filePath in errList:
        if filePath == rootDir:
            dirInfoDict[filePath].nbrOfErrDir += 1
        else:
            dirInfoDict[_os.path.dirname(filePath)].nbrOfErrDir += 1

    logger.info("updating the infos from child to parent")
    for key, currentDirInfo in sorted(dirInfoDict.items(), reverse=True, key=lambda x: x[1].depth):
        try:
            parentDirInfo = dirInfoDict[_os.path.dirname(key)]
            parentDirInfo.fileCount += currentDirInfo.fileCount
            parentDirInfo.size += currentDirInfo.size
            parentDirInfo.nbrOfErrDir += currentDirInfo.nbrOfErrDir
            parentDirInfo.nbrOfErrFile += currentDirInfo.nbrOfErrFile
        except KeyError:
            pass

    return _DirInfoList(sorted(dirInfoDict.values(), reverse=True, key=lambda x: x.size), errList, numberOfResultToDisplay, filterFunction=filterDirInfoList)


if __name__ == "__main__":
    from tap import Tap

    class Args(Tap):
        rootDir: str  # dir to start crawling files
        sizeUnit: Size = Size.m  # size display
        numberOfResultToDisplay: int = 100
        convertRootDirToAbsolutePath: bool = True
        numbersAfterDecimal: int = 1
        verbose: bool = False
        debug: bool = False

    args = Args().parse_args(known_only=True)

    if args.debug:
        import debugpy

        debugpy.listen(5678)
        print("IM LISTENNING ON 5678 MY CHILD, TAKE YOUR TIME AND ATTACH TO PAPA <3")
        debugpy.wait_for_client()
        debugpy.breakpoint()

    if not args.verbose:
        logger.setLevel(logging.ERROR)

    infos = getDirsSizes(
        rootDir=args.rootDir,
        sizeUnit=args.sizeUnit,
        numberOfResultToDisplay=args.numberOfResultToDisplay,
        convertRootDirToAbsolutePath=args.convertRootDirToAbsolutePath,
        numbersAfterDecimal=args.numbersAfterDecimal,
    )
    print(infos)
