# Fix_gSSURGO_MD_Tables.py
#
# Steve Peaslee, USDA-NRCS NCSS
#
# Replace outdated md* metadata tables in gSSURGO databases with current ones from
# from a populated Access Template Database

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
def ImportMDTables(newDB, accessDB):
    # Import as single set of metadata tables from first survey area's Access database
    # These tables contain table information, relationship classes and domain values
    # They have tobe populated before any of the other tables
    #
    # mdstatdomdet
    # mdstatdommas
    # mdstatidxdet
    # mdstatidxmas
    # mdstatrshipdet
    # mdstatrshipmas
    # mdstattabcols
    # mdstattabs

    try:
        #PrintMsg(" \nImporting metadata tables from " + tabularFolder, 1)

        # Create list of tables to be imported
        tables = ['mdstatdommas', 'mdstatidxdet', 'mdstatidxmas', 'mdstatrshipdet', 'mdstatrshipmas', 'mdstattabcols', 'mdstattabs', 'mdstatdomdet']

        # Process list of text files
        for table in tables:
            arcpy.SetProgressorLabel("Updating " + newDB + "  " + table + "...")
            inTbl = os.path.join(accessDB, table)
            outTbl = os.path.join(newDB, table)

            if arcpy.Exists(inTbl) and arcpy.Exists(outTbl):
                # Create cursor for all fields to populate the current table
                #
                # For a geodatabase, I need to remove OBJECTID from the fields list

                # First truncate any data in the existing FGDB
                arcpy.TruncateTable_management(outTbl)

                fldList = arcpy.Describe(outTbl).fields
                fldNames = list()
                fldLengths = list()

                for fld in fldList:
                    if fld.type != "OID":
                        fldNames.append(fld.name.lower())

                        if fld.type.lower() == "string":
                            fldLengths.append(fld.length)

                        else:
                            fldLengths.append(0)

                if len(fldNames) == 0:
                    raise MyError, "Failed to get field names for " + tbl

                with arcpy.da.InsertCursor(outTbl, fldNames) as outcur:
                    incur = arcpy.da.SearchCursor(inTbl, fldNames)
                    # counter for current record number
                    iRows = 0

                    #try:
                    # Use csv reader to read each line in the text file
                    for row in incur:
                        # replace all blank values with 'None' so that the values are properly inserted
                        # into integer values otherwise insertRow fails
                        # truncate all string values that will not fit in the target field
                        newRow = list()
                        fldNo = 0

                        for val in row:  # mdstatdomdet was having problems with this 'for' loop. No idea why.
                            fldLen = fldLengths[fldNo]

                            if fldLen > 0 and not val is None:
                                val = val[0:fldLen]

                            newRow.append(val)

                            fldNo += 1

                        try:
                            outcur.insertRow(newRow)

                        except:
                            raise MyError, "Error handling line " + Number_Format(iRows, 0, True) + " of " + txtPath

                        iRows += 1

                    if iRows < 63:
                        # the smallest table (msrmas.txt) currently has 63 records.
                        raise MyError, tbl + " has only " + str(iRows) + " records"

            else:
                raise MyError, "Required table '" + tbl + "' not found in " + newDB

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
# main
import string, os, sys, traceback, locale, arcpy
from arcpy import env

from urllib2 import urlopen, URLError, HTTPError
import socket

try:
    arcpy.overwriteOutput = True

    # Script arguments...
    # wildcard filter is parameter zero
    #
    inLoc = arcpy.GetParameterAsText(1)               # input folder
    gdbList = arcpy.GetParameter(2)                   # list of geodatabases in the folder
    accessDB = arcpy.GetParameterAsText(3)                  # populated Access Database (at least for metadata tables

    iCnt = len(gdbList)
    if iCnt > 1:
        PrintMsg(" \nProcessing " + str(iCnt) + " gSSURGO databases", 0)

    else:
        PrintMsg(" \nProcessing one gSSURGO database", 0)

    # initialize list of problem geodatabases
    problemList = list()

    for i in range(0, iCnt):
        gdbName = gdbList[i]
        newDB = os.path.join(inLoc, gdbName)
        PrintMsg(" \nUpdating " + gdbName + "...", 0)
        bImported = ImportMDTables(newDB, accessDB)

        if bImported == False:
            problemList.append(gdbName)


    if len(problemList) > 0:
        PrintMsg("The following geodatabases have problems: " + ", ".join(problemList) + " \n ", 2)

    else:
        PrintMsg(" \nAll " + str(iCnt) + " databases successfully updated \n ", 0)

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n ", 2)

except:
    errorMsg()
