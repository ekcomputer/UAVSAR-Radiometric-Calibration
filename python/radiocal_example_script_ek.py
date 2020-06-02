# -*- coding: utf-8 -*-
"""
Example script demonstrating batch radiometric calibration using vegetation
LUTs.

Calls functions contained in radiocal module to handle the batch processing.

Actual correction is performed by calling C programs.

Created on Tue May 26 11:32:00 2015

@author: mdenbina
"""
import numpy as np
import os
import subprocess
import multiprocessing as mp
from multiprocessing import Pool


import radiocal


# print
print('Starting radiocal example script.')

# sardata_base
sardatabase_list='/home/ekyzivat/scripts/random-wetlands/data_paths/rtc-test-1.txt' # path to list of UAVSAR IDs to run
sardatabase=open(sardatabase_list).read().splitlines() # a list of UAVSAR IDs

# uncomment for testing:
# sardatabase = ['bakerc_16008_19059_012_190904_L090_CX_01/'] # ['bakerc_16008_18048_011_180822_L090_CX_02'] #  ['bakerc_16008_19060_037_190905_L090'] # original: bakerc_16008_19060_037_190905_L090HHVV_CX_01.mlc #['padelE_36000_18047_000_180821_L090'] # _L090_CX_01

# Root names pointing to the UAVSAR data to use for LUT creation, excluding the polarization and correction type (which get appended to this string to produce the full filename).
def sarDataPathNameFunction(sardata_str):
    sardatapath=sardata_str[0:-6]
    return sardatapath
sardata = [sarDataPathNameFunction(sardata_str) for sardata_str in sardatabase] 

# Parent path to UAVSAR data files:
data_base_pth = '/att/nobackup/ekyzivat/tmp/rtc'

# Path to the UAVSAR data files:
def dataPathNameFunction(data_base_pth, sardata_str):
    datapath=os.path.join(data_base_pth, sardata_str, 'raw'+os.sep)
    return datapath
datapath = [dataPathNameFunction(data_base_pth, sardata_str) for sardata_str in sardatabase] # list(map(dataPathNameFunction, data_base_pth, sardata)) # '/att/nobackup/ekyzivat/tmp/rtc/bakerc_16008_18048_011_180822_L090_CX_02/raw/' # '/att/nobackup/ekyzivat/tmp/rtc/padelE_36000_18047_000_180821_L090_CX_01/raw/'

# Path to the folder containing the radiometric calibration programs
# (e.g., uavsar_calib_veg_v2 and geocode_uavsar)
programpath = '/home/ekyzivat/UAVSAR-rtc/'

# Calibration program:
calibprog = programpath+'uavsar_calib'

# Geocoding program:
geocodeprog = programpath+'uavsar_geocode'


# min and max look angles, if post processing is enabled...
# look angles outside these bounds will be set to zero:
# choose values that will definitely have data- if you get close to the real min/max look, be sure to set min_samples to a high value, i.e. 10,000 to filter out tall trees/mountains etc that can cause outliers
minlook = 24 #24 # 20.86 for PAD 2017
maxlook = 64 #64 # 65.55 for PAD 2017

# Polarizations to correct:
pol = [0,1,2] #[0, 1, 2] #[0] #[0, 1, 2]


# Subpaths pointing to a land cover or mask image to use for each UAVSAR scene.
# len() of maskdata needs to be the same as the len() of sardata.

def maskNameFunction(str):
    maskName=str[0:-4]+'landcovermask.tif'
    return maskName
maskdata= list(map(maskNameFunction, sardata)) # [maskNameFunction(item) for item in sardata] # 
# maskdata = ['ABoVE_LandCover_PAD_2018.tif']


# Path to save the LUT:
LUTpath = '/att/nobackup/ekyzivat/tmp/rtc/lut/' # '/att/nobackup/ekyzivat/UAVSAR/asf.alaska.edu/lut/'

# A name to describe the LUT:
LUTname = sardata #'PAD2018'

# A name to append to the filenames of the LUT corrected output:
calname='LUT'


# The SAR image and the mask should have the same extents, pixel size, etc.
# Trim the mask to the correct size (e.g., in QGIS) before running this.

# Array of allowed values in the mask -- values other than these will be
# excluded from the process.  For a boolean mask this should equal True, to
# include all pixels where the mask is True.  For a land cover image, list
# the class ID numbers of interest.
# Note: For Louisiana data using CCAP land cover, classes 15 and 18 are both
# emergent wetland (18: Estuarine Emergent Wetland, and 15: Palustrine
# Emergent Wetland).
allowed = range(1, 16) #[14] #range(1, 16) # 14 refers to barren class!


# These settings determine which pixels we use to generate the LUT, and which pixels are excluded, based on backscatter.
# Note, these cutoff values should be based on HV backscatter.  To be consistent between the polarizations, we always mask out
# the same pixels for each polarization.  The pixels excluded based on backscatter use the HVHV.
# TODO add auto min/max look angle masking?
max_cutoff = np.inf # pixels above this value will be excluded
min_cutoff = 0 # pixels below this will be excluded


