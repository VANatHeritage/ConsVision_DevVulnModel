"""
procSamples.py
Version: ArcGIS Pro
Creation Date: 2019-11-12
Creator: David Bucklin

Summary: This script contains processes to create a sampling mask, point samples, and attribute those samples with
values from raster variables.
"""

import arcpy.sa
import pandas
from Helper import *


def devChgImp(t1, t2, out, develmin=1, keep_intermediate=False):
   """Generate development change raster, based on impervious surface percentage from two time periods from NLCD.
   0 = not developed in either time period;
   1 = went from undeveloped to developed;
   2 = developed both time periods;
   3 = went from developed to undeveloped (rare)
   Parameters:
   - t1: Impervious raster in time 1
   - t2: Impervious raster in time 2
   - develmin = The minimum imperviousness (in percent), for a cell to be considered developed
   - keep_intermediate: Whether intermediate rasters should be saved (True), or deleted (False)
   """

   # make binary rasters
   r1 = os.path.basename(t1) + '_DevStat'
   r2 = os.path.basename(t2) + '_DevStat'

   print('Generating development status rasters...')
   remap = RemapRange([[0, develmin - 0.1, 0], [develmin - 0.1, 100.1, 1]])
   arcpy.sa.Reclassify(t1, "Value", remap, missing_values="NODATA").save(r1)
   remap = RemapRange([[0, develmin - 0.1, 0], [develmin - 0.1, 100.1, 1]])
   arcpy.sa.Reclassify(t2, "Value", remap, missing_values="NODATA").save(r2)

   print('Generating impervious change raster `' + out + '`...')
   rchg = Raster(r1) + (Raster(r2) * 100)
   remap = RemapValue([[0, 0], [1, 3], [100, 1], [101, 2]])
   arcpy.sa.Reclassify(rchg, 'Value', remap, missing_values="NODATA").save(out)
   arcpy.BuildPyramids_management(out)

   print('Cleaning up...')
   arcpy.Delete_management(rchg)
   # delete intermediate
   if not keep_intermediate:
      ls = [r1, r2]
      arcpy.Delete_management(ls)

   return out


def makeSampMask(exclList, outRast, mask=None):

   with arcpy.EnvManager(mask=mask):
      print('Making sampling mask `' + outRast + '`...')
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
      arcpy.Delete_management(nmList)


def attSamps(sampPts, rastFld, extra=None, strataFeat=None):
   # Function checks if fields exist throughout function, so this can be used to update an existing sample dataset.
   flds = [a.name for a in arcpy.ListFields(sampPts)]
   if "sampID" not in flds:
      print('Adding sampID field...')
      arcpy.CalculateField_management(sampPts, 'sampID', '!OBJECTID!', field_type="LONG")
   if strataFeat is not None:
      if 'gridid' in flds:
         arcpy.DeleteField_management(sampPts, 'gridid')
      print('Adding Unique_ID from strata features (new field name = gridid)...')
      arcpy.SpatialJoin_analysis(sampPts, strataFeat[0], 'tmp_sj')
      arcpy.JoinField_management(sampPts, 'sampID', 'tmp_sj', 'sampID', strataFeat[1])
      arcpy.AlterField_management(sampPts, strataFeat[1], 'gridid', clear_field_alias=True)
   with arcpy.EnvManager(workspace=rastFld):
      ls = [rastFld + os.sep + l for l in arcpy.ListRasters('*.tif') if l.replace('.tif', '') not in flds]
   if extra:
      ls = ls + [a for a in extra if os.path.basename(a).replace('.tif', '') not in flds]
   if len(ls) > 0:
      print('Extracting values for ' + str(len(ls)) + ' new rasters...')
      arcpy.sa.ExtractMultiValuesToPoints(sampPts, ls)
   else:
      print('No new rasters to extract values.')
   return sampPts


