# Code copied from SDA_CustomQuery script and modified to get NationalMusym from Soil Data Access
# Steve Peaslee 10-18-2016

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
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
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + "\n" + str(sys.exc_type)+ ": " + str(sys.exc_value)
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in unHandledException method", 2)
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
def AddNewFields0(outputShp, columnNames, columnInfo):
    # Add new fields from SDA data to the output featureclass
    #
    # ColumnNames and columnInfo come from the Attribute query JSON string
    # MUKEY would normally be included in the list, but it should already exist in the output featureclass
    #
    try:
        # Dictionary: SQL Server to FGDB
        dType = dict()

        dType["int"] = "long"
        dType["smallint"] = "short"
        dType["bit"] = "short"
        dType["varbinary"] = "blob"
        dType["nvarchar"] = "text"
        dType["varchar"] = "text"
        dType["char"] = "text"
        dType["datetime"] = "date"
        dType["datetime2"] = "date"
        dType["smalldatetime"] = "date"
        dType["decimal"] = "double"
        dType["numeric"] = "double"
        dType["float"] ="double"

        # numeric type conversion depends upon the precision and scale
        dType["numeric"] = "float"  # 4 bytes
        dType["real"] = "double" # 8 bytes

        # ColumnInfo contains:
        # ColumnOrdinal, ColumnSize, NumericPrecision, NumericScale, ProviderType, IsLong, ProviderSpecificDataType, DataTypeName
        # PrintMsg(" \nFieldName, Length, Precision, Scale, Type", 1)
        #joinFields = list()

        for i, fldName in enumerate(columnNames):
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if not fldName.lower() == "mukey":
                arcpy.AddField_management(outputShp, fldName, dataType, precision, scale, length)
                #PrintMsg("\tAdding field " + fldName + " to output featureclass", 1)

        return columnNames

        #else:
        #    return []

    except:
        errorMsg()
        return []


## ===================================================================================
def AddNewFields(outputShp, columnNames, columnInfo):
    # Create the empty output table that will contain the map unit AWS
    #
    # ColumnNames and columnInfo come from the Attribute query JSON string
    # MUKEY would normally be included in the list, but it should already exist in the output featureclass
    #
    # Problem using temporary, IN_MEMORY table and JoinField with shapefiles to add new columns. Really slow performance
    try:
        # Dictionary: SQL Server to FGDB
        dType = dict()

        dType["int"] = "long"
        dType["smallint"] = "short"
        dType["bit"] = "short"
        dType["varbinary"] = "blob"
        dType["nvarchar"] = "text"
        dType["varchar"] = "text"
        dType["char"] = "text"
        dType["datetime"] = "date"
        dType["datetime2"] = "date"
        dType["smalldatetime"] = "date"
        dType["decimal"] = "double"
        dType["numeric"] = "double"
        dType["float"] ="double"

        # numeric type conversion depends upon the precision and scale
        dType["numeric"] = "float"  # 4 bytes
        dType["real"] = "double" # 8 bytes

        # Iterate through list of field names and add them to the output table
        i = 0

        # ColumnInfo contains:
        # ColumnOrdinal, ColumnSize, NumericPrecision, NumericScale, ProviderType, IsLong, ProviderSpecificDataType, DataTypeName
        #PrintMsg(" \nFieldName, Length, Precision, Scale, Type", 1)

        joinFields = list()
        outputTbl = os.path.join("IN_MEMORY", "Template")
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        for i, fldName in enumerate(columnNames):
            # Get new field definition from columnInfo dictionary
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if not fldName.lower() == "mukey":
                joinFields.append(fldName)

            PrintMsg("\tAdded field '" + fldName + "'", 1)
            arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)

        if arcpy.Exists(outputTbl):
            PrintMsg(" \nBegin JoinField using " + outputTbl, 1)
            arcpy.JoinField_management(outputShp, "mukey", outputTbl, "mukey", joinFields)
            PrintMsg(" \nCompleted JoinField", 1)
            arcpy.Delete_management(outputTbl)
            return joinFields

        else:
            return []

    except:
        errorMsg()
        return []

## ===================================================================================
def GetMukeys(theInput):
    # Create bracketed list of MUKEY values from spatial layer for use in query
    #
    try:
        # Tell user how many features are being processed
        theDesc = arcpy.Describe(theInput)
        theDataType = theDesc.dataType
        PrintMsg("", 0)

        #if theDataType.upper() == "FEATURELAYER":
        # Get Featureclass and total count
        if theDataType.lower() == "featurelayer":
            theFC = theDesc.featureClass.catalogPath
            theResult = arcpy.GetCount_management(theFC)

        elif theDataType.lower() in ["featureclass", "shapefile"]:
            theResult = arcpy.GetCount_management(theInput)

        else:
            raise MyError, "Unknown data type: " + theDataType.lower()

        iTotal = int(theResult.getOutput(0))

        if iTotal > 0:
            sqlClause = (None, "ORDER BY MUKEY")
            mukeyList = list()

            with arcpy.da.SearchCursor(theInput, ["MUKEY"], sql_clause=sqlClause) as cur:
                for rec in cur:
                    if not rec[0] in mukeyList:
                        mukeyList.append(rec[0])

            #PrintMsg("\tmukey list: " + str(mukeyList), 1)
            return mukeyList

        else:
            return []


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []


