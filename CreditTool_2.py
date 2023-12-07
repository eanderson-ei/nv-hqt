"""
Name:     CreditTool_2.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better

The provided Map_Units feature class is used to derive the workspace.
Requires Credit_Project_Area feature class created by Credit Tool 1 unless project
proposes to remove anthropogenic features.

Copyright 2017-2023 Environmental Incentives, LLC.

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
    Map_Units_Provided = arcpy.GetParameterAsText(0)  # optional
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(1)  # optional
    Project_Folder = arcpy.GetParameterAsText(2)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    if Map_Units_Provided:
        workspace = arcpy.Describe(Map_Units_Provided).path
    elif Proposed_Modified_Features_Provided:
        workspace = arcpy.Describe(Proposed_Modified_Features_Provided).path
    else:
        arcpy.AddMessage("Please provide either a Map_Units or " +
                         "Proposed_Modified_Features layer.")
        sys.exit(0)
    arcpy.AddMessage("Project geodatabase: " + workspace)
    Project_Folder = arcpy.Describe(workspace).path
    arcpy.AddMessage("Project folder:" + Project_Folder)
    
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
        arcpy.CreateFolder_management( arcpy.Describe(workspace).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE GLOBAL VARIABLES
    AnthroAttributeTable = ccsStandard.AnthroAttributeTable
    # Filenames for feature class and rasters created by this script
    INDIRECT_IMPACT_AREA = "Indirect_Impact_Area"
    ANALYSIS_AREA = "Analysis_Area"
    # Filenames for feature classes or rasters used by this script
    MAP_UNITS = "Map_Units"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"
    CREDIT_PROJECT_AREA = "Credit_Project_Area"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check provided layers
    if not Map_Units_Provided and not Proposed_Modified_Features_Provided:
        arcpy.AddError("ERROR:: Please provide a 'Map_Units' and/or "
                       "'Proposed_Modified_Features' feature.")
        sys.exit(0)

    if not Proposed_Modified_Features_Provided:
        # Ensure Proposed_Modified_Features does not exist
        if arcpy.Exists("Proposed_Modified_Features"):
            arcpy.AddError("ERROR:: A 'Proposed_Modified_Features' layer "
                           "was detected in the project's geodatabase. "
                           "Provide the 'Proposed_Modified_Features' layer "
                           "and re-run Credit Tool 2.")
            sys.exit(0)

    if Map_Units_Provided:
        # Clear selection, if present
        ccslib.ClearSelectedFeatures(Map_Units_Provided)

        # Check provided layer
        feature = Map_Units_Provided
        required_fields = ["Map_Unit_ID", "Map_Unit_Name", "Meadow"]
        no_null_fields = ["Map_Unit_ID", "Meadow"]
        expected_fcs = [CREDIT_PROJECT_AREA]
        ccslib.CheckPolygonInput(feature, required_fields, expected_fcs,
                                 no_null_fields)

        # Update Map Units layer with provided layer
        provided_input = Map_Units_Provided
        parameter_name = MAP_UNITS
        preserve_existing = False
        Map_Units = ccslib.AdoptParameter(provided_input, parameter_name,
                                          preserve_existing)

        # Add Map Units layer to map
        layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
        ccslib.AddToMap(Map_Units, layerFile)

        # Provide location of Credit Project Area
        Credit_Project_Area = CREDIT_PROJECT_AREA

    # Set up flag for projects that propose to modify anthro features
    includes_anthro_mod = False

    if Proposed_Modified_Features_Provided:
        # Update flag
        includes_anthro_mod = True

        # Clear selection, if present
        ccslib.ClearSelectedFeatures(Proposed_Modified_Features_Provided)

        # Check provided layer
        required_fields = ["Type", "Subtype"]
        no_null_fields = required_fields
        expected_fcs = None
        ccslib.CheckPolygonInput(Proposed_Modified_Features_Provided,
                                 required_fields, expected_fcs, no_null_fields)

        # Update Proposed_Modified_Features with provided layer
        provided_input = Proposed_Modified_Features_Provided
        parameterName = PROPOSED_MODIFIED_FEATURES
        preserve_existing = False
        Proposed_Modified_Features = ccslib.AdoptParameter(
            provided_input, parameterName, preserve_existing
            )

        # Add Proposed Modified Features layer to map
        layerFile = ccsStandard.getLayerFile("SurfaceDisturbance.lyr")
        ccslib.AddToMap(Proposed_Modified_Features, layerFile)

        # Update message
        arcpy.AddMessage("Creating the area of indirect benefit")

        # Create Credit_Project_Area for projects that propose to modify
        # anthropogenic features
        # Create the Indirect_Impact_Area
        in_data = Proposed_Modified_Features
        out_name = INDIRECT_IMPACT_AREA
        Indirect_Impact_Area = ccslib.CreateIndirectImpactArea(
            in_data, AnthroAttributeTable, out_name
            )

        # Add field "Indirect"
        input_feature = Indirect_Impact_Area
        fieldsToAdd = ["Indirect"]
        fieldTypes = ["TEXT"]
        ccslib.AddFields(input_feature, fieldsToAdd, fieldTypes)

        # Update field 'Indirect' to equal 'True'
        with arcpy.da.UpdateCursor(Indirect_Impact_Area,
                                   fieldsToAdd) as cursor:
            for row in cursor:
                row[0] = "True"
                cursor.updateRow(row)

        if Map_Units_Provided:
            # Merge with Credit_Project_Boundary
            fileList = [Map_Units_Provided, Indirect_Impact_Area]
            out_name = "in_memory/Credit_Project_Boundary"
            Project_Area = arcpy.Union_analysis(fileList, out_name)
        else:
            Project_Area = Indirect_Impact_Area
                
        # Eliminate areas of non-habitat to create Credit_Project_Area
        out_name = CREDIT_PROJECT_AREA
        habitat_bounds = ccsStandard.HabitatBounds
        Credit_Project_Area = ccslib.EliminateNonHabitat(
            Project_Area, out_name, habitat_bounds
            )

    # Update message
    arcpy.AddMessage("Copying Credit_Project_Area as shapefile into project"
                     " folder")

    # Export feature class to shapefile in project folder so it can be sent to
    # NDOW for Dist_Lek layer
    arcpy.FeatureClassToShapefile_conversion(Credit_Project_Area,
                                             Project_Folder)

    # Update message
    arcpy.AddMessage("Creating Analysis Area")

    # Create Analysis Area
    out_name = ANALYSIS_AREA
    Analysis_Area = ccslib.CreateAnalysisArea(Credit_Project_Area,
                                              AnthroAttributeTable,
                                              out_name)

    # Add Analysis_Area to map
    layerFile = ccsStandard.getLayerFile("Analysis_Area.lyr")
    ccslib.AddToMap(Analysis_Area, layerFile, zoom_to=True)

    # Update message
    arcpy.AddMessage("Clipping all anthropogenic features to Analysis Area "
                     "and adding templates for digitizing new anthropogenic "
                     "features")

    # Clip all provided anthropogenic feature layers and add to map
    clip_features = Analysis_Area
    anthroFeaturePath = ccsStandard.AnthroFeaturePath
    ccslib.ClipAnthroFeaturesCredit(clip_features, anthroFeaturePath)
    featureList = arcpy.ListFeatureClasses("Anthro_*_Clip")

    # If the project proposes to modify anthropogenic features,
    # add a 'Subtype_As_Modified" field
    if includes_anthro_mod:
        fieldsToAdd = ["Subtype_As_Modified"]
        fieldTypes = ["TEXT"]
        for feature in featureList:
            ccslib.AddFields(feature, fieldsToAdd, fieldTypes)
            # Apply domains
            field = fieldsToAdd[0]
            domainName = feature[7:-5] + "_Subtypes"
            try:
                arcpy.AssignDomainToField_management(feature, field, domainName)
            except arcpy.ExecuteError:
                arcpy.AddMessage(domainName + " not updated. Use caution "
                                 "when populating attribute field")
            # Copy current subtype to Subtype as Modified field
            arcpy.CalculateField_management(feature, field, "!Subtype!",
                                            "PYTHON_9.3")

    # Add each feature to map for editing
    for feature in featureList:
        ccslib.AddAnthroToMap(workspace, feature)

    # Clean up
    arcpy.Delete_management("in_memory")

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
