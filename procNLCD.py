"""
procNLCD.py
Version:  ArcGIS Pro
Creation Date: 2019-09-05
Last Edit: 2020-01-09
Creator:  Kirsten R. Hazler / David Bucklin

Summary:
A library of functions for processing National Land Cover Database data

Usage Notes:
'year' is a standard variable that functions as a suffix for the file(s) to create. Use the full year (e.g. 2006)
here for single-year variables, and for multi-year variables, use the last 2 digits of the two years separated by '_'
(e.g. 06_16 for 2006/2016).
"""
from Helper import *


def MakeWeightKernel(out_File, nCells, gamma, scale=100, rounding=3, ysnInt=0, centerVal=0, annDist=10):
   '''Creates a weighted neighborhood kernel, in which the influence of cells in a circular neighborhood decays with
   (cell) distance. The output is a properly formatted text file that can be used in the ArcGIS Focal Statistics tool
   for the "Weight" neighborhood option.
   See: http://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/how-focal-statistics-works.htm.

   This function is based on the "Development Pressure" variable, defined by equation 2 in a paper by Meentemeyer et
   al., 2012 (https://www.tandfonline.com/doi/abs/10.1080/00045608.2012.707591. However, it can be broadly applied to
   any situation in which a weighted neighborhood kernel is needed.

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
   - annDist: The inner radius of the annulus neighborhood. Cells within this radius are set to the centerVal.
      Cells at the edge of this radius get the maximum weight, and weight decays outwards from there.
   '''
   # Set up array and do all the calculations
   diam = 2 * nCells + 1
   maxDist = nCells + 0.5
   dims = (diam, diam)
   s = numpy.zeros(dims)
   s += scale
   (ycoords, xcoords) = numpy.where(s)
   ycoords.shape = dims
   xcoords.shape = dims
   midY = ycoords.max() / 2
   midX = xcoords.max() / 2
   d = numpy.sqrt((xcoords - midX) ** 2 + (ycoords - midY) ** 2)
   weight = numpy.where(d > maxDist, 0, numpy.where(d <= annDist, centerVal * scale, s / (d - annDist) ** gamma))
   normWt = scale * weight / numpy.sum(weight)
   if ysnInt == 1:
      normWt = numpy.around(normWt)
   else:
      normWt = numpy.around(normWt, rounding)

   # Write to output file
   outfile = open(out_File, 'w')
   first_line = str(dims[1]) + ' ' + str(dims[0])
   outfile.write(first_line)
   for row in normWt:
      outfile.write('\n')
      for column in row:
         outfile.write(str(column) + '    ')
   outfile.close()

   return (s, d, weight, normWt)


def MakeKernelList(out_Dir):
   '''Creates a pre-defined list of parameter lists, to be input into the MultiWeightKernels function
   Parameters:
   - out_Dir: directory in which output text files will be saved.
   '''
   f1 = out_Dir + os.sep + 'wk30_025_3.txt'
   f2 = out_Dir + os.sep + 'wk30_050_3.txt'
   f3 = out_Dir + os.sep + 'wk30_100_3.txt'
   f4 = out_Dir + os.sep + 'wk10_025_1.txt'
   f5 = out_Dir + os.sep + 'wk10_050_1.txt'
   f6 = out_Dir + os.sep + 'wk10_100_1.txt'

   p1 = [f1, 30, 0.25, 100, 3, 0, 0, 3]
   p2 = [f2, 30, 0.50, 100, 3, 0, 0, 3]
   p3 = [f3, 30, 1.00, 100, 3, 0, 0, 3]
   p4 = [f4, 10, 0.25, 100, 3, 0, 0, 1]
   p5 = [f5, 10, 0.50, 100, 3, 0, 0, 1]
   p6 = [f6, 10, 1.00, 100, 3, 0, 0, 1]

   parmsList = [p1, p2, p3, p4, p5, p6]
   return parmsList


