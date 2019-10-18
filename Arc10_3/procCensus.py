# ----------------------------------------------------------------------------------------
# procCensus.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-10-11
# Last Edit: 2019-10-18
# Creator:  Kirsten R. Hazler

# Summary:
# A library of functions for processing U.S. Census data 
# FUNCTION NOTE: It is a little tricky to make a general function to process data from all years, since field names and formats differ. Therefore, initial functions were made specific to 2000, then more general functions were made with certain code lines contingent on the year specified. Whenever new data is downloaded, some of the code may need adjusting.

# DATA NOTE:  To cover the 50-mile processing buffer around Virginia, download data for the following states: DE, DC, KY, MD, NC, PA, VA, TN, WV
# ----------------------------------------------------------------------------------------

import Helper
from Helper import *

def PrepBlocks(in_Blocks, in_PopTab, in_Imperv, in_Imperv20, out_Tracts, in_Year):
   '''Prepares Block-level and Tract-level data from the Census for the MakeUrbanCores function. Assumes GIS and tabular data for census blocks have been downloaded from https://www.nhgis.org/. 
   
   GIS data for blocks is downloaded by state: one shapefile for each state. It is assumed that the individual shapefiles have already been merged into a single polygon feature class within a geodatabase.
   
   Tabular data are downloaded as a single CSV file covering all the states in the shapefiles, and should contain population counts for each block. It is assumed that the CSV file has been converted to a table within a geodatabase.
   
   Parameters:
   - in_Blocks: Input feature class representing Census blocks
   - in_PopTab: Input table containing population count for each block
   - in_Imperv: Input raster representing percent imperviousness
   - in_Imperv20: Input raster in which cells with 20% or greater imperviousness are set to 1, otherwise 0
   - out_Tracts: Output feature class representing Census tracts
   - in_Year: The census year of the data
   '''
   
   # # Change the relevant field name to POP, if not already done
   # if len(arcpy.ListFields(in_PopTab,"POP"))<1:
      # printMsg('Renaming field to POP...')
      # if in_Year == 2000:
         # arcpy.AlterField_management (in_PopTab, 'FXS001', 'POP', 'POP')
      # elif in_Year == 2010:
         # arcpy.AlterField_management (in_PopTab, 'H7V001', 'POP', 'POP')
      # else:
         # printErr('Not a valid year.')
   
   # # Join fields from the population table to the feature class
   # fnames = [f.name for f in arcpy.ListFields(in_PopTab)]
   # fnames.remove('GISJOIN')
   # fnames.remove('OBJECTID')
   # printMsg('Joining fields...')
   # arcpy.JoinField_management (in_Blocks, 'GISJOIN', in_PopTab, 'GISJOIN', fnames)  

   # # Get a unique tract ID
   # printMsg('Creating and calculating TRACT_ID field...')
   # arcpy.AddField_management(in_Blocks, "TRACT_ID", "TEXT", "", "", 11)
   # if in_Year == 2000:
      # expression = "!FIPSSTCO!+ !TRACT2000!"
   # elif in_Year == 2010:
      # expression = "!STATEFP10!+ !COUNTYFP10! + !TRACTCE10!"
   # else:
      # printErr('Not a valid year.')
   # arcpy.CalculateField_management(in_Blocks, "TRACT_ID", expression, "PYTHON_9.3") 
      
   # # Calculate the area in square miles, and change the output field name.
   # printMsg('Calculating area...')
   # arcpy.AddGeometryAttributes_management (in_Blocks, "AREA", "", "SQUARE_MILES_US")
   # arcpy.AlterField_management (in_Blocks, 'POLY_AREA', 'AREA_SQMI', 'AREA_SQMI')
   
   # # Calculate the population density in persons per square mile
   # printMsg('Calculating population density...')
   # arcpy.AddField_management(in_Blocks, "DENS_PPSM", "DOUBLE")
   # expression = "!POP! / !AREA_SQMI!"
   # arcpy.CalculateField_management(in_Blocks, "DENS_PPSM", expression, "PYTHON_9.3") 
   
   # # Calculate the shape index
   # printMsg('Calculating shape index...')
   # arcpy.AddField_management(in_Blocks, "SHP_IDX", "DOUBLE")
   # expression = "(4*math.pi* !Shape_Area!)/(!Shape_Length!**2)"
   # arcpy.CalculateField_management(in_Blocks, "SHP_IDX", expression, "PYTHON_9.3") 
   
   # # Calculate the imperviousness
   # printMsg('Calculating imperviousness...')
   # zTab = in_Blocks + '_Imperv'
   # ZonalStatisticsAsTable (in_Blocks, 'GISJOIN', in_Imperv, zTab, "DATA", "ALL")
   # arcpy.JoinField_management (in_Blocks, 'GISJOIN', zTab, 'GISJOIN', ['MEAN', 'MEDIAN'])  
   # arcpy.AlterField_management (in_Blocks, 'MEAN', 'IMPERV_MEAN')
   # arcpy.AlterField_management (in_Blocks, 'MEDIAN', 'IMPERV_MEDIAN')
   
   # Calculate the proportion of polygon covered by 20% or greater imperviousness
   printMsg('Calculating proportion with 20% or greater imperviousness...')
   zTab20 = in_Blocks + '_Imperv20'
   ZonalStatisticsAsTable (in_Blocks, 'GISJOIN', in_Imperv20, zTab20, "DATA", "MEAN")
   arcpy.JoinField_management (in_Blocks, 'GISJOIN', zTab20, 'GISJOIN', ['MEAN'])  
   arcpy.AlterField_management (in_Blocks, 'MEAN', 'IMPERV20_MEAN')
   
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
   return (in_Blocks, out_Tracts)

