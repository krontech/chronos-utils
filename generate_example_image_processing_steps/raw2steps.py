#!/usr/bin/python3 

"""
This script breaks a raw 16-bit video from a Chronos into discreet steps, so
that the video processing pipeline can be verified. Each step is output as an
uncompressed .data file. An associated .txt file contains some formatting
information and remarks. It roughly follows the first line of
https://en.wikipedia.org/wiki/Color_image_pipeline.

By default, this script only outputs one frame as this is usually what's needed
for reference. It chooses the middle frame of the video, assuming that's the
most stable. If the for-all-frames option is specified the script will produce
output folders for each frame. Similiarly, start and end frames (inclusive,
0-indexed like raw2dng) can be specified. If `frame` is specified, only that frame
will be output.


Known Issues:
  - Colour correction is terrible, so the matrix math is probably off.
  - We use the simplest linear demosaic, so colour artefacts do occur.
"""



import sys
import shutil
import os

import pdb
dbg = pdb.set_trace

bytes_per_channel = 2
channels_per_pixel = 4

# camSPECS CCM calculation: CIECAM02 RGB to sRGB & white balance
# (from camApp's camera.h defaultColorCalMatrix)
color_cal_matrix = [
	[+1.2330, +0.6468, -0.7764],
	[-0.3219, +1.6901, -0.3811],
	[-0.0614, -0.6409, +1.5258],
]
white_bal_matrix = [1.5150, 1, 1.1048]
gain = 1

final_color_correction_matrix = [
	# DDR 2018-04-16: We may need to apply the white bal matrix 012,012,012 instead of 000,111,222. However, this is how the camera does it at the moment.
	[color_cal_matrix[0][0] * white_bal_matrix[0] * gain,
	 color_cal_matrix[0][1] * white_bal_matrix[0] * gain,
	 color_cal_matrix[0][2] * white_bal_matrix[0] * gain],

	[color_cal_matrix[1][0] * white_bal_matrix[1] * gain,
	 color_cal_matrix[1][1] * white_bal_matrix[1] * gain,
	 color_cal_matrix[1][2] * white_bal_matrix[1] * gain],

	[color_cal_matrix[2][0] * white_bal_matrix[2] * gain,
	 color_cal_matrix[2][1] * white_bal_matrix[2] * gain,
	 color_cal_matrix[2][2] * white_bal_matrix[2] * gain],
]

