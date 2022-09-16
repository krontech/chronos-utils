#!/usr/bin/python

# standard python imports
import sys
import struct
import os
import time
import array
import getopt
import platform
import errno

class Type:
    # TIFF Type Format = (Tag TYPE value, Size in bytes of one instance)
    Invalid = (0,0) # Should not be used
    Byte = (1,1) # 8-bit unsigned
    Ascii = (2,1) # 7-bit ASCII code
    Short = (3,2) # 16-bit unsigned
    Long = (4,4) # 32-bit unsigned
    Rational = (5,8) # 2 Longs, numerator:denominator
    Sbyte = (6,1) # 8 bit signed integer
    Undefined = (7,1) # 8 bit byte containing anything
    Sshort = (8,2) # 16 bit signed
    Slong = (9,4) # 32 bit signed
    Srational = (10,8) # 2 Slongs, numerator:denominator
    Float = (11,4) # 32bit float IEEE
    Double = (12,8) # 64bit double IEEE
    IFD = (13,4) # IFD (Same as Long)

Types = [(getattr(Type,n),n) for n in dir(Type) if n!="__doc__" and n!="__module__"]


class Tag:
    Invalid                     = (0,Type.Invalid)
    # TIFF/DNG/EXIF/CinemaDNG Tag Format = (TAG value, Tag Type)
    NewSubfileType              = (254,Type.Long)
    ImageWidth                  = (256,Type.Long)
    ImageLength                 = (257,Type.Long)
    BitsPerSample               = (258,Type.Short)
    Compression                 = (259,Type.Short)
    PhotometricInterpretation   = (262,Type.Short)
    FillOrder                   = (266,Type.Short)
    ImageDescription            = (270,Type.Ascii)
    Make                        = (271,Type.Ascii)
    Model                       = (272,Type.Ascii)
    StripOffsets                = (273,Type.Long)
    Orientation                 = (274,Type.Short)
    SamplesPerPixel             = (277,Type.Short)
    RowsPerStrip                = (278,Type.Short)
    StripByteCounts             = (279,Type.Long)
    XResolution                 = (282,Type.Rational)
    YResolution                 = (283,Type.Rational)
    PlanarConfiguration         = (284,Type.Short)
    ResolutionUnit              = (296,Type.Short)
    Software                    = (305,Type.Ascii)
    DateTime                    = (306,Type.Ascii)
    Artist                      = (315,Type.Ascii)
    TileWidth                   = (322,Type.Short)
    TileLength                  = (323,Type.Short)
    TileOffsets                 = (324,Type.Long)
    TileByteCounts              = (325,Type.Long)
    SubIFD                      = (330,Type.IFD)
    XMP_Metadata                = (700,Type.Undefined)
    CFARepeatPatternDim         = (33421,Type.Short)
    CFAPattern                  = (33422,Type.Byte)
    Copyright                   = (33432,Type.Ascii)
    ExposureTime                = (33434,Type.Rational)
    FNumber                     = (33437,Type.Rational)
    EXIF_IFD                    = (34665,Type.IFD)
    ExposureProgram             = (34850,Type.Short)
    PhotographicSensitivity     = (34855,Type.Short)
    SensitivityType             = (34864,Type.Short)
    ExifVersion                 = (36864,Type.Undefined)
    DateTimeOriginal            = (36867,Type.Ascii)
    ShutterSpeedValue           = (37377,Type.Srational)
    ApertureValue               = (37378,Type.Rational)
    ExposureBiasValue           = (37380,Type.Srational)
    MaxApertureValue            = (37381,Type.Rational)
    SubjectDistance             = (37382,Type.Rational)
    MeteringMode                = (37383,Type.Short)
    Flash                       = (37385,Type.Short)
    FocalLength                 = (37386,Type.Rational)
    TIFF_EP_StandardID          = (37398,Type.Byte)
    SubsecTime                  = (37520,Type.Ascii)
    SubsecTimeOriginal          = (37521,Type.Ascii)
    FocalPlaneXResolution       = (41486,Type.Rational)
    FocalPlaneYResolution       = (41487,Type.Rational)
    FocalPlaneResolutionUnit    = (41488,Type.Short)
    FocalLengthIn35mmFilm       = (41989,Type.Short)
    EXIFPhotoBodySerialNumber   = (42033,Type.Ascii)
    EXIFPhotoLensModel          = (42036,Type.Ascii)
    DNGVersion                  = (50706,Type.Byte)
    DNGBackwardVersion          = (50707,Type.Byte)
    UniqueCameraModel           = (50708,Type.Ascii)
    CFAPlaneColor               = (50710,Type.Byte)
    CFALayout                   = (50711,Type.Short)
    LinearizationTable          = (50712,Type.Short)
    BlackLevelRepeatDim         = (50713,Type.Short)
    BlackLevel                  = (50714,Type.Short)
    WhiteLevel                  = (50717,Type.Short)
    DefaultScale                = (50718,Type.Rational)
    DefaultCropOrigin           = (50719,Type.Long)
    DefaultCropSize             = (50720,Type.Long)
    ColorMatrix1                = (50721,Type.Srational)
    ColorMatrix2                = (50722,Type.Srational)
    CameraCalibration1          = (50723,Type.Srational)
    CameraCalibration2          = (50724,Type.Srational)
    AnalogBalance               = (50727,Type.Rational)
    AsShotNeutral               = (50728,Type.Rational)
    BaselineExposure            = (50730,Type.Srational)
    BaselineNoise               = (50731,Type.Rational)
    BaselineSharpness           = (50732,Type.Rational)
    BayerGreenSplit             = (50733,Type.Long)
    LinearResponseLimit         = (50734,Type.Rational)
    CameraSerialNumber          = (50735,Type.Ascii)
    AntiAliasStrength           = (50738,Type.Rational)
    ShadowScale                 = (50739,Type.Rational)
    DNGPrivateData              = (50740,Type.Byte)
    MakerNoteSafety             = (50741,Type.Short)
    CalibrationIlluminant1      = (50778,Type.Short)
    CalibrationIlluminant2      = (50779,Type.Short)
    BestQualityScale            = (50780,Type.Rational)
    RawDataUniqueID             = (50781,Type.Byte)
    ActiveArea                  = (50829,Type.Long)
    CameraCalibrationSignature  = (50931,Type.Ascii)
    ProfileCalibrationSignature = (50932,Type.Ascii)
    NoiseReductionApplied       = (50935,Type.Rational)
    ProfileName                 = (50936,Type.Ascii)
    ProfileHueSatMapDims        = (50937,Type.Long)
    ProfileHueSatMapData1       = (50938,Type.Float)
    ProfileHueSatMapData2       = (50939,Type.Float)
    ProfileEmbedPolicy          = (50941,Type.Long)
    PreviewApplicationName      = (50966,Type.Ascii)
    PreviewApplicationVersion   = (50967,Type.Ascii)
    PreviewSettingsDigest       = (50969,Type.Byte)
    PreviewColorSpace           = (50970,Type.Long)
    PreviewDateTime             = (50971,Type.Ascii)
    NoiseProfile                = (51041,Type.Double)
    TimeCodes                   = (51043,Type.Byte)
    FrameRate                   = (51044,Type.Srational)
    OpcodeList1                 = (51008,Type.Undefined)
    OpcodeList2                 = (51009,Type.Undefined)
    ReelName                    = (51081,Type.Ascii)
    BaselineExposureOffset      = (51109,Type.Srational) # 1.4 Spec says rational but mentions negative values?
    NewRawImageDigest           = (51111,Type.Byte)

