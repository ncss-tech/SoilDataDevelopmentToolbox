# SDA_SpatialQuery_Custom.py
#
# Steve Peaslee, National Soil Survey Center, August 2016
#
# Purpose:  
#
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
def AddNewFields(outputShp, columnNames, columnInfo):
    # Create the empty output table that will contain the map unit AWS
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

        # Iterate through list of field names and add them to the output table
        i = 0

        # ColumnInfo contains:
        # ColumnOrdinal, ColumnSize, NumericPrecision, NumericScale, ProviderType, IsLong, ProviderSpecificDataType, DataTypeName
        #PrintMsg(" \nFieldName, Length, Precision, Scale, Type", 1)

        joinFields = list()
        outputTbl = os.path.join("IN_MEMORY", "QueryResults")
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        for i, fldName in enumerate(columnNames):
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if not fldName.lower() == "mukey":
                joinFields.append(fldName)

            arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)

        if arcpy.Exists(outputTbl):
            arcpy.JoinField_management(outputShp, "mukey", outputTbl, "mukey", joinFields)
            return columnNames

        else:
            return []

    except:
        errorMsg()
        return []

## ===================================================================================
def GetSdvFolderAtts(theURL):
    #
    # Create a master dictionary containing SDV attributes for the selected attribute fields
    # Data is queried via Soil Data Access
    #
    try:

        dSdvFolderAtts = dict()  # key is attributecolumnname

        sdvQuery = """select sdvattribute.attributename,  sdvfolder.folderkey, sdvattribute.attributekey
        from sdvattribute 
        inner join sdvfolder on sdvattribute.folderkey = sdvfolder.folderkey"""


        PrintMsg(" \nRequesting tabular data for SDV attribute information...", 0)
        #PrintMsg(" \n" + sdvQuery, 1)
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        dRequest = dict()
        dRequest["format"] = "JSON+COLUMNNAME+METADATA"
        #dRequest["format"] = "XML"
        dRequest["query"] = sdvQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(theURL, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        #PrintMsg(" \njsonString: " + str(jsonString), 1)
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sdvQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        #PrintMsg(" \n" + ", ".join(columnNames), 0)
        
        for sdvInfo in dataList:
            # Read through requested data and load into the proper dictionary
            attName, folderKey, attKey = sdvInfo
            dSdvFolderAtts[attName] = [int(folderKey), int(attKey)]

        #PrintMsg(" \nQueried Soil Data Access for " + str(len(dSdvFolderAtts)) + " SDV attribute types...", 1)
        #PrintMsg(str(dProperties), 1)
        return dSdvFolderAtts

    except:
        errorMsg()
        return dSdvFolderAtts

## ===================================================================================
def GetSdvAtts(gdb):
    #
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    # This function is a work in progress. It is only useful when the output fields
    # match the original field names in the database. I can't think of any easy way to
    # to do this.
    #
    try:

        # Get list of interps from the database-sdvattribute table
        dSDVAtts = dict()
        sdvattsTbl = os.path.join(gdb, "sdvattribute")
        fieldList = ['nasisrulename', 'attributename', 'attributekey']
        #PrintMsg(" \n" + ", ".join(columnNames), 0)
        
        with arcpy.da.SearchCursor(sdvattsTbl, fieldList) as cur:
            for rec in cur:
                ruleName, attName, attKey = rec
                dSDVAtts[ruleName] = [attName, attKey]
                
        #PrintMsg(" \nGot list of " + str(len(dSDVAtts)) + " interps from the geodatabase sdvattribute table...", 1)
        return dSDVAtts

    except:
        errorMsg()
        return dSDVAtts

## ===================================================================================
def GetInterpsList(gdb):
    #
    # Create a list of interpretation names from the geodatabase sainterp table
    # This seems to always be populated
    try:

        # Get list of interps from the database-distinterpmd table
        interpsList = list()
        sainterpTbl = os.path.join(gdb, "sainterp")
        fieldList = ["interpname"]
        #PrintMsg(" \n" + ", ".join(columnNames), 0)
        
        with arcpy.da.SearchCursor(sainterpTbl, fieldList) as cur:
            for rec in cur:
                interpsList.append(rec[0].encode('ascii'))

        PrintMsg(" \nInput database has " + str(len(interpsList)) + " interps in the sainterp table", 0)
        return interpsList

    except:
        errorMsg()
        return interpsList

## ===================================================================================
def GetKeysList(gdb):
    #
    # Create a list of interpretation names from the geodatabase sainterp table
    # This seems to always be populated
    try:

        # Get list of interps from the database-sdvfolderattribute table
        keyList = list()
        sdvfolderTbl = os.path.join(gdb, "sdvfolderattribute")
        fieldList = ["attributekey"]
        #PrintMsg(" \n" + ", ".join(columnNames), 0)
        
        with arcpy.da.SearchCursor(sdvfolderTbl, fieldList) as cur:
            for rec in cur:
                keyList.append(rec[0])

        #PrintMsg(" \nGot list of " + str(len(keyList)) + " attribute keys from the geodatabase sdvfolderattribute table...", 1)
        return keyList

    except:
        errorMsg()
        return keyList

## ===================================================================================
def CompareData(dSdvFolderAtts, interpsList, dSDVAtts, keyList):
    #
    # Create a list of interpretation names from the geodatabase sainterp table
    # This seems to always be populated

    # dSdvFolderAtt: dSdvFolderAtts[attName] = [folderKey, attKey] From SDA
    # interpsList - list of all sainterp.interpnames in gdb
    # dSDVAtts: dSDVAtts[nasis ruleName] = [attName, attKey] From gdb sdvattribute table

    
    try:
        bGood = True
        missingList = list() 

        if len(interpsList) > 0:
            sdvfolderTbl = os.path.join(gdb, "sdvfolderattribute")
            fieldList = ["folderkey", "attributekey"]
            
            cur = arcpy.da.InsertCursor(sdvfolderTbl, fieldList)

            #PrintMsg(" \nsdvfolderattribute: " + str(dSdvFolderAtts), 1)
            
            for ruleName in interpsList:
                try:
                    attName, attKey = dSDVAtts[ruleName]

                    folderKey, attKey = dSdvFolderAtts[attName]

                    if not attKey in keyList:
                        PrintMsg("\tMissing attributekey for '"  + attName + "' in the sdvfolderattributes table", 1)
                        rec = [folderKey, attKey]
                        cur.insertRow(rec)
                        missingList.append(attName)
                        bGood = False
                    
                except:
                    pass
                    #PrintMsg("\tInterp " + ruleName + " not found in the sdvattribute table", 0)

            del cur        

        if len(missingList) == 0:
            PrintMsg(" \nNo problems found in the sdvfolderattributes table \n ", 0)
            
        return bGood
    
    except:
        errorMsg()
        return bGood
    
## ===================================================================================
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed secondss[17:-18]
        eTotal = end - start

        # day = 86400 seconds
        # hour = 3600 seconds
        # minute = 60 seconds

        eMsg = ""

        # calculate elapsed days
        eDay1 = eTotal / 86400
        eDay2 = math.modf(eDay1)
        eDay = int(eDay2[1])
        eDayR = eDay2[0]

        if eDay > 1:
          eMsg = eMsg + str(eDay) + " days "
        elif eDay == 1:
          eMsg = eMsg + str(eDay) + " day "

        # Calculated elapsed hours
        eHour1 = eDayR * 24
        eHour2 = math.modf(eHour1)
        eHour = int(eHour2[1])
        eHourR = eHour2[0]

        if eDay > 0 or eHour > 0:
            if eHour > 1:
                eMsg = eMsg + str(eHour) + " hours "
            else:
                eMsg = eMsg + str(eHour) + " hour "

        # Calculate elapsed minutes
        eMinute1 = eHourR * 60
        eMinute2 = math.modf(eMinute1)
        eMinute = int(eMinute2[1])
        eMinuteR = eMinute2[0]

        if eDay > 0 or eHour > 0 or eMinute > 0:
            if eMinute > 1:
                eMsg = eMsg + str(eMinute) + " minutes "
            else:
                eMsg = eMsg + str(eMinute) + " minute "

        # Calculate elapsed secons
        eSeconds = "%.1f" % (eMinuteR * 60)

        if eSeconds == "1.00":
            eMsg = eMsg + eSeconds + " second "
        else:
            eMsg = eMsg + eSeconds + " seconds "

        return eMsg

    except:
        errorMsg()
        return ""

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
        return False

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, arcpy, traceback, urllib2, httplib, json
import xml.etree.cElementTree as ET
from arcpy import env
from random import randint

try:
    # Create geoprocessor object
    #gp = arcgisscripting.create(9.3)

    # Get input parameters
    #
    gdb = arcpy.GetParameterAsText(0)        # input gSSURGO database to be fixed
    sdaURL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest"

    # Get all sdvfolderattributes from Soil Data Access
    dSdvFolderAtts = GetSdvFolderAtts(sdaURL)

    # Get list of gSSURGO interp names from sainterp table
    interpsList = GetInterpsList(gdb)

    # Get sdv attributes from sdvattribute table in gSSURGO
    dSDVAtts = GetSdvAtts(gdb)

    # Get list of attributekeys from sdvfolderattributes table in geodatabase
    keyList = GetKeysList(gdb)

    # Use interpsList to interate through each interp and get the attribute key.
    # Compare this to the dSdvFolderAtts to get folder key and make sure it is populated in the geodatabase sdvfolderattributes 
    CompareData(dSdvFolderAtts, interpsList, dSDVAtts, keyList)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