# Convert 12-bit colour to 8-bit gamma-corrected colour. Taken from the camera's FPGA source.
gamma_lookup_table = [0, 1, 2, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 10, 11, 12, 13, 13, 14, 15, 15, 16, 16, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 23, 23, 24, 24, 25, 25, 26, 26, 26, 27, 27, 27, 28, 28, 29, 29, 29, 30, 30, 30, 31, 31, 31, 32, 32, 32, 33, 33, 33, 34, 34, 34, 35, 35, 35, 35, 36, 36, 36, 37, 37, 37, 37, 38, 38, 38, 39, 39, 39, 39, 40, 40, 40, 40, 41, 41, 41, 41, 42, 42, 42, 42, 43, 43, 43, 43, 44, 44, 44, 44, 45, 45, 45, 45, 45, 46, 46, 46, 46, 47, 47, 47, 47, 47, 48, 48, 48, 48, 49, 49, 49, 49, 49, 50, 50, 50, 50, 50, 51, 51, 51, 51, 51, 52, 52, 52, 52, 52, 53, 53, 53, 53, 53, 54, 54, 54, 54, 54, 54, 55, 55, 55, 55, 55, 56, 56, 56, 56, 56, 56, 57, 57, 57, 57, 57, 58, 58, 58, 58, 58, 58, 59, 59, 59, 59, 59, 59, 60, 60, 60, 60, 60, 60, 61, 61, 61, 61, 61, 61, 62, 62, 62, 62, 62, 62, 63, 63, 63, 63, 63, 63, 64, 64, 64, 64, 64, 64, 64, 65, 65, 65, 65, 65, 65, 66, 66, 66, 66, 66, 66, 66, 67, 67, 67, 67, 67, 67, 67, 68, 68, 68, 68, 68, 68, 68, 69, 69, 69, 69, 69, 69, 69, 70, 70, 70, 70, 70, 70, 70, 71, 71, 71, 71, 71, 71, 71, 72, 72, 72, 72, 72, 72, 72, 72, 73, 73, 73, 73, 73, 73, 73, 74, 74, 74, 74, 74, 74, 74, 74, 75, 75, 75, 75, 75, 75, 75, 76, 76, 76, 76, 76, 76, 76, 76, 77, 77, 77, 77, 77, 77, 77, 77, 78, 78, 78, 78, 78, 78, 78, 78, 79, 79, 79, 79, 79, 79, 79, 79, 79, 80, 80, 80, 80, 80, 80, 80, 80, 81, 81, 81, 81, 81, 81, 81, 81, 82, 82, 82, 82, 82, 82, 82, 82, 82, 83, 83, 83, 83, 83, 83, 83, 83, 83, 84, 84, 84, 84, 84, 84, 84, 84, 84, 85, 85, 85, 85, 85, 85, 85, 85, 85, 86, 86, 86, 86, 86, 86, 86, 86, 86, 87, 87, 87, 87, 87, 87, 87, 87, 87, 88, 88, 88, 88, 88, 88, 88, 88, 88, 89, 89, 89, 89, 89, 89, 89, 89, 89, 89, 90, 90, 90, 90, 90, 90, 90, 90, 90, 91, 91, 91, 91, 91, 91, 91, 91, 91, 91, 92, 92, 92, 92, 92, 92, 92, 92, 92, 92, 93, 93, 93, 93, 93, 93, 93, 93, 93, 93, 94, 94, 94, 94, 94, 94, 94, 94, 94, 94, 95, 95, 95, 95, 95, 95, 95, 95, 95, 95, 96, 96, 96, 96, 96, 96, 96, 96, 96, 96, 96, 97, 97, 97, 97, 97, 97, 97, 97, 97, 97, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 98, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 101, 102, 102, 102, 102, 102, 102, 102, 102, 102, 102, 102, 103, 103, 103, 103, 103, 103, 103, 103, 103, 103, 103, 104, 104, 104, 104, 104, 104, 104, 104, 104, 104, 104, 104, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, 105, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, 106, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 107, 108, 108, 108, 108, 108, 108, 108, 108, 108, 108, 108, 108, 109, 109, 109, 109, 109, 109, 109, 109, 109, 109, 109, 109, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 110, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 111, 112, 112, 112, 112, 112, 112, 112, 112, 112, 112, 112, 112, 112, 113, 113, 113, 113, 113, 113, 113, 113, 113, 113, 113, 113, 114, 114, 114, 114, 114, 114, 114, 114, 114, 114, 114, 114, 114, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 116, 116, 116, 116, 116, 116, 116, 116, 116, 116, 116, 116, 116, 117, 117, 117, 117, 117, 117, 117, 117, 117, 117, 117, 117, 117, 117, 118, 118, 118, 118, 118, 118, 118, 118, 118, 118, 118, 118, 118, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 119, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 120, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 121, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 122, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 123, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 124, 125, 125, 125, 125, 125, 125, 125, 125, 125, 125, 125, 125, 125, 125, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 126, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 127, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 129, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 130, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 131, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 132, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 133, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 134, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 135, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 136, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 137, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 138, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 139, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 140, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 141, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 142, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 143, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 144, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 145, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 146, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 147, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 148, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 149, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 150, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 151, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 152, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 153, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 154, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 155, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 156, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 157, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 158, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 159, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 160, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 161, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 162, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 163, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 164, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 165, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 166, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 167, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 168, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 169, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 170, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 171, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 172, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 173, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 174, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 175, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 177, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 178, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 179, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 180, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 181, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 182, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 183, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 184, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 185, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 186, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 187, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 188, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 189, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 190, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 191, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 192, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 193, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 194, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 195, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 196, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 197, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 198, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 201, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 202, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 203, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 204, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 205, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 206, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 207, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 208, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 209, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 210, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 211, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 212, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 213, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 214, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 215, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 216, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 217, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 218, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 219, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 220, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 221, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 222, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 223, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 224, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 225, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 226, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 227, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 228, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 229, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 230, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 231, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 232, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 233, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 234, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 235, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 236, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 237, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 238, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 239, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 241, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 242, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 243, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 244, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 245, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 246, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 247, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 248, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 249, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 250, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 251, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 252, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 253, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255]

