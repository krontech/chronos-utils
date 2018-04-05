#!/usr/bin/python
# coding=UTF-8

# this is a test of the debayer technique shown in:
# Low-complexity color demosaicing algorithm based on integrated gradients
# Journal of Electronic Imaging 19(2), 021104 (Apr–Jun 2010)
# https://pdfs.semanticscholar.org/5964/80130d42d9ed5ef6e0bb31677bdb2a8925f5.pdf
#

import sys
import struct
import os
import time
import array
import getopt
import platform
import errno


inputFilename = "S:\\KronTech\\Raw\\testScene_000002 (1).dng"

# set up the image binary data
rawFile = open(inputFilename, "rb")
rawDNG = rawFile.read()

# this will itterate through DNGs to find the raw image data
def parseIFD(rawFile, ifdOffset):
    foundIFDList = []
    stripOffset = None
    validImageFound = False
    width = 0
    height = 0
    ifdLength = struct.unpack_from("<H", rawFile, ifdOffset)[0]
    for i in range(ifdLength):
        tagID, tagDataType, tagDataCount, tagValue = struct.unpack_from("<HHII", rawFile, ifdOffset+2+(i*12))
        if tagID == 254 and tagValue == 0:
            validImageFound = True
            
        if tagID == 273:
            stripOffset = tagValue

        if tagID == 330:
            foundIFDList.append(tagValue)

        if tagID == 256:
            width = tagValue

        if tagID == 257:
            height = tagValue

    nextIFD = struct.unpack_from("<I", rawFile, ifdOffset+2 + ifdLength*12)[0]

    if nextIFD > 0:
        foundIFDList.append(nextIFD)

    if not validImageFound:
        for ifd in foundIFDList:
            stripOffset, width, height = parseIFD(rawFile, ifd)

    return stripOffset, width, height
        
ifdOffset = struct.unpack_from("<I", rawDNG, 4)[0]
stripOffset, hres, vres = parseIFD(rawDNG, ifdOffset)

if not stripOffset:
    print "Image data not found"
    sys.exit(0)

print "Image data found at offset: 0x%08X %dx%d" % (stripOffset, hres, vres)

rawImage = [hres, vres, array.array('H', rawDNG[stripOffset:(stripOffset + 2*hres*vres)])]

            
def getPixel(rawImage, x, y):
    # make sure the selected pixel is within the image while keeping it in bayer format
    while x < 0:
        x += 2
    while x >= rawImage[0]:
        x -= 2
    while y < 0:
        y += 2
    while y >= rawImage[1]:
        y -= 2

    value = rawImage[2][x+(y*rawImage[0])]
    return value

#===============================================================================================================
# From here down is the test

integrationGradientEW = []
for y in range(vres/2):
    integrationGradientEW.append(array.array('i', hres))

integrationGradientNS = []
for y in range(vres):
    integrationGradientEW.append(array.array('i', hres/2))


for y in range(vres>>1):
    for x in range(hres):
        integrationGradientEW[y][x] = (1  * getPixel(rawImage, x-2, y) +
                                       -3 * getPixel(rawImage, x-1, y) +
                                       4  * getPixel(rawImage,   x, y) +
                                       -3 * getPixel(rawImage, x+1, y) +
                                       1  * getPixel(rawImage, x+2, y)) / 6

for y in range(vres):
    for x in range(hres>>1):
        integrationGradientNS[y][x] = (1  * getPixel(rawImage, x-2, y) +
                                       -3 * getPixel(rawImage, x-1, y) +
                                       4  * getPixel(rawImage,   x, y) +
                                       -3 * getPixel(rawImage, x+1, y) +
                                       1  * getPixel(rawImage, x+2, y)) / 6
        


# G Interpolation
    

    # R/G Interpolation

    # R/B Interpolation

    # RGB to Lab

    # Homogeneity Map

    # Output
