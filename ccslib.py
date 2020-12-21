"""
Name:     ccslib.py
Author:   Erik Anderson
Created:  February 14, 2018
Revised:  May 6, 2019
Version:  Created using Python 2.7.10, Arc version 10.4.1
Requires: ArcGIS version 10.1 or later, Basic (ArcView) license or better
          Spatial Analyst extension

This library contains modules required to run the Nevada CCS HQT.

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
# Update the date after which this script will no longer be valid.
# Use format "MM/DD/YYYY"
# Use after this date will result in a warning to the user.
# See function CheckToolVersion() below.
warn_date = None

# Import system modules
import arcpy
import os
import sys
import random
import numpy as np
from arcpy.sa import EucDistance, Con, IsNull, Power, Raster, CellStatistics

# ----------------------------------------------------------------------------

# CLASSES


class ccsStandard:

    # Filenames and data directories
    _data_folder = "ToolData"
    _input_data = "Required_Data_Layers.gdb"
    _anthro_data = "Anthro_Features.gdb"
    _layer_files = "Layer_Files"
    _parameter_table = "Anthro_Attribute_Table"
    _extent_raster = "emptyRaster"
    _coordinate_reference = "Mgmt_Cat"
    _habitat_bounds = "Mgmt_Cat"
    _pj_phases = "PJ_Phases"
    _pj_phase_iii = "PJ_Phase_III"
    _brotec = "Annual_Grass_Layer"
    _public_land = "NV_Public"

    # Standard values
    _credit_terms = ["Current", "Projected"]
    _debit_terms = ["Current", "Projected", "Permanent"]
    _seasons = ["Breed", "LBR", "Winter"]
    _HSI_seasons = ["Spring", "Summer", "Winter"]

    def __init__(self, workspace, scriptPath):
        self.workspace = workspace
        self.toolSharePath = os.path.dirname(scriptPath)

    # Getters for files and data directories
    @property
    def ToolDataPath(self):
        return os.path.join(self.toolSharePath, self._data_folder)

    @property
    def InputDataPath(self):
        return os.path.join(self.ToolDataPath, self._input_data)

    @property
    def AnthroFeaturePath(self):
        return os.path.join(self.ToolDataPath, self._anthro_data)

    @property
    def LayerFilePath(self):
        return os.path.join(self.toolSharePath, self._layer_files)

    # Getters for standard credit system values and objects
    @property
    def CreditTerms(self):
        return self._credit_terms

    @property
    def DebitTerms(self):
        return self._debit_terms

    @property
    def Seasons(self):
        return self._seasons

    @property
    def HSISeasons(self):
        return self._HSI_seasons

    @property
    def CoorSystem(self):
        inputDataPath = self.InputDataPath
        reference_layer = os.path.join(inputDataPath, self._coordinate_reference)
        coordinate_system = arcpy.Describe(reference_layer).spatialReference
        return coordinate_system

    @property
    def HabitatBounds(self):
        inputDataPath = self.InputDataPath
        habitat_bounds = os.path.join(inputDataPath, self._habitat_bounds)
        return habitat_bounds

    @property
    def AnthroAttributeTable(self):
        anthroFeaturePath = self.AnthroFeaturePath
        return os.path.join(anthroFeaturePath, self._parameter_table)

    @property
    def EmptyRaster(self):
        anthroFeaturePath = self.AnthroFeaturePath
        return Raster(os.path.join(anthroFeaturePath, self._extent_raster))

    @property
    def PJ_Phases(self):
        inputDataPath = self.InputDataPath
        return os.path.join(inputDataPath, self._pj_phases)

    @property
    def PJ_Phase_III(self):
        inputDataPath = self.InputDataPath
        return os.path.join(inputDataPath, self._pj_phase_iii)

    @property
    def BROTEC(self):
        inputDataPath = self.InputDataPath
        return os.path.join(inputDataPath, self._brotec)

    @property
    def Public(self):
        inputDataPath = self.InputDataPath
        return os.path.join(inputDataPath, self._public_land)

    # Instance methods
    def getLayerFile(self, layer_name):
        layerFilePath = self.LayerFilePath
        layer_file = os.path.join(layerFilePath, layer_name)
        return layer_file

# ----------------------------------------------------------------------------

# UTILITIES
# Utility functions that are or may be called in other functions


def Str2Bool(string):
    """
    Converts a string to Python boolean. If not 'true' in lowercase, returns
    False.
    :param string: a string of True or False, not cap sensitive
    :return: Boolean
    """
    if string == 'True' or string == 'true':
        return True
    else:
        return False


def AddAnthroToMap(workspace, anthro_feature):
    """
    Adds anthropogenic features to the map document by replacing the existing
    state-wide layer with the clipped (project-specific) feature (replacing
    existing maintains the subtype templates for editing). Note that clipped
    anthro features must have 'Anthro_' and '_clip' (not cap sensitive) as
    prefix and suffix.
    :param workspace: the gdb with the clipped (project-specific) anthro features
    :param anthro_feature: the anthro feature to be added to the map document
    :return: None
    """

    if arcpy.ListInstallations()[0] == 'arcgispro':#switch for arcpro and gis desktop
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        try:
            for existingLayer in m.listLayers():
                if existingLayer.name == anthro_feature[7:-5]:
                    #workspace_type = "FILEGDB_WORKSPACE"
                    #dataset_name = anthro_feature
                    new_conn_prop = existingLayer.connectionProperties
                    new_conn_prop['connection_info']['database'] = workspace
                    new_conn_prop['dataset'] = anthro_feature
                    #existingLayer.replaceDataSource(workspace, workspace_type,
                                                   # dataset_name)
                    existingLayer.updateConnectionProperties(existingLayer.connectionProperties,new_conn_prop)
            #arcpy.RefreshActiveView()
        except arcpy.ExecuteError:
            for existingLayer in m.listLayers():
                if existingLayer.name == anthro_feature:
                    arcpy.mp.RemoveLayer(existingLayer)
            refLayer = m.ListLayers("Analysis_Area")[0]
            m.insertLayer(m, refLayer, anthro_feature, "AFTER")
        del p, m
    else: 
    # Add layer to map
        arcpy.AddMessage("Adding layer to map document")
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        layer = arcpy.mapping.Layer(anthro_feature)
        try:
            for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
                if existingLayer.name == layer.name[7:-5]:
                    workspace_type = "FILEGDB_WORKSPACE"
                    dataset_name = anthro_feature
                    existingLayer.replaceDataSource(workspace, workspace_type,
                                                    dataset_name)
            arcpy.RefreshActiveView()
        except arcpy.ExecuteError:
            for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
                if existingLayer.name == layer.name:
                    arcpy.mapping.RemoveLayer(df, existingLayer)
            refLayer = arcpy.mapping.ListLayers(mxd, "Analysis_Area", df)[0]
            arcpy.mapping.InsertLayer(df, refLayer, layer, "AFTER")
        del mxd, df, layer


def AddCodedTextDomain(feature_list, workspace, domain_name, code_list,
                       assign_default=False, populate_default=False):
    """
    Applies the code_list as a domain to the list of feature classes.
    Domain must be the same as the field name to which it is being applied.
    :param feature_list: list of feature classes
    :param workspace: the project's unique gdb
    :param domain_name: name of the domain as a string, must be same as name
    of field to which it is applied
    :param code_list: list of codes as strings
    :param assign_default: True to assign the first code in the code_list as
    default
    :param populate_default: True to populate existing features with the
    default code
    :return: None
    """
    # Create unique list from provided
    uniqueCodes = []
    for code in code_list:
        if code not in uniqueCodes:
            uniqueCodes.append(code)
    # Check for existence of domain; update domain if present, add domain if not
    desc = arcpy.Describe(workspace)
    domains = desc.domains
    if domain_name in domains:
        arcpy.AddMessage(domain_name + " is already specified as a domain")
        try:
            # try removing from all fields in all feature classes
            existingFeatures = arcpy.ListFeatureClasses()
            for existingFeature in existingFeatures:
                fields = arcpy.ListFields(existingFeature)
                for field in fields:
                    if field.domain == domain_name:
                        arcpy.RemoveDomainFromField_management(existingFeature,
                                                                field.name)
                        arcpy.AddMessage(domain_name + " domain removed from "
                                        + existingFeature + " " + field.name
                                        + " field")
                # try removing from all fields in all subtypes
                # Credit to:(https://community.esri.com/thread/
                # 198384-how-to-remove-domain-from-field-for-gdb)
                subtypes = arcpy.da.ListSubtypes(existingFeature)
                for stcode, stdict in list(subtypes.items()):
                    for stkey in list(stdict.keys()):
                        # if there is a Subtype Field
                        if not stdict['SubtypeField'] == '':
                            st_code = "'{}: {}'".format(stcode, stdict['Name'])
                        # if no Subtype Field, use "#" in RemoveDomainFromField
                        # for subtype_code
                        else:
                            st_code = "#"
                        if stkey == 'FieldValues':
                            fields = stdict[stkey]
                            for field, fieldvals in list(fields.items()):
                                # if field has a domain
                                if not fieldvals[1] is None:
                                    # and the domain is in our list
                                    if fieldvals[1].name == domain_name:
                                        # remove the domain
                                        arcpy.AddMessage(fieldvals[1].name
                                                            + " domain removed "
                                                            + "from " + existingFeature
                                                            + " field: " + field
                                                            + " subtype: " + st_code)
                                        arcpy.RemoveDomainFromField_management(
                                            existingFeature, field, st_code)

            arcpy.DeleteDomain_management(workspace, domain_name)
            arcpy.CreateDomain_management(workspace, domain_name,
                                            "Valid " + domain_name + "s",
                                            "TEXT", "CODED")

            for code in uniqueCodes:
                arcpy.AddCodedValueToDomain_management(workspace, domain_name,
                                                        code, code)
            for feature in feature_list:
                try: 
                    arcpy.AssignDomainToField_management(feature, domain_name,
                                                        domain_name)
                    # Check to make sure subtypes exist
                    subtypes = arcpy.da.ListSubtypes(feature)
                    if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                        pass
                    else:
                        st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                        arcpy.AssignDomainToField_management(feature, domain_name,
                                                            domain_name, st_codes)

                except arcpy.ExecuteError:
                    arcpy.AddMessage("--------------------------------"
                                     "\n" + domain_name
                                     + " domain for feature \n\n"
                                     + str(feature) + "\n\n"
                                     + "could not be updated. Use "
                                     "caution when populating attribute\n"
                                     "---------------------------------")
            arcpy.AddMessage(domain_name + " domain updated")

        except arcpy.ExecuteError:
            arcpy.AddMessage(domain_name + " domain could not be updated. Use "
                             "caution when populating attribute")
    else:
        arcpy.CreateDomain_management(workspace, domain_name,
                                      "Valid " + domain_name + "s",
                                      "TEXT", "CODED")
        for code in uniqueCodes:
            arcpy.AddCodedValueToDomain_management(workspace, domain_name,
                                                   code, code)
        for feature in feature_list:
            try: 
                arcpy.AssignDomainToField_management(feature, domain_name,
                                                     domain_name)
                # Check to make sure subtypes exist
                subtypes = arcpy.da.ListSubtypes(feature)
                if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                    pass
                else:
                    st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                    arcpy.AssignDomainToField_management(feature, domain_name,
                                                        domain_name, st_codes)                

            except arcpy.ExecuteError:
                arcpy.AddMessage(domain_name + " domain could not be updated. Use "
                                 "caution when populating attribute")
            
        arcpy.AddMessage(domain_name + " domain updated")
        
    # Assign the first value as the default
    if assign_default:
        for feature in feature_list:
            subtypes = arcpy.da.ListSubtypes(feature)
            if len(subtypes) == 1 and subtypes[0]['SubtypeField'] == '':
                arcpy.AssignDefaultToField_management(feature, domain_name, 
                                                      uniqueCodes[0])
            else:
                st_codes = [str(stcode) for stcode, stdict in list(subtypes.items())]
                arcpy.AssignDefaultToField_management(feature, domain_name, 
                                                    uniqueCodes[0], st_codes)

    # Populate field with default values if Null
    if populate_default:
        arcpy.AddMessage("Populating default values")
        for feature in feature_list:
            where_clause = "{0} = '' OR {0} IS NULL".format(
                arcpy.AddFieldDelimiters(feature, domain_name)
                )
            with arcpy.da.UpdateCursor(feature, domain_name, where_clause) as cursor:
                for row in cursor:
                    row[0] = uniqueCodes[0]
                    cursor.updateRow(row)


def AddToMap(feature_or_raster, layer_file=None, zoom_to=False):
    """
    Adds provided to the map document after removing any layers of the same
    name.
    :param feature_or_raster: feature class or raster dataset
    :param layer_file: layer file
    :param zoom_to: True to zoom to the added object
    :return: None
    """
    # Add layer to map
    arcpy.AddMessage("Adding layer to map document")
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m= p.activeMap
        layer_path = arcpy.Describe(feature_or_raster).catalogPath #arcpy.Describe calls metadata, so this gives full path
        for existingLayer in m.listLayers(m):
            if existingLayer.name == feature_or_raster:
               m.remove_layer(existingLayer)
        m.addDataFromPath(layer_path)
        # TODO: revisit layer file application in Pro.
        if layer_file:
            arcpy.ApplySymbologyFromLayer_management(feature_or_raster, layer_file)
        #if zoom_to:
         #   m.extent = layer.getSelectedExtent()
        del p, m

    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        layer_path = arcpy.Describe(feature_or_raster).catalogPath
        layer = arcpy.mapping.Layer(layer_path)
        for existingLayer in arcpy.mapping.ListLayers(mxd, "", df):
            if existingLayer.name == layer.name:
                arcpy.mapping.RemoveLayer(df, existingLayer)
        arcpy.mapping.AddLayer(df, layer)
        if layer_file:
            arcpy.ApplySymbologyFromLayer_management(layer.name, layer_file)
        if zoom_to:
            df.extent = layer.getSelectedExtent()
        del mxd, df, layer


def AddFields(input_feature, field_to_add, field_types, copy_existing=False):
    """
    Adds provided fields to the input_feature, removes or copies existing of
    the same name.
    :param input_feature: a feature class
    :param field_to_add: a list of field names as strings
    :param field_types: a list of field types as strings, in order of fields_
    to_add
    :param copy_existing: True to create a copy of any existing field with
    same name as field to add
    :return: None
    """
    # Create dictionary of field types mapped to fields to add
    fieldTypesDict = dict(zip(field_to_add, field_types))

    # Copy fields if they exist and delete original
    existingFields = arcpy.ListFields(input_feature)
    fieldNames = [each.name.lower() for each in existingFields]
    for field in field_to_add:
        if field.lower() in fieldNames:
            arcpy.AddMessage(field + " field exists.")
            if copy_existing:
                arcpy.AddMessage("Copying to new field named " + field
                                 + "_copy.")
                fieldIndex = fieldNames.index(field.lower())
                if field.lower() + "_copy" in fieldNames:
                    arcpy.AddMessage("Deleting field " + field + "_copy")
                    arcpy.DeleteField_management(input_feature,
                                                 field + "_copy")
                arcpy.AddField_management(input_feature, field + "_copy",
                                          existingFields[fieldIndex].type)
                with arcpy.da.UpdateCursor(
                        input_feature, [field, field + "_copy"]) as cursor:
                    try:
                        for row in cursor:
                            row[1] = row[0]
                            cursor.updateRow(row)
                    except arcpy.ExecuteError:
                        arcpy.AddMessage("Unable to copy from " + field
                                         + " to " + field + "_copy.")
            arcpy.AddMessage("Deleting original field.")
            arcpy.DeleteField_management(input_feature, field)

    # Add fields
    for field in field_to_add:
        # arcpy.AddMessage("Adding " + field + " field")
        arcpy.AddField_management(input_feature, field,
                                  fieldTypesDict[field],
                                  field_length=50)


def AddRangeDomain(feature, workspace, domain_name, range_low, range_high):
    """
    Applies the range domain to the feature. Removes domain from any existing
    features if necessary.
    :param feature: a feature class
    :param workspace: the project's unique gdb
    :param domain_name: the name of the domain as a string
    :param range_low: integer or float
    :param range_high: integer or float
    :return: None
    """
    # Check for existence of domain; update domain if present, add domain if
    # not
    desc = arcpy.Describe(workspace)
    domains = desc.domains

    if domain_name in domains:
        arcpy.AddMessage(domain_name + " is already specified as a domain")
        try:
            # try removing from all fields in all feature classes
            existingFeatures = arcpy.ListFeatureClasses()
            for existingFeature in existingFeatures:
                fields = arcpy.ListFields(existingFeature)
                for field in fields:
                    if field.domain == domain_name:
                        table = os.path.join(workspace, existingFeature)
                        arcpy.RemoveDomainFromField_management(table,
                                                               field.name)
                        arcpy.AddMessage(domain_name + " domain removed from "
                                         + existingFeature + " " + field.name
                                         + " field")
                # try removing from all fields in all subtypes
                subtypes = arcpy.da.ListSubtypes(existingFeature)
                for stcode, stdict in list(subtypes.items()):
                    for stkey in list(stdict.keys()):
                        # if there is a Subtype Field
                        if not stdict['SubtypeField'] == '':
                            st_code = "'{}: {}'".format(stcode, stdict['Name'])
                        # if no Subtype Field, use "#" in RemoveDomainFromField
                        # for subtype_code
                        else:
                            st_code = "#"
                        if stkey == 'FieldValues':
                            fields = stdict[stkey]
                            for field, fieldvals in list(fields.items()):
                                # if field has a domain
                                if not fieldvals[1] is None:
                                    # and the domain is in our list
                                    if fieldvals[1].name == domain_name:
                                        # remove the domain
                                        arcpy.AddMessage(fieldvals[1].name
                                                         + " domain removed "
                                                         + "from " + existingFeature
                                                         + " field: " + field
                                                         + " subtype: " + st_code)
                                        arcpy.RemoveDomainFromField_management(
                                            existingFeature, field, st_code
                                            )
            arcpy.DeleteDomain_management(workspace, domain_name)
            arcpy.CreateDomain_management(workspace, domain_name, domain_name
                                          + " must be integer", "SHORT", "RANGE")
            arcpy.SetValueForRangeDomain_management(workspace, domain_name,
                                                    range_low, range_high)
            arcpy.AssignDomainToField_management(feature, domain_name,
                                                 domain_name)
            arcpy.AddMessage(domain_name + " domain updated")
        except arcpy.ExecuteError:
            arcpy.AddMessage(domain_name + " domain could not be updated")
    else:
        arcpy.CreateDomain_management(workspace, domain_name, domain_name
                                      + " must be integer", "SHORT", "RANGE")
        arcpy.SetValueForRangeDomain_management(workspace, domain_name,
                                                range_low, range_high)
        arcpy.AssignDomainToField_management(feature, domain_name, domain_name)
        arcpy.AddMessage(domain_name + " domain updated")


def AddSubtypeDomains(feature_list, workspace, Anthro_Attribute_Table):
    """
    Applies the subtypes listed in the Anthro_Attribute_Table as a domain
    to the Subtype field in the anthro feature classes.
    :param feature_list: a list of anthro features
    :param workspace: the project's unique gdb
    :param Anthro_Attribute_Table: the Anthro_Attribute_Table
    :return: None
    """
    arcpy.TableToDomain_management(Anthro_Attribute_Table,
                                   "Subtype", "Subtype", workspace,
                                   "Subtype", "Valid anthropogenic subtypes",
                                   "REPLACE")
    for feature in feature_list:
        arcpy.AssignDomainToField_management(feature, "Subtype", "Subtype")


def AdoptParameter(provided_input, parameter_name, preserve_existing=True):
    """
    Copies the provided input into the geodatabase as the parameter_name
    parameter. If a feature class already exists with the parameter_name,
    a unique copy will be saved (with preserve_existing=True).
    Workspace must be defined as project's unique geodatabase before
    calling this function.
    :param provided_input: a feature class or shapefile
    :param parameter_name: the name to save the provided_input as string
    :param preserve_existing: True to avoid overwriting
    :return: the name of the adopted parameter as a string
    """
    # Save a copy of the existing feature class if it already exists
    if preserve_existing:
        if arcpy.Exists(parameter_name):
            new_parameter_name = arcpy.CreateUniqueName(parameter_name)
            arcpy.CopyFeatures_management(parameter_name, new_parameter_name)

    # Copy providedInput to temporary memory to allow overwriting
    arcpy.CopyFeatures_management(provided_input, "in_memory/tmp_provided")

    # Delete existing layers in the TOC of the paramaterName
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        for _ in m.listLayers():
            arcpy.Delete_management(parameter_name)
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        for _ in arcpy.mapping.ListLayers(mxd, parameter_name):
            arcpy.Delete_management(parameter_name)

    # Delete feature classes in the geodatabase
    for _ in arcpy.ListFeatureClasses(parameter_name):
        arcpy.Delete_management(parameter_name)

    # Execute renaming
    adopted_parameter = arcpy.CopyFeatures_management(
        "in_memory/tmp_provided", parameter_name
        )

    # Clean up
    arcpy.Delete_management("in_memory")

    return adopted_parameter


def ClearSelectedFeatures(fc):
    """
    Removes a selection from the provided feature class
    :param fc: a feature class
    :return: None
    """
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        for lyr in m.listLayers(fc):
            if lyr.getSelectionSet():
                arcpy.AddMessage("clearing {} selected features for "
                                 "layer: '{}'".format(len(lyr.getSelectionSet()),
                                                      lyr.name))
                arcpy.management.SelectLayerByAttribute(lyr, 'CLEAR_SELECTION')
        del m
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        for lyr in arcpy.mapping.ListLayers(mxd, fc):
            if lyr.getSelectionSet():
                arcpy.AddMessage("clearing {} selected features for "
                                 "layer: '{}'".format(len(lyr.getSelectionSet()),
                                                      lyr.name))
                arcpy.management.SelectLayerByAttribute(lyr, 'CLEAR_SELECTION')
        del mxd


def CreateTemplate(workspace, out_name, coordinate_system):
    """
    Creates a template to digitize proposed surface disturbance  or credit
    project boundary in the workspace provided.
    :param workspace: the project's unique gdb
    :param out_name: a name for the template as a string
    :param coordinate_system: the standard coordinate system as a
    SpatialReference object
    :return: None
    """
    # Create an empty feature class
    template_features = arcpy.CreateFeatureclass_management(
        workspace, out_name, "POLYGON", spatial_reference=coordinate_system
        )

    return template_features


def MergeFeatures(file_list, out_name):
    """
    Merges all feature classes into a single feature class.
    :param file_list: a list of feature classes to be merged
    :param out_name: the name to save the output as a string
    :return: the merged features
    """
    # Merge all clipped anthropogenic feature layers
    merged_features = arcpy.Merge_management(file_list, out_name)
    arcpy.AddMessage('Merge completed')

    return merged_features


def RenameFeatureClass(in_data, out_data):
    """
    Deletes existing layers and feature classes of the out_data name and
    renames provided feature class. Provided feature class may not have
    the same name as the out_data. The in_data will be deleted.
    :param in_data: a feature class
    :param out_data: the name to save the output as a string
    :return: the name of the output as a string
    """
    # Delete any existing instances of the file to be overwritten
    # Delete layers in the TOC
    if arcpy.ListInstallations()[0] == 'arcgispro':
        p = arcpy.mp.ArcGISProject("CURRENT")
        m = p.activeMap
        try:
            for layer in m.listLayers(out_data):
                arcpy.Delete_management(layer)
            for feature in arcpy.ListFeatureClasses(out_data):
                arcpy.Delete_management(feature)
        except arcpy.ExecuteError:
            arcpy.AddMessage("Renaming failed to delete existing feature")
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        try:
            for layer in arcpy.mapping.ListLayers(mxd, out_data):
                arcpy.Delete_management(layer)
            # Delete feature classes in the geodatabase
            for feature in arcpy.ListFeatureClasses(out_data):
                arcpy.Delete_management(feature)
        except arcpy.ExecuteError:
            arcpy.AddMessage("Renaming failed to delete existing feature")
    # Execute renaming
    out_fc = arcpy.CopyFeatures_management(in_data, out_data)
    arcpy.Delete_management(in_data)

    return out_fc


def RemoveFeatures(file_list, out_name):
    """
    Intersects the provided feature classes and, if overlapping features
    exist, unions the overlapping features with the first feature class,
    selects the overlapping features, and deletes those features. If no
    overlap exists, creates a copy of the first feature class saved as
    the out_name.
    :param file_list: a list of feature classes where overlapping features
    will be removed from the first feature classw
    :param out_name: a name to save the output, as a string
    :return: the name of the feature class with the remaining features
    as a string, the name of the overlapping feature as a string
    """
    # Remove features that will be updated
    overlap = arcpy.Intersect_analysis(file_list, "overlap")

    test = arcpy.GetCount_management(overlap)
    count = int(test.getOutput(0))

    if count > 0:
        # Union the first provided feature class with the result
        # of the intersect (i.e., overlapping features)
        union = arcpy.Union_analysis([file_list[0], overlap], "union")

        # Select from the union features identical to the overlap
        # and delete from the first provided feature class
        selected = arcpy.MakeFeatureLayer_management(union, "union_lyr")
        arcpy.SelectLayerByLocation_management(selected,
                                               "ARE_IDENTICAL_TO",
                                               overlap)
        arcpy.DeleteFeatures_management(selected)

        # Save the output as the out_name
        remaining_features = arcpy.CopyFeatures_management(selected,
                                                           out_name)

        arcpy.Delete_management("union")

    else:
        # Update message
        arcpy.AddMessage("No overlapping features identified")

        # Return None for overlap
        overlap = None

        # Make a copy of the first provided feature class
        remaining_features = arcpy.CopyFeatures_management(file_list[0],
                                                           out_name)

    # arcpy.Delete_management("overlap")

    return remaining_features, overlap


def SimplifyFields(input_features, allowable_fields):
    """
    Uses the dissolve tool to simplify the fields in the attribute
    table of the provided feature class.
    :param input_features: feature class with attribute table to be
    simplified
    :param allowable_fields: fields to remain in simplified feature
    class's attribute table
    :return: None
    """
    # Create a local copy to allow overwriting
    in_data = input_features
    temp_copy = "in_memory/tmpFC"
    arcpy.CopyFeatures_management(in_data, temp_copy)

    # Dissolve features
    in_features = temp_copy
    out_feature_class = input_features
    dissolve_fields = []
    for field in arcpy.ListFields(in_features):
        if (field.name in allowable_fields 
            and field.editable == True 
            and field.type != 'Geometry'):
            dissolve_fields.append(field.name)
    arcpy.Dissolve_management(in_features, out_feature_class, dissolve_fields)

    # Clean up
    arcpy.Delete_management("in_memory")

# ----------------------------------------------------------------------------

# CUSTOM FUNCTIONS


def CheckToolVersion():
    """
    Adds warning if tool is being used past the specified date.
    Warning date is specified at the top of the ccslib script.
    :return: None
    """
    # ! Update warning date at top of script
    if warn_date:   
        from datetime import datetime
        today = datetime.today()
        warn_format = datetime.strptime(warn_date, "%m/%d/%Y")
        if today > warn_format:
            arcpy.AddWarning(
                """
                WARNING:: This version of the HQT Toolset is outdated.\n
                Please see the User's Guide for instructions on downloading
                the most recent version of the HQT Toolset.\n
                Results obtained from this tool are no longer valid.
                """
            )


def CheckOutSpatialAnalyst():
    """
    Attempts to check out spatial analyst extension. If unavailable, tool
    exits with error message.
    :return: None
    """
    # Check out Spatial Analyst extension
    try:
        arcpy.CheckOutExtension("Spatial")
        arcpy.AddMessage("Spatial Analyst extension checked out")
    except arcpy.ExecuteError:
        arcpy.AddError("Could not check out Spatial Analyst extension. "
                       "Please ensure Spatial Analyst extension is "
                       "available or contact your system administrator.")
        sys.exit(0)


def CheckPolygonInput(feature, required_fields=None, expected_fcs=None,
                      no_null_fields=None):
    """
    If the provided feature is not a polygon, is empty, does not contain
    the required fields, or has null values in the no null feilds, the tool
    exists with an error message. If the expected feature classes are not
    found in the gdb of the provided feature, the tool exists with an error
    message.
    :param feature: feature class
    :param required_fields: list of field names as strings
    :param expected_fcs: list of feature class names as strings
    :param no_null_fields: list of field names as strings
    :return: None
    """
    errorStatus = 0
    # Check feature type of provided feature class
    desc = arcpy.Describe(feature)
    if desc.shapeType != "Polygon":
        arcpy.AddError("ERROR:: Feature class provided is not a polygon.\n"
                       "Please provide a polygon feature.")
        errorStatus = 1

    # Check provided layer for features
    test = arcpy.GetCount_management(feature)
    count = int(test.getOutput(0))
    if count == 0:
        arcpy.AddError("ERROR:: Provide feature " + feature + " is empty. "
                       + feature + " must contain at least one feature.")
        errorStatus = 2

    # Check provided layer for required fields
    if required_fields:
        present_fields = [field.name for field in arcpy.ListFields(feature)]
        for field in required_fields:            
            if field not in present_fields:
                arcpy.AddError("ERROR:: Required field '" + field + "' is not "
                               "present in the provided feature: " + feature)
                errorStatus = 3

    # Check provided layer for attributes in required fields
    if not errorStatus == 3:
        if no_null_fields:
            for field in no_null_fields:
                with arcpy.da.SearchCursor(feature, field) as cursor:
                    for row in cursor:
                        if row[0] is None:
                            errorStatus = 4
                            arcpy.AddError("ERROR:: " + field + " field "
                                           "in feature " + feature
                                           + " contains Null values.")
                    
    # Check to ensure provided layer is in the project's geodatabase
    if expected_fcs:
        workspace_fcs = arcpy.ListFeatureClasses()
        for fc in expected_fcs:
            if fc not in workspace_fcs:
                wrong_workspace = arcpy.Describe(feature).path
                arcpy.AddError("ERROR:: Expected feature class " + fc
                               + " not found in workspace of provided feature "
                               + feature + ". Provided feature MUST be located "
                               + "in the project's unique geodatabase.")
                errorStatus = 5
                arcpy.AddError("Provided feature was found in workspace: "
                               + wrong_workspace)

    if errorStatus > 0:
        sys.exit(0)


def ProjectInput(input_feature, out_name, coordinate_system):
    """
    Projects the provided feature to the projection of the coordinate system.
    Honors feature selections.
    :param input_feature: a feature class, selected features will be honored
    :param out_name: a name to save the output as a string
    :param coordinate_system: the standard coordinate system as a
    SpatialReference object
    :return: the name of the projected feature as a string
    """
    # Project input feature to reference coordinate system
    selected_features = "in_memory/selected"
    arcpy.CopyFeatures_management(input_feature, selected_features)
    projected_feature = arcpy.Project_management(input_feature, out_name,
                                                 coordinate_system)

    # Clean up
    arcpy.Delete_management("in_memory")

    return projected_feature


def EliminateNonHabitat(Project_Area, out_name, habitat_bounds):
    """
    Clips the project area to the boundary of the habitat.
    :param Project_Area: a feature class representing the project area
    :param out_name: a name to save the output as a string
    :param habitat_bounds: a feature class representing the habitat
    boundaries
    :return: the name of the project area with non-habitat removed as
    a string
    """
    # Eliminate areas categorized as 'Non-Habitat' from the Project Area
    clip_features = habitat_bounds
    clipped_feature = arcpy.Clip_analysis(Project_Area, clip_features,
                                          out_name)

    return clipped_feature


def CreateIndirectImpactArea(in_data, Anthro_Attribute_Table, out_name):
    """
    Buffers the provide feature class by the distance associated with the
    subytpe in the Anthro Attribute Table. Provided feature class must have
    a field named 'Subtype' populated exactly the same as
    Anthro_Attribute_Table subtype codes.
    :param in_data: feature class with a field named 'Subtype' populated
    exactly the same as the Anthro_Attribute_Table subtype codes.
    :param Anthro_Attribute_Table: the Anthro_Attribute_Table
    :param out_name: a name to save the output as a string
    :return: the name of the output as a string
    """
    # Join attribute table from AnthroAttributeTable.dbf based on Subtype
    # Get list of existing field names
    existingFields = arcpy.ListFields(in_data)
    fieldNames = [field.name.lower() for field in existingFields]
    # Perform join
    in_field = "Subtype"
    join_table = Anthro_Attribute_Table
    join_field = "Subtype"
    fields = ["Dist", "Weight"]
    for field in fields:
        if field.lower() in fieldNames:
            arcpy.DeleteField_management(in_data, field)
            
    arcpy.JoinField_management(in_data, in_field, join_table, join_field,
                               fields)

    # Buffer Proposed_Surface_Disturbance based on Distance field
    in_features = in_data
    out_feature_class = out_name
    buffer_field = "Dist"
    line_side = "FULL"
    line_end_type = "ROUND"
    dissolve_option = "ALL"
    indirect_impact_area = arcpy.Buffer_analysis(in_features,
                                                 out_feature_class,
                                                 buffer_field, line_side,
                                                 line_end_type,
                                                 dissolve_option)

    # Merge all features with 0 distance (skipped by buffer)
    fc = arcpy.MakeFeatureLayer_management(in_data, "lyr")
    where_clause = """{} = {}""".format(
        arcpy.AddFieldDelimiters(fc, buffer_field), 0)
    arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION",
                                            where_clause)
    
    merged_fc = arcpy.Merge_management([indirect_impact_area, fc], 
                                       'in_memory/merged')
    
    indirect_impact_area_merge = arcpy.Dissolve_management(
        merged_fc)

    return indirect_impact_area_merge


def CreateMapUnits(Project_Area, out_data):
    """
    Creates a copy of the project area feature class as the map units
    feature class
    :param Project_Area: a feature class, non-habitat must be removed
    :param out_data: a name to save the output as a string
    :return: the name of the output as a string
    """
    in_features = Project_Area
    out_feature_class = out_data
    map_units = arcpy.CopyFeatures_management(in_features, out_feature_class)

    return map_units


def CreateAnalysisArea(Project_Area, Anthro_Attribute_Table, out_name):
    """
    Buffers the Project_Area layer by the maximum distance found in the
    Anthro_Attribute_Table.
    :param Project_Area: the Project Area feature class, non-habitat must
    be removed
    :param Anthro_Attribute_Table: the Anthro_Attribute_Table
    :param out_name: a name to save the output as a string
    :return: the name of the output as a string
    """
    in_features = Project_Area
    out_feature_class = out_name
    line_side = "FULL"
    line_end_type = "ROUND"
    dissolve_option = "ALL"

    # identify maximum indirect effect distance for buffer
    effect_distances = [row[0] for row in arcpy.da.SearchCursor(
        Anthro_Attribute_Table, "Dist") if isinstance(row[0], (int, float))]
    buffer_distance = max(effect_distances)

    Analysis_Area = arcpy.Buffer_analysis(in_features, out_feature_class,
                                          buffer_distance, line_side,
                                          line_end_type, dissolve_option)

    return Analysis_Area


def ClipAnthroFeaturesCredit(clip_features, anthro_feature_path):
    """
    Clips all provided anthropogenic feature layers to the Analysis Area
    boundary and saves to the project's gdb. Tool must be run while the
    project's gdb is the active workspace.
    :param clip_features: the Analysis Area feature class
    :param anthro_feature_path: the path to the Anthro_Features gdb
    :return: None
    """
    walk = arcpy.da.Walk(anthro_feature_path, datatype="FeatureClass",
                         type="Polygon")
    for dirpath, _, filenames in walk:
        for filename in filenames:
            arcpy.AddMessage("Clipping " + filename)
            in_features = os.path.join(dirpath, filename)
            out_name = "Anthro_" + filename + "_Clip"
            arcpy.Clip_analysis(in_features, clip_features, out_name)


def ClipAnthroFeaturesDebit(clip_features, anthro_feature_path, 
                            proposed_anthro, fields_to_add, field_types, 
                            mod_field, removed_code, retained_code):
    """
    Clips all provided anthropogenic feature layers to the Analysis Area
    boundary and saves to the project's gdb. Tool must be run while the
    project's gdb is the active workspace.
    :param clip_features: the Analysis Area feature class
    :param anthro_feature_path: the path to the Anthro_Features gdb
    :param proposed_anthro: the proposed surface disturbance path
    :param fields_to_add: fields added to the clipped anthro features
    :param field_types: field types to be added
    :param mod_field: the "Modification" field
    :param removed_code: the code for "Removed" features in the mod_field
    :return: None
    """
    walk = arcpy.da.Walk(anthro_feature_path, datatype="FeatureClass",
                         type="Polygon")
    for dirpath, _, filenames in walk:
        # filenames = [os.path.join(anthro_feature_path, 'Roads')]
        for filename in filenames:
            in_features = os.path.join(dirpath, filename)

            # Save subtypes, domains and fields to add back later
            subtypes = arcpy.da.ListSubtypes(in_features)
            fields = arcpy.ListFields(in_features)
            
            # Update message 
            arcpy.AddMessage("Clipping " + filename)

            # Clip
            out_name = "in_memory/anthro_clip"
            anthro_clip = arcpy.Clip_analysis(in_features, clip_features, out_name)

            # Add fields
            AddFields(anthro_clip, fields_to_add, field_types)

            # Split polygons that overlap with proposed disturbance
            file_list = [anthro_clip, proposed_anthro]
            out_name = "in_memory/anthro_remove"
            anthro_remove, overlap = RemoveFeatures(file_list, out_name)
            
            # Save output
            out_name = "Anthro_" + filename + "_Clip"
            file_list = [anthro_remove, overlap]
            if overlap:
                # Update the Modification field to 'Removed'
                with arcpy.da.UpdateCursor(overlap, mod_field) as cursor:
                    for row in cursor:
                        row[0] = removed_code
                        cursor.updateRow(row)
                        
                # Update the Modification field for Powerlines to 'Retained'
                with arcpy.da.UpdateCursor(
                    overlap, [mod_field, "Type"]) as cursor:
                    for row in cursor:
                        if row[1] == 'Powerlines':
                            row[0] = retained_code
                            cursor.updateRow(row)
                
                # Merge the overlap back in with the removed features
                MergeFeatures(file_list, out_name)
                
                # Save the overlap type and subtype for reference
                for field in ["Overlap_Type", "Overlap_Subtype"]:
                    if field in [f.name for f in arcpy.ListFields(out_name)]:
                        arcpy.DeleteField_management(out_name, field)
                        
                arcpy.AlterField_management(out_name, "Type_1", 
                                            "Overlap_Type", 
                                            "Overlap_Type")
                arcpy.AlterField_management(out_name, "Subtype_1", 
                                            "Overlap_Subtype", 
                                            "Overlap_Subtype")

                # Simplify fields
                existing_fields = [str(field.name) for field in fields]
                allowable_fields = ([field.lower() for field in existing_fields] 
                                    + [field.lower() for field in fields_to_add]
                                    + ["overlap_type", "overlap_subtype"])
                for field in arcpy.ListFields(out_name):
                    if field.name.lower() not in allowable_fields:
                        arcpy.DeleteField_management(out_name, field.name)
            
            else:
                arcpy.CopyFeatures_management(anthro_clip, out_name)
            
            try:
                arcpy.Delete_management("overlap")
            except arcpy.ExecuteError:
                pass

            # Add back subtypes
            arcpy.SetSubtypeField_management(out_name, "Feature")
            for stcode, stdict in list(subtypes.items()):
                arcpy.AddSubtype_management(
                    out_name, stcode, stdict['Name']
                    )
                default_subtype = (subtypes.get(stcode).get('FieldValues')
                                   .get('Subtype')[0])
                arcpy.AssignDefaultToField_management(
                    out_name, 'Subtype', default_subtype, stcode
                )
                arcpy.AssignDefaultToField_management(
                    out_name, 'Subtype_As_Modified', default_subtype, stcode
                )
            
            # Add back default values


def SelectProposed(current_anthro, proposed_sd, mod_field, removed_code, 
                   subtype_mod_field, out_name):
    """
    Creates the Propsoed_Anthro_Features feature class
    :param current_anthro: the Current_Anthro_Features feature class
    :param proposed_sd: the Proposed Surface Disturbance feature class
    :param mod_field: the field name for the "Modification" field
    :param removed_code: the code for features that will be removed
    :param subtype_mod_field: the name of the Subtype_As_Modified field,
    as a string
    :param out_name: the name for the output file, as a string
    :return: the proposed anthro features feature class
    """
    # Select all but 'removed' features from the current anthro features
    fc = arcpy.MakeFeatureLayer_management(current_anthro, "lyr")
    where_clause = """{} = '{}'""".format(
        arcpy.AddFieldDelimiters(fc, mod_field), removed_code)
    arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION",
                                            where_clause)

    # Invert selection
    arcpy.SelectLayerByAttribute_management(fc, "SWITCH_SELECTION")

    # Make a copy
    tmp_current = arcpy.CopyFeatures_management(fc, 
        "in_memory/tmp_current")

    # Update the subtype field with the subtype as modified value
    with arcpy.da.UpdateCursor(tmp_current, ["Subtype",
                               subtype_mod_field]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)

    # Merge the selected features with the proposed disturbance
    features = [tmp_current, proposed_sd]
    proposed_anthro = MergeFeatures(features, out_name)

    # Return the proposed anthro features and clean up
    arcpy.Delete_management("lyr")
    
    return proposed_anthro


def SelectPermanent(current_anthro, proposed_sd, mod_field, 
                    returned_field, 
                    subtype_mod_field, duration_field, 
                    permanent_codes, reclass_code, 
                    reclass_subtype_field, out_name):
    """
    Creates the Permanent_Anthro_Features feature class
    :param current_anthro: the Current_Anthro_Features feature class
    :param proposed_sd: the Proposed Surface Disturbance feature class
    :param mod_field: the field name for the "Modification" field
    :param returned_field" the field name for the "Returned" field
    :param subtype_mod_field: the field name for the 
    "Subtype_As_Modified" field
    :param duration_field: the Surface_Disturbance field name
    :param permanent_codes: the codes used in the Surface_Disturbance
    field to signify permanent disturbance ("Term_Reclassified, 
    "Permanent"
    :param reclass_code: the code for reclassified surface disturance
    ("Term_Reclassified")
    :param reclass_subtype_field: The field name where reclassified subtypes
    are stored ("Reclassified_Subtype")
    :param out_name: a name to save the Permanent_Anthro_Features as a
    string.
    :return: the permanent anthro features feature class
    """
    # Select Permanent and Term_Reclassified features from the 
    # Proposed Surface Disturbance
    fc = arcpy.MakeFeatureLayer_management(proposed_sd, "lyr")
    arcpy.SelectLayerByAttribute_management(fc, "CLEAR_SELECTION")

    for code in permanent_codes:
        where_clause = "{} = '{}'".format(
            arcpy.AddFieldDelimiters(fc, duration_field), code,
            )
        arcpy.SelectLayerByAttribute_management(
            fc, "ADD_TO_SELECTION", where_clause
            )

    # Make a copy
    tmp_name = "in_memory/permanent_proposed"
    permanent_proposed = arcpy.CopyFeatures_management(fc, tmp_name)

    arcpy.Delete_management("lyr")

    # Update subtype for features that will be reclassified post-project
    # Select features that will be reclassified post-project
    fc = arcpy.MakeFeatureLayer_management(permanent_proposed, "lyr")
    where_clause = "{} = '{}'".format(
        arcpy.AddFieldDelimiters(fc, duration_field), reclass_code)
    arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION",
                                            where_clause)

    # Change subtype for reclassified features to reclassified
    # subtype
    with arcpy.da.UpdateCursor(fc, ["Subtype",
                                    reclass_subtype_field]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)

    arcpy.Delete_management("lyr")
    
    # Select all existing features that will be returned 
    fc = arcpy.MakeFeatureLayer_management(current_anthro, "lyr")
    arcpy.SelectLayerByAttribute_management(fc, "CLEAR_SELECTION")

    where_clause = "{} = '{}'".format(
        arcpy.AddFieldDelimiters(fc, returned_field), "True",
        )
    arcpy.SelectLayerByAttribute_management(
        fc, "ADD_TO_SELECTION", where_clause
        )

    # Add permanently modified features from Current_Anthro
    # (modification = "Modified" and "Returned" = "False")
    where_clause = "{} <> {} AND {} = '{}'".format(
        arcpy.AddFieldDelimiters(fc, "Subtype"), 
        arcpy.AddFieldDelimiters(fc, "Subtype_As_Modified"),
        arcpy.AddFieldDelimiters(fc, returned_field), "False"
        )
    arcpy.SelectLayerByAttribute_management(
        fc, "ADD_TO_SELECTION", where_clause
        )
    
    # Make a copy
    tmp_name = "in_memory/permanent_existing"
    permanent_existing = arcpy.CopyFeatures_management(fc, tmp_name)

    arcpy.Delete_management("lyr")

    # Update subtype for permanently modified features
    with arcpy.da.UpdateCursor(permanent_existing, 
                               ["Subtype", subtype_mod_field]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)

    # Merge all permanent features
    features = [permanent_existing, permanent_proposed]
    permanent_features = MergeFeatures(features, out_name)

    return permanent_features


def CalcAnthroDist(extent_fc, Anthro_Features, empty_raster,
                   Anthro_Attribute_Table, term, field="Subtype"):
    """
    Calculates the anthropogenic disturbance associated with all subtypes of
    disturbance present within the Analysis Area and multiplies those to
    calculate cumulative anthropogenic disturbance and saves to the project's
    gdb.
    :param extent_fc: fc to use as processing extent, provide Analysis_Area
    :param Anthro_Features: fc with anthropogenic features
    :param empty_raster: raster of value 1
    :param Anthro_Attribute_Table: table with weights and distances
    :param term: string corresponding to term
    :param field: attribute where anthro subtype is stored
    :return: the name of the resulting anthropogenic disturbance raster as
    a string
    """
    # Identify raster that will be used as the snap raster
    arcpy.env.snapRaster = empty_raster

    # Identify maximum extent of project area
    arcpy.env.extent = extent_fc

    # Create list of unique types and subtypes, and their corresponding weights
    # and distances
    typeList = [row[0] for row in arcpy.da.SearchCursor(
        Anthro_Attribute_Table, "Type")]
    subtypeList = [row[0] for row in arcpy.da.SearchCursor(
        Anthro_Attribute_Table, "Subtype")]
    distList = [row[0] for row in arcpy.da.SearchCursor(
        Anthro_Attribute_Table, "Dist")]
    weightList = [row[0] for row in arcpy.da.SearchCursor(
        Anthro_Attribute_Table, "Weight")]

    # Create dictionary of subtypes and types, weights, distances
    subtypeDict = dict(zip(subtypeList, zip(typeList, distList, weightList)))

    # Initialize list of rasters where features exist
    rasterList = []

    # Calculate anthropogenic disturbance for each feature subtype
    features = arcpy.MakeFeatureLayer_management(Anthro_Features, "lyr")

    for subtype in subtypeDict:

        # Get type, weight and distance values associated with subtype
        t = subtypeDict[subtype][0]
        dist = subtypeDict[subtype][1]
        weight = subtypeDict[subtype][2]

        # Cannot calculate disturbance if distance = 0
        if dist > 0:
            where_clause = """{} = '{}'""".format(
                arcpy.AddFieldDelimiters(features, field), subtype)
            arcpy.SelectLayerByAttribute_management(features, "NEW_SELECTION",
                                                    where_clause)

            test = arcpy.GetCount_management(features)
            count = int(test.getOutput(0))

            arcpy.AddMessage("Calculating " + term + " " + t + " " + subtype)
            arcpy.AddMessage("    " + str(count) + " features found")

            if count > 0:
                # Convert selected anthro features to raster to prevent losing
                # small features that do not align with cell centers
                AddFields(features, ["raster"], ["SHORT"])
                with arcpy.da.UpdateCursor(features, ["raster"]) as cursor:
                    for row in cursor:
                        row[0] = 1
                        cursor.updateRow(row)
                value_field = "raster"
                out_rasterdataset = "tmp_raster"
                cell_assignment = "MAXIMUM_AREA"
                priority_field = "raster"
                cellSize = arcpy.GetRasterProperties_management(
                    empty_raster, "CELLSIZEX").getOutput(0)
                arcpy.PolygonToRaster_conversion(features,
                                                 value_field,
                                                 out_rasterdataset,
                                                 cell_assignment,
                                                 priority_field,
                                                 cellSize)
                arcpy.DeleteField_management(features, "raster")

                # Calculate anthropogenic disturbance
                outEucDist = EucDistance(out_rasterdataset, dist, cellSize)
                # tmp1 = 100 - (weight - (outEucDist / distance) * weight)  # linear
                # tmp1 = 100 - (1/(1 + Exp(((outEucDist / (dist/2))-1)*5))) * weight  # sigmoidal
                tmp1 = (100 - (weight * Power((1 - outEucDist / dist), 2)))  # exponential
                tmp2 = Con(IsNull(tmp1), 100, tmp1)
                tmp3 = tmp2 / 100
                # tmp3.save(str(term + "_" + t + "_" + subtype + "_Disturbance"))
                rasterList.append(tmp3)

    arcpy.SelectLayerByAttribute_management(features, "CLEAR_SELECTION")
    arcpy.Delete_management("lyr")

    # Multiply individual rasters
    anthrodist = np.prod(np.array(rasterList))

    # Clean up
    arcpy.Delete_management("in_memory")
    arcpy.Delete_management("tmp_raster")

    return anthrodist


def AddIndirectBenefitArea(indirect_impact_area, mgmt_map_units):
    """
    Union the indirect impact/benefit area with the map units feature class
    and update attributes of the map units attribute table
    :param indirect_impact_area: feature class of indirect impacts or benefits
    :param mgmt_map_units: the Map Units feature class
    :return: the name of the unioned map units feature class as a string
    """
    # Combine the Map Units layer and Indirect Impact Layer
    # Remove from the Indirect_Impact_Area any existing Map_Units
    fileList = [indirect_impact_area, mgmt_map_units]
    out_name = "Map_Units_Indirect"
    Indirect_Map_Units, _ = RemoveFeatures(fileList, out_name)

    # Merge the created feature class with the Map Units feature class
    fileList = [mgmt_map_units, Indirect_Map_Units]
    out_name = "Map_Units_Union"
    map_units_union = MergeFeatures(fileList, out_name)

    # Update map unit IDs for indirect benefit area with next highest map
    # unit id
    feature = map_units_union
    current_muids = [row[0] for row in arcpy.da.SearchCursor(
        feature, "Map_Unit_ID") if isinstance(row[0], int)]
    # For credit projects that remove anthro features only, current_muids
    # will be empty, so use 1; else use max + 1.
    if not current_muids:
        next_muid = 1
    else:
        next_muid = max(current_muids) + 1
    
    with arcpy.da.UpdateCursor(feature, ["Indirect", "Map_Unit_ID",
                                         "Map_Unit_Name", "Meadow"]) as cursor:
        for row in cursor:
            if row[0] == "True":
                row[1] = next_muid
                row[2] = "Indirect Benefits Area"
                row[3] = "No_Meadow"
                cursor.updateRow(row)
            else:
                row[0] = "False"
                cursor.updateRow(row)

    # Rename Map_Units_Union to Map_Units
    map_units_out = RenameFeatureClass(map_units_union, mgmt_map_units)

    arcpy.Delete_management("Map_Units_Indirect")
    arcpy.Delete_management("Map_Units_Union")

    return map_units_out


def CalcModifiers(extent_fc, input_data_path, Dist_Lek, anthro_disturbance, term,
                  PJ_removal=False, suffix=None):
    """
    Calculates the winter, late brood-rearing, and breeding habitat quality
    modifiers and saves to the project's gdb.
    :param extent_fc: Analysis_Area feature class
    :param input_data_path: path name to the Input_Data gdb
    :param Dist_Lek: raster provided by NDOW on a scale from 0 - 1
    :param anthro_disturbance: anthropogenic disturbance raster of the
    associated term
    :param term: string corresponding to term
    :param PJ_removal: True if project proposes to remove Conifer
    :param suffix: string to append to output name
    :return: None
    """
    # Update message
    arcpy.AddMessage("Calculating " + term + " local-scale habitat function")

    # Identify raster that will be used as the snap raster
    arcpy.env.snapRaster = anthro_disturbance

    # Identify maximum extent of project area
    arcpy.env.extent = extent_fc

    # Identify location of Required_Data_Layers
    Spring_HSI = Raster(os.path.join(input_data_path, "Spring_HSI"))
    Summer_HSI = Raster(os.path.join(input_data_path, "Summer_HSI"))
    Winter_HSI = Raster(os.path.join(input_data_path, "Winter_HSI"))
    Dist_Brood = Raster(os.path.join(input_data_path, "Dist_Brood"))

    # Define helper functions for each season
    def calc_winter():
        """calculate winter modifier"""
        local_winter = (Raster(anthro_disturbance) * Winter_HSI)
        return local_winter

    def calc_lbr():
        """calculate late brood-rearing modifier"""
        local_lbr = (Raster(anthro_disturbance) * Summer_HSI)
        return local_lbr

    def calc_breed():
        """calculate breeding modifier"""
        local_breed = (Raster(anthro_disturbance)
                       * Spring_HSI
                       * Dist_Brood
                       * Dist_Lek)
        return local_breed

    def save_namer(season):
        """create a name to save the output raster as"""
        if suffix:
            return str(term + "_Local_" + season + "_" + suffix)
        else:
            return str(term + "_Local_" + season)

    # Calculate local-scale habitat function
    # Calculate PJ uplift for credit projects that propose to remove PJ cover
    if PJ_removal and term == "Projected":
        PJ = Raster(os.path.join(input_data_path, "PJ_Uplift"))
        arcpy.AddMessage("Calculating " + term + " local scale winter habitat "
                         "function")
        localwinter = calc_winter() * PJ
        localwinter.save(save_namer("Winter"))

        arcpy.AddMessage("Calculating " + term + " local scale late brood-"
                         "rearing habitat function")
        localLBR = calc_lbr() * PJ
        localLBR.save(save_namer("LBR"))

        arcpy.AddMessage("Calculating " + term + " local scale breeding habitat "
                         "function")
        localbreed = calc_breed() * PJ
        localbreed.save(save_namer("Breed"))

    else:
        # Update message
        arcpy.AddMessage("Calculating " + term + " local scale winter habitat "
                         "function")

        # Calculate local scale winter modifier
        localwinter = calc_winter()
        localwinter.save(save_namer("Winter"))

        # Update message
        arcpy.AddMessage("Calculating " + term + " local scale late brood-"
                         "rearing habitat function")

        # Calculate local scale summer modifier
        localLBR = calc_lbr()
        localLBR.save(save_namer("LBR"))

        # Update message
        arcpy.AddMessage("Calculating " + term + " local scale breeding habitat "
                         "function")

        # Calculate local scale breeding modifier
        localbreed = calc_breed()
        localbreed.save(save_namer("Breed"))


def calcDebitImpact(input_data_path):
    """
    Creates a raster to illustrate the local-scale impact of a debit project
    and saves as "Debit_Project_Impact" to the project's unique gdb. Requires
    Debit_Project_Area feature class.
    :param input_data_path: path name to the Input_Data gdb
    :return: None
    """
    arcpy.AddMessage("Visualizing local-scale debit project impact")
    # Calculate impact per season
    winterImpact = (Raster("Current_Local_Winter")
                    - Raster("Projected_Local_Winter"))
    breedImpact = (Raster("Current_Local_Breed")
                   - Raster("Projected_Local_Breed"))
    LBRImpact = (Raster("Current_Local_LBR")
                 - Raster("Projected_Local_LBR"))

    # Select maximum impact from three seasonal impact rasters
    debitImpact = CellStatistics([winterImpact, breedImpact, LBRImpact],
                                 "MAXIMUM", "NODATA")

    # Mask out de minimis habitat
    deMinDebits = Raster(os.path.join(input_data_path, "DeMinDebits"))
    debitImpact = debitImpact * deMinDebits

    # Clip to Debit Project Area
    in_raster = debitImpact
    clip_features = "Debit_Project_Area"
    out_raster = "Debit_Project_Impact"
    arcpy.Clip_management(in_raster, "#", out_raster, clip_features,
                          "#", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    arcpy.BuildPyramids_management(out_raster)


def calcCreditBenefit(input_data_path, includes_anthro_mod=False):
    """
    Calculates the maximum per pixel local-scale impact from a debit project
    and saves as "Credit_Quality" raster in the project's unique gdb. Requires
    the Map_Units_Dissolve feature class.
    :param input_data_path: path name to the Input_Data gdb
    :param includes_anthro_mod: True if the credit project proposes to remove
    or modify existing anthropogenic features
    :return: None
    """
    arcpy.AddMessage("Visualizing local-scale credit project benefit")
    # Set processing extent
    arcpy.env.extent = "Map_Units_Dissolve"
    cell_size = 30
    # Create baseline layer for each season
    seasons = ["Breed", "LBR", "Winter"]
    for season in seasons:
        in_features = os.path.join(input_data_path, "NV_WAFWA")
        field = season + "_HQ"
        baseline = os.path.join(season + "_Baseline")
        arcpy.FeatureToRaster_conversion(in_features, field, baseline,
                                         cell_size)
    # Create Mgmt_Importance layer
    in_features = os.path.join(input_data_path, "Mgmt_Cat")
    field = "Multiplier"
    importance = "Mgmt_Importance"
    arcpy.FeatureToRaster_conversion(in_features, field, importance,
                                     cell_size)
    # Calculate quality using 100% in place of site-scale quality
    winterQuality = (Raster("Projected_Local_Winter")
                     * (1 - Raster("Winter_Baseline")))
    breedQuality = (Raster("Projected_Local_Breed")
                    * (1 - Raster("Breed_Baseline")))
    LBRQuality = (Raster("Projected_Local_LBR")
                  * (1 - Raster("LBR_Baseline")))
    # Select maximum impact from three seasonal impact rasters
    creditQuality = CellStatistics([winterQuality, breedQuality, LBRQuality],
                                   "MAXIMUM", "NODATA")

    # Calculate quality uplift
    if includes_anthro_mod:
        # Calculate uplift
        winterUplift = (Raster("Projected_Local_Winter") -
                        Raster("Current_Local_Winter"))
        breedUplift = (Raster("Projected_Local_Breed") -
                       Raster("Current_Local_Breed"))
        LBRUplift = (Raster("Projected_Local_LBR") -
                     Raster("Current_Local_LBR"))
        creditUplift = CellStatistics([winterUplift, breedUplift, LBRUplift],
                                      "MAXIMUM", "NODATA")
        # Combine uplift and quality rasters
        feature = "Map_Units_Dissolve"
        arcpy.MakeFeatureLayer_management(feature, "lyr")
        where_clause = """{} = '{}'""".format(
            arcpy.AddFieldDelimiters(feature, "Indirect"), "True")
        arcpy.SelectLayerByAttribute_management(feature, "NEW_SELECTION",
                                                where_clause)
        test = arcpy.GetCount_management(feature)
        count = int(test.getOutput(0))
        if count > 0:
            # Clip uplift raster to selected map units
            in_raster = creditUplift
            clip_features = feature
            out_raster = "Indirect_Uplift"
            uplift_clip = arcpy.Clip_management(in_raster, "#", out_raster,
                                                clip_features,
                                                "#", "ClippingGeometry",
                                                "NO_MAINTAIN_EXTENT")
            # Combine with quality rasters
            maxRaster = Con(IsNull(uplift_clip), creditQuality, uplift_clip)
        arcpy.SelectLayerByAttribute_management(feature, "CLEAR_SELECTION")

    else:
        # Select maximum impact from three seasonal impact rasters
        maxRaster = creditQuality

    # Apply management importance multiplier
    creditImpact = maxRaster * "Mgmt_Importance"

    # Eliminate areas of direct disturbance

    # Clip to Credit Project Area
    in_raster = creditImpact
    clip_features = "Map_Units_Dissolve"
    out_raster = "Credit_Quality"
    arcpy.Clip_management(in_raster, "#", out_raster, clip_features,
                          "#", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    arcpy.BuildPyramids_management(out_raster)

    # Clean up
    arcpy.Delete_management("lyr")
    arcpy.Delete_management("in_memory")


def CreatePreDefinedMapUnits(Map_Units, in_features, field_name=None):
    """
    Intersects the Map Units feature class with the in_features feature class.
    A field name may be provided from the in_features to include in the output
    feature class as a label for the map unit, the field will be updated with
    'N/A' for any map units that don't interstect the in_features.
    :param Map_Units: the Map Units feature class
    :param in_features: a feature class to create pre-defined map units from
    :param field_name: the name of a field in the in_features attribute table
    to preserve in the output. Will be updated with 'N/A' if no overlap.
    :return: None
    """
    # Clip the provided features to the Map_Units layer
    clip_features = Map_Units
    out_feature_class = "in_memory/clip"
    arcpy.Clip_analysis(in_features, clip_features, out_feature_class)

    # Union the clipped features and the Map Units layer
    FCs = [Map_Units, out_feature_class]
    out_feature_class = "in_memory/Map_Units_Union"
    Map_Units_Union = arcpy.Union_analysis(FCs, out_feature_class)

    # Overwrite the existing Map_Units layer
    RenameFeatureClass(Map_Units_Union, Map_Units)

    # Populate blank fields with N/A
    if field_name:
        with arcpy.da.UpdateCursor(Map_Units, field_name) as cursor:
            for row in cursor:
                if row[0] is None or row[0] == "":
                    row[0] = "N/A"
                    cursor.updateRow(row)

    # # Add fields and populate with 'True' wherever a new map unit was created
    # if field_name:
    #     fieldsToAdd = [field_name]
    #     fieldTypes = ["TEXT"]
    #     AddFields(Map_Units, fieldsToAdd, fieldTypes)
    #     FID_field = "FID_clip"
    #     with arcpy.da.UpdateCursor(Map_Units,
    #                                [FID_field, field_name]) as cursor:
    #         for row in cursor:
    #             if row[0] > -1:
    #                 row[1] = "True"
    #             else:
    #                 row[1] = "N/A"
    #             cursor.updateRow(row)

    # Clean up
    arcpy.Delete_management("in_memory")


def DissolveMapUnits(Map_Units, allowable_fields, out_name, anthro_features):
    """
    Dissolves the Map Units feature class with the fields provided in the
    allowable fields. Deletes any anthropogenic features provided.
    :param Map_Units: the Map Units feature class
    :param allowable_fields: a list of field names as strings
    :param out_name: a name to save the output as a string
    :param anthro_features: anthropogenic features to delete from the
    Map Units feature class, usually Current_Anthro_Features
    :return: the name of the output as a string
    """
    # Clip and union Current Anthro Features within Map Units layer to identify
    # map units that correspond with current surface disturbance
    in_features = anthro_features
    clip_features = Map_Units
    out_feature_class = "in_memory/Anthro_Features_ClippedToProject"
    anthroClipped = arcpy.Clip_analysis(in_features, clip_features,
                                        out_feature_class)

    in_features = [anthroClipped, Map_Units]
    out_feature_class = "in_memory/Map_Units_SurfaceDisturbance"
    MUSurfaceDisturbance = arcpy.Union_analysis(in_features,
                                                out_feature_class)

    # Populate Map Unit ID, MapUnitName, and Meadow attributes for all map
    # units that correspond with surface disturbance
    feature = arcpy.MakeFeatureLayer_management(MUSurfaceDisturbance, "lyr")
    arcpy.SelectLayerByLocation_management(feature, "WITHIN", anthroClipped)
    arcpy.DeleteFeatures_management(feature)

    # Clear selection
    arcpy.SelectLayerByAttribute_management(feature, "CLEAR_SELECTION")
    arcpy.Delete_management("lyr")

    # Dissolve map units layer and simplify attribute table fields
    in_features = MUSurfaceDisturbance
    out_feature_class = out_name
    dissolve_fields = []
    for field in arcpy.ListFields(Map_Units):
        if field.name in allowable_fields:
            dissolve_fields.append(field.name)
    map_units_dissolve = arcpy.Dissolve_management(
        in_features, out_feature_class, dissolve_fields
        )

    # Combine notes fields
    # Retrieve lists of map unit ids and notes
    fc = Map_Units
    fields = ["Map_Unit_ID", "Notes"]
    mu_ids = []
    mu_notes = []
    with arcpy.da.SearchCursor(fc, fields) as cursor:
        for row in cursor:
            mu_ids.append(row[0])
            mu_notes.append(row[1])

    # Add notes field back to map units dissolve
    AddFields(map_units_dissolve, ["Notes"], ["TEXT"])

    # Update map unit dissolve table
    fc = map_units_dissolve
    fields = ["Map_Unit_ID", "Notes"]
    seperator = "; "
    with arcpy.da.UpdateCursor(fc, fields) as cursor:
        for row in cursor:
            try:
                # Get unique list of notes from map units dissolve
                new_notes = []
                for note, mu_id in zip(mu_notes, mu_ids):
                    if mu_id == row[0]:
                        new_notes.append(note)
                new_notes_unique = list(set(new_notes))
                new_notes_unique = [note for note in new_notes_unique \
                                    if note is not None]
                new_notes_string = seperator.join(new_notes_unique)
                # Truncate long notes (should be 255 chararcters)
                field_length = arcpy.ListFields(fc, fields[1])[0].length
                if len(new_notes_string) > field_length:
                    new_notes_string = new_notes_string[:field_length]
                # Update table
                row[1] = new_notes_string
                cursor.updateRow(row)
            except:
                arcpy.AddMessage("Notes field not populated, refer to original "
                                 "Map_Units feature class for notes")

    # Clean up
    arcpy.Delete_management("in_memory")

    return map_units_dissolve


def CalcAcres(feature):
    """
    Adds field 'Acres' to provided feature and calculates area in acres.
    Feature may not have field Acres in table.
    :param feature: feature class to calculate area of features
    :return: None
    """
    inTable = feature
    fieldName = "Acres"
    fieldType = "DOUBLE"
    expression = "!shape.area@ACRES!"    
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression,
                                    "PYTHON_9.3", "")


def CalcProportion(Map_Units_Dissolve, in_feature, out_feature_class,
                   field_name):
    """
    Calculates the proportion of each map unit in each category.
    :param Map_Units_Dissolve: the Map Units Dissolve feature class
    :param in_feature: the feature class to calculate proportions of
    :param out_feature_class: a name to save the output as a string
    :param field_name: the name of a field to add where the proportion
    will be saved as a string
    :return: None
    """
    # Interesct map unit layer and provided feature
    in_features = [Map_Units_Dissolve, in_feature]
    out_feature_class = out_feature_class
    arcpy.Intersect_analysis(in_features, out_feature_class)

    # Calculate area of each split map unit
    inTable = out_feature_class
    fieldName = "Temp_Acres"
    fieldType = "DOUBLE"
    expression = "!shape.area@ACRES!"    
    arcpy.AddField_management(inTable, fieldName, fieldType)
    arcpy.CalculateField_management(inTable, fieldName, expression,
                                    "PYTHON_9.3", "")

    # Calculate proportion of map unit per category
    arcpy.AddField_management(out_feature_class, field_name, "DOUBLE")
    with arcpy.da.UpdateCursor(out_feature_class,
                               [field_name, "Temp_Acres", "Acres"]) as cursor:
        for row in cursor:
            row[0] = row[1]/row[2]
            cursor.updateRow(row)


def CalcZonalStats(in_zone_data, zone_field, in_value_raster, out_table):
    """
    Resamples inValueRaster to 5m pixel size and calculates the average value
    within each map unit. Higher resolution required for map units <5 acres.
    :param in_zone_data: the Map Units Dissolve feature class
    :param zone_field: the field to use as zone field, must be integer and
    cannot be OBJECTID
    :param in_value_raster: raster dataset or basename as a string
    :param out_table: a name to save the ouput table as a string
    :return: None
    """
    resample = True
    if resample:
        # Resample raster
        tmp_raster = "sub_raster"
        arcpy.Resample_management(in_value_raster, tmp_raster, "5", "NEAREST")
    else:
        tmp_raster = in_value_raster
    # Calculate zonal statistics
    arcpy.gp.ZonalStatisticsAsTable(in_zone_data, zone_field, tmp_raster,
                                    out_table, "DATA", "MEAN")
    if resample:
        arcpy.Delete_management(tmp_raster)


def JoinMeanToTable(in_data, zonal_stats, zone_field, field_name):
    """
    Joins the MEAN field of the provided table to the Map_Units_Dissolve
    attribute table, deleting existing versions of the field if neccesary.
    :param in_data: the Map Unit Dissolve feature class
    :param zonal_stats: the table with statistics to join
    :param zone_field: the name of the field to join to ("Map_Unit_ID")
    :param field_name: a field name to save the joined field as a string
    :return: None
    """
    # Delete existing instances of the new field or MEAN, if present
    existingFields = arcpy.ListFields(in_data)
    for field in existingFields:
        if field.name.lower() == field_name.lower():
            arcpy.DeleteField_management(in_data, field.name)
        if field.name == "MEAN":
            arcpy.DeleteField_management(in_data, field.name)

    # Join MEAN field from ZonalStats table to Map_Units_Dissolve
    joinTable = zonal_stats
    joinField = zone_field
    field = "MEAN"
    arcpy.JoinField_management(in_data, zone_field, joinTable, joinField,
                               field)

    # Change name of joined field
    arcpy.AlterField_management(in_data, field, field_name)


def GenerateTransects(workspace, Map_Units, field_name, out_name):
    """
    DEPRECATING IN 1.5
    Creates random transect locations
    :param workspace: the project's unique geodatabase
    :param Map_Units: the Map_Units_Dissolve feature class with number of
    transects identified in the attribute table
    :param field_name: the field in the attribute table with transect
    requirements defined
    :param out_name: a name to save the output as
    :return: the name of the output as a string
    """
    arcpy.AddMessage("Generating random transect locations within each map "
                     "unit")
    # Create random points in buffered map units
    transects = arcpy.CreateRandomPoints_management(workspace, out_name,
                                                    Map_Units,
                                                    "#", field_name, 25)
    return transects


def AddTransectFields(Transects):
    """DEPRECATING IN 1.5"""
    """
    Inputs: a point shapefile or feature class containing transect points.
    Adds fields for Bearings and UTM Easting and Northing to the provided
    feature.
    Returns: none
    """
    # Add fields for Bearing
    arcpy.AddMessage("Generate random bearing directions for each transect")
    fieldsToAdd = ["Bearing1", "Bearing2", "Bearing3"]
    fieldTypes = ["SHORT", "SHORT", "SHORT"]
    AddFields(Transects, fieldsToAdd, fieldTypes)
    with arcpy.da.UpdateCursor(Transects, fieldsToAdd) as cursor:
        for row in cursor:
            row[0] = random.randint(0, 360)
            row[1] = random.randint(0, 360)
            row[2] = random.randint(0, 360)
            cursor.updateRow(row)
            
    # Add fields for UTM
    arcpy.AddMessage("Calculate the UTM Easting and Northing for each transect")
    fieldsToAdd = ["UTM_E", "UTM_N"]
    fieldTypes = ["DOUBLE", "DOUBLE"]
    AddFields(Transects, fieldsToAdd, fieldTypes)
    arcpy.AddGeometryAttributes_management(Transects, "POINT_X_Y_Z_M")
    with arcpy.da.UpdateCursor(
            Transects, ["UTM_E", "UTM_N", "POINT_X", "POINT_Y"]) as cursor:
        for row in cursor:
            row[0] = row[2]
            row[1] = row[3]
            cursor.updateRow(row)
    arcpy.DeleteField_management(Transects, "POINT_X")
    arcpy.DeleteField_management(Transects, "POINT_Y")


def TransectJoin(Map_Units_Dissolve, Transects, out_name):
    """
    Creates a spatial join of the Transects feature class with the Map Units
    Dissolve feature class
    :param Map_Units_Dissolve: Map Units Dissolve feature class
    :param Transects: Transects feature class
    :param out_name: a name to save the output as a string
    :return: None
    """
    arcpy.AddMessage("Executing spatial join of Transects and "
                     "Map_Unit_Dissolve layer")
    # Execute join
    transects = arcpy.SpatialJoin_analysis(Transects, Map_Units_Dissolve,
                                           out_name, "JOIN_ONE_TO_MANY",
                                           "KEEP_ALL", "#", "WITHIN")
    return transects


def ExportToExcel(input_table, Project_Folder, Project_Name):
    """
    Exports the attribute table of the provided feature or table as a .xls
    file and saves to the project folder with the project name appended.
    :param input_table: a table to be exported
    :param Project_Folder: the directory of the project's unique folder
    :param Project_Name: the unique name of the project as a string
    :return: None
    """
    # Update message
    arcpy.AddMessage("Exporting " + str(input_table)
                     + " attribute tables to "
                     "Excel within the Project Folder")
    # Export tables
    output_file = os.path.join(Project_Folder, str(Project_Name) + "_"
                               + str(input_table) + ".xls")
    arcpy.TableToExcel_conversion(input_table, output_file)