# IfdNames = [n for n in dir(Tag) if n!="__doc__" and n!="__module__"]
# IfdValues = [getattr(Tag,n) for n in IfdNames]
# IfdIdentifiers = [getattr(Tag,n) for n in IfdNames]
# IfdTypes = [getattr(Tag,n) for n in IfdNames]
# IfdLookup = dict(list(zip(IfdIdentifiers,IfdNames)))

class dngHeader(object):
    def __init__(self):
        self.IFDOffset = 8

    def raw(self):
        return struct.pack("<sI", "II\x2A\x00", self.IFDOffset)

class dngTag(object):
    def __init__(self, tagType=Tag.Invalid, value=[]):
        self.Type = tagType
        self.TagId = tagType[0]
        self.DataType = tagType[1]
        self.DataCount = len(value)
        self.DataOffset = 0

        self.subIFD = None
        
        # encode the given data
        self.setValue(value)
        
        self.DataLength = len(self.Value)

        if (self.DataLength <= 4): self.selfContained = True
        else:                      self.selfContained = False

    def setValue(self, value):
        if   self.DataType == Type.Byte:      self.Value = struct.pack('<%sB' % len(value), *value)
        elif self.DataType == Type.Short:     self.Value = struct.pack('<%sH' % len(value), *value)
        elif self.DataType == Type.Long:      self.Value = struct.pack('<%sL' % len(value), *value)
        elif self.DataType == Type.Sbyte:     self.Value = struct.pack('<%sb' % len(value), *value)
        elif self.DataType == Type.Undefined: self.Value = struct.pack('<%sB' % len(value), *value)
        elif self.DataType == Type.Sshort:    self.Value = struct.pack('<%sh' % len(value), *value)
        elif self.DataType == Type.Slong:     self.Value = struct.pack('<%sl' % len(value), *value)
        elif self.DataType == Type.Float:     self.Value = struct.pack('<%sf' % len(value), *value)
        elif self.DataType == Type.Double:    self.Value = struct.pack('<%sd' % len(value), *value)
        elif self.DataType == Type.Rational:  self.Value = struct.pack('<%sL' % (len(value)*2), *[item for sublist in value for item in sublist]) # ... This... uhm... flattens the list of two value pairs
        elif self.DataType == Type.Srational: self.Value = struct.pack('<%sl' % (len(value)*2), *[item for sublist in value for item in sublist])
        elif self.DataType == Type.Ascii:
            self.Value = struct.pack('<%scx0L' % len(value), *[bytes(x, 'utf-8') for x in value])
            self.DataCount += 1
        elif self.DataType == Type.IFD:
            self.Value = b'\x00\x00\x00\x00'
            self.subIFD = value[0]
        self.Value += b'\x00'*(((len(self.Value)+3) & 0xFFFFFFFC) - len(self.Value))
        

    def setBuffer(self, buf, tagOffset, dataOffset):
        self.buf = buf
        self.TagOffset = tagOffset
        self.DataOffset = dataOffset
        if self.subIFD:
            #print "subIDF: 0x%08X, 0x%08X" % (self.TagOffset, self.DataOffset)
            self.subIFD.setBuffer(buf, self.DataOffset)
            
    def dataLen(self):
        if self.subIFD:
            return self.subIFD.dataLen()
        if self.selfContained:
            return 0
        else:
            return (len(self.Value) + 3) & 0xFFFFFFFC
        
    def write(self):
        if not self.buf:
            raise RuntimeError("buffer not initialized")

        #if not self.subIFD:
        #    print "Tag: %04X - 0x%08X, 0x%08X - %-30s %s" % (self.TagId, self.TagOffset, self.DataOffset, IfdLookup.get(self.TagId,"Unknown"), self.Value.encode('hex'))
        
        if self.subIFD:
            self.subIFD.write()
            tagData = struct.pack("<HHII", self.TagId, Type.Long[0], self.DataCount, self.DataOffset)
            struct.pack_into("<12s", self.buf, self.TagOffset, tagData)
        else:
            if self.selfContained:
                tagData = struct.pack("<HHI4s", self.TagId, self.DataType[0], self.DataCount, self.Value)
                struct.pack_into("<12s", self.buf, self.TagOffset, tagData)
            else:
                tagData = struct.pack("<HHII", self.TagId, self.DataType[0], self.DataCount, self.DataOffset)
                struct.pack_into("<12s", self.buf, self.TagOffset, tagData)
                struct.pack_into("<%ds" % (self.DataLength), self.buf, self.DataOffset, self.Value)
            
        
