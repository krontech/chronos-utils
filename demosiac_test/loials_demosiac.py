#!/usr/bin/python
# coding=UTF-8

# this is a test of the debayer technique shown in:
# Low-complexity color demosaicing algorithm based on integrated gradients
# Journal of Electronic Imaging 19(2), 021104 (Apr–Jun 2010)
# https://pdfs.semanticscholar.org/5964/80130d42d9ed5ef6e0bb31677bdb2a8925f5.pdf
# http://www.eie.polyu.edu.hk/~enyhchan/J-JEI-Low_complexity_color_demosaicing_algorithm_based_on_IG.pdf
#

import sys
import struct
import os
import time
import array
import getopt
import platform
import errno

def constrain(val, min_val, max_val):
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    return min(max_val, max(min_val, val))
def demConstrain(val, min_val, max_val):
    while val < min_val:
        val += 2
    while val >= max_val:
        val -= 2
    return val

inputFilename = "S:\\KronTech\\Raw\\testScene_000002.dng"
outputBase = "S:\\KronTech\\Raw\\test_loials\\"

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


rawImage = {}
for y in range(vres):
    rawImage[y] = array.array('H', rawDNG[stripOffset+(hres*y*2):stripOffset+(hres*(y+1)*2)])
            
def getPixel(field, x, y):
    value = field[demConstrain(y,0,vres)][demConstrain(x,0,hres)]
    return value

def setPixel(field, x, y, value):
    field[demConstrain(y,0,vres)][demConstrain(x,0,hres)] = value

#===============================================================================================================
# From here down is the test

div_lookup = {}
for i in range(128):
    div_lookup[i] = 65535//(i or 1)


    
print('001 - Original image')
image_out = open(outputBase+'001_image.data', 'wb')
for y in range(vres):
    for x in range(hres):
        image_out.write(struct.pack("<H", getPixel(rawImage, x, y)))

image_out.close()



print('002 - Calculating Integrated Gradients')

# delta integrated gradients
dig_ew = {}
dig_ns = {}
dig_nwse = {}
dig_nesw = {}
dig_dir = {}
# inverse delta integrated gradients
idig_nwse = {}
idig_nesw = {}
for y in range(vres):
    dig_dir[y] = array.array('B', [0]*hres)
    dig_ew[y] = array.array('H', [0]*hres)
    dig_ns[y] = array.array('H', [0]*hres)
    dig_nwse[y] = array.array('H', [0]*hres)
    dig_nesw[y] = array.array('H', [0]*hres)
    idig_nwse[y] = array.array('H', [0]*hres)
    idig_nesw[y] = array.array('H', [0]*hres)


