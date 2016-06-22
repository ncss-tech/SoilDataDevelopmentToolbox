# gSSURGO_FixSDVTables.py
#
# Remove duplicate records in SDV* tables that were created by the SSURGO_Convert_to_Geodatabase.py
# script prior to 2015-12-15
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
                arcpy.AddError(" \n" + string)

    except:
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        #locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

## ===================================================================================
def CleanTables(gdbPath):
    #
    # Remove duplicate records from the four SDV* tables

    try:
        PrintMsg(" \nProcessing database: " + gdbPath, 0)

        # Set up enforcement of unique keys for SDV tables
        #
        dIndex = dict()  # dictionary storing field index for primary key of each SDV table
        dKeys = dict()  # dictionary containing a list of key values for each SDV table
        dFields = dict() # dictionary containing list of fields for each SDV table
        dOIDs = dict()   # dictionary containing field index for OID (usually zero)
        dOIDFields = dict()  # dictionary containing OID field names for each SDV table
        dDups = dict()       # dictionary containing duplicate OID values for each SDV table
        dCount = dict()      # record count (before)

        #keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"
        tblList = ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']

        for sdvTbl in tblList:

            keyField = keyFields[sdvTbl]
            dCount[sdvTbl] = int(arcpy.GetCount_management(os.path.join(gdbPath, sdvTbl)).getOutput(0))

            fldList = arcpy.Describe(os.path.join(gdbPath, sdvTbl)).fields
            fldNames = list()

            for fld in fldList:
                if fld.type == "OID":
                    oidName = fld.name.lower()
                    dOIDFields[sdvTbl] = oidName

                fldNames.append(fld.name.lower())

            dFields[sdvTbl] = fldNames                      # store list of fields for this SDV table
            dIndex[sdvTbl] = fldNames.index(keyField)       # store field index for primary key in this SDV table
            dOIDFields[sdvTbl] = fldNames.index(oidName)    # store field index for ObjectID in this SDV table
            dKeys[sdvTbl] = []                              # initialize key values list for this SDV table
            dDups[sdvTbl] = []                              # OIDs for duplicate records for this SDV table. Use these to eliminate duplicate records.


        iCntr = 0

        for tblName in tblList:
            # Identify duplicate records for each table
            #
            sdvTbl = os.path.join(gdbPath, tblName)

            if arcpy.Exists(sdvTbl):
                keyIndx = dIndex[tblName]
                oidIndx = dOIDFields[tblName]
                arcpy.SetProgressorLabel("Identifying duplicate records for the " +  tblName + " table in " + gdb)

                with arcpy.da.SearchCursor(sdvTbl, dFields[tblName]) as sdvCur:

                    for rec in sdvCur:
                        if rec[keyIndx] in dKeys[tblName]:
                            # this is a duplicate record, record OID for deletion
                            dDups[tblName].append(rec[oidIndx])

                        else:
                            # add primary key value to list
                            dKeys[tblName].append(rec[keyIndx])

            else:
                err = "Could not find input table " + sdvTbl
                raise MyError, err

        for tblName in tblList:
            # Select and delete duplicate records for each table
            #
            sdvTbl = os.path.join(gdbPath, tblName)


            if arcpy.Exists(sdvTbl):
                oidList = dDups[tblName]

                if len(oidList) > 0:
                    arcpy.SetProgressorLabel("Purging duplicate records for the " + tblName + " table in " + gdb)
                    sQuery = "OBJECTID IN (" + str(oidList)[1:-1] + ")"
                    #PrintMsg(" \n" + tblName + ": " + sQuery, 1)
                    tblView = "SDVTableView"
                    arcpy.MakeTableView_management(sdvTbl, tblView)
                    arcpy.SelectLayerByAttribute_management(tblView, "NEW_SELECTION", sQuery)
                    arcpy.DeleteRows_management(tblView)

                else:
                    PrintMsg("\tNo records identified for removal in " + tblName + " table in " + gdb, 1)

                postCnt = int(arcpy.GetCount_management(os.path.join(gdbPath, sdvTbl)).getOutput(0))
                PrintMsg("\t" + tblName + " before: " + Number_Format(dCount[tblName], 0, True) + "; after: " + Number_Format(postCnt, 0, True), 0)

            else:
                err = "Could not find input table " + sdvTbl
                raise MyError, err

        #arcpy.RefreshCatalog(outputWS)
        arcpy.SetProgressorLabel("Compacting database: " + gdb)
        arcpy.Compact_management(gdbPath)

        for tblName in tblList:
            arcpy.SetProgressorLabel("\tAdding attribute index for " + tblName, 0)
            sdvTbl = os.path.join(gdbPath, tblName)
            indexName = "Indx_" + tblName
            arcpy.AddIndex_management(sdvTbl, keyFields[tblName], indexName)
            

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time

# Create the Geoprocessor object
from arcpy import env
from time import sleep
#from _winreg import *

try:
    wildcard = arcpy.GetParameterAsText(0)  # Not used by script, just menu
    inputFolder = arcpy.GetParameterAsText(1)     # location of gSSURGO databases
    inputDBs = arcpy.GetParameter(2)        # list of gSSURGO database names to be processed


    skippedList = list()

    for gdb in inputDBs:
        gdbPath = os.path.join(inputFolder, gdb)
        bClean = CleanTables(gdbPath)
        if bClean == False:
            skippedList.append(gdb)

    if len(skippedList) > 0:
        PrintMsg(" \nThe following surveys already existed in the new database: " + ", ".join(skippedList), 1)

    else:
        PrintMsg(" \nSuccessfully completed processing \n ", 0)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