def MultiWeightKernels(parmsList):
   '''Creates multiple weighted neighborhood kernels using the MakeWeightKernel function, using a list of parameter sets.
   Parameters:
   - parmsList: A list of parameter lists. Each parameter list must contain the set of parameters in order required
      by the MakeWeightKernel function
   Returns a list with [NbrWeight object, Text file basename], which can be used for the 'neighborhoods' argument
      in the ImpFocal function.
   '''
   outList = []
   for p in parmsList:
      out_File = p[0]
      print(out_File)
      nCells = p[1]
      gamma = p[2]
      scale = p[3]
      rounding = p[4]
      ysnInt = p[5]
      centerVal = p[6]
      annDist = p[7]

      MakeWeightKernel(out_File, nCells, gamma, scale, rounding, ysnInt, centerVal, annDist)
      out = [arcpy.sa.NbrWeight(out_File), os.path.basename(out_File).replace('.txt', '')]
      outList.append(out)

   return outList


def ImpFocal(imperv, neighborhoods, year, stat="MEAN"):

   print('Setting value = 127 to NoData...')
   arcpy.sa.SetNull(imperv, imperv, 'Value = 127').save('tmp_imp')
   ls = []
   for n in neighborhoods:
      out = n[1] + '_imp_' + year
      print('Creating `' + out + '`...')
      arcpy.sa.FocalStatistics('tmp_imp', n[0], stat).save(out)
      ls.append(out)

   return ls


def LCFocal(lc, classes, neighborhoods, year, stat="MEAN"):

   q = ','.join([str(i) for i in classes[0]])
   print('Creating binary raster')
   arcpy.sa.Con(lc, 1, 0, 'Value IN (' + q + ')').save('tmp_lc')
   ls = []
   for n in neighborhoods:
      out = n[1] + '_' + classes[1] + '_' + year
      if arcpy.Exists(out):
         print('skipping, already exists')
         continue
      print('Creating `' + out + '`...')
      arcpy.sa.FocalStatistics('tmp_lc', n[0], stat).save(out)
      ls.append(out)
   return ls


def NewRoadDist(t1, t2, year, keep_intermediate=False):
   """Generate Impervious area growth spots, based on two time periods from NLCD.
   Parameters:
   - t1: Impervious descriptor raster in time 1
   - t2: Impervious descriptor raster in time 2
   - year: Year suffix added to output dataset
   - keep_intermediate: Whether intermediate rasters should be saved (True), or deleted (False)
   - edist: Whether to run Euclidean distance on the hotspots output. (file will have '_edist' suffix)
   """

   # set up naming scheme
   nm = 'newRoad'

   # Create difference raster
   print('Generating binary road rasters...')
   arcpy.sa.Con(t1, 1, 0, 'Value IN (20, 21, 22, 23)').save('T1')
   arcpy.sa.Con(t2, 1, 0, 'Value IN (20, 21, 22, 23)').save('T2')
   print('Generating new road raster `' + nm + '`...')
   arcpy.sa.Minus('T2', 'T1').save('tmp_minus')
   arcpy.sa.SetNull('tmp_minus', 1, 'Value <> 1').save(nm + '_' + year)

   print('Calculating euclidean distance...')
   arcpy.sa.EucDistance(nm + '_' + year).save('tmp_ed')
   arcpy.sa.Int(arcpy.sa.Raster('tmp_ed') + 0.5).save(nm + '_edist_' + year)
   arcpy.BuildPyramids_management(nm + '_edist_' + year)

   # clean up
   arcpy.Delete_management(['tmp_minus', 'tmp_ed'])
   # delete intermediate
   if not keep_intermediate:
      arcpy.Delete_management(['T1', 'T2'])

   return nm


