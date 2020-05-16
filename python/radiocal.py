# -*- coding: utf-8 -*-
"""
UAVSAR Radiometric Calibration Module

The actual radiometric calibration is done by the C programs uavsar_calib_area
and uavsar_calib_veg.  These are helper functions which allow easier batch
processing and calibration LUT creation.  Batch processing is performed using
the batchcal() function.  LUT creation is done using createlut().

See function definitions for the allowed arguments, or radiocal_script.py for
an example script that calls the functions.

Created on Tue May 26 11:29:51 2015

@author: mdenbina
"""

import numpy as np
import os
import subprocess
import osgeo.gdal as gdal
import scipy.signal
from scipy.stats import binned_statistic
import matplotlib.pyplot as plt

from buildUAVSARhdr import genHDRfromTXT





def batchcal(datapath, programpath, calibprog, geocodeprog, caltblroot,
             calname='area_veg', docorrectionflag=True, zerodemflag=False, 
             createmaskflag=True, createlookflag=False, createslopeflag=False, 
             overwriteflag=False, postprocessflag=True, minlook=25, 
             maxlook=64, pol=[0,1,2], hgtval=0, scene=None):
    """Function to perform batch radiometric calibration given a folder
    containing UAVSAR data.
    
    Input Arguments:
    
    - datapath, the path to the folder containing the UAVSAR data (which
        should include the .ann file, .mlc files, and .hgt file)
    - programpath, the path to the radiometric calibration program
        executables (e.g., uavsar_calib_veg)
    - calibprog, the filename of the calibration executable
    - geocodeprog, the filename of the geocode executable
    - caltblroot, the full path and root filename of the calibration LUT to
        use.  (e.g., programpath+'caltbl_LA_GulfCo_Wetlands')
    - calname, a descriptive name to append to the calibrated files.
    - docorrectionflag, a flag that determines whether the correction programs
        are actually called (you can set to False for testing, for example)
    - zerodemflag, a flag that determines whether the .hgt file is used for
        DEM information (if False), or whether a flat, zero height DEM file
        is temporarily created (if True).
    - createmaskflag, a flag that determines if the mask data (which records
        which pixels were able to be corrected) generated by the calibration
        program is saved.
    - createlookflag, a flag that determines if the look angle data
        generated by the calibration program is saved.
    - createslopeflag, a flag that determines if the range slope data
        generated by the calibration program is saved.
    - overwriteflag, a flag that determines if already created calibrated
        files are overwritten, or skipped.
    - postprocessflag, a flag that determines whether some tweaking is done
        to the corrected GRD file in order to limit the look angle range, and
        set masked pixels (from createmaskflag) to zero.  If this is set
        to true, the minlook and maxlook arguments will be used for the
        look angle bounds, and createmaskflag should be set to True.
    - minlook, the minimum look angle allowed, in degrees, if postprocessflag
        is enabled.
    - maxlook, the maximum look angle allowed, in degrees, if postprocessflag
        is enabled.
    - pol, list of polarizations to correct.  0: HH, 1: VV, 2: HV.  Default
        value is [0,1,2], to process all three.  Even if only one polarization
        is desired, still use a list to avoid an error, e.g., pol = [2] to
        only process the HV, rather than just pol = 2.
    - hgtval, the height to use for the flat DEM (if zerodemflag is True).
        (e.g., for the Louisiana Gulf Coast area, the EGM96 geoid is at about
        -26.5883m ellipsoidal height, so this is about the height you'd want
        to set for sea level).
    - scene, part of the filename of a specific scene you wish to process,
        if you only want to process a single scene.  Otherwise, leave this
        at the default value of None in order to process all scenes in the
        folder.
    
    """   
    
    pol_str = ['HHHH','VVVV','HVHV']
    pol_shortstr = ['HH','VV','HV']   
    
    lat = None
    lon = None
    
    os.chdir(datapath)
    
    # Browse through the directory, looking for the .ann files, and for each
    # .ann file, do the calibration on the HH, HV, and VV polarizations:
    files = os.listdir('.')
    for file in files:
        if file.endswith('.ann') and ((scene is None) or (scene in file)):
            print(file)
            rootname = file[0:-14]
            hgtname = file[0:-4] + '.hgt'
            skip = False
            
            # Load the annotation file info:
            anndata = open(file).read().splitlines()
            
            mlc_cols_str = str([s for s in anndata if 'mlc_pwr.set_cols' in s]) # find string containing the number of mlc columns
            mlc_cols = int(str(mlc_cols_str.split(sep='=')[1]).split(sep=';')[0])
            
            grd_rows_str = str([s for s in anndata if 'grd_pwr.set_rows' in s]) # find string containing the number of grd rows
            grd_rows = int(str(grd_rows_str.split(sep='=')[1]).split(sep=';')[0])
            
            grd_cols_str = str([s for s in anndata if 'grd_pwr.set_cols' in s]) # find string containing the number of grd columns
            grd_cols = int(str(grd_cols_str.split(sep='=')[1]).split(sep=';')[0])
            
            if (zerodemflag == True) and (docorrectionflag == True):
                # Rename current DEM:
                mvhgt_exec = 'mv '+hgtname+' '+hgtname+'_old'
                print(subprocess.getoutput(mvhgt_exec))
                
                # Create flat DEM:
                zerodem = np.ones((grd_rows,grd_cols),dtype='float32') * hgtval
                zerodem.tofile(hgtname)
            
            # Take the latitude/longitude of the corners from the ann file:
            ULlat = str([s for s in anndata if 'Approximate Upper Left Latitude' in s])
            ULlat = float(str(ULlat.split(sep='=')[1]).split(sep='\'')[0])
            ULlon = str([s for s in anndata if 'Approximate Upper Left Longitude' in s])
            ULlon = float(str(ULlon.split(sep='=')[1]).split(sep='\'')[0])
            URlat = str([s for s in anndata if 'Approximate Upper Right Latitude' in s])
            URlat = float(str(URlat.split(sep='=')[1]).split(sep='\'')[0])
            URlon = str([s for s in anndata if 'Approximate Upper Right Longitude' in s])
            URlon = float(str(URlon.split(sep='=')[1]).split(sep='\'')[0])
            LLlat = str([s for s in anndata if 'Approximate Lower Left Latitude' in s])
            LLlat = float(str(LLlat.split(sep='=')[1]).split(sep='\'')[0])
            LLlon = str([s for s in anndata if 'Approximate Lower Left Longitude' in s])
            LLlon = float(str(LLlon.split(sep='=')[1]).split(sep='\'')[0])
            LRlat = str([s for s in anndata if 'Approximate Lower Right Latitude' in s])
            LRlat = float(str(LRlat.split(sep='=')[1]).split(sep='\'')[0])
            LRlon = str([s for s in anndata if 'Approximate Lower Right Longitude' in s])
            LRlon = float(str(LRlon.split(sep='=')[1]).split(sep='\'')[0])
            
            if lat is None:
                lat = np.array([ULlat, URlat, LLlat, LRlat])
                lon = np.array([ULlon, URlon, LLlon, LRlon])
            else:
                lat = np.append(lat, (ULlat, URlat, LLlat, LRlat))
                lon = np.append(lon, (ULlon, URlon, LLlon, LRlon))
            
            
            for p in range(0,np.size(pol)):
                mlcfile = rootname+pol_str[pol[p]]+'_'+calname+'.mlc'
                grdfile = rootname+pol_str[pol[p]]+'_'+calname+'.grd'
                
                if (grdfile in files) and (overwriteflag == False):
                    print(grdfile,' already exists -- skipping...')
                    skip = True
                else:
                    # calib_exec = calibprog+' '+file+' '+pol_str[pol[p]]+' geomap_uavsar.trans '+mlcfile+' '+caltblfile
                    if caltblroot is not None:
                        caltblfile = caltblroot+'_'+pol_shortstr[pol[p]]+'.flt'
                        calib_exec = calibprog+' -u geomap_uavsar.trans -c '+caltblfile+' -l look_temp -s slope_temp -m mask_temp '+file+' '+pol_str[pol[p]]+' '+mlcfile
                    else:
                        calib_exec = calibprog+' -u geomap_uavsar.trans -l look_temp -s slope_temp -m mask_temp '+file+' '+pol_str[pol[p]]+' '+mlcfile
                    geocode_exec = geocodeprog+' '+mlcfile+' '+str(mlc_cols)+' geomap_uavsar.trans '+grdfile+' '+str(grd_cols)+' '+str(grd_rows)
                    
                    if docorrectionflag == True:
                        print(subprocess.getoutput(calib_exec))
                        print(subprocess.getoutput(geocode_exec))
                        
                        # Create header file:
                        genHDRfromTXT(file,grdfile,pol_str[pol[p]])
                
                
    
            if (docorrectionflag == True) and (skip == False):
                if createmaskflag == True:
                    geocode_mask_exec = geocodeprog + ' mask_temp '+str(mlc_cols)+' geomap_uavsar.trans '+rootname+'mask.grd '+str(grd_cols)+' '+str(grd_rows)
                    print(subprocess.getoutput(geocode_mask_exec))
                    genHDRfromTXT(file,rootname+'mask.grd',pol_str[0])
    
                if createslopeflag == True:
                    mvslope_exec = 'mv slope_temp '+rootname+'slope.grd'
                    print(subprocess.getoutput(mvslope_exec))
                    genHDRfromTXT(file,rootname+'slope.grd',pol_str[0])
                    
                if createlookflag == True:
                    mvlook_exec = 'mv look_temp '+rootname+'look.grd'
                    print(subprocess.getoutput(mvlook_exec))
                    genHDRfromTXT(file,rootname+'look.grd',pol_str[0])
    
    
    
            if (zerodemflag == True) and (docorrectionflag == True):
                # Put back the DEM:
                mvhgt_exec = 'mv '+hgtname+'_old '+hgtname
                print(subprocess.getoutput(mvhgt_exec))
    
    
    
            if (postprocessflag == True) and (docorrectionflag == True) and (skip == False):
                for p in range(0,np.size(pol)):
                    grdfile = rootname+pol_str[pol[p]]+'_'+calname+'.grd'
                    data = np.memmap(grdfile,shape=(grd_rows,grd_cols),dtype='<f4',mode='r+')
                    mask = np.memmap(rootname+'mask.grd',shape=(grd_rows,grd_cols),dtype='<f4',mode='r')
                    look = np.memmap(rootname+'look.grd',shape=(grd_rows,grd_cols),dtype='<f4',mode='r')
                                           
                    data[mask > 0] = 0
                    data[np.logical_not(np.isfinite(data))] = 0
                    data[look < minlook] = 0
                    data[look > maxlook] = 0
                    del data
                    del mask
                    del look

    
    
