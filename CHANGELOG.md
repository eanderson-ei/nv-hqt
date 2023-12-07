# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.3] 2023-02-23

### Added

* **Scripts/ccslib.py**: 
  * Updated the `CalcModifiers` function to multiply by the term (1 + SUI) for all projects (credit and debit).
* **Scripts/CreditTool3.py**: included SUI as term in `CalcModifiers` function

## [1.8.0] 2023-02-23

This version includes the Space Use Index as a modifier for Debit Projects only. The Space Use Index must be requested from the SETT. The Space Use Index is used to generate the previously requested `Dist_Lek` layer.

### Added
* **ToolData/Required_Data_Layers.gdb**: Added a remap table to create the `Dist_Lek` layer from the `Space_Use_Index` named `SUI_Remap`.
* **Scripts/ccslib.py**: 
    * Added a function to reclassify the `Space_Use_Layer` to create the `Dist_Lek` layer `calc_dist_lek`. 
    * Added a class method to retrieve the `SUI_Remap` table from `Required_Data_Layers.gdb`. 
    * Updated the `CalcModifiers()` function to to multiply by the term (1 + SUI) if provided, the SUI will only be provided for Debit Projects.
* **Debit_Tool_4**: Changed the `Dist_Lek` parameter to `Space_Use_Index`.
* **Scripts/DebitTool4.py**: 
  * Retrieved the `SUI_Remap` table from `ccsStandard` object and added a call to `ccslib.calc_dist_lek` to create the `Dist_Lek` layer.
  * Included SUI as term in `CalcModifiers` function
* **Credit_Tool_3**: Changed the `Dist_Lek` parameter to `Space_Use_Index`.
* **Scripts/CreditTool3.py**: Retrieved the `SUI_Remap` table from `ccsStandard` object and added a call to `ccslib.calc_dist_lek` to create the `Dist_Lek` layer.

### Changes

* **Calculators**: versioned up the Credit and Debit Calculators but made no changes.

### Bug Fixes

* **ToolData/Anthro_Features.gdb/Railroads**: Changed all Type and Subtype fields from “Railway” to “Railways” to correspond to the `Anthro_Attribute_Table`.
* **Scripts/ccslib.py**: Caught error when no anthropogenic disturbance is included at any term by substituting the `empty_raster` for the `anthro_dist` raster when the list of subtypes present is empty.
* **Scripts/DebitTool4.py:** Changed SimplifyFields to call on each Anthro*Clip layer individually rather than the merged Current_Anthro_Features to solve a memory overrun issue (https://www.mindland.com/solving-the-arcpy-dissolve/).

## [1.7.0] 2021-01-05

### Added

* **ToolData/Anthro_Features.gdb/Railroads**: Added a new feature class provided by the SETT for Railroads. Added required fields Feature (short), Type (text), and Subtype (text). Populated fields for all features. Projected provided shapefile to UTM Zone 11N. Created subtype for Railroad. 
* **ToolData/Required_Data_Layers.gdb/NV_Wet_Meadows**: Added a new feature class provided by the SETT outlining Wetlands. This will be used to automatically create map units for Credit & Debit Projects. Add a field Meadow and populated all features with "Unaltered" as default.
* **Scripts/ccslib.py**: Added the Wet Meadow layer as a property of the ccsStandard object.
* **Scripts/DebitTool_4.py**: Added a call to the ccslib.CreatePredefinedMapUnits() function passing the Wet Meadows layer as input and the Meadow field as the field to copy over to the Map Units layer. Added Meadow as an allowable field (line 324) prior to simplifying fields. Removed Meadow from list of fields to add (line 344).
* **Scripts/CreditTool_1.py**: Added a call to the ccslib.CreatePredefinedMapUnits() function passing the Wet Meadows layer as input and the Meadow field as the field to copy over to the Map Units layer. Removed Meadow from list of fields to add (line 239).

### Removed

* **ToolData/Anthro_Features.gdb/Anthro_Attribute_Table**: removed Pipelines as category.
* **Scripts/DebitTool_4.py**: removed auto generation of BROTEC map units.

### Changes

* **ToolData/Anthro_Features.gdb**: Swapped Anthro_Features.gdb with updated version provided by SETT.
* **ToolData/Anthro_Features.gdb**: Added Domains for Railroad and Other.
* **ToolData/Anthro_Features.gdb/Anthro_Attribute_Table**: added three new subtypes in the Other category, including Other_High, Other_Medium, and Other_Low. 
* **ToolData/Anthro_Features.gdb/Anthro_Attribute_Table**: added new category for Railroads
* **ToolData/Anthro_Features.gdb/Other**: added subtypes for Other_High, Other_Medium, and Other_Low. Re-added to the Map Document to show new subtypes.
* **Scripts/ccslib.py**: Added a variable to the CreatePredefinedMapUnits() function to provide a default value when a map unit is not created (e.g., "No Meadow" when not a meadow).
* **Documents/Debit_Project_Calculator**: moved the column "Meadow" from G to C to mirror the new field order for the Map_Units_Dissolve.xls output file created by Debit Tool 5.
* **Documents/Credit_Project_Calculator**: moved the column "Meadow" from 

## [1.6.21] 2021-02-18

* **Scripts/ccslib.py**: changed `arcpy.gp.ZonalStatisticsAsTable` to `arcpy.gp.ZonalStatisticsAsTable_sa` in line 1928 to fix ArcPro failed to find tool issue.

## [1.6.21] 2021-01-12

### Added

* **Scripts/Debit_Tool_1.py**: Check that provided anthropogenic feature layers do not contain a field named 'Feature' to prevent variable name collisions for debit projects.
* **ToolData/Anthro_Features.gdb**: Add a nondescript anthro feature type in the Anthro_Attribute_Table for features including clearings, gravel pit areas, ranches/homesteads/feedlots, etc. Type: 'Other', Subtype: 'No_Indirect_Dist'.
* **Documents/Users Guide**: Add row in Anthro Attribute Table (Table 1) to include new Other, No Indirect Disturbance type.

### Removed

* **Scripts/Debit_Tool_4.py**: Remove the BROTEC layer and incorporation into map units for debit projects. It just isn’t working as we were hoping/intending it would. We were hoping it would save time in the data collection, but the layer isn’t as good as we thought and it doesn’t save much time or effort in the end.
* **ToolData/Required_Data_Layers.gdb**: Remove Annual_Grass_Layer.

### Changes

* **Documents/Debit_Project_Calculator**: (tab 3.1, column BB) Update formula to apply meadow factor for permanent debits [KA].
* **Documents/Debit_Project_Calculator**: (tab 2.5, column F) Add “IF('2.2 Enter Field Info'!$H6=FALSE,"",” to the beginning of the code in order to not count the transects that were not completed and ding the credit count if the meadow type wasn’t filled out for those transects [KP].
* **Documents/Credit_Project_Calculator**: (tab 2.5, column F) Add “IF('2.2 Enter Field Info'!$H6=FALSE,"",” to the beginning of the code in order to not count the transects that were not completed and ding the credit count if the meadow type wasn’t filled out for those transects [KP].

## [1.6.0] 2020-03-05
* *First version released prior to changelog initiation.*



