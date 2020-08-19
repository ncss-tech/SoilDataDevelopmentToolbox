# SDA_Valu2Table.py
#
# Steve Peaslee, National Soil Survey Center, November 2019
#
# Purpose:  Queries Soil Data Access Tabular service for National Valu1 table data and aggregate to the map unit level

# The Tabular service uses a MS SQLServer database. 

# Attribute data only on the basis of !
#
# If this table is to be joined to either a gSSURGO raster or map unit polygon layer, the user is responsible for
# making sure that both are of the same vintage. Over time, the mukey values will 'drift' and some records may no
# longer join. Find the date for the most recent survey by looking at the end of the Credits section in the
# gSSURGO and the Valu1 tametadata for gSSURGO and the Valu1 table by finding
#
# gSSURGO metadata: 
#
# Valu1 metadata:  Look for the date at the end of the Credits section.

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
def CreateNewTable(newTable, columnNames, columnInfo):
    # Create new table. Start with in-memory and then export to geodatabase table
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
        outputTbl = os.path.join(os.path.dirname(newTable), os.path.basename(newTable))
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        for i, fldName in enumerate(columnNames):
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if fldName.lower().endswith("key"):
                # Per SSURGO standards, key fields should be string. They come from Soil Data Access as long integer.
                dataType = 'text'
                length = 30

            arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)

        return outputTbl

    except:
        errorMsg()
        return False

