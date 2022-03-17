"""
procCensus.py
Version:  ArcGIS 10.3.1 / Python 2.7.8 OR ArcPro / Python 3.x
Creation Date: 2019-10-11
Last Edit: 2019-10-24
Creator:  Kirsten R. Hazler

Summary:
A library of functions for processing U.S. Census data
FUNCTION NOTE: It is a little tricky to make a general function to process data from all years, since field names and
formats differ. Therefore, certain lines of code are contingent on the year specified. Whenever new data is downloaded,
some of the code may need adjusting.

DATA NOTE:  To cover the 50-mile processing buffer around Virginia, download data for the following states:
DE, DC, KY, MD, NC, PA, TN, VA, WV

TODO: Do these impervious surface rasters have any NoData cells (e.g. for water?)
TODO: Linear blocks around roads are not meeting shape index criteria in many cases for 2010. This results in
 exclusion of blocks from cores, since it breaks up contiguous blocks, and if contiguous blocks are not 1 sq mile,
 they can get excluded in fillCores, even if across a highway from a large core section. (This could be altered by
 adjusting fillCores to not exclude these polygons; they could be dropped after the grouping step instead.)
 Many of these 'road' blocks/areas are included in the 2000 cores; not sure why. It seems that block shapes are not
 consistent between years, which is the main issue. Despite this, there are about 30 more cores and 500 sq miles in
 2010 vs 2000 using original method, so maybe this isn't a big issue.
"""
from Helper import *


