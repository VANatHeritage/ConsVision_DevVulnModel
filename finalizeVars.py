'''
finalizeVars.py
Version: ArcGIS Pro
Creation Date: 2021-09-07
Creator: David Bucklin

This script finalizes all variables for the Development Vulnerability Model. This includes:
- Clip/Mask to study area
- If not already integer: multiply and convert to integer
- Output to TIF file

Reads from an Excel File in the 'input/vars' folder.
'''

import arcpy
import numpy as np
import pandas
from Helper import *


def finalizeVar(in_rast, out_rast, mask, mult=100):

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
      arcpy.sa.ExtractByMask(in_rast, mask).save(out_rast)
   print('Created raster ' + out_rast + '.')
   return out_rast


def main():

   # Load variable table
   vars_path = r'E:\git\ConsVision_DevVulnModel\inputs\vars\vars_MASTER.xlsx'
   vars = pandas.read_excel(vars_path, usecols=['varname', 'source_path', 'multi_temporal', 'multiplier', 'use'])
   # Years for multi-temporal variables (Only difference in paths between source rasters is the year).
   years = ['2006', '2016']

   # Run and overwrite if files already exist? If False, only new variables will be created.
   over = False

   # Mask and snap raster
   mask = r'E:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\VA_ModelMask'
   snap = r'E:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'

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
      out_rast = r'E:\git\ConsVision_DevVulnModel\inputs\vars' + os.sep + years[0] + os.sep + nm + '.tif'
      if not arcpy.Exists(out_rast) or over:
         finalizeVar(in_rast, out_rast, mask, mult)
      else:
         print('Skipping, `' + out_rast + '` already exists.')
      if vars['multi_temporal'][i] == 1:
         # only difference for 2016 raster paths is the year in the path name. Replace them in the path and rerun.
         in_rast = in_rast.replace(years[0], years[1])
         if not arcpy.Exists(in_rast):
            print('Missing multi-temporal raster ' + in_rast + '.')
            continue
         out_rast = r'E:\git\ConsVision_DevVulnModel\inputs\vars' + os.sep + years[1] + os.sep + nm + '.tif'
         if not arcpy.Exists(out_rast) or over:
            finalizeVar(in_rast, out_rast, mask, mult)
         else:
            print('Skipping, `' + out_rast + '` already exists.')
      else:
         # copy the variable to the 2016 folder ?
         # arcpy.Copy_management(out_rast, r'E:\git\ConsVision_DevVulnModel\inputs' + os.sep + years[1] + os.sep + nm + '.tif')
         print('Static variable.')


if __name__ == '__main__':
   main()
