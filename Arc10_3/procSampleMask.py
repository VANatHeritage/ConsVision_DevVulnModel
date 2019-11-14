# ---------------------------------------------------------------------------
# procSampleMask.py
# Version: ArcGIS 10.3 / Python 2.7
# Creation Date: 2019-11-12
# Last Edit: 2019-11-14
# Creator: David Bucklin
#
# Summary: Using a list of exclusion rasters and criteria for their exclusion values,
# creates a sampling mask for the development vulnerability model
# (Value of 1 = sampling region).
# ---------------------------------------------------------------------------

# Import modules and functions
import Helper
from Helper import *
arcpy.env.overwriteOutput = True
arcpy.env.workspace = 'L:/David/projects/vulnerability_model/vulnmod_processing.gdb'
arcpy.env.scratchWorkspace = 'L:/scratch'

# year for mask
year = '2006'
# output raster name
outRast = 'L:/David/projects/vulnerability_model/sampling_mask/sampMask_' + year + 'Test.tif'

# set environments
msk = 'C:/David/scratch/jurisbnd_lam_clipbound.shp'
ext = 'L:/David/projects/vulnerability_model/vulnmod.gdb/VA_ModelMask'
snap = 'L:/David/projects/vulnerability_model/SnapRaster_albers_wgs84.tif/SnapRaster_albers_wgs84.tif'
arcpy.env.mask = msk
arcpy.env.extent = ext
arcpy.env.snapRaster = snap
arcpy.env.outputCoordinateSystem = snap
arcpy.env.cellSize = snap

# make bmi/lps combination raster
bmi = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsBMI_' + year + '.tif'
lps = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsLPS_' + year + '.tif'
bmi1 = arcpy.sa.Con(bmi, 1, 0, 'Value = 1')
lps1 = arcpy.sa.Con(lps, 1, 0, 'Value = 1')
arcpy.sa.Plus(bmi1, lps1).save('bmi1lps1_' + year)

# list of raster + clauses combinations, indicating which pixels should be EXCLUDED from sampling mask
exclList = [['bmi1lps1_' + year, 'Value = 2'],
 ['L:/David/projects/vulnerability_model/road_ramp_distance/roadDist_' + year + '.tif', 'Value > 2000'],
 ['L:/David/GIS_data/NLCD/nlcd_2016/nlcd_2016ed_LandCover_albers.gdb/lc_' + year, 'Value = 11'],
 ['L:/David/projects/vulnerability_model/from_AGOL/slpx100/slpx100_30m_albersWGS84.tif', 'Value > 7000'],
 ['L:/David/GIS_data/NLCD/nlcd_2016/nlcd_2016ed_Impervious_albers.gdb/imperv_' + year, 'Value > 0']]

# make mask
ct = 0
nmList = []
for ex in exclList:
   print('Processing raster `' + os.path.basename(ex[0]) + '`...')
   nm = 'tmpMsk' + str(ct)
   arcpy.sa.SetNull(ex[0], 1, ex[1]).save(nm)
   nmList.append(nm)
   ct += 1
arcpy.sa.CellStatistics(nmList, 'MAXIMUM', 'NODATA').save(outRast)
arcpy.BuildPyramids_management(outRast)