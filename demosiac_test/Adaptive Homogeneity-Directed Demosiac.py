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
import math


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


rgb_to_lab = [[ 0.412453, 0.357580, 0.180423 ],
              [ 0.212671, 0.715160, 0.072169 ],
              [ 0.019334, 0.119193, 0.950227 ]]
xyz_cam = [[0.0,0.0,0.0],
           [0.0,0.0,0.0],
           [0.0,0.0,0.0]]
color_cal_matrix = [[ 1.2330,  0.6468, -0.7764],
	            [-0.3219,  1.6901, -0.3811],
	            [-0.0614, -0.6409,  1.5258]]
d65_white = [0.950456, 1.0, 1.088754]

for i in range(3):
    for j in range(3):
        for k in range(3):
            xyz_cam[i][j] += rgb_to_lab[i][k] * color_cal_matrix[k][j] / d65_white[i]

def getLab(data, x, y):
    pixel = getValue(data, x, y)
    out = [xyz_cam[0][0]*pixel[0] + xyz_cam[0][1]*pixel[1] + xyz_cam[0][2]*pixel[2],
           xyz_cam[1][0]*pixel[0] + xyz_cam[1][1]*pixel[1] + xyz_cam[1][2]*pixel[2],
           xyz_cam[2][0]*pixel[0] + xyz_cam[2][1]*pixel[1] + xyz_cam[2][2]*pixel[2]]
    return [(116*out[1]-16),
            (500*(out[0]-out[1])),
            (200*(out[1]-out[2]))]
           




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
ahdMap_out = open(outputBase+'003c_ahd_map.data', 'wb')
homogMap_H_out = open(outputBase+'003a_homog_H.data', 'wb')
homogMap_V_out = open(outputBase+'003b_homog_V.data', 'wb')
rgbOut_out = open(outputBase+'004_rgb_out.data', 'wb')
ahdOut_out = open(outputBase+'004b_ahd_out.data', 'wb')
gutter = 0
for y in range(vres):
    for x in range(hres):
        #p = [getValue(rgbInterpolation_V, x, y-2),
        #     getValue(rgbInterpolation_V, x, y-1),
        #     getValue(rgbInterpolation_V, x, y),
        #     getValue(rgbInterpolation_V, x, y+1),
        #     getValue(rgbInterpolation_V, x, y+2)]
        #v_homog = (abs(1  * p[0][0] +   -3 * p[1][0] +     4  * p[2][0] +   -3 * p[3][0] +     1  * p[4][0]) +
        #           abs(1  * p[0][1] +   -3 * p[1][1] +     4  * p[2][1] +   -3 * p[3][1] +     1  * p[4][1]) +
        #           abs(1  * p[0][2] +   -3 * p[1][2] +     4  * p[2][2] +   -3 * p[3][2] +     1  * p[4][2]))

        p = [[getLab(rgbInterpolation_H, x-1, y-1), getLab(rgbInterpolation_H, x, y-1), getLab(rgbInterpolation_H, x+1, y-1)],
             [getLab(rgbInterpolation_H, x-1, y  ), getLab(rgbInterpolation_H, x, y  ), getLab(rgbInterpolation_H, x+1, y  )],
             [getLab(rgbInterpolation_H, x-1, y+1), getLab(rgbInterpolation_H, x, y+1), getLab(rgbInterpolation_H, x+1, y+1)]]
        #p = [[getValue(rgbInterpolation_V, x-1, y-1), getValue(rgbInterpolation_V, x, y-1), getValue(rgbInterpolation_V, x+1, y-1)],
        #     [getValue(rgbInterpolation_V, x-1, y  ), getValue(rgbInterpolation_V, x, y  ), getValue(rgbInterpolation_V, x+1, y  )],
        #     [getValue(rgbInterpolation_V, x-1, y+1), getValue(rgbInterpolation_V, x, y+1), getValue(rgbInterpolation_V, x+1, y+1)]]


        p_l = [[p[0][0][0]+p[0][0][1]+p[0][0][2], p[0][1][0]+p[0][1][1]+p[0][1][2], p[0][2][0]+p[0][2][1]+p[0][2][2]],
               [p[1][0][0]+p[1][0][1]+p[1][0][2], p[1][1][0]+p[1][1][1]+p[1][1][2], p[1][2][0]+p[1][2][1]+p[1][2][2]],
               [p[2][0][0]+p[2][0][1]+p[2][0][2], p[2][1][0]+p[2][1][1]+p[2][1][2], p[2][2][0]+p[2][2][1]+p[2][2][2]]]
        
        #h_homog = (abs(-1  * p[0][0][0] +   2 * p[1][0][0] +     -1  * p[2][0][0]) +
        #           abs(-1  * p[0][0][1] +   2 * p[1][0][1] +     -1  * p[2][0][1]) +
        #           abs(-1  * p[0][0][2] +   2 * p[1][0][2] +     -1  * p[2][0][2]) +
        #           abs(-1  * p[0][1][0] +   2 * p[1][1][0] +     -1  * p[2][1][0]) +
        #           abs(-1  * p[0][1][1] +   2 * p[1][1][1] +     -1  * p[2][1][1]) +
        #           abs(-1  * p[0][1][2] +   2 * p[1][1][2] +     -1  * p[2][1][2]) +
        #           abs(-1  * p[0][2][0] +   2 * p[1][2][0] +     -1  * p[2][2][0]) +
        #           abs(-1  * p[0][2][1] +   2 * p[1][2][1] +     -1  * p[2][2][1]) +
        #           abs(-1  * p[0][2][2] +   2 * p[1][2][2] +     -1  * p[2][2][2]))

        h_homog = (abs(-1  * p_l[0][0] +   2 * p_l[1][0] +     -1  * p_l[2][0]) +
                   abs(-1  * p_l[0][1] +   2 * p_l[1][1] +     -1  * p_l[2][1]) +
                   abs(-1  * p_l[0][2] +   2 * p_l[1][2] +     -1  * p_l[2][2]))
        
        p = [[getValue(rgbInterpolation_H, x-1, y-1), getValue(rgbInterpolation_H, x, y-1), getValue(rgbInterpolation_H, x+1, y-1)],
             [getValue(rgbInterpolation_H, x-1, y  ), getValue(rgbInterpolation_H, x, y  ), getValue(rgbInterpolation_H, x+1, y  )],
             [getValue(rgbInterpolation_H, x-1, y+1), getValue(rgbInterpolation_H, x, y+1), getValue(rgbInterpolation_H, x+1, y+1)]]

        p_l = [[p[0][0][0]+p[0][0][1]+p[0][0][2], p[0][1][0]+p[0][1][1]+p[0][1][2], p[0][2][0]+p[0][2][1]+p[0][2][2]],
               [p[1][0][0]+p[1][0][1]+p[1][0][2], p[1][1][0]+p[1][1][1]+p[1][1][2], p[1][2][0]+p[1][2][1]+p[1][2][2]],
               [p[2][0][0]+p[2][0][1]+p[2][0][2], p[2][1][0]+p[2][1][1]+p[2][1][2], p[2][2][0]+p[2][2][1]+p[2][2][2]]]

        #v_homog = (abs(-1  * p[0][0][0] +   2 * p[0][1][0] +     -1  * p[0][2][0]) +
        #           abs(-1  * p[0][0][1] +   2 * p[0][1][1] +     -1  * p[0][2][1]) +
        #           abs(-1  * p[0][0][2] +   2 * p[0][1][2] +     -1  * p[0][2][2]) +
        #           abs(-1  * p[1][0][0] +   2 * p[1][1][0] +     -1  * p[1][2][0]) +
        #           abs(-1  * p[1][0][1] +   2 * p[1][1][1] +     -1  * p[1][2][1]) +
        #           abs(-1  * p[1][0][2] +   2 * p[1][1][2] +     -1  * p[1][2][2]) +
        #           abs(-1  * p[2][0][0] +   2 * p[2][1][0] +     -1  * p[2][2][0]) +
        #           abs(-1  * p[2][0][1] +   2 * p[2][1][1] +     -1  * p[2][2][1]) +
        #           abs(-1  * p[2][0][2] +   2 * p[2][1][2] +     -1  * p[2][2][2]))

        v_homog = (abs(-1  * p_l[0][0] +   2 * p_l[1][0] +     -1  * p_l[2][0]) +
                   abs(-1  * p_l[0][1] +   2 * p_l[1][1] +     -1  * p_l[2][1]) +
                   abs(-1  * p_l[0][2] +   2 * p_l[1][2] +     -1  * p_l[2][2]))

        #p = [getValue(rgbInterpolation_H, x-2, y),
        #     getValue(rgbInterpolation_H, x-1, y),
        #     getValue(rgbInterpolation_H, x, y),
        #     getValue(rgbInterpolation_H, x+1, y),
        #     getValue(rgbInterpolation_H, x+2, y)]
        #h_homog = (abs(1  * p[0][0] +   -3 * p[1][0] +     4  * p[2][0] +   -3 * p[3][0] +     1  * p[4][0]) +
        #           abs(1  * p[0][1] +   -3 * p[1][1] +     4  * p[2][1] +   -3 * p[3][1] +     1  * p[4][1]) +
        #           abs(1  * p[0][2] +   -3 * p[1][2] +     4  * p[2][2] +   -3 * p[3][2] +     1  * p[4][2]))
        #h_homog *= h_homog

        homogMap_V_out.write(struct.pack("<H", max(min(v_homog, 65535), 0)))
        homogMap_H_out.write(struct.pack("<H", max(min(h_homog, 65535), 0)))

        
        val = v_homog - h_homog
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

        # AHD original method
        
        lab = [[getLab(rgbInterpolation_H, x-1, y-1), getLab(rgbInterpolation_H, x, y-1), getLab(rgbInterpolation_H, x+1, y-1)],
               [getLab(rgbInterpolation_H, x-1, y  ), getLab(rgbInterpolation_H, x, y  ), getLab(rgbInterpolation_H, x+1, y  )],
               [getLab(rgbInterpolation_H, x-1, y+1), getLab(rgbInterpolation_H, x, y+1), getLab(rgbInterpolation_H, x+1, y+1)]]
        h_ldiff = [abs(lab[1][1][0] - lab[0][1][0]),
                   abs(lab[1][1][0] - lab[1][0][0]),
                   abs(lab[1][1][0] - lab[2][1][0]),
                   abs(lab[1][1][0] - lab[1][2][0])]
        h_abdiff = [(lab[1][1][1] - lab[0][1][1])**2 + (lab[1][1][2] - lab[0][1][2])**2,
                    (lab[1][1][1] - lab[1][0][1])**2 + (lab[1][1][2] - lab[1][0][2])**2,
                    (lab[1][1][1] - lab[2][1][1])**2 + (lab[1][1][2] - lab[2][1][2])**2,
                    (lab[1][1][1] - lab[1][2][1])**2 + (lab[1][1][2] - lab[1][2][2])**2]

        lab = [[getLab(rgbInterpolation_V, x-1, y-1), getLab(rgbInterpolation_V, x, y-1), getLab(rgbInterpolation_V, x+1, y-1)],
               [getLab(rgbInterpolation_V, x-1, y  ), getLab(rgbInterpolation_V, x, y  ), getLab(rgbInterpolation_V, x+1, y  )],
               [getLab(rgbInterpolation_V, x-1, y+1), getLab(rgbInterpolation_V, x, y+1), getLab(rgbInterpolation_V, x+1, y+1)]]
        v_ldiff = [abs(lab[1][1][0] - lab[0][1][0]),
                  abs(lab[1][1][0] - lab[1][0][0]),
                  abs(lab[1][1][0] - lab[2][1][0]),
                  abs(lab[1][1][0] - lab[1][2][0])]
        v_abdiff = [(lab[1][1][1] - lab[0][1][1])**2 + (lab[1][1][2] - lab[0][1][2])**2,
                    (lab[1][1][1] - lab[1][0][1])**2 + (lab[1][1][2] - lab[1][0][2])**2,
                    (lab[1][1][1] - lab[2][1][1])**2 + (lab[1][1][2] - lab[2][1][2])**2,
                    (lab[1][1][1] - lab[1][2][1])**2 + (lab[1][1][2] - lab[1][2][2])**2]

        leps = min(max(h_ldiff[0], h_ldiff[2]),
                   max(v_ldiff[1], v_ldiff[3]))
        abeps = min(max(h_abdiff[0], h_abdiff[2]),
                    max(v_abdiff[1], v_abdiff[3]))

        h_homog = 0
        v_homog = 0
        for i in range(4):
            if h_ldiff[i] <= leps and h_abdiff[i] <= abeps:
                h_homog += 1
            if v_ldiff[i] <= leps and v_abdiff[i] <= abeps:
                v_homog += 1
        
        if v_homog > h_homog:
            ahdMap_out.write(struct.pack("<H", 50000))
            ahdOut_out.write(struct.pack("<BBB", rgbInterpolation_V[y][x][0]>>4, rgbInterpolation_V[y][x][1]>>4, rgbInterpolation_V[y][x][2]>>4))
        elif v_homog < h_homog:
            ahdMap_out.write(struct.pack("<H", 10000))
            ahdOut_out.write(struct.pack("<BBB", rgbInterpolation_H[y][x][0]>>4, rgbInterpolation_H[y][x][1]>>4, rgbInterpolation_H[y][x][2]>>4))
        else:
            ahdMap_out.write(struct.pack("<H", 30000))
            ahdOut_out.write(struct.pack("<BBB",
                                         (rgbInterpolation_H[y][x][0]+rgbInterpolation_V[y][x][0])>>5,
                                         (rgbInterpolation_H[y][x][1]+rgbInterpolation_V[y][x][1])>>5,
                                         (rgbInterpolation_H[y][x][2]+rgbInterpolation_V[y][x][2])>>5))

homogMap_out.close()
homogMap_H_out.close()
homogMap_V_out.close()
rgbOut_out.close()
ahdOut_out.close()
ahdMap_out.close()

print('Done')