# Set to true to assume range slope is zero, false otherwise:
flatdemflag = True # HERE change

# Constant height value for the created flat DEM:
hgtval = 180

# Note that this example script was created for wetland areas along the Gulf
# Coast in Louisiana, United States.  Here we have set flatdemflag to True
# since there is minimal topography in this area.  However, in areas with
# significant topography, one should set flatdemflag to False in order
# to calculate the terrain slope angle from the DEM.  Here we create a
# perfectly flat DEM which is approximately equal to the mean sea level
# height in this area.


# Savitzky-Golay filter to smooth LUT?
sgfilterflag = True # set to True to filter, False to leave alone
sgfilterwindow = 51 # filter window size--larger windows yield more smoothing



# STEP 1: Area Correction (in order to make the data to generate the LUT)
print('DOING AREA CORRECTION...')
pool = Pool(mp.cpu_count())
for num in range(0,len(sardata)): # do first and third steps all at once as loop; do second  steps as loops within each step
    pool.apply_async(radiocal.batchcal, args=(datapath[num], programpath, calibprog, geocodeprog, 
                                              None,         # caltblroot
                                              'area_only',  # calname
                                              True,         # docorrectionflag
                                              True,         # zerodemflag
                                              False,        # createmaskflag
                                              True,         #  createlookflag
                                              True,         # createslopeflag
                                              False,        # overwriteflag
                                              False,        # postprocessflag
                                              minlook,      # minlook
                                              maxlook,      # maxlook
                                              pol,          # pol
                                              hgtval,       # hgtval
                                              sardata[num])) # scene  
                                              #     radiocal.batchcal(datapath[num], programpath, calibprog, geocodeprog, None, calname='area_only', docorrectionflag=True, zerodemflag=True, createmaskflag=False, createlookflag=True, createslopeflag=True,  overwriteflag=False, postprocessflag=False, pol=pol, hgtval=hgtval, scene=sardata[num])
# pool.join()

# STEP 2: Create landcover mask images
print('BUILDING LANDCOVER MASKS FROM MOSAIC') # using my custom script (on path) to crop and reproject from landcover mosaic
for num in range(0,len(sardatabase)): 
    target_align_file = datapath[num]+sardata[num][0:-4]+'slope'+'.grd' # just need ground-projected file to align to 
    landcover_file=datapath[num]+sardata[num][0:-4]+'landcovermask.tif' # output of custom reprojection script
    if not os.path.isfile(landcover_file): # maybe add "or overwriteflag"
        print('BUILDING: {}'.format(landcover_file))
        print(subprocess.getoutput('gdal_reproject_match.sh /att/nobackup/ekyzivat/landcover/ABoVE_LandCover.vrt ' \
            +landcover_file + ' '+ target_align_file))# HERE
    else: 
        print('LANDCOVER MASK ALREADY BUILT: {}'.format(landcover_file))

# STEP 3: LUT Creation
print('CREATING LUT...')
for num in range(0,len(sardata)): 
    pool.apply_async(radiocal.createlut, args=(datapath[num], [sardata[num]], [maskdata[num]], LUTpath, LUTname[num], allowed, # no loop bc creatlut already does loop over 3 polarizations
                pol, 'area_only', min_cutoff,
                max_cutoff, flatdemflag, sgfilterflag, 
                sgfilterwindow, minlook, maxlook, 10)) # datapath[num], [sardata[num]], [maskdata[num]], LUTpath, LUTname[num], allowed, # no loop bc creatlut already does loop over 3 polarizationspol=pol, corrstr='area_only', min_cutoff=min_cutoff,max_cutoff=max_cutoff, flatdemflag=flatdemflag, sgfilterflag=sgfilterflag, sgfilterwindow=sgfilterwindow, min_look=minlook, max_look=maxlook, min_samples=10))
# pool.join()


# STEP 4:  LUT Correction
print('DOING LUT CORRECTION...')
for num in range(0,len(sardata)): # do first steps all at once as loop; do second and third steps as loops within each step
    pool.apply_async(radiocal.batchcal, args=(datapath[num], programpath, calibprog, geocodeprog, 
                                              LUTpath+'caltbl_'+LUTname[num], # caltblroot      
                                              'area_only',  # calname
                                              True,         # docorrectionflag
                                              True,         # zerodemflag
                                              True,         # createmaskflag
                                              True,         #  createlookflag
                                              True,         # createslopeflag
                                              False,        # overwriteflag
                                              False,        # postprocessflag
                                              minlook,      # minlook
                                              maxlook,      # maxlook
                                              pol,          # pol
                                              hgtval,       # hgtval
                                              None)) # scene  
 # radiocal.batchcal, args=(datapath[num], programpath, calibprog, geocodeprog, LUTpath+'caltbl_'+LUTname[num],calname=calname, docorrectionflag=True, zerodemflag=True, createmaskflag=True, createlookflag=True, createslopeflag=True, overwriteflag=False, postprocessflag=False, minlook=minlook, maxlook=maxlook, pol=pol, hgtval=hgtval))
pool.close()
pool.join()
