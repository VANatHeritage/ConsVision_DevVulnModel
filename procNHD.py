"""
procNHD.py
Version:  ArcGIS Pro
Creation Date: 2022-03-17
Creator:  David Bucklin

Summary:
Processing for NHD-based predictor variables for the Development vulnerability model.

NOTE: these variables were originally processed in the NLCD variable geodatabase:
out_gdb = r'F:\David\projects\vulnerability_model\vars\nlcd_based\nlcdv19_variables.gdb'
"""
from Helper import *

# HEADER

# NHD geodatabase
nhd_gdb = r'F:\David\GIS_data\NHD\NHD_Merged.gdb'

# Outputs
out_folder = r'F:\David\projects\vulnerability_model\vars\nhd_based'
out_gdb = out_folder + os.sep + 'nhd_variables.gdb'
make_gdb(out_gdb)

# set environment variables
snap = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'
arcpy.env.mask = snap
arcpy.env.extent = snap
arcpy.env.snapRaster = snap
arcpy.env.outputCoordinateSystem = snap
arcpy.env.cellSize = snap
arcpy.env.overwriteOutput = True

# END HEADER

# Euclidean distance to NHD-based features

# Bay/Ocean
nhda = arcpy.MakeFeatureLayer_management(nhd_gdb + os.sep + 'NHDArea', where_clause="FType IN (445)")
nhdw = arcpy.MakeFeatureLayer_management(nhd_gdb + os.sep + 'NHDWaterbody', where_clause="FType IN (312, 493)")
arcpy.Merge_management([nhda, nhdw], 'nhd_bayOcean')
arcpy.sa.EucDistance('nhd_bayOcean').save('edist_bayOcean')

# Lake/resv > 100 acres
nhd_query = "FType IN (390, 436) AND AreaSqKm >= 0.404686"
arcpy.Select_analysis(nhd_gdb + os.sep + 'NHDWaterbody', 'nhd_lakeResv', where_clause=nhd_query)
arcpy.sa.EucDistance('nhd_lakeResv').save('edist_lakeResv')

# River/canal only
nhd_query = "FType IN (537, 336, 431, 460)"
arcpy.Select_analysis(nhd_gdb + os.sep + 'NHDArea', 'nhd_riverCanal', where_clause=nhd_query)
arcpy.sa.EucDistance('nhd_riverCanal').save('edist_riverCanal')
arcpy.sa.CellStatistics(['edist_lakeResv', 'edist_riverCanal'], 'MINIMUM').save('edist_inlandWater')

# Final combined layer
arcpy.sa.CellStatistics(['edist_bayOcean', 'edist_inlandWater'], 'MINIMUM').save('edist_oceanInland')