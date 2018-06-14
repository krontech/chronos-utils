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
outputBase = "S:\\KronTech\\Raw\\test_loials_pipelined\\"

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


real_rawImage = {}
for y in range(vres):
    real_rawImage[y] = array.array('H', rawDNG[stripOffset+(hres*y*2):stripOffset+(hres*(y+1)*2)])
            
def getPixel(field, x, y):
    value = field[demConstrain(y,0,vres)][demConstrain(x,0,hres)]
    return value

def setPixel(field, x, y, value):
    field[demConstrain(y,0,vres)][demConstrain(x,0,hres)] = value

class bucketBregade(object):
    def __init__(self, type, length, dimensions=(1280,1024)):
        self.hres = dimensions[0]
        self.vres = dimensions[1]
        self.type = type
        self.length = length
        self.data = array.array(type, [0]*length*self.hres)
        #self.useMap = {}
    def next(self, value):
        self.data = self.data[1:] + array.array(self.type, [value])
    def __repr__(self):
        return repr(self.data)
    def __getitem__(self, key):
        if type(key) != tuple:
            raise TypeError('index must be a tuple/coordinate')
        x_off = key[0]
        y_off = key[1]
        offset = y_off*self.hres + x_off
        if offset < -(self.length*self.hres):
            raise ValueError('index too old (%d,%d = %d < %d)' % (x_off, y_off, offset, -(self.length*self.hres)))
        if offset > 0:
            raise ValueError('index must not be in the future (%d,%d = %d)' % (x_off, y_off, offset))
        #self.useMap[x_off,y_off] = self.useMap.setdefault((x_off,y_off), 0) + 1
        return self.data[(offset-1)]


def mask(nbits):
    return (2**nbits)-1

#===============================================================================================================
# From here down is the test

# rawImage (12bit)
#          ABCDEFGHIJK
#  _ ______________________
#  0 ______aaaaa...........
#  1 ......aaaaa...........
#  2 ......aaaaa...........
#  3 ......aaaaa...........
#  4 ......aaaaax.x........
#  5 ......................
#  6 ...........x.xy.......
#  7 .............yyy......
#  8 ..............y_______

# greenInterp (12bit)
#          ABCDEFGHIJK
#  0 ______________________
#  1 ______________________
#  2 ______________________
#  3 ______________________
#  4 __________Bx.x........
#  5 ............x.........
#  6 ...........x.xy.......
#  7 .............yyy......
#  8 ..............yz______

# enhanceEW / enhanceNS (12bit)
#          ABCDEFGHIJK
#  0 ______________________
#  1 ______________________
#  2 ______________________
#  3 ______________________
#  4 ___________x.x........
#  5 ............x.........
#  6 ...........x.x________
#  7 ______________________
#  8 ______________________

# idig_nwse / idig_nesw (5bit * 2)
#          ABCDEFGHIJK
#  0 ______________________
#  1 ______________________
#  2 ______________________
#  3 ______________________
#  4 __________A...........
#  5 ......................
#  6 .............x________
#  7 ______________________
#  8 ______________________

idig_nwse_line4_6 = bucketBregade('h', (hres*2)+2)
idig_nwse_6H = 0
idig_nwse_6H

# rgbInterp_partial (12bit)
#          ABCDEFGHIJK
#  0 ______________________
#  1 ______________________
#  2 ______________________
#  3 ______________________
#  4 ______________________
#  5 ______________________
#  6 _____________Xy.......
#  7 .............y.y......
#  8 ..............yz______

# dig_dir (1bit)
#          ABCDEFGHIJK
#  0 ______________________
#  1 ______________________
#  2 ______________________
#  3 ______________________
#  4 __________A...........
#  5 ......................
#  6 ......................
#  7 ......................
#  8 ...............z______

# output (36bit)
#          ABCDEFGHIJK
#  7 ______________________
#  8 _______________Z______

# (12*(8+2+4+2) + 10*(2) + 1*(4)) * hres = 216 (18 lines)




div_lookup_128_16 = {}
for i in range(128):
    div_lookup_128_16[i] = 65535//(i or 1)

#crossover_lookup = {}
#for i in range():
#    
#    crossover_lookup
#    div_lookup_64_5[i] = 64//(i or 1)



