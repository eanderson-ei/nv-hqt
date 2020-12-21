"""
Name:     DebitTool_4.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better;
          Spatial Analyst extension

Path to the project's workspace is derived from the Map_Units
feature class provided by the user.
Requires Current_Anthro_Features and Map_Units feature classes created by
Debit Tool 3.

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
import os
import sys
import gc
import ccslib

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(ccslib)


def main():
    # GET PARAMETER VALUES
    Map_Units_Provided = arcpy.GetParameterAsText(0)
    Project_Folder = arcpy.GetParameterAsText(1)
    Project_Name = arcpy.GetParameterAsText(2)  # optional

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    workspace = arcpy.Describe(Map_Units_Provided).path
    arcpy.AddMessage("Project geodatabase: " + workspace)
    
    # Instantiate a ccsStandard object
    ccsStandard = ccslib.ccsStandard(workspace, scriptPath)

    # ENVIRONMENT SETTINGS
    # Set workspaces
    arcpy.env.workspace = workspace
    scratch_folder = os.path.join(
        arcpy.Describe(workspace).path, 'scratch'
        )
    if arcpy.Exists(scratch_folder):
        pass
    else:
        arcpy.CreateFolder_management(scratch_folder)
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE VARIABLES FOR INPUT DATA
    inputDataPath = ccsStandard.InputDataPath
    # Filenames of feature classes and rasters used by this script
    MAP_UNITS = "Map_Units"
    CURRENT_ANTHRO_FEATURES = "Current_Anthro_Features"
    # Filenames of feature classes and rasters created by this script
    MAP_UNITS_DISSOLVE = "Map_Units_Dissolve"
    CURRENT_MGMT_CAT = "Current_Mgmt_Cat"
    CURRENT_WMZ = "Current_WMZ"
    CURRENT_PMU = "Current_PMU"
    CURRENT_PRECIP = "Current_Precip"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check tool version
    ccslib.CheckToolVersion()
    
    # Check out Spatial Analyst extension
    ccslib.CheckOutSpatialAnalyst()

    # Clear selection, if present
    ccslib.ClearSelectedFeatures(Map_Units_Provided)

    # Check Map_Units layer
    feature = Map_Units_Provided
    required_fields = ["Map_Unit_ID", "Map_Unit_Name", "Meadow"]
    no_null_fields = ["Map_Unit_ID"]
    expected_fcs = [CURRENT_ANTHRO_FEATURES]
    ccslib.CheckPolygonInput(feature, required_fields, expected_fcs,
                             no_null_fields)

    # Update Map Units layer with provided layer and add to map
    Map_Units = ccslib.AdoptParameter(Map_Units_Provided, MAP_UNITS,
                                      preserve_existing=False)
    layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
    ccslib.AddToMap(Map_Units, layerFile)

    # Update message
    arcpy.AddMessage("Dissolving all multi-part map units to create "
                     "Map_Units_Dissolve")

    # Dissolve Map Units
    allowable_fields = ["Map_Unit_ID", "Map_Unit_Name", "Meadow",
                        "Disturbance_Type", "PJ", "BROTEC", "Conifer_Phase"]
    out_name = MAP_UNITS_DISSOLVE
    anthro_features = CURRENT_ANTHRO_FEATURES
    Map_Units_Dissolve = ccslib.DissolveMapUnits(Map_Units, allowable_fields,
                                                 out_name, anthro_features)

    # Update message
    arcpy.AddMessage("Adding Map_Units_Dissolve to map")

    # Add layer to map document
    feature = Map_Units_Dissolve
    layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
    ccslib.AddToMap(feature, layerFile)

    # Update message
    arcpy.AddMessage("Calculating area in acres for each map unit")

    # Calculate Area
    ccslib.CalcAcres(Map_Units_Dissolve)

    # Initialize a list to track proportion feature classes
    prop_fcs = []

    # Update message
    arcpy.AddMessage("Calculating Proportion within each precipitation zone")

    # Calculate Proportion of each map unit in each Precip Zone
    in_feature = os.path.join(inputDataPath, "Precip")
    out_feature_class = CURRENT_PRECIP
    field_name = "Precip_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Update message
    arcpy.AddMessage("Calculating Management Importance Factor")

    # Calculate Proportion of each map unit in each Management Category
    in_feature = os.path.join(inputDataPath, "Mgmt_Cat")
    out_feature_class = CURRENT_MGMT_CAT
    field_name = "Mgmt_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Update message
    arcpy.AddMessage("Calculating Proportion within each WAFWA Management "
                     "Zone")

    # Calculate Proportion in each map unit in each WAFWA Zone
    in_feature = os.path.join(inputDataPath, "NV_WAFWA")
    out_feature_class = CURRENT_WMZ
    field_name = "WMZ_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Update message
    arcpy.AddMessage("Calculating Proportion within each Priority Management "
                     "Unit")

    # Calculate Proportion in each map unit in each PMU
    in_feature = os.path.join(inputDataPath, "NV_PMU")
    out_feature_class = CURRENT_PMU
    field_name = "PMU_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Delete unnecessary fields in proportion feature classes
    allowable_fields = ["Map_Unit_ID", "Management", "Mgmt_zone",
                        "PMU_NAME", "Precip", "Mgmt_Proportion",
                        "WMZ_Proportion", "PMU_Proportion",
                        "Precip_Proportion"]
    for feature in prop_fcs:
        ccslib.SimplifyFields(feature, allowable_fields)

    # Set processing extent to Map_Units layer
    arcpy.env.extent = arcpy.Describe(Map_Units_Dissolve).extent
    
    # Calculate the average HSI values per map unit for each map unit
    HSIseasons = ccsStandard.HSISeasons
    for season in HSIseasons:
        # Update message
        arcpy.AddMessage("Summarizing " + season + " HSI")

        # Calculate zonal statistics for each map unit
        inZoneData = Map_Units_Dissolve
        inValueRaster = os.path.join(inputDataPath, season + "_HSI")
        zoneField = "Map_Unit_ID"
        outTable = "ZonalStats_" + season + "_HSI"
        ccslib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

        # Join the zonal statistic to the Map Units Dissolve table
        fieldName = season + "_HSI"
        ccslib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

    # Calculate the average seasonal modifier values per map unit and join to
    # Map_Units_Dissolve layer
    terms = ccsStandard.DebitTerms
    seasons = ccsStandard.Seasons
    for term in terms:
        for season in seasons:
            # Update message
            arcpy.AddMessage("Summarizing " + term + "_Local_" + season)

            # Calculate zonal statistics for each map unit
            inZoneData = Map_Units_Dissolve
            inValueRaster = term + "_Local_" + season
            zoneField = "Map_Unit_ID"
            outTable = "ZonalStats_" + term + season
            ccslib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

            # Join the zonal statistic to the Map Units Dissolve table
            fieldName = term + "_" + season
            ccslib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

    # Add transect field to Map_Units_Dissolve
    input_feature = Map_Units_Dissolve
    fields = ["Transects"]
    fieldTypes = ["SHORT"]
    ccslib.AddFields(input_feature, fields, fieldTypes)

    # Export data to Excel
    input_Tables = [MAP_UNITS_DISSOLVE, CURRENT_MGMT_CAT,
                    CURRENT_WMZ, CURRENT_PMU, CURRENT_PRECIP]
    for table in input_Tables:
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
