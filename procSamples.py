# ---------------------------------------------------------------------------
# procSamples.py
# Version: ArcGIS Pro
# Creation Date: 2019-11-12
# Last Edit: 2019-11-14
# Creator: David Bucklin
#
# Summary: Using a list of exclusion rasters and criteria for their exclusion values,
# creates a sampling mask (Value of 1 = sampling region) and sample points for the Development Vulnerability model.
# ---------------------------------------------------------------------------

# Import modules and functions
import arcpy.sa

from Helper import *


def makeSampMask(exclList, outRast):

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


def makeSampPts(devChg, sampMask, outPts, sampsPerClass=10000, sampType="random", probRaster=None):

   # sbp = Spatially balanced
   # random = Random stratified
   # TODO: probRaster with sbp?

   if sampType == 'random':
      with arcpy.EnvManager(mask=sampMask):
         print('Masking development change raster...')
         arcpy.sa.SetNull(devChg, devChg, "VALUE NOT IN (0, 1)").save('tmp_samps_mask')
      print('Generating ' + str(sampsPerClass) + ' random samples per class...')
      arcpy.sa.CreateAccuracyAssessmentPoints('tmp_samps_mask', outPts, "CLASSIFIED",
                                              sampsPerClass * 2, "EQUALIZED_STRATIFIED_RANDOM")
      arcpy.CalculateField_management(outPts, 'class', '!Classified!', field_type="SHORT")
   elif sampType == "sbp":
      # Note: with SPB, raster mask is a probability raster. To have equal probability of selection throughout mask, set to constant value = 1
      with arcpy.EnvManager(mask=sampMask):
         print('Masking devChg...')
         arcpy.sa.SetNull(devChg, 1, "VALUE <> 0").save('tmp_samps_mask0')
         arcpy.sa.SetNull(devChg, 1, "VALUE <> 1").save('tmp_samps_mask1')
      print('Generating ' + str(sampsPerClass) + ' spatially balanced samples per class...')
      arcpy.CreateSpatiallyBalancedPoints_ga("tmp_samps_mask0", sampsPerClass, "tmp_sbp0")
      arcpy.CalculateField_management("tmp_sbp0", 'class', '0', field_type="SHORT")
      arcpy.CreateSpatiallyBalancedPoints_ga("tmp_samps_mask1", sampsPerClass, "tmp_sbp1")
      arcpy.CalculateField_management("tmp_sbp1", 'class', '1', field_type="SHORT")
      arcpy.Merge_management(['tmp_sbp0', 'tmp_sbp1'], outPts)
   return outPts


def main():

   # set environments
   msk = r'E:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\jurisbnd_lam_clipbound'
   ext = r'E:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\VA_ModelMask'
   snap = r'E:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'
   arcpy.env.mask = msk
   arcpy.env.extent = ext
   arcpy.env.snapRaster = snap
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.cellSize = snap
   arcpy.env.overwriteOutput = True
   gdb = 'E:/git/ConsVision_DevVulnModel/inputs/samples/samples.gdb'
   make_gdb(gdb)
   arcpy.env.workspace = gdb

   # Data year
   years = ['2006', '2016']
   for year in years:
      # list of raster + clauses combinations, indicating which pixels should be EXCLUDED from the sampling mask (no points generated there)
      exclList = [['E:/git/ConsVision_DevVulnModel/ArcGIS/vulnmod.gdb/bmi1lps1_' + year, 'Value = 2'],
                  ['E:/git/ConsVision_DevVulnModel/inputs/vars/' + year + '/roadDist.tif', 'Value > 2000'],
                  ['L:/David/GIS_data/NLCD/nlcd_2019/nlcd_2019ed_LandCover_albers.gdb/lc_' + year, 'Value = 11'],
                  ['E:/git/ConsVision_DevVulnModel/inputs/vars/2006/slpx100.tif', 'Value > 7000'],
                  ['L:/David/GIS_data/NLCD/nlcd_2019/nlcd_2019ed_Impervious_albers.gdb/imperv_' + year, 'Value > 0']]
      sampMask = 'sampMask_' + year
      makeSampMask(exclList, sampMask)

   # Make sample points
   devChg = r'L:\David\projects\vulnerability_model\vars\nlcd_based\nlcdv19_variables.gdb\DevChg_min01_06_16'
   sampMask = 'sampMask_2006'
   sampType = 'sbp'  # sbp | random
   outPts = 'samps_' + sampType + '_06'
   makeSampPts(devChg, sampMask, outPts, 10000, sampType)

   # clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses('tmp_*') + arcpy.ListRasters('tmp_*'))

if __name__ == '__main__':
   main()




