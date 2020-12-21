"""
Name:     CreditTool_4.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  May 6, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better;
          Spatial Analyst extension

The provided Map_Units_Dissolve feature class is used to derive the workspace.
Requires Map_Units_Dissolve feature classes created by Credit Tool 3.
Transects_Provided must be provided by SETT.

Copyright 2017-2020 Environmental Incentives, LLC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

# Import system modules
import arcpy
import sys
import gc
import os
import ccslib

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(ccslib) #ensures up-to-date hqtlib runs on arcpro


def main():
    # GET PARAMETER VALUES
    Map_Units_Dissolve_Provided = arcpy.GetParameterAsText(0)
    Transects_Provided = arcpy.GetParameterAsText(1)
    Project_Folder = arcpy.GetParameterAsText(2)
    Project_Name = arcpy.GetParameterAsText(3)  # optional

    # DEFINE DIRECTORIES & PATH NAMES FOR FOLDERS & GBDs
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    # Construct pathname to workspace
    workspace = arcpy.Describe(Map_Units_Dissolve_Provided).path
    arcpy.AddMessage("Project geodatabase: " + workspace)

    # ENVIRONMENT SETTINGS
    # Set workspaces
    arcpy.env.workspace = workspace
    scratch_folder = os.path.join(
        arcpy.Describe(workspace).path, 'scratch'
        )
    if arcpy.Exists(scratch_folder):
        pass
    else:
        arcpy.CreateFolder_management(arcpy.Describe(workspace).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    # Filenames for feature classes or rasters used by this script

    # Filenames for feature classes or rasters created by this script
    TRANSECTS_SJ = "Transects_SpatialJoin"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    if Transects_Provided:
        # Update message
        arcpy.AddMessage("Executing spatial join of Transects and "
                         "Map_Unit_Dissolve layer")

        # ccslib.AddTransectFields(Transects)
        Map_Units_Dissolve = Map_Units_Dissolve_Provided
        out_name = "in_memory/Transects"
        transects = ccslib.TransectJoin(Map_Units_Dissolve, Transects_Provided, out_name)

    else:
        arcpy.AddError("ERROR:: Please provide the transects feature"
                       "class or shapefile provided by the SETT")
        sys.exit(0)

    # Update message
    arcpy.AddMessage("Preparing Transects Spatial Join for export")

    # Remove unnecessary fields
    allowable_fields = ["Bearing1", "Bearing2", "Bearing3", "UTM_E", "UTM_N",
                        "Map_Unit_ID", "Map_Unit_Name", "Meadow", "Indirect",
                        "Acres", "Spring_HSI", "Summer_HSI", "Winter_HSI",
                        "PJ_Cover", "Current_Breed", "Current_LBR",
                        "Current_Winter", "Projected_Breed",
                        "Projected_LBR", "Projected_Winter", "Permanent_Breed",
                        "Permanent_LBR", "Permanent_Winter", "Transects",
                        "Transect_Number", "Sample_Type", "Notes"]
    allowable_fields_lower = [allow_field.lower() for allow_field
                              in allowable_fields]
    for field in arcpy.ListFields(transects):
        if field.name.lower() not in allowable_fields_lower \
                and field.required is False:
            try:
                arcpy.DeleteField_management(transects, field.name)
            except arcpy.ExecuteError:
                pass
    # ccslib.SimplifyFields(TRANSECTS_SJ, allowable_fields)

    # Sort fields by Transect ID
    arcpy.Sort_management(transects, TRANSECTS_SJ,
                          [["Transect_Number", "ASCENDING"]])

    # Add Transects to map
    ccslib.AddToMap(TRANSECTS_SJ)

    # Export data to Excel
    table = TRANSECTS_SJ
    ccslib.ExportToExcel(table, Project_Folder, Project_Name)

    # Save map document
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        p.save()
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        mxd.save()

    # ------------------------------------------------------------------------

# EXECUTE SCRIPT


if __name__ == "__main__":
    gc.enable()
    main()
    gc.collect()