rawImage           = bucketBregade('H', 10, (212,200))
greenInterp        = bucketBregade('H', 10, (212,200))
enhanceEW          = bucketBregade('h', 10, (212,200))
enhanceNS          = bucketBregade('h', 10, (212,200))
integratedDir      = bucketBregade('B', 10, (212,200))
diagWeighting_NWSE = bucketBregade('B', 10, (212,200))
diagWeighting_NESW = bucketBregade('B', 10, (212,200))
rgbInterp_partial  = bucketBregade('H', 10, (212,200))
rOut               = bucketBregade('H', 10, (212,200))
gOut               = bucketBregade('H', 10, (212,200))
bOut               = bucketBregade('H', 10, (212,200))

rawImage_out           = open(outputBase+'000_rawImage.data', 'wb')
integratedDir_out      = open(outputBase+'001a_integratedDir.data', 'wb')
diagWeighting_NWSE_out = open(outputBase+'001b_diagWeighting_NWSE.data', 'wb')
diagWeighting_NESW_out = open(outputBase+'001c_diagWeighting_NESW.data', 'wb')
enhanceEW_out          = open(outputBase+'002a_enhanceEW.data', 'wb')
enhanceNS_out          = open(outputBase+'002b_enhanceNS.data', 'wb')
greenInterp_out        = open(outputBase+'002_greenInterp.data', 'wb')
rgbInterp_partial_out  = open(outputBase+'003_rgbInterpPartial.data', 'wb')
rgbInterp_out          = open(outputBase+'004_rgb_out.data', 'wb')