def MakeUrbanCores(in_Blocks, in_Tracts, out_Cores):
   '''Creates urban cores from input census blocks and tracts, based on the first paragraph of Section 1 on page 53040 of the "Urban Area Criteria for the 2010 Census" (https://www.federalregister.gov/documents/2011/08/24/2011-21647/urban-area-criteria-for-the-2010-census).
   Parameters:
   - in_Blocks: Input feature class representing Census blocks; this should have been updated using the PrepBlocks function
   - in_Tracts: Input feature class representing Census tracts; this should have been created using the PrepBlocks function
   - out_Cores: Output feature class representing urban cores
   '''
   scratchGDB = arcpy.env.scratchGDB
   
   # # Select census tracts with land area < 3 sq.mi. and population density at least 1000 ppsm
   # initCores = scratchGDB + os.sep + "initCores"
   # where_clause = "AREA_SQMI < 3 AND DENS_PPSM >= 1000"
   # printMsg('Selecting tracts for initial urban cores, and saving...')
   # arcpy.MakeFeatureLayer_management(in_Tracts, 'lyr_InitCores', where_clause)
   # arcpy.CopyFeatures_management('lyr_InitCores', initCores)
   # mergeList = [initCores]

   # # Select census tracts with land area < 3 sq.mi. and population density at least 500 ppsm that are adjacent to initial urban cores
   # #CoreFringeTracts = scratchGDB + os.sep + 'CoreFringeTracts'
   # where_clause = "AREA_SQMI < 3 AND DENS_PPSM >= 500"
   # printMsg('Selecting tracts to expand cores...')
   # arcpy.MakeFeatureLayer_management(in_Tracts, 'lyr_CoreFringeTracts', where_clause)
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeTracts', 'WITHIN_A_DISTANCE', initCores, '0 METERS', 'NEW_SELECTION')
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeTracts', 'ARE_IDENTICAL_TO', initCores, '', 'REMOVE_FROM_SELECTION')
   # c = countSelectedFeatures('lyr_CoreFringeTracts')
   # if c > 0:
      # mergeList.append('lyr_CoreFringeTracts')
   # #arcpy.CopyFeatures_management('lyr_CoreFringeTracts', CoreFringeTracts)
   
   # # Select census blocks with population density at least 1000 ppsm that are adjacent to initial urban cores
   # #CoreFringeBlock = scratchGDB + os.sep + 'CoreFringeBlocks'
   # where_clause = "DENS_PPSM >= 1000"
   # printMsg('Selecting blocks to expand cores...')
   # arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_CoreFringeBlocks', where_clause)
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN_A_DISTANCE', initCores, '0 METERS', 'NEW_SELECTION')
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN', initCores, '', 'REMOVE_FROM_SELECTION')
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN', 'lyr_CoreFringeTracts', '', 'REMOVE_FROM_SELECTION')
   # c = countSelectedFeatures('lyr_CoreFringeBlocks')
   # if c > 0:
      # mergeList.append('lyr_CoreFringeBlocks')
   # #arcpy.CopyFeatures_management('lyr_CoreFringeBlocks', CoreFringeBlocks)
   
   # Merge the initial urban cores with the additional selected tracts and blocks
   expandCores = scratchGDB + os.sep + "expandCores"
   # printMsg('Merging features...')
   # arcpy.Merge_management (mergeList, expandCores)
   # arcpy.CopyFeatures_management(expandCores, initCores) # Initial cores overwritten with expansion
   # ### Above code accomplishes first paragraph, creating initial cores.
   # ### Now start a loop to continue expanding.
   
   # # Continue to add blocks meeting density and/or imperviousness criteria, that are adjacent to expanding urban cores
   # extendCores = scratchGDB + os.sep + "extendCores"
   # where_clause = "(DENS_PPSM >= 500) OR (IMPERV_MEAN >= 20 AND SHP_IDX >= 0.185)"
   # printMsg('Selecting lower density blocks to expand cores...')
   # arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_CoreFringeBlocks', where_clause)
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
   # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN', expandCores, '', 'REMOVE_FROM_SELECTION')
   # c = countSelectedFeatures('lyr_CoreFringeBlocks')
   # while c > 0:
      # printMsg('Continuing to expand cores with %s additional blocks...'%str(c))
      # arcpy.Merge_management ([expandCores, 'lyr_CoreFringeBlocks'], extendCores)
      # arcpy.CopyFeatures_management(extendCores, expandCores) # Expanded cores overwritten with extension
      # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
      # arcpy.SelectLayerByLocation_management ('lyr_CoreFringeBlocks', 'WITHIN', expandCores, '', 'REMOVE_FROM_SELECTION')
      # c = countSelectedFeatures('lyr_CoreFringeBlocks')
   # printMsg('Finished expanding cores.')   
   
   # Dissolve cores
   dissCores = scratchGDB + os.sep + "dissCores"
   printMsg('Dissolving features...')
   arcpy.Dissolve_management(expandCores, dissCores, "", "", "SINGLE_PART")
   
   # Fill holes
   fillCores = scratchGDB + os.sep + "fillCores"
   printMsg('Eliminating gaps...')
   arcpy.EliminatePolygonPart_management(dissCores, fillCores, "AREA", "5 SquareMiles", "", "CONTAINED_ONLY")
   
   # Repair geometry
   
   # Generate CORE_ID field 
   printMsg('Adding CORE_ID field...')
   arcpy.AddField_management(fillCores, "CORE_ID", "LONG")
   expression = "!OBJECTID!"
   arcpy.CalculateField_management(fillCores, "CORE_ID", expression, "PYTHON_9.3") 
   
   # Attach CORE_ID to blocks
   tmpBlocks = scratchGDB + os.sep + "tmpBlocks"
   printMsg('Performing spatial join...')
   arcpy.SpatialJoin_analysis (in_Blocks, fillCores, tmpBlocks, "JOIN_ONE_TO_ONE", "KEEP_COMMON", "", "WITHIN")
   
   # Get population and area for each urban core
   printMsg('Summarizing population and area...')
   arcpy.Dissolve_management(tmpBlocks, out_Cores, "CORE_ID", "POP SUM;AREA_SQMI SUM", "MULTI_PART")
   arcpy.AlterField_management(out_Cores, "SUM_POP", "POP")
   arcpy.AlterField_management(out_Cores, "SUM_AREA_SQMI", "AREA_SQMI")
   
   printMsg('Finished making cores.')
   return out_Cores
   
