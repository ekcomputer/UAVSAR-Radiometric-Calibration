import numpy as np
import osgeo.gdal as gdal
# from matplotlib import pyplot as plt
import os
import shutil
import subprocess

# TODO: finish and import from /mnt/d/Dropbox/Python/UAVSAR-Radiometric-Calibration/local/multiply-2.py; switch to subprocess modeule on ASC; copy *.hdr files...
def complexRTC(base, lutBase, corrstr, calname, lutDir,origDir, outDir):
    '''Takes LUT-corrected real grd files, calculates correction ratio, applies to non LUT-corrected grd files'''
    ## vars
    pol_real=['HHHH','VVVV','HVHV']
    pol_complex=['HHHV','HVVV','HHVV']
    
    for i in range(3):
            ## mkdir outDir
        print('Making outdir. Result: {}'.format(os.system('mkdir -p '+ outDir)))
            ## copy LUT-corrected real GRD image files
        pthGRD_lut_orig=os.path.join(lutDir, lutBase + '_' + pol_real[i] + '_' + calname + '.grd')
        pthGRD_lut_copy=os.path.join(outDir, base + pol_real[i] + '_' + corrstr + '.grd')
        pthANN_orig=os.path.join(origDir, base + '_' + corrstr + '.ann')
        pthANN_copy=os.path.join(outDir, base + '_' + corrstr + '.ann')
        
        # shutil.copy2(pthGRD_orig, pthGRD_copy)
        os.system('cp '+pthGRD_lut_orig+' '+pthGRD_lut_copy) # executes as parallel thread in subshell, but doesn't return errors # HERE
        print('Copied \t{} \t to\n\t {}'.format(pthGRD_lut_orig, pthGRD_lut_copy))
        if i==2: # last time only
            os.system('cp '+pthANN_orig+' '+pthANN_copy)
            print('Copied ANN \t{} \t to\n\t {}'.format(pthANN_orig, pthANN_copy))
        # subprocess.getoutput('cp '+pthGRD_orig+' '+pthGRD_copy)

            ## load real
        pthA1=os.path.join(origDir, base + pol_real[i] + '_' + corrstr + '.grd')
        pthB1=pthGRD_lut_orig
        pthOut1=os.path.join(outDir, pol_real[i] + '_GeomLut_factor.tif')
        
            ## calculate correction ratio between default GRD and RTC GRD
        cmd='gdal_calc.py -A ' + pthA1 + ' -B ' + pthB1 + ' --calc=B/A --co=COMPRESS=LZW --NoDataValue=-9999 --overwrite --outfile=' + pthOut1
        print('Executing:\n\t {}'.format(cmd))
        os.system(cmd) # HERE

    for i in range(3):        
            ## load for complex
        # pthA=r'F:\UAVSAR\bakerc_16008_19059_012_190904_L090_CX_01\raw\combined_LUT_geom_mean\HHHH_GeomLut_factor.grd'
        pthA2=os.path.join(outDir, pol_complex[i][:2] + pol_complex[i][:2] + '_GeomLut_factor.tif') #'/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/HHHH_GeomLut_factor.tif'
        pthB2=os.path.join(outDir, pol_complex[i][2:] + pol_complex[i][2:] + '_GeomLut_factor.tif') #'/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/HVHV_GeomLut_factor.tif'
        pthC2=os.path.join(origDir, base + pol_complex[i] + '_' + corrstr + '.grd')#  '/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/orig_grd/bakerc_16008_19059_012_190904_L090HHHV_CX_01.grd'
        pthOut2=os.path.join(outDir, base + pol_complex[i] + '_' + corrstr + '.grd') # '/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/bakerc_16008_19059_012_190904_L090HHHV_CX_01.grd'

        ## gdal load
        A = gdal.Open(pthA2,gdal.GA_ReadOnly)
        A = A.ReadAsArray()
        B = gdal.Open(pthB2,gdal.GA_ReadOnly)
        B = B.ReadAsArray()
        C_gdal = gdal.Open(pthC2,gdal.GA_ReadOnly)
        C = C_gdal.ReadAsArray()

        ## perform calcs on complex GRD images
        out=C*np.sqrt(A*B)

        ## write to geotiff
        out_gdal = gdal.GetDriverByName('ENVI').Create(pthOut2, C_gdal.RasterXSize, C_gdal.RasterYSize, 1, gdal.GDT_CFloat32)
        out_gdal.GetRasterBand(1).WriteArray(out)
        out_gdal.GetRasterBand(1).SetNoDataValue(-9999)
        out_gdal.SetGeoTransform(C_gdal.GetGeoTransform())
        out_gdal.SetProjection(C_gdal.GetProjection())
        out_gdal.FlushCache()
        out_gdal=None # necessary if debugging...
        print('Wrote geometric mean correction: {}'.format(pthOut2))

## testing
if __name__ == "__main__":
    complexRTC(base='bakerc_16008_19059_012_190904_L090', lutBase='bakerc_16008_19059_012_190904', corrstr='CX_01',lutDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/LUT', calname='LUT', origDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/orig_grd', outDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/auto_test')