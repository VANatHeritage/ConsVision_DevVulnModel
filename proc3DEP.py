# ----------------------------------------------------------------------------------------
# Proc3DEP.py
# Version:  Python 2.7.5
# Creation Date: 2015-07-14
# Last Edit: 2019-10-03
# Creator:  Kirsten R. Hazler
#
# Summary:
# Set of functions for batch-downloading and post-processing elevation files from the 3DEP program. 
#
# Usage Tips:
# Recommended default parameters for different data sources are below. These may change over time, and code will need to be updated accordingly. 
# 
# 3D Elevation Program (3DEP; formerly NED)
#     Last updated 2019-10-03

#     url = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/ArcGrid/'

#     ### For 1/3 arc-second data (approx. 10-m resolution), most served files are like this:
#     pre = 'USGS_NED_13_'
#     suf = '_ArcGrid.zip' 
         
#     ### But some files are like this:
#     pre = ''
#     suf = '.zip'

#     in_fld = 'FileCode_3DEP' (assuming this is from the index file I modified)
# ----------------------------------------------------------------------------------------

# Import required modules
import urllib
import zipfile
import Helper
from Helper import *
#from arcpy.sa import *
#arcpy.CheckOutExtension("Spatial")


def BatchDownload(in_tab, in_fld, url, out_dir, pre = '', suf = ''):
   '''Downloads a set of files specified in a table
   Parameters:
   - in_tab: Input table containing unique basenames for the files to be retrieved
   - in_fld: Field in the input table, containing the unique basename
   - url: The web location containing the files to be downloaded
   - out_dir: Output directory to store downloaded files
   - pre: Filename prefix; optional
   - suf : Filename suffix; optional
   '''

   # Create and open a log file.
   # If this log file already exists, it will be overwritten.  If it does not exist, it will be created.
   ProcLogFile = out_dir + os.sep + 'README.txt'
   Log = open(ProcLogFile, 'w+') 
   FORMAT = '%Y-%m-%d %H:%M:%S'
   timestamp = datetime.now().strftime(FORMAT)
   Log.write("Process logging started %s \n" % timestamp)
     
   fileList = []  
   # Make a list of the files to download, from the input table                                     
   try:
      sc = arcpy.da.SearchCursor(in_tab, in_fld)
      for row in sc:
        fname = pre + row[0] + suf
        fileList.append(fname)
   except:
      printErr('Unable to parse input table.  Exiting...')
      Log.write('Unable to parse input table.  Exiting...')
      quit()
          
   # Download the files and save to the output directory, while keeping track of success/failure
   procList = []
   for fileName in fileList:
      try:
         inFile = url + fileName
         outFile = out_dir + os.sep + fileName
        
         rf = urllib.urlopen(inFile)
         msg = rf.getcode()
         rf.close()
         
         if msg == 404:
            printMsg('File does not exist: %s.' % fileName)
            procList.append('File does not exist: %s' % fileName)
         else:
            printMsg('Downloading %s. Patience please ...' % fileName)
            urllib.urlretrieve(inFile,outFile)
            procList.append('Successfully downloaded %s' % fileName)
      except:
         printWrng('Failed to download %s ...' % fileName)
         procList.append('Failed to download %s' % fileName)

   # Write download results to log.
   for item in procList:
      Log.write("%s\n" % item)
    
   timestamp = datetime.now().strftime(FORMAT)
   Log.write("\nProcess logging ended %s" % timestamp)   
   Log.close()
   
   return

def BatchStripName(in_dir, pre = '', suf = ''):
   '''Strips specified prefixes and suffixes from file names.
   Parameters:
   - in_dir: The directory containing files to rename
   - pre: The prefix to strip from file names
   - suf: The suffix to strip from file names
   '''
   for fileName in os.listdir(in_dir):
      oldName = in_dir + os.sep + fileName
      newName = oldName.replace(pre, '')
      newName = newName.replace(suf, '')
      if oldName != newName:
         if os.path.exists(newName):
            printWrng('This file already exists: %s' %os.path.basename(newName))
         else:
            os.rename(oldName, newName)
            printMsg('%s renamed to %s.' %(os.path.basename(oldName), os.path.basename(newName)))
   return

