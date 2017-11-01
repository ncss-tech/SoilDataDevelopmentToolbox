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
def AddNewFields(outputShp, columnNames, columnInfo):
    # Create the empty output table that will contain the map unit AWS
    #
    # ColumnNames and columnInfo come from the Attribute query JSON string
    # MUKEY would normally be included in the list, but it should already exist in the output featureclass
    #
    # Problem using temporary, IN_MEMORY table and JoinField with shapefiles to add new columns. Really slow performance.

    try:
        # Dictionary: SQL Server to FGDB
        #PrintMsg(" \nAddNewFields function begins", 1)
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

        joinedFields = list() # new fields that need to be added to the output table
        dataFields = list()   # fields that need to be updated in the AttributeRequest function
        outputTbl = os.path.join("IN_MEMORY", "Template")
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        # Get a list of fields that already exist in outputShp
        outFields = arcpy.Describe(outputShp).fields
        existingFields = [fld.name.lower() for fld in outFields]


        # Using JoinField to add the NATMUSYM column to the outputTbl (but not the data)
        #
        for i, fldName in enumerate(columnNames):
            # Get new field definition from columnInfo dictionary
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            #if not fldName.lower() == "mukey":
            #    joinedFields.append(fldName)

            if not fldName.lower() in existingFields:
                # This is a new data field that needs to be added to the output table.
                #arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length) # add to IN_MEMORY table
                arcpy.AddField_management(outputShp, fldName, dataType, precision, scale, length) # add direct to featureclass
                joinedFields.append(fldName)
                dataFields.append(fldName)

            elif fldName.lower() in existingFields and fldName.lower() != "mukey":
                # This is an existing data field in the output table.
                dataFields.append(fldName)

            elif fldName.lower() == "mukey":
                #arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)
                pass

        if arcpy.Exists(outputTbl) and len(joinedFields) > 0:
            #PrintMsg(" \nAdded these new fields to " + os.path.basename(outputShp) + ": " + ", ".join(joinedFields), 1)
            #arcpy.JoinField_management(outputShp, "mukey", outputTbl, "mukey", joinedFields) # instead add directly to output featureclass
            arcpy.Delete_management(outputTbl)
            return dataFields

        else:
            #PrintMsg(" \nThese fields already exist in the output table: " + ", ".join(dataFields), 1)
            arcpy.Delete_management(outputTbl)
            return dataFields

    except:
        errorMsg()
        return ["Error"]

## ===================================================================================
def GetKeys(theInput, keyField):
    # Create bracketed list of AREASYMBOL values from spatial layer for use in query
    #
    try:
        # Tell user how many features are being processed
        theDesc = arcpy.Describe(theInput)
        theDataType = theDesc.dataType
        PrintMsg("", 0)
        PrintMsg(" \nGetting AREASYMBOL values from spatial layer... \n ", 0)

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
            sqlClause = ("DISTINCT " + keyField, "ORDER BY " + keyField)
            keyList = list()

            with arcpy.da.SearchCursor(theInput, [keyField], sql_clause=sqlClause) as cur:
                for rec in cur:
                    keyList.append(rec[0].encode('ascii'))

            keySet = set(keyList)
            keyList = list(keySet)

            # Make sure list of keys isn't too long for Soil Data Access
            if len(keyList) > 250:
                keyLists = [keyList[x:x+250] for x in range(0, len(keyList), 250)]
                return keyLists

            else:
                return [keyList]

        else:
            return [[]]

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return [[]]

    except:
        errorMsg()
        return [[]]