def ImpGrowthSpots(t1, t2, year, cutoff=20, areamin=20000, keep_intermediate=False, edist=False):
   """Generate Impervious area growth spots, based on two time periods from NLCD.
   Parameters:
   - t1: Impervious raster in time 1
   - t2: Impervious raster in time 2
   - cutoff: The minimum (smoothed) difference in percent imperviousness values required for a cell to be classified as
      a potential hotspot
   - areamin = The minimum area, in square map units (typically meters), required for a contiguous cluster of potential
      hotspot cells to be considered a hotspot.
   - keep_intermediate: Whether intermediate rasters should be saved (True), or deleted (False)
   - edist: Whether to run Euclidean distance on the hotspots output. (file will have '_edist' suffix)
   """

   # set up naming scheme
   label = 'imphot_' + str(cutoff) + '_' + '{:02d}'.format(int(round(areamin / 10000)))
   nm = label + '_' + year
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

   print('Calculating areas of regions, removing those smaller than threshold...')
   arcpy.sa.ZonalGeometry('Regions_' + nm, 'VALUE', 'AREA').save('Area_' + nm)
   arcpy.sa.Con('Area_' + nm, 1, None, 'Value >= ' + str(areamin)).save(nm)
   arcpy.BuildPyramids_management(nm)

   if edist:
      print('Calculating euclidean distance...')
      arcpy.sa.EucDistance(nm).save('tmp_ed')
      arcpy.sa.Int(arcpy.sa.Raster('tmp_ed') + 0.5).save(label + '_edist_' + year)
      arcpy.BuildPyramids_management(label + '_edist_' + year)
      arcpy.Delete_management('tmp_ed')

   # delete intermediate
   if not keep_intermediate:
      ls = ['Diff_', 'FDiff_', 'Pot_', 'Regions_', 'Area_']
      ls = [s + nm for s in ls]
      arcpy.Delete_management(ls)

   return nm


def EucDistNLCD(nlcd, classes, year, maxDist=None):
   """Generate euclidean distance rasters for one or more class combinations from NLCD. Distance is rounded to integer.
   Parameters:
   - nlcd: NLCD classified land cover raster
   - classes: List of lists: Each sub-list indicates the NLCD classes on which to run
      Euclidean Distance analyses (e.g. `classes = [[11], [41,42,43], [90,95]]`)
   - maxDist: maximum distance for Euclidean Distance (map units)
   """

   ls = []
   for cl in classes:
      q = ','.join([str(l) for l in cl[0]])
      suf = cl[1]

      nm = 'edist_' + suf + '_' + year
      print('Working on raster `' + nm + '`...')

      # process raster
      query = "Value NOT IN  (" + q + ")"
      arcpy.sa.SetNull(nlcd, nlcd, query).save('sn')
      arcpy.sa.EucDistance('sn', maxDist).save('ed')
      arcpy.sa.Int(arcpy.sa.Raster('ed') + 0.5).save(nm)
      ls.append(nm)
      arcpy.BuildPyramids_management(nm)

   arcpy.Delete_management(['sn', 'ed'])
   return ls


def CostNLCD(nlcd, year):

   out = 'lc_cost_'
   print('Making land cover cost raster `' + out + '`.')

   # Assign costs to remap value
   rcl = arcpy.sa.RemapValue([[11, 5], [21, 0], [22, 0], [23, 0], [24, 0], [31, 1], [41, 4], [42, 4], [43, 4],
                              [52, 3], [71, 2], [81, 2], [82, 2], [90, 4], [95, 2]])
   arcpy.sa.Reclassify(nlcd, 'Value', rcl, "NODATA").save(out + year)
   print('Calculating focal statistic in 3-cell circle...')
   arcpy.sa.FocalStatistics(out, NbrCircle(3, "CELL"), "MEAN").save(out + '3cell_' + year)
   return out