def main():

   # HEADER

   # set environments
   ext = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\VA_ModelMask'
   snap = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'
   arcpy.env.mask = ext
   arcpy.env.extent = ext
   arcpy.env.snapRaster = snap
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.cellSize = snap
   arcpy.env.overwriteOutput = True

   # Folder/gdb for outputs
   outFold = r'D:/git/ConsVision_DevVulnModel/inputs/samples'
   gdb = 'D:/git/ConsVision_DevVulnModel/inputs/samples/samples.gdb'
   make_gdb(gdb)
   arcpy.env.workspace = gdb

   # Bounding polygon for sampling mask
   bnd = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\jurisbnd_lam_clipbound'

   # NLCD Land cover and impervious gdbs
   lc_gdb = r'L:/David/GIS_data/NLCD/nlcd_2019/nlcd_2019ed_LandCover_albers.gdb'
   imp_gdb = r'L:/David/GIS_data/NLCD/nlcd_2019/nlcd_2019ed_Impervious_albers.gdb'

   # Folder where predictor variable rasters are stored
   rastLoc = r'D:\git\ConsVision_DevVulnModel\inputs\vars'

   # Predictor variable spreadsheet
   vars_path = r'D:\git\ConsVision_DevVulnModel\inputs\vars\vars_DV.xlsx'
   vars = pandas.read_excel(vars_path, usecols=['varname', 'source_path', 'static', 'use'])

   # Original sample points
   sampPts0 = 'TrainingPoints_0616_orig'  # this is an original copy from the feature service

   # Strata features / Unique ID column name
   strataFeat = [r'F:\David\GIS_data\snap_template_data\NestedHexes.gdb\Diam_03mile', 'Unique_ID']

   # END HEADER


   ## 1. Sampling mask
   year = '2006'
   # list of raster + where clause combinations, indicating which pixels should be EXCLUDED from the sampling mask.
   exclList = [[r'D:/git/ConsVision_DevVulnModel/inputs/masks/conslands_pmult_' + year + '.tif', 'Value = 0'],
               ['D:/git/ConsVision_DevVulnModel/inputs/vars/' + year + '/roadDist.tif', 'Value > 2000'],
               ['D:/git/ConsVision_DevVulnModel/inputs/vars/2006/slpx100.tif', 'Value > 7000'],
               [lc_gdb + os.sep + 'lc_' + year, 'Value = 11'],
               [imp_gdb + os.sep + 'imperv_' + year, 'Value > 0']]
   sampMask = outFold + os.sep + 'sampMask_' + year + '.tif'
   if not arcpy.Exists(sampMask):
      makeSampMask(exclList, sampMask, mask=bnd)


   ## 2. Make development change raster, and sample points
   chg = [['06', '16']]  #, ['16', '19']]
   for y in chg:
      devChg = outFold + os.sep + 'DevChg' + y[0] + '_' + y[1] + '.tif'  # any impervious
      if not arcpy.Exists(devChg):
         print('Raster ' + devChg + ' does not exist, making new...')
         # Development change (any impervious).
         devChgImp(imp_gdb + os.sep + 'imperv_20' + y[0], imp_gdb + os.sep + 'imperv_20' + y[1], devChg, develmin=1)

   # TODO: add Kirsten's sample point generation function.

   ## 3. Attribute sample points

   # Attribute sample points with all variables.
   year = "2006"
   if year == "2016":
      # NOTE: DID NOT USE.
      # [extra] holds paths to 'static' variables stored in the 2006 folder only.
      # They should get attached to 2016, if sample points are generated for that time period.
      ex = vars['varname'][vars['static'] == 1]
      extra = [rastLoc + os.sep + '2006' + os.sep + e + '.tif' for e in ex.to_list()]
      sampPts = 'TrainingPoints_1619'
   else:
      extra = None
      sampPts = 'TrainingPoints_0616'
   if not arcpy.Exists(sampPts):
      arcpy.CopyFeatures_management(sampPts0, sampPts)
   attSamps(sampPts, rastLoc + os.sep + year, extra, strataFeat)


   ## 4. Make masks used to apply to adjusted model rasters

   # Water mask. This covers ONLY areas within the Virginia boundary.
   va_bnd = r'D:\git\ConsVision_DevVulnModel\ArcGIS\dev_vuln.gdb\VirginiaCounty_Dissolve'
   out_dir = r'D:\git\ConsVision_DevVulnModel\inputs\masks'
   years = ['2006', '2019']
   for year in years:
      out_rast = out_dir + os.sep + 'water_mask_' + year + '.tif'
      print(out_rast)
      with arcpy.EnvManager(extent=va_bnd, mask=va_bnd):
         arcpy.sa.SetNull(lc_gdb + os.sep + 'lc_' + year, 1, 'Value = 11').save(out_rast)
   # Development masks (used for setting already-developed to 101 in adjusted model rasters)
   for year in years:
      out_rast = out_dir + os.sep + 'dev_mask_' + year + '.tif'
      print(out_rast)
      with arcpy.EnvManager(extent=va_bnd, mask=va_bnd):
         arcpy.sa.SetNull(imp_gdb + os.sep + 'imperv_' + year, 1, 'Value > 0').save(out_rast)

   # clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses('tmp_*') + arcpy.ListRasters('tmp_*'))

if __name__ == '__main__':
   main()




