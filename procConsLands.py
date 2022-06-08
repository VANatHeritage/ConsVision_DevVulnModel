"""
procConsLands.py
Version:  ArcGIS 10.3 / Python 2.7
Creation Date: 2019-06-19
Last Edit: 2019-11-07
Creators:  Kirsten R. Hazler / David Bucklin
Notes: Borrowed from ProcConsLands.py from ConSiteTools repo

Summary: Processing for conservation lands data for the Development Vulnerability model. Includes creating flattened
feature class and raster versions of conservation lands, based on BMI and LPS attributes, and creation of a protection
multiplier raster.
It also includes development of a euclidean distance to conservation lands predictor variable, which includes protected
lands outside of VA as well.
"""
from Helper import *


def polyFlatten(inPolys, outPolys, field, values=None, scratchGDB=None):
   """Eliminates overlaps in a polygon feature class based on values in a field.
   Field values provided to `values` are used in the order provided, with later values in the list having preference.
   If `values` is not provided, all values in the column are used, and sorted in decreasing order.

   Parameters:
   - inPolys: Input polygon feature class.
   - outPolys: Output feature class with "flattened" values
   - field: Name of field used for flattening
   - values: Optional list of values in `field`, sorted in preferred order (later values have preference)
   - scratchGDB: Optional. Geodatabase for storing scratch products
   """

   if not scratchGDB:
      scratchGDB = arcpy.env.scratchGDB

   if values is None:
      values = unique_values(inPolys, field)
      values = [str(v) for v in values]
      values.sort(reverse=True)
      printMsg('Using all values, sorted in decreasing order.')
   else:
      printMsg('Using defined sort order from `values`.')

   for val in values:
      # Make a subset feature layer
      lyr = "value%s" % val
      where_clause = field + " = '%s'" % val
      printMsg('Making feature layer...')
      arcpy.MakeFeatureLayer_management(inPolys, lyr, where_clause)

      # Dissolve
      dissFeats = scratchGDB + os.sep + "valueDiss" + str(values.index(val))
      printMsg('Dissolving...')
      arcpy.Dissolve_management(lyr, dissFeats, field, "", "SINGLE_PART")

      # Update
      if values.index(val) == 0:
         printMsg('Setting initial features to be updated...')
         inFeats = dissFeats
      else:
         printMsg('Updating with value %s...' % val)
         printMsg('input features: %s' % inFeats)
         printMsg('update features: %s' % dissFeats)
         if values.index(val) == len(values)-1:
            updatedFeats = outPolys
         else:
            updatedFeats = scratchGDB + os.sep + "upd_value%s" % str(values.index(val))
         arcpy.Update_analysis(inFeats, dissFeats, updatedFeats)
         inFeats = updatedFeats
   return outPolys


def protMult(bmi, lps, outRast, nlcd=None):
   """
   :param bmi: BMI raster
   :param lps: LPS raster
   :param outRast: Output protection multiplier raster
   :param nlcd: NLCD dataset. If given, areas of open water will be set to 0 in the protection multiplier
   :return: outRast
   """
   print('Making protection multiplier raster...')
   if nlcd:
      arcpy.sa.Con(nlcd, 0, 1, 'Value = 11').save('tmp_water')
      water = arcpy.sa.Raster('tmp_water')
      (water * (0.5 * ((arcpy.sa.Raster(bmi) - 1) / 5 + (arcpy.sa.Raster(lps) - 1) / 4))).save('tmp_mult')
   else:
      (0.5 * ((arcpy.sa.Raster(bmi) - 1) / 5 + (arcpy.sa.Raster(lps) - 1) / 4)).save('tmp_mult')
   print('Multiplying by 100 and converting to integer...')
   arcpy.sa.Int(arcpy.sa.Raster('tmp_mult') * 100 + 0.5).save(outRast)

   return outRast


def protMultBMI(bmi, outRast, nlcd=None):
   """
   :param bmi: BMI raster
   :param outRast: Output protection multiplier raster
   :param nlcd: If given, areas of open water will be set to 0 in the protection multiplier
   :return: outRast
   """
   print('Making protection multiplier raster...')
   if nlcd:
      arcpy.sa.Con(nlcd, 0, 1, 'Value = 11').save('tmp_water')
      water = arcpy.sa.Raster('tmp_water')
      (water * ((arcpy.sa.Raster(bmi) - 1) / 5)).save('tmp_mult')
   else:
      ((arcpy.sa.Raster(bmi) - 1) / 5).save('tmp_mult')
   print('Multiplying by 100 and converting to integer...')
   arcpy.sa.Int(arcpy.sa.Raster('tmp_mult') * 100 + 0.5).save(outRast)

   return outRast


