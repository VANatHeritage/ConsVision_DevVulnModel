# ---------------------------------------------------------------------------
# procNLCDImpDesc.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creator: David N. Bucklin
# Creation Date: 2019-09-11

# Summary:
# Used to create cost surfaces from NLCD's Impervious Descriptor raster dataset (released with NLCD 2016).
# Both Limited access highways and local (all other roads) cost rasters are output.
# Speeds are assigned in 'Remap' variable; alter this as needed.

# Tiger roads are used to define limited access highways and ramps. 2018 Tiger was used,
# as this dataset was found to have the better LAH/ramp classification than older datasets (i.e. 2016).
# This information is only used to reclassify the impervious descriptor dataset (it does not "create" roads).
# This potentially could miss LAH/ramps from earlier time periods that are not in the same location
# as the Tiger 2018 LAH/ramps.

# These cost rasters can be used with the ServiceAreas toolset (https://github.com/VANatHeritage/ServiceAreas).

# FIXME: Tunnels are not represented in this dataset (they are not surface roads).
#  SOLUTION: Major tunnels were manually digitized and are burned in to the dataset (see 'burnin_tunnels' feature class)
# ---------------------------------------------------------------------------

# Import Helper module and functions
from Helper import *


def ImpDesc_CostSurf(impDesc, urbanAreas, out_gdb, lah, ramps, ramp_pts, burn_tunnels=None):
   # working: this works, but not sure if want to use. Another option would be to use Impervious Descriptor to adjust a
   #  current roads dataset (vector), assigning those not existing in previous time period to be excluded.
   #  Any other options???

   # reclassify to 1-6 values
   print("Reclassifying impervious descriptor roads...")
   remap0 = RemapValue([[20, 2], [21, 4], [22, 6]])  # These are primary/secondary/tertiary roads.
   arcpy.sa.Reclassify(impDesc, "Value", remap0, "NODATA").save("tmp_imp0")
   arcpy.sa.Con(arcpy.sa.IsNull('tmp_imp0'), 0, 'tmp_imp0', "VALUE = 1").save('tmp_imp1')  # Set NoData to 0

   print('Rasterizing urban areas...')
   arcpy.CopyFeatures_management(urbanAreas, 'tmp_ua')
   arcpy.CalculateField_management('tmp_ua', 'rast', "1", field_type="SHORT")
   arcpy.PolygonToRaster_conversion('tmp_ua', 'rast', 'tmp_ua_rast0')
   arcpy.sa.Con(arcpy.sa.IsNull('tmp_ua_rast0'), 0, 1, "VALUE = 1").save('tmp_ua_rast')

   # create urban-area adjusted impervious descriptor roads
   imp = 'imp_rcl'
   if burn_tunnels is not None:
      print('Burning in tunnels...')
      arcpy.PolylineToRaster_conversion(burn_tunnels, 'rast', 'tmp_tunnels', cellsize='tmp_imp1')
      arcpy.sa.CellStatistics(['tmp_imp1', 'tmp_tunnels'], 'MAXIMUM').save('tmp_imp2')
      arcpy.sa.Minus('tmp_imp2', 'tmp_ua_rast').save(imp)
   else:
      arcpy.sa.Minus('tmp_imp1', 'tmp_ua_rast').save(imp)

   print('Making euclidean distance to roads layer (allRoads_dist)...')
   arcpy.sa.SetNull(imp, 1, 'Value < 1').save('tmp_allrd')
   arcpy.sa.EucDistance('tmp_allrd').save('allRoads_dist')

   print('Processing limited-access highways...')
   # process limited access roads/ramps for reclassifying roads in impervious descriptor
   arcpy.PairwiseBuffer_analysis(lah, 'tmp_rd_bufflah', 45, dissolve_option="ALL")
   # set LAH areas for Primary/Secondary roads to value of 100 (Tertiary road class ignored for LAH)
   arcpy.sa.ExtractByMask(imp, 'tmp_rd_bufflah').save('tmp_lah2')
   arcpy.sa.Reclassify('tmp_lah2', "Value", RemapRange([[-10, 0, 0], [0.5, 4.5, 100], [4.5, 126, 0]])).save('tmp_lah_raster')

   # only take ramps that intersect LAH
   print('Processing ramps...')
   arcpy.PairwiseBuffer_analysis(ramps, 'tmp_rd_buffrmp', 45, dissolve_option="ALL")
   arcpy.MultipartToSinglepart_management('tmp_rd_buffrmp', 'tmp_rd_buffrmp1')
   rmp_lyr = arcpy.MakeFeatureLayer_management('tmp_rd_buffrmp1')
   arcpy.SelectLayerByLocation_management(rmp_lyr, "INTERSECT", "tmp_rd_bufflah", "#", "NEW_SELECTION")
   # set all ramp road areas to value of 10 (ramps can be any road class)
   arcpy.sa.ExtractByMask(imp, rmp_lyr).save('tmp_rmp')
   arcpy.sa.Reclassify('tmp_rmp', "Value", RemapRange([[-10, 0, 0], [0.5, 6.5, 10], [6.5, 126, 0]])).save('tmp_rmp_raster')

   print('Adding LAH (+100) and RMP (+10) indicators to reclassified impervious descriptor...')
   arcpy.sa.CellStatistics(['tmp_lah_raster', 'tmp_rmp_raster'], "MAXIMUM", "DATA").save('tmp_lah_rmp')
   arcpy.sa.CellStatistics([imp, 'tmp_lah_rmp'], "SUM", "DATA").save('tmp_imprcl')

   # now set NULL LAH areas (ramps will get included in both local/LAH rasters)
   arcpy.sa.SetNull('tmp_imprcl', 'tmp_imprcl', 'Value > 100').save('tmp_imprcl_nolah')
   print('Reclassifying to MPH...')
   # reclassify values to MPH
   speed_remap = RemapValue([[-1, 3], [0, 3],  # background
                             [1, 45], [2, 55], [3, 35], [4, 45], [5, 25], [6, 35],  # not ramp/hwy
                             [11, 45], [12, 55], [13, 35], [14, 45], [15, 25], [16, 35],  # ramp
                             [101, 60], [102, 70], [103, 50], [104, 60]])  # hwy
   arcpy.sa.Reclassify('tmp_imprcl_nolah', 'Value', speed_remap).save('tmp_mph_local1')
   # assign an MPH to NULL LAH areas for the local cost raster (over/under-passes)
   arcpy.sa.ExtractByMask(arcpy.sa.FocalStatistics('tmp_mph_local1', NbrCircle(3, "CELL"), "MAXIMUM", "DATA"),
                          'tmp_lah_raster').save('tmp_mph_local2')

   print('Calculating cost from MPH...')
   # add the two local MPH rasters, convert to cost
   arcpy.sa.CellStatistics(['tmp_mph_local1', 'tmp_mph_local2'], "MAXIMUM", "DATA").save('local_mph')
   (0.037 / Raster('local_mph')).save('local_cost')
   # now output an LAH-only raster (ramps included)
   arcpy.sa.SetNull('tmp_imprcl', 'tmp_imprcl',
                    'Value NOT IN (11,12,13,14,15,16,101,102,103,104)').save('tmp_imprcl_lah')
   arcpy.sa.Reclassify('tmp_imprcl_lah', 'Value', speed_remap).save('lah_mph')
   (0.037 / Raster('lah_mph')).save('lah_cost')

   # Ramp processing (remove those on NODATA from LAH cost raster)
   print('Selecting ramp points...')
   arcpy.sa.ExtractValuesToPoints(ramp_pts, 'lah_cost', 'rmpt0')
   arcpy.Select_analysis('rmpt0', "ramp_points", '"RASTERVALU" <> -9999')
   arcpy.Delete_management('rmpt0')

   print('Making euclidean distance to ramps layer (allRamps_dist)...')
   arcpy.sa.EucDistance('ramp_points').save('allRamps_dist')

   # delete temp, build pyramids
   print('Deleting temporary files...')
   rm = arcpy.ListFeatureClasses("tmp_*") + (arcpy.ListRasters("tmp_*"))
   try:
      arcpy.Delete_management(rm)
   except:
      print('Not all temporary files could be deleted.')
   arcpy.BuildPyramidsandStatistics_management(arcpy.env.workspace)

   return out_gdb