def PrepBlocks(in_Blocks, in_PopTab, in_Imperv, in_Year):  # in_Imperv20, out_Tracts):
   '''Prepares Block-level and Tract-level data from the Census for the MakeUrbanCores function. Assumes GIS and
   tabular data for census blocks have been downloaded from https://www.nhgis.org/.
   
   GIS data for blocks is downloaded by state: one shapefile for each state. It is assumed that the individual
   shapefiles have already been merged into a single polygon feature class within a geodatabase.
   
   Tabular data are downloaded as a single CSV file covering all the states in the shapefiles, and should contain
   population counts for each block. It is assumed that the CSV file has been converted to a table within a
   geodatabase.

   The function will check if each new attribute already exists in the dataset, skipping calculation for those that
   already exist.
   
   Parameters:
   - in_Blocks: Input feature class representing Census blocks
   - in_PopTab: Input table containing population count for each block
   - in_Imperv: Input raster representing percent imperviousness
   - REMOVED (generated in-function): in_Imperv20: Input raster in which cells with 20% or greater imperviousness are set to 1, otherwise 0
   - REMOVED (not output): out_Tracts: Output feature class representing Census tracts
   - in_Year: The census year of the data
   '''

   # Existing field names in blocks feature class
   bnames = [f.name for f in arcpy.ListFields(in_Blocks)]

   # Change the relevant field name to POP, if not already done
   if len(arcpy.ListFields(in_PopTab, "POP")) < 1:
      printMsg('Renaming field to POP...')
      if in_Year == 2000:
         arcpy.AlterField_management(in_PopTab, 'FXS001', 'POP', 'POP')
      elif in_Year == 2010:
         # arcpy.AlterField_management (in_PopTab, 'H7V001', 'POP', 'POP')
         # DB Note: Had issues with the subsequent join, when using AlterField. Calculating new field instead
         arcpy.AddField_management(in_PopTab, 'POP', 'LONG')
         arcpy.CalculateField_management(in_PopTab, 'POP', '!H7V001!', 'PYTHON')
      else:
         printErr('Not a valid year.')

   # Join fields from the population table to the feature class
   fnames = [f.name for f in arcpy.ListFields(in_PopTab)]
   fnames.remove('GISJOIN')
   fnames.remove('OBJECTID')
   if 'POP' not in bnames:
      printMsg('Joining fields...')
      # arcpy.JoinField_management (in_Blocks, 'GISJOIN', in_PopTab, 'GISJOIN', fnames)
      arcpy.JoinField_management(in_Blocks, 'GISJOIN', in_PopTab, 'GISJOIN', 'POP')

   # Get a unique tract ID
   # printMsg('Creating and calculating TRACT_ID field...')
   # arcpy.AddField_management(in_Blocks, "TRACT_ID", "TEXT", "", "", 11)
   # if in_Year == 2000:
   #    expression = "!FIPSSTCO!+ !TRACT2000!"
   # elif in_Year == 2010:
   #    expression = "!STATEFP10!+ !COUNTYFP10! + !TRACTCE10!"
   # else:
   #    printErr('Not a valid year.')
   # arcpy.CalculateField_management(in_Blocks, "TRACT_ID", expression, "PYTHON_9.3")

   # Calculate the area in square miles, and change the output field name.
   if 'AREA_SQMI' not in bnames:
      printMsg('Calculating area...')
      arcpy.AddGeometryAttributes_management(in_Blocks, "AREA", "", "SQUARE_MILES_US")
      arcpy.AlterField_management(in_Blocks, 'POLY_AREA', 'AREA_SQMI', 'AREA_SQMI')

   # Calculate the population density in persons per square mile
   if 'DENS_PPSM' not in bnames:
      printMsg('Calculating population density...')
      arcpy.AddField_management(in_Blocks, "DENS_PPSM", "DOUBLE")
      expression = "!POP! / !AREA_SQMI!"
      arcpy.CalculateField_management(in_Blocks, "DENS_PPSM", expression, "PYTHON_9.3")

   # Calculate the shape index
   if 'SHP_IDX' not in bnames:
      printMsg('Calculating shape index...')
      arcpy.AddField_management(in_Blocks, "SHP_IDX", "DOUBLE")
      expression = "(4*math.pi* !Shape_Area!)/(!Shape_Length!**2)"
      arcpy.CalculateField_management(in_Blocks, "SHP_IDX", expression, "PYTHON_9.3")

   # Calculate the imperviousness
   if 'IMPERV_MEAN' not in bnames:
      printMsg('Calculating imperviousness...')
      zTab = in_Blocks + '_Imperv'
      ZonalStatisticsAsTable(in_Blocks, 'GISJOIN', in_Imperv, zTab, "DATA", "ALL")
      arcpy.JoinField_management(in_Blocks, 'GISJOIN', zTab, 'GISJOIN', ['MEAN', 'MEDIAN'])
      arcpy.AlterField_management(in_Blocks, 'MEAN', 'IMPERV_MEAN')
      arcpy.AlterField_management(in_Blocks, 'MEDIAN', 'IMPERV_MEDIAN')

   # Calculate the proportion of polygon covered by 20% or greater imperviousness
   if 'IMPERV20_MEAN' not in bnames:
      printMsg('Calculating proportion with 20% or greater imperviousness...')
      in_Imperv20 = 'tmp_imp20'
      with arcpy.EnvManager(extent=in_Blocks):
         arcpy.sa.SetNull(in_Imperv, 1, 'Value >= 20').save(in_Imperv20)
      zTab20 = in_Blocks + '_Imperv20'
      ZonalStatisticsAsTable(in_Blocks, 'GISJOIN', in_Imperv20, zTab20, "DATA", "MEAN")
      arcpy.JoinField_management(in_Blocks, 'GISJOIN', zTab20, 'GISJOIN', ['MEAN'])
      arcpy.AlterField_management(in_Blocks, 'MEAN', 'IMPERV20_MEAN')

   # # Dissolve blocks to get tracts. Aggregate to get sums of population and area.
   # # Keep multi-parts, because some tracts get split by water but should be counted as a single unit
   # printMsg('Dissolving blocks to create tracts...')
   # arcpy.Dissolve_management(in_Blocks, out_Tracts, "TRACT_ID", "POP SUM;AREA_SQMI SUM", "MULTI_PART")
   # arcpy.AlterField_management(out_Tracts, "SUM_POP", "POP")
   # arcpy.AlterField_management(out_Tracts, "SUM_AREA_SQMI", "AREA_SQMI")

   # # Calculate the population density in persons per square mile, for the tracts
   # printMsg('Calculating tract population density...')
   # arcpy.AddField_management(out_Tracts, "DENS_PPSM", "DOUBLE")
   # expression = "!POP! / !AREA_SQMI!"
   # arcpy.CalculateField_management(out_Tracts, "DENS_PPSM", expression, "PYTHON_9.3") 

   # printMsg('Finished prepping blocks and tracts.')
   # return (in_Blocks, out_Tracts)

   return in_Blocks


