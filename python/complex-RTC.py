import numpy as np
import osgeo.gdal as gdal
# from matplotlib import pyplot as plt
import os
# TODO: finish and import from /mnt/d/Dropbox/Python/UAVSAR-Radiometric-Calibration/local/multiply-2.py
def complexRTC(base, ):
    '''Takes LUT-corrected real grd files, calculates correction ratio, applies to non LUT-corrected grd files'''
    ## vars
    pol_real=['HHHH','VVVV','HVHV']
    
    for i in range(3):
        ## load
        # pthA=r'F:\UAVSAR\bakerc_16008_19059_012_190904_L090_CX_01\raw\combined_LUT_geom_mean\HHHH_GeomLut_factor.grd'
        pthA=os.path.join(outdir, pol_real[i], '_GeomLut_factor.tif') #'/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/HHHH_GeomLut_factor.tif'
        pthB=os.path.join(outdir, pol_real[i], '_GeomLut_factor.tif') #'/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/HVHV_GeomLut_factor.tif'
        pthC='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/orig_grd/bakerc_16008_19059_012_190904_L090HHHV_CX_01.grd'
        pthOut='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean/bakerc_16008_19059_012_190904_L090HHHV_CX_01.grd'

        ## gdal load
        A = gdal.Open(pthA,gdal.GA_ReadOnly)
        A = A.ReadAsArray()
        B = gdal.Open(pthB,gdal.GA_ReadOnly)
        B = B.ReadAsArray()
        C_gdal = gdal.Open(pthC,gdal.GA_ReadOnly)
        C = C_gdal.ReadAsArray()

        ## calcs
        out=C*np.sqrt(A*B)

        ## write to geotiff
        out_gdal = gdal.GetDriverByName('ENVI').Create(pthOut, C_gdal.RasterXSize, C_gdal.RasterYSize, 1, gdal.GDT_CFloat32)
        out_gdal.GetRasterBand(1).WriteArray(out)
        out_gdal.GetRasterBand(1).SetNoDataValue(-9999)
        out_gdal.SetGeoTransform(C_gdal.GetGeoTransform())
        out_gdal.SetProjection(C_gdal.GetProjection())
        out_gdal.FlushCache()
        out_gdal=None # necessary if debugging...
        print('Wrote: '.format('foo'))

complexRTC(base='bakerc_16008_19059_012_190904_L090', lutBase='bakerc_16008_19059_012_190904', suffix='CX_01',lutDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/LUT', origDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/orig_grd', outDir='/mnt/f/UAVSAR/bakerc_16008_19059_012_190904_L090_CX_01/raw/combined_LUT_geom_mean')