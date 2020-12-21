"""
Name:     DebitTool_3.py
Author:   Erik Anderson
Created:  May 5, 2017
Revised:  February 25, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better

Path to the project's workspace is derived from the 
Proposed_Surface_Disturbance_Eligible feature class provided by the user.

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
    Proposed_Surface_Disturbance_Eligible = arcpy.GetParameterAsText(0)

    # DEFINE DIRECTORIES
    # Get the pathname to this script
    scriptPath = sys.path[0]
    arcpy.AddMessage("Script folder: " + scriptPath)
    # Construct pathname to workspace
    workspace = arcpy.Describe(Proposed_Surface_Disturbance_Eligible).path
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
    
    # Filenames for feature classes or rasters used by this script
    ELIGIBLE_PROPOSED_FEATURES = "Proposed_Surface_Disturbance_Eligible"

    # Filenames for feature classes or rasters created by this script
    ANALYSIS_AREA = "Analysis_Area" 

    # ------------------------------------------------------------------------

    # FUNCTION CALLS
    # Check tool version
    ccslib.CheckToolVersion()
    
    # Clear selection, if present
    ccslib.ClearSelectedFeatures(Proposed_Surface_Disturbance_Eligible)

    # Check Proposed_Surface_Disturbance_Eligible
    feature = Proposed_Surface_Disturbance_Eligible
    required_fields = ["Type", "Subtype", "Surface_Disturbance"]
    no_null_fields = required_fields
    expected_fcs = None
    ccslib.CheckPolygonInput(feature, required_fields,
                             expected_fcs, no_null_fields)

    # Update Proposed_Surface_Disturbance_Elligible layer with provided layer
    provided_input = Proposed_Surface_Disturbance_Eligible
    parameter_name = ELIGIBLE_PROPOSED_FEATURES
    Proposed_Surface_Disturbance_Eligible = ccslib.AdoptParameter(
        provided_input, parameter_name, preserve_existing=False
        )

    # Replace Proposed_Surface_Disturbance_Elibible layer on map
    layerFile = ccsStandard.getLayerFile("SurfaceDisturbance.lyr")
    ccslib.AddToMap(Proposed_Surface_Disturbance_Eligible, layerFile)

    # Update message
    arcpy.AddMessage("Clipping all anthropogenic features to Analysis Area "
                     "and adding templates for digitizing new anthropogenic "
                     "features")

    # Clip all provided anthropogenic feature layers and add to map
    clip_features = ANALYSIS_AREA
    anthroFeaturePath = ccsStandard.AnthroFeaturePath
    proposed_anthro = Proposed_Surface_Disturbance_Eligible
    fieldsToAdd = ["Overlap_Status", "Returned", "Subtype_As_Modified"]
    fieldTypes = ["TEXT", "TEXT", "TEXT"]
    mod_field = fieldsToAdd[0]
    removed_code = "Removed"
    retained_code = "Retained"
    ccslib.ClipAnthroFeaturesDebit(clip_features, anthroFeaturePath,
                                   proposed_anthro, fieldsToAdd, fieldTypes,
                                   mod_field, removed_code, retained_code)

    # Apply domains for Overlap_Status field and populate default
    featureList = arcpy.ListFeatureClasses("Anthro_*_Clip")
    domain_name = fieldsToAdd[0]
    code_list = ["Retained", "Removed"]
    ccslib.AddCodedTextDomain(featureList, workspace, 
                              domain_name, code_list,
                              assign_default=True,
                              populate_default=True)
        
    # Apply domains for Returned field
    domain_name = fieldsToAdd[1]
    code_list = ["True", "False"]
    ccslib.AddCodedTextDomain(featureList, workspace, 
                              domain_name, code_list,
                              assign_default=True,
                              populate_default=True)
    
    # Add all Subtype anthro domains because ArcGIS doesn't transfer them 
    # consistently
    desc_c = arcpy.Describe(workspace)
    current_domains = desc_c.domains
    desc_w = arcpy.Describe(ccsStandard.AnthroFeaturePath)
    anthro_domains = desc_w.domains
    for domain_name in anthro_domains:
        if domain_name not in current_domains and "Subtype" in domain_name:
            source_workspace = ccsStandard.AnthroFeaturePath
            code_field = 'code'
            description_field = 'description'
            domain_table = arcpy.DomainToTable_management(
                source_workspace, domain_name, domain_name,
                code_field, description_field
            )
            arcpy.TableToDomain_management(domain_table, code_field,
                                           description_field, workspace,
                                           domain_name)
            arcpy.Delete_management(domain_table)
    
    # Apply domains for each anthro feature
    for feature in featureList:
        # Apply for each Subtype field
        field = "Subtype"
        domainName = feature[7:-5] + "_Subtypes"
        arcpy.AssignDomainToField_management(feature, field, domainName)
        subtypes = arcpy.da.ListSubtypes(feature)
        if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
            pass
        else:
            st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
            arcpy.AssignDomainToField_management(feature, field, domainName, 
                                                 st_codes)
        
        # Apply for each Subtype As Modified Field
        field = fieldsToAdd[-1]
        domainName = feature[7:-5] + "_Subtypes"
        arcpy.AssignDomainToField_management(feature, field, domainName)
        subtypes = arcpy.da.ListSubtypes(feature)
        if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
            pass
        else:                
            st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
            arcpy.AssignDomainToField_management(feature, field, domainName, 
                                                st_codes)
        
        # Copy current subtype to Subtype as Modified field
        arcpy.CalculateField_management(feature, field, "!Subtype!",
                                        "PYTHON_9.3")
    
    # Add each feature to map for editing
    for feature in featureList:
        ccslib.AddAnthroToMap(workspace, feature)

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