def MakeUrbanCores(in_Blocks, out_Cores):
   '''Creates urban cores from input census blocks. Methodology adapted loosely from Section 1 on page 53040 of the
   "Urban Area Criteria for the 2010 Census" (https://www.federalregister.gov/documents/2011/08/24/2011-21647/urban
   -area-criteria-for-the-2010-census).

   Parameters:
      - in_Blocks: Input feature class representing Census blocks; this should have been updated using the PrepBlocks function
      - out_Cores: Output feature class representing urban cores
   '''
   scratchGDB = arcpy.env.scratchGDB
   coreBlocks = scratchGDB + os.sep + 'coreBlocks'
   expandCores = scratchGDB + os.sep + 'expandCores'

   # Select census blocks with population density at least 1000 ppsm 
   # Later added criterion that size must be not smaller than four 30-m pixels, to avoid spurious cores
   where_clause = "DENS_PPSM >= 1000 AND Shape_Area >= 3600"
   printMsg('Selecting high-density blocks to initiate cores...')
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_PrimaryBlocks', where_clause)
   arcpy.CopyFeatures_management('lyr_PrimaryBlocks', coreBlocks)

   # Continue to add blocks meeting density and/or imperviousness criteria, that are adjacent to expanding urban cores
   # t0 = time.time()
   # arcpy.CopyFeatures_management(coreBlocks, expandCores)
   # where_clause = "(DENS_PPSM >= 500) OR (IMPERV_MEAN >= 20 AND SHP_IDX >= 0.185) OR (IMPERV20_MEAN >= 0.33 AND SHP_IDX >= 0.185)"
   # printMsg('Selecting additional adjacent blocks to expand cores...')
   # arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_SecondaryBlocks', where_clause)
   # arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
   # arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'ARE_IDENTICAL_TO', expandCores, '', 'REMOVE_FROM_SELECTION')
   # c = countSelectedFeatures('lyr_SecondaryBlocks')
   # while c > 0:
   #    printMsg('Continuing to expand cores with %s additional blocks...'%str(c))
   #    arcpy.Append_management ('lyr_SecondaryBlocks', expandCores)
   #    arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
   #    arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'ARE_IDENTICAL_TO', expandCores, '', 'REMOVE_FROM_SELECTION')
   #    c = countSelectedFeatures('lyr_SecondaryBlocks')
   # t1 = time.time()
   # elapsed_method1 = t1 - t0

   # initiate selection
   # t0 = time.time()
   where_clause = "(DENS_PPSM >= 500) OR (IMPERV_MEAN >= 20 AND SHP_IDX >= 0.185) OR (IMPERV20_MEAN >= 0.33 AND SHP_IDX >= 0.185)"
   printMsg('Selecting additional adjacent blocks to expand cores...')
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_SecondaryBlocks', where_clause)
   arcpy.SelectLayerByLocation_management('lyr_SecondaryBlocks', 'WITHIN_A_DISTANCE', coreBlocks, '0 METERS',
                                          'NEW_SELECTION')
   c0 = countFeatures(coreBlocks)
   c1 = countSelectedFeatures('lyr_SecondaryBlocks')
   # loop until no new are added
   while c1 > c0:
      printMsg('Cores expanding, with %s additional blocks...' % str(c1 - c0))
      c0 = countSelectedFeatures('lyr_SecondaryBlocks')
      arcpy.SelectLayerByLocation_management('lyr_SecondaryBlocks', 'WITHIN_A_DISTANCE', 'lyr_SecondaryBlocks',
                                             '0 METERS', 'ADD_TO_SELECTION')
      c1 = countSelectedFeatures('lyr_SecondaryBlocks')
   arcpy.CopyFeatures_management('lyr_SecondaryBlocks', expandCores)
   printMsg('Finished expanding cores.')
   # t1 = time.time()
   # elapsed_method2 = t1 - t0

   # Dissolve cores
   dissCores = scratchGDB + os.sep + "dissCores"
   printMsg('Dissolving features...')
   arcpy.Dissolve_management(expandCores, dissCores, "", "", "MULTI_PART")

   # Remove small holes and polygons
   fillCores = scratchGDB + os.sep + "fillCores"
   printMsg('Eliminating gaps and runts...')
   arcpy.EliminatePolygonPart_management(dissCores, fillCores, "AREA", "1 SquareMiles", "", "ANY")
   # TODO: Only remove inner holes instead of ANY? With ANY, cores get removed when separated
   #  (e.g. by road or river blocks), if none of the inidvidual parts are not at least 1 sq mile.
   # arcpy.EliminatePolygonPart_management(dissCores, fillCores, "AREA", "1 SquareMiles")

   # Group disjunct but nearby cores
   buffCores = scratchGDB + os.sep + "buffCores"
   grpCores = scratchGDB + os.sep + "grpCores"
   printMsg('Grouping cores...')
   arcpy.Buffer_analysis(fillCores, buffCores, "0.25 Miles", "", "", "ALL")
   arcpy.MultipartToSinglepart_management(buffCores, grpCores)

   # Generate CORE_ID field 
   printMsg('Adding CORE_ID field...')
   arcpy.AddField_management(grpCores, "CORE_ID", "LONG")
   expression = "!OBJECTID!"
   arcpy.CalculateField_management(grpCores, "CORE_ID", expression, "PYTHON_9.3")

   # Attach CORE_ID to relevant blocks
   tmpBlocks = scratchGDB + os.sep + "tmpBlocks"
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_coreBlocks')
   arcpy.SelectLayerByLocation_management('lyr_coreBlocks', 'WITHIN', fillCores, '', 'NEW_SELECTION')
   printMsg('Performing spatial join...')
   arcpy.SpatialJoin_analysis('lyr_coreBlocks', grpCores, tmpBlocks, "JOIN_ONE_TO_ONE", "KEEP_COMMON", "", "WITHIN")

   # Get population and area for each urban core
   printMsg('Summarizing population and area...')
   arcpy.Dissolve_management(tmpBlocks, out_Cores, "CORE_ID", "POP SUM;AREA_SQMI SUM", "MULTI_PART")
   arcpy.AlterField_management(out_Cores, "SUM_POP", "POP")
   arcpy.AlterField_management(out_Cores, "SUM_AREA_SQMI", "AREA_SQMI")
   # TODO: Remove cores < 1 sq mile here? Would be necessary if change is made not to remove these in fillCores.

   printMsg('Finished making cores.')
   return out_Cores