class dngIFD(object):
    def __init__(self):
        self.tags = []
        self.NextIFDOffset = 0

    def setBuffer(self, buf, offset):
        self.buf = buf
        self.offset = offset
        currentDataOffset = offset + 2 + len(self.tags)*12 + 4
        currentTagOffset = offset + 2
        for tag in sorted(self.tags, key=lambda x: x.TagId):
            tag.setBuffer(buf, currentTagOffset, currentDataOffset)
            currentTagOffset += 12
            currentDataOffset += tag.dataLen()
            #currentDataOffset = (currentDataOffset + 3) & 0xFFFFFFFC
            

    def dataLen(self):
        totalLength = 2 + len(self.tags)*12 + 4
        for tag in sorted(self.tags, key=lambda x: x.TagId):
            totalLength += tag.dataLen()
        return (totalLength + 3) & 0xFFFFFFFC

    def write(self):
        if not self.buf:
            raise RuntimeError("buffer not initialized")

        struct.pack_into("<H", self.buf, self.offset, len(self.tags))

        for tag in sorted(self.tags, key=lambda x: x.TagId):
            tag.write()

        #print "IDF: 0x%08X" % (self.offset)
        struct.pack_into("<I", self.buf, self.offset + 2 + len(self.tags)*12, self.NextIFDOffset)


