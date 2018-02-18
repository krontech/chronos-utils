pyraw2dng
=========

Overview
--------

This is meant to be a cross platform example on how to convert the raw (16bit standard) images from the Chronos1.4 high speed cameras to DNG.

The script will not autodetect any settings - you must provide the correct frame size using the --lenght --width (-l/-w) parameters.

This will, however, automatically make a directory where it'll put the output DNGs named after the input file; if you wish.

Requirements
------------

Python 2.7

This might work in Python 3 as well but it has not been tested.

Help (via --help)
-----------------

```
pyraw2dng.py - Command line converter from Chronos1.4 raw format to DNG image sequence
Copywrite KronTech 2018.

pyraw2dng.py <options> <inputFilename> [<OutputFilenameFormat>]

Options:
 -h/--help   Display this help message
 -M/--mono   Raw data is mono
 -C/--color  Raw data is colour
 -w/--width  Frame width
 -l/--length Frame length
   
Output filename format must include '%06d' which will be replaced by the image sequence number.

Examples:
  pyraw2dng.py -M -w 1280 -l 1024 test.raw
  pyraw2dng.py -w 336 -l 96 test.raw test_output/test_%06d.DNG
```