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


inputFilename = "S:\\KronTech\\Raw\\testScene_000002.dng"
outputBase = "S:\\KronTech\\Raw\\test\\"

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
    print("Image data not found")
    sys.exit(0)

print("Image data found at offset: 0x%08X %dx%d" % (stripOffset, hres, vres))

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
    return value >> 4

#===============================================================================================================
# From here down is the test


    
# G Interpolation
print('-------------------------------------------------')
print("calculating green interpolation")
gInterpolation_H = {}
gInterpolation_V = {}
for y in range(-2,vres+2):
    gInterpolation_H[y] = {}
    gInterpolation_V[y] = {}

print(" - horizontal mapping")
for y in range(-2,vres+2):
    for x in range(-2,hres+2):
        gInterpolation_H[y][x] = (-1 * getPixel(rawImage, x-2,   y) +
                                  2  * getPixel(rawImage, x-1,   y) +
                                  2  * getPixel(rawImage,   x,   y) +
                                  2  * getPixel(rawImage, x+1,   y) +
                                  -1 * getPixel(rawImage, x+2,   y)) // 4

        if gInterpolation_H[y][x] > 4095: gInterpolation_H[y][x] = 4095
        if gInterpolation_H[y][x] <    0: gInterpolation_H[y][x] = 0

print(" - vertical mapping")
for y in range(-2,vres+2):
    for x in range(-2,hres+2):
        gInterpolation_V[y][x] = (-1 * getPixel(rawImage,   x, y-2) +
                                  2  * getPixel(rawImage,   x, y-1) +
                                  2  * getPixel(rawImage,   x,   y) +
                                  2  * getPixel(rawImage,   x, y+1) +
                                  -1 * getPixel(rawImage,   x, y+2)) // 4

        if gInterpolation_V[y][x] > 4095: gInterpolation_V[y][x] = 4095
        if gInterpolation_V[y][x] <    0: gInterpolation_V[y][x] = 0

print(" Writing to disk")
# write interpolation 
gInterpolation_H_out = open(outputBase+'001a_gInterpolation_H_out.data', 'wb')
gInterpolation_V_out = open(outputBase+'001b_gInterpolation_V_out.data', 'wb')
for y in range(vres):
    for x in range(hres):
        gInterpolation_H_out.write(struct.pack("<H", gInterpolation_H[y][x] << 4))
        gInterpolation_V_out.write(struct.pack("<H", gInterpolation_V[y][x] << 4))
    
        
# R/B Interpolation
print('-------------------------------------------------')
print('calculating R/B interpolation')

rgbInterpolation_H = {}
rgbInterpolation_V = {}
for y in range(vres):
    rgbInterpolation_H[y] = {}
    rgbInterpolation_V[y] = {}