def main():

   # HEADER

   # Input geodatabases
   nlcd_gdb = r'F:\David\GIS_data\NLCD\nlcd_2019\nlcd_2019ed_LandCover_albers.gdb'
   imp_gdb = r'F:\David\GIS_data\NLCD\nlcd_2019\nlcd_2019ed_Impervious_albers.gdb'

   # Outputs
   out_folder = r'F:\David\projects\vulnerability_model\vars\nlcd_based'
   out_gdb = out_folder + os.sep + 'nlcdv19_variables.gdb'
   make_gdb(out_gdb)

   # Set environments
   templ = nlcd_gdb + os.sep + 'lc_2019'
   arcpy.env.workspace = out_gdb
   arcpy.env.extent = templ
   arcpy.env.mask = templ
   arcpy.env.cellSize = templ
   arcpy.env.outputCoordinateSystem = templ
   arcpy.env.snapRaster = templ

   # Target NLCD year(s)
   years = ['2006', '2019']

   # END HEADER

   # Impervious in neighborhood
   # coulddo: implement alternative kernels?
   kl = MakeKernelList(out_folder + os.sep + 'kernels')
   ngh = MultiWeightKernels(kl)

   for y in years:
      imp = imp_gdb + os.sep + 'imperv_' + y
      # Note that large-radius kernels can take a very long time to process.
      ImpFocal(imp, ngh, y)

   # Standard kernels
   # Did not use Annulus:
      # [NbrAnnulus(1, 10), 'imp_ann1_10'], [NbrAnnulus(10, 20), 'imp_ann10_20'], [NbrAnnulus(20, 30), 'imp_ann20_30'],
      # [NbrAnnulus(30, 40), 'imp_ann30_40'], [NbrAnnulus(40, 50), 'imp_ann40_50']
   neighborhoods = [[NbrIrregular(r'F:\David\projects\vulnerability_model\vars\nlcd_based\kernels\krect_3x3.txt'), 'kRect3']]
   for y in years:
      imp = imp_gdb + os.sep + 'imperv_' + y
      ImpFocal(imp, neighborhoods, y)

   # Focal land cover
   kl = MakeKernelList(out_folder + os.sep + 'kernels')
   ngh = MultiWeightKernels(kl)
   ind = [1, 4]  # only want the 0.5-gamma kernels
   ngh = [ngh[i] for i in ind]  # subset
   classes = [[['90', '95'], 'wetland'], [['11'], 'openwater']]
   for y in years:
      nlcd = nlcd_gdb + os.sep + 'lc_' + y
      for cl in classes:
         LCFocal(nlcd, cl, ngh, y, 'MEAN')

   # Euclidean distance to NLCD classes
   for y in years:
      nlcd = nlcd_gdb + os.sep + 'lc_' + y
      classes = [[[11], 'openwater'], [[90, 95], 'wetland']]  # [[41, 42, 43], 'forest']]
      EucDistNLCD(nlcd, classes, y)



   # Land cover cost
   for y in years:
      nlcd = nlcd_gdb + os.sep + 'lc_' + y
      CostNLCD(nlcd, y)


   ### Multiple-year (change) variables

   # Impervious hot spots
   tps = [[imp_gdb + os.sep + 'imperv_2001', imp_gdb + os.sep + 'imperv_2006'],
          [imp_gdb + os.sep + 'imperv_2013', imp_gdb + os.sep + 'imperv_2019']]
   for tp in tps:
      t1 = tp[0]
      t2 = tp[1]
      y = t2[-4:]  # naming scheme (uses last year of sequence)
      reps = [[20, 20000], [20, 50000], [20, 100000]]
      for i in reps:
         ImpGrowthSpots(t1, t2, y, i[0], i[1], edist=True)

   # New road euclidean distance
   tps = [[imp_gdb + os.sep + 'impDescriptor_2001', imp_gdb + os.sep + 'impDescriptor_2006'],
          [imp_gdb + os.sep + 'impDescriptor_2013', imp_gdb + os.sep + 'impDescriptor_2019']]
   for tp in tps:
      t1 = tp[0]
      t2 = tp[1]
      y = t2[-4:]  # naming scheme (uses last year of sequence)
      NewRoadDist(t1, t2, y)


if __name__ == '__main__':
   main()