def main():

   # set environments
   snap = r'F:\David\projects\vulnerability_model\SnapRaster_albers_wgs84.tif\SnapRaster_albers_wgs84.tif'
   msk = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\VA_ModelMask'

   arcpy.env.workspace = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb'
   arcpy.env.mask = msk
   arcpy.env.extent = msk
   arcpy.env.snapRaster = snap
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.cellSize = snap
   arcpy.env.overwriteOutput = True

   # Output gdb
   out_dir = r'F:\David\projects\vulnerability_model\vars\non_nlcd_based\conslands'
   out_gdb = out_dir + os.sep + 'conslands.gdb'
   make_gdb(out_gdb)
   arcpy.env.workspace = out_gdb

   # PAD and extended boundary for selecting out of state PAs
   pad = r'F:\David\GIS_data\PAD\PAD_US2_1_GDB\PAD_US2_1.gdb\PADUS2_1Fee'
   bnd = r'F:\David\GIS_data\snap_template_data\VA_Buff50mi.shp'

   # Current conservation lands
   conslands_current = r'D:\biotics\bioticsdata_Sept2021.gdb\managed_areas'

   ## Process Conservation Lands for protection multiplier
   for year in ['2006', 'current']:

      # Load and subset conservation lands
      if year != 'current':
         inPolys0 = os.path.join(out_dir, 'conslands' + year + '.shp')
      else:
         inPolys0 = conslands_current
      inPolys = arcpy.MakeFeatureLayer_management(inPolys0, where_clause="BMI <> 'U'")  # U is excluded; rec'd by Dave Boyd

      # LPS
      outPolys = 'conslands_lps_' + year + '_feat'
      outRast = 'conslands_lps_' + year
      polyFlatten(inPolys, outPolys, "LPS", values=["4", "3", "2", "1"])
      arcpy.AddField_management(outPolys, "lpsint", "SHORT")
      arcpy.CalculateField_management(outPolys, "lpsint", "!LPS!", "PYTHON")
      arcpy.PolygonToRaster_conversion(outPolys, 'lpsint', 'lpsrast')
      arcpy.sa.Con(arcpy.sa.IsNull('lpsrast'), 5, 'lpsrast').save(outRast)  # LPS values are between 1-4
      # BMI
      outPolys = 'conslands_bmi_' + year + '_feat'
      outRast = 'conslands_bmi_' + year
      polyFlatten(inPolys, outPolys, "BMI", values=["5", "4", "3", "2", "1"])
      arcpy.AddField_management(outPolys, "bmiint", "SHORT")
      arcpy.CalculateField_management(outPolys, "bmiint", "!BMI!", "PYTHON")
      arcpy.PolygonToRaster_conversion(outPolys, 'bmiint', 'bmirast')
      arcpy.sa.Con(arcpy.sa.IsNull('bmirast'), 6, 'bmirast').save(outRast)  # BMI values are between 1-5

      # Protection multiplier
      # 1: Protection multiplier, based on LPS and BMI); this was tried as a predictor variable, but ultimately
      # only was used as an input for the sampling mask.
      outRast = r'D:\git\ConsVision_DevVulnModel\inputs\masks\conslands_pmult_' + year + '.tif'
      protMult('conslands_bmi_' + year, 'conslands_lps_' + year, outRast)

      # 2. BMI-only multiplier (based on BMI only). This was used to adjust raw model values.
      outRast = r'D:\git\ConsVision_DevVulnModel\inputs\masks\conslands_pmultBMI_' + year + '.tif'
      protMultBMI('conslands_bmi_' + year, outRast)


   ## Create a distance to protected areas layer to use as a model variable.
   # PAD-US is added to VA data for non-VA Protected Lands
   for year in ['2006', '2019']:
      inPolys0 = os.path.join(out_dir, 'conslands' + year + '.shp')
      inPolys = arcpy.MakeFeatureLayer_management(inPolys0, where_clause="BMI <> 'U'")
      print(year)
      with arcpy.EnvManager(extent=snap, mask=snap):
         pad_query = "State_Nm <> 'VA' AND (Date_Est = ' ' OR CAST (Date_Est AS INT) <= " + year + ")"
         pad_lyr = arcpy.MakeFeatureLayer_management(pad, where_clause=pad_query)
         arcpy.SelectLayerByLocation_management(pad_lyr, 'INTERSECT', bnd)
         arcpy.Merge_management([pad_lyr, inPolys], 'conslands_wPAD_' + year)
         arcpy.sa.EucDistance('conslands_wPAD_' + year).save('conslands_edist_' + year)

   # clean up
   arcpy.Delete_management(arcpy.ListFeatureClasses('tmp_*') + arcpy.ListRasters('tmp_*'))


if __name__ == '__main__':
   main()