## ===================================================================================
def FormAttributeQuery(sQuery, keyList):
    #
    # Given a simplified polygon layer, use vertices to form the spatial query for a Tabular request
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    #
    # input parameter 'keyList' is a comma-delimited and single quoted list of key values

    try:

        aQuery = sQuery.split(r"\n")
        bQuery = ""
        for s in aQuery:
            if not s.strip().startswith("--"):
                bQuery = bQuery + " " + s

        sKeys = str(keyList)[1:-1]
        sQuery = bQuery.replace("xxKEYSxx", sKeys)
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
    # Requires MUKEY column

    try:
        if theURL == "":
            theURL = "https://sdmdataaccess.sc.egov.usda.gov"

        keyField = "areasymbol"
    	# Get list of mukeys for use in tabular request
        #
        # Check to see if there is an associated SAPOLYGON featureclass in the geodatabase.
        shpDesc = arcpy.Describe(outputShp)
        fullPath = shpDesc.catalogPath
        gdb = os.path.dirname(fullPath)
        gdbDesc = arcpy.Describe(gdb)
        
        if gdbDesc.workspaceFactoryProgID.startswith("esriDataSourcesGDB.FileGDBWorkspaceFactory"):
            # might be gSSURGO, look for SAPOLYGON featureclass. Faster way to get list.
            keyLists = GetKeys(os.path.join(gdb, "SAPOLYGON"), keyField)

        else:   
            keyLists = GetKeys(outputShp, keyField)

        if len(keyLists[0]) == 0:
            # No areasymbols returned by GetKeys
            raise MyError, ""

        polyCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        dMapunitInfo = dict()

        keyCntr = 0
        
        for keyList in keyLists:

            keyCntr += 1

            sQuery = """SELECT M.mukey, M.nationalmusym AS natmusym FROM mapunit M WITH (nolock)
            INNER JOIN legend L ON M.lkey = L.lkey AND L.areasymbol IN (xxKEYSxx)"""

            outputValues = []  # initialize return values (min-max list)

            #PrintMsg(" \nRequesting tabular data for " + Number_Format(len(keyList), 0, True) + " soil survey areas...")
            arcpy.SetProgressorLabel("Sending tabular request " + str(keyCntr) + " to Soil Data Access...")

            sQuery = FormAttributeQuery(sQuery, keyList)  # Combine user query with list of mukeys from spatial layer.

            if sQuery == "":
                raise MyError, ""

            # Tabular service to append to SDA URL
            url = theURL + "/Tabular/SDMTabularService/post.rest"
            dRequest = dict()
            dRequest["format"] = "JSON+COLUMNNAME+METADATA"
            dRequest["query"] = sQuery

            #PrintMsg(" \nURL: " + url)
            #PrintMsg("FORMAT: " + dRequest["FORMAT"])
            #PrintMsg("QUERY: " + sQuery)


            # Create SDM connection to service using HTTP
            jData = json.dumps(dRequest)

            # Send request to SDA Tabular service
            req = urllib2.Request(url, jData)
            resp = urllib2.urlopen(req)

            #PrintMsg(" \nImporting attribute data...", 0)
            #PrintMsg(" \nGot back requested data...", 0)

            # Read the response from SDA into a string
            jsonString = resp.read()

            #PrintMsg(" \njsonString: " + str(jsonString), 1)
            data = json.loads(jsonString)
            del jsonString, resp, req

            if not "Table" in data:
                raise MyError, "Query failed to select anything: \n " + sQuery

            dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.
            arcpy.SetProgressorLabel("Adding new fields to output table...")
            PrintMsg(" \nRequested data consists of " + Number_Format(len(dataList), 0, True) + " records", 0)

            # Get column metadata from first two records
            columnNames = dataList.pop(0)
            columnInfo = dataList.pop(0)

            if keyCntr == 1:
                PrintMsg(" \nAdding new fields...", 0)
                newFields = AddNewFields(outputShp, columnNames, columnInfo)   # Here's where I'm seeing a slow down (JoinField)

                if newFields[0] == "Error":
                    raise MyError, "Error from AddNewFields"

                #ratingField = newFields[-1]  # last field in query will be used to symbolize output layer

                if len(newFields) == 0:
                    raise MyError, ""

            # Reading the attribute information returned from SDA Tabular service
            #
            arcpy.SetProgressor("step", "Importing attribute data for " + Number_Format(len(keyList), 0, True) + " soil survey areas...", 1, polyCnt, 1)
            
            mukeyIndx = -1
            for i, fld in enumerate(columnNames):
                if fld.upper() == "MUKEY":
                    mukeyIndx = i
                    break

            if mukeyIndx == -1:
                raise MyError, "MUKEY column not found in query data"

            #PrintMsg(" \nUpdating information for " + ", ".join(newFields))

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
        PrintMsg(" \nAdding natmusym labels to " + outputShp + "...", 0)
        arcpy.SetProgressorLabel("Adding natmusym labels to target layer...")

        with arcpy.da.UpdateCursor(outputShp, columnNames) as cur:
            for rec in cur:
                arcpy.SetProgressorPosition()

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
        PrintMsg(" \nImport complete... \n ", 0)

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