c2b = lambda f: bytes([f>>8]) # channel to byte - discard some information to get 8 bit colour from 16. Used for .data files, which are importable into gimp.





######################################
# extract/parse command-line options #
######################################

def print_help():
	print("\nUsage: raw2steps input_video.raw width height [for-all-frames] [start=frame_number end=frame_number]|[frame=frame_number] [force]")
	print("\nExample: python3 raw2steps.py vid_2015-02-14_09-21-10.raw 800 600\n")

if len(sys.argv) < 4:
	print("Too few args.")
	print_help()
	sys.exit(1)

video = open(sys.argv[1], "rb")
if not video.seekable():
	print("Fatal Error: Your OS or filesystem does not support file seeking, which is required by this script.")
	sys.exit(2)

try:
	frame_w = int(sys.argv[2])
	if frame_w < 10:
		raise ValueError('Your frame width, in pixels, should probably be greater than 10.')
except ValueError as err:
	print_help()
	raise err
	
try:
	frame_h = int(sys.argv[3])
	if frame_h < 10:
		raise ValueError('Your frame height, in pixels, should probably be greater than 10.')
except ValueError as err:
	print_help()
	raise err

pixels_per_frame = frame_w * frame_h
bytes_per_frame = pixels_per_frame * bytes_per_channel # This might have to be aligned to 512-byte boundaries.

output_video = False
average_over_frames = 1
force_folder_creation = False

video_byte_length = os.path.getsize(video.name)
first_frame = 0
last_frame = (video_byte_length * 1) // bytes_per_frame # I don't know why ×4. Returns the middle frame though.
start_frame = (first_frame + last_frame)//2 # A representative frame, half-way through the video
end_frame = start_frame+1
current_frame = start_frame;

for opt in sys.argv[4:]:
	opt = opt.strip('-')
	
	if(opt == "for-all-frames"):
		start_frame = first_frame
		current_frame = first_frame
		end_frame = last_frame
		
	elif(opt[:5] == "frame"):
		start_frame = int(opt[6:])
		current_frame = start_frame
		end_frame = 1 + start_frame # End frame is, internally, not inclusive.
		
	elif(opt[:5] == "start"):
		start_frame = int(opt[6:])
		current_frame = start_frame
		
	elif(opt[:3] == "end"):
		end_frame = 1 + int(opt[4:])
		
	elif(opt == "force"):
		force_folder_creation = True
		
	else:
		print("Unknown option: " + opt)
		print_help()
		sys.exit(1)

if end_frame <= start_frame:
	print("Start frame (%d) must be before end frame (%d)." % (start_frame, end_frame-1))





###################################
# Set up output folder and files. #
###################################

output_folder = video.name[:-4] + ".steps" # Replace the assumed ".raw" extension with ".steps".
if os.path.exists(output_folder):
	if force_folder_creation:
		shutil.rmtree(output_folder)
	else:
		print("Error: Output folder " + output_folder + " already exists, and won't be overwritten for safety reasons. Delete or rename the folder before running this script again, or use --force to suppress this message.")
		sys.exit(3)
os.mkdir(output_folder)
os.chdir(output_folder)

