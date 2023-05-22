# Lyra Tool
Open source tool for modifying TESCAN Lyra Project files.

![Editor](doc/img/editor.png)


## Features
* Supports editing nearly all shape types in LyraTC DrawBeam Project `.xml` files.
* Supports editing some of the Material and Process project properties.
  _**Note:** Beam properties such as Current and Spot Size are saved in the project data,
  but are usually not representative of the actual measured values during SEM operation._


## Installation
* Clone the project or download the zipped source (ideally from a tagged release).
* Open a terminal and navigate to the project directory.
* Run `pip install -r requirements.txt`.
* (Ubuntu) Install `tkinter` using `apt install python3-tk`.
* Run `python3 app.py`.