rawImage_offset = 0
for itteration in range(((200+12)*(200+7)) + 0): # vres
    # ---------------------------------------------------------------------------------------------
    # pixel input
    
    rawImage_xpos = rawImage_offset % (200+12)
    rawImage_ypos = rawImage_offset // (200+12)
    if rawImage_ypos < 200:
        if rawImage_xpos < 2:
            rawImage.next(getPixel(real_rawImage, rawImage_xpos+430, rawImage_ypos+650))
        elif rawImage_xpos < 8:
            rawImage.next(rawImage[-1,0])
        elif rawImage_xpos < 200+6:
            rawImage.next(getPixel(real_rawImage, rawImage_xpos+430-6, rawImage_ypos+650))
        else:
            rawImage.next(rawImage[-1,0])
    else:
        rawImage.next(0)

    rawImage_out.write(struct.pack("<H", rawImage[-2,-2]))

    if rawImage_xpos == 0:
        print('line %d' % (rawImage_ypos))
        
    # ---------------------------------------------------------------------------------------------
    # stage 1
    # weights and directions
    dig_ew = 0
    dig_ew +=   abs(2*((rawImage[-1,-4]>>8)-(rawImage[-3,-4]>>8)) - ((rawImage[ 0,-4]>>8)-(rawImage[-4,-4]>>8)))
    dig_ew += 2*abs(2*((rawImage[-1,-3]>>8)-(rawImage[-3,-3]>>8)) - ((rawImage[ 0,-3]>>8)-(rawImage[-4,-3]>>8)))
    dig_ew += 2*abs(2*((rawImage[-1,-2]>>8)-(rawImage[-3,-2]>>8)) - ((rawImage[ 0,-2]>>8)-(rawImage[-4,-2]>>8)))
    dig_ew += 2*abs(2*((rawImage[-1,-1]>>8)-(rawImage[-3,-1]>>8)) - ((rawImage[ 0,-1]>>8)-(rawImage[-4,-1]>>8)))
    dig_ew +=   abs(2*((rawImage[-1, 0]>>8)-(rawImage[-3, 0]>>8)) - ((rawImage[ 0, 0]>>8)-(rawImage[-4, 0]>>8)))
    dig_ew += 8*abs((rawImage[-3,-2]>>8) - (rawImage[-1,-2]>>8))
    dig_ew += 8*abs((rawImage[-4,-2]>>8) - (rawImage[-2,-2]>>8))
    dig_ew += 8*abs((rawImage[ 0,-2]>>8) - (rawImage[-2,-2]>>8))
    dig_ew = constrain(int(dig_ew)>>7, 0, 63)

    dig_ns = 0
    dig_ns +=   abs(2*((rawImage[-4, -1]>>8)-(rawImage[-4, -3]>>8)) - ((rawImage[-4,  0]>>8)-(rawImage[-4, -4]>>8)))
    dig_ns += 2*abs(2*((rawImage[-3, -1]>>8)-(rawImage[-3, -3]>>8)) - ((rawImage[-3,  0]>>8)-(rawImage[-3, -4]>>8)))
    dig_ns += 2*abs(2*((rawImage[-2, -1]>>8)-(rawImage[-2, -3]>>8)) - ((rawImage[-2,  0]>>8)-(rawImage[-2, -4]>>8)))
    dig_ns += 2*abs(2*((rawImage[-1, -1]>>8)-(rawImage[-1, -3]>>8)) - ((rawImage[-1,  0]>>8)-(rawImage[-1, -4]>>8)))
    dig_ns +=   abs(2*((rawImage[ 0, -1]>>8)-(rawImage[ 0, -3]>>8)) - ((rawImage[ 0,  0]>>8)-(rawImage[ 0, -4]>>8)))
    dig_ns += 8*abs((rawImage[-2, -3]>>8) - (rawImage[-2, -1]>>8))
    dig_ns += 8*abs((rawImage[-2, -4]>>8) - (rawImage[-2, -2]>>8))
    dig_ns += 8*abs((rawImage[-2,  0]>>8) - (rawImage[-2, -2]>>8))
    dig_ns = constrain(int(dig_ns)>>7, 0, 63)

    integratedDir.next(dig_ew <= dig_ns)
    if integratedDir[0,0]:
        integratedDir_out.write(struct.pack("<H", 0x4000))
    else:
        integratedDir_out.write(struct.pack("<H", 0x0000))
    
    dig_nwse = 0
    dig_nwse += abs((rawImage[-4, -4]>>8) - (rawImage[-2, -2]>>8))
    dig_nwse += abs((rawImage[-4, -3]>>8) - (rawImage[-2, -1]>>8))
    dig_nwse += abs((rawImage[-4, -2]>>8) - (rawImage[-2,  0]>>8))
    dig_nwse += abs((rawImage[-3, -4]>>8) - (rawImage[-1, -2]>>8))
    dig_nwse += abs((rawImage[-3, -3]>>8) - (rawImage[-1, -1]>>8))
    dig_nwse += abs((rawImage[-3, -2]>>8) - (rawImage[-1,  0]>>8))
    dig_nwse += abs((rawImage[-2, -4]>>8) - (rawImage[ 0, -2]>>8))
    dig_nwse += abs((rawImage[-2, -3]>>8) - (rawImage[ 0, -1]>>8))
    dig_nwse += abs((rawImage[-2, -2]>>8) - (rawImage[ 0,  0]>>8))
    dig_nwse = constrain(int(dig_nwse)>>3, 0, 63)
    
    dig_nesw = 0
    dig_nesw += abs((rawImage[ 0, -4]>>8) - (rawImage[-2, -2]>>8))
    dig_nesw += abs((rawImage[ 0, -3]>>8) - (rawImage[-2, -1]>>8))
    dig_nesw += abs((rawImage[ 0, -2]>>8) - (rawImage[-2,  0]>>8))
    dig_nesw += abs((rawImage[-1, -4]>>8) - (rawImage[-3, -2]>>8))
    dig_nesw += abs((rawImage[-1, -3]>>8) - (rawImage[-3, -1]>>8))
    dig_nesw += abs((rawImage[-1, -2]>>8) - (rawImage[-3,  0]>>8))
    dig_nesw += abs((rawImage[-2, -4]>>8) - (rawImage[-4, -2]>>8))
    dig_nesw += abs((rawImage[-2, -3]>>8) - (rawImage[-4, -1]>>8))
    dig_nesw += abs((rawImage[-2, -2]>>8) - (rawImage[-4,  0]>>8))
    dig_nesw = constrain(int(dig_nesw)>>3, 0, 63)

    diagWeighting_NESW.next(63 // (dig_nesw or 1))
    diagWeighting_NWSE.next(63 // (dig_nwse or 1))
    diagWeighting_NESW_out.write(struct.pack("<H", diagWeighting_NESW[0,0] << 10))
    diagWeighting_NWSE_out.write(struct.pack("<H", diagWeighting_NWSE[0,0] << 10))

    
    # ---------------------------------------------------------------------------------------------
    # stage 2
    # Green estimation

    if not (((rawImage_xpos) & 1) ^ ((rawImage_ypos) & 1)):
        next_green = rawImage[-2,-2]
    else:
        enhance_ew = (2*rawImage[-2,-2] - rawImage[-4,-2] - rawImage[ 0,-2]) // 3
        enhance_ns = (2*rawImage[-2,-2] - rawImage[-2,-4] - rawImage[-2, 0]) // 3
    
        if integratedDir[0,0]:
            next_green = constrain((rawImage[-3,-2] + rawImage[-1,-2] + enhance_ew) >> 1, 0, 0xFFFF)
        else:
            next_green = constrain((rawImage[-2,-3] + rawImage[-2,-1] + enhance_ns) >> 1, 0, 0xFFFF)

    greenInterp.next(next_green)
    greenInterp_out.write(struct.pack("<H", greenInterp[0,0]))

    
    # ---------------------------------------------------------------------------------------------
    # stage 3
    # RGB X-interpolation
    
    d_northeast = greenInterp[-1,-3] - rawImage[-1-2,-3-2]
    d_northwest = greenInterp[-3,-3] - rawImage[-3-2,-3-2]
    d_southeast = greenInterp[-1,-1] - rawImage[-1-2,-1-2]
    d_southwest = greenInterp[-3,-1] - rawImage[-3-2,-1-2]
    
    delta_g_colour = ((diagWeighting_NWSE[-2-2,-2-2]*(d_northwest+d_southeast) + diagWeighting_NESW[-2-2,-2-2]*(d_northeast + d_southwest)) * div_lookup_128_16[diagWeighting_NWSE[-2-2,-2-2]+diagWeighting_NESW[-2-2,-2-2]]) >> (1+16)
    rgbInterp_partial.next(constrain(int(greenInterp[-2,-2] - delta_g_colour), 0, 0xFFFF))
    rgbInterp_partial_out.write(struct.pack("<H", rgbInterp_partial[0,0]))
    
    
    # ---------------------------------------------------------------------------------------------
    # stage 4
    # The rest of interpolation
    d1_east  = greenInterp[-3,-4] - rawImage[-5,-6]
    d1_west  = greenInterp[-5,-4] - rawImage[-7,-6]
    d1_north = greenInterp[-4,-5] - rawImage[-6,-7]
    d1_south = greenInterp[-4,-3] - rawImage[-6,-5]
    
    d2_east  = greenInterp[-3,-4] - rgbInterp_partial[-1,-2]
    d2_west  = greenInterp[-5,-4] - rgbInterp_partial[-3,-2]
    d2_north = greenInterp[-4,-5] - rgbInterp_partial[-2,-3]
    d2_south = greenInterp[-4,-3] - rgbInterp_partial[-2,-1]
    
    green = greenInterp[-4,-4]
    pos = (rawImage_xpos & 1) | ((rawImage_ypos & 1)<<1)
    if pos == 0:
        if integratedDir[-4,-4]:
            red  = constrain(green - (d1_east + d1_west) // 2, 0, 0xFFFF)
            blue = constrain(green - (d2_east + d2_west) // 2, 0, 0xFFFF)
        else:
            red  = constrain(green - (d2_north + d2_south) // 2, 0, 0xFFFF)
            blue = constrain(green - (d1_north + d1_south) // 2, 0, 0xFFFF)
    elif pos == 1:
        red = rawImage[-6,-6]
        blue = rgbInterp_partial[-2,-2]
    elif pos == 2:
        red = rgbInterp_partial[-2,-2]
        blue = rawImage[-6,-6]
    else:
        if integratedDir[-4,-4]:
            red  = constrain(green - (d2_east + d2_west) // 2, 0, 0xFFFF)
            blue = constrain(green - (d1_east + d1_west) // 2, 0, 0xFFFF)
        else:
            red  = constrain(green - (d1_north + d1_south) // 2, 0, 0xFFFF)
            blue = constrain(green - (d2_north + d2_south) // 2, 0, 0xFFFF)
    
    rOut.next(red)
    gOut.next(green)
    bOut.next(blue)
            
    output_xOff = (rawImage_offset - (212*6+6)) % 212
    output_yOff = (rawImage_offset - (212*5+6)) // 212
    
    if 6 <= output_xOff < 206 and output_yOff > 0:
        rgbInterp_out.write(struct.pack("<BBB", rOut[0,0]>>8 & 0xFF, gOut[0,0]>>8 & 0xFF, bOut[0,0]>>8 & 0xFF))

    rawImage_offset += 1

#------------------------------------------------------------------------------------------



rawImage_out.close()
integratedDir_out.close()
diagWeighting_NESW_out.close()
diagWeighting_NWSE_out.close()
enhanceEW_out.close()
enhanceNS_out.close()
greenInterp_out.close()
rgbInterp_partial_out.close()
rgbInterp_out.close()
