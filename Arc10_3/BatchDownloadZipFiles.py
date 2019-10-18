# ----------------------------------------------------------------------------------------
# BatchDownloadZipFiles.py
# Version:  Python 2.7.5
# Creation Date: 2015-07-14
# Last Edit: 2015-08-05
# Creator:  Kirsten R. Hazler
# Credits:  I adapted the FTP-related procedures from code provided by Adam Thom, here:  
# https://gis.stackexchange.com/questions/59047/downloading-multiple-files-from-tiger-ftp-site/
#
# Summary:
#     Downloads a set of zip files from an FTP site.  
#     The file set is determined by a list in a user-provided table.
#
# Usage Tips:
# Recommended default parameters to attach to tools in ArcGIS toolbox are below.  This single script can be added to multiple script tools with different defaults.
#
# TIGER/Line Roads data
#     in_fld = 'GEOID' (5-digit code for state/county)
#     pre = 'tl_2014_' (for 2014 data)
#     suf = '_roads.zip' 
#     ftpHOST = 'ftp2.census.gov'
#     ftpDIR = 'geo/tiger/TIGER2014/ROADS'
#
# National Hydrography Dataset (NHD) 
#     in_fld = 'HUC4' (for subregions)
#     pre = 'NHDH' (for high-resolution data)
#           'NHDM' (for medium-resolution data)
#     suf = '_931v220.zip' (for high-resolution data)
#           '_92v200.zip' (for medium-resolution data)
#     ftpHOST = 'nhdftp.usgs.gov'
#     ftpDIR = 'DataSets/Staged/SubRegions/FileGDB/HighResolution'
#              'DataSets/Staged/SubRegions/FileGDB/MediumResolution'
# 
# National Elevation Dataset (NED)
#     in_fld = 'FILE_ID' (assuming this is obtained from reference shapefile ned_1arcsec_g)
#     pre = 'USGS_NED_1_' (for 1 arc-second data)
#     suf = '_ArcGrid.zip' (for ArcGrid format)
#     ftpHOST = 'rockyftp.cr.usgs.gov'
#     ftpDIR = 'vdelivery/Datasets/Staged/Elevation/1/ArcGrid' (for 1 arc-second data)
# ----------------------------------------------------------------------------------------

# Import required modules
import ftplib # needed to connect to the FTP server and download files
import socket # needed to test FTP connection (or something; I dunno)
import csv # needed to read/write CSV files
import os # provides access to operating system funtionality such as file and directory paths
import sys # provides access to Python system functions
import traceback # used for error handling
import gc # garbage collection
import datetime # for time stamps
from datetime import datetime

# Script arguments to be input by user
in_tab = arcpy.GetParameterAsText(0) # Table containing unique ID field for the files to retrieve
in_fld = arcpy.GetParameterAsText(1) # Field containing the unique ID
pre = arcpy.GetParameterAsText(2) # Filename prefix; optional
suf = arcpy.GetParameterAsText(3) # Filename suffix; optional
out_dir = arcpy.GetParameterAsText(4) # Output directory to store downloaded files
ftpHOST = arcpy.GetParameterAsText(5) # FTP site
ftpDIR = arcpy.GetParameterAsText(6) # FTP directory

# Derived variables
if not pre:
   pre = ''
if not suf:
   suf = ''

# Create and open a log file.
# If this log file already exists, it will be overwritten.  If it does not exist, it will be created.
ProcLogFile = out_dir + os.sep + 'README.txt'
Log = open(ProcLogFile, 'w+') 
FORMAT = '%Y-%m-%d %H:%M:%S'
timestamp = datetime.now().strftime(FORMAT)
Log.write("Process logging started %s" % timestamp)
                                    
try:
   ftp = ftplib.FTP(ftpHOST)
   arcpy.AddMessage("CONNECTED TO HOST '%s'" % ftpHOST)
   Log.write("CONNECTED TO HOST '%s' \n" % ftpHOST)
except (socket.error, socket.gaierror) as e:
   arcpy.AddError('Error: cannot reach "%s" \n' % ftpHOST)
   Log.write('Error: cannot reach "%s"' % ftpHOST)

try:
   ftp.login()
except ftplib.error_perm:
   arcpy.AddError('Error: cannot login annonymously')
   Log.write('Error: cannot login annonymously \n')
   ftp.quit()
print 'Logged in'

try:
    ftp.cwd(ftpDIR)
except ftplib.error_perm:
   arcpy.AddError('Error: cannot CD to "%s"' %ftpDIR)
   Log.write ('Error: cannot CD to "%s" \n' %ftpDIR)
   ftp.quit()
print 'Changed to "%s" folder' %ftpDIR

nhdList = list() # List to hold NHD filenames
ProcList = list() # List to hold processing results

# Make a list of the files to download, from the input table                                     
try:
   sc = arcpy.da.SearchCursor(in_tab, in_fld)
   for row in sc:
      fname = pre + row[0] + suf
      nhdList.append(fname)
except:
   arcpy.AddError('Unable to parse input table.  Exiting...')
   Log.write('Unable to parse input table.  Exiting...')
   quit()
         
# Download the files and save to the output directory, while keeping track of success/failure
for fileName in nhdList:
   try:
      arcpy.AddMessage('Downloading %s ...' % fileName)
      with open(os.path.join(out_dir, fileName), 'wb') as local_file:
         ftp.retrbinary('RETR '+ fileName, local_file.write)
      ProcList.append('Successfully downloaded %s' % fileName)
   except:
      arcpy.AddWarning('Failed to download %s ...' % fileName)
      ProcList.append('Failed to download %s' % fileName)

# Write download results to log.
for item in ProcList:
   Log.write("%s\n" % item)
 
timestamp = datetime.now().strftime(FORMAT)
Log.write("\nProcess logging ended %s" % timestamp)   
Log.close()

