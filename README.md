# Usage

This is a Python codelet (.py) that identifies duplicate files in a folder and prints a text file (.txt) listing said duplicates. Document data is not transmitted beyond the computer.

The Python codelet should be run in Terminal with the name of the file that contains potentially duplicated files. If the file is the *~/Documents* file and the codelet were located at *~/duplicate_file_finder.py*, the command would be:

```
python3 duplicate_file_finder.py ~/Documents
```

The codelet produces a text file (.txt) which lists all duplications. Document data is not transmitted outside the machine in this operation. Neither does the codelet delete any data. The user must read the text file and then delete duplications manually. 
