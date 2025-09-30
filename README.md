Rain
====

A simplistic programming language made in Python as a prototype. I might release a Rust version in the future and I might not.

Rainc and Rain
--------------

The Rain project is split into two parts:

Rain - The interpreter
    Handles how Rain code is executed.

Rainc - The tools
    Located in the tools folder, these Python files handle tasks such as converting Rain scripts into executables and setting up default Rain projects.

How to Install
--------------

Prerequisites
--------------
You will need:
- Python 3+
- argparse module
- pyinstaller module

Install the Python modules with:

- pip install argparse
- pip install pyinstaller

Installation Steps
------------------
1. Download both the Rain interpreter (Rain) and all Rainc tools (either from the latest release or repository).
2. Run the installer:

    python install.py

3. After installation, you can delete the following:
- install.py
- main.py
- the tools folder

Now Rain is installed and ready to use!

How to use Rain
----------------
To utilise the Rain project, type in:

    rainc -h

into a terminal and follow the help instructions.


Rain Syntax
----------------