def CategorizeCores(in_Cores):
   '''Use population and area criteria to categorize urban cores.
   Parameters:
   - in_Cores: the input cores, generated by the MakeUrbanCores function. This will be modified by adding and populating a new field.'''

   arcpy.AddField_management(in_Cores, "CORE_TYPE", "SHORT")
   codeblock = '''def catCores(pop, area):
      if pop < 2500:
         if pop >= 1000 and area >=1:
            return 1 # Seed Core
         else:
            return 0 # Excluded Core
      elif pop < 25000:
         return 2 # Small Town Core
      elif pop < 250000:
         return 3 # Small City Core
      elif pop < 2500000:
         return 4 # Big City Core
      else:
         return 5 # Major Metro Core
   '''
   expression = "catCores(!POP!, !AREA_SQMI!)"
   arcpy.CalculateField_management(in_Cores, "CORE_TYPE", expression, "PYTHON_9.3", codeblock)
   return in_Cores


### Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   out_gdb = r'F:\David\projects\vulnerability_model\vars\travel_time\urban_cores.gdb'
   make_gdb(out_gdb)

   # # Set up variables
   # in_Blocks = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusBlocks2000_70mi'
   # # blocks subset to an additional 20 miles around the processing buffer, i.e., 70 miles around Virginia.
   # in_PopTab = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusBlocks2000_Pop'
   # in_Imperv = r'D:\Backups\GIS_Data_VA\NLCD\Products_2016\NLCD_imperv_20190405\NLCD_2006_Impervious_L48_20190405.img'
   # in_Imperv20 = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\vuln_work.gdb\imperv2006_20plus'
   # out_Tracts = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusTracts2000_70mi'
   # in_Year = 2000
   # in_Tracts = out_Tracts
   # out_Cores = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\UrbanCores2000'
   # out_Cores3 = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\UrbanCores2000_method3'
   # in_Cores = out_Cores3
   #
   # # End of variable input
   #
   # # Specify function(s) to run below
   # # PrepBlocks(in_Blocks, in_PopTab, in_Imperv, in_Imperv20, out_Tracts, in_Year)
   # # MakeUrbanCores(in_Blocks, out_Cores3)
   # CategorizeCores(in_Cores)

   # Set up variables
   in_Blocks = r'F:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\CensusBlocks2010_70mile'
   in_PopTab = r'F:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\CensusBlocks2010_Pop'
   # Uses the full-extent impervious raster, since the processing boundary is beyond the 50-mile version
   in_Imperv = r'F:\David\GIS_data\NLCD\nlcd_2019_impervious_l48_20210604\nlcd_2019_impervious_l48_20210604.img'
   # out_Tracts = r'F:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\CensusTracts2010_70mile'
   in_Year = 2010
   # in_Tracts = out_Tracts
   out_Cores = r'F:\David\GIS_data\NHGIS\blocks_pop_2010\CensusBlocks2010.gdb\UrbanCores2010_w2019imp'

   # End of variable input

   # Specify function(s) to run below
   PrepBlocks(in_Blocks, in_PopTab, in_Imperv, in_Year)
   MakeUrbanCores(in_Blocks, out_Cores)
   CategorizeCores(out_Cores)


if __name__ == '__main__':
   main()