def BatchExtractZips(ZipDir, OutDir):
   '''Extracts all zip files within a specified directory, and saves the output to another specified directory.
   Parameters:
   - ZipDir:  The directory containing the zip files to be extracted
   - OutDir:  The directory in which extracted files will be stored
   '''
   # If the output directory does not already exist, create it
   if not os.path.exists(OutDir):
      os.makedirs(OutDir)
                                      
   # Set up the processing log                                   
   ProcLog = OutDir + os.sep + "ZipLog.txt"
   log = open(ProcLog, 'w+')

   try:
      flist = os.listdir (ZipDir) # Get a list of all items in the input directory
      zfiles = [f for f in flist if '.zip' in f] # This limits the list to zip files
      for zfile in zfiles:
         if zipfile.is_zipfile (ZipDir + os.sep + zfile):
            printMsg('Extracting %s' % zfile)
            try:
               zf = zipfile.ZipFile(ZipDir + os.sep + zfile)
               zf.extractall(OutDir)
               printMsg(zfile + ' extracted')
               log.write('\n' + zfile + ' extracted')

            except:
               printMsg('Failed to extract %s' % zfile)
               log.write('\nWarning: Failed to extract %s' % zfile)
               # Error handling code swiped from "A Python Primer for ArcGIS"
               tb = sys.exc_info()[2]
               tbinfo = traceback.format_tb(tb)[0]
               pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n " + str(sys.exc_info()[1])
               msgs = "ARCPY ERRORS:\n" + arcpy.GetMessages(2) + "\n"

               printWrng(msgs)
               printWrng(pymsg)
               printWrng(arcpy.GetMessages(1))
         else: 
            printWrng('%s is not a valid zip file' % zfile)
            log.write('\nWarning: %s is not a valid zip file' % zfile)
      arcpy.AddMessage('Your files have been extracted to %s.' % OutDir)
            
   except:
      # Error handling code swiped from "A Python Primer for ArcGIS"
      tb = sys.exc_info()[2]
      tbinfo = traceback.format_tb(tb)[0]
      pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n " + str(sys.exc_info()[1])
      msgs = "ARCPY ERRORS:\n" + arcpy.GetMessages(2) + "\n"

      printErr(msgs)
      printErr(pymsg)
      printMsg(arcpy.GetMessages(1))
      
   finally:
      log.close()

def MosaicDEM(in_dir, outRaster):
   '''Mosaics multiple DEM files into a single raster dataset. Assumes they are in ArcGRID format as downloaded and extracted from the 3DEP data.
   Parameters:
   - in_dir: directory containing extracted grids
   - outRaster: output raster file.
   '''
   arcpy.env.workspace = in_dir
   rasterList = arcpy.ListRasters('','GRID')
   rastDir = os.path.dirname(outRaster)
   rastName = os.path.basename(outRaster)
   
   printMsg('Mosaicking. This will take awhile...')
   arcpy.MosaicToNewRaster_management(rasterList, rastDir, rastName, "", "32_BIT_FLOAT", "", "1", "MEAN")
   printMsg('Building pyramids. This will take awhile...')
   arcpy.BuildPyramids_management (outRaster)
   
   return