for y in range(vres):
    for x in range(hres):
        dig_ew[y][x] = 0
        dig_ns[y][x] = 0
        dig_nwse[y][x] = 0
        dig_nesw[y][x] = 0
        #for i in range(-2,0):
        dig_ew[y][x] +=   abs(2*((getPixel(rawImage, x+1, y-2)>>8)-(getPixel(rawImage, x-1, y-2)>>8)) - ((getPixel(rawImage, x+2, y-2)>>8)-(getPixel(rawImage, x-2, y-2)>>8)))
        dig_ew[y][x] += 2*abs(2*((getPixel(rawImage, x+1, y-1)>>8)-(getPixel(rawImage, x-1, y-1)>>8)) - ((getPixel(rawImage, x+2, y-1)>>8)-(getPixel(rawImage, x-2, y-1)>>8)))
        dig_ew[y][x] += 2*abs(2*((getPixel(rawImage, x+1, y  )>>8)-(getPixel(rawImage, x-1, y  )>>8)) - ((getPixel(rawImage, x+2, y  )>>8)-(getPixel(rawImage, x-2, y  )>>8)))
        dig_ew[y][x] += 2*abs(2*((getPixel(rawImage, x+1, y+1)>>8)-(getPixel(rawImage, x-1, y+1)>>8)) - ((getPixel(rawImage, x+2, y+1)>>8)-(getPixel(rawImage, x-2, y+1)>>8)))
        dig_ew[y][x] +=   abs(2*((getPixel(rawImage, x+1, y+2)>>8)-(getPixel(rawImage, x-1, y+2)>>8)) - ((getPixel(rawImage, x+2, y+2)>>8)-(getPixel(rawImage, x-2, y+2)>>8)))
        dig_ew[y][x] += 8*abs((getPixel(rawImage, x-1, y)>>8) - (getPixel(rawImage, x+1, y)>>8))
        dig_ew[y][x] += 8*abs((getPixel(rawImage, x-2, y)>>8) - (getPixel(rawImage, x  , y)>>8))
        dig_ew[y][x] += 8*abs((getPixel(rawImage, x+2, y)>>8) - (getPixel(rawImage, x  , y)>>8))
        
        dig_ns[y][x] +=   abs(2*((getPixel(rawImage, x-2, y+1)>>8)-(getPixel(rawImage, x-2, y-1)>>8)) - ((getPixel(rawImage, x-2, y+2)>>8)-(getPixel(rawImage, x-2, y-2)>>8)))
        dig_ns[y][x] += 2*abs(2*((getPixel(rawImage, x-1, y+1)>>8)-(getPixel(rawImage, x-1, y-1)>>8)) - ((getPixel(rawImage, x-1, y+2)>>8)-(getPixel(rawImage, x-1, y-2)>>8)))
        dig_ns[y][x] += 2*abs(2*((getPixel(rawImage, x  , y+1)>>8)-(getPixel(rawImage, x  , y-1)>>8)) - ((getPixel(rawImage, x  , y+2)>>8)-(getPixel(rawImage, x  , y-2)>>8)))
        dig_ns[y][x] += 2*abs(2*((getPixel(rawImage, x+1, y+1)>>8)-(getPixel(rawImage, x+1, y-1)>>8)) - ((getPixel(rawImage, x+1, y+2)>>8)-(getPixel(rawImage, x+1, y-2)>>8)))
        dig_ns[y][x] +=   abs(2*((getPixel(rawImage, x+2, y+1)>>8)-(getPixel(rawImage, x+2, y-1)>>8)) - ((getPixel(rawImage, x+2, y+2)>>8)-(getPixel(rawImage, x+2, y-2)>>8)))
        dig_ns[y][x] += 8*abs((getPixel(rawImage, x, y-1)>>8) - (getPixel(rawImage, x, y+1)>>8))
        dig_ns[y][x] += 8*abs((getPixel(rawImage, x, y-2)>>8) - (getPixel(rawImage, x, y  )>>8))
        dig_ns[y][x] += 8*abs((getPixel(rawImage, x, y+2)>>8) - (getPixel(rawImage, x, y  )>>8))

        for i in range(-2,0):
            for j in range(-2,0):
                dig_nwse[y][x] += abs((getPixel(rawImage, x+i, y+j)>>8) - (getPixel(rawImage, x+i+2, y+j+2)>>8))
                dig_nesw[y][x] += abs((getPixel(rawImage, x-i, y+j)>>8) - (getPixel(rawImage, x-i-2, y+j+2)>>8))
        
        dig_ew[y][x] = constrain(int(dig_ew[y][x])>>7, 0, 63)
        dig_ns[y][x] = constrain(int(dig_ns[y][x])>>7, 0, 63)
        dig_nwse[y][x] = constrain(int(dig_nwse[y][x])>>3, 0, 63)
        dig_nesw[y][x] = constrain(int(dig_nesw[y][x])>>3, 0, 63)

        idig_nwse[y][x] = 63 // (dig_nwse[y][x] or 1)
        idig_nesw[y][x] = 63 // (dig_nesw[y][x] or 1)

        # find the direction as one bit
        dig_dir[y][x] = dig_ew[y][x] <= dig_ns[y][x]
        
print(' - writing')
DIG_EW_out = open(outputBase+'002aa_DIG_delta_EW.data', 'wb')
DIG_NS_out = open(outputBase+'002bb_DIG_delta_NS.data', 'wb')
DIG_NWSE_out = open(outputBase+'002cc_DIG_NWSE.data', 'wb')
DIG_NESW_out = open(outputBase+'002dd_DIG_NESW.data', 'wb')

for y in range(vres):
    for x in range(hres):
        DIG_EW_out.write(struct.pack("<H", dig_ew[y][x]))
        DIG_NS_out.write(struct.pack("<H", dig_ns[y][x]))
        DIG_NWSE_out.write(struct.pack("<H", dig_nwse[y][x]))
        DIG_NESW_out.write(struct.pack("<H", dig_nesw[y][x]))

DIG_EW_out.close()
DIG_NS_out.close()
DIG_NWSE_out.close()
DIG_NESW_out.close()

#------------------------------------------------------------------------------------------
print('003 - Green estimation')

h_greenInterp = {}
v_greenInterp = {}
d_greenInterp = {}
greenInterp = {}
interpDirection = {}
for y in range(vres):
    h_greenInterp[y] = {}
    v_greenInterp[y] = {}
    d_greenInterp[y] = {}
    greenInterp[y] = {}
    interpDirection[y] = {}

    