class DNG(object):
    def __init__(self):
        self.IFDs = []
        self.ImageDataStrips = []
        self.StripOffsets = {}

    def setBuffer(self, buf):
        self.buf = buf

        currentOffset = 8

        for ifd in self.IFDs:
            ifd.setBuffer(buf, currentOffset)
            currentOffset += ifd.dataLen()
            

    def dataLen(self):
        totalLength = 8
        for ifd in self.IFDs:
            totalLength += (ifd.dataLen() + 3) & 0xFFFFFFFC

        for i in range(len(self.ImageDataStrips)):
            self.StripOffsets[i] = totalLength
            strip = self.ImageDataStrips[i]
            totalLength += (len(strip) + 3) & 0xFFFFFFFC
            
        return (totalLength + 3) & 0xFFFFFFFC

    def write(self):
        struct.pack_into("<ccbbI", self.buf, 0, b'I', b'I', 0x2A, 0x00, 8) # assume the first IFD happens immediately after header

        for ifd in self.IFDs:
            ifd.write()

        for i in range(len(self.ImageDataStrips)):
            self.buf[self.StripOffsets[i]:self.StripOffsets[i]+len(self.ImageDataStrips[i])] = self.ImageDataStrips[i]


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

## Read the frame data out and convert it to 16-bpp
def readFrame(file, width, length, bpp):
    try:
        if (bpp == 16):
            return file.read(width*length*2)

        elif (bpp == -12):
            ## Legacy (and probably broken) 12-bpp unpacking.
            frame = bytearray(width * length * 2)
            for off in range(0, len(frame), 4):
                pix = bytearray(file.read(3))
                a = (pix[2] << 4) + ((pix[1] & 0x0f) << 12)
                b = (pix[0] << 8) + ((pix[1] & 0xf0) << 0)
                frame[off + 0] = (a & 0x00ff) >> 0
                frame[off + 1] = (a & 0xff00) >> 8
                frame[off + 2] = (b & 0x00ff) >> 0
                frame[off + 3] = (b & 0xff00) >> 8

            return frame

        elif (bpp == 12):
            ## Read and convert to 16-bpp.
            frame = bytearray(width * length * 2)
            for off in range(0, len(frame), 4):
                pix = bytearray(file.read(3))
                a = (pix[0] << 4) + ((pix[1] & 0xf0) << 8)
                b = (pix[2] << 8) + ((pix[1] & 0x0f) << 4)
                frame[off + 0] = (a & 0x00ff) >> 0
                frame[off + 1] = (a & 0xff00) >> 8
                frame[off + 2] = (b & 0x00ff) >> 0
                frame[off + 3] = (b & 0xff00) >> 8
            
            return frame
    
    except:
        return None

def convertVideo(inputFilename, outputFilenameFormat, width, length, colour, bpp):
    dngTemplate = DNG()

    creationTime = creation_date(inputFilename)
    creationTimeString = time.strftime("%x %X", time.localtime(creationTime))

    # https://stackoverflow.com/questions/12517451/automatically-creating-directories-with-file-output
    if not os.path.exists(os.path.dirname(outputFilenameFormat % (0))):
        try:
            os.makedirs(os.path.dirname(outputFilenameFormat % (0)))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    # set up the image binary data
    rawFile = open(inputFilename, "rb")
    rawFrame = readFrame(rawFile, width, length, bpp)
    dngTemplate.ImageDataStrips.append(rawFrame)

    # set up the FULL IFD
    mainIFD = dngIFD()
    mainTagStripOffset = dngTag(Tag.StripOffsets, [0])
    mainIFD.tags.append(dngTag(Tag.NewSubfileType           , [0]))
    mainIFD.tags.append(dngTag(Tag.StripByteCounts          , [width*length*2]))
    mainIFD.tags.append(dngTag(Tag.ImageWidth               , [width]))
    mainIFD.tags.append(dngTag(Tag.ImageLength              , [length]))
    mainIFD.tags.append(dngTag(Tag.SamplesPerPixel          , [1]))
    mainIFD.tags.append(dngTag(Tag.BitsPerSample            , [16]))
    mainIFD.tags.append(dngTag(Tag.RowsPerStrip             , [length]))
    mainIFD.tags.append(dngTag(Tag.Compression              , [1])) # uncompressed
    
    if (colour):
        mainIFD.tags.append(dngTag(Tag.PhotometricInterpretation, [32803])) # bayer - i think
        mainIFD.tags.append(dngTag(Tag.CFARepeatPatternDim      , [2, 2]))
        mainIFD.tags.append(dngTag(Tag.CFAPattern               , [1, 0, 2, 1]))
    else:
        mainIFD.tags.append(dngTag(Tag.PhotometricInterpretation, [1]))
        
    mainIFD.tags.append(mainTagStripOffset)
    mainIFD.tags.append(dngTag(Tag.PlanarConfiguration      , [1]))
    
    mainIFD.tags.append(dngTag(Tag.WhiteLevel               , [65520]))
    
    mainIFD.tags.append(dngTag(Tag.Make                     , "Kron Technologies"))
    mainIFD.tags.append(dngTag(Tag.Model                    , "Chronos 1.4"))
    mainIFD.tags.append(dngTag(Tag.DateTime                 , creationTimeString))
    mainIFD.tags.append(dngTag(Tag.Software                 , "pyraw2dng"))
    mainIFD.tags.append(dngTag(Tag.Orientation              , [1]))
    
    mainIFD.tags.append(dngTag(Tag.DNGVersion               , [1, 1, 0, 0]))
    mainIFD.tags.append(dngTag(Tag.DNGBackwardVersion       , [1, 0, 0, 0]))
    mainIFD.tags.append(dngTag(Tag.UniqueCameraModel        , "Krontech Chronos 1.4"))
    mainIFD.tags.append(dngTag(Tag.ColorMatrix1             , [[15407, 10000], [-3218, 10000], [-1652, 10000],	#CIECAM16 color matrix for LUX1310, D55 illuminant
                                                               [-3799, 10000], [13260, 10000], [-408, 10000],
                                                               [-3047, 10000], [ 6673, 10000], [ 6774, 10000]]))
    mainIFD.tags.append(dngTag(Tag.AsShotNeutral            , [[10000, 15150], [10000, 10000], [10000, 11048]]))
    mainIFD.tags.append(dngTag(Tag.CalibrationIlluminant1   , [20]))

    dngTemplate.IFDs.append(mainIFD)

    totalLength = dngTemplate.dataLen()
    # this must happen after dataLen is calculated! (dataLen caches the offsets)
    mainTagStripOffset.setValue([dngTemplate.StripOffsets[0]])

    buf = bytearray(totalLength)
    dngTemplate.setBuffer(buf)

    frameNum = 0
    while(rawFrame):
        dngTemplate.ImageDataStrips[0] = rawFrame
        dngTemplate.write()

        outfile = open(outputFilenameFormat % frameNum, "wb")
        outfile.write(buf)
        outfile.close()

        # go onto next frame
        rawFrame = readFrame(rawFile, width, length, bpp)
        frameNum += 1



