# gSSURGO_MapDescriptions.py
#
# Creates short description of each soil property or soil interpretation in the database
#
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
        PrintMsg("Unhandled error in attFld method", 2)
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

        return "???"

## ===================================================================================
def BadTable(tbl):
    # Make sure the table has data
    #
    # If has contains one or more records, return False (not a bad table)
    # If the table is empty, return True (bad table)

    try:
        if not arcpy.Exists(tbl):
            return True

        recCnt = int(arcpy.GetCount_management(tbl).getOutput(0))

        if recCnt > 0:
            return False

        else:
            return True

    except:
        errorMsg()
        return True

## ===================================================================================
def GetDescription(gdb, dSDV, tblList):
    # Print selected property or interp description to the console window
    #
    try:

        # Save parameter settings for layer description
        parameterString = sdvFolder + "\n" + sdvAtt + "\nTables used: " + ", ".join(tblList) + "\n" + ("=" * 80) + "\n" + dSDV["attributedescription"]

        if not dSDV["attributeuom"] is None:
            parameterString = parameterString + "\r\n" + "Units of Measure: " +  dSDV["attributeuom"]

        if dSDV["primaryconstraintlabel"] is not None:
            parameterString = parameterString + "\r\n" + dSDV["primaryconstraintlabel"]

        if dSDV["secondaryconstraintlabel"] is not None:
            parameterString = parameterString + "; " + dSDV["secondaryconstraintlabel"]

        # Finish adding system information to description
        #parameterString = parameterString + "\r\nGeoDatabase: " + gdb

        PrintMsg(" \n" + parameterString + " \n ", 1)
        return True

    except:
        errorMsg()
        return False

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time
import xml.etree.cElementTree as ET

# Create the environment
from arcpy import env

try:
    inputLayer = arcpy.GetParameterAsText(0)      # Input mapunit polygon layer
    sdvFolder = arcpy.GetParameter(1)             # SDV Folder
    sdvAtt = arcpy.GetParameter(2)                # SDV Attribute

    # Quit immmediately if the aggregation method selected has not yet been
    # implemented.
    #if aggMethod in ["Least Limiting", "Most Limiting"]:
    #    raise MyError, "Sorry, the '" + aggMethod + "' aggregation method has not yet been implemented"

    # Get target gSSURGO database
    muDesc = arcpy.Describe(inputLayer)
    fc = muDesc.catalogPath                         # full path for input mapunit polygon layer
    gdb = os.path.dirname(fc)                       # need to expand to handle featuredatasets

    # Set current workspace to the geodatabase
    env.workspace = gdb
    env.overwriteOutput = True

    # Open sdvattribute table and query for [attributename] = sdvAtt
    dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
    sdvattTable = os.path.join(gdb, "sdvattribute")
    flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
    sql1 = "attributename = '" + sdvAtt + "'"

    with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
        rec = cur.next()  # just reading first record
        i = 0
        for val in rec:
            dSDV[flds[i]] = val
            # PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
            i += 1

    # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
    if dSDV["nasisrulename"] is not None and dSDV["nasisrulename"][0:5] == "NCCPI":
        dSDV["attributecolumnname"] = "interphr"

    # Temporary workaround for sql whereclause. File geodatabase is case sensitive.
    if dSDV["sqlwhereclause"] is not None:
        sqlParts = dSDV["sqlwhereclause"].split("=")
        dSDV["sqlwhereclause"] = "UPPER(" + sqlParts[0] + ") = " + sqlParts[1].upper()

    #if top > 0 and bot > 0:
    #    dSDV["sqlwhereclause"] = "(CHORIZON.HZDEPT_R between " + str(top) + " and " + str(bot) + " or CHORIZON.HZDEPB_R between " + str(top) + " and " + str(bot + 1) + ")"



    # 'Big' 3 tables
    big3Tbls = ["MAPUNIT", "COMPONENT", "CHORIZON"]

    #  Create a dictionary to define minimum field list for the tables being used
    #
    dFields = dict()
    dFields["MAPUNIT"] = ["MUKEY"]
    dFields["COMPONENT"] = ["MUKEY", "COKEY", "COMPPCT_R"]
    dFields["CHORIZON"] = ["COKEY", "CHKEY", "HZDEPT_R", "HZDEPB_R"]
    dFields["COMONTH"] = ["COKEY", "COMONTHKEY"]
    #dFields["COMONTH"] = ["COMONTHKEY", "MONTH"]
    dMissing = dict()
    dMissing["MAPUNIT"] = [None] * len(dFields["MAPUNIT"])
    dMissing["COMPONENT"] = [None] * (len(dFields["COMPONENT"]) - 1)  # adjusted number down because of mukey
    dMissing["CHORIZON"] = [None] * (len(dFields["CHORIZON"]) - 1)
    dMissing["COMONTH"] = [None] * (len(dFields["COMONTH"]) - 1)

    # Dictionary containing sql_clauses for the Big 3
    #
    dSQL = dict()
    dSQL["MAPUNIT"] = (None, "ORDER BY MUKEY ASC")
    dSQL["COMPONENT"] = (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC")
    dSQL["CHORIZON"] = (None, "ORDER BY COKEY ASC, HZDEPT_R ASC")

    # Get information about the SDV output result field
    #
    sdvTbl = dSDV["attributetablename"].upper()
    sdvFld = dSDV["attributecolumnname"].upper()
    dataType = dSDV["attributelogicaldatatype"].lower()
    fldLength = dSDV["attributefieldsize"]
    fldPrecision = max(0, dSDV["attributeprecision"])
    ltabphyname = dSDV["attributetablename"].upper()
    rtabphyname = dSDV["attributetablename"].upper()
    resultcolumn = dSDV["resultcolumnname"].upper()

    primaryconcolname = dSDV["primaryconcolname"]
    if primaryconcolname is not None:
        primaryconcolname = primaryconcolname.upper()

    secondaryconcolname = dSDV["secondaryconcolname"]
    if secondaryconcolname is not None:
        secondaryconcolname = secondaryconcolname.upper()


    # Identify related tables using mdstatrshipdet and add to tblList
    #
    mdTable = os.path.join(gdb, "mdstatrshipdet")
    mdFlds = ["LTABPHYNAME", "RTABPHYNAME", "LTABCOLPHYNAME", "RTABCOLPHYNAME"]
    level = 0  # table depth
    tblList = list()

    # Setup initial queries
    while ltabphyname != "MAPUNIT":
        level += 1
        sql = "RTABPHYNAME = '" + ltabphyname.lower() + "'"
        #PrintMsg("\tGetting relates for " + ltabphyname, 1)

        with arcpy.da.SearchCursor(mdTable, mdFlds, where_clause=sql) as cur:
            for rec in cur:
                ltabphyname = rec[0].upper()
                rtabphyname = rec[1].upper()
                ltabcolphyname = rec[2].upper()
                rtabcolphyname = rec[3].upper()
                tblList.append(rtabphyname) # save list of tables involved

        if level > 6:
            break  # failsafe

    #PrintMsg(" \nLast half of script", 1)
    # Create a list of all fields needed for the initial output table. This
    # one will include primary keys that won't be in the final output table.
    #
    if len(tblList) == 0:
        # No Aggregation Necessary, append field to mapunit list
        tblList = ["MAPUNIT"]
        dFields["MAPUNIT"].append(sdvFld)

    else:
        tblList.append("MAPUNIT")

    tblList.reverse()  # Set order of the tables so that mapunit is on top

    bDesc = GetDescription(gdb, dSDV, tblList)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
