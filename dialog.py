from tkinter import filedialog, Tk
from pathlib import Path
from io import IOBase
import logging as log


tk_root = Tk()
tk_root.withdraw()


# Opens a file open dialog and returns either an open file handle for reading
# or None if the user cancelled the operation
def file_open(extension: str = '.xml') -> IOBase | None:
    log.info('Popping a file open dialog')
    file = filedialog.askopenfile(defaultextension=extension)
    log.info('File open dialog returned:', file)
    return file


# Opens a file save dialog and returns either an open file handle for writing
# or None if the user cancelled the operation
def file_save(extension: str = '.xml') -> IOBase | None:
    log.info('Popping a file save dialog')
    file = filedialog.asksaveasfile(defaultextension=extension)
    log.info('File save dialog returned:', file)
    return file