#=========================================================================================================
helptext = '''pyraw2dng.py - Command line converter from Chronos1.4 raw format to DNG image sequence
Version 0.1
Copyright 2018 Kron Technologies Inc.

pyraw2dng.py <options> <inputFilename> [<OutputFilenameFormat>]

Options:
 --help      Display this help message
 -M/--mono   Raw data is mono
 -C/--color  Raw data is colour
 -p/--packed Raw 12-bit packed data (default: 16-bit)
 --legacy    Legacy 12-bit packed data (v0.3.0 and earlier)
 -w/--width  Frame width
 -l/--length Frame length
 -h/--height Frame length (please use only one)
   
Output filename format must include '%06d' which will be replaced by the image sequence number.

Examples:
  pyraw2dng.py -M -w 1280 -l 1024 test.raw
  pyraw2dng.py -w 336 -l 96 test.raw test_output/test_%06d.DNG
'''


def main():
    width = None
    length = None
    colour = True
    inputFilename = None
    outputFilenameFormat = None
    bpp = 16
    
    try:
        options, args = getopt.getopt(sys.argv[1:], 'CMpw:l:h:',
            ['help', 'color', 'packed', 'mono', 'width', 'length', 'height', 'oldpack'])
    except getopt.error:
        print('Error: You tried to use an unknown option.\n\n')
        print(helptext)
        sys.exit(0)
        
    if len(sys.argv[1:]) == 0:
        print(helptext)
        sys.exit(0)
    
    for o, a in options:
        if o in ('--help'):
            print(helptext)
            sys.exit(0)

        elif o in ('-C', '--color'):
            colour = True

        elif o in ('-M', '--mono'):
            colour = False
        
        elif o in ('-p', '--packed'):
            bpp = 12
        
        elif o in ('--oldpack'):
            bpp = -12
        
        elif o in ('-l', '-h', '--length', '--height'):
            length = int(a)

        elif o in ('-w', '--width'):
            width = int(a)

    if len(args) < 1:
        print(helptext)
        sys.exit(0)

    elif len(args) == 1:
        inputFilename = args[0]
        dirname = os.path.splitext(inputFilename)[0]
        basename = os.path.basename(inputFilename)
        print(basename)
        outputFilenameFormat = dirname + '/frame_%06d.DNG'
    else:
        inputFilename = args[0]
        outputFilenameFormat = args[1]

    convertVideo(inputFilename, outputFilenameFormat, width, length, colour, bpp)

if __name__ == "__main__":
    main()

        
        
