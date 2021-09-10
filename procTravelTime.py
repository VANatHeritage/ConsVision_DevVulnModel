'''
Cost Distance for urban areas / cores (TBD)
'''

import sys

import arcpy.sa

from Helper import *
sys.path.append(r'E:\git\ServiceAreas')
from makeServiceAreas import *


def main():

   # Set up variables
   # costGDB = r'L:\David\projects\vulnerability_model\cost_surfaces\cost_surfaces_2006.gdb'  # old
   costGDB = r'L:\David\projects\vulnerability_model\vars\nlcd_based\cost_surfaces\costSurface_2006.gdb'
   costRastLoc = costGDB + os.sep + 'local_cost'
   costRastHwy = costGDB + os.sep + 'lah_cost'
   rampPts = costGDB + os.sep + 'ramp_points'
   rampPtsID = 'UniqueID'  # unique ramp segment ID attribute field, since some ramps have multiple points

   # Set environments
   arcpy.env.extent = costRastLoc
   arcpy.env.mask = costRastLoc
   arcpy.env.snapRaster = costRastLoc
   arcpy.env.outputCoordinateSystem = costRastLoc
   arcpy.env.cellSize = costRastLoc

   # time to closest facility (all points considered at once). Returns actual cost distance in minutes.
   # accFeat0 = r'L:\David\projects\vulnerability_model\vars\cost_distance\UrbanCores2000\UrbanCores2000.shp'  # 2006
   # outGDB = r'E:\scratch\urbanCores2006_travelTime.gdb'
   # outGDB = r'L:\David\projects\vulnerability_model\vars\travel_time\urbanCores2006_travelTime.gdb'

   accFeat0 = r'L:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\UrbanCores2010_method3'  # 2016
   outGDB = r'E:\scratch\urbanCores2016_travelTime.gdb'

   accFeat = arcpy.MakeFeatureLayer_management(accFeat0, where_clause="CORE_TYPE <> 0")
   grpFld = 'CORE_TYPE'
   maxCost = None  # in minutes
   attFld = None  # will return actual cost distance
   makeServiceAreas(outGDB, accFeat, costRastLoc, costRastHwy, rampPts, rampPtsID, grpFld, maxCost, attFld)

   # Make summaries for groups 2-5 and 4-5
   arcpy.env.workspace = outGDB
   rasts = ['grp_' + i + '_servArea' for i in ['2', '3', '4', '5']]
   arcpy.sa.CellStatistics(rasts, 'MINIMUM').save('grp_2_5_servArea')
   rasts = ['grp_' + i + '_servArea' for i in ['4', '5']]
   arcpy.sa.CellStatistics(rasts, 'MINIMUM').save('grp_4_5_servArea')


if __name__ == '__main__':
   main()