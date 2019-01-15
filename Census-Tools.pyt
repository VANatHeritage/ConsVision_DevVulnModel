# ----------------------------------------------------------------------------------------
# Census-Tools.pyt
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-01-15
# Last Edit: 2019-01-15
# Creator:  Kirsten R. Hazler

# Summary:
# A toolbox for preparing U.S. Census data for use in the Development Vulnerability Model

# Usage Notes:
#  
# ----------------------------------------------------------------------------------------

import ProcACS
from ProcACS import *

# First define some handy functions
def defineParam(p_name, p_displayName, p_datatype, p_parameterType, p_direction, defaultVal = None):
   '''Simplifies parameter creation. Thanks to http://joelmccune.com/lessons-learned-and-ideas-for-python-toolbox-coding/'''
   param = arcpy.Parameter(
      name = p_name,
      displayName = p_displayName,
      datatype = p_datatype,
      parameterType = p_parameterType,
      direction = p_direction)
   param.value = defaultVal 
   return param

def declareParams(params):
   '''Sets up parameter dictionary, then uses it to declare parameter values'''
   d = {}
   for p in params:
      name = str(p.name)
      value = str(p.valueAsText)
      d[name] = value
      
   for p in d:
      globals()[p] = d[p]
   return 

# Define the toolbox
class Toolbox(object):
   def __init__(self):
      """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
      self.label = "Census Toolbox"
      self.alias = "Census-Toolbox"

      # List of tool classes associated with this toolbox
      self.tools = [addFieldsBG]

# Define the tools
class addFieldsBG(object):
   def __init__(self):
      """Define the tool (tool name is the name of the class)."""
      self.label = "Add Fields to Block Groups"
      self.description = 'Adds various tabular attributes to a Block Groups feature class. Assumes Block Groups feature class is contained in a geodatabase with specific structure and naming convention within input geodatabase. Such data can be obtained here: https://www.census.gov/geo/maps-data/data/tiger-data.html.'
      self.canRunInBackground = True
      self.category = "American Community Survey Tools"

   def getParameterInfo(self):
      """Define parameters"""
      parm0 = defineParam("in_BG", "Input Block Groups", "DEFeatureClass", "Required", "Input")
      parm1 = defineParam("out_BG", "Output Block Groups", "DEFeatureClass", "Required", "Output")

      parms = [parm0, parm1]
      return parms

   def isLicensed(self):
      """Set whether tool is licensed to execute."""
      return True

   def updateParameters(self, parameters):
      """Modify the values and properties of parameters before internal
      validation is performed.  This method is called whenever a parameter
      has been changed."""
      return

   def updateMessages(self, parameters):
      """Modify the messages created by internal validation for each tool
      parameter.  This method is called after internal validation."""
      return

   def execute(self, parameters, messages):
      """The source code of the tool."""
      # Set up parameter names and values
      declareParams(parameters)

      addFieldsToBlockGroups(in_BG, out_BG)
      
      return out_BG