def MakeUrbanCores2(in_Blocks, in_Tracts, out_Cores):
   '''Creates urban cores from input census blocks and tracts, based on the first paragraph of Section 1 on page 53040 of the "Urban Area Criteria for the 2010 Census" (https://www.federalregister.gov/documents/2011/08/24/2011-21647/urban-area-criteria-for-the-2010-census).
   Parameters:
   - in_Blocks: Input feature class representing Census blocks; this should have been updated using the PrepBlocks function
   - in_Tracts: Input feature class representing Census tracts; this should have been created using the PrepBlocks function
   - out_Cores: Output feature class representing urban cores
   '''
   scratchGDB = arcpy.env.scratchGDB
   coreTracts = scratchGDB + os.sep + 'coreTracts'
   coreBlocks = scratchGDB + os.sep + 'coreBlocks'
   expandCores = scratchGDB + os.sep + "expandCores"
   
   # Select census tracts with land area < 3 sq.mi. and population density at least 1000 ppsm
   where_clause = "AREA_SQMI < 3 AND DENS_PPSM >= 1000"
   printMsg('Selecting tracts for initial urban cores and saving...')
   arcpy.MakeFeatureLayer_management(in_Tracts, 'lyr_PrimaryTracts', where_clause)
   arcpy.CopyFeatures_management('lyr_PrimaryTracts', coreTracts)

   # Select census tracts with land area < 3 sq.mi. and population density at 500-1000 ppsm that are adjacent to initial urban cores
   where_clause = "AREA_SQMI < 3 AND DENS_PPSM >= 500 AND DENS_PPSM < 1000"
   printMsg('Selecting adjacent tracts to expand cores...')
   arcpy.MakeFeatureLayer_management(in_Tracts, 'lyr_SecondaryTracts', where_clause)
   arcpy.SelectLayerByLocation_management ('lyr_SecondaryTracts', 'WITHIN_A_DISTANCE', coreTracts, '0 METERS', 'NEW_SELECTION')
   c = countSelectedFeatures('lyr_SecondaryTracts')
   if c > 0:
      printMsg('Appending secondary tracts...')
      arcpy.Append_management ('lyr_SecondaryTracts', coreTracts)
   
   # Select blocks within coreTracts, that have non-zero population
   where_clause = "POP <> 0"
   printMsg('Selecting populated blocks within core tracts...')
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_PrimaryBlocks', where_clause)
   arcpy.CopyFeatures_management('lyr_PrimaryBlocks', coreBlocks)
   
   # Select census blocks with population density at least 1000 ppsm that are adjacent to initial urban cores
   where_clause = "DENS_PPSM >= 1000"
   printMsg('Selecting adjacent high-density blocks to expand cores...')
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_SecondaryBlocks', where_clause)
   arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'WITHIN_A_DISTANCE', coreBlocks, '0 METERS', 'NEW_SELECTION')
   arcpy.SelectLayerByLocation_management ('lyr_SecondaryBlocks', 'ARE_IDENTICAL_TO', coreBlocks, '', 'REMOVE_FROM_SELECTION')
   c = countSelectedFeatures('lyr_SecondaryBlocks')
   if c > 0:
      arcpy.Append_management ('lyr_SecondaryBlocks', coreBlocks)
   ### Above code accomplishes first paragraph (with slight modification), creating initial cores.
   ### Now start a loop to continue expanding.
   
   # Continue to add blocks meeting density and/or imperviousness criteria, that are adjacent to expanding urban cores
   arcpy.CopyFeatures_management(coreBlocks, expandCores)
   where_clause = "(DENS_PPSM >= 500) OR (IMPERV_MEAN >= 20 AND SHP_IDX >= 0.185) OR (IMPERV20_MEAN >= 0.33 AND SHP_IDX >= 0.185)"
   printMsg('Selecting additional adjacent blocks to expand cores...')
   arcpy.MakeFeatureLayer_management(in_Blocks, 'lyr_TertiaryBlocks', where_clause)
   arcpy.SelectLayerByLocation_management ('lyr_TertiaryBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
   arcpy.SelectLayerByLocation_management ('lyr_TertiaryBlocks', 'ARE_IDENTICAL_TO', expandCores, '', 'REMOVE_FROM_SELECTION')
   c = countSelectedFeatures('lyr_TertiaryBlocks')
   while c > 0:
      printMsg('Continuing to expand cores with %s additional blocks...'%str(c))
      arcpy.Append_management ('lyr_TertiaryBlocks', expandCores)
      arcpy.SelectLayerByLocation_management ('lyr_TertiaryBlocks', 'WITHIN_A_DISTANCE', expandCores, '0 METERS', 'NEW_SELECTION')
      arcpy.SelectLayerByLocation_management ('lyr_TertiaryBlocks', 'ARE_IDENTICAL_TO', expandCores, '', 'REMOVE_FROM_SELECTION')
      c = countSelectedFeatures('lyr_TertiaryBlocks')
   printMsg('Finished expanding cores.')   
   
   # Dissolve cores
   dissCores = scratchGDB + os.sep + "dissCores"
   printMsg('Dissolving features...')
   arcpy.Dissolve_management(expandCores, dissCores, "", "", "SINGLE_PART")
   
   # Fill holes
   fillCores = scratchGDB + os.sep + "fillCores"
   printMsg('Eliminating gaps...')
   arcpy.EliminatePolygonPart_management(dissCores, fillCores, "AREA", "5 SquareMiles", "", "CONTAINED_ONLY")
   
   # Coalesce disjunct cores that should group together
   grpCores = scratchGDB + os.sep + "grpCores"
   printMsg('Grouping cores...')
   Coalesce(fillCores, "0.25 Miles", grpCores)
   
   # Generate CORE_ID field 
   printMsg('Adding CORE_ID field...')
   arcpy.AddField_management(grpCores, "CORE_ID", "LONG")
   expression = "!OBJECTID!"
   arcpy.CalculateField_management(grpCores, "CORE_ID", expression, "PYTHON_9.3") 
   
   # Attach CORE_ID to blocks
   tmpBlocks = scratchGDB + os.sep + "tmpBlocks"
   printMsg('Performing spatial join...')
   arcpy.SpatialJoin_analysis (in_Blocks, fillCores, tmpBlocks, "JOIN_ONE_TO_ONE", "KEEP_COMMON", "", "WITHIN")
   
   # Get population and area for each urban core
   printMsg('Summarizing population and area...')
   arcpy.Dissolve_management(tmpBlocks, out_Cores, "CORE_ID", "POP SUM;AREA_SQMI SUM", "MULTI_PART")
   arcpy.AlterField_management(out_Cores, "SUM_POP", "POP")
   arcpy.AlterField_management(out_Cores, "SUM_AREA_SQMI", "AREA_SQMI")
   
   printMsg('Finished making cores.')
   return out_Cores
      
   
### Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   # Set up variables
   in_Blocks = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusBlocks2000_70mi' 
   # blocks subset to an additional 20 miles around the processing buffer, i.e., 70 miles around Virginia.
   in_PopTab = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusBlocks2000_Pop'
   in_Imperv = r'D:\Backups\GIS_Data_VA\NLCD\Products_2016\NLCD_imperv_20190405\NLCD_2006_Impervious_L48_20190405.img'
   in_Imperv20 = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\vuln_work.gdb\imperv2006_20plus'
   out_Tracts = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\CensusTracts2000_70mi'
   in_Year = 2000
   in_Tracts = out_Tracts
   out_Cores = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\CensusWork2000.gdb\UrbanCores2000'

   # End of variable input

   # Specify function(s) to run below
   #PrepBlocks(in_Blocks, in_PopTab, in_Imperv, in_Imperv20, out_Tracts, in_Year)
   MakeUrbanCores2(in_Blocks, in_Tracts, out_Cores)
   
if __name__ == '__main__':
   main()
   
