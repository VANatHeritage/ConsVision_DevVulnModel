"""
finalizeModelProducts.py
Version:  ArcGIS Pro
Creation Date: 2022-05-10
Creator:  David Bucklin

Purpose: Create GDB and TIF copies of the final Development Vulnerability model (raw values and final model).
"""
from Helper import *

# Final model (folder) name
in_model = 'DevVuln_AllVars_20220510'
# Input locations
in_model_loc = r'D:\git\ConsVision_DevVulnModel\outputs' + os.sep + in_model
out_tif_loc = r'D:\git\ConsVision_DevVulnModel\outputs\final_model\final_tifs'
out_gdb_loc = r'D:\git\ConsVision_DevVulnModel\outputs\final_model\final_model.gdb'
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

# Create final GDB rasters
yrs = ['2006', '2019']
for y in yrs:
   print('Working on raw values for ' + y + '...')
   rin = in_model_loc + os.sep + in_model + '_' + y + '.tif'
   rout = out_gdb_loc + os.sep + 'DevVuln_to' + str(int(y) + 10) + '_raw'
   if arcpy.Exists(rout):
      arcpy.Rename_management(rout, os.path.dirname(rout) + os.sep + 'x_' + os.path.basename(rout))
   arcpy.sa.ExtractByMask(rin, bnd).save(rout)
   # update metadata
   md_templ = out_gdb_loc + os.sep + 'template_' + os.path.basename(rout)
   metadata_copy(md_templ, rout)
   print('Working on final model values for ' + y + '...')
   rin = in_model_loc + os.sep + in_model + '_' + y + '_final.tif'
   rout = out_gdb_loc + os.sep + 'DevVuln_to' + str(int(y) + 10)
   if arcpy.Exists(rout):
      arcpy.Rename_management(rout, os.path.dirname(rout) + os.sep + 'x_' + os.path.basename(rout))
   arcpy.sa.ExtractByMask(rin, bnd).save(rout)
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
   md_templ = out_gdb_loc + os.sep + 'template_' + os.path.basename(rout)
   metadata_copy(md_templ, rout)
   print("Done with " + y + '.')
arcpy.BuildPyramidsandStatistics_management(out_gdb_loc)

# Copy to TIFs (2019 only)
arcpy.CopyRaster_management(out_gdb_loc + os.sep + 'DevVuln_to2029_raw',
                            out_tif_loc + os.sep + 'RawDevelopmentVulnerabilityScore.tif')
arcpy.CopyRaster_management(out_gdb_loc + os.sep + 'DevVuln_to2029',
                            out_tif_loc + os.sep + 'DevelopmentVulnerabilityModel.tif')
arcpy.CopyRaster_management(bmi_mult,
                            out_tif_loc + os.sep + 'ConservationLandsBMI_Multiplier.tif')
arcpy.BuildPyramidsandStatistics_management(out_tif_loc)


# In ArcGIS Pro, make layer packages for the TIF rasters.

# end
