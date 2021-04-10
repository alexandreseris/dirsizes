# dirsizes

A python function which compute the size of directories recursively and pretty print the result using [tabulate](https://pypi.org/project/tabulate/)  
_tested on python 3.6_

## Usage

```python
import dirSises
dirSises.getDirsSizes(
    "/your/root/dir", 
    sizeUnit="g",
    numberOfResultToDisplay=100,
    convertRootDirToAbsolutePath=True,
    numbersAfterDecimal=1,
    filterDirInfoList=lambda x: x.size >= dirSises.sizeToInt("g", 1),
    debug=True
)

# filterDirInfoList parameter is excpeted to be a function taking _DirInfo object as input and returning True or False
```