with open("about.txt", "w") as about:
	about.write("""About These Files:

Each folder in this directory contains file representing an image processing
step in the camera. Hopefully, having the steps in plain python will lead to
faster iteration and bug fixes on the camera image pipeline.

Each file is titled something like:
	frame-number: the frame of the video processed
	step-number: the processing step the image was generated from
	--- information about the step ---
	.raw or .data: .raw is the 16-bit output from the step. (little-endian)
		.data is always formatted for easy import into Gimp, as rgb 8-bit
		output. .raw may also be imported into Gimp, starting from version
		2.10, by selecting "data" as the file format and choosing an
		appropriate raw format.



Specifically:
	xxxxxx.step-00.rgb.input-data.linear.non-debayered.raw
		This is a .raw file containing a slice of the input .raw file. It is
		calculated by figuring out the number of bytes per frame, and then
		multiplying by the number of frames. Step-wise:
		> bytes_per_channel = 2 #because we're working with 16-bit colour depth
		> pixels_per_frame = frame_w * frame_h
		> bytes_per_frame = pixels_per_frame * bytes_per_channel
		> video.seek(current_frame * bytes_per_frame)
		> raw_data.write(video.read(bytes_per_frame))
	
	xxxxxx.step-01.red.linear.rgb.data
		This file is 8-bit RGB data, which can be imported into Gimp. It
		contains the most-significant 8 bits of the red channel, as read
		from the .raw input file. The blue and green channels are zeroed.
		It is half the width and half the height of the input image,
		because the bayer filter only has ¼ of its pixels filtered red.
	
	xxxxxx.step-01.red.linear.single-channel.raw
		This file contains each 16-bit little-endian red value in the input
		frame, one after the other. It is half the width and half the height of
		the input image, because the bayer filter only has ¼ of its pixels red.
	
	xxxxxx.step-02.green.1.linear.rgb.data
		This file is 8-bit RGB data, which can be imported into Gimp. It
		contains the most-significant 8 bits of the first of two green
		channels. This green channel is on the odd rows (1st, 3rd, 5th, etc.)
		of the sensor. It is half the width and half the height of the input
		image, because — although half the bayer filter is green — it is
		convenient to think of the greens as two separate groups for now.
	
	xxxxxx.step-02.green.1.linear.single-channel.raw
		This file contains each 16-bit little-endian green value on an odd row
		of the camera sensor. See previous entry for details.
	
	xxxxxx.step-03-green.2.linear.rgb.data
		This file is 8-bit RGB data, which can be imported into Gimp. It
		contains the most-significant 8 bits of the second of two green
		channels. This green channel is on the even rows (2st, 4rd, 6th, etc.)
		of the sensor. It is half the width and half the height of the input
		image, because — although half the bayer filter is green — it is
		convenient to think of the greens as two separate groups for now.
	
	xxxxxx.step-03-green.2.linear.single-channel.raw
		This file contains each 16-bit little-endian green value on an even row
		of the camera sensor. See previous entry for details.
	
	xxxxxx.step-04.blue.linear.single-channel.data
		This file is 8-bit RGB data, which can be imported into Gimp. It
		contains the most-significant 8 bits of the blue channel, as read
		from the .raw input file. The red and green channels are zeroed.
		It is half the width and half the height of the input image,
		because the bayer filter only has ¼ of it's pixels blue.
	
	xxxxxx.step-04.blue.linear.single-channel.raw
		This file contains each 16-bit little-endian blue value in the input
		frame, one after the other. It is half the width and half the height of
		the input image because the bayer filter only has ¼ of its pixels blue.
	
	xxxxxx.step-05.rgb.debayered.linear.data
		This file is 8-bit RGB data, which can be imported into Gimp. The data
		in this image has been debayered, which means each pixel — instead of
		being a pure red, green, or blue colour — has pulled in the missing
		colours from the pixels around it and so has all three colours.
		Currently, we use the simplest linear debayering algorithm, which does
		not produce good results around sharp brightness gradients. (This
		effect is called colour fringing.)
	
	xxxxxx.step-05.rgb.debayered.linear.raw
		This file is as above, but instead of 8 bits, 16 bits are used. This
		format can't be imported into Gimp natively. However, if the data needs
		to be inspected, it can be imported as 16-bit greyscale at 3x the width
		of the input file. Columns alternate between displaying the r, g, and b
		values.
	
	xxxxxx.step-06.rgb.ciecam-color-corrected.linear.data
		This file is 8-bit RGB data, which can be imported into Gimp. The
		colour has now been converted into the CIECAM colour space. Colour
		values are still linear at this point.
	
	xxxxxx.step-06.rgb.ciecam-color-corrected.linear.raw
		This file contains 16-bit RGB data. (That is, each of the RGB channels
		is 16 bits wide, so each pixel is 48 bits of data.) The colour has now
		been converted into the CIECAM colour space. Colour values are still
		linear at this point.
	
	xxxxxx.step-07.rgb.gamma-corrected.raw.data
		This file is 8-bit RGB data, which can be imported into Gimp. The
		colour has now been passed through a 12-bit gamma lookup table, which
		converts the colours into non-linear colour space. (The Chronos uses
		12-bit colour internally for the most part.) Since both the raw and the
		data formats are the same for this step, there is only one file for
		them now.""")

