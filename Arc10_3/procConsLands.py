# ---------------------------------------------------------------------------
# ProcConsLands.py
# Version:  ArcGIS 10.3 / Python 2.7
# Creation Date: 2019-06-19
# Last Edit: 2019-11-07
# Creators:  Kirsten R. Hazler
# Notes: Borrowed from ProcConsLands.py from ConSiteTools repo
#
# Summary: Creates flattened feature class and raster versions of
# conservation lands, based on BMI and LPS attributes.
# ---------------------------------------------------------------------------

# Import modules and functions
import Helper
from Helper import *
arcpy.env.overwriteOutput = True

def polyFlatten(inPolys, outPolys, field, values=None, scratchGDB=None):
   '''Eliminates overlaps in a polygon feature class based on values in a field.
   Field values provided to `values` are used in the order provided, with later values in the list having preference.
   If `values` is not provided, all values in the column are used, and sorted in decreasing order.

   Parameters:
   - inPolys: Input polygon feature class.
   - outPolys: Output feature class with "flattened" values
   - field: Name of field used for flattening
   - values: Optional list of values in `field`, sorted in preferred order (later values have preference)
   - scratchGDB: Optional. Geodatabase for storing scratch products
   '''

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
      dissFeats = scratchGDB + os.sep + "valueDiss" + val
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
            updatedFeats = scratchGDB + os.sep + "upd_value%s" % val
         arcpy.Update_analysis(inFeats, dissFeats, updatedFeats)
         inFeats = updatedFeats
   return outPolys

########################################################################################

# set environments
snap = r'L:\David\projects\vulnerability_model\SnapRaster_albers_wgs84.tif\SnapRaster_albers_wgs84.tif'
msk = r'L:\David\projects\vulnerability_model\vulnmod.gdb\VA_ModelMask'

arcpy.env.workspace = r'L:\David\projects\vulnerability_model\vulnmod.gdb'
arcpy.env.mask = msk
arcpy.env.extent = msk
arcpy.env.snapRaster = snap
arcpy.env.outputCoordinateSystem = snap
arcpy.env.cellSize = snap

# process Conservation Lands
for year in ['2006', '2016']:
   # load and subset conservation lands
   inPolys0 = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslands' + year + '.shp'
   inPolys = arcpy.MakeFeatureLayer_management(inPolys0, where_clause="BMI <> 'U'")  # U is excluded; rec'd by Dave Boyd

   # LPS
   outPolys = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsLPS_' + year + '.shp'
   outRast = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsLPS_' + year + '.tif'
   polyFlatten(inPolys, outPolys, "LPS", values=["4", "3", "2", "1"])
   arcpy.AddField_management(outPolys, "lpsint", "SHORT")
   arcpy.CalculateField_management(outPolys, "lpsint", "!LPS!", "PYTHON")
   arcpy.PolygonToRaster_conversion(outPolys, 'lpsint', 'lpsrast')
   arcpy.sa.Con(arcpy.sa.IsNull('lpsrast'), 5, 'lpsrast').save(outRast)  # LPS values are between 1-4

   # BMI
   outPolys = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsBMI_' + year + '.shp'
   outRast = 'L:/David/projects/vulnerability_model/conslands/' + year + '/conslandsBMI_' + year + '.tif'
   polyFlatten(inPolys, outPolys, "BMI", values=["5", "4", "3", "2", "1"])
   arcpy.AddField_management(outPolys, "bmiint", "SHORT")
   arcpy.CalculateField_management(outPolys, "bmiint", "!BMI!", "PYTHON")
   arcpy.PolygonToRaster_conversion(outPolys, 'bmiint', 'bmirast')
   arcpy.sa.Con(arcpy.sa.IsNull('bmirast'), 6, 'bmirast').save(outRast)  # BMI values are between 1-5