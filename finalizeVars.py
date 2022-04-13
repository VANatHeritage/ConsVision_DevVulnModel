"""
finalizeVars.py
Version: ArcGIS Pro
Creation Date: 2021-09-07
Creator: David Bucklin

This script finalizes all predictor variables for the Development Vulnerability Model. This includes:
- Clip/Mask to study area
- If not already integer: apply multiplier and convert to integer
- Output to TIF file

Reads from an Excel File in the 'input/vars' folder, which includes the columns:
['varname', 'source_path', 'static', 'multiplier', 'use']
"""
from Helper import *


def finalizeVar(in_rast, out_rast, mask, mult=100):
   """
   Finalize a raster predictor, clipping and masking to the provide mask, applying a multiplier and
   converting to integer.
   :param in_rast: input raster
   :param out_rast: output raster
   :param mask: data mask
   :param mult: Multiplier to apply to dataset.
   :return: out_rast
   """

   r = arcpy.sa.Raster(in_rast)
   print('Finalizing raster ' + in_rast + '...')
   if not r.isInteger:
      if mult == 1:
         print('Rounding values to integer...')
         arcpy.sa.Int(r + 0.5).save('tmp_rast')
      else:
         print('Multiplying and rounding values to integer...')
         arcpy.sa.Int(r * int(mult) + 0.5).save('tmp_rast')
      arcpy.sa.ExtractByMask('tmp_rast', mask).save(out_rast)
   else:
      if mult == 1:
         arcpy.sa.ExtractByMask(in_rast, mask).save(out_rast)
      else:
         print('Multiplying values...')
         arcpy.sa.Int(r * int(mult)).save('tmp_rast')
         arcpy.sa.ExtractByMask('tmp_rast', mask).save(out_rast)
   print('Created raster ' + out_rast + '.')
   return out_rast


def main():

   # Load variable table
   vars_path = r'D:\git\ConsVision_DevVulnModel\inputs\vars\vars_DV.xlsx'
   vars = pandas.read_excel(vars_path, usecols=['varname', 'source_path', 'static', 'multiplier', 'use'])

   # Years for predictor variables. In the excel file, the path uses the first year (2006). The only difference in
   # paths between source rasters is the year, so a replace is used to get the path of the second year raster (2019).
   years = ['2006', '2019']

   # Run and overwrite if files already exist? If False, only new variables will be created.
   over = False

   # Mask and snap raster
   mask = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\VA_ModelMask'
   snap = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'

   # Output folder (sub-folders for each processing year should be here)
   out_folder = r'D:\git\ConsVision_DevVulnModel\inputs\vars'

   # Set environments
   arcpy.env.overwriteOutput = True
   arcpy.env.snapRaster = snap
   arcpy.env.cellSize = snap
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.workspace = arcpy.env.scratchGDB
   arcpy.env.extent = mask

   # Loop over table, skipping those marked use = 0.
   for i in list(range(0, len(vars))):
      in_rast = vars['source_path'][i]
      if vars['use'][i] == 0:
         print('Skipping raster `' + in_rast + '`.')
         continue
      nm = vars['varname'][i]
      mult = vars['multiplier'][i]
      out_rast = out_folder + os.sep + years[0] + os.sep + nm + '.tif'
      if not arcpy.Exists(out_rast) or over:
         finalizeVar(in_rast, out_rast, mask, mult)
      else:
         print('Skipping, `' + out_rast + '` already exists.')
      if vars['static'][i] != 1:
         # only difference for year[1] raster paths is the year in the path name. Replace them in the path and rerun.
         in_rast = in_rast.replace(years[0], years[1])
         if not arcpy.Exists(in_rast):
            print('Missing multi-temporal raster ' + in_rast + '.')
            continue
         out_rast = out_folder + os.sep + years[1] + os.sep + nm + '.tif'
         if not arcpy.Exists(out_rast) or over:
            finalizeVar(in_rast, out_rast, mask, mult)
         else:
            print('Skipping, `' + out_rast + '` already exists.')
      else:
         # static variable (only one time period)
         print('Static variable.')


if __name__ == '__main__':
   main()
