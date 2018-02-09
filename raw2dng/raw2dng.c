/****************************************************************************
 *  Copyright (C) 2013-2017 Kron Technologies Inc <http://www.krontech.ca>. *
 *                                                                          *
 *  This program is free software: you can redistribute it and/or modify    *
 *  it under the terms of the GNU General Public License as published by    *
 *  the Free Software Foundation, either version 3 of the License, or       *
 *  (at your option) any later version.                                     *
 *                                                                          *
 *  This program is distributed in the hope that it will be useful,         *
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of          *
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           *
 *  GNU General Public License for more details.                            *
 *                                                                          *
 *  You should have received a copy of the GNU General Public License       *
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.   *
 ****************************************************************************

Converts raw binary files to Adobe DNG.
gcc -o raw2dng raw2dng.c -O4 -Wall -lm -ljpeg -ltiff -ljpeg
Requires LibTIFF 3.8.0 plus a patch.

Based on elphel_dng written by Dave Coffin for Berkeley
Engineering and Research.

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <math.h>
#include <jpeglib.h>
#include <tiffio.h>
#include <stdint.h>


enum
{
	SUCCESS = 0,
	ERR_FILE_ERROR,
	ERR_EOF_FOUND
};
	
enum
{
	PACK_TYPE_16B_LJ = 0, 
	PACK_TYPE_16B_RJ,
	PACK_TYPE_12B
};

int checkAndCreateDir(const char * dir)
{
	struct stat st;

	//Check for and create cal directory
	if(stat(dir, &st) != 0 || !S_ISDIR(st.st_mode))
	{
		printf("Path %s not found, creating.\n", dir);
		const int dir_err = mkdir(dir, S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH);
		if (-1 == dir_err)
		{
			printf("Error creating directory!\n");
			return ERR_FILE_ERROR;
		}
	}
	else
		printf("Path %s found, no need to create.\n", dir);

	return SUCCESS;
}

int writeTiff(FILE * fp, struct tm tm, const char * origFilename, const char * fileName, uint32_t xRes, uint32_t yRes, uint32_t frame, int packType)
{
	static const short CFARepeatPatternDim[] = { 2,2 };
	//This is the matrix that converts XYZ to the camera color space, not the other way around as the name implies. Compute the inverse of the cam to XYZ matrix and put it here.
	static const float cam_xyz[] =
	{1.7716, -0.5404, -0.1674, -0.2845, 1.2494, 0.0247, -0.2300, 0.6236, 0.6471};
	//{ 1.7324, -0.5415, -0.1561, -0.2725, 1.2467, 0.0194, -0.2057, 0.6289, 0.6900 }; //D50 CIECAM02 for LUX1310
	//{ 2.005,-0.771,-0.269, -0.752,1.688,0.064, -0.149,0.283,0.745 }; //Old matrix that came with elphel_dng
	//This is the white balance matrix, this seems to need to be 1 over the white balance values
	static const float neutral[] = {1.0/1.1921, 1.0/1.0, 1.0/1.0935}; //{ 0.807133, 1.0, 0.913289 };
	long sub_offset=0, white;
	uint16_t buf[2048];
	float gam;
	int row;
	unsigned short curve[4096];
	char datetime[64];
	int ret_in;
	TIFF *tif;

	switch(packType)
	{
		case PACK_TYPE_16B_RJ:
			white=0x0fff;
		break;
		
		case PACK_TYPE_16B_LJ:
			white=0xfff0;
		break;
		
		case PACK_TYPE_12B:
			white=0x0fff;
		break;
	}
/*
	gam = 100.0;

	for (i=0; i < 4096; i++)
		curve[i] = 0x0fff * pow (i/4095.0, 100/gam) + 0.5;
*/
	sprintf (datetime, "%04d:%02d:%02d %02d:%02d:%02d",
	tm.tm_year+1900,tm.tm_mon+1,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);

	if (!(tif = TIFFOpen (fileName, "w"))) return ERR_FILE_ERROR;

	TIFFSetField (tif, TIFFTAG_SUBFILETYPE, 1);
	TIFFSetField (tif, TIFFTAG_IMAGEWIDTH, xRes >> 4);
	TIFFSetField (tif, TIFFTAG_IMAGELENGTH, yRes >> 4);
	TIFFSetField (tif, TIFFTAG_BITSPERSAMPLE, 8);
	TIFFSetField (tif, TIFFTAG_COMPRESSION, COMPRESSION_NONE);
	TIFFSetField (tif, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_RGB);
	TIFFSetField (tif, TIFFTAG_MAKE, "Kron Technologies");
	TIFFSetField (tif, TIFFTAG_MODEL, "Chronos 1.4");
	TIFFSetField (tif, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
	TIFFSetField (tif, TIFFTAG_SAMPLESPERPIXEL, 3);
	TIFFSetField (tif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
	TIFFSetField (tif, TIFFTAG_SOFTWARE, "raw2dng");
	TIFFSetField (tif, TIFFTAG_DATETIME, datetime);
	TIFFSetField (tif, TIFFTAG_SUBIFD, 1, &sub_offset);
	TIFFSetField (tif, TIFFTAG_DNGVERSION, "\001\001\0\0");
	TIFFSetField (tif, TIFFTAG_DNGBACKWARDVERSION, "\001\0\0\0");
	TIFFSetField (tif, TIFFTAG_UNIQUECAMERAMODEL, "Krontech Chronos 1.4");
	TIFFSetField (tif, TIFFTAG_COLORMATRIX1, 9, cam_xyz);
	TIFFSetField (tif, TIFFTAG_ASSHOTNEUTRAL, 3, neutral);
	TIFFSetField (tif, TIFFTAG_CALIBRATIONILLUMINANT1, 20);
	TIFFSetField (tif, TIFFTAG_ORIGINALRAWFILENAME, origFilename);

	memset (buf, 0, xRes);	// all-black thumbnail
	for (row=0; row < yRes >> 4; row++)
	{
		//printf("Writing thumb line %d\r\n", row);	
		TIFFWriteScanline (tif, buf, row, 0);
	}
	TIFFWriteDirectory (tif);

	TIFFSetField (tif, TIFFTAG_SUBFILETYPE, 0);
	TIFFSetField (tif, TIFFTAG_IMAGEWIDTH, xRes);
	TIFFSetField (tif, TIFFTAG_IMAGELENGTH, yRes);
	TIFFSetField (tif, TIFFTAG_BITSPERSAMPLE, 16);
	TIFFSetField (tif, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_CFA);
	TIFFSetField (tif, TIFFTAG_SAMPLESPERPIXEL, 1);
	TIFFSetField (tif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
	TIFFSetField (tif, TIFFTAG_CFAREPEATPATTERNDIM, CFARepeatPatternDim);
	TIFFSetField (tif, TIFFTAG_CFAPATTERN, 4, "\001\0\002\001");
	//TIFFSetField (tif, TIFFTAG_LINEARIZATIONTABLE, 4096, curve);	//Do we need this?
	TIFFSetField (tif, TIFFTAG_WHITELEVEL, 1, &white);

	ret_in = fseek (fp, (off_t) sizeof(unsigned short) * xRes *
					yRes * frame, SEEK_SET);

	if (ret_in == (off_t) -1)
	{
		printf("Error: Seek failed\r\n");
		TIFFClose (tif);
		return ERR_FILE_ERROR;
	}

	for (row=0; row < yRes; row++)
	{
		//printf("Writing line %d\r\n", row);

		ret_in = fread (buf, sizeof(unsigned short), xRes, fp);

		if(ret_in != xRes)
		{
			printf("Error: ret_in != width, ret_in = %d, widthBytes = %d\r\n", ret_in,
			yRes);
			TIFFClose (tif);
			remove(fileName);	//Delete the incompletely written file
			return ERR_EOF_FOUND;
		}
    
		TIFFWriteScanline (tif, buf, row, 0);
	}

	TIFFClose (tif);
	return SUCCESS;
}

int main (int argc, char **argv)
{
	int status=1, i;
	uint32_t xRes, yRes, packType = PACK_TYPE_16B_LJ;
	int maxFrames = 0x7FFFFFFF;
	struct stat st;
	struct tm tm;
	int ret_in;
	char filename[512];
	char outputPath[512];
	FILE *ifp;


	if (argc < 5)
	{
		printf("Usage: %s xRes yRes infile outfile [options]\n"
		"Example: %s 1280 720 inFile.raw outputFile -n 5 -f 16rj\n"
		"Options:\n"
		"  -n <number> - process only <number> frames (default: process all frames)\n"
		"  -f <format> - data packing type:\n"
		"    ""16""   - 16-bit left justified ('Raw 16bit' setting on camera) (default)\n"
		"    ""16rj"" - 16-bit right justified ('Raw 16RJ' setting on camera)\n"
		"    ""12""   - 12-bit packed ('Raw 12bit packed' setting on camera)\n",
		argv[0],argv[0]);
		return 1;
	}
	
	if(argc > 5)	//If we have any options
	{
		for(i = 5; i < argc; i++)	//For each option switch
		{
			if(0 == strcmp(argv[i], "-n"))	//-n number of frames
			{
				i++;
				
				if(i >= argc)
				{
					printf("Error: Incomplete arguments - number did not follow '-n' switch\n");
					return 1;
				}
				maxFrames = atoi(argv[i]);
				printf("Frame count limit set to %d\n", maxFrames);
			}	
			
			if(0 == strcmp(argv[i], "-f"))	//-f format
			{
				i++;
				
				if(i >= argc)
				{
					printf("Error: Incomplete arguments - format specifier did not follow -f switch\n");
					return 1;
				}
				
				if(0 == strcmp(argv[i], "16"))
				{
					packType = PACK_TYPE_16B_LJ;
					printf("Format: 16-bit left justified\n");
				}
				else if(0 == strcmp(argv[i], "16rj"))
				{
					packType = PACK_TYPE_16B_RJ;
					printf("Format: 16-bit right justified\n");	
				}
				else if(0 == strcmp(argv[i], "12"))
				{
					packType = PACK_TYPE_12B;
					printf("12-bit packed data format isn't yet supported\n");
					return 1;
				}
				else
				{
					printf("Format specifier ""%s"" is invalid, must be ""16"", ""16rj"", or ""12""\n", argv[i]);
					return 1;
				}
			}
		}
	}
	
	if (!(ifp = fopen (argv[3], "rb"))) {
		perror (argv[3]);
		return 1;
	}
	
	xRes = atoi(argv[1]);
	yRes = atoi(argv[2]);
	
	if(xRes % 16 || xRes == 0)
	{
		printf("Error: xRes not a multiple of 16");
		fclose (ifp);
		return status;
	}
	
	if(yRes % 2 || yRes == 0)
	{
		printf("Error: yRes not a multiple of 2");
		fclose (ifp);
		return status;
	}
  
  	stat (argv[3], &st);
	gmtime_r (&st.st_mtime, &tm);


	sprintf(outputPath, "./%s", argv[4]);	//File path is just the file name

	checkAndCreateDir(outputPath);
	

	i = 0;
	do
	{
		//If the user didn't specify the frame count, don't print the max
		if(maxFrames == 0x7FFFFFFF)	
			printf("Processing frame %d\r", i+1);
		else
			printf("Processing frame %d of %d\r", i+1, maxFrames);
		
		//Get destination filename and append number
		sprintf(filename, "%s/%s_%06d.dng", outputPath, argv[4], i+1);	

	  	ret_in = writeTiff(ifp, tm, argv[3], filename, xRes, yRes, i, packType);
	  	if(SUCCESS != ret_in)
	  	{
	  		printf("writeTiff returned error %d", ret_in);
	  	}
	  	i++;
  	}
  	while(SUCCESS == ret_in && i < maxFrames);
  
  	printf("\nDone!\r\n");

	fclose (ifp);
	return status;
}
