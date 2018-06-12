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
    return min(max_val, max(min_val, val))
def demConstrain(val, min_val, max_val):
    while val < min_val:
        val += 2
    while val >= max_val:
        val -= 2
    return val

inputFilename = "S:\\KronTech\\Raw\\testScene_000002.dng"
outputBase = "S:\\KronTech\\Raw\\test_igd\\"

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
    return value

#===============================================================================================================
# From here down is the test

print('001 - Original image')
image_out = open(outputBase+'001_image.data', 'wb')
for y in range(vres):
    for x in range(hres):
        image_out.write(struct.pack("<H", getPixel(rawImage, x, y)))

image_out.close()



print('002 - Calculating Integrated Gradients')

integrationGradientEWGB = {}
integrationGradientEWGR = {}
integrationGradientNSGB = {}
integrationGradientNSGR = {}
for y in range(vres//2):
    integrationGradientEWGB[y] = {}
    integrationGradientEWGR[y] = {}
    
for y in range(vres):
    integrationGradientNSGB[y] = {}
    integrationGradientNSGR[y] = {}


    
ig_ew = {}
ig_ns = {}
for y in range(vres):
    ig_ew[y] = {}
    ig_ns[y] = {}

for y in range(vres):
    for x in range(hres):
        IG = (1  * getPixel(rawImage, x-2, y) +
              -3 * getPixel(rawImage, x-1, y) +
              4  * getPixel(rawImage,   x, y) +
              -3 * getPixel(rawImage, x+1, y) +
              1  * getPixel(rawImage, x+2, y)) // 6

        if (x & 1):
            IG = -IG
        IG = abs(IG)
        IG = constrain(IG, 0, 65535)
        if (y & 1):
            integrationGradientEWGB[y//2][x] = IG
        else:
            integrationGradientEWGR[y//2][x] = IG

for y in range(0,vres,2):
    for x in range(hres):
        ig_ew[y][x] = 0
        for t in range(-1,2):
            ig_ew[y][x] += abs(integrationGradientEWGB[y//2][demConstrain(x+t,0,hres)] - integrationGradientEWGB[y//2][demConstrain(x+t-1,0,hres)])
            ig_ew[y][x] += abs(integrationGradientEWGR[y//2][demConstrain(x+t,0,hres)] - integrationGradientEWGR[y//2][demConstrain(x+t-1,0,hres)])
        ig_ew[y+1][x] = ig_ew[y][x]
            
for y in range(vres):
    for x in range(hres):
        IG = (1  * getPixel(rawImage, x, y-2) +
              -3 * getPixel(rawImage, x, y-1) +
              4  * getPixel(rawImage, x,   y) +
              -3 * getPixel(rawImage, x, y+1) +
              1  * getPixel(rawImage, x, y+2)) // 6
        if (y & 1):
            IG = -IG
        IG = abs(IG)
        IG = constrain(IG, 0, 65535)
        if (x & 1):
            integrationGradientNSGB[y][x//2] = IG
        else:
            integrationGradientNSGR[y][x//2] = IG

for y in range(vres):
    for x in range(0,hres,2):
        ig_ns[y][x] = 0
        for t in range(-1,2):
            ig_ns[y][x] += abs(integrationGradientNSGB[demConstrain(y+t,0,vres)][x//2] - integrationGradientNSGB[demConstrain(y+t-1,0,vres)][x//2])
            ig_ns[y][x] += abs(integrationGradientNSGR[demConstrain(y+t,0,vres)][x//2] - integrationGradientNSGR[demConstrain(y+t-1,0,vres)][x//2])
        ig_ns[y][x+1] = ig_ns[y][x]

print(' - writing')
IG_EWGB_out = open(outputBase+'002a_IG_EWGB.data', 'wb')
IG_EWGR_out = open(outputBase+'002b_IG_EWGR.data', 'wb')
IG_NSGB_out = open(outputBase+'002c_IG_NSGB.data', 'wb')
IG_NSGR_out = open(outputBase+'002d_IG_NSGR.data', 'wb')
IG_EW_out = open(outputBase+'002ab_IG_EW.data', 'wb')
IG_NS_out = open(outputBase+'002cd_IG_NS.data', 'wb')

IG_DEW_out = open(outputBase+'002ab_IG_delta_EW.data', 'wb')
IG_DNS_out = open(outputBase+'002cd_IG_delta_NS.data', 'wb')

for y in range(vres):
    for x in range(hres):
        if (y & 1):
            IG_EWGB_out.write(struct.pack("<H", integrationGradientEWGB[y//2][x]))
            IG_EW_out.write(struct.pack("<H", integrationGradientEWGB[y//2][x]))
        else:
            IG_EWGR_out.write(struct.pack("<H", integrationGradientEWGR[y//2][x]))
            IG_EW_out.write(struct.pack("<H", integrationGradientEWGR[y//2][x]))
        if (x & 1):
            IG_NSGB_out.write(struct.pack("<H", integrationGradientNSGB[y][x//2]))
            IG_NS_out.write(struct.pack("<H", integrationGradientNSGB[y][x//2]))
        else:
            IG_NSGR_out.write(struct.pack("<H", integrationGradientNSGR[y][x//2]))
            IG_NS_out.write(struct.pack("<H", integrationGradientNSGR[y][x//2]))

        IG_DEW_out.write(struct.pack("<H", ig_ew[y][x]))
        IG_DNS_out.write(struct.pack("<H", ig_ns[y][x]))

IG_EWGB_out.close()
IG_EWGR_out.close()
IG_NSGB_out.close()
IG_NSGR_out.close()
IG_EW_out.close()
IG_NS_out.close()
IG_DEW_out.close()
IG_DNS_out.close()

#------------------------------------------------------------------------------------------
print('003 - Green estimation')

h_greenInterp = {}
v_greenInterp = {}
d_greenInterp = {}
greenInterp = {}
interpDirection = {}
ig_delta_h = {}
ig_delta_v = {}
for y in range(vres):
    h_greenInterp[y] = {}
    v_greenInterp[y] = {}
    d_greenInterp[y] = {}
    greenInterp[y] = {}
    interpDirection[y] = {}
    ig_delta_h[y] = {}
    ig_delta_v[y] = {}

    
for y in range(vres):
    for x in range(hres):
        delta = ig_ew[y][x] - ig_ns[y][x]
        if abs(delta) < 200:
            interpDirection[y][x] = 20000
        elif delta > 0:
            interpDirection[y][x] = 30000
        else:
            interpDirection[y][x] = 10000

        if not ((x & 1) ^ (y & 1)):
            greenInterp[y][x] = getPixel(rawImage, x, y)
            h_greenInterp[y][x] = getPixel(rawImage, x, y)
            v_greenInterp[y][x] = getPixel(rawImage, x, y)
            d_greenInterp[y][x] = getPixel(rawImage, x, y)
        else:
            h_greenInterp[y][x] = ((getPixel(rawImage, x-1, y) + getPixel(rawImage, x+1, y))//2  +   (2*getPixel(rawImage, x, y) - getPixel(rawImage, x-2, y) - getPixel(rawImage, x+2, y))//6)
            v_greenInterp[y][x] = ((getPixel(rawImage, x, y-1) + getPixel(rawImage, x, y+1))//2  +   (2*getPixel(rawImage, x, y) - getPixel(rawImage, x, y-2) - getPixel(rawImage, x, y+2))//6)
            d_greenInterp[y][x] = (h_greenInterp[y][x] + v_greenInterp[y][x]) // 2

            h_greenInterp[y][x] = constrain(h_greenInterp[y][x], 0, 65535)
            v_greenInterp[y][x] = constrain(v_greenInterp[y][x], 0, 65535)
            d_greenInterp[y][x] = constrain(d_greenInterp[y][x], 0, 65535)

            if abs(delta) < 200:
                greenInterp[y][x] = d_greenInterp[y][x]
            elif delta > 0:
                greenInterp[y][x] = v_greenInterp[y][x]
            else:
                greenInterp[y][x] = h_greenInterp[y][x]
                
                

print(' - writing')
h_greenInterp_out   = open(outputBase+'003a_h_green.data', 'wb')
v_greenInterp_out   = open(outputBase+'003b_v_green.data', 'wb')
d_greenInterp_out   = open(outputBase+'003c_d_green.data', 'wb')
interpDirection_out = open(outputBase+'003d_interp.data', 'wb')
greenInterp_out     = open(outputBase+'003e_output.data', 'wb')

for y in range(vres):
    for x in range(hres):
        h_greenInterp_out.write(struct.pack("<H", h_greenInterp[y][x]))
        v_greenInterp_out.write(struct.pack("<H", v_greenInterp[y][x]))
        d_greenInterp_out.write(struct.pack("<H", d_greenInterp[y][x]))
        interpDirection_out.write(struct.pack("<H", interpDirection[y][x]))
        greenInterp_out.write(struct.pack("<H", greenInterp[y][x]))

h_greenInterp_out.close()
v_greenInterp_out.close()
d_greenInterp_out.close()
interpDirection_out.close()
greenInterp_out.close()

#------------------------------------------------------------------------------------------
print('004 - Enhance Green')

enhancedGreen = {}
for y in range(vres):
    enhancedGreen[y] = {}

for y in range(vres):
    for x in range(hres):
        if ((x & 1) ^ (y & 1)): # not a green sample
            d_east  = greenInterp[y][demConstrain(x+2,0,hres)] - getPixel(rawImage, x+2, y)
            d_west  = greenInterp[y][demConstrain(x-2,0,hres)] - getPixel(rawImage, x-2, y)
            d_north = greenInterp[demConstrain(y-2,0,vres)][x] - getPixel(rawImage, x, y-2)
            d_south = greenInterp[demConstrain(y+2,0,vres)][x] - getPixel(rawImage, x, y+2)
            d_center = greenInterp[y][x]                       - getPixel(rawImage, x, y)
            
            w_east  = 65536 // (abs(d_center - d_east) or 1)
            w_west  = 65536 // (abs(d_center - d_west) or 1)
            w_north = 65536 // (abs(d_center - d_north) or 1)
            w_south = 65536 // (abs(d_center - d_south) or 1)
            
            delta_g_colour = (w_east*d_east + w_west*d_west + w_north*d_north + w_south*d_south) / (w_east + w_west + w_north + w_south)
            beta = 0.33
            estimated_delta = beta*(d_center) + (1-beta)*(delta_g_colour)
            new_estimate = getPixel(rawImage, x, y) + int(estimated_delta)

            #if new_estimate > 65535 or new_estimate < 0:
            #    print("<%4d,%4d> [%d/%f,%d/%f,%d/%f,%d/%f]: %f, %f, %d, %d, %d" % (x, y, d_west, w_ew, d_north, w_ns, d_east, w_ew, d_south, w_ns, delta_g_colour, estimated_delta, getPixel(rawImage, x, y), greenInterp[y][x], new_estimate))
            new_estimate = constrain(new_estimate, 0, 65535)

            enhancedGreen[y][x] = int(new_estimate)
        else:
            enhancedGreen[y][x] = greenInterp[y][x]

print(' - writing')
enhancedGreen_out   = open(outputBase+'004_enhanced_green.data', 'wb')
for y in range(vres):
    for x in range(hres):
        enhancedGreen_out.write(struct.pack("<H", enhancedGreen[y][x]))
enhancedGreen_out.close()


#------------------------------------------------------------------------------------------
print('005 - RGB interpolation stage 1')


rgbInterp_partial = {}
for y in range(vres):
    rgbInterp_partial[y] = {}

for y in range(vres):
    for x in range(hres):
        if ((x & 1) ^ (y & 1)): # not a green sample
            d_northeast = greenInterp[demConstrain(y-1,0,vres)][demConstrain(x+1,0,hres)] - getPixel(rawImage, x+1, y-1)
            d_northwest = greenInterp[demConstrain(y-1,0,vres)][demConstrain(x-1,0,hres)] - getPixel(rawImage, x-1, y-1)
            d_southeast = greenInterp[demConstrain(y+1,0,vres)][demConstrain(x+1,0,hres)] - getPixel(rawImage, x+1, y+1)
            d_southwest = greenInterp[demConstrain(y+1,0,vres)][demConstrain(x-1,0,hres)] - getPixel(rawImage, x-1, y+1)

            delta_nw_se = 65536 / ((abs(greenInterp[demConstrain(y-2,0,vres)][demConstrain(x-2,0,hres)] - greenInterp[demConstrain(y-0,0,vres)][demConstrain(x-0,0,hres)]) +
                                    abs(greenInterp[demConstrain(y-1,0,vres)][demConstrain(x-1,0,hres)] - greenInterp[demConstrain(y+1,0,vres)][demConstrain(x+1,0,hres)]) + 
                                    abs(greenInterp[demConstrain(y+0,0,vres)][demConstrain(x+0,0,hres)] - greenInterp[demConstrain(y+2,0,vres)][demConstrain(x+2,0,hres)])) or 65535)
            
            delta_ne_sw = 65536 / ((abs(greenInterp[demConstrain(y-2,0,vres)][demConstrain(x+2,0,hres)] - greenInterp[demConstrain(y-0,0,vres)][demConstrain(x+0,0,hres)]) +
                                    abs(greenInterp[demConstrain(y-1,0,vres)][demConstrain(x+1,0,hres)] - greenInterp[demConstrain(y+1,0,vres)][demConstrain(x-1,0,hres)]) + 
                                    abs(greenInterp[demConstrain(y+0,0,vres)][demConstrain(x-0,0,hres)] - greenInterp[demConstrain(y+2,0,vres)][demConstrain(x-2,0,hres)])) or 65535)

            delta_total = delta_nw_se + delta_ne_sw
            try:
                delta_g_colour = (delta_nw_se*(d_northwest + d_southeast) + delta_ne_sw*(d_northeast + d_southwest)) // (2*delta_total)
            except ZeroDivisionError:
                print("Zero div: %d+%d = %d. |%d-%d|+|%d-%d|+|%d-%d|, |%d-%d|+|%d-%d|+|%d-%d|" %
                      (delta_nw_se,delta_ne_sw,delta_total,
                       greenInterp[demConstrain(y-2,0,vres)][demConstrain(x-2,0,hres)], greenInterp[demConstrain(y-0,0,vres)][demConstrain(x-0,0,hres)],
                       greenInterp[demConstrain(y-1,0,vres)][demConstrain(x-1,0,hres)], greenInterp[demConstrain(y+1,0,vres)][demConstrain(x+1,0,hres)],
                       greenInterp[demConstrain(y+0,0,vres)][demConstrain(x+0,0,hres)], greenInterp[demConstrain(y+2,0,vres)][demConstrain(x+2,0,hres)],
            
                       greenInterp[demConstrain(y-2,0,vres)][demConstrain(x+2,0,hres)], greenInterp[demConstrain(y-0,0,vres)][demConstrain(x+0,0,hres)],
                       greenInterp[demConstrain(y-1,0,vres)][demConstrain(x+1,0,hres)], greenInterp[demConstrain(y+1,0,vres)][demConstrain(x-1,0,hres)],
                       greenInterp[demConstrain(y+0,0,vres)][demConstrain(x-0,0,hres)], greenInterp[demConstrain(y+2,0,vres)][demConstrain(x-2,0,hres)]
                      ))
                delta_g_colour = 0
            rgbInterp_partial[y][x] = constrain(int(greenInterp[y][x] - delta_g_colour), 0, 65535)

            if (x > 500 and x < 510 and y > 200 and y < 210):
                print("<%d,%d> %f(%d,%d), %f(%d,%d) / %f  = %d-%f  = %d" % (x,y, delta_nw_se,d_northwest,d_southeast, delta_ne_sw,d_northeast,d_southwest, delta_total, greenInterp[y][x],delta_g_colour, rgbInterp_partial[y][x]))

        else:
            rgbInterp_partial[y][x] = 0

rgbInterp_out = open(outputBase+'005_rgb_partial_out.data', 'wb')

print(' - writing')
for y in range(vres):
    for x in range(hres):
        rgbInterp_out.write(struct.pack("<H", rgbInterp_partial[y][x]))

rgbInterp_out.close()


#------------------------------------------------------------------------------------------
print('006 - RGB interpolation stage 2 - complete')

rgbInterp = {}
for y in range(vres):
    rgbInterp[y] = {}

for y in range(vres):
    for x in range(hres):
        d_east   = greenInterp[demConstrain(y  ,0,vres)][demConstrain(x+1,0,hres)] - getPixel(rawImage,x+1,y  )
        d_west   = greenInterp[demConstrain(y  ,0,vres)][demConstrain(x-1,0,hres)] - getPixel(rawImage,x-1,y  )
        d_north  = greenInterp[demConstrain(y-1,0,vres)][demConstrain(x  ,0,hres)] - getPixel(rawImage,x  ,y-1)
        d_south  = greenInterp[demConstrain(y+1,0,vres)][demConstrain(x  ,0,hres)] - getPixel(rawImage,x  ,y+1)
        
        green = greenInterp[y][x]
        pos = (x & 1) | ((y & 1)<<1)
        if pos == 0:
            red   = constrain(green - (d_east  + d_west)  // 2, 0, 65535)
            blue  = constrain(green - (d_north + d_south) // 2, 0, 65535)
        elif pos == 1:
            red   = getPixel(rawImage,x,y)
            blue  = rgbInterp_partial[y][x]
        elif pos == 2:
            red   = rgbInterp_partial[y][x]
            blue  = getPixel(rawImage,x,y)
        else:
            red   = constrain(green - (d_north + d_south) // 2, 0, 65535)
            blue  = constrain(green - (d_east  + d_west)  // 2, 0, 65535)
        
        rgbInterp[y][x] = [red, green, blue]


        
rgbInterp_out = open(outputBase+'006_rgb_out.data', 'wb')

print(' - writing')
for y in range(vres):
    for x in range(hres):
        pix = rgbInterp[y][x]
        rgbInterp_out.write(struct.pack("<BBB", pix[0]>>8 & 0xFF, pix[1]>>8 & 0xFF, pix[2]>>8 & 0xFF))

rgbInterp_out.close()


#------------------------------------------------------------------------------------------
print('005 - RGB interpolation stage 1')


