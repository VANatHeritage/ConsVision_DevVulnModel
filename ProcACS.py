# ----------------------------------------------------------------------------------------
# ProcACS.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-12-14
# Last Edit: 2019-01-15
# Creator(s):  Kirsten R. Hazler and Emily Routman

# Summary:
# Functions for processing data from the American Community Survey (ACS) needed for the Virginia Vulnerability Model


# Usage Tips:
# [Add usage tips if needed.]

# Dependencies:
# [Does this require anything special? Other scripts?]

# ----------------------------------------------------------------------------------------

# Import modules
import os, sys, traceback
# arcpy.CheckOutExtension("Spatial")
# from arcpy.sa import *

try:
   arcpy
   print "Arcpy is already loaded"
except:
   import arcpy   
   print "Initiating arcpy..."

from datetime import datetime as datetime   
   
# Set overwrite option so that existing data may be overwritten
arcpy.env.overwriteOutput = True

def printMsg(msg):
   arcpy.AddMessage(msg)
   print msg

def addFieldsToBlockGroups(in_BG, out_BG):
   '''Adds various tabular attributes to a Block Groups feature class. Assumes Block Groups feature class is contained in a geodatabase with specific structure and naming convention within input geodatabase. Such data can be obtained here: https://www.census.gov/geo/maps-data/data/tiger-data.html.
   Parameters:
   - in_BG = Input Block Groups feature class
   - out_BG = Output Block Groups feature class with attributes added
   '''
   
   # Set up some basic parameters
   in_GDB = os.path.dirname(in_BG)
   keyFldBG = 'GEOID_Data'
   keyFldTabs = 'GEOID' 
   
   # Copy the input feature class to a new feature class
   printMsg('Copying input to a new output feature class...')
   arcpy.Copy_management(in_BG, out_BG)
   
   # Join the Age/Sex fields
   printMsg('Joining selected Age/Sex fields to output...')
   tabAgeSex = in_GDB + os.sep + 'X01_AGE_AND_SEX'
   fldsAgeSex = ['B01001e1'] # Add more fields within list as needed, separated by commas
   arcpy.JoinField_management (out_BG, keyFldBG, tabAgeSex, keyFldTabs, fldsAgeSex)
   
   # Join the Commute fields
   printMsg('Joining selected Commute fields to output...')
   tabCommute = in_GDB + os.sep + 'X08_COMMUTING'
   fldsCommute = ['B08303e1', 'B08303e12', 'B08303e13']
   arcpy.JoinField_management (out_BG, keyFldBG, tabCommute, keyFldTabs, fldsCommute)
   
   # Join the Employment fields
   printMsg('Joining selected Employment fields to output...')
   tabEmploy = in_GDB + os.sep + 'X23_EMPLOYMENT_STATUS'
   fldsEmploy = ['B23027e17', 'B23027e19']
   arcpy.JoinField_management (out_BG, keyFldBG, tabEmploy, keyFldTabs, fldsEmploy)
   
   ### EMILY TO DO:
   # Add and calculate additional fields
   # See http://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/add-field.htm
   # See http://desktop.arcgis.com/en/arcmap/10.3/tools/data-management-toolbox/calculate-field.htm
   
   # Set up dictionary of field aliases
   flds = {}
   flds['B01001e1']='TotPop'
   flds['B08303e1']='Commuters'
   flds['B08303e12']='Commuters_60to89'
   flds['B08303e13']='Commuters_gte90'
   flds['B23027e17']='Pop_45to54'
   flds['B23027e19']='FullTime_45to54'
   ### EMILY TO DO: Add more field/alias pairs to dictionary as needed
   
   # Assign aliases to fields
   printMsg('Assigning aliases to fields...')
   for f in flds:
      fldName = f
      fldAlias = flds[a]
      arcpy.AlterField_management(out_BG, fldName, "", fldAlias)

   printMsg('Mission accomplished.')
   return out_BG

   
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables
def main():
   # Set up parameters
   in_BG = r'H:\Backups\GIS_Data_VA\TIGER\ACS\ACS_2016_5YR_BG_51\ACS_2016_5YR_BG_51_VIRGINIA.gdb\ACS_2016_5YR_BG_51_VIRGINIA'
   out_BG = r'H:\Backups\GIS_Data_VA\TIGER\ACS\ACS_2016_5YR_BG_51\TestOutputs.gdb\attr_ACS_2016_5YR_BG_51_VIRGINIA'
   
   # Set up function(s) to run
   addFieldsToBlockGroups(in_BG, out_BG)
   
if __name__ == '__main__':
   main()