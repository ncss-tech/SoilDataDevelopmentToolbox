# SDVSave_10.py
#
# Steve Peaslee, National Soil Survey Center
# March 14, 2013
#
# Purpose: Merge Soil Data Viewer map layers into a single geodatabase featureclass
# and preserve symbology for each layer.
#
# ArcGIS 10.0 - SP5
# This version is NOT compatible with ArcGIS 9.x!
# ArcGIS 10.1 - SP1
# Altered input parameter 0 to make it act like a list instead of a value table
# Problems with updating layer source when a personal geodatabase is used. For now
# I am going to remove Personal geodatabase as an output option.
# 2014-03-28 Updated some issues with qualified field names being used in output aliases
# Fixed duplicate field handling error
# 2014-08-20 Ian Reid reported a problem when outputting to a featuredataset. Found out that
# the method 'replaceDataSource' always requires the name of the geodatabase, not the full
# path to the featuredataset. Counterintuitive.

# Uses arcpy.mapping functions
#
## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + " \n" + str(sys.exc_type)+ ": " + str(sys.exc_value) + " \n"
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in errorMsg method", 2)
        pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # Adds tool message to the geoprocessor
    #
    #Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
    try:
        for string in msg.split('\n'):
            #Add a geoprocessing message (in case this is run as a tool)
            if severity == 0:
                arcpy.AddMessage(string)

            elif severity == 1:
                arcpy.AddWarning(string)

            elif severity == 2:
                arcpy.AddMessage("    ")
                arcpy.AddError(string)

    except:
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()

        return "???"