def DEM2FGDB(in_dir, out_gdb):
   '''Imports GRID-format DEMs into a file geodatabase, in preparation for adding them to a mosaic dataset. Deletes the source data after successful import of each raster, and writes processing results to a log file.
   Parameters:
   - in_dir: Directory containing GRID-format rasters
   - outGDB: Geodatabase in which copied rasters will be stored
   '''
   
   myLogFile = in_dir + os.sep + 'ProcLog.txt'

   arcpy.env.overwriteOutput = True # Set overwrite option so that existing data may be overwritten

   # Get the list of GRID-format rasters in the input directory
   arcpy.env.workspace = in_dir
   rasterList = arcpy.ListRasters("*", "GRID")

   # Initialize a list for processing records
   myProcList = []

   for gname in rasterList:
      try:
         printMsg('Working on %s...' % gname)
         
         inNED = in_dir + os.sep + gname
         outNED = out_gdb + os.sep + gname
         nedTag = gname[3:]
         
         arcpy.CopyRaster_management (inNED, outNED)
         printMsg('- Added %s to geodatabase' % gname)
         myProcList.append('\nAdded %s to geodatabase' % gname)
               
         # Delete the source data
         try: 
            printMsg('- Deleting source NED for %s' % gname)
            arcpy.Delete_management(inNED)
         except:
            printMsg('Unable to delete source NED for %s' % gname)
            myProcList.append('Unable to delete source NED for %s' % gname)
         
         # Get the list of files remaining, related to the file just copied
         flist = os.listdir (in_dir) # Get a list of all items in the input directory
         dfiles = [in_dir + os.sep + f for f in flist if nedTag in f] 
         printMsg('Files to delete: %s' % dfiles)
         delfails = 0
         for d in dfiles:
            try:
               os.remove(d)
            except:
               delfails += 1
         if delfails == 0:
            printMsg('Successfully cleaned up ancillary files for %s' % gname)
            myProcList.append('Successfully cleaned up ancillary files for %s' % gname)
         else:
            printMsg('Unable to delete all ancillary files for %s' % gname)
            myProcList.append('Unable to delete all ancillary files for %s' % gname)
            
      except:
         printMsg('Failed to process %s' % gname)
         myProcList.append('\nFailed to process %s' % gname)
         # Error handling code swiped from "A Python Primer for ArcGIS"
         tb = sys.exc_info()[2]
         tbinfo = traceback.format_tb(tb)[0]
         pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n " + str(sys.exc_info()[1])
         msgs = "ARCPY ERRORS:\n" + arcpy.GetMessages(2) + "\n"

         printWrng(msgs)
         printWrng(pymsg)
         printMsg(arcpy.GetMessages(1))

   # Write processing results to a log file.
   # If this log file already exists, it will be overwritten.  If it does not exist, it will be created.
   Log = open(myLogFile, 'w+') 
   timeStamp = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
   Log.write('NED processing completed %s.  Results below.\n' % timeStamp)
   for item in myProcList:
      Log.write("%s\n" % item)
   Log.close()
   printMsg('Processing results can be viewed in %s' % myLogFile)

# Use the main function below to run desired function(s) directly from Python IDE or command line with hard-coded variables
def main():
   ### Set up variables
   in_tab = r'C:\Users\xch43889\Documents\Working\ConsVision\VulnMod\vuln_scratch.gdb\usgs_1x1_Degree'
   in_fld = 'FileCode_3DEP' 
   url = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/ArcGrid/'
   out_dir = r'D:\Backups\GIS_Data_VA\3DEP\Zips'
   in_dir = r'D:\Backups\GIS_Data_VA\3DEP\Extract_13Arc'
   out_gdb = r'D:\Backups\GIS_Data_VA\3DEP\elev_13Arc.gdb'
   
   ### Most download files are like this:
   pre1 = 'USGS_NED_13_'
   suf1 = '_ArcGrid.zip' 
   
   ### Some download files are like this:
   pre2 = ''
   suf2 = '.zip'
   
   ### For BatchStripName function, use this:
   pre3 = 'USGS_NED_13_'
   suf3 = '_ArcGrid' 
   
   # End of variable input

   ### Specify function(s) to run below
   # BatchDownload(in_tab, in_fld, url, out_dir, pre1, suf1) # This should get most files
   # BatchDownload(in_tab, in_fld, url, out_dir, pre2, suf2) # This should hopefully get all remaining
   # BatchStripName(in_dir, pre3, suf3)
   DEM2FGDB(in_dir, out_gdb)
   
if __name__ == '__main__':
   main()
