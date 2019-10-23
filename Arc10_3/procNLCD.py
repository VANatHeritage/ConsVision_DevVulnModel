# ----------------------------------------------------------------------------------------
# procNLCD.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-09-05
# Last Edit: 2019-09-06
# Creator:  Kirsten R. Hazler

# Summary:
# A library of functions for processing National Land Cover Database data 
# ----------------------------------------------------------------------------------------

import Helper
from Helper import *

def MakeWeightKernel(out_File, nCells, gamma, scale = 100, rounding = 0, ysnInt = 1, centerVal = 0):
   '''Creates a weighted neighborhood kernel, in which the influence of cells in a circular neighborhood decays with (cell) distance. The output is a properly formatted text file that can be used in the ArcGIS Focal Statistics tool for the "Weight" neighborhood option. See: http://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/how-focal-statistics-works.htm.

   This function is based on the "Development Pressure" variable, defined by equation 2 in a paper by Meentemeyer et al., 2012 (https://www.tandfonline.com/doi/abs/10.1080/00045608.2012.707591. However, it can be broadly applied to any situation in which a weighted neighborhood kernel is needed.

   The weight of a neighboring cell is calculated as:
   w = scale/(distance^gamma)

   See also:
   https://grasswiki.osgeo.org/wiki/Workshop_on_urban_growth_modeling_with_FUTURES#Development_pressure
   https://grass.osgeo.org/grass76/manuals/addons/r.futures.devpressure.html

   Parameters:
   - out_File: The output file. Should end in .txt.
   - nCells: The radius, in number of cells, for the kernel neighborhood.
   - gamma: The exponent in the equation above
   - scale: The scaling parameter in the equation above
   - rounding: The number of decimal places to maintain in rounding
   - ysnInt: Indicator of whether the output should be integerized (1) or not (0)
   - centerVal: Indicator of whether focal cell influences the output (1) or not (0)
   '''
   # Set up array and do all the calculations
   diam = 2*nCells + 1
   maxDist = nCells + 0.5
   dims = (diam,diam)
   s = numpy.zeros(dims)
   s += scale
   (ycoords, xcoords) = numpy.where(s)
   ycoords.shape = dims
   xcoords.shape = dims
   midY = ycoords.max()/2
   midX = xcoords.max()/2
   d = numpy.sqrt((xcoords - midX)**2 + (ycoords - midY)**2)
   weight = numpy.where(d> maxDist, 0, numpy.where(d==0, centerVal*scale, s/d**gamma))
   normWt = scale*weight/numpy.sum(weight)
   if ysnInt == 1:
      normWt = numpy.around(normWt)
   else:
      normWt = numpy.around(normWt, rounding)

   # Write to output file
   outfile = open(out_File, 'w')
   first_line = str(dims[1]) + ' ' + str(dims[0])
   outfile.write(first_line)
   for row in weight:
      outfile.write('\n')
      for column in row:
         outfile.write(str(column) + '    ')
   outfile.close()

   return (s, d, weight, normWt)


def ImpGrowthSpots(t1, t2, out, label, cutoff=20, areamin=20000, keep_intermediate=False):
   """Generate Impervious area growth spots, based on two time periods from NLCD.
   Parameters:
   - t1: Impervious raster in time 1
   - t2: Impervious raster in time 2
   - out: The output geodatabase. Will be created if it doesn't exist.
   - label: A string, name applied to output rasters. Note that an automatic suffix based on cutoff and areamin
      parameters is appended to this)
   - cutoff: The minimum (smoothed) difference in percent imperviousness values required for a cell to be classified as
      a potential hotspot
   - areamin = The minimum area, in square map units (typically meters), required for a contiguous cluster of potential
      hotspot cells to be considered a hotspot.
   - keep_intermediate: Whether intermediate rasters should be saved (True), or deleted (False)
   """
   # Make GDB and set environments
   make_gdb(out)
   arcpy.env.workspace = out
   arcpy.env.extent = t1
   arcpy.env.mask = t1
   arcpy.env.cellSize = t1
   arcpy.env.outputCoordinateSystem = t1
   arcpy.env.snapRaster = t1

   # set up naming scheme
   suf = '_' + str(cutoff) + '_' + '{:02d}'.format(int(round(areamin/10000)))
   nm = label + suf
   # Create difference raster
   print('Generating hotspots raster `' + nm + '`...')

   # Difference
   arcpy.sa.Minus(t2, t1).save('Diff_' + nm)

   # Filter, reclassify, and group cells
   arcpy.sa.Filter('Diff_' + nm, 'LOW', 'DATA').save('FDiff_' + nm)
   mx = arcpy.GetRasterProperties_management('Diff_' + nm, 'MAXIMUM')
   if int(mx[0]) < cutoff:
      print('No output: no areas are above the cutoff threshold. Consider using a lower `cutoff` value.')
      return
   arcpy.sa.Con('FDiff_' + nm, 1, None, 'Value >= ' + str(cutoff)).save('Pot_' + nm)
   arcpy.sa.RegionGroup('Pot_' + nm, 'EIGHT', 'WITHIN').save('Regions_' + nm)

   # Calculate areas of regions, remove those smaller than threshold
   arcpy.sa.ZonalGeometry('Regions_' + nm, 'VALUE', 'AREA').save('Area_' + nm)
   arcpy.sa.Con('Area_' + nm, 1, None, 'Value >= ' + str(areamin)).save(nm)
   arcpy.BuildPyramids_management(nm)

   # delete or build pyramids for intermediate
   ls = ['Diff_', 'FDiff_', 'Pot_', 'Regions_', 'Area_']
   ls = [s + nm for s in ls]
   for r in ls:
      if not keep_intermediate:
         try:
            arcpy.Delete_management(r)
         except:
            continue
      else:
         arcpy.BuildPyramids_management(r)

   out = arcpy.Raster(nm)
   return(out)