def sgolay2d (z, window_size, order, derivative=None):
    """Savitzky-Golay 2D Filter
    
    Taken from: http://scipy.github.io/old-wiki/pages/Cookbook/SavitzkyGolay
    
    """
    # number of terms in the polynomial expression
    n_terms = ( order + 1 ) * ( order + 2)  / 2.0

    if  window_size % 2 == 0:
        raise ValueError('window_size must be odd')

    if window_size**2 < n_terms:
        raise ValueError('order is too high for the window size')

    half_size = window_size // 2

    # exponents of the polynomial. 
    # p(x,y) = a0 + a1*x + a2*y + a3*x^2 + a4*y^2 + a5*x*y + ... 
    # this line gives a list of two item tuple. Each tuple contains 
    # the exponents of the k-th term. First element of tuple is for x
    # second element for y.
    # Ex. exps = [(0,0), (1,0), (0,1), (2,0), (1,1), (0,2), ...]
    exps = [ (k-n, n) for k in range(order+1) for n in range(k+1) ]

    # coordinates of points
    ind = np.arange(-half_size, half_size+1, dtype=np.float64)
    dx = np.repeat( ind, window_size )
    dy = np.tile( ind, [window_size, 1]).reshape(window_size**2, )

    # build matrix of system of equation
    A = np.empty( (window_size**2, len(exps)) )
    for i, exp in enumerate( exps ):
        A[:,i] = (dx**exp[0]) * (dy**exp[1])

    # pad input array with appropriate values at the four borders
    new_shape = z.shape[0] + 2*half_size, z.shape[1] + 2*half_size
    Z = np.zeros( (new_shape) )
    # top band
    band = z[0, :]
    Z[:half_size, half_size:-half_size] =  band -  np.abs( np.flipud( z[1:half_size+1, :] ) - band )
    # bottom band
    band = z[-1, :]
    Z[-half_size:, half_size:-half_size] = band  + np.abs( np.flipud( z[-half_size-1:-1, :] )  -band )
    # left band
    band = np.tile( z[:,0].reshape(-1,1), [1,half_size])
    Z[half_size:-half_size, :half_size] = band - np.abs( np.fliplr( z[:, 1:half_size+1] ) - band )
    # right band
    band = np.tile( z[:,-1].reshape(-1,1), [1,half_size] )
    Z[half_size:-half_size, -half_size:] =  band + np.abs( np.fliplr( z[:, -half_size-1:-1] ) - band )
    # central band
    Z[half_size:-half_size, half_size:-half_size] = z

    # top left corner
    band = z[0,0]
    Z[:half_size,:half_size] = band - np.abs( np.flipud(np.fliplr(z[1:half_size+1,1:half_size+1]) ) - band )
    # bottom right corner
    band = z[-1,-1]
    Z[-half_size:,-half_size:] = band + np.abs( np.flipud(np.fliplr(z[-half_size-1:-1,-half_size-1:-1]) ) - band )

    # top right corner
    band = Z[half_size,-half_size:]
    Z[:half_size,-half_size:] = band - np.abs( np.flipud(Z[half_size+1:2*half_size+1,-half_size:]) - band )
    # bottom left corner
    band = Z[-half_size:,half_size].reshape(-1,1)
    Z[-half_size:,:half_size] = band - np.abs( np.fliplr(Z[-half_size:, half_size+1:2*half_size+1]) - band )

    # solve system and convolve
    if derivative == None:
        m = np.linalg.pinv(A)[0].reshape((window_size, -1))
        return scipy.signal.fftconvolve(Z, m, mode='valid')
    elif derivative == 'row':
        c = np.linalg.pinv(A)[1].reshape((window_size, -1))
        return scipy.signal.fftconvolve(Z, -c, mode='valid')
    elif derivative == 'row':
        r = np.linalg.pinv(A)[2].reshape((window_size, -1))
        return scipy.signal.fftconvolve(Z, -r, mode='valid')
    elif derivative == 'both':
        c = np.linalg.pinv(A)[1].reshape((window_size, -1))
        r = np.linalg.pinv(A)[2].reshape((window_size, -1))
        return scipy.signal.fftconvolve(Z, -r, mode='valid'), scipy.signal.fftconvolve(Z, -c, mode='valid')



