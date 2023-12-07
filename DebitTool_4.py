"""
Name:     DebitTool_4.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 23, 2023
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst Extension

Path to the project's workspace is derived from the Analysis_Area
feature class provided by the user.
Requires Analysis_Area created by Debit Tool 3 and Space Use Index 
provided by the SETT.

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
    Analysis_Area = arcpy.GetParameterAsText(0)
    Current_Anthro_Features_Provided = arcpy.GetParameterAsText(1)  # optional
    Space_Use_Index = arcpy.GetParameterAsText(2)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    # Construct pathname to workspace
    workspace = arcpy.Describe(Analysis_Area).path
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
    emptyRaster = ccsStandard.EmptyRaster
    inputDataPath = ccsStandard.InputDataPath
    
    # Filenames for feature classes and raster used by this script
    ELIGIBLE_PROPOSED_FEATURES = "Proposed_Surface_Disturbance_Eligible"
    DEBIT_PROJECT_AREA = "Debit_Project_Area"

    # Filenames for feature classes and rasters created by this script
    CURRENT_ANTHRO_FEATURES = "Current_Anthro_Features"
    PROJECTED_ANTHRO_FEATURES = "Projected_Anthro_Features"
    PERMANENT_ANTHRO_FEATURES = "Permanent_Anthro_Features"
    CURRENT_ANTHRO_DISTURBANCE = "Current_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE = "Projected_Anthro_Disturbance"
    PERMANENT_ANTHRO_DISTURBANCE = "Permanent_Anthro_Disturbance"
    DIST_LEK = "Dist_Lek"
    MAP_UNITS = "Map_Units"    

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check tool version
    ccslib.CheckToolVersion()
    
    # Check out Spatial Analyst extension
    ccslib.CheckOutSpatialAnalyst()

    # Check Analysis_Area
    expected_fcs = [ELIGIBLE_PROPOSED_FEATURES, DEBIT_PROJECT_AREA]
    ccslib.CheckPolygonInput(Analysis_Area, expected_fcs=expected_fcs)

    # Create Current_Anthro_Features layer, or copy provided into geodatabase
    if Current_Anthro_Features_Provided:
        # Clear selection, if present
        ccslib.ClearSelectedFeatures(Current_Anthro_Features_Provided)

        # Check Current_Anthro_Features
        required_fields = ["Type", "Subtype", "Overlap_Status", "Returned", 
                           "Subtype_As_Modified"]
        no_null_fields = None
        expected_fcs = None
        ccslib.CheckPolygonInput(Current_Anthro_Features_Provided,
                                 required_fields,
                                 expected_fcs, no_null_fields)

        # Update message
        arcpy.AddMessage("Copying Current_Anthro_Features to project "
                         "geodatabase")

        # Copy Current_Anthro_Features to geodatabase
        provided_input = Current_Anthro_Features_Provided
        parameter_name = CURRENT_ANTHRO_FEATURES
        Current_Anthro_Features = ccslib.AdoptParameter(
            provided_input, parameter_name, preserve_existing=True
            )

    else:
        # Update message
        arcpy.AddMessage("Merging all clipped anthropogenic features to "
                         "create the Current_Anthro_Features layer")

        # Simplify fields. critical to remove any fields named
        # 'Surface_Disturbance' in Current_Anthro_Features before joining
        # Proposed_Surface_Disturbance to create Projected_Anthro_Features
        allowable_fields = ["Type", "Subtype", "SubtypeID", 
                            "Subtype_As_Modified", "Overlap_Status", 
                            "Returned", "Feature", "Featre"]
    
        
        fileList = arcpy.ListFeatureClasses("Anthro*Clip",
                                            feature_type="Polygon")
        for file in fileList:
            ccslib.SimplifyFields(file, allowable_fields)
        
        out_name = CURRENT_ANTHRO_FEATURES
        # Merge features (selecting only polygon features)
        Current_Anthro_Features = ccslib.MergeFeatures(fileList, out_name)

    
    # ccslib.SimplifyFields(Current_Anthro_Features, allowable_fields)
    

    # Remove subtypes from Current_Anthro_Features
    feature = Current_Anthro_Features
    subtypes = arcpy.da.ListSubtypes(feature)
    try:
        if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
            pass
        else:
            for subtype in subtypes:
                arcpy.RemoveSubtype_management(feature, subtype)
                arcpy.AddMessage("Subtype removed")
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not remove Subtype Domain from "
                        "Current_Anthro_Features")

    # Add Domains for Type and Subtype
    try:
        arcpy.RemoveDomainFromField_management(feature, "Type")
        arcpy.AssignDomainToField_management(feature, "Type", "Type")
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not update Type Domain for "
                         "Current_Anthro_Features")
    try:
        arcpy.RemoveDomainFromField_management(feature, "Subtype")
        arcpy.AssignDomainToField_management(feature, "Subtype", "Subtype")
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not update Subtype Domain for "
                         "Current_Anthro_Features")
    try:
        arcpy.RemoveDomainFromField_management(feature, "Subtype_As_Modified")
        arcpy.AssignDomainToField_management(feature, "Subtype", "Subtype")
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not update Type Domain for "
                         "Current_Anthro_Features")

    # Calculate Current_Anthro_Disturbance
    extent_fc = Analysis_Area
    anthro_features = Current_Anthro_Features
    term = ccsStandard.DebitTerms[0]
    Current_Anthro_Disturbance = ccslib.CalcAnthroDist(
        extent_fc, anthro_features, emptyRaster,
        AnthroAttributeTable, term
        )
    Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE)

    # Update message
    arcpy.AddMessage("Current_Anthro_Disturbance Calculated")
    arcpy.AddMessage("Removing any anthropogenic features from the "
                     "Current_Anthro_Features layer that will be "
                     "replaced or upgraded from one subtype to another "
                     "by the debit project")

    # Calculate post-project anthropogenic disturbance
    mod_field = "Overlap_Status"
    removed_code = "Removed"
    subtype_mod_field = "Subtype_As_Modified"
    out_name = PROJECTED_ANTHRO_FEATURES
    Projected_Anthro_Features = ccslib.SelectProposed(
        Current_Anthro_Features, ELIGIBLE_PROPOSED_FEATURES,
        mod_field, removed_code, subtype_mod_field,
        out_name
    )
    
    # Simplify fields (do not remove Surface Disturbance or Reclassified
    # MEMORY ISSUE SEE https://www.mindland.com/solving-the-arcpy-dissolve/
    # Subtype field for use in SelectPermanent())
    allowable_fields = ["Type", "Subtype", "SubtypeID",
                        "Overlap_Status", "Returned",
                        "Subtype_As_Modified"
                        "Surface_Disturbance",
                        "Reclassified_Subtype", 
                        "Feature", "Featre"]
    ccslib.SimplifyFields(Projected_Anthro_Features, allowable_fields)

    # Calculate Projected_Anthro_Disturbance
    extent_fc = Analysis_Area
    anthro_features = Projected_Anthro_Features
    term = ccsStandard.DebitTerms[1]
    Projected_Anthro_Disturbance = ccslib.CalcAnthroDist(
        extent_fc, anthro_features, emptyRaster,
        AnthroAttributeTable, term
        )
    Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE)

    # Update message
    arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")
    arcpy.AddMessage("Creating Permanent Anthro Features and calculating "
                     "disturbance")

    # Calculate permanent anthropogenic disturbance
    # Select permanent anthropogenic features from Projected Anthro Features
    mod_field = "Overlap_Status"
    returned_field = "Returned"
    subtype_mod_field = "Subtype_As_Modified"
    duration_field = "Surface_Disturbance"
    permanent_codes = ["Term_Reclassified", "Permanent"]
    reclass_code = "Term_Reclassified"
    reclass_subtype_field = "Reclassified_Subtype"
    out_name = PERMANENT_ANTHRO_FEATURES
    Permanent_Anthro_Features = ccslib.SelectPermanent(
        Current_Anthro_Features, ELIGIBLE_PROPOSED_FEATURES,
        mod_field, returned_field, subtype_mod_field,
        duration_field, permanent_codes,
        reclass_code, reclass_subtype_field, out_name
        )
    
    # Simplify fields
    # MEMORY ISSUE SEE https://www.mindland.com/solving-the-arcpy-dissolve/
    allowable_fields = ["Type", "Subtype", "SubtypeID",
                        "Overlap_Status", "Returned",
                        "Subtype_As_Modified"
                        "Surface_Disturbance",
                        "Reclassified_Subtype",
                        "Feature", "Featre"]
    ccslib.SimplifyFields(Permanent_Anthro_Features, allowable_fields)

    # Calculate Permanent Anthro Disturbance
    extent_fc = Analysis_Area
    anthro_features = Permanent_Anthro_Features
    term = ccsStandard.DebitTerms[2]
    Permanent_Anthro_Disturbance = ccslib.CalcAnthroDist(
        extent_fc, anthro_features, emptyRaster, AnthroAttributeTable, term
        )
    Permanent_Anthro_Disturbance.save(PERMANENT_ANTHRO_DISTURBANCE)

    # Update message
    arcpy.AddMessage("Permanent_Anthro_Disturbance Calculated")

    # Update message
    arcpy.AddMessage("Calculating Distance to Lek")

    # Calculate Dist_Lek layer and save
    remap_table = ccsStandard.SUIClass
    Dist_Lek = ccslib.CalcDistLek(Space_Use_Index, remap_table)
    Dist_Lek.save(DIST_LEK)

    # Calculate local scale modifiers for Current, Projected, and
    # Permanent condition
    extent_fc = Analysis_Area
    terms = ccsStandard.DebitTerms
    for term in terms:
        anthro_disturbance = term + "_Anthro_Disturbance"
        ccslib.CalcModifiers(extent_fc, inputDataPath, Dist_Lek,
                             anthro_disturbance, term, Space_Use_Index)

    # Calculate impact intensity for debit project
    try:
        ccslib.calcDebitImpact(inputDataPath)

        # Add debit project impact to map
        layerFile = ccsStandard.getLayerFile("Debit_Project_Impact.lyr")
        ccslib.AddToMap("Debit_Project_Impact" ,layerFile, zoom_to=True)
    except:
        pass

    # Update message
    arcpy.AddMessage("Creating Map Units layer")

    # Create Map_Units layer
    Project_Area = DEBIT_PROJECT_AREA
    out_name = MAP_UNITS
    Map_Units = ccslib.CreateMapUnits(Project_Area, out_name)
    
    # Update message
    arcpy.AddMessage("Creating pre-defined map units of Wet Meadows")

    # Intersect the Map_Units layer with the NV Wet Meadows layer
    in_feature = ccsStandard.Wet_Meadows
    field_name = "Meadow"
    na_value = "No Meadow"
    ccslib.CreatePreDefinedMapUnits(Map_Units, in_feature, field_name, 
                                    na_value)

    # Update message
    arcpy.AddMessage("Creating pre-defined map units of PJ")

    # Intersect the Map_Units layer with the Phase III PJ layer
    in_feature = ccsStandard.PJ_Phase_III
    field_name = "Conifer_Phase"
    ccslib.CreatePreDefinedMapUnits(Map_Units, in_feature, field_name)

    # Update message
    arcpy.AddMessage("Creating pre-defined map units of proposed surface "
                     "disturbance")

    # Intersect the Map_Units layer with the proposed surface disturbance
    in_features = ELIGIBLE_PROPOSED_FEATURES
    ccslib.CreatePreDefinedMapUnits(Map_Units, in_features, field_name)

    # Remove unwanted fields from Map Units feature class
    allowable_fields = ["Disturbance_Type",
                        "BROTEC", "Conifer_Phase", "Meadow"]
    ccslib.SimplifyFields(Map_Units, allowable_fields)

    # Populate empty attributes with Indirect
    feature = Map_Units
    fieldName = "Disturbance_Type"
    where_clause = "{} = ''".format(arcpy.AddFieldDelimiters(feature,
                                                             fieldName))
    with arcpy.da.UpdateCursor(feature, fieldName,
                               where_clause) as cursor:
        for row in cursor:
            row[0] = "Indirect"
            cursor.updateRow(row)

    # Add Map_Units to map
    layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
    ccslib.AddToMap(Map_Units, layerFile)

    # Add fields Map_Unit_ID, Map_Unit_Name, and Precip to map unit
    input_feature = Map_Units
    fields = ["Map_Unit_ID", "Map_Unit_Name", "Notes"]
    fieldTypes = ["SHORT", "TEXT", "TEXT"]
    ccslib.AddFields(input_feature, fields, fieldTypes, copy_existing=True)
        
    # Add Domains to Map_Units layer
    # Create Domain for Map_Unit_ID attributes
    input_feature = Map_Units
    domainName = "Map_Unit_ID"
    range_low = 0
    range_high = 10000
    ccslib.AddRangeDomain(input_feature, workspace, domainName,
                          range_low, range_high)

    # Create Domain for Meadow attributes
    featureList = [Map_Units]
    domainName = "Meadow"
    codeList = ["Altered", "Unaltered", "No Meadow"]
    ccslib.AddCodedTextDomain(featureList, workspace, domainName, codeList)

    # Clean up
    arcpy.Delete_management("in_memory")

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
