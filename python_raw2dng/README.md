pyraw2dng
=========

Overview
--------

This is meant to be a cross platform example on how to convert the raw (16bit standard) images from the Chronos1.4 high speed cameras to DNG.  This script will only work with 16 bit standard files and 12-bit packed files, but not the right-aligned "Raw16RJ" format, which has been removed as of software v0.3.0.

The script will not autodetect any settings - you must provide the correct frame size in the command line.

This will, however, automatically make a directory where it will put the output DNGs named after the input file, if you wish.

Requirements
------------

Python 3

Windows users will need Python, [available here](https://www.python.org/downloads/windows/)

Instructions
------------

Copy the script file, pyraw2dng.py and the raw 16 bit format video into the same directory.

Open a terminal in that directory and use a command similar to the following, but replacing (width) and (length) with the horizontal and vertical resolutions of the video, and (filename.raw) with the name of the raw video file.

### For Windows

    python pyraw2dng.py -w (width) -l (length) (filename.raw)
  
Under default install (without python in PATH), the first term "python" has to be replaced with "c:\Python37\python.exe"

### For Linux:

    ./pyraw2dng.py -w (width) -l (length) (filename.raw)

Optional arguments to add to decode 12-bit videos:

  * --packed option will decode the raw file as a 12-bit packed format generated from cameras with a software version v0.3.1 and newer.
  * --oldpack option will attempt to decode the raw file as a 12-bit packed format generated from software versions v0.3.0 and older. However due bugs in this encoding format, there may be off-by-one pixel errors in the encoded files. This is most noticeable as colour corruption after demosiac.

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
