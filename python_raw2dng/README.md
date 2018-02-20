pyraw2dng
=========

Overview
--------

This is meant to be a cross platform example on how to convert the raw (16bit standard) images from the Chronos1.4 high speed cameras to DNG.  This script will only work with 16 bit standard files, not the right-aligned "Raw16RJ" format.

The script will not autodetect any settings - you must provide the correct frame size in the command line.

This will, however, automatically make a directory where it will put the output DNGs named after the input file, if you wish.

Requirements
------------

Python 2.7

This might work in Python 3 as well, but it has not been tested.

Windows users will need Python 2.7, available here: https://www.python.org/downloads/release/python-278/

Instructions
------------

Copy the script file, pyraw2dng.py and the raw 16 bit format video into the same directory.

Open a terminal in that directory and use a command similar to the following, but replacing (width) and (length) with the horizontal and vertical resolutions of the video, and (filename.raw) with the name of the raw video file.

For Windows:
python pyraw2dng.py -w (width) -l (length) (filename.raw)
	Note: Under default install (without python in PATH), the first term "python" has to be replaced with "c:\Python27\python.exe"

For Linux:
./pyraw2dng.py -w (width) -l (length) (filename.raw)

If the script runs successfully, there will be a folder with the same name as your file containing the .dng images and the text "(filename).raw" will appear in the terminal.

Help (via --help)
-----------------

```
pyraw2dng.py - Command line converter from Chronos1.4 raw format to DNG image sequence
Copywrite KronTech 2018.

pyraw2dng.py <options> <inputFilename> [<OutputFilenameFormat>]

Options:
 --help      Display this help message
 -M/--mono   Raw data is mono
 -C/--color  Raw data is colour
 -w/--width  Frame width
 -l/--length Frame length
 -h/--height Also frame length
   
Output filename format must include '%06d' which will be replaced by the image sequence number.

Examples:
  pyraw2dng.py -M -w 1280 -l 1024 test.raw
  pyraw2dng.py -w 336 -l 96 test.raw test_output/test_%06d.DNG
```