# Tiger/Line roads (only LAH and ramps are used from this dataset, for reclassifying those roads)
road = r'L:\David\projects\RCL_processing\Tiger_2018\roads_proc.gdb\all_centerline'
lah = arcpy.MakeFeatureLayer_management(road, where_clause="MTFCC IN ('S1100')")
ramp = arcpy.MakeFeatureLayer_management(road, where_clause="MTFCC IN ('S1630')")
ramp_pts = r'L:\David\projects\RCL_processing\Tiger_2018\cost_surfaces.gdb\rmpt_final'
# burn in tunnels feature class
burn = r'L:\David\projects\RCL_processing\Tiger_2018\roads_proc.gdb\burnin_tunnels'

# OSM
# lah_rmp = r'E:\projects\OSM\network\OSM_RoadsNet_Albers.gdb\Roads_Hwy'
# lah = arcpy.MakeFeatureLayer_management(lah_rmp, where_clause="code = 5111")
# ramp = arcpy.MakeFeatureLayer_management(lah_rmp, where_clause="code = 5131")
# ramp_pts = r'E:\projects\OSM\network\OSM_RoadsNet_Albers.gdb\ramp_points'

# Impervious descriptor
impDesc = r'L:\David\GIS_data\NLCD\nlcd_2019\nlcd_2019ed_Impervious_albers.gdb\impDescriptor_2016'
# urban areas
urbanAreas = r'L:\David\GIS_data\US_CENSUS_TIGER\UrbanAreas\tl_2016_us_uac10\tl_2016_us_uac10.shp'

# workspace (will be created if not existing)
out_gdb = r'L:\David\projects\vulnerability_model\vars\nlcd_based\cost_surfaces\costSurface_2016.gdb'
make_gdb(out_gdb)
arcpy.env.workspace = out_gdb

# Environment settings
snap = impDesc
arcpy.env.mask = snap
arcpy.env.extent = snap
arcpy.env.cellSize = snap
arcpy.env.snapRaster = snap
arcpy.env.outputCoordinateSystem = snap
arcpy.env.overwriteOutput = True

# Create cost surfaces
ImpDesc_CostSurf(impDesc, urbanAreas, out_gdb, lah, ramp, ramp_pts, burn)


# end