for y in range(vres):
    for x in range(hres):
        if not ((x & 1) ^ (y & 1)):
            greenInterp[y][x] = getPixel(rawImage, x, y)
        else:
            enhance_ew = (2*getPixel(rawImage, x, y) - getPixel(rawImage, x-2, y) - getPixel(rawImage, x+2, y))//3
            enhance_ns = (2*getPixel(rawImage, x, y) - getPixel(rawImage, x, y-2) - getPixel(rawImage, x, y+2))//3

            if dig_dir[y][x]:
                greenInterp[y][x] = constrain((getPixel(rawImage, x-1, y) + getPixel(rawImage, x+1, y) + enhance_ew) // (2), 0, 0xFFFF)
            else:
                greenInterp[y][x] = constrain((getPixel(rawImage, x, y-1) + getPixel(rawImage, x, y+1) + enhance_ns) // (2), 0, 0xFFFF)
                
            if (x < 10) and (y < 10):
                print("<%d,%d> %f: green[%d,%d,%d,%d], weight %d" %
                      (x, y,
                       greenInterp[y][x],
                       getPixel(rawImage, x-1, y), getPixel(rawImage, x+1, y), getPixel(rawImage, x, y-1), getPixel(rawImage, x, y+1),
                       dig_dir[y][x]))
                
                

print(' - writing')
greenInterp_out     = open(outputBase+'003_output.data', 'wb')

for y in range(vres):
    for x in range(hres):
        greenInterp_out.write(struct.pack("<H", constrain(int(greenInterp[y][x]),0,65535)))

greenInterp_out.close()




#------------------------------------------------------------------------------------------
print('004 - RGB interpolation stage 1')


rgbInterp_partial = {}
for y in range(vres):
    rgbInterp_partial[y] = {}

for y in range(vres):
    for x in range(hres):
        if ((x & 1) ^ (y & 1)): # not a green sample
            d_northeast = getPixel(greenInterp, x+1, y-1) - getPixel(rawImage, x+1, y-1)
            d_northwest = getPixel(greenInterp, x-1, y-1) - getPixel(rawImage, x-1, y-1)
            d_southeast = getPixel(greenInterp, x+1, y+1) - getPixel(rawImage, x+1, y+1)
            d_southwest = getPixel(greenInterp, x-1, y+1) - getPixel(rawImage, x-1, y+1)

            delta_g_colour = ((idig_nwse[y][x]*(d_northwest + d_southeast) + idig_nesw[y][x]*(d_northeast + d_southwest)) * div_lookup[idig_nwse[y][x]+idig_nesw[y][x]]) >> (1+16)
            rgbInterp_partial[y][x] = constrain(int(greenInterp[y][x] - delta_g_colour), 0, 65535)

        else:
            rgbInterp_partial[y][x] = 0

rgbInterp_out = open(outputBase+'004_rgb_partial_out.data', 'wb')

print(' - writing')
for y in range(vres):
    for x in range(hres):
        rgbInterp_out.write(struct.pack("<H", rgbInterp_partial[y][x]))

rgbInterp_out.close()




#------------------------------------------------------------------------------------------
print('005 - RGB interpolation stage 2 - complete')

rgbInterp = {}
for y in range(vres):
    rgbInterp[y] = {}

for y in range(vres):
    for x in range(hres):
        d1_east  = getPixel(greenInterp, x+1, y) - getPixel(rawImage,x+1,y)
        d1_west  = getPixel(greenInterp, x-1, y) - getPixel(rawImage,x-1,y)
        d1_north = getPixel(greenInterp, x, y-1) - getPixel(rawImage,x,y-1)
        d1_south = getPixel(greenInterp, x, y+1) - getPixel(rawImage,x,y+1)

        d2_east  = getPixel(greenInterp, x+1, y) - getPixel(rgbInterp_partial, x+1, y)
        d2_west  = getPixel(greenInterp, x-1, y) - getPixel(rgbInterp_partial, x-1, y)
        d2_north = getPixel(greenInterp, x, y-1) - getPixel(rgbInterp_partial, x, y-1)
        d2_south = getPixel(greenInterp, x, y+1) - getPixel(rgbInterp_partial, x, y+1)
        
        green = greenInterp[y][x]
        pos = (x & 1) | ((y & 1)<<1)
        if pos == 0:
            if dig_dir[y][x]:
                red   = constrain(green - (d1_east + d1_west) // (2), 0, 65535)
                blue  = constrain(green - (d2_east + d2_west) // (2), 0, 65535)
            else:
                red   = constrain(green - (d2_north + d2_south) // (2), 0, 65535)
                blue  = constrain(green - (d1_north + d1_south) // (2), 0, 65535)
        elif pos == 1:
            red   = getPixel(rawImage,x,y)
            blue  = rgbInterp_partial[y][x]
        elif pos == 2:
            red   = rgbInterp_partial[y][x]
            blue  = getPixel(rawImage,x,y)
        else:
            if dig_dir[y][x]:
                red   = constrain(green - (d2_east + d2_west) // (2), 0, 65535)
                blue  = constrain(green - (d1_east + d1_west) // (2), 0, 65535)
            else:
                red   = constrain(green - (d1_north + d1_south) // (2), 0, 65535)
                blue  = constrain(green - (d2_north + d2_south) // (2), 0, 65535)
        
        rgbInterp[y][x] = [red, green, blue]


        
rgbInterp_out = open(outputBase+'005_rgb_out.data', 'wb')

print(' - writing')
for y in range(vres):
    for x in range(hres):
        pix = rgbInterp[y][x]
        rgbInterp_out.write(struct.pack("<BBB", pix[0]>>8 & 0xFF, pix[1]>>8 & 0xFF, pix[2]>>8 & 0xFF))

rgbInterp_out.close()


#------------------------------------------------------------------------------------------


