List of changes to be made:

* add cropping procedure into workflow?
* negative values NR image edges (b/w 0 and -1)
* ONLY IF NECESSARY: run LUT 2-3 times for 2-3 landcover classes, then mask and combine
* Change my ENVI header bash script in polsar_pro_wkflow to use python script instead
* ONLY IF NECESSARY: set flatDEM = False when building LUT - but need to write and debug this branch first

Switch for real run:

* min and max looks
* flat DEM = false
* keep min_samples high ca 10000
* run over all 6 input files or just main 3?

Done:

* rename _slope.grd -> .slope
* Change 'allowed' back to all 14 classes
* add defensive checks for improper file naming or missing files
* add auto gdal warp to extract landcover mask raster
* add auto no-overwrite
* zero_DEM = false
* run for all three polarizations
* add multiprocessing to increase speed, or vectorize LUT process in radiocal.py
* Check that LUT has non-zero edges for my files
* **set min/max_look and min_samples to dynamically update based on image size and look geom**
* import 2019 lines from local

For pull request:
* include LUT folder
* new build_lut() vectorized version
* parallel?
* auto min/max look for Step 1 and 4 (radiocal.batchcal)