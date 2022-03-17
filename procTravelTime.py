"""
procTravelTime
Version:  ArcGIS Pro / Python 3.x
Creator: David N. Bucklin
Creation Date: 2021-09-09

This script runs raster cost distance (travel time) analyses for urban areas and/or cores for use as predictors in the
development vulnerability model.

Prerequisites: Cost surfaces developed using procNLCDImpDesc.py. Uses the ServiceAreas toolset (a standalone
repository) to run travel time analyses.
"""
from Helper import *
sys.path.append(r'D:\git\ServiceAreas')
from makeServiceAreas import *


def main():

   # Set NLCD year
   yr = '2019'

   costGDB = r'C:\David\proc\costSurface_' + yr + '.gdb'
   # costGDB = r'F:\David\projects\vulnerability_model\vars\nlcd_based\cost_surfaces\costSurface_' + yr + '.gdb'
   costRastLoc = costGDB + os.sep + 'local_cost'
   costRastHwy = costGDB + os.sep + 'lah_cost'
   rampPts = costGDB + os.sep + 'ramp_points'
   rampPtsID = 'UniqueID'  # unique ramp segment ID attribute field, since some ramps have multiple points
   arcpy.DeleteField_management(rampPts, ['FID_rmp', 'FID_loc', 'ORIG_FID', 'RASTERVALU'])

   # Set environments
   arcpy.env.extent = costRastLoc
   arcpy.env.mask = costRastLoc
   arcpy.env.snapRaster = costRastLoc
   arcpy.env.outputCoordinateSystem = costRastLoc
   arcpy.env.cellSize = costRastLoc

   # Travel time to urban Cores

   # Input features
   if yr == '2006':
      accFeat0 = r'F:\David\projects\vulnerability_model\vars\travel_time\UrbanCores2000\UrbanCores2000.shp'  # T1
   elif yr == "2019":
      accFeat0 = r'F:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\UrbanCores2010_method3'  # T2
   # Output geodatabase
   outGDB = r'C:\David\proc\urbanCores' + yr + '_travelTime.gdb'

   # Select input features, run function
   accFeat = arcpy.MakeFeatureLayer_management(accFeat0, where_clause="CORE_TYPE <> 0")
   grpFld = 'CORE_TYPE'
   maxCost = None  # in minutes
   attFld = None  # None will return actual cost distance
   makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

   # Make summaries for multiple groups
   arcpy.env.workspace = outGDB
   rasts = ['grp_' + i + '_servArea' for i in ['2', '3', '4', '5']]
   arcpy.sa.CellStatistics(rasts, 'MINIMUM').save('grp_2_5_servArea')
   rasts = ['grp_' + i + '_servArea' for i in ['4', '5']]
   arcpy.sa.CellStatistics(rasts, 'MINIMUM').save('grp_4_5_servArea')
   rasts = ['grp_' + i + '_servArea' for i in ['2', '3']]
   arcpy.sa.CellStatistics(rasts, 'MINIMUM').save('grp_2_3_servArea')

   # Run a cost distance on local roads to ramps
   arcpy.sa.CostDistance(rampPts, costRastLoc, None).save('tt_ramps')

   # copy GDBs to archive location
   # arcpy.Copy_management(outGDB, r'F:\David\projects\vulnerability_model\vars\travel_time' + os.sep + os.path.basename(outGDB))
   # arcpy.Copy_management(costGDB, r'F:\David\projects\vulnerability_model\vars\nlcd_based\cost_surfaces' + os.sep + os.path.basename(costGDB))


if __name__ == '__main__':
   main()
