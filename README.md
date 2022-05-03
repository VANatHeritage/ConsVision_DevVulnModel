# ConservationVision Development Vulnerability Model
The Virginia Development Vulnerability Model quantifies the predicted risk of conversion from "natural", rural, or other open space lands to urbanized or other built-up land uses. 

The most recent edition of the model was released in 2022. For more information, see [here](https://www.dcr.virginia.gov/natural-heritage/vaconvisvulnerable).

---
## Script overview

### General-purpose

- **Helper.py**: a set of general-purpose functions, imported by all other python scripts
- **BatchDownloadZipFiles.py**: downloads a set of zip files from an FTP site

### Predictor variable processing

- **proc3DEP.py**: functions for batch-downloading and post-processing elevation files from the 3DEP program
- **procCensus.py**: functions for processing U.S. Census data, primarily for developing urban cores from block data
- **procConsLands.py**: processing for conservation lands data, including predictor variables and the protection multiplier
- **procNHD.py**: processing for NHD-based predictor variables
- **procNLCD.py**: processing for most predictor variables from National Land Cover Database data
- **procNLCDImpDesc.py**: develops cost surfaces and distance to road/ramp predictors from NLCD impervious descriptor (with Tiger-Line roads used as ancillary data).
- **procTravelTime.py**: runs cost distance (travel time) analyses for urban cores

### Model input preparation

- **finalizeVars.py**: finalizes all predictor variables for the Development Vulnerability Model (clip/mask, convert to integer, and output as a TIF file)
- **procSamples.py**: processes to create a sampling mask, point samples, attribute those samples with values from raster variables. Also creates development and water masks used to make the final Development Vulnerability model

### Random forest model

- **RFModel_run.R**: creates a new random forest model with specified samples. Includes entire process: variable selection, cross-validation, final model with partial plots
- **RFModel_predict.R**: functions to run post-model processes for the development vulnerability random forest model, including creating predictions raster(s), adjusting predictions raster using protection multiplier, development, and water, and validating a model using validation points data set. These functions are called at the end of **RFModel_run.R**.