## ===================================================================================
def FormAttributeQuery(sQuery, mukeys):
    #
    # Given a simplified polygon layer, use vertices to form the spatial query for a Tabular request
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    #
    # input parameter 'mukeys' is a comma-delimited and single quoted list of mukey values
    #
    try:

        aQuery = sQuery.split(r"\n")
        bQuery = ""
        for s in aQuery:
            if not s.strip().startswith("--"):
                bQuery = bQuery + " " + s

        #PrintMsg(" \nSplit query into " + str(len(aQuery)) + " lines", 1)
        #bQuery = " ".join(aQuery)
        #PrintMsg(" \n" + bQuery, 1)
        sQuery = bQuery.replace("xxMUKEYSxx", mukeys)
        #PrintMsg(" \n" + sQuery, 1)

        return sQuery

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def AttributeRequest(theURL, outputShp):
    # POST REST which uses urllib and JSON
    #
    # Send query to SDM Tabular Service, returning data in JSON format

    try:
        if theURL == "":
            theURL = "http://sdmdataaccess.sc.egov.usda.gov"

    	# Get list of mukeys for use in tabular request
        mukeyList = GetMukeys(outputShp)

        sQuery = "SELECT m.mukey, m.nationalmusym as natmusym from mapunit m where mukey in (xxMUKEYSxx)"

        outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \nRequesting tabular data for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        mukeys = ",".join(mukeyList)


        # Determine whether the source is a shapefile or geodatabase featureclass
        desc = arcpy.Describe(outputShp)

        if dataType.upper() == "FEATURECLASS":

        sQuery = FormAttributeQuery(sQuery, mukeys)  # Combine user query with list of mukeys from spatial layer.
        if sQuery == "":
            raise MyError, ""

        # Tabular service to append to SDA URL
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"
        dRequest["QUERY"] = sQuery

        PrintMsg(" \nURL: " + url)
        PrintMsg("FORMAT: " + dRequest["FORMAT"])
        PrintMsg("QUERY: " + sQuery)

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)

        # Read the response from SDA into a string
        jsonString = resp.read()

        #PrintMsg(" \njsonString: " + str(jsonString), 1)
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        if len(mukeyList) != len(dataList):
            PrintMsg(" \nWarning! Only returned data for " + str(len(dataList)) + " mapunits", 1)

        newFields = AddNewFields(outputShp, columnNames, columnInfo)   # Here's where I'm seeing a slow down (JoinField)

        if len(newFields) == 0:
            raise MyError, ""

        ratingField = newFields[-1]  # last field in query will be used to symbolize output layer

        if len(newFields) == 0:
            raise MyError, ""

        # Reading the attribute information returned from SDA Tabular service
        #
        arcpy.SetProgressorLabel("Importing attribute data...")
        PrintMsg(" \nImporting attribute data...", 0)

        dMapunitInfo = dict()
        mukeyIndx = -1
        for i, fld in enumerate(columnNames):
            if fld.upper() == "MUKEY":
                mukeyIndx = i
                break

        if mukeyIndx == -1:
            raise MyError, "MUKEY column not found in query data"

        #PrintMsg(" \nColumnNames (" + str(mukeyIndx) + ") : " + ", ".join(columnNames))
        #PrintMsg(" \n" + str(fieldList), 1)
        noMatch = list()
        cnt = 0

        for rec in dataList:
            try:
                mukey = rec[mukeyIndx]
                dMapunitInfo[mukey] = rec
                #PrintMsg("\t" + mukey + ":  " + str(rec), 1)

            except:
                errorMsg()
                PrintMsg(" \n" + ", ".join(columnNames), 1)
                PrintMsg(" \n" + str(rec) + " \n ", 1)
                raise MyError, "Failed to save " + str(columnNames[i]) + " (" + str(i) + ") : " + str(rec[i])

        # Write the attribute data to the featureclass table
        #
        with arcpy.da.UpdateCursor(outputShp, columnNames) as cur:
            for rec in cur:
                try:
                    mukey = rec[mukeyIndx]
                    newrec = dMapunitInfo[mukey]
                    #PrintMsg(str(newrec), 0)
                    cur.updateRow(newrec)

                except:
                    if not mukey in noMatch:
                        noMatch.append(mukey)

        if len(noMatch) > 0:
            PrintMsg(" \nNo attribute data for mukeys: " + str(noMatch), 1)

        arcpy.SetProgressorLabel("Finished importing attribute data")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, arcpy, traceback, urllib2, httplib, json
from arcpy import env

try:
    if __name__ == "__main__":
        outputShp = arcpy.GetParameterAsText(0)  # target featureclass or table which contains MUKEY
        theURL = ""
        bAtts = AttributeRequest(theURL, outputShp)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()