def createlut(rootpath, sardata, maskdata, LUTpath, LUTname, allowed,
              pol=[0,1,2], corrstr='area_only', min_cutoff=0,
              max_cutoff=np.inf, flatdemflag=False, sgfilterflag=True, 
              sgfilterwindow=51, min_look=22, max_look=65, min_samples=1):
    """Create a LUT that is a function of look angle and range slope,
    for use in radiometric calibration if vegetation.
    
    Input Arguments:
    
    - rootpath, the pathname containing the UAVSAR data you wish to use to
        generate the LUT.
    - sardata, a list containing the specific UAVSAR scenes to use to
        generate the LUT.  These should include only the flight, line,
        data take, and date parts of the filename, not the full filename
        (e.g., gulfco_14011_15058_109_150509).
    - maskdata, a list the same size as sardata, containing the filenames of
        the mask arrays (e.g., land cover information) to use for each UAVSAR
        scene.  These files should have the same pixel spacing and extents
        as the UAVSAR GRD files.  This can be done in QGIS, for example, using
        the Raster Calculator.
    - LUTpath, a path to a folder of where to save the created LUT.
    - LUTname, the filename for the LUT.
    - allowed, the values of the mask data for pixels to be used in the LUT
        creation process.  (e.g., for CCAP land cover, 15 and 18 are the land
        cover ID numbers for palustrine emergent wetland, and estuarine
        emergent wetland, respectively).  If the masks are boolean, this can
        be set to True or 1, for example.
    - pol, list of polarizations to correct.  0: HH, 1: VV, 2: HV.  Default
        value is [0,1,2], to process all three.  Even if only one polarization
        is desired, still use a list to avoid an error, e.g., pol = [2] to
        only process the HV, rather than just pol = 2.
    - corrstr, the filename descriptor for the correction to load.  Generally,
        this should probably be 'area_only', to load the area corrected images,
        since the area corrected images are the ones we wish to use to create
        the LUT.
    - min_cutoff, minimum backscatter value, in the same units as the input 
        UAVSAR GRD data (for area only, this is linear units), for a pixel
        to be included in the LUT.  Note, these cutoff values should be based
        on HV backscatter.  To be consistent between the polarizations, we
        always mask out the same pixels for each polarization, and the pixels
        excluded based on backscatter always use the HVHV.
    - max_cutoff, maximum backscatter value, in the same units as the input
        UAVSAR GRD data, for a pixel to be included in the LUT.
    - flatdemflag, set to False to use the range slope.  Set to True if the
        data was processed with a flat "DEM" and there is no range slope
        information.
    - sgfilterflag, flag to determine if the Savitzky-Golay filter should
        be used to smooth the LUT.  Note that if flatdemflag is enabled,
        there's some messing around so that at the edges of the data where
        the Savitzky-Golay filter doesn't have a full window of data (and
        begins to smooth the data with zeroes), we switch over to a small
        moving averaging window instead.  If flatdemflag is disabled, this
        is not done, and the edges of the LUT are kind of questionable.  This
        aspect could probably use some more work.
    - sgfilterwindow, the window size of the Savitzky-Golay filter.
    - min_look, minimum look angle for a pixel to be included in the LUT.
    - max_look, maximum look angle for a pixel to be included in the LUT.
    - min_samples, the minimum number of samples for each LUT bin.  If there
        are less than this number of samples in a given bin, that bin will be
        set to void.
    
    """
    
    # List of strings corresponding to the polarization you wish to create LUT for.  (e.g,. 'HVHV' for the HV channel)
    pol_str = ['HHHH','VVVV','HVHV']
    shortpol_str = ['HH','VV','HV']   
    
    # Empty LUT arrays:
    # LUT_val = np.zeros((900,900,np.size(pol))) # will hold the cumulative sum of all pixels that fall in this bin
    LUT_num = np.zeros((900,900,np.size(pol))) # will hold count of of all pixels that fall in this bin
    LUT_val=np.zeros((900,900,np.size(pol)))
    
    
    for num in range(0,np.size(sardata)):
        driver = gdal.GetDriverByName('ENVI')
        driver.Register()
        
        # Load the mask, look, slope, etc.
        mask = gdal.Open(rootpath+maskdata[num],gdal.GA_ReadOnly)
        mask = mask.ReadAsArray()

        # binarize landcover classification to only include classes of interest
        mask_bool = np.zeros(mask.shape,dtype='bool')
        for val in range(0,np.size(allowed)):
            mask_bool = mask_bool | (mask == allowed[val])
        del mask
        
        look = gdal.Open(rootpath+sardata[num]+'_look.grd',gdal.GA_ReadOnly) # HERE should change file naming scheme
        look = np.degrees(look.ReadAsArray()) # HERE changed to degrees
    
        
        # Mask out look angles outside the range:
        mask_bool = mask_bool & (look > min_look) & (look < max_look) # HERE I converted rad to deg and need to confirm look is same as inc
    
        
        # Use HV image to mask out backscatter values outside the range:
        sarimage = gdal.Open(rootpath+sardata[num]+'HVHV_'+corrstr+'.grd') # HERE I MADE A CHANGE
        sarimage = sarimage.ReadAsArray()
        # sarimage[~np.isfinite(sarimage)] = -99 # HERE edit
        mask_bool = mask_bool & (sarimage > min_cutoff) & (sarimage < max_cutoff)  # positive mask
        
        # apply same mask to look file
        look = look[mask_bool]
    
    
        if flatdemflag == False:
            slope = gdal.Open(rootpath+sardata[num]+'_'+corrstr+'.slope',gdal.GA_ReadOnly)
            slope = np.degrees(slope.ReadAsArray()) # HERE changed to degrees
            slope = slope[mask_bool] #NOTE : I didn't need to mask out the -10000 nodata value bc it is out of the range I'm binning
    
        
        for p in range(0,np.size(pol)): # loop through HHHH, HHHHV, etc. for each scene
            print('Processing '+rootpath+sardata[num]+pol_str[pol[p]]+'_'+corrstr+'.grd'+' ...')
            sarimage = gdal.Open(rootpath+sardata[num]+pol_str[pol[p]]+'_'+corrstr+'.grd')
            sarimage = sarimage.ReadAsArray()
            sarimage = sarimage[mask_bool] # reshapes sarimage to linear vector
            
            
            # Populate the LUT:
            dim = np.size(sarimage)
            
            ## masked version
            bins_look=np.linspace(0,90, 901)
            # mask_look=np.digitize(look, bins_look)
            bins_slope=np.linspace(-45,45, 901)
            # if flatdemflag == False:
            #      mask_slope=np.digitize(slope, bins_look) 
            # else:
            #     mask_slope=np.ones(mask_look.shape, mask_look.dtype)*450
            
            ## zonal stats
            zonal_look=binned_statistic(look, sarimage, 'sum', bins=bins_look)
            
            ## vectorize second dim
            zonal_slope=binned_statistic(slope, sarimage, 'sum', bins=bins_slope)
            
            ## end
            
            if flatdemflag == False:
                zonal_slope=binned_statistic(slope, sarimage, 'sum', bins=bins_slope)
            # else:
                # zonal_slope=binned_statistic(np.zeros(look.shape, look.dtype), sarimage, 'sum', bins=bins_slope)
            
            for row in range(LUT_val[:,:,0].shape[0]):
                print('Slopes {} to {}'.format(bins_slope[row], bins_slope[row+1]))
                if flatdemflag == False:
                    # if  np.sum(zonal_slope.binnumber==row)>0: #sarimage_slope_bin_msk.shape[0]!=0: #if there are values present with this particular slope
                    # zonal stats on masked array
                    for col in range(LUT_val[:,:,0].shape[1]): # iterate over look/col
                        print('\tLook {} to {}'.format(bins_look[col], bins_look[col+1]))
                        # sarimage_slope_bin_msk=sarimage # init
                        # look_slope_bin_msk=look;
                        # sarimage_slope_bin_msk = sarimage_slope_bin_msk[zonal_slope.binnumber==row] # mask sarimage by slope bin
                        # look_slope_bin_msk=look[zonal_slope.binnumber==row];
                        # zonal_slopemask_look=binned_statistic(look_slope_bin_msk, sarimage_slope_bin_msk, 'sum', bins=bins_look)
                        # zonal_slopemask_look_count=binned_statistic(look_slope_bin_msk, sarimage_slope_bin_msk, 'count', bins=bins_look)
                        
                        # put into LUT and LUT_num_temp
                        LUT_val[row,col, p]=np.sum(sarimage[(slope > bins_slope[col]) & (slope <= bins_slope[col+1]) & (look>bins_look[col]) & (look <= bins_look[col+1])]) #zonal_slopemask_look_count.statistic # HERE switch dims
                        LUT_num[row,col, p]=np.sum((slope > bins_slope[col]) & (slope <= bins_slope[col+1]) & (look>bins_look[col]) & (look <= bins_look[col+1]))
                else: 
                    pass
                
            if flatdemflag == True: # don't need to loop over columns
                # put into LUT and LUT_num_temp for all colums at once w/o looping
                zonal_look_count=binned_statistic(look, sarimage, 'count', bins=bins_look)
                LUT_num[:,:,p]=np.tile(zonal_look_count.statistic,(900,1)) # np.transpose
                LUT_val[:,:,p]= np.tile(zonal_look.statistic,(900,1))                    
                
            ## remove zeros
                
            
            ## remove this
            # for pix in range(0,dim): # TODO: don't iterate over pixels!
                
            #     # print reporting
            #     if (pix % 1000000) == 0:
            #         print(pix)
            #     if np.isfinite(sarimage[pix]): # data is all finite, no nans...
            #         look_bin = int(np.floor(look[pix]*10))
                    
            #         if flatdemflag == True:
            #             slope_bin = 450 # zero degrees /flat
            #         else:
            #             slope_bin = int(np.floor((slope[pix] + 90)*5))
                        
            #         LUT_val[slope_bin,look_bin,p] += sarimage[pix] # accumulate backscatter values
            #         LUT_num[slope_bin,look_bin,p] += 1 # accumulate px count
                    
                    
    
    
    # Finalize the LUT:    
    print('Finalizing look up tables...')
    for p in range(0,np.size(pol)):
        LUT_val_temp = LUT_val[:,:,p] # re-initiated for each polarization
        LUT_num_temp = LUT_num[:,:,p]
        LUT_num_temp[LUT_num_temp==0]=1 # set zero counts to one to avoid divide by zero
        
        LUT = LUT_val_temp / LUT_num_temp # take average, convert to actual LUT format, hopefully no div by zero errors
        
        # LUT=LUT_val[:,:,p] # select polarization of interst
        
        if flatdemflag==False:
            LUT[LUT_num_temp < min_samples] = 0 # exclude bins w/o enough data
        else:
            LUT[LUT_num_temp < min_samples*LUT.shape[0]] = 0 # use a larger number, because all counts will be lumped into each slope bin (repeated 900 times)
        LUTma = LUT
        
        if flatdemflag == True: # TODO: necessary?
            # Make the LUT independent of range slope:
            LUT = LUT[450,:]
            LUT = np.tile(LUT,(900,1)) # MATLAB repmat
        
        startloc = 10
        endloc = 890
        if sgfilterflag == True:
            if flatdemflag == True:
                # Don't want to smooth the zeroes:
                foundstart = False
                foundend = False
                LUT[LUT == 0] = np.nan
                for lookbin in range(10,890):
                    if (LUT_num_temp[450,lookbin] > 1) and (foundstart == False):
                        foundstart = True
                        startloc = lookbin
                    if (LUT_num_temp[450,lookbin] == 1) and (foundstart == True) and (foundend == False):
                        foundend = True
                        endloc = lookbin
                    if (foundstart == True) and (foundend == False):
                        LUTma[450,lookbin] = np.nanmean(LUT[450,lookbin-2:lookbin+3])
                                  
                # Smooth it:
                LUT[np.logical_not(np.isfinite(LUT))] = 0
                LUTsm = scipy.signal.savgol_filter(LUT,sgfilterwindow,3,axis=1)
                
                # Set any bin without a full smoothing window to the moving
                # average smoothed LUT, which ignores the zero values:
                LUTsm[450,startloc:startloc+int(np.ceil(sgfilterwindow/2)+1)] = LUTma[450,startloc:int(startloc+np.ceil(sgfilterwindow/2)+1)]
                LUTsm[450,endloc-int(np.ceil(sgfilterwindow/2)):endloc+1] = LUTma[450,endloc-int(np.ceil(sgfilterwindow/2)):endloc+1]
                
                
                LUTsm[LUT_num_temp < min_samples] = 0
                LUT = LUTsm[450,:]
                LUT = np.tile(LUT,(900,1))
            else:
                LUTsm = sgolay2d(LUT,sgfilterwindow,3,derivative=None)
                LUTsm[LUT_num_temp < min_samples] = 0
                
                
        # Copy edges of LUT along look angle axis to rest of data, in case
        # the data to correct has a wider look angle range (extrapolate values).
        look_low_bin = int(np.floor(min_look*10))       
        look_high_bin = int(np.floor(max_look*10))-1
        
        LUT[:,0:look_low_bin] = LUT[:,look_low_bin,np.newaxis]       
        LUT[:,look_high_bin+1:] = LUT[:,look_high_bin,np.newaxis]

                
        
        if np.sum(LUT) < 1: #(startloc == 10) and (endloc == 890):
            print('radiocal.createlut | WARNING: Generated LUT appears to be empty.  Does your mask contain enough pixels?  Are the values given to the min_cutoff, max_cutoff, min_look, max_look, and min_samples arguments reasonable?')
        
        # save as binary
        LUT = LUT.astype('float32')
        LUT.tofile(LUTpath+'caltbl_'+LUTname+'_'+shortpol_str[pol[p]]+'.flt')
        
        # Plot
        plt.imshow(LUT, label='caltbl_'+LUTname+'_'+shortpol_str[pol[p]])
        plt.colorbar()
        plt.savefig(LUTpath+'caltbl_'+LUTname+'_'+shortpol_str[pol[p]]+'.png')
        plt.xlabel('Incidence angle'); plt.ylabel('Slope')
                    
        # Plot 2
        plt.figure()
        plt.plot(np.linspace(0, 90, LUT.shape[1]), np.nanmean(LUT,axis=0),label='caltbl_'+LUTname+'_'+shortpol_str[pol[p]]) # This returns runtime error for empty rows
        plt.xlabel('Incidence angle'); plt.ylabel('Magnitude')
        plt.savefig(LUTpath+'calplot_'+LUTname+'_'+shortpol_str[pol[p]]+'.png')