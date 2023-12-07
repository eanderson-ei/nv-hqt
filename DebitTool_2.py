"""
Name:     DebitTool_2.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better

Path to the project's workspace is derived from the Proposed_Surface_Disturbance
feature class provided by the user.

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
import os
import sys
import gc
import ccslib

if arcpy.ListInstallations()[0] == 'arcgispro':  # switch
    import importlib
    importlib.reload(ccslib)


def main():
    # GET PARAMETER VALUES
    Proposed_Surface_Disturbance_Provided = arcpy.GetParameterAsText(0)
    Proposed_Modified_Features_Provided = arcpy.GetParameterAsText(1)  # optional
    Project_Folder = arcpy.GetParameterAsText(2)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    arcpy.AddMessage("Python version: " + sys.version)
    # Construct pathname to workspace
    workspace = arcpy.Describe(Proposed_Surface_Disturbance_Provided).path
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
        arcpy.CreateFolder_management(arcpy.Describe(workspace).path, 'scratch')
    arcpy.env.scratchWorkspace = scratch_folder
    # Overwrite outputs
    arcpy.env.overwriteOutput = True

    # DEFINE VARIABLES FOR INPUT DATA
    AnthroAttributeTable = ccsStandard.AnthroAttributeTable
    habitat_bounds = ccsStandard.HabitatBounds
    public_land = ccsStandard.Public
    
    # Filenames for feature classes or rasters used by this script
    PROPOSED_SURFACE_DISTURBANCE_DEBITS = "Proposed_Surface_Disturbance_Debits"
    # Filenames for feature classes or rasters created by this script
    ELIGIBLE_PROPOSED_FEATURES = "Proposed_Surface_Disturbance_Eligible"
    ANALYSIS_AREA = "Analysis_Area"
    DEBIT_PROJECT_AREA = "Debit_Project_Area"
    INDIRECT_IMPACT_AREA = "Indirect_Impact_Area"
    INDIRECT_BENEFIT_AREA = "Indirect_Benefit_Area"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check tool version
    ccslib.CheckToolVersion()
    
    # Check for proposed modified features
    if not Proposed_Modified_Features_Provided:
        # Ensure Proposed_Modified_Features does not exist
        if arcpy.Exists("Proposed_Modified_Features"):
            arcpy.AddError("ERROR:: A 'Proposed_Modified_Features' layer "
                           "was detected in the project's geodatabase. "
                           "Provide the 'Proposed_Modified_Features' layer "
                           "and re-run Debit Tool 2.")
            sys.exit(0)

    # Clear selection, if present
    ccslib.ClearSelectedFeatures(Proposed_Surface_Disturbance_Provided)

    # Check Proposed_Surface_Disturbance
    feature = Proposed_Surface_Disturbance_Provided
    required_fields = ["Type", "Subtype", "Surface_Disturbance"]
    no_null_fields = required_fields
    expected_fcs = None
    ccslib.CheckPolygonInput(feature, required_fields,
                             expected_fcs, no_null_fields)

    # Update Proposed_Surface_Disturbance layer with provided layer
    provided_input = Proposed_Surface_Disturbance_Provided
    parameter_name = PROPOSED_SURFACE_DISTURBANCE_DEBITS
    Proposed_Surface_Disturbance_Debits = ccslib.AdoptParameter(
        provided_input, parameter_name, preserve_existing=False
        )

    # Replace Proposed_Surface_Disturbance_Debits layer on map
    layerFile = ccsStandard.getLayerFile("SurfaceDisturbance.lyr")
    ccslib.AddToMap(Proposed_Surface_Disturbance_Debits, layerFile)
    
    # Clip the Proposed Surface Disturbance to Public Lands
    input_features = PROPOSED_SURFACE_DISTURBANCE_DEBITS
    clip_features = public_land
    out_name = ELIGIBLE_PROPOSED_FEATURES
    Proposed_Surface_Disturbance = arcpy.Clip_analysis(input_features,
                                                       clip_features,
                                                       out_name)
    
    # Exit if no features on public land exist
    test = arcpy.GetCount_management(Proposed_Surface_Disturbance)
    count = int(test.getOutput(0))

    if count < 1:
        arcpy.AddWarning(
            """
            There are no proposed features located on public lands.\n
            Therefore, this project does not require mitigation.\n
            Please confirm with the SETT.            
            """
        )
        sys.exit(0)
    
    # Add Surface_Disturbance_Eligible layer on map
    layerFile = ccsStandard.getLayerFile("SurfaceDisturbance.lyr")
    ccslib.AddToMap(Proposed_Surface_Disturbance, layerFile)

    # Add field for Disturbance_Type and populate. Values will be used in
    # Map_Units_Dissolve to identify map units of direct disturbance
    feature = Proposed_Surface_Disturbance
    fields = ["Disturbance_Type"]
    fieldTypes = ["TEXT"]
    ccslib.AddFields(feature, fields, fieldTypes)

    with arcpy.da.UpdateCursor(feature, ["Surface_Disturbance"] + fields) as cursor:
        for row in cursor:
            row[1] = "Direct_" + row[0]
            cursor.updateRow(row)

    # Update message
    arcpy.AddMessage("Creating the area of indirect impact")

    # Buffer proposed surface disturbance to create Indirect_Impact_Area
    in_data = Proposed_Surface_Disturbance
    out_name = INDIRECT_IMPACT_AREA
    Indirect_Impact_Area = ccslib.CreateIndirectImpactArea(
        in_data, AnthroAttributeTable, out_name
        )

    if Proposed_Modified_Features_Provided:
        # Clear selection, if present
        ccslib.ClearSelectedFeatures(Proposed_Modified_Features_Provided)

        # Check provided layer
        required_fields = ["Type", "Subtype"]
        no_null_fields = required_fields
        expected_fcs = None
        ccslib.CheckPolygonInput(Proposed_Modified_Features_Provided, required_fields,
                                 expected_fcs, no_null_fields)

        # Update Proposed_Modified_Features with provided layer and add to map
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

        # Create the Indirect_Impact_Area
        in_data = Proposed_Modified_Features
        out_name = INDIRECT_BENEFIT_AREA
        Indirect_Benefit_Area = ccslib.CreateIndirectImpactArea(
            in_data, AnthroAttributeTable, out_name
            )

        # Union the indirect benefit area and the indirect impact area
        in_features = [Indirect_Impact_Area, Indirect_Benefit_Area]
        out_name = "in_memory/Impact_Union"
        Impact_Union = arcpy.Union_analysis(in_features, out_name)

        # Dissolve the unioned indirect impact and benefit areas as
        # Indirect Impact Area
        in_features = Impact_Union
        out_feature_class = INDIRECT_IMPACT_AREA
        Indirect_Impact_Area = arcpy.Dissolve_management(in_features,
                                                         out_feature_class)

    # Update message
    arcpy.AddMessage("Determining project area - eliminating areas of non-"
                     "habitat from the Project Area")

    # Eliminate non-habitat
    project_area = Indirect_Impact_Area
    out_name = DEBIT_PROJECT_AREA
    Debit_Project_Area = ccslib.EliminateNonHabitat(
        project_area, out_name, habitat_bounds
        )

    # Update message
    arcpy.AddMessage("Copying Debit_Project_Area as shapefile into project "
                     "folder")

    # Export feature class to shapefile in project folder so it can be sent to
    # NDOW for Dist_Lek layer
    arcpy.FeatureClassToShapefile_conversion(Debit_Project_Area,
                                             Project_Folder)

    # Update message
    arcpy.AddMessage("Creating Analysis Area")

    # Create Analysis_Area
    out_name = ANALYSIS_AREA
    Analysis_Area = ccslib.CreateAnalysisArea(Debit_Project_Area,
                                              AnthroAttributeTable,
                                              out_name)

    # Add Analysis_Area to map
    layerFile = ccsStandard.getLayerFile("Analysis_Area.lyr")
    ccslib.AddToMap(Analysis_Area, layerFile, zoom_to=True)

    # Save map document and exit
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