rgbInterpolation_H_out = open(outputBase+'002a_rgbInterpolation_H_out.data', 'wb')
print(' - Horizontal')
for y in range(vres):
    for x in range(hres):
        hBlend = (getPixel(rawImage, x, y) +
                  (getPixel(rawImage, x-1, y) + getPixel(rawImage, x+1, y) -
                   gInterpolation_H[y][x-1] - gInterpolation_H[y][x+1])//2)
        vBlend = (getPixel(rawImage, x, y) +
                  (getPixel(rawImage, x, y-1) + getPixel(rawImage, x, y+1) -
                   gInterpolation_H[y-1][x] - gInterpolation_H[y+1][x])//2)
        xBlend = (gInterpolation_H[y][x] +
                  (getPixel(rawImage, x-1,y-1) + getPixel(rawImage, x+1,y-1) +
                   getPixel(rawImage, x-1,y+1) + getPixel(rawImage, x+1,y+1) -
                   gInterpolation_H[y-1][x-1] - gInterpolation_H[y-1][x+1] -
                   gInterpolation_H[y+1][x-1] - gInterpolation_H[y+1][x+1])//4)
        if hBlend < 0: hBlend = 0
        if hBlend > 4095: hBlend = 4095
        if vBlend < 0: vBlend = 0
        if vBlend > 4095: vBlend = 4095
        if xBlend < 0: xBlend = 0
        if xBlend > 4095: xBlend = 4095
        pos = (x & 1) | ((y & 1)<<1)
        if pos == 0:
            red = hBlend
            green = getPixel(rawImage,x,y)
            blue = vBlend
        elif pos == 1:
            red = getPixel(rawImage,x,y)
            green = gInterpolation_H[y][x]
            blue = xBlend
        elif pos == 2:
            red = xBlend
            green = gInterpolation_H[y][x]
            blue = getPixel(rawImage,x,y)
        else:
            red = vBlend
            green = getPixel(rawImage,x,y)
            blue = hBlend
        rgbInterpolation_H[y][x] = [red, green, blue]
        rgbInterpolation_H_out.write(struct.pack("<BBB", red>>4, green>>4, blue>>4))
rgbInterpolation_H_out.close()

rgbInterpolation_V_out = open(outputBase+'002b_rgbInterpolation_V_out.data', 'wb')
print(' - Vertical')
for y in range(vres):
    for x in range(hres):
        hBlend = (getPixel(rawImage, x, y) +
                  (getPixel(rawImage, x-1, y) + getPixel(rawImage, x+1, y) -
                   gInterpolation_V[y][x-1] - gInterpolation_V[y][x+1])//2)
        vBlend = (getPixel(rawImage, x, y) +
                  (getPixel(rawImage, x, y-1) + getPixel(rawImage, x, y+1) -
                   gInterpolation_V[y-1][x] - gInterpolation_V[y+1][x])//2)
        xBlend = (gInterpolation_V[y][x] +
                  (getPixel(rawImage, x-1,y-1) + getPixel(rawImage, x+1,y-1) +
                   getPixel(rawImage, x-1,y+1) + getPixel(rawImage, x+1,y+1) -
                   gInterpolation_V[y-1][x-1] - gInterpolation_V[y-1][x+1] -
                   gInterpolation_V[y+1][x-1] - gInterpolation_V[y+1][x+1])//4)
        if hBlend < 0: hBlend = 0
        if hBlend > 4095: hBlend = 4095
        if vBlend < 0: vBlend = 0
        if vBlend > 4095: vBlend = 4095
        if xBlend < 0: xBlend = 0
        if xBlend > 4095: xBlend = 4095
        pos = (x & 1) | ((y & 1)<<1)
        if pos == 0:
            red = hBlend
            green = getPixel(rawImage,x,y)
            blue = vBlend
        elif pos == 1:
            red = getPixel(rawImage,x,y)
            green = gInterpolation_V[y][x]
            blue = xBlend
        elif pos == 2:
            red = xBlend
            green = gInterpolation_V[y][x]
            blue = getPixel(rawImage,x,y)
        else:
            red = vBlend
            green = getPixel(rawImage,x,y)
            blue = hBlend
        rgbInterpolation_V[y][x] = [red, green, blue]
        rgbInterpolation_V_out.write(struct.pack("<BBB", red>>4, green>>4, blue>>4))
rgbInterpolation_V_out.close()


def getValue(data, x, y):
    while x < 0: x+= 2
    while x >= len(data[0]): x -= 2
    while y < 0: y+= 2
    while y >= len(data): y -= 2
    return data[y][x]
    

rgbOut = {}
for y in range(vres):
    rgbOut[y] = {}

homogMap = {}
for y in range(vres):
    homogMap[y] = {}
    
# Homogeneity Map
print('-------------------------------------------------')
print('Selecting data')
homogMap_out = open(outputBase+'003_homogMap.data', 'wb')
rgbOut_out = open(outputBase+'004_rgb_out.data', 'wb')
gutter = 100
for y in range(vres):
    for x in range(hres):
        p = [getValue(rgbInterpolation_V, x, y-2),
             getValue(rgbInterpolation_V, x, y-1),
             getValue(rgbInterpolation_V, x, y),
             getValue(rgbInterpolation_V, x, y+1),
             getValue(rgbInterpolation_V, x, y+2)]
        v_homog = (abs(1  * p[0][0] +   -3 * p[1][0] +     4  * p[2][0] +   -3 * p[3][0] +     1  * p[4][0]) +
                   abs(1  * p[0][1] +   -3 * p[1][1] +     4  * p[2][1] +   -3 * p[3][1] +     1  * p[4][1]) +
                   abs(1  * p[0][2] +   -3 * p[1][2] +     4  * p[2][2] +   -3 * p[3][2] +     1  * p[4][2]))
        p = [getValue(rgbInterpolation_H, x-2, y),
             getValue(rgbInterpolation_H, x-1, y),
             getValue(rgbInterpolation_H, x, y),
             getValue(rgbInterpolation_H, x+1, y),
             getValue(rgbInterpolation_H, x+2, y)]
        h_homog = (abs(1  * p[0][0] +   -3 * p[1][0] +     4  * p[2][0] +   -3 * p[3][0] +     1  * p[4][0]) +
                   abs(1  * p[0][1] +   -3 * p[1][1] +     4  * p[2][1] +   -3 * p[3][1] +     1  * p[4][1]) +
                   abs(1  * p[0][2] +   -3 * p[1][2] +     4  * p[2][2] +   -3 * p[3][2] +     1  * p[4][2]))

        val = h_homog - v_homog
        homogMap[y][x] = val
        if homogMap[y][x] > 32767: homogMap[y][x] = 32767
        if homogMap[y][x] < -32767: homogMap[y][x] = -32767
        if (val > gutter):
            rgbOut[y][x] = rgbInterpolation_V[y][x]
        elif (val < -gutter):
            rgbOut[y][x] = rgbInterpolation_H[y][x]
        else:
            rgbOut[y][x] = [(rgbInterpolation_V[y][x][0] + rgbInterpolation_H[y][x][0])>>1,
                            (rgbInterpolation_V[y][x][1] + rgbInterpolation_H[y][x][1])>>1,
                            (rgbInterpolation_V[y][x][2] + rgbInterpolation_H[y][x][2])>>1]

        homogMap_out.write(struct.pack("<H", homogMap[y][x] + 32768))
        rgbOut_out.write(struct.pack("<BBB", rgbOut[y][x][0]>>4, rgbOut[y][x][1]>>4, rgbOut[y][x][2]>>4))

homogMap_out.close()
rgbOut_out.close()

print('Done')