# Output files will be initialized later.
raw_data   = None 
raw_r      = None
dat_r      = None
raw_g1     = None
dat_g1     = None
raw_g2     = None
dat_g2     = None
raw_b      = None
dat_b      = None
raw_rgb    = None
dat_rgb    = None
raw_ciecam = None
dat_ciecam = None
dat_gamma  = None





##########################
# Reading and Debayering #
##########################

class RawFrameChannels():
	# Return a channel from a frame of video.
	# Implemented as a frame-caching class because bilinear debayering is hard to implement on a stream, doubly so considering ignoring out-of-bounds pixels.
	
	def __init__(self, video):
		self.frame_data = video.read(bytes_per_frame)
		raw_data.write(self.frame_data)
	
	# So, this demands a bit of an explanation. And maybe an apology. There
	# are two things going on:
	# 1) The linear frame data is looked up by x/y coordinate. That is,
	#    basically, full lines (y*frame_w) + part of the line (frame_x).
	# 2) The consumer of this function, the bilinear demosaicing algorithm,
	#    would really like to look up pixels without having to worry if
	#    they're out of bounds. The logic there is complicated enough as it
	#    is. (If the pixels are out of bounds, they are to be ignored.)
	# Because the demosaicing algorithm only ever averages pixels mirrored
	# along a square line, if we return a mirrored pixel here then the
	# demosaicing algorithm will average a pixel with itself, thus
	# implementing the requirement to ignore the out of bound pixel without
	# ever actually having to do so itself.
	def get(self, x,y):
		safe_x = frame_w - abs(abs(x)-frame_w+1)-1 #This formula mirror-constrains x between 0 and frame_w.
		safe_y = frame_h - abs(abs(y)-frame_h+1)-1 #For example, if the frame was 5px tall, and we were asked for pixels -1,0,1,2,3,4,5,6, we'd give back pixels 1,0,1,2,3,4,5,4.
		index = safe_y*frame_w*bytes_per_channel + safe_x*bytes_per_channel
		
		return int.from_bytes(self.frame_data[index:index+bytes_per_channel], byteorder='little')

