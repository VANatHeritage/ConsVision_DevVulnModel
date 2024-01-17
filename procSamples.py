"""
procSamples.py
Version: ArcGIS Pro
Creation Date: 2019-11-12
Creator: David Bucklin

Summary: This script contains processes to create a sampling mask, point samples, and attribute those samples with
values from raster variables.
It also includes the steps used to make water/developed masks for adjusting the final model.
"""
from Helper import *


def devChgImp(t1, t2, out, develmin=1, keep_intermediate=False):
   """Generate development change status raster, based on impervious surface percentage from two time periods from NLCD.
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
   """Given a list of of rasters and exclusion queries, make a mask indicating where samples can be placed.
   Exclusion queries are SQL which indicate where samples cannot be placed (e.g. "Value = 11" for water in NLCD).
   :param exclList: list of rasters and associated exclusion query (e.g. [[r1, query], [r2, query], ...])
   :param outRast: Output raster sampling mask
   :param mask: global mask to apply to processing
   :return: outRast
   """
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


def makeStrataFeat(inFeat, outFeat, inBnd, trainPercentage=50):
   """
   Create a sampling strata feature class
   :param inFeat: input features
   :param outFeat: output features, with new attributes [SampleType, SRC_FEAT]
   :param inBnd: boundary polygon feature class. Only features intersecting this layer will be included
   :param trainPercentage: Percentage of features to include in the training data stratum. All others assigned to
   validation.
   :return: outFeat
   """
   print("Selecting strata features intersecting bounding polygon...")
   lyr = arcpy.MakeFeatureLayer_management(inFeat)
   arcpy.SelectLayerByLocation_management(lyr, "INTERSECT", inBnd)
   arcpy.CopyFeatures_management(lyr, 'tmp_int')
   print("Making strata features...")
   arcpy.SubsetFeatures_ga('tmp_int', 'tmp_trn', 'tmp_test', trainPercentage, "PERCENTAGE_OF_INPUT")
   arcpy.CalculateField_management('tmp_trn', 'SampleType', "'training'")
   arcpy.CalculateField_management('tmp_test', 'SampleType', "'validation'")
   arcpy.Merge_management(['tmp_trn', 'tmp_test'], outFeat)
   arcpy.CalculateField_management(outFeat, 'SRC_FEAT', "'" + os.path.basename(inFeat) + "'")
   arcpy.Delete_management(['tmp_trn', 'tmp_test'])
   return outFeat


def makeSamps(devChg, sampMask, strataFeat, outTrain, outValidation, sepDist="0.5 Miles"):
   """
   Create training and validation point samples.
   :param devChg: Development change status raster
   :param sampMask: Sampling mask raster
   :param strataFeat: Strata feature class
   :param outTrain: output training points feature class
   :param outValidation: output validation points feature class
   :param sepDist: minimum separation distance between samples of the same class
   :return: [outTrain, outValidation]
   """
   print("Masking development change to sampling mask...")
   dc = 'tmp_dc'
   arcpy.sa.ExtractByMask(devChg, sampMask).save(dc)

   print("Making points for developed class...")
   arcpy.sa.SetNull(dc, 1, "Value <> 1").save('tmp_dev')
   # Make new-development points
   arcpy.RasterToPolygon_conversion('tmp_dev', 'tmp_dev_polys', "NO_SIMPLIFY", "Value", "SINGLE_OUTER_PART")
   lyr = arcpy.MakeFeatureLayer_management('tmp_dev_polys', where_clause="Shape_Area >= 8100")
   arcpy.CreateRandomPoints_management(arcpy.env.workspace, "tmp_DevPts", lyr, "0 0 250 250", 3, sepDist, "POINT")
   del lyr
   arcpy.DeleteIdentical_management("tmp_DevPts", "Shape", sepDist)
   arcpy.CalculateField_management('tmp_DevPts', 'DevStatus', '1', field_type="SHORT")

   print("Making points for not-developed class...")
   arcpy.CreateRandomPoints_management(arcpy.env.workspace, "tmp_NoDevPts", strataFeat,
                                       "0 0 250 250", 10, sepDist, "POINT")
   arcpy.sa.ExtractMultiValuesToPoints('tmp_NoDevPts', [dc])
   # Remove points not falling in DevChg = 0 areas.
   lyr = arcpy.MakeFeatureLayer_management('tmp_NoDevPts')
   arcpy.SelectLayerByAttribute_management(lyr, "NEW_SELECTION", dc + " = 0", "INVERT")
   arcpy.DeleteFeatures_management(lyr)
   del lyr
   # Thin points
   arcpy.DeleteIdentical_management('tmp_NoDevPts', "Shape", sepDist)
   arcpy.CalculateField_management('tmp_NoDevPts', 'DevStatus', '0', field_type="SHORT")

   print("Creating `" + outTrain + "` and `" + outValidation + "` datasets...")
   arcpy.Merge_management(['tmp_DevPts', 'tmp_NoDevPts'], 'tmp_all_samples')
   todel = [a.name for a in arcpy.ListFields('tmp_all_samples') if a.name not in ['OBJECTID', 'Shape', 'DevStatus']]
   arcpy.DeleteField_management('tmp_all_samples', todel)
   arcpy.JoinAttributesFromPolygon_ca('tmp_all_samples', strataFeat, ["SRC_FEAT", "Unique_ID", "SampleType"])
   arcpy.AlterField_management('tmp_all_samples', 'Unique_ID', 'gridid', 'Unique_ID')
   arcpy.Select_analysis('tmp_all_samples', outTrain, "SampleType = 'training'")
   arcpy.Select_analysis('tmp_all_samples', outValidation, "SampleType = 'validation'")

   return [outTrain, outValidation]


def attSamps(sampPts, rastFold, extra=None):
   """
   Attribute samples with values from a set of raster datasets. Fields are added to the existing feature class. The
   function checks if fields already exist, and skips processing for rasters matching those fields.
   :param sampPts: Input sample points
   :param rastFold: Folder holding rasters
   :param extra: List of rasters (which are not found in rastFold) for which to extract values.
   :return: sampPts

   NOTE: `extra` can accept paths to 'static' variables rasters which are not in the provided raster folder
   (`rastFold`), which would then also be included as attributes. In practice, this is only needed for attributing
   samples outside of the training time period, which was not necessary for the 2022 model. Example below.
   vars_path = r'D:\git\ConsVision_DevVulnModel\inputs\vars\vars_DV.xlsx'
   vars = pandas.read_excel(vars_path, usecols=['varname', 'source_path', 'static', 'use'])
   ex = vars['varname'][vars['static'] == 1]
   extra = [rastLoc + os.sep + '2006' + os.sep + e + '.tif' for e in ex.to_list()]
   """
   flds = [a.name for a in arcpy.ListFields(sampPts)]
   if "sampID" not in flds:
      print('Adding sampID field...')
      arcpy.CalculateField_management(sampPts, 'sampID', '!OBJECTID!', field_type="LONG")
   with arcpy.EnvManager(workspace=rastFold):
      ls = [rastFold + os.sep + l for l in arcpy.ListRasters('*.tif') if l.replace('.tif', '') not in flds]
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
   outFold = r'D:\git\ConsVision_DevVulnModel\inputs\samples'
   gdb = r'D:\git\ConsVision_DevVulnModel\inputs\samples\samples.gdb'
   make_gdb(gdb)
   arcpy.env.workspace = gdb

   # Bounding polygon for sampling mask
   bnd = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\jurisbnd_lam_clipbound'

   # NLCD Land cover and impervious gdbs
   lc_gdb = r'F:\David\GIS_data\NLCD\nlcd_2021\nlcd_2021ed_LandCover_albers.gdb'
   imp_gdb = r'F:\David\GIS_data\NLCD\nlcd_2021\nlcd_2021ed_Impervious_albers.gdb'

   # Folder where predictor variable rasters are stored
   rastLoc = r'D:\git\ConsVision_DevVulnModel\inputs\vars'

   # Strata features. Needs to have a column `Unique_ID` for unique polygons
   inStrata = r'F:\David\GIS_data\snap_template_data\NestedHexes.gdb\Diam_03mile'

   # END HEADER


   ## 1. Make sampling mask
   var_yr = '2006'
   # list of raster + clause combinations, clauses indicating which pixels should be EXCLUDED from the sampling mask.
   exclList = [['D:/git/ConsVision_DevVulnModel/inputs/masks/conslands_pmult_' + var_yr + '.tif', 'Value = 0'],
               ['D:/git/ConsVision_DevVulnModel/inputs/vars/' + var_yr + '/roadDist.tif', 'Value > 2000'],
               ['D:/git/ConsVision_DevVulnModel/inputs/vars/2006/slpx100.tif', 'Value > 7000'],
               [lc_gdb + os.sep + 'lc_' + var_yr, 'Value = 11'],
               [imp_gdb + os.sep + 'imperv_' + var_yr, 'Value > 0']]
   sampMask = outFold + os.sep + 'sampMask_' + var_yr + '.tif'
   if not arcpy.Exists(sampMask):
      makeSampMask(exclList, sampMask, mask=bnd)


   ## 2. Make development change raster
   chg_yrs = ['06', '16']
   devChg = outFold + os.sep + 'DevChg' + chg_yrs[0] + '_' + chg_yrs[1] + '.tif'
   if not arcpy.Exists(devChg):
      print('Raster ' + devChg + ' does not exist, making new...')
      devChgImp(imp_gdb + os.sep + 'imperv_20' + chg_yrs[0], imp_gdb + os.sep + 'imperv_20' + chg_yrs[1], devChg)


   ## 3. Generate sample points
   # NOTE: Training/Validation points for the 2022 model were developed manually in ArcGIS Pro.
   # The functions used in this step were added later to replicate the process used.
   chg_yrs = ['06', '16']
   devChg = outFold + os.sep + 'DevChg' + chg_yrs[0] + '_' + chg_yrs[1] + '.tif'
   sampMask = outFold + os.sep + 'sampMask_20' + chg_yrs[0] + '.tif'
   strataFeat = 'HexStrata'
   outTrain = 'TrainingPoints_' + chg_yrs[0] + chg_yrs[1]
   outValidation = 'ValidationPoints_' + chg_yrs[0] + chg_yrs[1]

   makeStrataFeat(inStrata, strataFeat, bnd)
   makeSamps(devChg, sampMask, strataFeat, outTrain, outValidation)


   ## 4. Attribute sample points
   chg_yrs = ['06', '16']
   sampPts = 'TrainingPoints_' + chg_yrs[0] + chg_yrs[1]
   attSamps(sampPts, rastLoc + os.sep + '20' + chg_yrs[0], extra=None)


   ## 5. Make masks used to apply to adjusted model rasters
   # Water mask. This covers ONLY areas within the Virginia boundary.
   va_bnd = r'D:\git\ConsVision_DevVulnModel\ArcGIS\dev_vuln.gdb\VirginiaCounty_Dissolve'
   out_dir = r'D:\git\ConsVision_DevVulnModel\inputs\masks'
   years = ['2006', '2019']
   years = ['2021']  # for updates
   # Water mask (used for setting water to NoData in adjusted model rasters)
   for y in years:
      out_rast = out_dir + os.sep + 'water_mask_' + y + '.tif'
      print(out_rast)
      with arcpy.EnvManager(mask=va_bnd):
         arcpy.sa.SetNull(lc_gdb + os.sep + 'lc_' + y, 1, 'Value = 11').save(out_rast)
   # Development masks (used for setting already-developed to 101 in adjusted model rasters)
   for y in years:
      out_rast = out_dir + os.sep + 'dev_mask_' + y + '.tif'
      print(out_rast)
      with arcpy.EnvManager(mask=va_bnd):
         arcpy.sa.SetNull(imp_gdb + os.sep + 'imperv_' + y, 1, 'Value > 0').save(out_rast)

   # clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses('tmp_*') + arcpy.ListRasters('tmp_*'))


if __name__ == '__main__':
   main()




