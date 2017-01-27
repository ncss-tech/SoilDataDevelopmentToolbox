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
def GetFieldInfo(sdvLayer):
    # Create a list of field properties for an SDV map layer's last column
    # Field object properties
    # ===================================================
    # name - Returns the name
    # aliasName - Returns the field alias name
    # domain - Returns the name of the associated domain
    # editable - Returns True if the field is editable
    # hasIndex - Returns True if the field has an index
    # isNullable - Returns True if the field is nullable
    # isUnique - Returns True if the field is unique
    # length - Returns the length
    # precision - Returns the precision
    # scale - Returns the scale
    # type - Returns whether SmallInteger, Integer, Single, Double, String, Date, OID, Geometry, or BLOB

    try:
        # Get field object
        flds = arcpy.ListFields(sdvLayer, "*")
        fld = flds[len(flds) - 1]
        #pName = fld.name
        pName = GetRatingField(sdvLayer)  # at 10.1 the fld.name started returning qualified field name
        pAliasName = fld.aliasName
        pIsNullable = fld.isNullable
        pLength = fld.length
        pPrecision = fld.precision
        pScale = fld.scale
        pType = fld.type.lower()

        if pType == "string":
            pType = "text"

        elif pType == "integer":
            pType = "long"

        elif pType == "smallinteger":
            pType = "short"

        elif pType == "single":
            pType = "float"

        #PrintMsg(" \n\tField pName: " + pName, 0)

        # AddField_management <in_table> <field_name> <LONG | TEXT | FLOAT | DOUBLE | SHORT | DATE | BLOB> {field_precision} {field_scale} {field_length} {field_alias} {NULLABLE | NON_NULLABLE} {NON_REQUIRED | REQUIRED} {field_domain}
        #
        fldInfo = [pName,pType,pPrecision,pScale,pLength,pAliasName,"NULLABLE","NON_REQUIRED"]

        return fldInfo

    except:
        errorMsg()
        return ""

## ===================================================================================
def CreateMergedTable(sdvLayers, outputTbl, lastShp):
    # Perform all functions required to convert SDV text files into an ArcGIS table
    try:
        numLayers = len(sdvLayers)  # 10.1

        # Probably should make sure all of these input layers have the same featureclass
        #
        # first get path where input SDV shapefiles are located (using last one in list)
        # hopefully each layer is based upon the same set of polygons
        #


        # First check each input table to make sure there are no duplicate rating fields
        # Begin by getting adding fields from the input shapefile (lastShp). This is necessary
        # to avoid duplication such as MUNAME which may often exist in a county shapefile.

        ratingFields = list()
        chkFields = list()

        # Next get the rating field from each of the input SDV tables joined to the shapefile
        for i in range(numLayers):
            sdvLayer = sdvLayers[i][1:-1]
            desc = arcpy.Describe(sdvLayer)
            gdb = os.path.dirname(desc.featureclass.catalogPath)
            fName = desc.fields[-1].name
            bName = desc.fields[-1].baseName
            sdvTbl = os.path.join(gdb, fName[:(-1 * (len(bName) + 1))])
            #PrintMsg(" \n" + sdvTbl, 0)
            tblFlds = arcpy.Describe(sdvTbl).fields
            fldNames = [fld.name.upper() for fld in tblFlds]
            ratingFld = fldNames[-1]

            if i == 0:
                # Make outputTbl based upon first sdvTbl
                PrintMsg(" \nCreating output table with " + ratingFld  + " column...", 0)
                arcpy.CopyRows_management(sdvTbl, outputTbl)

                if "COMPPCT_R" in fldNames:
                    arcpy.DeleteField_management(outputTbl, "COMPPCT_R")

            else:
                # Append the rating column to the outputTbl
                PrintMsg("\tAppending " + ratingFld + " column...", 0)
                arcpy.JoinField_management(outputTbl, "MUKEY", sdvTbl, "MUKEY", [ratingFld])





        return True

    except MyError, e:
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetRatingField(layerName):
    # Original function from SDV_Save
    # Check SDV temporary layer table for the 'rating' field and return the name string

    try:
        if arcpy.Exists(layerName):
            #PrintMsg("\nGetting fields for " + theInput, 0)
            theFields = arcpy.ListFields(layerName)
            chkField = "MUKEY"
            mukeyCnt = 0

            #for theField in theFields:

            # Assume rating field is the last one in the layer
            theField = theFields[len(theFields) - 1]
            #PrintMsg("\tFound field " + theField.Name, 0)
            # Get unqualified field name
            theNameList = arcpy.ParseFieldName(theField.name).split(",")
            theCnt = len(theNameList) - 1
            theFieldName = theNameList[theCnt].strip()
            PrintMsg("\tField name parsed: " + theFieldName, 0)

            return theFieldName


        else:
            PrintMsg("\tInput layer not found (" + layerName + ")", 0)
            return ""

    except:
        errorMsg()
        return ""

# ====================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, traceback, arcpy
from arcpy import env

try:

    sdvLayers = arcpy.GetParameterAsText(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
    outputTbl = arcpy.GetParameter(1)      # Output featureclass (preferably in a geodatabase)

    env.overwriteOutput = True # Overwrite existing output tables

    # Get arcpy mapping objects
    thisMXD = arcpy.mapping.MapDocument("CURRENT")
    mLayers = arcpy.mapping.ListLayers(thisMXD)

    # Get number of SDV layers selected for export
    sdvLayers = sdvLayers.split(";")
    numLayers = len(sdvLayers)      # ArcGIS 10.1 returns count for list object

    if numLayers > 0:
        # Relying upon validation code in Toolbox to screen the input sdvLayers
        # sdvLoc should end in "USDA\Soil Data Viewer 6.x\temp" or "USDA\Soil Data Viewer 6\temp"

        sdvLayer = sdvLayers[numLayers - 1]             # 10.1
        if sdvLayer.startswith("'"):
            sdvLayer = sdvLayer[1:-1]

        inDesc = arcpy.Describe(sdvLayer)
        lastShp = inDesc.catalogPath
        sdvLoc = os.path.dirname(lastShp)

        # Get the name of the output featureclass, assuming user entered fullpath
        thePath = arcpy.Describe(outputTbl).catalogPath

        #if not arcpy.Exists(thePath):
        #    err = "Output geodatabase does not exist (" + thePath + ")"
        #    raise MyError, err


        # Process individual SDV layers, starting out in the SDV temp folder
        env.workspace = sdvLoc

        # Create a single table that contains
        bMerged = CreateMergedTable(sdvLayers, thePath, lastShp)



except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