def debayered_frame_pixels(video):
	def corners(x,y):
		return ( channels.get(x-1,y-1) 
		       + channels.get(x-1,y+1) 
		       + channels.get(x+1,y-1) 
		       + channels.get(x+1,y+1) ) // 4
		
	def sides(x,y):
		return ( channels.get(x  ,y-1) 
		       + channels.get(x  ,y+1) 
		       + channels.get(x-1,y  ) 
		       + channels.get(x+1,y  ) ) // 4
		
	def verticals(x,y):
		return ( channels.get(x  ,y-1) 
		       + channels.get(x  ,y+1) ) // 2
		
	def horizontals(x,y):
		return ( channels.get(x-1,y  ) 
		       + channels.get(x+1,y  ) ) // 2
		
	def center(x,y):
		return ( channels.get(x  ,y  ) ) // 1
	
	channels = RawFrameChannels(video)
	
	# Yield a (linear) RGB pixel using bilinear debayering to get approximate colours for each missing channel.
	# For each bit, write to raw_b, raw_g1, raw_g2, or raw_r. This helps debug ordering and channel issues.
	# Our sensor has GRGRGR/BGBRBR pixels in it. ("stride"?) Each pixel is 16 bits, or 2 bytes, of data.
	for y in range(frame_h):
		for x in range(frame_w):
			
			if x==0:
				print('Processing frame %d… %d%%' % (current_frame, (y*100) // (frame_h-1)), end='\033[50D', flush=True)
			
			if x%2==0:
				if y%2==0: #green (odd rows)
					raw_g1.write(center(x,y).to_bytes(2, byteorder='little')) #ok
					dat_g1.write(bytes([0, c2b(center(x,y))[0], 0]))
					yield [horizontals(x,y), center(x,y), verticals(x,y)]
				else:      #blue
					raw_b.write(center(x,y).to_bytes(2, byteorder='little')) # off on side
					dat_b.write(bytes([0, 0, c2b(center(x,y))[0]]))
					yield [corners(x,y), sides(x,y), center(x,y)]
			else:
				if y%2==0: #red
					raw_r.write(center(x,y).to_bytes(2, byteorder='little')) #off on bottom
					dat_r.write(bytes([c2b(center(x,y))[0], 0, 0]))
					yield [center(x,y), sides(x,y), corners(x,y)]
				else:      #green (even rows)
					raw_g2.write(center(x,y).to_bytes(2, byteorder='little')) #off on bottom and side
					dat_g2.write(bytes([0, c2b(center(x,y))[0], 0]))
					yield [verticals(x,y), center(x,y), horizontals(x,y)]





#####################
# Colour Correction #
#####################

# Seek to start position of video.
video.seek(current_frame * bytes_per_frame)

for frame in range(start_frame, end_frame):
	#Create output files.
	raw_data   = open("%06d.step-00.rgb.input-data.linear.non-debayered.raw" % current_frame, "wb")
	raw_r      = open("%06d.step-01.red.linear.single-channel.raw" % current_frame, "wb")
	dat_r      = open("%06d.step-01.red.linear.rgb.data" % current_frame, "wb")
	raw_g1     = open("%06d.step-02.green.1.linear.single-channel.raw" % current_frame, "wb") # g1 and g2 are the two green channels from the camera sensor - our sensor pattern is clusters of [[g,r],[b,g]].
	dat_g1     = open("%06d.step-02.green.1.linear.rgb.data" % current_frame, "wb")
	raw_g2     = open("%06d.step-03-green.2.linear.single-channel.raw" % current_frame, "wb")
	dat_g2     = open("%06d.step-03-green.2.linear.rgb.data" % current_frame, "wb")
	raw_b      = open("%06d.step-04.blue.linear.single-channel.raw" % current_frame, "wb")
	dat_b      = open("%06d.step-04.blue.linear.single-channel.data" % current_frame, "wb")
	raw_rgb    = open("%06d.step-05.rgb.debayered.linear.raw" % current_frame, "wb")
	dat_rgb    = open("%06d.step-05.rgb.debayered.linear.data" % current_frame, "wb")
	raw_ciecam = open("%06d.step-06.rgb.ciecam-color-corrected.linear.raw" % current_frame, "wb")
	dat_ciecam = open("%06d.step-06.rgb.ciecam-color-corrected.linear.data" % current_frame, "wb")
	dat_gamma  = open("%06d.step-07.rgb.gamma-corrected.raw.data" % current_frame, "wb")
	
	for pixel in debayered_frame_pixels(video):
		for i in [0,1,2]: # r,g,b channels
			
			# Debayered individual channels, one fully-coloured pixel per sensor channel.
			raw_rgb.write(pixel[i].to_bytes(2, byteorder='little'))
			dat_rgb.write(c2b(pixel[i])) #discard lower byte and write
			
			
			# Colour temperature and white balance. (Colour profile) These are calculated as one step because the camApp multiplies their matrices together, and then the FPGA uses that matrix to perform the steps at the same time.
			fccm = final_color_correction_matrix
			channel = int(max(0, min(65535, 
				pixel[0]*fccm[i][0] + pixel[1]*fccm[i][1] + pixel[2]*fccm[i][2]
			)))
			
			raw_ciecam.write(channel.to_bytes(2, byteorder='little'))
			dat_ciecam.write(c2b(channel))
			
			
			# Gamma correction. (This is separate from the linear RGB to sRGB conversion. sRGB is normally applied by the program viewing the data - so we don't include it as a step here, because then we'd double-apply it.)
			# The following is the formula one might use, but we have a lookup table we use instead.
			# > channel = int(pow(channel/65535, 1/2.2) * 65535)
			channel = gamma_lookup_table[channel>>4]
			dat_gamma.write(bytes([channel]))
	
	raw_data.close()
	raw_r.close()
	dat_r.close()
	raw_g1.close()
	dat_g1.close()
	raw_g2.close()
	dat_g2.close()
	raw_b.close()
	dat_b.close()
	raw_rgb.close()
	dat_rgb.close()
	raw_ciecam.close()
	dat_ciecam.close()
	dat_gamma.close()
	
	print() # Keep the last "Processing frame" line we printed.
	current_frame += 1