## ===================================================================================
def CreateMergedTable(sdvLayers, outputTbl):
    # Merge rating tables from for the selected soilmap layers to create a single, mapunit-level table
    #
    try:
        # Get number of SDV layers selected for export
        #sdvLayers = sdvLayers.split(";")  # switch from semi-colon-delimited string to list of layer names
        #numLayers = len(sdvLayers)      # ArcGIS 10.1 returns count for list object

        env.overwriteOutput = True # Overwrite existing output tables

        # Tool validation code is supposed to prevent duplicate output tables

        # Get arcpy mapping objects
        thisMXD = arcpy.mapping.MapDocument("CURRENT")
        mLayers = arcpy.mapping.ListLayers(thisMXD)

        # Probably should make sure all of these input layers have the same featureclass
        #
        # first get path where input SDV shapefiles are located (using last one in list)
        # hopefully each layer is based upon the same set of polygons
        #
        # First check each input table to make sure there are no duplicate rating fields
        # Begin by getting adding fields from the input shapefile (lastShp). This is necessary
        # to avoid duplication such as MUNAME which may often exist in a county shapefile.

        chkFields = list()  # list of rating fields from SDV soil map layers (basenames). Use this to count dups.
        #dFields = dict()
        dLayerFields = dict()
        maxRecords = 0  # use this to determine which table has the most records and put it first
        maxTable = ""

        # Iterate through each of the layers and get its rating field
        for sdvLayer in sdvLayers:

            if sdvLayer.startswith("'") and sdvLayer.endswith("'"):
                sdvLayer = sdvLayers[i][1:-1]  # this is dropping first and last char in name for RUSLE2 maps..

            desc = arcpy.Describe(sdvLayer)
            dataType = desc.dataType

            if dataType == "FeatureLayer":
                gdb = os.path.dirname(desc.featureclass.catalogPath)

            elif dataType == "RasterLayer":
                gdb = os.path.dirname(desc.catalogPath)

            else:
                raise MyError, "Soil map datatype (" + dataType + ") not valid"

            allFields = desc.fields
            ratingField = allFields[-1]  # rating field should be the last one in the table
            fName = ratingField.name.encode('ascii')       # fully qualified name
            bName = ratingField.baseName.encode('ascii')   # physical name
            clipLen = (-1 * (len(bName))) - 1
            sdvTblName = fName[0:clipLen]
            sdvTbl = os.path.join(gdb, sdvTblName)
            fldType = ratingField.type
            fldLen = ratingField.length
            fldAlias = bName + ", " + sdvTblName
            mukeyField = [fld.name for fld in desc.fields if fld.basename.upper() == "MUKEY"][0]
            dLayerFields[sdvLayer] = (sdvTblName, bName, fName, fldType, fldLen, fldAlias, mukeyField)
            chkFields.append(bName)

            # get record count for sdvTbl
            recCnt = int(arcpy.GetCount_management(sdvTbl).getOutput(0))
            #PrintMsg("\tTable " + sdvTblName + " has " + Number_Format(recCnt, 0, True) + " records", 1)

            if recCnt > maxRecords or (recCnt == maxRecords and sdvLayer == "Map Unit Name"):
                maxRecords = recCnt
                maxTable = str(sdvLayer)

        # Put the biggest table (assuming this one is the most complete) in front
        if not sdvLayers[0] == maxTable:
            PrintMsg(" \nPutting " + maxTable + " at the front", 0)
            sdvLayers.remove(maxTable)
            sdvLayers.insert(0, maxTable)
        
        # Iterate through each of the layers and merge the associated rating table columns
        i = 0

        for sdvLayer in sdvLayers:
            sdvLayer = sdvLayers[i]

            if sdvLayer.startswith("'"):
                sdvLayer = sdvLayers[i][1:-1]  # this is dropping first and last char in name for RUSLE2 maps..

            PrintMsg(" \n\t" + str(i + 1) + ". Processing sdvLayer: " + sdvLayer, 0)
            desc = arcpy.Describe(sdvLayer)
            dataType = desc.dataType

            if dataType == "FeatureLayer":
                gdb = os.path.dirname(desc.featureclass.catalogPath)

            elif dataType == "RasterLayer":
                gdb = os.path.dirname(desc.catalogPath)

            else:
                raise MyError, "Soil map datatype (" + dataType + ") not valid"

            sdvTblName, bName, fName, fldType, fldLen, fldAlias, mukeyField = dLayerFields[sdvLayer]
            sdvTbl = os.path.join(gdb, sdvTblName)
            dMissingData = dict()

            if i == 0 and chkFields.count(bName) == 1:
                # Make outputTbl based upon first sdvTbl
                #PrintMsg(" \nCreating new output table using " + bName, 0)
                #PrintMsg("\tAppending " + bName + " column...", 0)
                arcpy.CopyRows_management(sdvTbl, outputTbl)

            else:
                # if the field name is a duplicate, use AddField instead of JoinField
                #PrintMsg(" \nFound " + str(chkFields.count(bName)) + " " + bName + " columns", 1)
                #PrintMsg(" \nchkFields: " + str(chkFields), 1)

                if chkFields.count(bName) == 1:
                    # unique field name
                    # Append the just the rating column to the outputTbl
                    #PrintMsg("\tAppending " + bName + " column...", 0)
                    arcpy.JoinField_management(outputTbl, "MUKEY", sdvTbl, "MUKEY", [bName])

                else:
                    # duplicate field name
                    if i == 0:
                        # Also need to add mukey field
                        #PrintMsg("\tAdding new mukey column...", 0)
                        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))
                        arcpy.AddField_management(outputTbl, "mukey", "string", "", "", 30, "mukey")

                    dRatings = dict()

                    with arcpy.da.SearchCursor(sdvLayer, [mukeyField, fName]) as cur:

                        for rec in cur:
                            dRatings[str(rec[0])] = rec[1]

                    # Need to validate qualified field name
                    #
                    fName = arcpy.ValidateFieldName(bName + "_" + sdvTblName, gdb)  # reverse qualified field name
                    #PrintMsg("\tAdding new " + fName + " column...", 0)
                    arcpy.AddField_management(outputTbl, fName, fldType, "", "", fldLen, fldAlias)

                    if i == 0:

                        with arcpy.da.InsertCursor(outputTbl, ["mukey", fName]) as cur:
                            for mukey, rating in dRatings.items():
                                rec = (mukey, rating)
                                cur.insertRow(rec)

                    else:
                        with arcpy.da.UpdateCursor(outputTbl, ["mukey", fName]) as cur:
                            for rec in cur:
                                try:
                                    rec[1] = dRatings[rec[0]]
                                    cur.updateRow(rec)

                                except:
                                    #PrintMsg("\tMissing " + fName + " data for " + mukey, 1)
                                    if fName in dMissingData:
                                        dMissingData[fName] += 1

                                    else:
                                        dMissingData[fName] = 1

            i += 1

        # Print results of error trapping
        if len(dMissingData) > 0:
            for fName, errCnt in dMissingData.items():
                PrintMsg("\t" + fName + " is missing " + Number_Format(errCnt, 0, True) + " map units", 1)

        # I could probably switch out the individual rating table joins with the merged table right here??
        arcpy.AddIndex_management(outputTbl, ["mukey"], "Indx_RUSLE2_Mukey")

        PrintMsg(" \nMerged ratings table: " + str(outputTbl) + " \n ", 0)

        return True

    except MyError, e:
        PrintMsg(str(e) + " \n", 2)
        try:
            del thisMXD
        except:
            pass
        return False

    except:
        errorMsg()
        try:
            del thisMXD
        except:
            pass
        return False

# ====================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, traceback, arcpy
from arcpy import env

try:


    if __name__ == "__main__":
        # Create a single table that contains
        #sdvLayers = arcpy.GetParameterAsText(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        sdvLayers = arcpy.GetParameter(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        outputTbl = arcpy.GetParameterAsText(1)      # Output featureclass (preferably in a geodatabase)

        bMerged = CreateMergedTable(sdvLayers, outputTbl)


except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