## ===================================================================================
def AttributeRequest(sdaURL, outputTable, sQuery):
    # POST REST which uses urllib and JSON
    #
    # Uses an InsertCursor to populate the new outputTable
    #
    # Send query to SDM Tabular Service, returning data in JSON format,
    # creates a new table and loads the data into a new Table in the geodatabase
    # Returns a list of key values and if keyField = "mukey", returns a dictionary like the output table

    try:
        keyList = list()
        
        if sQuery == "":
            raise MyError, "Missing query string"

        # Tabular service to append to SDA URL
        url = sdaURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)
        #time.sleep(2)

        dRequest = dict()
        dRequest["format"] = "JSON+COLUMNNAME+METADATA"
        dRequest["query"] = sQuery

        #PrintMsg(" \nURL: " + url)
        #PrintMsg("QUERY: " + sQuery)

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            return keyList
            #raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        PrintMsg(" \n\tImporting attribute data to " + os.path.basename(outputTable) + "...", 0)
        PrintMsg(" \nColumn names in SDA data: \n" + str(columnNames), 1)

        # Create new table to hold data
        if arcpy.Exists(outputTable):
            arcpy.Delete_management(outputTable)
            
        outputTable = CreateNewTable(outputTable, columnNames, columnInfo)

        if "mukey" in columnNames:
            keyIndx = columnNames.index("mukey")

        elif "cokey" in columnNames:
            keyIndx = columnNames.index("cokey")

        else:
            keyIndx = 0

        # Look at fields in new table
        newFields = [fld.name for fld in arcpy.Describe(outputTable).fields]
        
        PrintMsg(" \n" + outputTable + " fields: " + ",".join(newFields), 1)

        with arcpy.da.InsertCursor(outputTable, columnNames) as cur:
            for rec in dataList:
                cur.insertRow(rec)
                keyList.append(rec[keyIndx])


        #PrintMsg("\tPopulated " + os.path.basename(outputTable) + " with " + Number_Format(len(keyList), 0, True) + " records", 1)

        return keyList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def GetKeys(theInput, keyField):
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
            sqlClause = ("DISTINCT " + keyField, "ORDER BY " + keyField)
            keyList = list()

            with arcpy.da.SearchCursor(theInput, [keyField], sql_clause=sqlClause) as cur:
                for rec in cur:
                    keyList.append(int(rec[0]))

            #PrintMsg("\tmukey list: " + str(keyList), 1)
            return keyList

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
        locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateOutputTableMu(valuTable, depthList, dPct, mukeyList):
    #
    try:
        # If this table does not already exist, create the output table and add required fields
        # Populate mukey column using DISTINCT horizon table information

        #PrintMsg(" \nAdding new fields to table: " + os.path.basename(theMuTable), 0)
        outputDB = os.path.dirname(valuTable)

        if not arcpy.Exists(valuTable):
            #PrintMsg(" \nCreating new table: " + os.path.basename(valuTable), 0)
            arcpy.CreateTable_management(os.path.dirname(valuTable), os.path.basename(valuTable))

            # Add fields for AWS
            for rng in depthList:
                # Create the AWS fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "aws" + str(td) + "_" + str(bd)
                arcpy.AddField_management(valuTable, awsField, "FLOAT", "", "", "", awsField)  # Integer is more appropriate

            for rng in depthList:
                # Create the AWS fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "tk" + str(td) + "_" + str(bd) + "a"
                arcpy.AddField_management(valuTable, awsField, "FLOAT", "", "", "", awsField)

            arcpy.AddField_management(valuTable, "musumcpcta", "SHORT", "", "", "")

            # Add Fields for SOC
            for rng in depthList:
                # Create the SOC fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                socField = "soc" + str(td) + "_" + str(bd)
                arcpy.AddField_management(valuTable, socField, "FLOAT", "", "", "", socField)  # Integer is more appropriate

            for rng in depthList:
                # Create the SOC thickness fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                socField = "tk" + str(td) + "_" + str(bd) + "s"
                arcpy.AddField_management(valuTable, socField, "FLOAT", "", "", "", socField)

            arcpy.AddField_management(valuTable, "musumcpcts", "SHORT", "", "", "")


            if mainRuleName == "NCCPI - National Commodity Crop Productivity Index (Ver 2.0)":
                # Add fields for NCCPI version 2
                #
                arcpy.AddField_management(valuTable, "nccpi2cs", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi2sg", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi2co", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi2all", "FLOAT", "", "", "")

            elif mainRuleName == "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)":
                # Add fields for NCCPI version 3
                #  "mukey", "NCCPI2CORN", "NCCPI2SOY", "NCCPI2COT","NCCPI2SG", "NCCPI2ALL"
                arcpy.AddField_management(valuTable, "nccpi3corn", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi3soy", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi3cot", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi3sg", "FLOAT", "", "", "")
                arcpy.AddField_management(valuTable, "nccpi3all", "FLOAT", "", "", "")

            else:
                PrintMsg(" \n\tNCCPI version 2 or 3 not found", 1)
                #raise MyError, "Problem handling mainrule: " + mainRuleName

            # Add fields for root zone depth and root zone available water supply
            arcpy.AddField_management(valuTable, "pctearthmc", "SHORT", "", "", "")
            arcpy.AddField_management(valuTable, "rootznemc", "LONG", "", "", "")
            arcpy.AddField_management(valuTable, "rootznaws", "LONG", "", "", "")

            # Add field for droughty soils
            arcpy.AddField_management(valuTable, "droughty", "SHORT", "", "", "")

            # Add field for potential wetland soils
            arcpy.AddField_management(valuTable, "pwsl1pomu", "SHORT", "", "", "")

            # Add field for mapunit-sum of ALL component-comppct_r values
            arcpy.AddField_management(valuTable, "musumcpct", "SHORT", "", "", "")

            # Add Mukey field (primary key)
            arcpy.AddField_management(valuTable, "mukey", "TEXT", "", "", "30", "mukey")


        # Populate mukey and mapunit-sum-of-comppct_r values for each survey area
        outcur = arcpy.da.InsertCursor(valuTable, ["mukey", "musumcpct"])

        PrintMsg(" \nPopulating mutable with mukey and sum of comppct_r", 1)

        for mukey in mukeyList:
            #PrintMsg("\t" + str(mukey), 1)
            try:
                comppct = dPct[str(mukey)][0]
            except:
                comppct = 0

            outcur.insertRow([str(mukey), comppct])

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateOutputTableCo(coValu, depthList):
    # Create the CoValu table as coValu. Probably should rename this component level ratings table
    # The new input field is created using adaptive code from another script.
    #
    try:
        #PrintMsg(" \nCreating new output table (" + os.path.basename(coValu) + ") for component level data", 0)

        outputDB = os.path.dirname(coValu)

        if not arcpy.Exists(coValu):

            arcpy.CreateTable_management(os.path.dirname(coValu), os.path.basename(coValu))

            # Add fields appropriate for the component level restrictions
            # mukey,cokey, compName, localphase, compPct, comppct, resdept, restriction

            arcpy.AddField_management(coValu, "COKEY", "TEXT", "", "", "30", "COKEY")
            arcpy.AddField_management(coValu, "COMPNAME", "TEXT", "", "", "60", "COMPNAME")
            arcpy.AddField_management(coValu, "LOCALPHASE", "TEXT", "", "", "40", "LOCALPHASE")
            arcpy.AddField_management(coValu, "COMPPCT_R", "SHORT", "", "", "", "COMPPCT_R")

            for rng in depthList:
                # Create the AWS fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "AWS" + str(td) + "_" + str(bd)
                arcpy.AddField_management(coValu, awsField, "FLOAT", "", "", "", awsField)


            for rng in depthList:
                # Create the TK-AWS fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "TK" + str(td) + "_" + str(bd) + "A"
                arcpy.AddField_management(coValu, awsField, "FLOAT", "", "", "", awsField)

            arcpy.AddField_management(coValu, "MUSUMCPCTA", "SHORT", "", "", "")

            for rng in depthList:
                # Create the SOC fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "SOC" + str(td) + "_" + str(bd)
                arcpy.AddField_management(coValu, awsField, "FLOAT", "", "", "")

            for rng in depthList:
                # Create the rest of the SOC thickness fields in a loop
                #
                td = rng[0]
                bd = rng[1]
                awsField = "TK" + str(td) + "_" + str(bd) + "S"
                arcpy.AddField_management(coValu, awsField, "FLOAT", "", "", "")
                arcpy.AddField_management(coValu, "MUSUMCPCTS", "SHORT", "", "", "")

            # Root Zone and root zone available water supply
            arcpy.AddField_management(coValu, "PCTEARTHMC", "SHORT", "", "", "")
            arcpy.AddField_management(coValu, "ROOTZNEMC", "LONG", "", "", "")
            arcpy.AddField_management(coValu, "ROOTZNAWS", "LONG", "", "", "")
            arcpy.AddField_management(coValu, "RESTRICTION", "TEXT", "", "", "254", "RESTRICTION")

            # Droughty soils
            arcpy.AddField_management(coValu, "DROUGHTY", "SHORT", "", "", "")

            # Add field for potential wetland soils
            arcpy.AddField_management(coValu, "PWSL1POMU", "SHORT", "", "", "")

            # Add primary key field
            arcpy.AddField_management(coValu, "MUKEY", "TEXT", "", "", "30", "MUKEY")

            # add attribute indexes for key fields
            arcpy.AddIndex_management(coValu, "MUKEY", "Indx_Res2Mukey", "NON_UNIQUE", "NON_ASCENDING")
            arcpy.AddIndex_management(coValu, "COKEY", "Indx_ResCokey", "UNIQUE", "NON_ASCENDING")

        # populate component level table with mukey and component data
        sqlClause = ("DISTINCT", "ORDER BY cokey")
        #PrintMsg(" \nApparent problem with DISTINCT COKEY clause for " + hzTable, 1)
        #lastCokey = 'xxxx'
        coCnt = 0
        hzCnt = int(arcpy.GetCount_management(hzTable).getOutput(0))
        #PrintMsg(" \nInput table " + hzTable + " has " + Number_Format(hzCnt, 0, True) + " records", 1)
        uniqueList = list()

        with arcpy.da.SearchCursor(hzTable, ["mukey", "cokey", "compname", "localphase", "comppct_r"], sql_clause=sqlClause) as incur:
            #incur.reset()
            # Populate component-level table from the horizon query table
            outcur = arcpy.da.InsertCursor(coValu, ["mukey", "cokey", "compname", "localphase", "comppct_r"])

            for inrec in incur:
                coCnt += 1
                outcur.insertRow(inrec)

            #PrintMsg(" \nUsing sql_clause " + str(sqlClause) + " we got " + Number_Format(coCnt, 0, True) + " components", 1)

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CheckTexture(mukey, cokey, desgnmaster, om, texture, lieutex, taxorder, taxsubgrp):
    # Is this an organic horizon? Look at desgnmaster and OM first. If those
    # don't help, look at chtexturegrp.texture next.
    #
    # if True: Organic, exclude from root zone calculations unless it is 'buried'
    # if False: Mineral, include in root zone calculations
    #
    # 01-26-2015
    #
    # According to Bob, if TAXORDER = 'Histosol' and DESGNMASTER = 'O' or 'L' then it should NOT be included in the RZAWS calculations
    #
    # If desgnmast = 'O' or 'L' and not (TAXORDER = 'Histosol' OR TAXSUBGRP like 'Histic%') then exclude this horizon from all RZAWS calcualtions.
    #
    # lieutext values: Slightly decomposed plant material, Moderately decomposed plant material,
    # Bedrock, Variable, Peat, Material, Unweathered bedrock, Sand and gravel, Mucky peat, Muck,
    # Highly decomposed plant material, Weathered bedrock, Cemented, Gravel, Water, Cobbles,
    # Stones, Channers, Parachanners, Indurated, Cinders, Duripan, Fragmental material, Paragravel,
    # Artifacts, Boulders, Marl, Flagstones, Coprogenous earth, Ashy, Gypsiferous material,
    # Petrocalcic, Paracobbles, Diatomaceous earth, Fine gypsum material, Undecomposed organic matter

    # According to Bob, any of the 'decomposed plant material', 'Muck, 'Mucky peat, 'Peat', 'Coprogenous earth' LIEUTEX
    # values qualify.
    #
    # This function does not determine whether the horizon might be a buried organic. That is done in CalcRZAWS1.
    #

    lieuList = ['Slightly decomposed plant material', 'Moderately decomposed plant material', \
    'Highly decomposed plant material', 'Undecomposed plant material', 'Muck', 'Mucky peat', \
    'Peat', 'Coprogenous earth']
    txList = ["CE", "COP-MAT", "HPM", "MPM", "MPT", "MUCK", "PDOM", "PEAT", "SPM", "UDOM"]

    try:

        if str(taxorder) == 'Histosols' or str(taxsubgrp).lower().find('histic') >= 0:
            # Always treat histisols and histic components as having all mineral horizons
            #if mukey == tmukey:
            #    PrintMsg("\tHistisol or histic: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
            return False

        elif desgnmaster in ["O", "L"]:
            # This is an organic horizon according to CHORIZON.DESGNMASTER OR OM_R
            #if mukey == tmukey:
            #    PrintMsg("\tO: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
            return True

        #elif om > 19:
            # This is an organic horizon according to CHORIZON.DESGNMASTER OR OM_R
        #    if mukey == tmukey:
        #        PrintMsg("\tHigh om_r: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
        #    return True

        elif str(texture) in txList:
            # This is an organic horizon according to CHTEXTUREGRP.TEXTURE
            #if mukey == tmukey:
            #    PrintMsg("\tTexture: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
            return True

        elif str(lieutex) in lieuList:
            # This is an organic horizon according to CHTEXTURE.LIEUTEX
            #if mukey == tmukey:
            #    PrintMsg("\tLieutex: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
            return True

        else:
            # Default to mineral horizon if it doesn't match any of the criteria
            #if mukey == tmukey:
            #    PrintMsg("\tDefault mineral: " + cokey + ", " + str(taxorder) + ", " + str(taxsubgrp), 1)
            return False

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CheckBulkDensity(sand, silt, clay, bd, mukey, cokey):
    # Bob's check for a dense layer
    # If sand, silt or clay are missing then we default to Dense layer = False
    # If the sum of sand, silt, clay are less than 100 then we default to Dense layer = False
    # If a single sand, silt or clay value is NULL, calculate it

    try:

        #if mukey == tmukey:
        #    PrintMsg("\tCheck for Dense: " + str(mukey) + ", " + str(cokey) + ", " + \
        #    str(sand) + ", " + str(silt) + ", " + str(clay) + ", " + str(bd), 1)

        txlist = [sand, silt, clay]

        if bd is None:
            # This is not a Dense Layer
            #if mukey == tmukey:
            #    PrintMsg("\tMissing bulk density", 1)
            return False

        if txlist.count(None) == 1:
            # Missing a single total_r value, calculate it
            if txlist[0] is None:
                sand = 100.0 - silt - clay

            elif silt is None:
                silt = 100.0 - sand - clay

            else:
                clay = 100.0 - sand - silt

            txlist = [sand, silt, clay]

        if txlist.count(None) > 0:
            # Null values for more than one, return False
            #if mukey == tmukey:
            #    PrintMsg("\tDense layer with too many null texture values", 1)
            return False

        if round(sum(txlist), 1) <> 100.0:
            # Cannot run calculation, default value is False
            #if mukey == tmukey:
            #    PrintMsg("\tTexture values do not sum to 100", 1)
            return False

        # All values required to run the Dense Layer calculation are available

        a = bd - ((( sand * 1.65 ) / 100.0 ) + (( silt * 1.30 ) / 100.0 ) + (( clay * 1.25 ) / 100.0))

        b = ( 0.002081 * sand ) + ( 0.003912 * silt ) + ( 0.0024351 * clay )

        if a > b:
            # This is a Dense Layer
            #if mukey == tmukey:
            #    PrintMsg("\tDense layer: a = " + str(a) + " and   b = " + str(b) + " and BD = " + str(bd), 1)

            return True

        else:
            # This is not a Dense Layer
            #if mukey == tmukey:
            #    PrintMsg("\tNot a Dense layer: a = " + str(a) + " and   b = " + str(b) + " and BD = " + str(bd), 1)

            return False

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcRZDepth(db, coTable, hzTable, maxD, dPct, dCR):
    #
    # Look at soil horizon properties to adjust the root zone depth.
    # This is in addition to the standard component restrictions
    #
    # Read the component restrictions into a dictionary, then read through the
    # QueryTable_Hz table, calculating the final component rootzone depth
    #
    # Only major components are used
    # Components with COMPKIND = 'Miscellaneous area' or NULL are filtered out.
    # Components with no horizon data are assigned a root zone depth of zero.
    #
    # Horizons with NULL hzdept_r or hzdepb_r are filtered out
    # Horizons with hzdept_r => hzdepb_r are filtered out
    # O horizons or organic horizons from the surface down to the first mineral horizon
    # are filtered out.
    #
    # Horizon data below 150cm or select component restrictions are filtered out.
    # A Dense layer calculation is also included as an additional horizon-specific restriction.

    try:
        dComp = dict()      # component level data for all component restrictions
        dComp2 = dict()     # store all component level data plus default values
        coList = list()

        # Create dictionaries and lists
        dMapunit = dict()   # store mapunit weighted restriction depths

        # FIELDS LIST FOR INPUT TABLE
        # areasymbol, mukey, musym, muname, mukname,
        # cokey, compct, compname, compkind, localphase,
        # taxorder, taxsubgrp, ec, pH, dbthirdbar, hzname,
        # hzdesgn, hzdept, hzdepb, hzthk, sand,
        # silt, clay, om, reskind, reshard,
        # resdept, resthk, texture, lieutex

        # All reskind values: Strongly contrasting textural stratification, Lithic bedrock, Densic material,
        # Ortstein, Permafrost, Paralithic bedrock, Cemented horizon, Undefined, Fragipan, Plinthite,
        # Abrupt textural change, Natric, Petrocalcic, Duripan, Densic bedrock, Salic,
        # Human-manufactured materials, Sulfuric, Placic, Petroferric, Petrogypsic
        #
        # Using these restrictions:
        # Lithic bedrock, Paralithic bedrock, Densic bedrock, Fragipan, Duripan, Sulfuric

        # Other restrictions include pH < 3.5 and EC > 16

        crFlds = ["cokey","reskind", "reshard", "resdept_r"]
        sqlClause = (None, "ORDER BY cokey, resdept_r ASC")

        # ********************************************************
        #
        # Read the QueryTable_HZ and adjust the component restrictions for additional
        # issues such as pH, EC, etc.
        #
        # Save these new restriction values to dComp dictionary
        #
        # Only process major-earthy components...
        #whereClause = "component.compkind <> 'Miscellaneous area' and component.compkind is not Null and component.majcompflag = 'Yes'"
        whereClause = "compkind <> 'Miscellaneous area' and compkind is not Null and majcompflag = 'Yes'"

        sqlClause = (None, "ORDER BY mukey, comppct_r DESC, cokey, hzdept_r ASC")


        # CURRENT PROBLEM: missing texture and lieutex 
        curFlds = ["mukey", "cokey", "compname", "compkind", "localphase", "comppct_r", "taxorder", "taxsubgrp", "hzname", "desgnmaster", "hzdept_r", "hzdepb_r", "sandtotal_r", "silttotal_r", "claytotal_r", "om_r", "dbthirdbar_r", "ph1to1h2o_r", "ec_r", "awc_r", "texture", "lieutex"]
        # mukey, musymbol, muname, cokey, compname, comppct_r, majcompflag, compkind, localphase, otherph, taxorder, taxsubgrp, hydricrating,
        # drainagecl, hzname, desgnmaster, chkey, hzdept_r, hzdepb_r, awc_r, ksat_r, sandtotal_r, silttotal_r, claytotal_r, vfsand, om_r,
        # dbthirdbar_r, ph1to1h2o_r, ec_r, fragvol
        resList = ['Lithic bedrock','Paralithic bedrock','Densic bedrock', 'Fragipan', 'Duripan', 'Sulfuric']

        lastCokey = "xxxx"
        lastMukey = 'xxxx'

        # Display status of processing input table containing horizon data and component restrictions
        PrintMsg(" \nReading table (" + os.path.basename(hzTable) + " using fields: " + ",".join(curFlds), 1)

        with arcpy.da.SearchCursor(hzTable, curFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            # Reading horizon-level data
            for rec in cur:

                # ********************************************************
                #
                # Read QueryTable_HZ record
                mukey, cokey, compName, compKind, localPhase, compPct, taxorder, taxsubgrp, hzname, desgnmaster, hzDept, hzDepb, sand, silt, clay, om, bd, pH, ec, awc, texture, lieutex = rec

                # Initialize component restriction depth to maxD
                dComp2[cokey] = [mukey, compName, localPhase, compPct, maxD, ""]

                if lastCokey != cokey:
                    # Accumulate a list of components for future use
                    lastCokey = cokey
                    coList.append(cokey)

                if hzDept < maxD:
                    # ********************************************************
                    # For horizons above the floor level (maxD), look for other restrictive
                    # layers based on horizon properties such as pH, EC and bulk density.
                    # Start with the top horizons and work down.

                    # initialize list of restrictions
                    resKind = ""
                    restriction = list()

                    bOrganic = CheckTexture(mukey, cokey, desgnmaster, om, texture, lieutex, taxorder, taxsubgrp)

                    if not bOrganic:
                        # calculate alternate dense layer per Dobos
                        bDense = CheckBulkDensity(sand, silt, clay, bd, mukey, cokey)

                        if bDense:
                            # use horizon top depth for the dense layer
                            restriction.append("Dense")
                            resDept = hzDept

                        # Not sure whether these horizon property checks should be skipped for Organic
                        # Bob said to only skip Dense Layer check, but VALU table RZAWS looks like all
                        # horizon properties were skipped.
                        #
                        # If we decide to skip EC and pH horizon checks for histosols/histic, use this query
                        # Example Pongo muck in North Carolina that have low pH but no other restriction
                        #
                        if str(taxorder) != 'Histosols' and str(taxsubgrp).lower().find('histic') == -1:
                            # Only non histosols/histic soils will be checked for pH or EC restrictive horizons
                            if pH <= 3.5 and pH is not None:
                                restriction.append("pH")
                                resDept = hzDept
                                #if mukey == tmukey:
                                #    PrintMsg("\tpH restriction at " + str(resDept) + "cm", 1)

                        if ec >= 16.0 and ec is not None:
                            # Originally I understood that EC > 12 is a restriction, but Bob says he is
                            # now using 16.
                            restriction.append("EC")
                            resDept = hzDept
                            #if mukey == tmukey:
                            #    PrintMsg("\tEC restriction at " + str(resDept) + "cm", 1)

                        #if bd >= 1.8:
                        #    restriction.append("BD")
                        #    resDept = hzDept

                        #if awc is None:
                        #    restriction.append("AWC")
                        #    resDept = hzDept

                    # ********************************************************
                    #
                    # Finally, check for one of the standard component restrictions
                    #
                    if cokey in dCR:
                        resDepth2, resKind = dCR[cokey]

                        if hzDept <= resDepth2 < hzDepb:
                            # This restriction may not be at the top of the horizon, thus we
                            # need to override this if one of the other restrictions exists for this
                            # horizon

                            if len(restriction) == 0:
                                # If this is the only restriction, set the restriction depth
                                # to the value from the corestriction table.
                                resDept = resDepth2

                            # Adding this restriction name to the list even if there are others
                            # May want to take this out later
                            restriction.append(resKind)

                    # ********************************************************
                    #
                    if len(restriction) > 0:
                        # Found at least one restriction for this horizon

                        if not cokey in dComp:
                            # if there are no higher restrictions for this component, save this one
                            # to the dComp dictionary as the upper-most restriction
                            #
                            dComp[cokey] = [mukey, compName, localPhase, compPct, resDept, restriction]

        # Load restrictions from dComp into dComp2 so that there is complete information for all components

        for cokey in dComp2:
            try:
                dComp2[cokey] = dComp[cokey]

            except:
                pass

        # Return the dictionary containing restriction depths and the dictionary containing defaults
        return dComp2

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return dComp2

    except:
        errorMsg()
        return dComp2


## ===================================================================================
def GetCoRestrictions(crTable, maxD, resList):
    #
    # Returns a dictionary of top component restrictions for root growth
    #
    # resList is a comma-delimited string of reskind values, surrounded by parenthesis
    #
    # Get component root zone depth from QueryTable_CR and load into dictionary (dCR)
    # This is NOT the final root zone depth. This information will be compared with the
    # horizon soil properties to determine the final root zone depth.

    try:
        rSQL = "resdept_r < " + str(maxD) + " and reskind in " + resList
        sqlClause = (None, "ORDER BY cokey, resdept_r ASC")
        #PrintMsg("\tGetting corestrictions matching: " + resList, 1)

        dRestrictions = dict()

        # Get the top component restriction from the sorted table
        with arcpy.da.SearchCursor(crTable, ["cokey", "resdept_r", "reskind"], where_clause=rSQL, sql_clause=sqlClause) as cur:
            for rec in cur:
                cokey, resDept, reskind = rec
                #PrintMsg("Restriction: " + str(rec), 1)

                if not cokey in dRestrictions:
                    dRestrictions[str(cokey)] = resDept, reskind

        return dRestrictions

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return dict()

    except:
        errorMsg()
        return dict()


## ===================================================================================
#def CalcRZAWS(inputDB, outputDB, td, bd, coValu, theMuTable, dRestrictions, maxD, dPct):
def CalcRZAWS(db, outputDB, td, bd, coValu, muTable, hzTable, valuTable, dRestrictions, maxD, dPct):
    #         inputDB, outputDB, td, bd, coValu, hzTable, valuTable, dRestrictions, maxD, dPct
    # Create a component-level summary table
    # Calculate mapunit-weighted average for each mapunit and write to a mapunit-level table
    # Need to filter out compkind = 'Miscellaneous area' for RZAWS
    # dRestrictions[cokey] = [mukey, compName, localPhase, compPct, resDept, restriction]

    try:
        import decimal

        env.workspace = outputDB

        # Using the same component horizon table that has been
        #queryTbl = os.path.join(outputDB, "QueryTable_Hz")

        numRows = int(arcpy.GetCount_management(hzTable).getOutput(0))

        PrintMsg(" \n\tCalculating Root Zone AWS for " + str(td) + " to " + str(bd) + "cm...", 0)

        # hzTable fields
        qFieldNames = ["mukey", "cokey", "comppct_r",  "compname", "localphase", "majcompflag", "compkind", "taxorder", "taxsubgrp", "desgnmaster", "om_r", "awc_r", "hzdept_r", "hzdepb_r", "texture", "lieutex"]

        # Open edit session on geodatabase to allow multiple update cursors
        with arcpy.da.Editor(db) as edit:

            # Output fields for root zone and droughty
            # Was writing to muTable, but these fields don't exist there. Switching to Valu1 table..
            muFieldNames = ["mukey", "pctearthmc", "rootznemc", "rootznaws", "droughty"]
            #muCursor = arcpy.da.UpdateCursor(muTable, muFieldNames)
            muCursor = arcpy.da.UpdateCursor(valuTable, muFieldNames)

            # Open component-level output table for updates
            #coCursor = arcpy.da.InsertCursor(coValu, coFieldNames)
            coFieldNames = ["mukey", "cokey", "compname", "localphase", "comppct_r", "pctearthmc", "rootznemc", "rootznaws", "restriction"]
            #coCursor = arcpy.da.UpdateCursor(coTable, coFieldNames)
            coCursor = arcpy.da.UpdateCursor(coValu, coFieldNames)

            # Process query table using cursor, write out horizon data for each major component
            sqlClause = [None, "order by mukey, comppct_r DESC, cokey, hzdept_r ASC"]

            inCur = arcpy.da.SearchCursor(hzTable, qFieldNames, sql_clause=sqlClause)

            arcpy.SetProgressor("step", "Reading hzTable...",  0, numRows, 1)

            # Create dictionaries to handle the mapunit and component summaries
            dMu = dict()
            dComp = dict()

            # I may have to pull the sum of component percentages out of this function?
            # It seems to work OK for the earthy-major components, but will not work for
            # the standard AWS calculations. Those 'Miscellaneous area' components with no horizon data
            # are excluded from the Query table because it does not support Outer Joins.
            #
            mCnt = 0
            #PrintMsg("\tmukey, cokey, comppct, top, bottom, resdepth, thickness, aws", 0)

            # TEST: keep list of cokeys as a way to track the top organic horizons
            skipList = list()

            for rec in inCur:
                # read each horizon-level input record from QueryTable_HZ ...
                #
                mukey, cokey, compPct, compName, localPhase, mjrFlag, cKind, taxorder, taxsubgrp, desgnmaster, om, awc, top, bot, texture, lieutex = rec

                if mjrFlag == "Yes" and cKind != "Miscellaneous area" and cKind is not None:

                    # For major-earthy components
                    # Get restriction information from dictionary

                    # For non-Miscellaneous areas with no horizon data, set hzdepth values to zero so that
                    # PWSL and Droughty will get populated with zeros instead of NULL.
                    if top is None and bot is None:

                        if not cokey in dComp:
                            dComp[cokey] = mukey, compName, localPhase, compPct, 0, 0, ""

                    try:
                        # mukey, compName, localPhase, compPct, resDept, restriction
                        # rDepth is the component restriction depth or calculated horizon restriction from CalcRZDepth1 function

                        # mukey, compName, localPhase, compPct, resDept, restriction] = dRestrictions
                        d1, d2, d3, d4, rDepth, restriction = dRestrictions[cokey]
                        cBot = min(rDepth, bot, maxD)  # 01-05-2015 Added maxD because I found 46 CONUS mapunits with a ROOTZNEMC > 150

                        #if mukey == tmukey and rDepth != 150:
                        #    PrintMsg("\tRestriction, " + str(mukey) + ", " + str(cokey) + ", " + str(rDepth) + ", " + str(restriction), 1)

                    except:
                        #errorMsg()
                        cBot = min(maxD, bot)
                        restriction = []
                        rDepth = maxD

                        #if mukey == tmukey:
                        #    PrintMsg("RestrictionError, " + str(mukey) + ", " + str(cokey) + ", " + str(rDepth) + ", " + str(restriction), 1)

                    bOrganic = CheckTexture(mukey, cokey, desgnmaster, om, texture, lieutex, taxorder, taxsubgrp)

                    #if mukey == tmukey and bOrganic:
                    #    PrintMsg("Organic: " + str(mukey) + ", " + str(cokey) )


                    # fix awc_r to 2 decimal places
                    if awc is None:
                        awc = 0.0

                    else:
                        awc = round(awc, 2)

                    # Reasons for skipping RZ calculations on a horizon:
                    #   1. Desgnmaster = O, L and Taxorder != Histosol and is at the surface
                    #   2. Do I need to convert null awc values to zero?
                    #   3. Below component restriction or horizon restriction level

                    if bOrganic and not cokey in skipList:
                        # Organic surface horizon - Not using this horizon in the calculations
                        useHz = False

                        #if mukey == tmukey:
                        #    PrintMsg("Organic, " + str(mukey) + ", " + str(cokey) + ", " + str(compPct) + ", " + str(desgnmaster) + ", " + taxorder  + ", " + str(top) + ", " + str(bot) + ", " + str(cBot)  + ", " + str(awc) + ", " + str(useHz), 1)

                    else:
                        # Mineral, Histosol, buried Organic, Bedrock or there is a horizon restriction (EC, pH - Using this horizon in the calculations
                        useHz = True
                        skipList.append(cokey)

                        # Looking for problems
                        #if mukey == tmukey:
                        #    PrintMsg("Mineral, " + str(mukey) + ", " + str(cokey)  + ", " + str(compPct) + ", " + str(desgnmaster) + ", " + str(taxorder) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(awc)  + ", " + str(useHz), 1)

                        # Attempt to fix component with a surface-level restriction that might be in an urban soil
                        if not cokey in dComp and cBot == 0:
                            dComp[cokey] = mukey, compName, localPhase, compPct, 0, 0, restriction

                            # Looking for problems
                            #if mukey == tmukey:
                            #    PrintMsg("MUKEY2: " + str(mukey) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(useHz), 1)

                    if top < cBot and useHz == True:
                        # If the top depth is less than the bottom depth, proceed with the calculation
                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = cBot - top
                        aws = float(hzT) * float(awc) * 10.0

                        # Looking for problems
                        #if mukey == tmukey:
                        #    PrintMsg("MUKEY3: " + str(mukey) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(useHz), 1)


                        if cokey in dComp:
                            # accumulate total thickness and total rating value by adding to existing component values
                            mukey, compName, localPhase, compPct, dHzT, dAWS, restriction = dComp[cokey]
                            dAWS = dAWS + aws
                            dHzT += hzT

                            dComp[cokey] = mukey, compName, localPhase, compPct, dHzT, dAWS, restriction

                        else:
                            # Create initial entry for this component using the first horizon
                            dComp[cokey] = mukey, compName, localPhase, compPct, hzT, aws, restriction

                    else:
                        # Do not include this horizon in the rootzone calculations
                        pass

                else:
                    # Not a major-earthy component, so write out everything BUT rzaws-related data (last values)
                    dComp[cokey] = mukey, compName, localPhase, compPct, None, None, None, None

                arcpy.SetProgressorPosition()

                # end of processing major-earthy components

            arcpy.ResetProgressor()

            # get the total number of major-earthy components from the dictionary count
            iComp = len(dComp)

            # Read through the component-level data and summarize to the mapunit level

            if iComp > 0:
                #PrintMsg(" \nSaving component average RZAWS to table... (" + str(iComp) + ")", 0 )
                arcpy.SetProgressor("step", "Saving component data...",  0, iComp, 1)
                iCo = 0 # count component records written to theCompTbl

                for corec in coCursor:
                    mukey, cokey, compName, localPhase, compPct, pctearthmc, rDepth, aws, restrictions = corec

                    try:
                        # get sum of component percent for the mapunit
                        pctearthmc = float(dPct[mukey][1])   # sum of comppct_r for all major components Test 2014-10-07

                        # get rootzone data from dComp
                        mukey1, compName1, localPhase1, compPct1, hzT, awc, restriction = dComp[cokey]

                    except:
                        pctearthmc = 0
                        hzT = None
                        rDepth = None
                        awc = None
                        restriction = []

                    # calculate component percentage adjustment
                    if pctearthmc > 0 and not awc is None:
                        # If there is no data for any of the component horizons, could end up with 0 for
                        # sum of comppct_r

                        adjCompPct = float(compPct) / float(pctearthmc)

                        # adjust the rating value down by the component percentage and by the sum of the usable horizon thickness for this component
                        aws = adjCompPct * float(awc) # component rating

                        if restriction is None:
                            restrictions = ''

                        elif len(restriction) > 0:
                            restrictions = ",".join(restriction)

                        else:
                            restrictions = ''

                        corec = mukey, cokey, compName, localPhase, compPct, pctearthmc, hzT, aws, restrictions

                        coCursor.updateRow(corec)
                        iCo += 1

                        # Weight hzT for ROOTZNEMC by component percent
                        hzT = (float(hzT) * float(compPct) / pctearthmc)

                        if mukey in dMu:
                            val1, val2, val3 = dMu[mukey]
                            dMu[mukey] = pctearthmc, (hzT + val2), (aws + val3)

                        else:
                            # first entry for map unit ratings
                            dMu[mukey] = pctearthmc, hzT, aws

                        # PrintMsg("Mapunit " + mukey + ":" + cokey + "  " + str(dMu[mukey]), 1)

                    else:
                        # Populate component level record for a component with no AWC
                        corec = mukey, cokey, compName, localPhase, compPct, None, None, None, ""
                        coCursor.updateRow(corec)
                        iCo += 1

                    arcpy.SetProgressorPosition()

                arcpy.ResetProgressor()

            else:
                raise MyError, "No component data in dictionary dComp"

            if len(dMu) > 0:
                PrintMsg(" \n\tSaving map unit average RZAWS to table...(" + str(len(dMu)) + ")", 0 )

            else:
                raise MyError, "No map unit information in dictionary dMu"

            # Save root zone available water supply and droughty soils to output map unit table
            #
            PrintMsg(" \nUpdating muTable: " + muTable, 1)
            
            for murec in muCursor:
                mukey, pctearthmc, rootznemc, rootznaws, droughty = murec

                try:
                    rec = dMu[mukey]
                    pct, rootznemc, rootznaws = rec
                    pctearthmc = dPct[mukey][1]

                    if rootznemc > 150.0:
                        # This is a bandaid for components that have horizon problems such
                        # overlapping that causes the calculated total to exceed 150cm.
                        rootznemc = 150.0

                    rootznaws = round(rootznaws, 0)
                    rootznemc = round(rootznemc, 0)

                    if rootznaws > 152:
                        droughty = 0

                    else:
                        droughty = 1

                except:
                    pctearthmc = 0
                    rootznemc = None
                    rootznaws = None

                murec = mukey, pctearthmc, rootznemc, rootznaws, droughty
                muCursor.updateRow(murec)


            PrintMsg("", 0)

            return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False


## ===================================================================================
def CalcRZAWS_NeedsFix(inputDB, outputDB, td, bd, coValu, hzTable, valuTable, dRestrictions, maxD, dPct):
    # Create a component-level summary table
    # Calculate mapunit-weighted average for each mapunit and write to a mapunit-level table
    # Need to filter out compkind = 'Miscellaneous area' for RZAWS
    # dRestrictions[cokey] = [mukey, compName, localPhase, compPct, resDept, restriction]

    try:
        import decimal

        env.workspace = outputDB

        # Using the same component horizon table that has been
        queryTbl = hzTable

        numRows = int(arcpy.GetCount_management(queryTbl).getOutput(0))

        PrintMsg(" \nCalculating Root Zone AWS for " + str(td) + " to " + str(bd) + "cm...", 0)
        arcpy.SetProgressorLabel("Calculating Root Zone AWS")

        # QueryTable_HZ fields
        qFieldNames = ["mukey", "cokey", "comppct_r",  "compname", "localphase", "majcompflag", "compkind", "taxorder", "taxsubgrp", "desgnmaster", "om_r", "awc_r", "hzdept_r", "hzdepb_r", "texture", "lieutex"]

        #arcpy.SetProgressorLabel("Creating output tables using dominant component...")
        #arcpy.SetProgressor("step", "Calculating root zone available water supply..." , 0, numRows, 1)

        # Open edit session on geodatabase to allow multiple update cursors
        with arcpy.da.Editor(inputDB) as edit:

            # initialize list of components with horizon overlaps
            #badCo = list()

            # Output fields for root zone and droughty
            muFieldNames = ["mukey", "pctearthmc", "rootznemc", "rootznaws", "droughty"]
            muCursor = arcpy.da.UpdateCursor(valuTable, muFieldNames)

            # Open component-level output table for updates
            #coCursor = arcpy.da.InsertCursor(coValu, coFieldNames)
            coFieldNames = ["mukey", "cokey", "compname", "localphase", "comppct_r", "pctearthmc", "rootznemc", "rootznaws", "restriction"]
            coCursor = arcpy.da.UpdateCursor(coValu, coFieldNames)

            # Process query table using cursor, write out horizon data for each major component
            sqlClause = [None, "order by mukey, comppct_r DESC, cokey, hzdept_r ASC"]
            iCnt = int(arcpy.GetCount_management(queryTbl).getOutput(0))

            # For root zone calculations, we only want earthy, major components
            #PrintMsg(" \nFiltering components in Query_HZ for CalcRZAWS1 function", 1)
            #
            # Major-Earthy Components
            #hzSQL = "component.compkind <> 'Miscellaneous area' and component.compkind is not NULL and component.majcompflag = 'Yes'"
            # All Components

            inCur = arcpy.da.SearchCursor(queryTbl, qFieldNames, sql_clause=sqlClause)

            # Create dictionaries to handle the mapunit and component summaries
            dMu = dict()
            dComp = dict()

            # I may have to pull the sum of component percentages out of this function?
            # It seems to work OK for the earthy-major components, but will not work for
            # the standard AWS calculations. Those 'Miscellaneous area' components with no horizon data
            # are excluded from the Query table because it does not support Outer Joins.
            #
            mCnt = 0
            #PrintMsg("\tmukey, cokey, comppct, top, bottom, resdepth, thickness, aws", 0)

            # TEST: keep list of cokeys as a way to track the top organic horizons
            skipList = list()

            for rec in inCur:
                # read each horizon-level input record from QueryTable_HZ ...
                #
                mukey, cokey, compPct, compName, localPhase, mjrFlag, cKind, taxorder, taxsubgrp, desgnmaster, om, awc, top, bot, texture, lieutex = rec

                if mjrFlag == "Yes" and cKind != "Miscellaneous area" and cKind is not None:
                    # For major-earthy components
                    # Get restriction information from dictionary

                    # For non-Miscellaneous areas with no horizon data, set hzdepth values to zero so that
                    # PWSL and Droughty will get populated with zeros instead of NULL.
                    if top is None and bot is None:

                        if not cokey in dComp:
                            dComp[cokey] = mukey, compName, localPhase, compPct, 0, 0, ""

                    try:
                        # mukey, compName, localPhase, compPct, resDept, restriction
                        # rDepth is the component restriction depth or calculated horizon restriction from CalcRZDepth1 function

                        # mukey, compName, localPhase, compPct, resDept, restriction] = dRestrictions
                        d1, d2, d3, d4, rDepth, restriction = dRestrictions[cokey]
                        cBot = min(rDepth, bot, maxD)  # 01-05-2015 Added maxD because I found 46 CONUS mapunits with a ROOTZNEMC > 150

                        #if mukey == tmukey and rDepth != 150:
                        #    PrintMsg("\tRestriction, " + str(mukey) + ", " + str(cokey) + ", " + str(rDepth) + " at " + str(restriction) + "cm", 1)

                    except:
                        #errorMsg()
                        cBot = min(maxD, bot)
                        restriction = []
                        rDepth = maxD

                        if mukey == tmukey:
                            PrintMsg("RestrictionError, " + str(mukey) + ", " + str(cokey) + ", " + str(rDepth) + ", " + str(restriction), 1)

                    bOrganic = CheckTexture(mukey, cokey, desgnmaster, om, texture, lieutex, taxorder, taxsubgrp)

                    # fix awc_r to 2 decimal places
                    if awc is None:
                        awc = 0.0

                    else:
                        awc = round(awc, 2)

                    # Reasons for skipping RZ calculations on a horizon:
                    #   1. Desgnmaster = O, L and Taxorder != Histosol and is at the surface
                    #   2. Do I need to convert null awc values to zero?
                    #   3. Below component restriction or horizon restriction level

                    if bOrganic:
                        # Organic surface horizon - Not using this horizon in the calculations
                        useHz = False

                        #if mukey == tmukey:
                        #    PrintMsg("Organic, " + str(mukey) + ", " + str(cokey) + ", " + str(compPct) + ", " + str(desgnmaster) + ", " + taxorder  + ", " + str(top) + ", " + str(bot) + ", " + str(cBot)  + ", " + str(awc) + ", " + str(useHz), 1)

                    else:
                        # Mineral, Histosol, buried Organic, Bedrock or there is a horizon restriction (EC, pH - Using this horizon in the calculations
                        useHz = True
                        skipList.append(cokey)

                        # Looking for problems
                        #if mukey == tmukey:
                        #    PrintMsg("Mineral, " + str(mukey) + ", " + str(cokey)  + ", " + str(compPct) + ", " + str(desgnmaster) + ", " + str(taxorder) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(awc)  + ", " + str(useHz), 1)

                        # Attempt to fix component with a surface-level restriction that might be in an urban soil
                        if not cokey in dComp and cBot == 0:
                            dComp[cokey] = mukey, compName, localPhase, compPct, 0, 0, restriction

                            # Looking for problems
                            #if mukey == tmukey:
                            #    PrintMsg("MUKEY2: " + str(mukey) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(useHz), 1)

                    if top < cBot and useHz == True:
                        # If the top depth is less than the bottom depth, proceed with the calculation
                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = cBot - top
                        aws = float(hzT) * float(awc) * 10.0 # volume in millimeters

                        # Looking for problems
                        #if mukey == tmukey:
                        #    PrintMsg("MUKEY3: " + str(mukey) + ", " + str(top) + ", " + str(bot) + ", " + str(cBot) + ", " + str(useHz), 1)


                        if cokey in dComp:
                            # accumulate total thickness and total rating value by adding to existing component values
                            mukey, compName, localPhase, compPct, dHzT, dAWS, restriction = dComp[cokey]
                            dAWS = dAWS + aws
                            dHzT += hzT
                            dComp[cokey] = mukey, compName, localPhase, compPct, dHzT, dAWS, restriction

                        else:
                            # Create initial entry for this component using the first horizon
                            dComp[cokey] = mukey, compName, localPhase, compPct, hzT, aws, restriction

                    else:
                        # Do not include this horizon in the rootzone calculations
                        pass

                else:
                    # Not a major-earthy component, so write out everything BUT rzaws-related data (last values)
                    dComp[cokey] = mukey, compName, localPhase, compPct, None, None, None, None

                #arcpy.SetProgressorPosition()

            # End of processing major-earthy horizon-level data

            #arcpy.ResetProgressor()

            # get the total number of major-earthy components from the dictionary count
            iComp = len(dComp)

            # Read through the component-level data and summarize to the mapunit level
            #
            if iComp > 0:
                #PrintMsg(" \nSaving component average RZAWS to table... (" + str(iComp) + ")", 0 )
                iCo = 0 # count component records written to theCompTbl

                for corec in coCursor:
                    mukey, cokey, compName, localPhase, compPct, pctearthmc, rDepth, aws, restrictions = corec

                    try:
                        # get sum of earthy major components percent for the mapunit
                        pctearthmc = float(dPct[mukey][1])   # sum of comppct_r for all major components Test 2014-10-07

                        # get rootzone data from dComp
                        mukey1, compName1, localPhase1, compPct1, hzT, awc, restriction = dComp[cokey]

                    except:
                        pctearthmc = 0
                        hzT = None
                        rDepth = None
                        awc = None
                        restriction = []

                    # calculate component percentage adjustment
                    if pctearthmc > 0 and not awc is None:
                        # If there is no data for any of the component horizons, could end up with 0 for
                        # sum of comppct_r

                        adjCompPct = float(compPct) / float(pctearthmc)
                        
                        

                        # adjust the rating value down by the component percentage and by the sum of the usable horizon thickness for this component
                        #aws = round(adjCompPct * float(awc), 2) # component volume
                        aws = float(adjCompPct) * float(awc) # component volume
                        PrintMsg(str(mukey) + ":" + str(cokey) + "\t" + str(compPct1) + ", " + str(round(adjCompPct, 2)), 1)

                        if restriction is None:
                            restrictions = ''

                        elif len(restriction) > 0:
                            restrictions = ",".join(restriction)

                        else:
                            restrictions = ''

                        corec = mukey, cokey, compName, localPhase, compPct, pctearthmc, hzT, aws, restrictions

                        coCursor.updateRow(corec)
                        iCo += 1

                        # Weight hzT for ROOTZNEMC by component percent
                        hzT = round((float(hzT) * float(compPct) / pctearthmc), 2)

                        if mukey in dMu:
                            val1, val2, val3 = dMu[mukey]
                            dMu[mukey] = pctearthmc, (hzT + val2), (aws + val3)

                        else:
                            # first entry for map unit ratings
                            dMu[mukey] = pctearthmc, hzT, aws

                        #if mukey == tmukey:
                        #    PrintMsg("Mapunit " + mukey + ":" + cokey + "  " + str(dMu[mukey]), 1)

                    else:
                        # Populate component level record for a component with no AWC
                        corec = mukey, cokey, compName, localPhase, compPct, None, None, None, ""
                        coCursor.updateRow(corec)
                        iCo += 1


            else:
                raise MyError, "No component data in dictionary dComp"

            if len(dMu) > 0:
                PrintMsg(" \nSaving map unit average RZAWS to table...", 0 )

            else:
                raise MyError, "No map unit information in dictionary dMu"

            # Final step. Save root zone available water supply and droughty soils to output map unit table
            #
            for murec in muCursor:
                mukey, pctearthmc, rootznemc, rootznaws, droughty = murec

                try:
                    rec = dMu[mukey]
                    pct, rootznemc, rootznaws = rec
                    pctearthmc = dPct[mukey][1]

                    if rootznemc > 150.0:
                        # This is a bandaid for components that have horizon problems such
                        # overlapping that causes the calculated total to exceed 150cm.
                        rootznemc = 150.0

                    rootznaws = round(rootznaws, 0)
                    rootznemc = round(rootznemc, 0)

                    if rootznaws > 152:
                        droughty = 0

                    else:
                        droughty = 1

                except:
                    pctearthmc = 0
                    rootznemc = None
                    rootznaws = None

                murec = mukey, pctearthmc, rootznemc, rootznaws, droughty
                try:
                    muCursor.updateRow(murec)

                except:
                    PrintMsg("RootzoneAWS for mukey " + str(mukey) + ": " + str(rootznaws), 1)
                    errorMsg()
                    raise MyError, ""
                    #

            PrintMsg("", 0)

            return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcAWS(db, coValu, valuTable, hzTable, dPct, depthList):
    # 
    # Create a component-level summary table
    # Calculate the standard mapunit-weighted available water supply for each mapunit and
    # add it to the map unit-level table.
    #

    try:
        # Using the same component horizon table that has been
        numRows = int(arcpy.GetCount_management(hzTable).getOutput(0))

        # mukey, cokey, compPct,val, top, bot
        qFieldNames = ["mukey", "cokey", "comppct_r", "awc_r", "hzdept_r", "hzdepb_r"]

        # Track map units that are missing data
        missingList = list()
        minusList = list()

        PrintMsg(" \nCalculating standard available water supply...", 0)
        arcpy.SetProgressorLabel("Calculating standard available water supply")
        #arcpy.SetProgressor("step", "Reading QueryTable_HZ ...",  1, len(depthList), 1)

        for rng in depthList:
            # Calculating and updating just one AWS column at a time
            #
            td = rng[0]
            bd = rng[1]
            #PrintMsg("\tUpdating AWS for " + str(td) + " to " + str(bd) + "cm", 1)
            #outputFields = "AWS" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "A"

            # Open output table Mu...All in write mode
            muFieldNames = ["MUKEY", "MUSUMCPCTA", "AWS" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "A"]
            coFieldNames = ["COKEY", "AWS" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "A"]

            # Create dictionaries to handle the mapunit and component summaries
            dMu = dict()
            dComp = dict()
            dSum = dict()     # store sum of comppct_r and total thickness for the component
            dHz = dict()      # Trying a new dictionary that will s

            #arcpy.SetProgressorLabel("Calculating available water supply for " + str(td) + " - " + str(bd) + "cm")
            #arcpy.SetProgressor("step", "Aggregating data for the dominant component..." , 0, numRows, 1)

            # Open edit session on geodatabase to allow multiple insert cursors
            with arcpy.da.Editor(db) as edit:

                # Open output mapunit-level table in update mode
                # MUKEY, AWS
                muCursor = arcpy.da.UpdateCursor(valuTable, muFieldNames)

                # Open output component-level table in write mode
                # MUKEY, AWS
                coCursor = arcpy.da.UpdateCursor(coValu, coFieldNames)

                # Process query table using a searchcursor, write out horizon data for each component
                # At this time, almost all components are being used! There is no filter.
                sqlClause = (None, "order by mukey, comppct_r DESC, cokey, hzdept_r ASC")
                #hzSQL = "compkind is not null and hzdept_r is not null"  # prevent divide-by-zero errors
                hzSQL = "hzdept_r is not null"  # prevent divide-by-zero errors by skipping components with no horizons

                iCnt = int(arcpy.GetCount_management(hzTable).getOutput(0))
                inCur = arcpy.da.SearchCursor(hzTable, qFieldNames, where_clause=hzSQL, sql_clause=sqlClause)

                for rec in inCur:
                    # read each horizon-level input record from the query table ...

                    mukey, cokey, compPct, awc, top, bot = rec

                    if awc is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(bot, bd) - max(top, td)   # usable thickness from this horizon

                        if hzT > 0:
                            aws = float(hzT) * float(awc) * 10

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horizon CHK
                                dComp[str(cokey)] = (mukey, compPct, hzT, aws)

                                # Update sum of comppct for dMu. Not sure why I need to do this.
                                if not mukey in dMu:
                                    dMu[mukey] = (compPct, 0, 0)

                                else:
                                    val0 = dMu[mukey][0]
                                    dMu[mukey] = (val0 + compPct, 0, 0)

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                # comppct does not change
                                mukey, compName, dHzT, dAWS = dComp[str(cokey)]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[str(cokey)] = (mukey, compPct, dHzT, dAWS)

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    PrintMsg("\t\t" + str(td) + " - " + str(bd) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for corec in coCursor:
                        # get component level data  CHK
                        cokey = str(corec[0])

                        if cokey in dComp:
                            # get component-level values...
                            dRec = dComp[cokey]
                            mukey, compPct, hzT, awc = dRec
                            mukey = str(mukey)  # not sure if I need this

                            # get sum of component percent for the mapunit  CHK
                            try:
                                # Value[0] is for all components,
                                # Value[1] is just for major-earthy components,
                                # Value[2] is all major components
                                # Value[3] is earthy components
                                sumCompPct = float(dPct[mukey][0])

                            except:
                                # set the component percent to zero if it is not found in the
                                # dictionary. This is probably a 'Miscellaneous area' not included in the  CHK
                                # data or it has no horizon information.
                                sumCompPct = 0

                            # calculate component percentage adjustment
                            if sumCompPct > 0:
                                # If there is no data for any of the component horizons, could end up with 0 for
                                # sum of comppct_r

                                #adjCompPct = float(compPct) / sumCompPct   # WSS method
                                adjCompPct = compPct / 100.0                # VALU table method

                                # adjust the rating value down by the component percentage and by the sum of the usable horizon thickness for this component
                                aws = round((adjCompPct * awc), 2) # component rating

                                corec[1] = aws
                                hzT = hzT * adjCompPct    # Adjust component share of horizon thickness by comppct
                                corec[2] = hzT             # This is new for the TK0_5A column
                                coCursor.updateRow(corec)

                                # Update component values in component dictionary   CHK
                                # Not sure what dComp is being used for ???
                                dComp[cokey] = mukey, compPct, hzT, aws

                                # Try to fix high mapunit aggregate HZ by weighting with comppct

                                # Summarize component values to the mapunit
                                if mukey in dMu:
                                    #val1, val2, val3 = dMu[mukey]
                                    compPct, val2, val3 = dMu[mukey]
                                    #compPct = compPct + val1  # problem here. This appears to be tripling the comppct
                                    #compPct = adjCompPct + val1 #???
                                    hzT = hzT + val2
                                    aws = aws + val3

                                dMu[mukey] = (compPct, hzT, aws)
                                #dMu[mukey] = (sumCompPct, hzT, aws)  # get comppct from dPct

                else:
                    PrintMsg("\t" + Number_Format(iComp, 0, True) + " components for "  + str(td) + " - " + str(bd) + "cm", 1)

                # Write out map unit aggregated AWS
                # muFieldNames = ["MUKEY", "MUSUMCPCTA", "AWS" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "A"]
                for murec in muCursor:
                    mukey = murec[0]

                    if mukey in dMu:
                        compPct, hzT, aws = dMu[mukey]
                        murec[1] = compPct
                        #murec[2] = round(aws, 2)
                        murec[2] = round(aws, 2)
                        murec[3] = round(hzT, 2)
                        muCursor.updateRow(murec)
                        PrintMsg("\tAWS for " + str(td) + " to " + str(bd) + "cm " + mukey + ": " + str(murec), 1)


        if len(missingList) > 0:
            missingList = list(set(missingList))
            PrintMsg(" \n\tFollowing mapunits have no comppct_r: " + ", ".join(missingList), 1)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcSOC(db, coValu, valuTable, hzTable, dPct, dFrags, depthList, dRestrictions, maxD):
    # Create a component-level summary table
    # Calculate the standard mapunit-weighted available SOC for each mapunit and
    # add it to the map unit-level table
    # Does not calculate SOC below the following component restrictions:
    #     Lithic bedrock, Paralithic bedrock, Densic bedrock, Fragipan, Duripan, Sulfuric

    try:
        # Using the same component horizon table that has been
        numRows = int(arcpy.GetCount_management(hzTable).getOutput(0))

        # mukey, cokey, compPct,val, top, bot
        #qFieldNames = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", "om_r", "dbthirdbar_r"]
        qFieldNames = ["mukey","cokey","comppct_r","compname","localphase","chkey","om_r","dbthirdbar_r", "hzdept_r","hzdepb_r", "fragvol"]

        # Track map units that are missing data
        missingList = list()
        minusList = list()

        PrintMsg(" \nCalculating soil organic carbon...", 0)
        arcpy.SetProgressorLabel("Calculating soil organic carbon...")

        for rng in depthList:
            # Calculating and updating just one SOC column at a time
            #
            td = rng[0]
            bd = rng[1]

            # Open output table Mu...All in write mode
            # I lately added the "MUSUMCPCTS" to the output. Need to check output because
            # it will be writing this out for every range. Lots more overhead.
            #

            # Create dictionaries to handle the mapunit and component summaries
            dMu = dict()
            dComp = dict()
            #dSumPct = dict()  # store the sum of comppct_r for each mapunit to use in the calculations
            dSum = dict()     # store sum of comppct_r and total thickness for the component
            dHz = dict()      # Trying a new dictionary that will s
            mCnt = 0

            #arcpy.SetProgressorLabel("Calculating SOC for " + str(td) + "->" + str(bd) + "cm...")

            # Open edit session on geodatabase to allow multiple insert cursors
            with arcpy.da.Editor(db) as edit:

                # Open output mapunit-level table in update mode
                muFieldNames = ["MUKEY", "MUSUMCPCTS", "SOC" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "S"]
                #muFieldNames = ["MUKEY", "SOC" + str(td) + "_" + str(bd)]

                muCursor = arcpy.da.UpdateCursor(valuTable, muFieldNames)

                # Open output component-level table in write mode

                coFieldNames = ["COKEY", "SOC" + str(td) + "_" + str(bd), "TK" + str(td) + "_" + str(bd) + "S"]
                #coFieldNames = ["COKEY", "SOC" + str(td) + "_" + str(bd)]
                coCursor = arcpy.da.UpdateCursor(coValu, coFieldNames)

                # Process query table using a searchcursor, write out horizon data for each component
                # At this time, almost all components are being used! There is no filter.
                hzSQL = "hzdept_r is not null"  # prevent divide-by-zero errors by skipping components with no horizons
                sqlClause = (None, "order by mukey, comppct_r DESC, cokey, hzdept_r ASC")

                iCnt = int(arcpy.GetCount_management(hzTable).getOutput(0))
                inCur = arcpy.da.SearchCursor(hzTable, qFieldNames, where_clause=hzSQL, sql_clause=sqlClause)

                for rec in inCur:
                    # read each horizon-level input record from the query table ...

                    mukey, cokey, compPct, compName, localPhase, chkey, om, db3, top, bot, fragvol = rec

                    if fragvol is None:
                        fragvol = 0.0
                        #PrintMsg("hzTable: " + str(rec), 1)

                    if om is not None and db3 is not None:
                        # Calculate sum of horizon thickness and sum of component ratings for
                        # that portion of the horizon that is with in the td-bd range
                        top = max(top, td)
                        bot = min(bot, bd)
                        om = round(om, 3)

                        try:
                            rz, resKind = dRestrictions[cokey]

                        except:
                            rz = maxD
                            resKind = ""

                        # Now check for horizon restrictions within this range. Do not calculate SOC past
                        # root zone restrictive layers.
                        #
                        if top < rz < bot:
                            # restriction found in this horizon, use it to set a new depth
                            #PrintMsg("\t\t" + resKind + " restriction for " + mukey + ":" + cokey + " at " + str(rz) + "cm", 1)
                            cBot = rz

                        else:
                            cBot = min(rz, bot)

                        # Calculate initial usable horizon thickness
                        hzT = cBot - top

                        if hzT > 0 and top < cBot:
                    
                            #if mukey == "158070" and td == 0 and bd == 100.0:
                            #    test = [mukey, cokey, compPct, compName, localPhase, chkey, om, db3, top, bot, fragvol]
                            #    PrintMsg(str(test), 1)

                            # Calculate SOC using horizon thickness, OM, BD, FragVol, CompPct.
                            # changed the OM to carbon conversion from * 0.58 to / 1.724 after running FY2017 value table
                            if fragvol is None:
                                fragvol = 0.0
                                
                            soc =  ( (hzT * ( ( om / 1.724 ) * db3 )) / 100.0 ) * ((100.0 - fragvol) / 100.0) * ( compPct * 100 )

                            #if mukey == "158056" and td == 0 and bd == 100.0:
                                # Everything here matches the other script
                            #    test = [mukey, cokey, compPct, compName, localPhase, chkey, om, db3, top, bot, fragvol, round(soc, 2)]
                            #    PrintMsg(str(test), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horizon CHK
                                dComp[cokey] = (mukey, compPct, hzT, soc)


                                # Update sum of comppct for dMu. Not sure why I need to do this.
                                if not mukey in dMu:
                                    dMu[mukey] = (compPct, 0, 0)

                                else:
                                    val0 = dMu[mukey][0]
                                    dMu[mukey] = (val0 + compPct, 0, 0)
                                
                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, compName, dHzT, dSOC = dComp[cokey]
                                dSOC = dSOC + soc
                                dHzT = dHzT + hzT
                                dComp[cokey] = (mukey, compPct, dHzT, dSOC)


                    #arcpy.SetProgressorPosition()

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level
                #
                if iComp > 0:
                    PrintMsg("\t\t" + str(td) + " - " + str(bd) + "cm (" + Number_Format(iComp, 0, True) + " components)", 0)
                    #arcpy.SetProgressor("step", "Saving map unit and component SOC data...",  0, iComp, 1)

                    for corec in coCursor:
                        # Could this be where I am losing minor components????
                        #
                        # get component level data  CHK
                        cokey = str(corec[0])

                        if cokey in dComp:
                            # get SOC-related data from dComp by cokey
                            # dComp soc = ( (hzT * ( ( om * 0.58 ) * db3 )) / 100.0 ) * (100.0 - fragvol) / 100.0) * ( compPct * 100 )
                            mukey, compPct, hzT, soc = dComp[cokey]

                            # get sum of component percent for the mapunit (all components???)
                            # Value[0] is for all components,
                            # Value[1] is just for major-earthy components,
                            # Value[2] is all major components
                            # Value[3] is earthy components
                            try:
                                sumCompPct = float(dPct[mukey][0]) # Sum comppct for ALL components
                                #PrintMsg("Comppct for all components " + str(mukey) + ": " + str(sumCompPct), 1)

                            except:
                                # set the component percent to zero if it is not found in the
                                # dictionary. This is probably a 'Miscellaneous area' not included in the  CHK
                                # data or it has no horizon information.
                                sumCompPct = 0.0

                            # calculate component percentage adjustment
                            if sumCompPct > 0:
                                # adjust the rating value down by the component percentage and by the sum of the usable horizon thickness for this component

                                #adjCompPct = float(compPct) / sumCompPct  #

                                # write the new component-level SOC data to the Co_VALU table

                                corec[1] = soc                      # Test
                                hzT = hzT * compPct / 100.0      # Adjust component share of horizon thickness by comppct
                                corec[2] = hzT  # Just added this in
                                coCursor.updateRow(corec)

                                # Update component values in component dictionary   CHK
                                dComp[cokey] = mukey, compPct, hzT, soc

                                if mukey in dMu:
                                    compPct, val2, val3 = dMu[mukey]
                                    #compPct = compPct + val1
                                    hzT = hzT + val2
                                    soc = soc + val3

                                dMu[mukey] = (compPct, hzT, soc)
                                #PrintMsg("\t" + mukey + ": " + str((compPct, hzT, soc)), 1)

                else:
                    PrintMsg("\t" + Number_Format(iComp, 0, True) + " components for "  + str(td) + " - " + str(bd) + "cm", 1)

                # Write out map unit aggregated SOC
                #
                for murec in muCursor:
                    mukey = murec[0]

                    if mukey in dMu:
                        compPct, hzT, soc = dMu[mukey]
                        #murec[1] = compPct
                        #murec[2] = round(soc, 0)
                        #murec[3] = round(hzT, 0)  # this value appears to be low sometimes
                        murec =  [mukey, compPct, round(soc, 0), round(hzT, 0)]
                        PrintMsg("\tSOC for " + str(td) + " to " + str(bd) + "cm " + mukey + ": " + str(murec), 1)
                        muCursor.updateRow(murec)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetFragVol(db):
    # Get the horizon summary of rock fragment volume (percent)
    # load sum of comppct_r into a dictionary by chkey. This
    # value will be used to reduce amount of SOC for each horizon
    # If not all horizons are not present in the dictionary, failover to
    # zero for the fragvol value.

    try:

        fragFlds = ["chkey", "fragvol_r"]

        dFrags = dict()

        with arcpy.da.SearchCursor(os.path.join(db, "chfrags"), fragFlds) as fragCur:
            for rec in fragCur:
                chkey, fragvol = rec

                if chkey in dFrags:
                    # This horizon already has a volume for another fragsize
                    # Get the existing value and add to it.
                    # limit total fragvol to 100 or we will get negative SOC values where there
                    # are problems with fragvol data
                    val = dFrags[chkey]
                    dFrags[chkey] = min(val + max(fragvol, 0), 100)

                else:
                    # this is the first component for this map unit
                    dFrags[chkey] = min(max(fragvol, 0), 100)

        # in the rare case where fragvol sum is greater than 100%, return 100
        return dFrags

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def GetSumPct(hzTable):
    # Get map unit - sum of component percent for all components and also for major-earthy components
    # load sum of comppct_r into a dictionary.
    # Value[0] is for all components,
    # Value[1] is just for major-earthy components,
    # Value[2] is all major components
    # Value[3] is earthy components
    #
    # Do I need to add another option for earthy components?
    # WSS and SDV use all components with data for AWS.

    try:
        pctSQL = "comppct_r is not null"
        pctFlds = ["mukey", "cokey", "compkind", "majcompflag", "comppct_r"]
        cokeyList = list()

        dPct = dict()

        flds = arcpy.Describe(hzTable).fields
        fldNames = [fld.name for fld in flds]
        #PrintMsg(" \nField names for hzTable: " + ", ".join(fldNames), 1)

        cnt = 0

        with arcpy.da.SearchCursor(hzTable, pctFlds, pctSQL) as pctCur:
            for rec in pctCur:
                mukey, cokey, compkind, flag, comppct = rec
                m = 0     # major component percent
                me = 0    # major-earthy component percent
                e = 0     # earthy component percent

                if not cokey in cokeyList:
                    # These are horizon data, so we only want to use the data once per component
                    cokeyList.append(cokey)
                    cnt += 1

                    if flag == 'Yes':
                        # major component percent
                        m = comppct

                        if not compkind in  ["Miscellaneous area", ""]:
                            # major-earthy component percent
                            me = comppct
                            e = comppct

                        else:
                            me = 0

                    elif not compkind in  ["Miscellaneous area", ""]:
                        e = comppct

                    if mukey in dPct:
                        # This mapunit has a pair of values already
                        # Get the existing values from the dictionary
                        #pctAll, pctMjr = dPct[mukey] # all components, major-earthy
                        pctAll, pctME, pctMjr, pctE = dPct[mukey]
                        dPct[mukey] = (pctAll + comppct, pctME + me, pctMjr + m, pctE + e)

                    else:
                        # this is the first component for this map unit
                        dPct[mukey] = (comppct, me, m, e)

        #PrintMsg(" \ndPct: " + str(dPct), 1)                        
        #PrintMsg(" \nProcessed " + str(cnt) + " components in GetSumPct", 1)
        
        return dPct

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def CalcNCCPI(db, theMuTable, qTable, dPct):
    #
    try:

        PrintMsg(" \nAggregating NCCPI data to mapunit level...", 0)

        # Alternate component fields for all NCCPI values
        cFlds = ["MUKEY","COKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]
        mFlds = ["MUKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]

        # Create dictionary key as MUKEY:INTERPHRC
        # Need to look through the component rating class for ruledepth = 0
        # and sum up COMPPCT_R for each key value
        #
        dVals = dict()  # dictionary containing sum of comppct for each MUKEY:RATING combination

        # Get sum of component percent for each map unit. There are different options:
        #     1. Use all major components
        #     2. Use all components that have an NCCPI rating
        #     3. Use all major-earthy components. This one is not currently available.
        #     4. Use all components (that have a component percent)
        #

        # Query table fields
        qFields = ["MUKEY", "COKEY", "COMPPCT_R", "RULEDEPTH", "RULENAME", "INTERPHR"]

        sortFields = "ORDER BY COKEY ASC, COMPPCT_R DESC"
        querytblSQL = "COMPPCT_R IS NOT NULL"  # all major components
        sqlClause = (None, sortFields)

        iCnt = int(arcpy.GetCount_management(interpTable).getOutput(0))
        noVal = list()  # Get a list of components with no overall index rating

        PrintMsg(" \nReading interp data from " + interpTable, 0)

        arcpy.SetProgressor("step", "Reading interp data from " + interpTable, 0, iCnt, 1)

        with arcpy.da.SearchCursor(interpTable, qFields, where_clause=querytblSQL, sql_clause=sqlClause) as qCursor:

            for qRec in qCursor:
                # qFields = MUKEY, COKEY, COMPPCT_R, RULEDEPTH, RULENAME, INTERPHR
                mukey, cokey, comppct, ruleDepth, ruleName, fuzzyValue = qRec

                # Dictionary order:  All, CS, CT, SG
                if not mukey in dVals:
                    # Initialize mukey NCCPI values
                    dVals[mukey] = [None, None, None, None]
                    #dVals[mukey] = [None, None]

                if not fuzzyValue is None:

                    if ruleDepth == 0:
                        # This is NCCPI Overall Index
                        oldVal = dVals[mukey][0]

                        if oldVal is None:
                            dVals[mukey][0] = fuzzyValue * comppct

                        else:
                            dVals[mukey][0] = (oldVal + (fuzzyValue * comppct))

                    # The rest of these will be ruledepth=1
                    #
                    elif ruleName == "NCCPI - NCCPI Corn and Soybeans Submodel (II)":
                        oldVal = dVals[mukey][1]

                        if oldVal is None:
                            dVals[mukey][1] = fuzzyValue * comppct

                        else:
                            dVals[mukey][1] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Cotton Submodel (II)":
                        oldVal = dVals[mukey][2]

                        if oldVal is None:
                            dVals[mukey][2] =  fuzzyValue * comppct

                        else:
                            dVals[mukey][2] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Small Grains Submodel (II)":
                        oldVal = dVals[mukey][3]

                        if oldVal is None:
                            dVals[mukey][3] = fuzzyValue * comppct

                        else:
                            dVals[mukey][3] = (oldVal + (fuzzyValue * comppct))

                elif ruleName.startswith("NCCPI - National Commodity Crop Productivity Index"):
                    # This component does not have an NCCPI rating
                    #PrintMsg(" \n" + mukey + ":" + cokey + ", " + str(comppct) + "% has no NCCPI rating", 1)
                    noVal.append("'" + cokey + "'")

                #arcpy.SetProgressorPosition()
                #
                # End of query table iteration
                #
        #if len(noVal) > 0:
        #    PrintMsg(" \nThe following components had no NCCPI overall index: " + ", ".join(noVal), 1)

        iCnt = len(dVals)

        if iCnt > 0:
            #PrintMsg(" \n\tWriting NCCPI data (" + Number_Format(iCnt, 0, True) + " records) to " + os.path.basename(theMuTable) + "..." , 0)
            # Write map unit aggregate data to Mu_NCCPI2 table
            #
            # theMuTable is a global variable. Need to check this out in the gSSURGO_ValuTable script

            outputFields = ["mukey", "NCCPI2CS", "NCCPI2CO","NCCPI2SG", "NCCPI2ALL"]
            #outputFields = ["mukey", "nccpi2cs","nccpi2sg"]
            with arcpy.da.UpdateCursor(theMuTable, outputFields) as muCur:

                #arcpy.SetProgressor("step", "Saving map unit weighted NCCPI data to VALU table...", 0, iCnt, 0)
                for rec in muCur:
                    mukey = rec[0]

                    try:
                        # Get output values from dVals and dPct dictionaries
                        #val = dVals[mukey]
                        ovrall, cs, co, sg = dVals[mukey]
                        #ovrall, cs, sg = dVals[mukey]
                        #cs, sg = dVals[mukey]

                        sumPct = dPct[mukey][2]  # sum of major-earthy components
                        if not cs is None:
                            cs = round(cs / sumPct, 3)

                        if not co is None:
                            co = round(co / sumPct, 3)

                        if not sg is None:
                            sg = round(sg / sumPct, 3)

                        if not ovrall is None:
                            ovrall = round(ovrall / sumPct, 3)

                        newrec = mukey, cs, co, sg, ovrall
                        #newrec = mukey, cs, sg,

                        muCur.updateRow(newrec)

                    except KeyError:
                        pass

                    except:
                        # Miscellaneous map unit encountered with no comppct_r?
                        errorMsg()
                        #pass

            PrintMsg(" \nDeleting " + qTable, 1)
            arcpy.Delete_management(qTable)
            return True

        else:
            raise MyError, "No NCCPI data processed"

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcNCCPI2(inputDB, theMuTable, qTable, dPct):
    #
    #
    try:
        # FY2018 Big change. NCCPI version 3 will be available. Main rulename will change.
        # Soybeans will be split out from 'Corn and Soybeans', requiring a new column in the
        # Valu1 table.
        #
        # NCCPI version 3 Information
        # -------------------------------------
        # MRULENAME:	NCCPI - National Commodity Crop Productivity Index (Ver 3.0)  (ruledepth=0)
        #
        # RULENAME:	NCCPI - NCCPI Cotton Submodel (II)		(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Small Grains Submodel (II)	(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Corn Submodel (I)			(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Soybeans Submodel (I)		(ruledepth=1)

        # and write to Mu_NCCPI2 table


        #
        PrintMsg(" \nAggregating NCCPI2 data to mapunit level...", 0)

        # Alternate component fields for all NCCPI values
        cFlds = ["MUKEY","COKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]
        mFlds = ["MUKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]

        # Create dictionary key as MUKEY:INTERPHRC
        # Need to look through the component rating class for ruledepth = 0
        # and sum up COMPPCT_R for each key value
        #
        dVals = dict()  # dictionary containing sum of comppct for each MUKEY:RATING combination

        # Get sum of component percent for each map unit. There are different options:
        #     1. Use all major components
        #     2. Use all components that have an NCCPI rating
        #     3. Use all major-earthy components. This one is not currently available.
        #     4. Use all components (that have a component percent)
        #

        # Query table fields
        qFields = ["MUKEY", "COKEY", "COMPPCT_R", "RULEDEPTH", "RULENAME", "INTERPHR"]
        sortFields = "ORDER BY COKEY ASC, COMPPCT_R DESC"
        querytblSQL = "COMPPCT_R IS NOT NULL AND RULENAME = '" + "NCCPI - National Commodity Crop Productivity Index (Ver 2.0)" + "'" # all major components
        sqlClause = (None, sortFields)

        iCnt = int(arcpy.GetCount_management(qTable).getOutput(0))
        noVal = list()  # Get a list of components with no overall index rating

        #PrintMsg(" \n\tReading query table with " + Number_Format(iCnt, 0, True) + " records...", 0)

        arcpy.SetProgressor("step", "Reading query table...", 0,iCnt, 1)

        with arcpy.da.SearchCursor(qTable, qFields, where_clause=querytblSQL, sql_clause=sqlClause) as qCursor:

            for qRec in qCursor:
                # qFields = MUKEY, COKEY, COMPPCT_R, RULEDEPTH, RULENAME, INTERPHR
                mukey, cokey, comppct, ruleDepth, ruleName, fuzzyValue = qRec

                # Dictionary order:  All, CS, CT, SG
                if not mukey in dVals:
                    # Initialize mukey NCCPI values
                    dVals[mukey] = [None, None, None, None]

                if not fuzzyValue is None:

                    if ruleDepth == 0:
                        # This is NCCPI Overall Index
                        oldVal = dVals[mukey][0]

                        if oldVal is None:
                            dVals[mukey][0] = fuzzyValue * comppct

                        else:
                            dVals[mukey][0] = (oldVal + (fuzzyValue * comppct))

                    # The rest of these will be ruledepth=1
                    #
                    elif ruleName == "NCCPI - NCCPI Corn and Soybeans Submodel (II)":
                        oldVal = dVals[mukey][1]

                        if oldVal is None:
                            dVals[mukey][1] = fuzzyValue * comppct

                        else:
                            dVals[mukey][1] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Cotton Submodel (II)":
                        oldVal = dVals[mukey][2]

                        if oldVal is None:
                            dVals[mukey][2] =  fuzzyValue * comppct

                        else:
                            dVals[mukey][2] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Small Grains Submodel (II)":
                        oldVal = dVals[mukey][3]

                        if oldVal is None:
                            dVals[mukey][3] = fuzzyValue * comppct

                        else:
                            dVals[mukey][3] = (oldVal + (fuzzyValue * comppct))

                elif ruleName == "NCCPI - National Commodity Crop Productivity Index (Ver 2.0)":
                    # This component does not have an NCCPI rating
                    #PrintMsg(" \n" + mukey + ":" + cokey + ", " + str(comppct) + "% has no NCCPI rating", 1)
                    noVal.append("'" + cokey + "'")

                arcpy.SetProgressorPosition()
                #
                # End of query table iteration
                #



        #if len(noVal) > 0:
        #    PrintMsg(" \nThe following components had no NCCPI overall index: " + ", ".join(noVal), 1)

        iCnt = len(dVals)

        if iCnt > 0:

            #PrintMsg(" \n\tSaving map unit weighted NCCPI data (" + Number_Format(iCnt, 0, True) + " records) to " + os.path.basename(theMuTable) + "..." , 0)
            # Write map unit aggregate data to Mu_NCCPI2 table
            #
            # theMuTable is a global variable. Need to check this out in the gSSURGO_ValuTable script

            with arcpy.da.UpdateCursor(theMuTable, ["mukey", "NCCPI2CS", "NCCPI2CO","NCCPI2SG", "NCCPI2ALL"]) as muCur:

                arcpy.SetProgressor("step", "Saving map unit weighted NCCPI data to VALU table...", 0, iCnt, 0)
                for rec in muCur:
                    mukey = rec[0]

                    try:
                        # Get output values from dVals and dPct dictionaries
                        #val = dVals[mukey]
                        ovrall, cs, co, sg = dVals[mukey]
                        sumPct = dPct[mukey][2]  # sum of major-earthy components
                        if not cs is None:
                            cs = round(cs / sumPct, 3)

                        if not co is None:
                            co = round(co / sumPct, 3)

                        if not sg is None:
                            sg = round(sg / sumPct, 3)

                        if not ovrall is None:
                            ovrall = round(ovrall / sumPct, 3)

                        newrec = mukey, cs, co, sg, ovrall
                        muCur.updateRow(newrec)

                    except:
                        # Miscellaneous map unit encountered with no comppct_r?
                        pass

                    arcpy.SetProgressorPosition()

            arcpy.Delete_management(qTable)
            return True

        else:
            raise MyError, "No NCCPI data processed"

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcNCCPI3(inputDB, theMuTable, qTable, dPct):
    #
    #
    try:
        # FY2018 Big change. NCCPI version 3 will be available. Main rulename will change.
        # Soybeans will be split out from 'Corn and Soybeans', requiring a new column in the
        # Valu1 table.
        #
        # NCCPI version 3 Information
        # -------------------------------------
        # MRULENAME:	NCCPI - National Commodity Crop Productivity Index (Ver 3.0)  (ruledepth=0)
        #
        # RULENAME:	NCCPI - NCCPI Cotton Submodel (II)		(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Small Grains Submodel (II)	(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Corn Submodel (I)			(ruledepth=1)
        # RULENAME:	NCCPI - NCCPI Soybeans Submodel (I)		(ruledepth=1)

        # and write to Mu_NCCPI2 table

        #
        PrintMsg(" \nAggregating NCCPI3 data to the map unit level...", 0)
        arcpy.SetProgressorLabel("Aggregating NCCPI3 data to the map unit level")

        # Alternate component fields for all NCCPI values
        cFlds = ["MUKEY","COKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]
        mFlds = ["MUKEY","COMPPCT_R","COMPNAME","LOCALPHASE", "DUMMY"]

        # Create dictionary key as MUKEY:INTERPHRC
        # Need to look through the component rating class for ruledepth = 0
        # and sum up COMPPCT_R for each key value
        #
        dVals = dict()  # dictionary containing sum of comppct for each MUKEY:RATING combination

        # Get sum of component percent for each map unit. There are different options:
        #     1. Use all major components
        #     2. Use all components that have an NCCPI rating
        #     3. Use all major-earthy components. This one is not currently available.
        #     4. Use all components (that have a component percent)
        #

        # Query table fields
        qFields = ["MUKEY", "COKEY", "COMPPCT_R", "RULEDEPTH", "RULENAME", "INTERPHR"]
        sortFields = "ORDER BY COKEY ASC, COMPPCT_R DESC"
        querytblSQL = "COMPPCT_R IS NOT NULL" # all major components
        sqlClause = (None, sortFields)
        # End of Original...


        iCnt = int(arcpy.GetCount_management(qTable).getOutput(0))
        noVal = list()  # Get a list of components with no overall index rating

        #PrintMsg(" \n\tReading query table with " + Number_Format(iCnt, 0, True) + " records...", 0)

        #arcpy.SetProgressor("step", "Reading query table (" + qTable + "...", 0,iCnt, 1)

        with arcpy.da.SearchCursor(qTable, qFields, where_clause=querytblSQL, sql_clause=sqlClause) as qCursor:

            for qRec in qCursor:
                # qFields = MUKEY, COKEY, COMPPCT_R, RULEDEPTH, RULENAME, INTERPHR
                #PrintMsg(str(qRec), 1)
                mukey, cokey, comppct, ruleDepth, ruleName, fuzzyValue = qRec

                # Dictionary order:  All, CT, CR, SB, SG
                if not mukey in dVals:
                    # Initialize mukey NCCPI values
                    dVals[mukey] = [None, None, None, None, None]

                if not fuzzyValue is None:

                    if ruleDepth == 0:
                        # This is NCCPI Overall Index
                        oldVal = dVals[mukey][0]

                        if oldVal is None:
                            dVals[mukey][0] = fuzzyValue * comppct

                        else:
                            dVals[mukey][0] = (oldVal + (fuzzyValue * comppct))

                    # The rest of these will be ruledepth=1
                    #
                    elif ruleName == "NCCPI - NCCPI Cotton Submodel (II)":
                        oldVal = dVals[mukey][1]

                        if oldVal is None:
                            dVals[mukey][1] =  fuzzyValue * comppct

                        else:
                            dVals[mukey][1] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Corn Submodel (I)":
                        oldVal = dVals[mukey][2]

                        if oldVal is None:
                            dVals[mukey][2] = fuzzyValue * comppct

                        else:
                            dVals[mukey][2] = (oldVal + (fuzzyValue * comppct))

                    elif ruleName == "NCCPI - NCCPI Soybeans Submodel (I)":
                        oldVal = dVals[mukey][3]

                        if oldVal is None:
                            dVals[mukey][3] = fuzzyValue * comppct

                        else:
                            dVals[mukey][3] = (oldVal + (fuzzyValue * comppct))


                    elif ruleName == "NCCPI - NCCPI Small Grains Submodel (II)":
                        oldVal = dVals[mukey][4]

                        if oldVal is None:
                            dVals[mukey][4] = fuzzyValue * comppct

                        else:
                            dVals[mukey][4] = (oldVal + (fuzzyValue * comppct))

                #elif ruleName.startswith("NCCPI - National Commodity Crop Productivity Index"):
                    # This component does not have an NCCPI rating
                    #PrintMsg(" \n" + mukey + ":" + cokey + ", " + str(comppct) + "% has no NCCPI rating", 1)
                #    noVal.append("'" + cokey + "'")

                arcpy.SetProgressorPosition()
                #
                # End of query table iteration
                #



        #if len(noVal) > 0:
        #    PrintMsg(" \nThe following components had no NCCPI overall index: " + ", ".join(noVal), 1)

        iCnt = len(dVals)

        if iCnt > 0:

            #PrintMsg(" \n\tSaving map unit weighted NCCPI data (" + Number_Format(iCnt, 0, True) + " records) to " + os.path.basename(theMuTable) + "..." , 0)
            # Write map unit aggregate data to Mu_NCCPI2 table
            #
            # theMuTable is a global variable. Need to check this out in the gSSURGO_ValuTable script
            #                                                 corn&soybeans, cotton, smallgrains, overall

            with arcpy.da.UpdateCursor(theMuTable, ["mukey", "NCCPI3CORN", "NCCPI3SOY", "NCCPI3COT","NCCPI3SG", "NCCPI3ALL"]) as muCur:

                arcpy.SetProgressor("step", "Saving map unit weighted NCCPI data to VALU table...", 0, iCnt, 0)
                for rec in muCur:
                    mukey = rec[0]

                    try:
                        # Get output values from dVals and dPct dictionaries
                        #val = dVals[mukey]
                        ovrall, cot, corn, soy, sg = dVals[mukey]
                        sumPct = dPct[mukey][2]  # sum of major-earthy components

                        if not ovrall is None:
                            ovrall = round(ovrall / sumPct, 3)

                        if not cot is None:
                            cot = round(cot / sumPct, 3)

                        if not corn is None:
                            corn = round(corn / sumPct, 3)

                        if not soy is None:
                            soy = round(soy / sumPct, 3)

                        if not sg is None:
                            sg = round(sg / sumPct, 3)

                        # "mukey", "NCCPI3CORN", "NCCPI3SOY", "NCCPI3COT","NCCPI3SG", "NCCPI3ALL"
                        newrec = mukey, corn, soy, cot, sg, ovrall
                        muCur.updateRow(newrec)

                    except:
                        # Miscellaneous map unit encountered with no comppct_r?
                        pass

                    arcpy.SetProgressorPosition()

            #arcpy.Delete_management(qTable)
            return True

        else:
            raise MyError, "No NCCPI data processed"

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CalcPWSL(db, theMuTable, dPct):
    # Get potential wet soil landscape rating for each map unit
    # Assuming that all components (with comppct_r) will be processed
    #
    # Sharon: I treat all map unit components the same, so if I find 1% water I think
    # it should show up as 1% PWSL.  If the percentage of water is >= 80% then I class
    # it into the water body category or 999.
    try:
        # Using the same component horizon table as always
        #queryTbl = os.path.join(outputDB, "QueryTable_Hz")
        numRows = int(arcpy.GetCount_management(hzTable).getOutput(0))
        PrintMsg(" \nCalculating Potential Wet Soil Landscapes using " + os.path.basename(hzTable) + "...", 0)
        arcpy.SetProgressorLabel("Calculating Potential Wet Soil Landscapes...")
        qFieldNames = ["mukey", "muname", "cokey", "comppct_r",  "compname", "localphase", "otherph", "majcompflag", "compkind", "hydricrating", "drainagecl"]
        pwSQL = "COMPPCT_R > 0"
        compList = list()
        dMu = dict()

        drainList = ["Poorly drained", "Very poorly drained"]
        phaseList = ["drained", "undrained", "channeled", "protected", "ponded", "flooded"]

        # Defining water components SDP
        # 1. compkind = 'Miscellaneous area' or is NULL and (
        # 2. compname = 'Water' or
        # 3. compname like '% water' or
        # 4. compname like '% Ocean' or
        # 5. compname like '% swamp'
        # nameList = []

        iCnt = int(arcpy.GetCount_management(hzTable).getOutput(0))
        lastCokey = 'xxx'
        #arcpy.SetProgressor("step", "Reading query table table for wetland information...",  0, iCnt, 1)

        with arcpy.da.SearchCursor(hzTable, qFieldNames, where_clause=pwSQL) as pwCur:
            for rec in pwCur:
                mukey, muname, cokey, comppct_r,  compname, localphase, otherph, majcompflag, compkind, hydricrating, drainagecl = rec
                mukey = str(mukey)
                cokey = str(cokey)

                if cokey != lastCokey:
                    # only process first horizon record for each component

                    compList.append(cokey)
                    # Only check the first horizon record, really only need component level
                    # Not very efficient, should problably create a new query table
                    #
                    # Need to split up these tests so that None types can be handled

                    # Sharon says that if the hydricrating for a component is 'No', don't
                    # look at it any further. If it is unranked, go ahead and look at
                    # other properties.
                    #
                    pw = False

                    if ( muname == "Water" or str(compname) == "Water" or (str(compname).lower().find(" water") >= 0) or (str(compname).lower().find(" ocean") >= 0)  or (str(compname).find(" swamp") >= 0) or str(compname) == "Swamp" ) :

                        # Check for water before looking at Hydric rating
                        # Probably won't catch everything. Waiting for Sharon's criteria.

                        if comppct_r >= 80:
                            # Flag this mapunit with a '999'
                            # Not necessarily catching map unit with more than one Water component that
                            # might sum to >= 80. Don't think there are any right now.
                            #PrintMsg("\tFlagging " + muname + " as Water", 1)
                            #PrintMsg("\t" + mukey + "; " + muname + "; " + compname + "; " + str(compkind) + "; " + str(comppct_r), 1)
                            pw = False
                            dMu[mukey] = 999

                        else:
                            pw = True

                            try:
                                sumPct = dMu[mukey]

                                if sumPct != 999:
                                    dMu[mukey] = sumPct + comppct_r

                            except:
                                dMu[mukey] = comppct_r

                    elif hydricrating == 'No':
                        # Added this bit so that other properties cannot override hydricrating = 'No'
                        pw = False

                    elif hydricrating == 'Yes':
                        # This is always a Hydric component
                        # Get component percent and add to map unit total PWSL
                        pw = True
                        #if mukey == tmukey:
                        #    PrintMsg("\tHydric percent = " + str(comppct_r), 1)

                        try:
                            sumPct = dMu[mukey]

                            if sumPct != 999:
                                dMu[mukey] = sumPct + comppct_r

                        except:
                            dMu[mukey] = comppct_r

                    elif hydricrating == 'Unranked':
                        # Not sure how Sharon is handling NULL hydric
                        #
                        # Unranked hydric from here on down, looking at other properties such as:
                        #   Local phase
                        #   Other phase
                        #   Drainage class
                        #   Map unit name strings
                        #       drainList = ["Poorly drained", "Very poorly drained"]
                        #       phaseList = ["drained", "undrained", "channeled", "protected", "ponded", "flooded"]

                        if [d for d in phaseList if str(localphase).lower().find(d) >= 0]:
                            pw = True

                            try:
                                sumPct = dMu[mukey]
                                dMu[mukey] = sumPct + comppct_r

                            except:
                                dMu[mukey] = comppct_r

                        # otherphase
                        elif [d for d in phaseList if str(otherph).lower().find(d) >= 0]:
                            pw = True

                            try:
                                sumPct = dMu[mukey]
                                dMu[mukey] = sumPct + comppct_r

                            except:
                                dMu[mukey] = comppct_r

                        # look for specific strings in the map unit name
                        elif [d for d in phaseList if muname.find(d) >= 0]:
                            pw = True
                            #if mukey == tmukey:
                            #    PrintMsg("\tMuname = " + muname, 1)

                            try:
                                sumPct = dMu[mukey]
                                dMu[mukey] = sumPct + comppct_r

                            except:
                                dMu[mukey] = comppct_r

                        elif str(drainagecl) in drainList:
                            pw = True

                            try:
                                sumPct = dMu[mukey]
                                dMu[mukey] = sumPct + comppct_r

                            except:
                                dMu[mukey] = comppct_r

                lastCokey = cokey # use this to skip the rest of the horizons for this component
                #arcpy.SetProgressorPosition()

        if len(dMu) > 0:
            #arcpy.SetProgressor("step", "Populating " + os.path.basename(theMuTable) + "...",  0, len(dMu), 1)

            # Populate the PWSL1POMU column in the map unit level table
            muFlds = ["mukey", "pwsl1pomu"]
            with arcpy.da.UpdateCursor(theMuTable, muFlds) as muCur:
                for rec in muCur:
                    mukey = rec[0]
                    try:
                        rec[1] = dMu[mukey]
                        muCur.updateRow(rec)

                    except:
                        pass

                    #arcpy.SetProgressorPosition()

        #arcpy.ResetProgressor()
        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def StateNames():
    # Create dictionary object containing list of state abbreviations and their names that
    # will be used to name the file geodatabase.
    # For some areas such as Puerto Rico, U.S. Virgin Islands, Pacific Islands Area the
    # abbrevation is

    # NEED TO UPDATE THIS FUNCTION TO USE THE LAOVERLAP TABLE AREANAME. AREASYMBOL IS STATE ABBREV

    try:
        stDict = dict()
        stDict["AL"] = "Alabama"
        stDict["AK"] = "Alaska"
        stDict["AS"] = "American Samoa"
        stDict["AZ"] = "Arizona"
        stDict["AR"] = "Arkansas"
        stDict["CA"] = "California"
        stDict["CO"] = "Colorado"
        stDict["CT"] = "Connecticut"
        stDict["DC"] = "District of Columbia"
        stDict["DE"] = "Delaware"
        stDict["FL"] = "Florida"
        stDict["GA"] = "Georgia"
        stDict["HI"] = "Hawaii"
        stDict["ID"] = "Idaho"
        stDict["IL"] = "Illinois"
        stDict["IN"] = "Indiana"
        stDict["IA"] = "Iowa"
        stDict["KS"] = "Kansas"
        stDict["KY"] = "Kentucky"
        stDict["LA"] = "Louisiana"
        stDict["ME"] = "Maine"
        stDict["MD"] = "Maryland"
        stDict["MA"] = "Massachusetts"
        stDict["MI"] = "Michigan"
        stDict["MN"] = "Minnesota"
        stDict["MS"] = "Mississippi"
        stDict["MO"] = "Missouri"
        stDict["MT"] = "Montana"
        stDict["NE"] = "Nebraska"
        stDict["NV"] = "Nevada"
        stDict["NH"] = "New Hampshire"
        stDict["NJ"] = "New Jersey"
        stDict["NM"] = "New Mexico"
        stDict["NY"] = "New York"
        stDict["NC"] = "North Carolina"
        stDict["ND"] = "North Dakota"
        stDict["OH"] = "Ohio"
        stDict["OK"] = "Oklahoma"
        stDict["OR"] = "Oregon"
        stDict["PA"] = "Pennsylvania"
        stDict["PRUSVI"] = "Puerto Rico and U.S. Virgin Islands"
        stDict["RI"] = "Rhode Island"
        stDict["Sc"] = "South Carolina"
        stDict["SD"] ="South Dakota"
        stDict["TN"] = "Tennessee"
        stDict["TX"] = "Texas"
        stDict["UT"] = "Utah"
        stDict["VT"] = "Vermont"
        stDict["VA"] = "Virginia"
        stDict["WA"] = "Washington"
        stDict["WV"] = "West Virginia"
        stDict["WI"] = "Wisconsin"
        stDict["WY"] = "Wyoming"
        return stDict

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return stDict


## ===================================================================================
def GetLastDate(surveyList):
    # Get the most recent date 'YYYYMMDD' from SACATALOG.SAVEREST and use it to populate metadata
    #
    try:
        dateList = list()

        for survey in surveyList:
            surveyInfo = survey.split(",")
            areasymbol = surveyInfo[0]
            saverest = surveyInfo[1]
            dateList.append(saverest)

        lastDate = sorted(dateList)[-1]  # last date in the list
            

        return lastDate

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def UpdateMetadata(outputWS, target, surveyInfo):
    # Update metadata for target object (VALU1 table)
    #
    try:

        # Clear process steps from the VALU1 table. Mostly AddField statements.
        #
        # Different path for ArcGIS 10.2.2??
        #
        #
        if not arcpy.Exists(target):
            target = os.path.join(outputWS, target)

        env.workspace = outputWS

        # Remove geoprocessing history
        remove_gp_history_xslt = os.path.join(os.path.dirname(sys.argv[0]), "remove geoprocessing history.xslt")
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        # Using the stylesheet, write 'clean' metadata to out_xml file and then import back in
        arcpy.XSLTransform_conversion(target, remove_gp_history_xslt, out_xml, "")
        arcpy.MetadataImporter_conversion(out_xml, os.path.join(outputWS, target))

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Define input and output XML files
        #mdExport = os.path.join(env.scratchFolder, "xxExport.xml")  # initial metadata exported from current data data
        xmlPath = os.path.dirname(sys.argv[0])
        # Use this translator to export the following metadata templates (mdExport)
        #mdExport = os.path.join(xmlPath, "gSSURGO_ValuTable.xml")   # Use this version with data having NCCPI2 data
        mdExport = os.path.join(xmlPath, "gSSURGO_ValuTable2.xml")  # template metadata stored in ArcTool folder. Use this version with NCCPI3 data.
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info

        # Cleanup XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        # Start editing metadata using search and replace
        #
        stDict = StateNames()
        st = os.path.basename(outputWS)[8:-4]

        if st in stDict:
            # Get state name from the geodatabase name
            mdState = stDict[st]

        else:
            mdState = ""

        # Set date strings for metadata, based upon today's date
        #
        d = datetime.now()
        #today = d.strftime('%Y%m%d')

        # Alternative to using today's date. Use the last SAVEREST date
        today = GetLastDate(surveyInfo)

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        # Convert XML from template metadata to tree format
        tree = ET.parse(mdExport)
        root = tree.getroot()

        # new citeInfo has title.text, edition.text, serinfo/issue.text
        citeInfo = root.findall('idinfo/citation/citeinfo/')

        if not citeInfo is None:
            # Process citation elements
            # title
            #
            # PrintMsg("citeInfo with " + str(len(citeInfo)) + " elements : " + str(citeInfo), 1)
            for child in citeInfo:
                PrintMsg("\t\t" + str(child.tag), 0)
                if child.tag == "title":
                    child.text = os.path.basename(target).title()

                    if mdState != "":
                        child.text = child.text + " - " + mdState

                elif child.tag == "edition":
                    if child.text.find('xxFYxx') >= 0:
                        child.text = child.text.replace('xxFYxx', fy)
                    else:
                        PrintMsg(" \n\tEdition: " + child.text, 1)

                    if child.text.find('xxTODAYxx') >= 0:
                        child.text = child.text.replace('xxTODAYxx', today)

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            subchild.text = fy

                        if child.text.find('xxTODAYxx') >= 0:
                            child.text = child.text.replace('xxTODAYxx', today)


        # Update place keywords
        #PrintMsg("\tplace keywords", 0)
        ePlace = root.find('idinfo/keywords/theme')

        if ePlace is not None:
            for child in ePlace.iter('themekey'):
                if child.text == "xxSTATExx":
                    #PrintMsg("\tReplaced xxSTATExx with " + mdState)
                    child.text = mdState

                elif child.text == "xxSURVEYSxx":
                    #child.text = "The Survey List"
                    child.text = surveyInfo

        else:
            PrintMsg("\tsearchKeys not found", 1)

        idDescript = root.find('idinfo/descript')

        if not idDescript is None:
            for child in idDescript.iter('supplinf'):
                #id = child.text
                #PrintMsg("\tip: " + ip, 1)
                if child.text.find("xxTODAYxx") >= 0:
                    #PrintMsg("\t\tip", 1)
                    child.text = child.text.replace("xxTODAYxx", today)

                if child.text.find("xxFYxx") >= 0:
                    #PrintMsg("\t\tip", 1)
                    child.text = child.text.replace("xxFYxx", fy)

        if not idDescript is None:
            for child in idDescript.iter('purpose'):
                #ip = child.text
                #PrintMsg("\tip: " + ip, 1)
                if child.text.find("xxFYxx") >= 0:
                    #PrintMsg("\t\tip", 1)
                    child.text = child.text.replace("xxFYxx", fy)

                if child.text.find("xxTODAYxx") >= 0:
                    #PrintMsg("\t\tip", 1)
                    child.text = child.text.replace("xxTODAYxx", today)

        idAbstract = root.find('idinfo/descript/abstract')
        if not idAbstract is None:
            iab = idAbstract.text

            if iab.find("xxFYxx") >= 0:
                #PrintMsg("\t\tip", 1)
                idAbstract.text = iab.replace("xxFYxx", fy)
                #PrintMsg("\tAbstract", 0)

        # Use contraints
        #idConstr = root.find('idinfo/useconst')
        #if not idConstr is None:
        #    iac = idConstr.text
            #PrintMsg("\tip: " + ip, 1)
        #    if iac.find("xxFYxx") >= 0:
        #        idConstr.text = iac.replace("xxFYxx", fy)
        #        PrintMsg("\t\tUse Constraint: " + idConstr.text, 0)

        # Update credits
        eIdInfo = root.find('idinfo')

        if not eIdInfo is None:

            for child in eIdInfo.iter('datacred'):
                sCreds = child.text

                if sCreds.find("xxTODAYxx") >= 0:
                    #PrintMsg("\tdata credits1", 1)
                    sCreds = sCreds.replace("xxTODAYxx", today)

                if sCreds.find("xxFYxx") >= 0:
                    #PrintMsg("\tdata credits2", 1)
                    sCreds = sCreds.replace("xxFYxx", fy)

                child.text = sCreds
                #PrintMsg("\tCredits: " + sCreds, 1)

        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        arcpy.MetadataImporter_conversion(mdExport, target)

        if not arcpy.Exists(mdImport):
            raise MyError, "Missing metadata file (" + mdImport + ")"
        
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")

        # delete the temporary xml metadata files
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        #if os.path.isfile(mdExport):
        #    os.remove(mdExport)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False
    
    except:
        errorMsg()
        False

## ===================================================================================
def CreateValuTable(db, valuTable, coValu, muTable, coTable, hzTable, crTable, txTable, interpTable, mukeyList):
    #        
    # Run all processes from here

    try:
        PrintMsg(" \nCreating " + muTable + " table...", 0)
        arcpy.OverwriteOutput = True
        #dValue = dict() # return dictionary by mukey

        # Set location for temporary tables

        # Name of component level output table (global variable)
        coValu = os.path.join(db, "Co_VALU")

        # Save record of any issues to a text file
        logFile = os.path.basename(db)[:-4] + "_Problems.txt"
        logFile = os.path.join(os.path.dirname(db), logFile)

        # Let's get the mainrulename from the SDVAttribute table
        # This may break again in the future. October 2017
        global mainRuleName


        # Override the previous value
        mainRuleName = "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)"
        
        # Get the mapunit - sum of component percent for calculations
        arcpy.SetProgressor("Summarizing component percent")
        dPct = GetSumPct(hzTable)

        if len(dPct) == 0:
            raise MyError, ""

        # Create permanent output tables for the map unit and component levels
        depthList = [(0,5), (5, 20), (20, 50), (50, 100), (100, 150), (150, 999), (0, 20), (0, 30), (0, 100), (0, 150), (0, 999)]

        if CreateOutputTableMu(valuTable, depthList, dPct, mukeyList) == False:
            raise MyError, "Problem creating " + valuTable + " table"

        if CreateOutputTableCo(coValu, depthList) == False:
            raise MyError, ""

        # Store component restrictions for root growth in a dictionary
        resListAWS = "('Lithic bedrock','Paralithic bedrock','Densic bedrock', 'Densic material', 'Fragipan', 'Duripan', 'Sulfuric')"
        dRestrictions = GetCoRestrictions(crTable, 150.0, resListAWS)

        # Find the top restriction for each component, both from the corestrictions table and the horizon properties
        #dComp2 = CalcRZDepth(db, coValu, 150.0, dPct, dRestrictions)
        dComp2 = CalcRZDepth(db, coTable, hzTable, 150.0, dPct, dRestrictions)

        # Calculate root zone available water capacity using a floor of 150cm or a root restriction depth
        #            inputDB, outputDB, td, bd, coValu, hzTable, valuTable, dRestrictions, maxD, dPct
        #            inputDB, outputDB, td, bd, coValu, theMuTable, dRestrictions, maxD, dPct
        #if CalcRZAWS(db, db,          0.0, 150.0, coValu, hzTable, valuTable, dComp2, 150.0, dPct) == False:
        if CalcRZAWS(db, db, 0.0, 150.0, coValu, muTable, hzTable, valuTable, dRestrictions, 150.0, dPct) == False:
            raise MyError, ""

        # Calculate standard available water supply
        if CalcAWS(db, coValu, valuTable, hzTable, dPct, depthList) == False:
            raise MyError, ""

        # Run SOC calculations
        maxD = 999.0
        # Get bedrock restrictions for SOC  and write them to the output tables
        resListSOC = "('Lithic bedrock', 'Paralithic bedrock', 'Densic bedrock')"
        dSOCRestrictions = GetCoRestrictions(crTable, maxD, resListSOC)

        # Store all component-horizon fragment volumes (percent) in a dictionary (by chkey)
        # and use in the root zone SOC calculations
        dFrags = dict() # bandaid, create empty dictionary for fragvol. That data is now in hzTable

        # Calculate soil organic carbon for all the different depth ranges
        depthList = [(0,5), (5, 20), (20, 50), (50, 100), (100, 150), (150, 999), (0, 20), (0, 30), (0, 100), (0, 150), (0, 999)]
        #          db, coValu, valuTable, hzTable, dPct, dFrags, depthList, dRestrictions, maxD
        if CalcSOC(db, coValu, valuTable, hzTable, dPct, dFrags, depthList, dSOCRestrictions, maxD) == False:
            raise MyError, ""

        # Calculate NCCPI
        if mainRuleName == "NCCPI - National Commodity Crop Productivity Index (Ver 3.0)":
            if CalcNCCPI3(db, valuTable, interpTable, dPct) == False:
                raise MyError, ""

        elif mainRuleName == "NCCPI - National Commodity Crop Productivity Index (Ver 2.0)":
            if CalcNCCPI2(db, valuTable, interpTable, dPct) == False:
                raise MyError, ""

        else:
            PrintMsg(" \nFailed to process NCCPI data", 1)

        # Calculate PWSL
        if CalcPWSL(db, valuTable, dPct) == False:
            raise MyError, ""

        #PrintMsg(" \n\tAll calculations complete", 0)

        bMetaData = True

        if bMetaData:
            # Create metadata for the VALU table
            # Query the output SACATALOG table to get list of surveys that were exported to the gSSURGO
            #
            # Update metadata for the geodatabase and all featureclasses
            PrintMsg(" \nSkipping " + os.path.basename(valuTable) + " metadata...", 0)
            arcpy.SetProgressorLabel("Skipping " + valuTable + " table metadata")

            
            surveyList = ["Survey1", "Survey2"]
           
            #bMetadata = UpdateMetadata(db, valuTable, surveyList)

            #if arcpy.Exists(coValu):
            #    arcpy.Delete_management(coValu)

            #if bMetadata:
            #    PrintMsg("\tMetadata complete", 0)

            PrintMsg(" \n" + os.path.basename(valuTable) + " table complete for " + os.path.basename(db) + " \n ", 0)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def RunQueries(db, valuTable, sdaURL, mukeyQuery, muTable, coTable, hzTable, crTable, txTable, interpTable ):
    # Get associated soil attribute data by creating queries and calling a
    # series of functions to run those queries against Soil Data Access.
    #
    # Several tables will be created
    #
    # Since this script is designed to be able to create a National Valu1 table, it
    # will have to iterate through each areasymbol and append the results to each table
    #
    try:
        #PrintMsg(" \nFrom SDA_Valu2Table.RunQueries, using AttributeRequest function to populate some tables: hzTable, crTable, interpTable", 1)


            
        sQuery = """SELECT L.areasymbol, M.mukey, M.musym, M.muname, MAG.wtdepaprjunmin, MAG.flodfreqdcd, MAG.pondfreqprs, MAG.drclassdcd, MAG.drclasswettest, MAG.hydgrpdcd, MAG.hydclprs
FROM mapunit M
LEFT OUTER JOIN muaggatt MAG ON M.mukey = MAG.mukey
INNER JOIN legend L ON L.lkey = M.lkey
WHERE M.mukey IN """ + mukeyQuery + """
ORDER BY mukey;"""

        mukeyList = AttributeRequest(sdaURL, muTable, sQuery)

        # Here I'm try to remove the chtexture data (texcl, lieutex) and place it into a separate query.
        #I was having problems with duplicate horizon data with the previous version
        sQuery = """SELECT M.mukey, M.musym AS musymbol, M.muname, C.cokey,  C.compname,
C.comppct_r, C.majcompflag, C.compkind, C.localphase, C.otherph, C.taxorder,
C.taxsubgrp, C.hydricrating, C.drainagecl, H.hzname, H.desgnmaster, H.chkey,
H.hzdept_r, H.hzdepb_r, H.awc_r, H.ksat_r, H.sandtotal_r, H.silttotal_r, H.claytotal_r,
H.sandfine_r AS vfsand, H.om_r, H.dbthirdbar_r, H.ph1to1h2o_r, H.ec_r,
(SELECT SUM(CF.fragvol_r) FROM chfrags CF WHERE H.chkey = CF.chkey GROUP BY CF.chkey) AS fragvol
FROM mapunit M
INNER JOIN legend L ON L.lkey = M.lkey
LEFT OUTER JOIN component C ON M.mukey = C.mukey AND C.comppct_r IS NOT NULL
LEFT OUTER JOIN chorizon H ON C.cokey = H.cokey AND H.hzdept_r IS NOT NULL AND H.hzdepb_r IS NOT NULL
WHERE M.mukey IN """ + mukeyQuery + """
ORDER BY M.mukey, C.comppct_r DESC, C.cokey, H.hzdept_r ASC;"""

        #junk =  AttributeRequest(sdaURL, hzTable, sQuery)
        # 
        sQuery = """SELECT M.mukey, M.musym AS musymbol, M.muname, C.cokey,  C.compname, C.comppct_r, C.majcompflag,
C.compkind, C.localphase, C.otherph, C.taxorder, C.taxsubgrp, C.hydricrating, C.drainagecl, H.hzname,
H.desgnmaster, H.chkey, H.hzdept_r, H.hzdepb_r, H.awc_r, H.ksat_r, H.sandtotal_r, H.silttotal_r,
H.claytotal_r, H.sandfine_r AS vfsand, H.om_r, H.dbthirdbar_r, H.ph1to1h2o_r, H.ec_r, ctg.texture,
CT2.texcl as textcls, CT2.lieutex, (SELECT SUM(CF.fragvol_r) FROM chfrags CF
WHERE H.chkey = CF.chkey GROUP BY CF.chkey) AS fragvol
FROM mapunit M
INNER JOIN legend L ON L.lkey = M.lkey
LEFT OUTER JOIN component C ON M.mukey = C.mukey AND C.comppct_r IS NOT NULL
LEFT OUTER JOIN chorizon H ON C.cokey = H.cokey AND H.hzdept_r IS NOT NULL AND H.hzdepb_r IS NOT NULL
LEFT OUTER JOIN (SELECT chkey,  MAX(chtgkey) chtgkey FROM chtexturegrp WHERE rvindicator = 'yes' GROUP BY chkey) CHTG
ON H.chkey = CHTG.chkey
LEFT OUTER JOIN dbo.chtexturegrp ctg ON ctg.chtgkey = chtg.chtgkey
LEFT OUTER JOIN (SELECT chtgkey, MAX(chtkey) chtkey FROM chtexture GROUP BY chtgkey) ct 
ON CT.chtgkey = ctg.chtgkey
LEFT OUTER JOIN chtexture ct2 ON ct2.chtkey = ct.chtkey
WHERE M.mukey IN """ + mukeyQuery + """
ORDER BY M.mukey, C.comppct_r DESC, C.cokey, H.hzdept_r ASC;"""

        #areasymbolList, dataList = AttributeRequest(sdaURL, mukeyList, hzTable, sQuery, "areasymbol")
        #cokeyList = AttributeRequest(sdaURL, txTable, sQuery)
        cokeyList = AttributeRequest(sdaURL, hzTable, sQuery)

        if len(cokeyList) == 0:
            raise MyError, ""


        # Create component restrictions table
        sQuery = """SELECT C.cokey, CR.reskind, CR.reshard, CR.resdept_r
FROM mapunit M
LEFT OUTER JOIN component C on M.mukey = C.mukey
INNER JOIN legend L ON L.lkey = M.lkey
LEFT OUTER JOIN corestrictions CR ON C.cokey = CR.cokey
WHERE M.mukey IN """ + mukeyQuery + """
ORDER BY C.cokey, CR.resdept_r ASC;"""

        cokeyList = AttributeRequest(sdaURL, crTable, sQuery)

        if len(cokeyList) == 0:
            raise MyError, ""

        # Create cointerp table for NCCPI
        # This will grab both NCCPI 2 and 3 if present
        # ["COMPONENT_MUKEY", "COMPONENT_COKEY", "COMPONENT_COMPPCT_R", "COINTERP_RULEDEPTH", "COINTERP_RULENAME", "COINTERP_INTERPHR"]
        sQuery = """SELECT C.mukey, C.cokey, C.comppct_r, CI.ruledepth, CI.rulename, CI.interphr
FROM legend L
INNER JOIN mapunit M ON L.lkey = M.lkey
LEFT OUTER JOIN component C on C.mukey = M.mukey
LEFT OUTER JOIN cointerp CI ON C.cokey = CI.cokey AND C.majcompflag = 'Yes' AND CI.mrulekey = 54955 AND NOT CI.ruledepth IS NULL
WHERE M.mukey IN """ + mukeyQuery + """
ORDER BY M.mukey, C.cokey, C.comppct_r ASC"""


        #cokeyList, dataList = AttributeRequest(sdaURL, areasymbols, interpTable, sQuery, "cokey")
        cokeyList = AttributeRequest(sdaURL, interpTable, sQuery)

        if len(cokeyList) == 0:
            raise MyError, ""

        # Create subset of Valu table from gSSURGO)
        #bValue = CreateValuTable(valuTable, hzTable, crTable, interpTable, mukeyList)
        #PrintMsg("\tPopulating database with " + Number_Format(len(mukeyList), 0, True) + " mapunit records", 1)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSoilsData(db, sdaURL):
    # driving function that calls all other functions in this module
    # acpfDB is the target ACPF geodatabase which must already contain the
    # 'buf' featureclass and the 'wsCDL' rasters.
    #
    try:

        from arcpy import env
        import time
        env.overWriteOutput = True

        # Global variables.
        # It would be better if these were defined as function parameters instead of global variables.
        global muTable, hzTable, crTable, interpTable, txTable

        # Begin by getting a list of mukeys in the mupolygon featureclass

        muPoly = os.path.join(db, "mupolygon")

        if not arcpy.Exists(muPoly):
            raise MyError, "Missing mupolygon featureclass"

        mukeyList = list()
        
        with arcpy.da.SearchCursor(muPoly, ["mukey"], sql_clause=("DISTINCT mukey", "ORDER BY mukey ASC")) as cur:
            for rec in cur:
                mukeyList.append(int(rec[0]))
            
        #PrintMsg(" \nmukeyList: " + str(mukeyList) + " \n ", 1)

        iCnt = len(mukeyList)

        #arcpy.SetProgressor("step", "Creating Valu1 table for " + Number_Format(iCnt, 0, True) + " survey areas...", 0, iCnt, 1)


        if len(mukeyList) > 0:
            mukeyQuery = str(tuple(mukeyList))
            
        PrintMsg(" \nRetrieving data for " + Number_Format(iCnt, 0, True) + " mapunits using Soil Data Access...", 0)
        #time.sleep(2)
        statusCnt = 0

        #for areasymbol in areasymbols:
        time.sleep(1)
        statusCnt += 1

        hzTable = os.path.join(db, "HzData")
        muTable = os.path.join(db, "MuData")
        coTable = os.path.join(db, "CoData")  # Is this one being used?
        crTable = os.path.join(db, "CrData")
        txTable = os.path.join(db, "TxData")
        interpTable = os.path.join(db, "InterpData")
        valuTable = os.path.join(db, "Valu_ACPF")
        coValu = os.path.join(db, "Co_Valu")

        # Get the associated soil attribute data
        #
                        # valuTable, sdaURL, mukeyQuery, db, muTable, coTable, hzTable, crTable, txTable, interpTable 
        if RunQueries(db, valuTable, sdaURL, mukeyQuery, muTable, coTable, hzTable, crTable, txTable, interpTable) == False:
            raise MyError, "Problem getting raw data from SDA"


        # Next step is to see which of the above tables are being populated, and which ones are being used in CreateValuTable
        #raise MyError, "EARLY OUT AFTER RunQueries FUNCTION"

        

        PrintMsg(" \nAll required data has been retrieved from Soil Data Access", 0)
        
        
        arcpy.SetProgressorLabel("Creating " + valuTable + " table from query tables...")
        #                        valuTable, db, muTable, coTable, hzTable, crTable, txTable, interpTable, mukeyList
        bValu = CreateValuTable( db, valuTable, coValu, muTable, coTable, hzTable, crTable, txTable, interpTable, mukeyList)

        # Add attribute indexes for key fields. Moved this to the end to see if there is an improvement in performance
        #arcpy.SetProgressorLabel("Indexing Valu1 table")
        #arcpy.AddIndex_management(valuTable, "MUKEY", "Indx_Valu2Mukey", "NON_UNIQUE", "NON_ASCENDING")

        
        # Cleanup table variables
        del hzTable
        del muTable
        del crTable
        del txTable # not being used anyway
        del interpTable
        del valuTable


        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, arcpy, traceback, urllib2, httplib, json
import xml.etree.cElementTree as ET
from datetime import datetime
from arcpy import env
from random import randint

try:

    if __name__ == "__main__":
        # get parameters
        db = arcpy.GetParameterAsText(0)              # Output file geodatabase that will contain all output including Valu1 table
        #surveyList = arcpy.GetParameter(2)            # list of soil survey areas to be processed

        #baseURL = "https://sdmdataaccess.nrcs.usda.gov"
        sdaURL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"

        # Call function that does all of the work
        bSoils = CreateSoilsData(db, sdaURL)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
