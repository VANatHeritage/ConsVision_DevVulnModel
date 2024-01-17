"""
finalizeModelProducts.py
Version:  ArcGIS Pro
Creation Date: 2022-05-10
Creator:  David Bucklin

Purpose: Create GDB and TIF versions model products for the final Development Vulnerability model. This includes
the final model, raw vulnerability values, and the protection multiplier. Metadata is copied from template raster in
the output GDB.

Usage: Run entire script. For updates to the classification of the final model, see the UpdateCursor in finalizeModel.
Make sure to archive old versions of rasters first. overwriteOuptut is set to False, to avoid losing these files.
"""
from Helper import *


def finalizeModel(model, model_loc, year, boundary, out_gdb, upd=None):
   print('Working on raw values for ' + year + '...')
   if upd is None:
      rin = model_loc + os.sep + model + '_' + year + '.tif'
      rout = out_gdb + os.sep + 'DevVuln_to' + str(int(year) + 10) + '_raw'
      if arcpy.Exists(rout):
         arcpy.Rename_management(rout, os.path.dirname(rout) + os.sep + 'x_' + os.path.basename(rout))
      arcpy.sa.ExtractByMask(rin, boundary).save(rout)
      # update metadata
      md_templ = out_gdb + os.sep + 'template_' + os.path.basename(rout)
      metadata_copy(md_templ, rout)
   else:
      print("Update only, skipping raw values.")
   if upd is None:
      rin = model_loc + os.sep + model + '_' + year + '_final.tif'
      rout = out_gdb + os.sep + 'DevVuln_to' + str(int(year) + 10)
   else:
      print("Making updated final raster...")
      rin = model_loc + os.sep + model + '_' + year + '_final_' + upd + '.tif'
      rout = out_gdb + os.sep + 'DevVuln_to' + str(int(year) + 10) + '_' + upd
   print('Working on final model values for ' + year + '...')
   if arcpy.Exists(rout):
      arcpy.Rename_management(rout, os.path.dirname(rout) + os.sep + 'x_' + os.path.basename(rout))
   arcpy.sa.ExtractByMask(rin, boundary).save(rout)
   arcpy.AddField_management(rout, 'Vuln_Class', 'SHORT')
   arcpy.AddField_management(rout, 'Vuln_Label', 'TEXT', field_length=50)
   with arcpy.da.UpdateCursor(rout, ['Value', 'Vuln_Class', 'Vuln_Label']) as uc:
      for u in uc:
         value = u[0]
         if value < 0:
            u[1] = 0
            u[2] = 'Undevelopable (-1)'
         elif value <= 5:
            u[1] = 1
            u[2] = 'Class I (0 - 5: Least Vulnerable)'
         elif value <= 10:
            u[1] = 2
            u[2] = 'Class II (6 - 10)'
         elif value <= 25:
            u[1] = 3
            u[2] = 'Class III (11 - 25)'
         elif value <= 50:
            u[1] = 4
            u[2] = 'Class IV (26 - 50)'
         elif value <= 100:
            u[1] = 5
            u[2] = 'Class V (51 - 100: Most Vulnerable)'
         else:
            u[1] = 6
            u[2] = 'Already Developed (101)'
         uc.updateRow(u)
   # Update metadata
   md_templ = out_gdb + os.sep + 'template_' + os.path.basename(rout)
   metadata_copy(md_templ, rout)
   print("Done with " + year + '.')
   arcpy.BuildPyramidsandStatistics_management(out_gdb)
   return out_gdb


def main():

   ### HEADER
   # Final model (folder) name
   in_model = 'DevVuln_AllVars_20220510'
   # Input locations
   in_model_loc = r'D:\git\ConsVision_DevVulnModel\outputs' + os.sep + in_model
   out_tif_loc = r'D:\git\ConsVision_DevVulnModel\outputs\final_model\final_tifs'
   out_gdb_loc = r'D:\git\ConsVision_DevVulnModel\outputs\final_model\final_model.gdb'
   make_gdb(out_gdb_loc)
   # BMI multiplier
   bmi_mult = r'D:\git\ConsVision_DevVulnModel\inputs\masks\conslands_pmultBMI_current.tif'
   # Mask/extent for outputs
   bnd = r'D:\git\ConsVision_DevVulnModel\ArcGIS\dev_vuln.gdb\VirginiaCounty_Dissolve'
   # Snap raster
   snap = r'D:\git\ConsVision_DevVulnModel\ArcGIS\vulnmod.gdb\SnapRaster_albers_wgs84'

   # Set environments
   arcpy.env.extent = bnd
   arcpy.env.snapRaster = snap
   arcpy.env.outputCoordinateSystem = snap
   arcpy.env.cellSize = snap
   arcpy.env.overwriteOutput = False
   # END HEADER

   # Create final GDB rasters
   yrs = ['2006', '2019']
   for y in yrs:
      finalizeModel(model=in_model, model_loc=in_model_loc, year=y, boundary=bnd, out_gdb=out_gdb_loc)
   # Update run, to make a new finalized version incorporating updated NLCD/BMI
   finalizeModel(model=in_model, model_loc=in_model_loc, year="2019", boundary=bnd, out_gdb=out_gdb_loc, upd="2023upd")

   # Copy BMI multiplier used for final model to GDB
   bmi_gdb = out_gdb_loc + os.sep + 'ConslandsBMI_Multiplier'
   arcpy.sa.ExtractByMask(bmi_mult, bnd).save(bmi_gdb)
   md_templ = out_gdb_loc + os.sep + 'template_' + os.path.basename(bmi_gdb)
   metadata_copy(md_templ, bmi_gdb)

   # Copy GDB rasters to TIFs (only for final model time period)
   arcpy.CopyRaster_management(out_gdb_loc + os.sep + 'DevVuln_to2029_raw', out_tif_loc + os.sep + 'RawDevelopmentVulnerabilityScore.tif')
   arcpy.CopyRaster_management(out_gdb_loc + os.sep + 'DevVuln_to2029', out_tif_loc + os.sep + 'DevelopmentVulnerabilityModel.tif')
   arcpy.CopyRaster_management(bmi_gdb, out_tif_loc + os.sep + 'ConservationLandsBMI_Multiplier.tif')
   # Build pyramids for folder
   arcpy.BuildPyramidsandStatistics_management(out_tif_loc)

   # In ArcGIS Pro, make tile layers and layer packages from the TIF rasters, and share to ArcGIS Online.


if __name__ == '__main__':
   main()
