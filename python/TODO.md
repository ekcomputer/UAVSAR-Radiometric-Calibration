List of changes to be made:

* add multiprocessing to increase speed, or vectorize LUT process in radiocal.py
* add cropping procedure into workflow?
* add auto min/max look angle masking?
* **set min/max_look and min_samples to dynamically update based on image size and look geom**
* import 2019 lines from local

Switch for real run:

* min and max looks
* flat DEM = false
* run for all three polarizations
* keep min_samples high ca 10000
* run over all 6 input files or just main 3?
* Check that LUT has non-zero edges for my files

Done:

* rename _slope.grd -> .slope
* Change 'allowed' back to all 14 classes
* add defensive checks for improper file naming or missing files
* add auto gdal warp to extract landcover mask raster
* add auto no-overwrite

For pull request:
* include LUT folder
* new build_lut() vectorized version
* parallel?