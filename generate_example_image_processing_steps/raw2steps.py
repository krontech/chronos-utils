#!/usr/bin/python3 

"""
This script breaks a raw 16-bit video from a Chronos into discreet steps, so
that the video processing pipeline can be verified. Each step is output as an
uncompressed .data file. An associated .txt file contains some formatting
information and remarks. It roughly follows the first line of
https://en.wikipedia.org/wiki/Color_image_pipeline.

By default, it only outputs one frame as this is usually what's needed for
reference. It chooses the middle frame of the video, assuming that's the most
stable. If the denoise option is specified, it will average the middle hundred
frames of the raw video to get rid of sensor noise. This enables easier colour-
picker sampling. If the for-all-frames option is specified the script will
produce output folders for each frame, or group of hundred frames if denoising,
in the input .raw file.

Usage: raw2steps input_video.raw width height [denoise] [for-all-frames] [as-video] [force]
Example: python3 raw2steps.py vid_2015-02-14_09-21-10.raw 800 600 denoise

Known Issues:
  - There is always one pixel off, either top-left or bottom-right. Currently
    set to top-left because the rest of the math works out better that way.
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
	#DDR 2018-04-16: We may need to apply the white bal matrix 012,012,012 instead of 000,111,222. However, this is how the camera does it at the moment.
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

def print_help():
	print("\nUsage: raw2steps input_video.raw width height [denoise] [for-all-frames] [as-video]")
	print("\nExample: python3 raw2steps.py vid_2015-02-14_09-21-10.raw 800 600 denoise\n")

# extract/parse command-line options
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
bytes_per_frame = pixels_per_frame * bytes_per_channel #This might have to be aligned to 512-byte boundaries.

output_video = False
average_over_frames = 1
force_folder_creation = False

video_byte_length = os.path.getsize(video.name)
first_frame = 0
last_frame = (video_byte_length * 1) // bytes_per_frame #I don't know why ×4. Returns the middle frame though.
start_frame = (first_frame + last_frame)//2 #a representitive frame, half-way through the video
end_frame = start_frame+1
current_frame = start_frame;

for opt in sys.argv[4:]:
	if(opt == "denoise"):
		print("unimplimented")
		sys.exit(1)
	elif(opt == "for-all-frames"):
		print("unimplimented")
		sys.exit(1)
	elif(opt == "as-video"):
		print("unimplimented")
		sys.exit(1)
	elif(opt == "force"):
		force_folder_creation = True
	else:
		print("Unknown option: " + opt)
		print_help()
		sys.exit(1)

output_folder = "%s.%d.steps" % (video.name[:-4], start_frame) # Replace the assumed ".raw" extension with ".steps".
if os.path.exists(output_folder):
	if force_folder_creation:
		shutil.rmtree(output_folder)
	else:
		print("Error: Output folder " + output_folder + " already exists, and won't be overwritten for safety reasons. Delete or rename it before running this script again. (You can suppress this message with the force option.)")
		os.exit(3)
os.mkdir(output_folder)
os.chdir(output_folder)

raw_data= open(    "step-00.input-dat.linear.non-debayered.raw", "wb")
raw_r   = open(    "step-01.red.linear.single-channel.raw", "wb")
dat_r   = open(    "step-01.red.linear.rgb.data", "wb")
raw_g1  = open("step-02.green.1.linear.single-channel.raw", "wb") # g1 and g2 are the two green channels from the camera sensor - our sensor pattern is clusters of [[g,r],[b,g]].
dat_g1  = open("step-02.green.1.linear.rgb.data", "wb")
raw_g2  = open("step-03-green.2.linear.single-channel.raw", "wb")
dat_g2  = open("step-03-green.2.linear.rgb.data", "wb")
raw_b   = open(   "step-04.blue.linear.single-channel.raw", "wb")
dat_b   = open(   "step-04.blue.linear.single-channel.data", "wb")
raw_rgb = open( "step-05.rgb.debayered.linear.raw", "wb")
dat_rgb = open( "step-05.rgb.debayered.linear.data", "wb")
raw_srgb = open("step-06.sRGB.raw", "wb")
dat_srgb = open("step-06.sRGB.data", "wb")
raw_ciecam = open("step-07.sRGB.ciecam-color-corrected.raw", "wb")
dat_ciecam = open("step-07.sRGB.ciecam-color-corrected.data", "wb")

class RawFrameChannels():
	# Return a channel from a frame of video.
	# Implemented as a frame-caching class because bilinear debayering is hard to implement on a stream, doubly so considering ignoring out-of-bounds pixels. It's a lot to do at once.
	
	def __init__(self):
		self.frame_data = video.read(bytes_per_frame)
		raw_data.write(self.frame_data)
	
	def get(self, x,y):
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
		# ever actually having to do so.
		safe_x = frame_w - abs(abs(x)-frame_w+1)-1 #This formula mirror-constrains x between 0 and frame_w.
		safe_y = frame_h - abs(abs(y)-frame_h+1)-1 #There seems to be an issue where one pixel is off, either top-left or bottom-right alternately, but I'm not sure why. :/ 
		index = safe_y*frame_w*bytes_per_channel + safe_x*bytes_per_channel
		
		#if(x==250 and y==0):
		#	import pdb; pdb.set_trace()
		
		return int.from_bytes(self.frame_data[index:index+bytes_per_channel], byteorder='little')

c2b = lambda f: bytes([min(255, f//256)]) #channel to byte - discard some information to get 8 bit color from 16.

def frame_pixels():
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
	
	channels = RawFrameChannels()
	
	for y in range(frame_h):
		for x in range(frame_w):
			# Yield a (linear) RGB pixel using bilinear debayering to get approximate colours for each missing channel.
			# For each bit, write to raw_b, raw_g1, raw_g2, or raw_r. This helps debug ordering and channel issues.
			# Our sensor has GRGRGR/BGBRBR pixels in it. ("stride"?) Each pixel is 16 bits, or 2 bytes, of data.
			if x==0:
				print('Processing frame %d… %d%%' % (current_frame, (y*100) // frame_h), end='\n' and '\033[50D', flush=True)
			
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
		


# Set up raw stream of video.
video.seek(current_frame * bytes_per_frame)
for frames in range(start_frame, end_frame): #TODO: Make new folders for each frame, if more than one?
	for pixel in frame_pixels():
		for i in [0,1,2]: # r,g,b channels
			
			# Debayered individual channels, one fully-coloured pixel per sensor channel.
			raw_rgb.write(pixel[i].to_bytes(2, byteorder='little'))
			dat_rgb.write(c2b(pixel[i])) #discard lower byte and write
			
			
			# Linear RGB to sRGB (includes gamma correction)
			if pixel[i]/65535 <= 0.0031308: #65535 is max possible channel value
				pixel[i] = int(12.92 * pixel[i])
			else:
				pixel[i] = int((1.055 * pow(pixel[i]/65535, 1/2.4) - 0.055) * 65535)
			
			raw_srgb.write(pixel[i].to_bytes(2, byteorder='little'))
			dat_srgb.write(c2b(pixel[i]))
			
			
			# Colour temperature and white balance. (Colour profile) These are calculated as one step because the camApp multiplies their matrices together, and then the FPGA uses that matrix to perform the steps at the same time.
			fccm = final_color_correction_matrix
			pixel[i] = int(max(0, min(65535, pixel[0]*fccm[i][0] + pixel[1]*fccm[i][1] + pixel[2]*fccm[i][2])))
			
			raw_ciecam.write(pixel[i].to_bytes(2, byteorder='little'))
			dat_ciecam.write(c2b(pixel[i]))
		
		
		
		# Run raw2dng.py over the output. (But fix the embedded matrices first…)