"""
Name:     CreditTool_3.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better;
          Spatial Analyst extension

The provided Analysis_Area feature class is used to derive the workspace.
Requires Map_Units and Analysis_Area feature classes created by Credit Tool 2.
When re-run on the same project, edits to the Map Units layer made since
Credit Tool 2 was run will not be overwritten.

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
    importlib.reload(ccslib) #ensures up-to-date hqtlib runs on arcpro


def main():
    # GET PARAMETER VALUES
    Analysis_Area = arcpy.GetParameterAsText(0)
    Dist_Lek = arcpy.GetParameterAsText(1)
    Current_Anthro_Features_Provided = arcpy.GetParameterAsText(2)  # optional
    Project_Folder = arcpy.GetParameterAsText(3)
    Project_Name = arcpy.GetParameterAsText(4)  # optional

    # DEFINE DIRECTORIES & PATH NAMES FOR FOLDERS & GBDs
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

    # DEFINE GLOBAL VARIABLES
    AnthroAttributeTable = ccsStandard.AnthroAttributeTable
    emptyRaster = ccsStandard.EmptyRaster
    inputDataPath = ccsStandard.InputDataPath
    # Filenames for feature classes or rasters used by this script
    MAP_UNITS = "Map_Units"
    ANALYSIS_AREA = "Analysis_Area"  # provided
    CURRENT_ANTHRO_FEATURES = "Current_Anthro_Features"
    CREDIT_PROJECT_AREA = "Credit_Project_Area"
    PROPOSED_MODIFIED_FEATURES = "Proposed_Modified_Features"
    # Filenames for feature classes or rasters created by this script
    CURRENT_ANTHRO_DISTURBANCE = "Current_Anthro_Disturbance"
    PROJECTED_ANTHRO_DISTURBANCE = "Projected_Anthro_Disturbance"
    MAP_UNITS_DISSOLVE = "Map_Units_Dissolve"
    CURRENT_MGMT_CAT = "Current_Mgmt_Cat"
    CURRENT_WMZ = "Current_WMZ"
    CURRENT_PMU = "Current_PMU"
    CURRENT_PRECIP = "Current_Precip"

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check out Spatial Analyst extension
    ccslib.CheckOutSpatialAnalyst()

    # Check Analysis_Area
    feature = Analysis_Area
    expected_fcs = [MAP_UNITS, ANALYSIS_AREA, CREDIT_PROJECT_AREA]
    ccslib.CheckPolygonInput(feature, expected_fcs=expected_fcs)

    # Set up flag for projects that propose to modify anthro features
    includes_anthro_mod = False

    # Check for existence of 'Proposed_Modified_Features'
    if arcpy.Exists(PROPOSED_MODIFIED_FEATURES):
        # Update flag
        includes_anthro_mod = True

    # Copy Dist_Lek to geodatabase

    # Create Current_Anthro_Features layer, or copy provided into geodatabase
    if Current_Anthro_Features_Provided:
        # Clear selection, if present
        ccslib.ClearSelectedFeatures(Current_Anthro_Features_Provided)

        # Check Current_Anthro_Features
        feature = Current_Anthro_Features_Provided
        required_fields = ["Type", "Subtype"]
        no_null_fields = None
        expected_fcs = None
        ccslib.CheckPolygonInput(feature, required_fields,
                                 expected_fcs, no_null_fields)

        # Update message
        arcpy.AddMessage("Copying Current_Anthro_Features to project "
                         "geodatabase")

        # Copy Current_Anthro_Features to geodatabase
        provided_input = Current_Anthro_Features_Provided
        parameter_name = CURRENT_ANTHRO_FEATURES
        preserve_existing = True
        Current_Anthro_Features = ccslib.AdoptParameter(
            provided_input, parameter_name, preserve_existing
            )

    else:
        # Update message
        arcpy.AddMessage("Merging all clipped anthropogenic features to "
                         "create the Current_Anthro_Features layer")

        # Merge features (selecting only polygon features)
        fileList = arcpy.ListFeatureClasses("Anthro*Clip",
                                            feature_type="Polygon")
        out_name = CURRENT_ANTHRO_FEATURES
        Current_Anthro_Features = ccslib.MergeFeatures(fileList, out_name)

    # Simplify fields
    allowable_fields = ["Type", "Subtype", "Feature", "Subtype_As_Modified"]
    ccslib.SimplifyFields(Current_Anthro_Features, allowable_fields)

    # Remove subtypes from Current_Anthro_Features
    feature = Current_Anthro_Features
    try:
        subtypes = arcpy.da.ListSubtypes(feature)
        for subtype in subtypes:
            arcpy.RemoveSubtype_management(feature, subtype)
            arcpy.AddMessage("Subtype removed")
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not remove subtypes from "
                         "Current_Anthro_Features")

    # Add Domains for Type and Subtype
    arcpy.RemoveDomainFromField_management(feature, "Type")
    try:
        domainName = "Type"
        arcpy.CreateDomain_management(workspace, domainName,
                                      "Valid " + domainName + "s",
                                      "TEXT", "CODED")
        typeList = [row[0] for row in arcpy.da.SearchCursor(
                        AnthroAttributeTable, "Type")]
        for code in typeList:
            arcpy.AddCodedValueToDomain_management(workspace, domainName,
                                                   code, code)
    except arcpy.ExecuteError:
        arcpy.AddMessage("Could not add domains for "
                         "Current_Anthro_Features")

    arcpy.AssignDomainToField_management(feature, "Type", "Type")

    arcpy.RemoveDomainFromField_management(feature, "Subtype")
    arcpy.TableToDomain_management(AnthroAttributeTable,
                                   "Subtype", "Subtype", workspace,
                                   "Subtype", "Valid anthropogenic subtypes",
                                   "REPLACE")
    arcpy.AssignDomainToField_management(feature, "Subtype", "Subtype")

    # Update Message
    arcpy.AddMessage("Calculating Current Anthropogenic Disturbance")

    # Calculate Current_Anthro_Disturbance
    extent_fc = Analysis_Area
    anthro_features = Current_Anthro_Features
    term = ccsStandard.CreditTerms[0]
    Current_Anthro_Disturbance = ccslib.CalcAnthroDist(
        extent_fc, anthro_features, emptyRaster, AnthroAttributeTable, term
        )
    Current_Anthro_Disturbance.save(CURRENT_ANTHRO_DISTURBANCE)

    # Update message
    arcpy.AddMessage("Current_Anthro_Disturbance Calculated")

    # If the project proposes to modify existing anthropogenic features,
    # calculate post-project anthropogenic disturbance (uplift)
    if includes_anthro_mod:
        # Calculate uplift
        extent_fc = Analysis_Area
        anthro_features = Current_Anthro_Features
        term = ccsStandard.CreditTerms[1]
        field = "Subtype_As_Modified"
        Projected_Anthro_Disturbance = ccslib.CalcAnthroDist(
            extent_fc, anthro_features, emptyRaster, AnthroAttributeTable,
            term, field
            )
        Projected_Anthro_Disturbance.save(PROJECTED_ANTHRO_DISTURBANCE)

        # Update message
        arcpy.AddMessage("Projected_Anthro_Disturbance Calculated")
        arcpy.AddMessage("Creating pre-defined map units of PJ")

        Map_Units = MAP_UNITS
        
        if len(arcpy.ListFields(Map_Units, "Meadow")) == 0:
            # Create pre-defined map units for Wet Meadow
            # Update message
            arcpy.AddMessage("Creating pre-defined map units of Wet Meadows")

            # Intersect the Map_Units layer with the NV Wet Meadows layer
            in_feature = ccsStandard.Wet_Meadows
            field_name = "Meadow"
            na_value = "No Meadow"
            ccslib.CreatePreDefinedMapUnits(Map_Units, in_feature, field_name, 
                                            na_value)
            
            # Create Domain for Meadow attributes
            featureList = [Map_Units]
            domainName = "Meadow"
            codeList = ["No Meadow", "Altered", "Unaltered"]
            ccslib.AddCodedTextDomain(featureList, workspace, domainName, codeList,
                                    assign_default=True)        

        if len(arcpy.ListFields(Map_Units, "Conifer_Phase")) == 0:
            # Create pre-defined map units for PJ
            # Intersect the Map_Units layer with the PJ layer
            in_feature = ccsStandard.PJ_Phases
            field_name = "Conifer_Phase"
            ccslib.CreatePreDefinedMapUnits(Map_Units, in_feature, field_name)

            # Remove unwanted fields from Map Units feature class
            allowable_fields = ["Conifer_Phase",
                                "Map_Unit_ID", "Map_Unit_Name",
                                "Meadow", "Notes", "Indirect"]
            ccslib.SimplifyFields(Map_Units, allowable_fields)

        # Update message
        arcpy.AddMessage("Merging indirect benefits area and map units layer")

        # Combine the Map Units layer and Indirect Impact Layer
        indirect_benefit_area = CREDIT_PROJECT_AREA
        mgmt_map_units = Map_Units
        Map_Units = ccslib.AddIndirectBenefitArea(indirect_benefit_area,
                                                  mgmt_map_units)

        # Add Map Units layer to map document
        layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
        ccslib.AddToMap(Map_Units, layerFile)

    else:
        # Add Indirect field to Map Units layer and populate with False
        # Add field "Indirect"
        feature = MAP_UNITS
        fieldsToAdd = ["Indirect"]
        fieldTypes = ["TEXT"]
        ccslib.AddFields(feature, fieldsToAdd, fieldTypes)

        # Update field to equal "False"
        with arcpy.da.UpdateCursor(feature,
                                   fieldsToAdd) as cursor:
            for row in cursor:
                row[0] = "False"
                cursor.updateRow(row)

    # Calculate local scale modifiers for Current condition
    extent_fc = Analysis_Area
    anthro_disturbance = CURRENT_ANTHRO_DISTURBANCE
    term = ccsStandard.CreditTerms[0]
    ccslib.CalcModifiers(extent_fc, inputDataPath, Dist_Lek, anthro_disturbance, term)

    # Calculate local scale modifiers for Projected condition
    # Determine which anthropogenic disturbance raster to use
    extent_fc = Analysis_Area
    if arcpy.Exists(PROJECTED_ANTHRO_DISTURBANCE):
        anthro_disturbance = PROJECTED_ANTHRO_DISTURBANCE
    else:
        anthro_disturbance = CURRENT_ANTHRO_DISTURBANCE
    term = ccsStandard.CreditTerms[1]
    ccslib.CalcModifiers(extent_fc, inputDataPath, Dist_Lek, anthro_disturbance,
                         term, PJ_removal=True)

    # Update message
    arcpy.AddMessage("Dissolving all multi-part map units to create "
                     "Map_Units_Dissolve")

    # Dissolve Map Units
    allowable_fields = ["Map_Unit_ID", "Map_Unit_Name", "Meadow", "Conifer_Phase",
                        "Indirect"]
    out_name = MAP_UNITS_DISSOLVE
    anthro_features = Current_Anthro_Features
    Map_Units_Dissolve = ccslib.DissolveMapUnits(MAP_UNITS, allowable_fields,
                                                 out_name, anthro_features)

    # Update message
    arcpy.AddMessage("Adding Map_Units_Dissolve to map")

    # Add layer to map document
    feature = Map_Units_Dissolve
    layerFile = ccsStandard.getLayerFile("Map_Units.lyr")
    ccslib.AddToMap(feature, layerFile, zoom_to=True)

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
    arcpy.AddMessage("Evaluating WAFWA Management Zone")

    # Calculate Proportion in each map unit in each WAFWA Zone
    in_feature = os.path.join(inputDataPath, "NV_WAFWA")
    out_feature_class = CURRENT_WMZ
    field_name = "WMZ_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Update message
    arcpy.AddMessage("Evaluating Priority Management Unit")

    # Calculate Proportion in each map unit in each PMU
    in_feature = os.path.join(inputDataPath, "NV_PMU")
    out_feature_class = CURRENT_PMU
    field_name = "PMU_Proportion"
    ccslib.CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                          field_name)
    prop_fcs.append(out_feature_class)

    # Delete unnecessary fields in proportion feature classes
    allowable_fields = ["Map_Unit_ID", "Management",
                        "Mgmt_zone", "PMU_NAME", "Precip", "Mgmt_Proportion",
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

    # Update message
    arcpy.AddMessage("Calculating PJ cover per map unit")

    # Calculate the average pinon-juniper cover per map unit
    inZoneData = Map_Units_Dissolve
    inValueRaster = os.path.join(inputDataPath, "PJ_Cover")
    zoneField = "Map_Unit_ID"
    outTable = "ZonalStats_PJCover"
    ccslib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

    # Join the zonal statistic to the Map Units Dissolve table
    fieldName = "PJ_Cover"
    ccslib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

    # Calculate the average seasonal modifier values per map unit and
    # join to Map_Unit_Dissolve table
    terms = ccsStandard.CreditTerms
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

    # Calculate impact intensity for credit project
    try:
        ccslib.calcCreditBenefit(inputDataPath, includes_anthro_mod)

        # Add credit project quality to map
        layerFile = ccsStandard.getLayerFile("Credit_Project_Benefit.lyr")
        ccslib.AddToMap("Credit_Quality", layerFile, zoom_to=True)
    except:
        pass
    
    # Remove uplift modifier for map units that do not qualify
    # Select map units of Indirect if project involves anthro
    # feature modification
    if includes_anthro_mod:
        feature = MAP_UNITS_DISSOLVE
        arcpy.MakeFeatureLayer_management(feature, "lyr")
        where_clause = """({} = '{}') AND ({} <> {} OR {} <> {} OR {} <> {})""".format(
            arcpy.AddFieldDelimiters(feature, "Indirect"), "True",
            arcpy.AddFieldDelimiters(feature, "Projected_Breed"),
            arcpy.AddFieldDelimiters(feature, "Current_Breed"),
            arcpy.AddFieldDelimiters(feature, "Projected_LBR"),
            arcpy.AddFieldDelimiters(feature, "Current_LBR"),
            arcpy.AddFieldDelimiters(feature, "Projected_Winter"),
            arcpy.AddFieldDelimiters(feature, "Current_Winter"))
        arcpy.SelectLayerByAttribute_management(feature, "NEW_SELECTION",
                                                where_clause)
        test = arcpy.GetCount_management(feature)
        count = int(test.getOutput(0))
        if count > 0:
            # Update message
            arcpy.AddMessage("Confirming removal of PJ cover credits meet "
                             "eligibility criteria (if applicable)")

            # Substitute Projected_Anthro_Disturbance if it exists
            extent_fc = Analysis_Area
            if arcpy.Exists(PROJECTED_ANTHRO_DISTURBANCE):
                anthroDisturbance = PROJECTED_ANTHRO_DISTURBANCE
            else:
                anthroDisturbance = CURRENT_ANTHRO_DISTURBANCE

            # Repeat calculation of modifiers w/o PJ_uplift
            term = ccsStandard.CreditTerms[1]
            ccslib.CalcModifiers(extent_fc, inputDataPath, Dist_Lek,
                                 anthroDisturbance, term, PJ_removal=False,
                                 suffix="noPJ")

            # Repeat joins to table
            for season in seasons:
                # Calculate zonal statistics for each map unit
                inZoneData = Map_Units_Dissolve
                inValueRaster = term + "_Local_" + season + "_noPJ"
                zoneField = "Map_Unit_ID"
                outTable = "ZonalStats_" + term + season
                ccslib.CalcZonalStats(inZoneData, zoneField, inValueRaster, outTable)

                # Join the zonal statistic to the Map Units Dissolve table
                fieldName = term + "_" + season + "_noPJ"
                ccslib.JoinMeanToTable(inZoneData, outTable, zoneField, fieldName)

                # Overwrite Projected seasonal local scale scores
                overwrite_field = ccsStandard.CreditTerms[1] + "_" + season
                with arcpy.da.UpdateCursor(feature,
                                           [fieldName, overwrite_field]) as cursor:
                    for row in cursor:
                        row[1] = row[0]
                        cursor.updateRow(row)

                # Clean up
                arcpy.DeleteField_management(feature, fieldName)

        # Clean up
        arcpy.SelectLayerByAttribute_management(feature, "CLEAR_SELECTION")
        arcpy.Delete_management("lyr")

    # Add transect field to Map_Units_Dissolve
    fields = ["Transects"]
    fieldTypes = ["SHORT"]
    ccslib.AddFields(Map_Units_Dissolve, fields, fieldTypes)

    # Export data to Excel
    input_Tables = [MAP_UNITS_DISSOLVE, CURRENT_MGMT_CAT,
                    CURRENT_WMZ, CURRENT_PMU, CURRENT_PRECIP]
    for table in input_Tables:
        ccslib.ExportToExcel(table, Project_Folder, Project_Name)

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
