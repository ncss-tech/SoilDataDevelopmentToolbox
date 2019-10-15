# gSSURGO_ImportDSM.py
#
# ArcGIS 10.3 - 10.5.1
#
# Steve Peaslee, National Soil Survey Center, Lincoln, Nebraska
#
# Purpose: Import Raster Soil Survey data into a gSSURGO or gNATSGO database
#
# Some issues I've run into...
#  1. Raster attribute tables: CellValue != Mukey
#  2. NOTCOM in some rasters. These should not be included when mosaicing with the gNATSGO raster.
#  3. NOTCOM in RSS mapunit and component tables should not be copied to gNATSGO database.
#  4. Inconsistent cellsize (Essex is 5m, Boundary Waters is 10m)
#  5. Essex spatial data is UTM meters, NAD1983
#  5. Areasymbol in Essex RSS is the same as the SSURGO Areasymbol
#  6. WMS - Irrigation, Micro (subsurface drip) had two different rulekeys
#  7.

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        excInfo = sys.exc_info()
        tb = excInfo[2]
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
        locale.setlocale(locale.LC_ALL, "")
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
def AddNewFields(outputShp, columnNames, columnInfo):
    # TEMPORARY CODE
    #
    # Create the empty output table that will contain the data from Soil Data Access
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
        #arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

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
def GetSDMInfo(theURL, tblName):
    # TEMPORARY CODE
    #
    # POST REST which uses urllib and JSON
    #
    # Send query to SDM Tabular Service, returning data in JSON format

    try:
        if theURL == "":
            theURL = "https://sdmdataaccess.sc.egov.usda.gov"

        sQuery = """SELECT TOP 1 * FROM """ + tblName

        #PrintMsg(" \nRequesting tabular data for " + Number_Format(len(keyList), 0, True) + " soil survey areas...")
        arcpy.SetProgressorLabel("Sending tabular request for " + tblName + " to Soil Data Access...")

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
def SetScratch():
    # try to set scratchWorkspace and scratchGDB if null
    #        SYSTEMDRIVE
    #        APPDATA C:\Users\adolfo.diaz\AppData\Roaming
    #        USERPROFILE C:\Users\adolfo.diaz
    try:
        #envVariables = os.environ

        #for var, val in envVariables.items():
        #    PrintMsg("\t" + str(var) + ": " + str(val), 1)

        if env.scratchWorkspace is None:
            #PrintMsg("\tWarning. Scratchworkspace has not been set for the geoprocessing environment", 1)
            env.scratchWorkspace = env.scratchFolder
            #PrintMsg("\nThe scratch geodatabase has been set to: " + str(env.scratchGDB), 1)

        elif str(env.scratchWorkspace).lower().endswith("default.gdb"):
            #PrintMsg("\tChanging scratch geodatabase from Default.gdb", 1)
            env.scratchWorkspace = env.scratchFolder
            #PrintMsg("\tTo: " + str(env.scratchGDB), 1)

        #else:
        #    PrintMsg(" \nOriginal Scratch Geodatabase is OK: " + env.scratchGDB, 1)

        if env.scratchGDB:
            return True
        
        else:
            return False

    
    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def SetOutputCoordinateSystem(inLayer, AOI):
    #
    # Not being used any more!
    #
    # The GetXML function is now used to set the XML workspace
    # document and a single NAD1983 to WGS1984 datum transformation (ITRF00) is now being used.
    #
    # Below is a description of the 2013 settings
    # Set a hard-coded output coordinate system (Geographic WGS 1984)
    # Set an ESRI datum transformation method for NAD1983 to WGS1984
    # Based upon ESRI 10.1 documentation and the methods that were used to
    # project SDM featureclasses during the transition from ArcSDE to SQL Server spatial
    #
    #   CONUS - NAD_1983_To_WGS_1984_5
    #   Hawaii and American Samoa- NAD_1983_To_WGS_1984_3
    #   Alaska - NAD_1983_To_WGS_1984_5
    #   Puerto Rico and U.S. Virgin Islands - NAD_1983_To_WGS_1984_5
    #   Other  - NAD_1983_To_WGS_1984_1 (shouldn't run into this case)

    try:
        outputSR = arcpy.SpatialReference(4326)        # GCS WGS 1984
        # Get the desired output geographic coordinate system name
        outputGCS = outputSR.GCS.name

        # Describe the input layer and get the input layer's spatial reference, other properties
        desc = arcpy.Describe(inLayer)
        dType = desc.dataType
        sr = desc.spatialReference
        srType = sr.type.upper()
        inputGCS = sr.GCS.name

        # Print name of input layer and dataype
        if dType.upper() == "FEATURELAYER":
            #PrintMsg(" \nInput " + dType + ": " + desc.nameString, 0)
            inputName = desc.nameString

        elif dType.upper() == "FEATURECLASS":
            #PrintMsg(" \nInput " + dType + ": " + desc.baseName, 0)
            inputName = desc.baseName

        else:
            #PrintMsg(" \nInput " + dType + ": " + desc.name, 0)
            inputName = desc.name

        if outputGCS == inputGCS:
            # input and output geographic coordinate systems are the same
            # no datum transformation required
            #PrintMsg(" \nNo datum transformation required", 0)
            tm = ""

        else:
            # Different input and output geographic coordinate systems, set
            # environment to unproject to WGS 1984, matching Soil Data Mart
            tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        # These next two lines set the output coordinate system environment
        arcpy.env.outputCoordinateSystem = outputSR
        arcpy.env.geographicTransformations = tm

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateSSURGO_DB(outputWS, inputXML, areasymbolList, aliasName):
    # Create new 10.0 File Geodatabase using XML workspace document
    #
    try:
        if not arcpy.Exists(inputXML):
            PrintMsg(" \nMissing input file: " + inputXML, 2)
            return False

        outputFolder = os.path.dirname(outputWS)
        gdbName = os.path.basename(outputWS)

        if arcpy.Exists(os.path.join(outputFolder, gdbName)):
            arcpy.Delete_management(os.path.join(outputFolder, gdbName))

        PrintMsg(" \nCreating new geodatabase (" + gdbName + ") in " + outputFolder, 0)

        arcpy.CreateFileGDB_management(outputFolder, gdbName, "10.0")

        # The following command will fail when the user only has a Basic license
        arcpy.ImportXMLWorkspaceDocument_management(os.path.join(outputFolder, gdbName), inputXML, "SCHEMA_ONLY")

        # Create indexes for cointerp here.
        # If it works OK, incorporate these indexes into the xml workspace document
        try:
            pass

        except:
            PrintMsg(" \nUnable to index the cointerp table", 1)

        if not arcpy.Exists(os.path.join(outputFolder, gdbName)):
            raise MyError, "Failed to create new geodatabase"

        env.workspace = os.path.join(outputFolder, gdbName)
        tblList = arcpy.ListTables()

        if len(tblList) < 50:
            raise MyError, "Output geodatabase has only " + str(len(tblList)) + " tables"

        # Alter aliases for featureclasses
        if aliasName != "":
            try:
                arcpy.AlterAliasName("MUPOLYGON", "Map Unit Polygons - " + aliasName)
                arcpy.AlterAliasName("MUPOINT", "Map Unit Points - " + aliasName)
                arcpy.AlterAliasName("MULINE", "Map Unit Lines - " + aliasName)
                arcpy.AlterAliasName("FEATPOINT", "Special Feature Points - " + aliasName)
                arcpy.AlterAliasName("FEATLINE", "Special Feature Lines - " + aliasName)
                arcpy.AlterAliasName("SAPOLYGON", "Survey Boundaries - " + aliasName)

            except:
                pass

        arcpy.RefreshCatalog(outputFolder)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetTableList(outputWS):
    # Query mdstattabs table to get list of input text files (tabular) and output tables
    # This function assumes that the MDSTATTABS table is already present and populated
    # in the output geodatabase per XML Workspace Document.
    #
    # Skip all 'MDSTAT' tables. They are static.
    #
    try:
        tblList = list()
        mdTbl = os.path.join(outputWS, "mdstattabs")

        if not arcpy.Exists(outputWS):
            raise MyError, "Missing output geodatabase: " + outputWS

        if not arcpy.Exists(mdTbl):
            raise MyError, "Missing mdstattabs table in output geodatabase"

        else:
            # got the mdstattabs table, create list
            #mdFields = ('tabphyname','iefilename')
            mdFields = ('tabphyname')

            with arcpy.da.SearchCursor(mdTbl, mdFields) as srcCursor:
                for rec in srcCursor:
                    tblName = rec[0].lower()
                    if not tblName in tblList and not tblName.startswith('mdstat') and not tblName in ('mupolygon', 'muline', 'mupoint', 'featline', 'featpoint', 'sapolygon'):
                        tblList.append(tblName)

        return tblList

    except MyError, e:
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def GetLastDate(inputDB):
    # Get the most recent date 'YYYYMMDD' from SACATALOG.SAVEREST and use it to populate metadata
    #
    try:
        tbl = os.path.join(inputDB, "SACATALOG")
        today = ""
        sqlClause = [None, "ORDER BY SAVEREST DESC"]

        with arcpy.da.SearchCursor(tbl, ['SAVEREST'], sql_clause=sqlClause ) as cur:
            for rec in cur:
                lastDate = rec[0].strftime('%Y%m%d')
                break

        return lastDate


    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def GetTemplateDate(newDB, areaSym):
    # Get SAVEREST date from previously existing Template database
    # Use it to compare with the date from the WSS dataset
    # If the existing database is same or newer, it will be kept and the WSS version skipped.
    # This function is also used to test the output geodatabase to make sure that
    # the tabular import process was successful.
    #
    # Right now I am not using this function with the NASIS Exports, but may need to add it
    # back in if I want to allow exports to be merged, keeping only the most recent version.
    #
    try:
        if not arcpy.Exists(newDB):
            return 0

        saCatalog = os.path.join(newDB, "SACATALOG")
        dbDate = 0
        whereClause = "UPPER(AREASYMBOL) = '" + areaSym.upper() + "'"
        #PrintMsg(" \nWhereClause for sacatalog: " + areaSym, 1)

        if arcpy.Exists(saCatalog):
            with arcpy.da.SearchCursor(saCatalog, ("SAVEREST"), where_clause=whereClause) as srcCursor:
                for rec in srcCursor:
                    dbDate = str(rec[0]).split(" ")[0]

            del saCatalog
            del newDB
            return dbDate

        else:
            # unable to open SACATALOG table in existing dataset
            return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def SSURGOVersionTxt(tabularFolder):
    # For future use. Should really create a new table for gSSURGO in order to implement properly.
    #
    # Get SSURGO version from the Template database "SYSTEM Template Database Information" table
    # or from the tabular/version.txt file, depending upon which is being imported.
    # Compare the version number (first digit) to a hardcoded version number which should
    # be theoretically tied to the XML workspace document that accompanies the scripts.

    try:
        # Get SSURGOversion number from version.txt
        versionTxt = os.path.join(tabularFolder, "version.txt")

        if arcpy.Exists(versionTxt):
            # read just the first line of the version.txt file
            fh = open(versionTxt, "r")
            txtVersion = int(fh.readline().split(".")[0])
            fh.close()
            return txtVersion

        else:
            # Unable to compare vesions. Warn user but continue
            PrintMsg("Unable to find tabular file: version.txt", 1)
            return 0

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def SSURGOVersionDB(templateDB):
    # For future use. Should really create a new table for gSSURGO in order to implement properly.
    #
    # Get SSURGO version from the Template database "SYSTEM Template Database Information" table

    try:
        if not arcpy.Exists(templateDB):
            raise MyError, "Missing input database (" + newDB + ")"

        systemInfo = os.path.join(templateDB, "SYSTEM - Template Database Information")

        if arcpy.Exists(systemInfo):
            # Get SSURGO Version from template database
            dbVersion = 0

            with arcpy.da.SearchCursor(systemInfo, "*", "") as srcCursor:
                for rec in srcCursor:
                    if rec[0] == "SSURGO Version":
                        dbVersion = int(str(rec[2]).split(".")[0])
                        #PrintMsg("\tSSURGO Version from DB: " + dbVersion, 1)

            del systemInfo
            del templateDB
            return dbVersion

        else:
            # Unable to open SYSTEM table in existing dataset
            # Warn user but continue
            raise MyError, "Unable to open 'SYSTEM - Template Database Information'"


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def ImportMDTables(newDB, dsmDB):
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
        # 
        for table in tables:
            arcpy.SetProgressorLabel("Importing " + table + "...")
            PrintMsg("\tImporting table " + table, 0)
            inTbl = os.path.join(dsmDB, table)
            outTbl = os.path.join(newDB, table)

            if arcpy.Exists(inTbl) and arcpy.Exists(outTbl):
                # Create cursor for all fields to populate the current table
                #
                # For a geodatabase, I need to remove OBJECTID from the fields list
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

        arcpy.SetProgressorLabel("")
        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ImportTables(outputWS, dsmDB):
    #
    # Import tables from RSS database. Does not require text files
    # Origin: SSURGO_Convert_to_Geodatabase.py

    try:
        tblList = GetTableList(outputWS)

        if len(tblList) == 0:
            raise MyError, "No tables found in " +  outputWS

        PrintMsg(" \nImporting tabular data from RSS database " + dsmDB + "...", 0)

        # Create lists of key values to use in preventing duplicate keys in some SDV* tables
        #
        dKeys = dict() # dictionary containing a list of key values for each SDV table

        keyIndx = dict()  # dictionary containing key field index number for each SDV table
        # Do I need to add 1 to each index since the input is a file geodatabase table?
        
        keyIndx['sdvfolderattribute'] = 2
        keyIndx['sdvattribute'] = 1
        keyIndx['sdvfolder'] = 4
        keyIndx['sdvalgorithm'] = 1
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"

        # Getting list of primary key values for each of these sdv tables in the gNATSGO database
        for sdvTbl in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
            indx = keyIndx[sdvTbl]
            fldName = keyFields[sdvTbl]
            attKeys = list()

            with arcpy.da.SearchCursor(os.path.join(outputWS, sdvTbl), (keyFields[sdvTbl])) as sdvCur:
                for rec in sdvCur:
                    attKeys.append(rec[0])

            dKeys[sdvTbl] = attKeys

        # End of sdv keys


        for tblName in tblList:
            # Import data for each table
            #
            outputTbl = os.path.join(outputWS, tblName)
            inputTbl = os.path.join(dsmDB, tblName)

            if arcpy.Exists(inputTbl):

                with arcpy.da.SearchCursor(inputTbl, "*") as sdvCur:
                    outCur = arcpy.da.InsertCursor(outputTbl, "*")

                    # dbAreasymbol is not being used and will error in this next line
                    # arcpy.SetProgressorLabel("Importing " +  dbAreaSymbol.upper() + "  (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(dbList), 0, True) + "): " + tblName)
                    arcpy.SetProgressorLabel("Importing RSS table: " + tblName)
                    PrintMsg("\tImporting table from RSS: " + tblName, 0)

                    if tblName.lower() in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
                        # Process the 'SDV' tables separately to prevent key errors from duplicate records
                        #
                        indx = keyIndx[tblName]

                        for rec in sdvCur:
                            if not rec[indx] in dKeys[tblName]:
                                dKeys[tblName].append(rec[indx])
                                outCur.insertRow(rec)

                    elif tblName.lower() == "mapunit":
                        fields = sdvCur.fields
                        musymIndx = [f.lower() for f in fields].index("musym")
                        
                        for rec in sdvCur:
                            if not rec[musymIndx] == "NOTCOM":
                                outCur.insertRow(rec)

                    elif tblName.lower() == "component":
                        fields = sdvCur.fields
                        compIndx = [f.lower() for f in fields].index("compname")
                        
                        for rec in sdvCur:
                            if not rec[compIndx] == "NOTCOM":
                                outCur.insertRow(rec)
                        
                    else:
                        # Process the rest of the 'non-SDV' tables
                        #
                        for rec in sdvCur:
                            outCur.insertRow(rec)

            else:
                err = "\tError. Could not find table " + tblName
                raise MyError, err


        arcpy.RefreshCatalog(outputWS)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===============================================================================================================
def MergeData(outputWS, dsmRasterLayer, outputRaster, newMukeys):
    #
    # Mosaic gNATSGO


    """
    1. Create new LookupTbl.
    2. Add CELLVALUE (long) and MUKEY.
    3. Open raster table and LookupTbl with Search and InsertCursor.
    4. Calculate CELLVALUE and MUKEY for all records unless MUSYM='NOTCOM'.
    4. Join LookupTbl to raster attribute on mukey
    5. Select all records except NOTCOM
    6. Use Lookup_sa on LookupTbl.CELLVALUE
    Use JoinField to add MUSYM and MUKEY to new raster.

    """
    try:
        PrintMsg(" \nUpdating raster layer....", 0)

        # Create lookup table for mukey values to facilitate raster conversion
        # and addition of mukey column to raster attribute table.
        arcpy.CheckOutExtension("Spatial")
        lu = os.path.join(env.scratchGDB, "LookupTbl")

        if arcpy.Exists(lu):
            arcpy.Delete_management(lu)

        # Get projection for output raster
        #rasDesc = arcpy.Describe(outputRaster)
        #rasPrj = rasDesc.spatialReference
        #iRaster = rasDesc.meanCellHeight

        # The Lookup table contains both MUKEY and its integer counterpart (CELLVALUE).
        # Using the joined lookup table creates a raster with CellValues that are the
        # same as MUKEY (but integer). This will maintain correct MUKEY values
        # during a moscaic or clip.
        #
        PrintMsg("\tCreating Lookup table (" + lu + "...", 0)
        arcpy.CreateTable_management(os.path.dirname(lu), os.path.basename(lu))
        arcpy.AddField_management(lu, "CELLVALUE", "LONG")
        arcpy.AddField_management(lu, "MUKEY", "TEXT", "#", "#", "30")                                                              

        with arcpy.da.InsertCursor(lu, ("CELLVALUE", "MUKEY")) as inCursor:
            
            for mukey in newMukeys:
                rec = mukey, mukey
                inCursor.insertRow(rec)

        # Add MUKEY attribute index to Lookup table
        arcpy.AddIndex_management(lu, ["mukey"], "Indx_LU")
        #PrintMsg(" \nJoining Lookup table...", 1)
        arcpy.AddJoin_management (dsmRasterLayer, "MUKEY", lu, "MUKEY", "KEEP_ALL")

        arcpy.SetProgressorLabel("Updating input raster...")
        #env.extent = fullExtent

        # Need to make sure that the join was successful
        time.sleep(1)
        rasterFields = arcpy.ListFields(dsmRasterLayer)
        rasterFieldNames = list()

        for rFld in rasterFields:
            rasterFieldNames.append(rFld.name.upper())

        if not "LOOKUPTBL.CELLVALUE" in rasterFieldNames:
            raise MyError, "Join failed for Lookup table (CELLVALUE)"

        env.pyramid = "PYRAMIDS 0 NEAREST"

        # The original RSS raster is crippled because it does not have a unique cell value based
        # upon mukey. Use Lookup sa function to create a new temporary raster.
        env.snapRaster = outputRaster
        env.cellSize = outputRaster
        fixedRas = os.path.join(env.scratchGDB, "xxRaster")
        tmpRas = Lookup(dsmRasterLayer, "LookupTbl.CELLVALUE")
        tmpRas.save(fixedRas)
        arcpy.RemoveJoin_management(dsmRasterLayer, os.path.basename(lu))
        

        # ****************************************************
        # Build pyramids and statistics
        # ****************************************************
        #
        # DO I NEED TO HAVE STATISTICS FOR THIS INTERIM RASTER?
        #
        #
        if arcpy.Exists(fixedRas):
            time.sleep(3)

            # ****************************************************
            # Add MUKEY to final raster
            # ****************************************************
            # Build attribute table for final output raster. Sometimes it fails to automatically build.
            PrintMsg("\tBuilding raster attribute table and updating MUKEY values (" + fixedRas + ")", )
            #arcpy.SetProgressor("default", "Building raster attribute table...")
            arcpy.BuildRasterAttributeTable_management(fixedRas)
            arcpy.AddField_management(fixedRas, "MUKEY", "TEXT", "#", "#", "30")

            with arcpy.da.UpdateCursor(fixedRas, ["VALUE", "MUKEY"]) as cur:
                for rec in cur:
                    rec[1] = str(rec[0])
                    cur.updateRow(rec)

        else:
            err = "Missing output raster (" + fixedRas + ")"
            raise MyError, err
        
        #

        # Merge the gSSURGO raster and statsgo_ras using Mosaic
        arcpy.ResetProgressor()
        #newRaster = os.path.join(outputWS, "MergedRaster")

        
        ssurgoRaster = os.path.join(outputWS, outputRaster)

        
        PrintMsg("\tMerging the RSS and gNATSGO rasters...", 0)
        arcpy.SetProgressor("default", "Merging the RSS and gNATSGO rasters...")
        #pixType = "32_BIT_UNSIGNED"Updating 
        #cellSize = 10
        nBands = 1
        mosaicMethod = "LAST"
        # Mosaic the existing mapunit raster with the new RSS raster. The new raster has priority.
        arcpy.Mosaic_management([fixedRas], outputRaster, "LAST", "", "", "", "NONE", 0.5, "NONE")
        
        PrintMsg("\tRebuilding attribute table for updated raster (" + outputRaster + ")", 0)
        arcpy.SetProgressor("default", "Building raster attribute table...")
        arcpy.BuildRasterAttributeTable_management(outputRaster)

        PrintMsg(" \n\tIs it necessary to calculate mukey values after mosaic?", 1)
        
        with arcpy.da.UpdateCursor(outputRaster, ["VALUE", "MUKEY"]) as cur:
            for rec in cur:
                rec[1] = rec[0]
                cur.updateRow(rec)

        arcpy.SetProgressor("default", "Updating raster statistics...")
        arcpy.CalculateStatistics_management (outputRaster, 1, 1, "", "OVERWRITE" )
        arcpy.SetProgressor("default", "Building pyramids for new raster...")
        PrintMsg("\tBuilding pyramids for new raster", 0)
        arcpy.BuildPyramids_management(outputRaster, 0, "NONE", "NEAREST", "DEFAULT", "", "OVERWRITE")
        arcpy.BuildPyramids_management(outputRaster, -1, "NONE", "NEAREST", "DEFAULT", "", "OVERWRITE")
        arcpy.ResetProgressor()

        if 1 == 1:
            # Skipping creation of RSS mupolygon 
            # Convert fixedRas to a temporary polygon featureclass for inclusion in the output MUPOLYGON featureclass
            #
            #PrintMsg(" \nCreating RSS soil polygon featureclass...", 0)
            #newPolygons = os.path.join(env.scratchGDB, "xxMupolygons")
            #arcpy.SetProgressor("default", "Creating RSS soil polygon featureclass...")
            #arcpy.RasterToPolygon_conversion(fixedRas, newPolygons, "NO_SIMPLIFY", "VALUE")
            # Use gridcode to add and calculate MUKEY.
            # Output polygon featureclass has extra columns 'Id' and 'gridcode' that need to be dropped
            # Add other attribute fields and calculate using mapunit table and legend table: AREASYMBOL, SPATIALVER, MUSYM, MUKEY
            # Also need to dissolve this featureclass to create SAPOLYGON with AREASYMBOL, SPATIALVER, LKEY

            # Get legend info, assuming this is a single survey area
            arcpy.SetProgressorLabel("Updating RSS attributes for legend and mapunit tables...")
            legendTbl = os.path.join(dsmDB, "legend")
            dLegend = dict()
            dAreasymbol = dict()

            with arcpy.da.SearchCursor(legendTbl, ["areasymbol", "lkey"]) as cur:
                for rec in cur:
                    areasym, lkey = rec
                    dLegend[lkey] = areasym
                    dAreasymbol[areasym] = lkey
                                       
            if len(dLegend) == 1:
                # As expected, the RSS database consists of a single survey area
                pass

            else:
                raise MyError, "RSS database consists of " + str(len(dLegend)) + " survey areas"

            # Get legend info, assuming this is a single survey area
            mapunitTbl = os.path.join(dsmDB, "mapunit")
            dMapunit = dict()

            with arcpy.da.SearchCursor(mapunitTbl, ["mukey", "musym", "lkey"]) as cur:
                for rec in cur:
                    mukey, musym, lkey = rec
                    areasym = dLegend[lkey]
                    dMapunit[mukey] = (musym, areasym)
                    saList = [areasym, lkey, "DRSS"]
                   
            fldName = "AREASYMBOL"
            dataType = "TEXT"
            precision = ""
            scale = ""
            length = 7
            #arcpy.AddField_management(newPolygons, fldName, dataType, precision, scale, length)

            fldName = "SPATIALVER"
            dataType = "DOUBLE"
            precision = ""
            scale = ""
            length = ""
            #arcpy.AddField_management(newPolygons, fldName, dataType, precision, scale, length) 

            fldName = "MUSYM"
            dataType = "TEXT"
            precision = ""
            scale = ""
            length = 6
            #arcpy.AddField_management(newPolygons, fldName, dataType, precision, scale, length)

            fldName = "MUKEY"
            dataType = "TEXT"
            precision = ""
            scale = ""
            length = 30
            #arcpy.AddField_management(newPolygons, fldName, dataType, precision, scale, length)

            spatialver = 0
            
            # Populate RSS polygon attributes
            #PrintMsg("\tUpdating RSS soil polygon attributes for " + newPolygons, 1)
            #arcpy.SetProgressorLabel("Updating RSS polygon attributes..")
            #pCnt = int(arcpy.GetCount_management(newPolygons).getOutput(0)) - 1
            #arcpy.SetProgressor("step", "Updating RSS polygon attributes..", 0, pCnt, 1)
            
            #with arcpy.da.UpdateCursor(newPolygons, ["gridcode", "areasymbol", "spatialver", "musym", "mukey"]) as cur:
            #    for rec in cur:
            #        gridcode = rec[0]
            #        mukey = str(gridcode)
            #        musym, areasym = dMapunit[mukey]
            #        newrec = [gridcode, areasym, spatialver, musym, mukey]
            #        cur.updateRow(newrec)
            #        arcpy.SetProgressorPosition()
                    

            #arcpy.DeleteField_management(newPolygons, "Id")
            #arcpy.DeleteField_management(newPolygons, "gridcode")

        
        # Create SAPOLYGON equivalent for RSS survey
        #
        # Also very slow, but perhaps that's just the Update process that follows?
        #
        saPolygons = os.path.join(env.scratchGDB, "xxSapolygons")
        PrintMsg(" \nCreating RSS survey boundary featureclass (" + saPolygons + ")", 0)
        arcpy.SetProgressor("default", "Creating RSS survey boundary featureclass...")
        #arcpy.Dissolve_management(newPolygons, saPolygons, "AREASYMBOL", "", "SINGLE_PART")

        # Create constant raster based upon original RSS raster
        # Problem here. NoData cells are being included. I don't want those.
        saRas = Con(dsmRasterLayer, 1, "#", "VALUE > 0")
        arcpy.RasterToPolygon_conversion(saRas, saPolygons, "NO_SIMPLIFY", "VALUE")

        fldName = "AREASYMBOL"
        dataType = "TEXT"
        precision = ""
        scale = ""
        length = 20
        arcpy.AddField_management(saPolygons, fldName, dataType, precision, scale, length)
        
        fldName = "SPATIALVER"
        dataType = "DOUBLE"
        precision = ""
        scale = ""
        length = ""
        arcpy.AddField_management(saPolygons, fldName, dataType, precision, scale, length)

        fldName = "LKEY"
        dataType = "TEXT"
        precision = ""
        scale = ""
        length = 30
        arcpy.AddField_management(saPolygons, fldName, dataType, precision, scale, length)

        fldName = "SOURCE"
        dataType = "TEXT"
        precision = ""
        scale = ""
        length = 30
        arcpy.AddField_management(saPolygons, fldName, dataType, precision, scale, length)

        with arcpy.da.UpdateCursor(saPolygons, ["areasymbol", "lkey", "source"]) as cur:
            for rec in cur:
                #lkey = dAreasymbol[rec[0]]
                rec = saList  # Here I am assuming there is only one areasymbol in this RSS survey
                cur.updateRow(rec)
        

        # Finally, update the soil polygons and survey polygons using the xx layers in scratchGDB
        # The updates seem to be very slow. Tiling takes place.
        # Also need to incorporate the STATSGO 'US' polygons into the SAPOLYGON featureclass. This
        # should be done in the other script.
        #
        tmpSaPolygons = os.path.join(env.scratchGDB, "tmpSapolygon")
        saPolygonFC = os.path.join(outputWS, "SAPOLYGON")
        PrintMsg(" \nUpdating " + tmpSaPolygons, 1)
        arcpy.SetProgressor("default", "Updating " + tmpSaPolygons + "...")
        arcpy.Update_analysis(saPolygonFC, saPolygons, tmpSaPolygons, "BORDERS", 0)

        # Make sure that tmpSaPolygons has a SOURCE column
        saFields = arcpy.Describe(tmpSaPolygons).fields
        saFieldNames = [f.name.lower() for f in saFields]

        if not "source" in saFieldNames:
            arcpy.AddField_management(tmpSaPolygons, "SOURCE", "TEXT", "", "", 30)

        # Make sure that tmpSaPolygons has a SOURCE column
        saFields = arcpy.Describe(saPolygons).fields
        saFieldNames = [f.name.lower() for f in saFields]

        if not "source" in saFieldNames:
            arcpy.AddField_management(saPolygons, "SOURCE", "TEXT", "", "", 30)


        # Make sure that tmpSaPolygons has a SOURCE column
        saFields = arcpy.Describe(saPolygonFC).fields
        saFieldNames = [f.name.lower() for f in saFields]

        if not "source" in saFieldNames:
            arcpy.AddField_management(saPolygonFC, "SOURCE", "TEXT", "", "", 30)

        # Update SAPOLYGON featureclass. Not at all sure if this is designed properly.
        #
        if arcpy.Exists(tmpSaPolygons):
            # Replace SAPOLYGON features
            arcpy.TruncateTable_management(saPolygonFC)
            PrintMsg(" \nTransferring data from " + tmpSaPolygons + " to " + saPolygonFC, 1)

            with arcpy.da.InsertCursor(saPolygonFC, ["shape@", "areasymbol", "spatialver", "lkey", "source"]) as udCur:
                sCur = arcpy.da.SearchCursor(tmpSaPolygons, ["shape@", "areasymbol", "spatialver", "lkey", "source"])
                
                for rec in sCur:
                    newRec = list(rec)
                    
                    if newRec[-1] is None and rec[2] is None:
                        # if source is None and spatialver is None then assume this is RSS data
                        newRec[-1] = "DRSS"
                        #PrintMsg("\tDRSS added", 1)

                    elif newRec[-1] is None:
                        # if only source is None, assume this is SSURGO
                        newRec[-1] = "SSURGO"
                        
                    udCur.insertRow(newRec)

                del sCur

            arcpy.Delete_management(tmpSaPolygons)
            del tmpSaPolygons
            
        if 1 == 2:
            # Skipping this mupolygon section for RSS
            # Update MUPOLYGON featureclass
            PrintMsg(" \nSkipping MUPOLYGON update...", 1)
            if 1 == 2:
                tmpMuPolygons = os.path.join(outputWS, "tmpMupolygons")
                mupolygonFC = os.path.join(outputWS, "MUPOLYGON")
                PrintMsg(" \nUpdating " + tmpMuPolygons, 1)
                arcpy.SetProgressor("default", "Updating " + tmpMuPolygons + "...")
                arcpy.Update_analysis(mupolygonFC, newPolygons, tmpMuPolygons, "BORDERS", 0)  # slow!
                muCnt = int(arcpy.GetCount_management(tmpMuPolygons).getOutput(0))
                arcpy.SetProgressor("step", "Updating " + mupolygonFC, 1, muCnt, 1)
                
                if arcpy.Exists(tmpMuPolygons):
                    PrintMsg(" \nUpdating " + mupolygonFC, 1)
                    # Replace SAPOLYGON features
                    arcpy.TruncateTable_management(mupolygonFC)

                    with arcpy.da.InsertCursor(mupolygonFC, ["shape@", "areasymbol", "spatialver", "musym", "mukey"]) as udCur:
                        sCur = arcpy.da.SearchCursor(tmpMuPolygons, ["shape@", "areasymbol", "spatialver", "musym", "mukey"])
                        
                        for rec in sCur:
                            udCur.insertRow(rec)
                            arcpy.SetProgressorPosition()

                        del sCur

                    arcpy.Delete_management(tmpMuPolygons)
                    del tmpMuPolygons
                        
        
        arcpy.CheckInExtension("Spatial")

        #PrintMsg(" \nStill need to add the step to delete the original Mu and Sa polygon layer and rename", 1)
        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetSoilPolygons(outputWS, AOI, soilPolygons, featCnt, bValidation, bUpdateMukeys, wc):
    # outputWS, AOI, soilPolygons, featCnt
    # Merge all spatial layers into a set of file geodatabase featureclasses
    # Compare shapefile feature count to GDB feature count
    # featCnt:  0 mupoly, 1 muline, 2 mupoint, 3 sfline, 4 sfpoint, 5 sapoly
    #
    # Not being used right now for the NASIS-SSURGO Export process
    
    try:
        # Set output workspace
        env.workspace = outputWS

        # Put datum transformation methods in place
        #AOI = "CONUS"
        PrintMsg(" \nImporting spatial data...", 0)

        # Problem if soil polygon shapefile has MUNAME column or other alterations
        # Need to use fieldmapping parameter to fix append error.
        fieldmappings = arcpy.FieldMappings()
        fieldmappings.addTable(os.path.join(outputWS, "MUPOLYGON"))
        fieldmappings.addTable(os.path.join(outputWS, "MULINE"))
        fieldmappings.addTable(os.path.join(outputWS, "MUPOINT"))
        fieldmappings.addTable(os.path.join(outputWS, "FEATLINE"))
        fieldmappings.addTable(os.path.join(outputWS, "FEATPOINT"))
        fieldmappings.addTable(os.path.join(outputWS, "SAPOLYGON"))

        # Assuming input featureclasses from Web Soil Survey are GCS WGS1984 and that
        # output datum is either NAD 1983 or WGS 1984. Output coordinate system will be
        # defined by the existing output featureclass.

        # WITH XML workspace method, I need to use Append_management


        # Merge process MUPOLYGON


        PrintMsg(" \n\tAppending ALL soil mapunit polygons to create new featureclass: MUPOLYGON", 0)
        
        arcpy.SetProgressorLabel("Appending features to MUPOLYGON layer")
        #wc = "areasymbol IN " + queryInfo

        desc = arcpy.Describe(soilPolygons)
        dType = desc.dataType
        soilLayer = "SelectedSet"
        arcpy.MakeFeatureLayer_management(soilPolygons, soilLayer, wc)

        selCnt = int(arcpy.GetCount_management(soilLayer).getOutput(0))
        missingMapunits = list()

        if selCnt == 0:
            raise MyError, "Failed to find matching mapunits in " + soilPolygons + " layer"
        
        arcpy.Append_management([soilLayer],  os.path.join(outputWS, "MUPOLYGON"), "NO_TEST", fieldmappings )
        arcpy.Delete_management(soilLayer)

        if bUpdateMukeys:
            # Using draft soil polygon layer that has missing or out-of-date mukeys
            missingMapunits = UpdateMukeys(outputWS)

            if len(missingMapunits) > 0:
                PrintMsg(" \n\tFailed to find tabular match for the following map units:  " + ", ".join(missingMapunits), 1)
       
        # For the NASIS-SSURGO Export data, we need to make sure that the tabular and spatial
        # mukeys match. Need to consult with Kyle and Steve C about the best way to handle
        # this from the perspective of an SDQS or State Soil Scientist
        if bValidation:
            # Make sure mapunits and soil polygons match mukeys
            # This should not be necessary for STATSGO. Should primarily be used for initial surveys.
            bValid = CheckMatch(outputWS)

        else:
            # May want to skip validation for very large datasets
            bValid = True

        if bValid == False:
            raise MyError, "Failed validation"

        # Probably need to fix this, but for now I'm assuming that there is only a single input soil polygon layer

        # Add spatial index
        arcpy.AddSpatialIndex_management (os.path.join(outputWS, "MUPOLYGON"))
        arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUKEY", "Indx_MupolyMukey")
        arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUSYM", "Indx_MupolyMusym")
        arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "AREASYMBOL", "Indx_MupolyAreasymbol")
        arcpy.RefreshCatalog(outputWS)

        return missingMapunits

    except MyError, e:
        PrintMsg(str(e), 2)
        return missingMapunits

    except:
        errorMsg()
        return missingMapunits

## ===============================================================================================================
def CheckMatch(outputWS):
    # Compare spatial to tabular. Report any missing mapunits from either direction.
    # Working with mapunit and MUPOLYGON tables

    try:
        arcpy.SetProgressorLabel("Validating join between spatial and tabular...")
        mapunitTbl = os.path.join(outputWS, "mapunit")
        mupolygonTbl = os.path.join(outputWS, "mupolygon")

        mapunitList = list()
        mupolygonList = list()

        with arcpy.da.SearchCursor(mapunitTbl, ["mukey"]) as cur:
            # should generate a unique list of mukeys
            for rec in cur:
                mapunitList.append(rec[0].encode('ascii'))

        with arcpy.da.SearchCursor(mupolygonTbl, ["mukey"]) as cur:
            # should generate a non-unique list of mukeys
            for rec in cur:
                if not rec[0] is None:
                    mupolygonList.append(rec[0].encode('ascii'))

        mupolygonList = list(set(mupolygonList)) # now make this list unique
                                   
        missingMupolygon = set(mapunitList) - set(mupolygonList)
        missingMapunit = set(mupolygonList) - set(mapunitList)
        

        if len(missingMupolygon) > 0:
            PrintMsg(" \n\t" + mupolygonTbl + " has " + Number_Format(len(missingMupolygon), 0, True) + " mapunit(s) with no match to the NASIS export", 1)
            PrintMsg(" \n\tmukeys: " + ",".join(missingMupolygon), 1)
            arcpy.SetProgressorLabel("Validation complete. Missing mapunits in spatial.")
            return False

        if len(missingMapunit) > 0:
            PrintMsg(" \n\t" + mapunitTbl + " has " + Number_Format(len(missingMapunit), 0, True) + " mapunit(s) with no match in the spatial layer", 1)
            PrintMsg(" \n\tmukeys: " + ",".join(missingMapunit), 1)
            arcpy.SetProgressorLabel("Validation complete. Missing mapunits in tabular.")
            return False

        arcpy.SetProgressorLabel("Validation successful. Spatial and tabular data match.")
        PrintMsg(" \n\tValidation successful. Spatial and tabular data match.", 0)
        return True
              
        
    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===============================================================================================================
def GetTableInfo(newDB):
    # Adolfo's function
    #
    # Retrieve physical and alias names from MDSTATTABS table and assigns them to a blank dictionary.
    # Stores physical names (key) and aliases (value) in a Python dictionary i.e. {chasshto:'Horizon AASHTO,chaashto'}
    # Fieldnames are Physical Name = AliasName,IEfilename

    try:
        tblInfo = dict()

        # Open mdstattabs table containing information for other SSURGO tables
        theMDTable = "mdstattabs"
        env.workspace = newDB


        # Establishes a cursor for searching through field rows. A search cursor can be used to retrieve rows.
        # This method will return an enumeration object that will, in turn, hand out row objects
        if arcpy.Exists(os.path.join(newDB, theMDTable)):

            fldNames = ["tabphyname","tablabel","iefilename"]
            with arcpy.da.SearchCursor(os.path.join(newDB, theMDTable), fldNames) as rows:

                for row in rows:
                    # read each table record and assign 'tabphyname' and 'tablabel' to 2 variables
                    physicalName = row[0]
                    aliasName = row[1]
                    importFileName = row[2]

                    # i.e. {chaashto:'Horizon AASHTO',chaashto}; will create a one-to-many dictionary
                    # As long as the physical name doesn't exist in dict() add physical name
                    # as Key and alias as Value.
                    #if not physicalName in tblAliases:
                    if not importFileName in tblInfo:
                        #PrintMsg("\t" + importFileName + ": " + physicalName, 1)
                        tblInfo[importFileName] = physicalName, aliasName

            del theMDTable

            return tblInfo

        else:
            # The mdstattabs table was not found
            raise MyError, "Missing mdstattabs table"
            return tblInfo


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return dict()

## ===================================================================================
def UpdateMukeys(outputWS):
    # For preliminary spatial data or for NASIS-SSURGO downloads,
    # the mukeys may be missing or may not match the attribute tables
    # Using the mapunit and legend tables from the new geodatabase,
    # populate the mukeys in the new Mupolygon featureclass.
    
    try:
        PrintMsg(" \n\tUpdating mukeys in output soil polygon featureclass", 0)
        mapunitTbl = os.path.join(outputWS, "mapunit")
        legendTbl = os.path.join(outputWS, "legend")
        newMupolygon = os.path.join(outputWS, "mupolygon")
        areasymList = list()

        dLegend = dict() # key = lkey, value = areasymbol
        dMapunit = dict()    # key = musym, value = mukey

        with arcpy.da.SearchCursor(legendTbl, ["lkey", "areasymbol"]) as cur:
            
            for rec in cur:
                if not rec[0] in dLegend:
                    dLegend[rec[0]] = rec[1]
                    areasymList.append(rec[1].encode('ascii'))

        with arcpy.da.SearchCursor(mapunitTbl, ["lkey", "musym", "mukey"]) as cur:
                            
            for rec in cur:
                lkey, musym, mukey = rec
                areasym = dLegend[lkey]
                newkey = areasym + ":" + musym
                
                if not newkey in dMapunit:
                    dMapunit[newkey] = mukey

        # Do I need a whereclause to kickout records with missing areasymbol or musym,
        # or should I just keep a list of bad records and report them?
        if len(areasymList) == 0:
            wc = ""

        elif len(areasymList) == 1:
            wc = "areasymbol = '" + areasymList[0] + "'"

        else:
            wc = "areasymbol IN " + str(tuple(areasymList))

        missingMapunits = list()
                                    
        with arcpy.da.UpdateCursor(newMupolygon, ["areasymbol", "musym", "mukey"], where_clause=wc) as cur:
            for rec in cur:
                areasym, musym, mukey = rec
                newkey = str(areasym) + ":" + str(musym)
                try:
                    mukey = dMapunit[newkey]
                    rec[2] = mukey
                    #PrintMsg("\t" + str(rec), 1)
                    cur.updateRow(rec)

                except:
                    if not newkey in missingMapunits:
                        missingMapunits.append(newkey)


        if len(missingMapunits) > 0:
            PrintMsg(" \n\tFailed to find tabular match for the following map units:  " + ", ".join(missingMapunits), 1)
                            
        return missingMapunits
    
    except MyError, e:
        PrintMsg(str(e), 2)
        return missingMapunits

    except:
        errorMsg()
        return missingMapunits
    
## ===================================================================================
def AppendFeatures(outputWS, AOI, mupolyList, mulineList, mupointList, sflineList, sfpointList, sapolyList, featCnt):
    # Merge all spatial layers into a set of file geodatabase featureclasses
    # Compare shapefile feature count to GDB feature count
    # featCnt:  0 mupoly, 1 muline, 2 mupoint, 3 sfline, 4 sfpoint, 5 sapoly
    #
    # Not being used right now for the NASIS-SSURGO Export process
    
    try:
        # Set output workspace
        env.workspace = outputWS

        # Put datum transformation methods in place
        #AOI = "CONUS"
        PrintMsg(" \nImporting spatial data...", 0)

        # Problem if soil polygon shapefile has MUNAME column or other alterations
        # Need to use fieldmapping parameter to fix append error.
        fieldmappings = arcpy.FieldMappings()
        fieldmappings.addTable(os.path.join(outputWS, "MUPOLYGON"))
        fieldmappings.addTable(os.path.join(outputWS, "MULINE"))
        fieldmappings.addTable(os.path.join(outputWS, "MUPOINT"))
        fieldmappings.addTable(os.path.join(outputWS, "FEATLINE"))
        fieldmappings.addTable(os.path.join(outputWS, "FEATPOINT"))
        fieldmappings.addTable(os.path.join(outputWS, "SAPOLYGON"))

        # Assuming input featureclasses from Web Soil Survey are GCS WGS1984 and that
        # output datum is either NAD 1983 or WGS 1984. Output coordinate system will be
        # defined by the existing output featureclass.

        # WITH XML workspace method, I need to use Append_management

        # Merge process MUPOLYGON
        if len(mupolyList) > 0:
            PrintMsg(" \n\tAppending " + str(len(mupolyList)) + " soil mapunit polygon shapefiles to create new featureclass: " + "MUPOLYGON", 0)
            arcpy.SetProgressorLabel("Appending features to MUPOLYGON layer")
            arcpy.Append_management(mupolyList,  os.path.join(outputWS, "MUPOLYGON"), "NO_TEST", fieldmappings )
            mupolyCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "MUPOLYGON")).getOutput(0))

            if mupolyCnt != featCnt[0]:
                raise MyError, "MUPOLYGON short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "MUPOLYGON"))

            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUKEY", "Indx_MupolyMukey")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUSYM", "Indx_MupolyMusym")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "AREASYMBOL", "Indx_MupolyAreasymbol")

        #PrintMsg(" \nSkipping import for other featureclasses until problem with shapefile primary key is fixed", 0)
        #return True

        # Merge process MULINE
        if len(mulineList) > 0:
            PrintMsg(" \n\tAppending " + str(len(mulineList)) + " soil mapunit line shapefiles to create new featureclass: " + "MULINE", 0)
            arcpy.SetProgressorLabel("Appending features to MULINE layer")
            arcpy.Append_management(mulineList,  os.path.join(outputWS, "MULINE"), "NO_TEST", fieldmappings)
            mulineCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "MULINE")).getOutput(0))

            if mulineCnt != featCnt[1]:
                raise MyError, "MULINE short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "MULINE"))

            # Add attribute indexes
            arcpy.AddIndex_management(os.path.join(outputWS, "MULINE"), "MUKEY", "Indx_MulineMukey")
            arcpy.AddIndex_management(os.path.join(outputWS, "MULINE"), "MUSYM", "Indx_MulineMusym")
            arcpy.AddIndex_management(os.path.join(outputWS, "MULINE"), "AREASYMBOL", "Indx_MulineAreasymbol")

        # Merge process MUPOINT
        if len(mupointList) > 0:
            PrintMsg(" \n\tAppending " + str(len(mupointList)) + " soil mapunit point shapefiles to create new featureclass: " + "MUPOINT", 0)
            arcpy.SetProgressorLabel("Appending features to MUPOINT layer")
            arcpy.Append_management(mupointList,  os.path.join(outputWS, "MUPOINT"), "NO_TEST", fieldmappings)
            mupointCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "MUPOINT")).getOutput(0))

            if mupointCnt != featCnt[2]:
                raise MyError, "MUPOINT short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "MUPOINT"))

            # Add attribute indexes
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOINT"), "MUKEY", "Indx_MupointMukey")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOINT"), "MUSYM", "Indx_MupointMusym")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOINT"), "AREASYMBOL", "Indx_MupointAreasymbol")

        # Merge process FEATLINE
        if len(sflineList) > 0:
            PrintMsg(" \n\tAppending " + str(len(sflineList)) + " special feature line shapefiles to create new featureclass: " + "FEATLINE", 0)
            arcpy.SetProgressorLabel("Appending features to FEATLINE layer")
            arcpy.Append_management(sflineList,  os.path.join(outputWS, "FEATLINE"), "NO_TEST", fieldmappings)
            sflineCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "FEATLINE")).getOutput(0))

            if sflineCnt != featCnt[3]:
                raise MyError, "FEATLINE short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "FEATLINE"))

            # Add attribute indexes
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATLINE"), "FEATKEY", "Indx_SFLineFeatkey")
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATLINE"), "FEATSYM", "Indx_SFLineFeatsym")
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATLINE"), "AREASYMBOL", "Indx_SFLineAreasymbol")

        # Merge process FEATPOINT
        if len(sfpointList) > 0:
            PrintMsg(" \n\tAppending " + str(len(sfpointList)) + " special feature point shapefiles to create new featureclass: " + "FEATPOINT", 0)
            arcpy.SetProgressorLabel("Appending features to FEATPOINT layer")
            arcpy.Append_management(sfpointList,  os.path.join(outputWS, "FEATPOINT"), "NO_TEST", fieldmappings)
            sfpointCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "FEATPOINT")).getOutput(0))

            if sfpointCnt != featCnt[4]:
                PrintMsg(" \nWA619 SF Points had 3136 in the original shapefile", 1)
                PrintMsg("featCnt is " + str(featCnt[4]), 1)
                PrintMsg(" \nExported " + str(sfpointCnt) + " points to geodatabase", 1)
                raise MyError, "FEATPOINT short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "FEATPOINT"))

            # Add attribute indexes
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATPOINT"), "FEATKEY", "Indx_SFPointFeatkey")
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATPOINT"), "FEATSYM", "Indx_SFPointFeatsym")
            arcpy.AddIndex_management(os.path.join(outputWS, "FEATPOINT"), "AREASYMBOL", "Indx_SFPointAreasymbol")

        # Merge process SAPOLYGON
        if len(sapolyList) > 0:
            PrintMsg(" \n\tAppending " + str(len(sapolyList)) + " survey boundary shapefiles to create new featureclass: " + "SAPOLYGON", 0)
            arcpy.SetProgressorLabel("Appending features to SAPOLYGON layer")
            arcpy.Append_management(sapolyList,  os.path.join(outputWS, "SAPOLYGON"), "NO_TEST", fieldmappings)
            sapolyCnt = int(arcpy.GetCount_management(os.path.join(outputWS, "SAPOLYGON")).getOutput(0))

            if sapolyCnt != featCnt[5]:
                raise MyError, "SAPOLYGON short count"

            # Add spatial index
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "SAPOLYGON"))

            # Add attribute indexes
            arcpy.AddIndex_management(os.path.join(outputWS, "SAPOLYGON"), "LKEY", "Indx_SapolyLKey")
            arcpy.AddIndex_management(os.path.join(outputWS, "SAPOLYGON"), "AREASYMBOL", "Indx_SapolyAreasymbol")

        arcpy.RefreshCatalog(outputWS)

        if not arcpy.Exists(outputWS):
            raise MyError, outputWS + " not found at end of AppendFeatures..."

        return True

    except MyError, e:
        PrintMsg(str(e), 2)

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
def GetXML(AOI):
    # Set appropriate XML Workspace Document according to AOI
    # The xml files referenced in this function must all be stored in the same folder as the
    # Python script and toolbox
    #
    # FY2016. Discovered that my MD* tables in the XML workspace documents were out of date.
    # Need to update and figure out a way to keep them updated
    #
    try:
        # Set folder path for workspace document (same as script)
        xmlPath = os.path.dirname(sys.argv[0])

        # Changed datum transformation to use ITRF00 for ArcGIS 10.1
        # FYI. Multiple geographicTransformations would require a semi-colon delimited string
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        # Input XML workspace document used to create new gSSURGO schema in an empty geodatabase
        if AOI == "Lower 48 States":
            inputXML = os.path.join(xmlPath, "gSSURGO_CONUS_AlbersNAD1983.xml")
            tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        elif AOI == "Hawaii":
            inputXML = os.path.join(xmlPath, "gSSURGO_Hawaii_AlbersWGS1984.xml")
            tm = ""

        elif AOI == "American Samoa":
            inputXML = os.path.join(xmlPath, "gSSURGO_Hawaii_AlbersWGS1984.xml")
            tm = ""

        elif AOI == "Alaska":
            inputXML = os.path.join(xmlPath, "gSSURGO_Alaska_AlbersWGS1984.xml")
            tm = ""

        elif AOI == "Puerto Rico and U.S. Virgin Islands":
            inputXML = os.path.join(xmlPath, "gSSURGO_CONUS_AlbersNAD1983.xml")
            tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        elif AOI == "Pacific Islands Area":
            inputXML = os.path.join(xmlPath, "gSSURGO_PACBasin_AlbersWGS1984.xml")
            # No datum transformation required for PAC Basin data
            tm = ""

        elif AOI == "World":
            PrintMsg(" \nOutput coordinate system will be Geographic WGS 1984", 0)
            inputXML = os.path.join(xmlPath, "gSSURGO_Geographic_WGS1984.xml")
            tm = ""

        else:
            PrintMsg(" \nNo projection is being applied", 1)
            inputXML = os.path.join(xmlPath, "gSSURGO_GCS_WGS1984.xml")
            tm = ""

        arcpy.env.geographicTransformations = tm

        return inputXML

    except:
        errorMsg()
        return ""

## ===================================================================================
def UpdateMetadata(outputWS, target, surveyInfo, description, remove_gp_history_xslt):
    #
    # Used for featureclass and geodatabase metadata. Does not do individual tables
    # Reads and edits the original metadata object and then exports the edited version
    # back to the featureclass or database.
    #
    try:
        if outputWS == target:
            # Updating the geodatabase metadata
            #target = outputWS
            PrintMsg("\tGeodatabase", 0)

        else:
            # Updating featureclass metadata
            target = os.path.join(outputWS, target)
            PrintMsg("\t" + os.path.basename(target.title()), 0)

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        #prod = r"Metadata/Translator/ArcGIS2ISO19139.xml"
        mdTranslator = os.path.join(installPath, prod)

        if not arcpy.Exists(mdTranslator):
            raise MyError, "Missing metadata translator file (" + mdTranslator + ")"

        # Define input and output XML files
        mdExport = os.path.join(env.scratchFolder, "xxExport.xml")  # initial metadata exported from current MUPOLYGON featureclass
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info

        # Cleanup XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        if os.path.isfile(mdExport):
            os.remove(mdExport)

        #PrintMsg(" \nExporting metadata from " + target, 1)
        #PrintMsg("Current workspace is " + env.workspace, 1)
        
        arcpy.ExportMetadata_conversion (target, mdTranslator, mdExport)

        if outputWS == target:
            arcpy.ExportMetadata_conversion (target, mdTranslator, os.path.join(env.scratchFolder, "xxGDBExport.xml"))

        # Get replacement value for the search words
        #
        stDict = StateNames()
        st = os.path.basename(outputWS)[8:-4]

        if st in stDict:
            # Get state name from the geodatabase
            mdState = stDict[st]

        else:
            # Use description as state name
            #mdState = st
            mdState = description

        # Set date strings for metadata, based upon today's date
        #
        d = datetime.date.today()
        #today = str(d.isoformat().replace("-",""))

        lastDate = GetLastDate(outputWS)

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)


        # Parse exported XML metadata file
        #
        # Convert XML to tree format
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
                #PrintMsg("\t\t" + str(child.tag), 0)
                if child.tag == "title":
                    if child.text.find('xxSTATExx') >= 0:
                        child.text = child.text.replace('xxSTATExx', mdState)

                    elif mdState != "":
                        child.text = child.text + " - " + mdState

                elif child.tag == "edition":
                    if child.text == 'xxFYxx':
                        child.text = fy

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            subchild.text = fy

        # Update place keywords
        #PrintMsg("\t\tplace keywords", 0)
        ePlace = root.find('idinfo/keywords/place')

        for child in ePlace.iter('placekey'):
            if child.text == "xxSTATExx":
                child.text = mdState

            elif child.text == "xxSURVEYSxx":
                child.text = surveyInfo

        # Update credits
        eIdInfo = root.find('idinfo')
        #PrintMsg("\t\tcredits", 0)

        for child in eIdInfo.iter('datacred'):
            sCreds = child.text

            if sCreds.find("xxSTATExx") >= 0:
                #PrintMsg("\t\tcredits " + mdState, 0)
                child.text = child.text.replace("xxSTATExx", mdState)

            if sCreds.find("xxFYxx") >= 0:
                #PrintMsg("\t\tcredits " + fy, 0)
                child.text = child.text.replace("xxFYxx", fy)

            if sCreds.find("xxTODAYxx") >= 0:
                #PrintMsg("\t\tcredits " + today, 0)
                child.text = child.text.replace("xxTODAYxx", lastDate)

        idPurpose = root.find('idinfo/descript/purpose')
        if not idPurpose is None:
            ip = idPurpose.text
            #PrintMsg("\tip: " + ip, 1)
            if ip.find("xxFYxx") >= 0:
                #PrintMsg("\t\tip", 1)
                idPurpose.text = ip.replace("xxFYxx", fy)

        procDates = root.find('dataqual/lineage')
        if not procDates is None:
            #PrintMsg(" \nUpdating process step dates", 1)
            for child in procDates.iter('procdate'):

                sDate = child.text
                #PrintMsg("\tFound process date: " + sDate, 1)
                if sDate.find('xxTODAYxx'):
                    #PrintMsg("\tReplacing process date: " + sDate + " with " + lastDate, 1)
                    child.text = lastDate

        else:
            PrintMsg("\nNo find process date", 1)


        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")

        # Clear geoprocessing history from the target metadata
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        arcpy.XSLTransform_conversion(target, remove_gp_history_xslt, out_xml, "")
        arcpy.MetadataImporter_conversion(out_xml, target)

        # delete the temporary xml metadata files
        if os.path.isfile(mdImport):
            os.remove(mdImport)
            #pass

        if os.path.isfile(mdExport):
            os.remove(mdExport)
            pass
            #PrintMsg(" \nKeeping temporary medatafiles: " + mdExport, 1)
            #time.sleep(5)

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        return True

    except:
        errorMsg()
        False

## ===================================================================================
def UpdateMetadata_ISO(outputWS, target, surveyInfo, description):
    # Adapted from MapunitRaster metadata function
    #
    # old function args: outputWS, target, surveyInfo, description
    #
    # Update and import the ISO 19139 metadata for the Map Unit Raster layer
    # Since the raster layer is created from scratch rather than from an
    # XML Workspace Document, the metadata must be imported from an XML metadata
    # file named 'gSSURGO_MapunitRaster.xml
    # Search nodevalues and replace keywords: xxSTATExx, xxSURVEYSxx, xxTODAYxx, xxFYxx
    #
    # Note: for existing featureclasses, this function would have to be modified to first
    # export their metadata to a temporary xml file, updated and saved to a new, temporary
    # xml file and then imported back to the featureclass.
    #
    try:
        #import xml.etree.cElementTree as ET
        PrintMsg("\t" + os.path.basename(target), 0)

        # Identify the raster template metadata file stored with the Python scripts
        #xmlPath = os.path.dirname(sys.argv[0])

        inputXML = os.path.join(env.scratchFolder, "xxOldMetadata.xml")       # original metadata from target
        midXML = os.path.join(env.scratchFolder, "xxMidMetadata.xml")         # intermediate xml
        outputXML = os.path.join(env.scratchFolder, "xxUpdatedMetadata.xml")  # updated metadata xml
        #inputXML = os.path.join(env.scratchFolder, "in_" + os.path.basename(target).replace(".", "") + ".xml")
        #outputXML = os.path.join(env.scratchFolder, "out_" + os.path.basename(target).replace(".", "") + ".xml")

        # Export original metadata from target
        #
        # Set ISO metadata translator file
        # C:\Program Files (x86)\ArcGIS\Desktop10.1\Metadata\Translator\ARCGIS2ISO19139.xml
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        #prod = r"Metadata/Translator/ARCGIS2ISO19139.xml"
        #prod = r"Metadata/Translator/ESRI_ISO2ISO19139.xml"
        prod = r"Metadata/Translator/ISO19139_2ESRI_ISO.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Cleanup XML files from previous runs
        if os.path.isfile(inputXML):
            os.remove(inputXML)

        if os.path.isfile(midXML):
            os.remove(midXML)

        if os.path.isfile(outputXML):
            os.remove(outputXML)

        # initial metadata export is not ISO
        arcpy.ExportMetadata_conversion (target, mdTranslator, inputXML)

        # second export creates ISO metatadata
        prod = r"Metadata/Translator/ESRI_ISO2ISO19139.xml"
        mdTranslator = os.path.join(installPath, prod)
        #arcpy.ExportMetadata_conversion (target, mdTranslator, midXML)
        arcpy.ESRITranslator_conversion(inputXML, mdTranslator, midXML)


        # Try to get the statename by parsing the gSSURGO geodatabase name.
        # If the standard naming convention was not followed, the results
        # will be unpredictable
        #
        stDict = StateNames()
        st = os.path.basename(outputWS)[8:-4]

        if st in stDict:
            mdState = stDict[st]

        else:
            mdState = description

        #mdTitle = "Map Unit Raster " + str(iRaster) + "m - " + mdState

        # Set date strings for metadata, based upon today's date
        #
        d = datetime.date.today()
        today = str(d.isoformat().replace("-",""))

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        # Begin parsing input xml file
        doc = minidom.parse(midXML)

        # TITLE
        nodeValue = 'title'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if not node.firstChild is None:
                            if node.firstChild.nodeValue.find("xxSTATExx") >= 0:
                                PrintMsg("\t\tFound " + nodeValue + ": " + node.firstChild.nodeValue, 1)
                                #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                                title = node.firstChild.nodeValue.replace("xxSTATExx", mdState)
                                node.firstChild.nodeValue = title
                                PrintMsg("\t\t" + node.firstChild.nodeValue)

        # KEYWORDS
        nodeValue = 'keyword'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxSTATExx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = mdState
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

                        elif node.firstChild.nodeValue.find("xxSURVEYSxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = surveyInfo
                            PrintMsg("\t\t" + node.firstChild.nodeValue)


        # DATETIME
        nodeValue = 'dateTime'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "DateTime":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound datetime.DateTime: " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today + "T00:00:00"
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # DATESTAMP
        nodeValue = 'dateStamp'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "Date":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # DATE
        nodeValue = 'date'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "Date":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # CREDITS
        nodeValue = 'credit'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\tCredit: " + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            newCredit = node.firstChild.nodeValue
                            newCredit = newCredit.replace("xxTODAYxx", today).replace("xxFYxx", fy)
                            node.firstChild.nodeValue = newCredit
                            PrintMsg("\t\t" + node.firstChild.nodeValue)
                            #PrintMsg("\tEdited: " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 0)

        # FISCAL YEAR
        nodeValue = 'edition'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxFYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = fy
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # ISSUE IDENTIFICATION
        nodeValue = 'issueIdentification'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxFYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = fy
                            PrintMsg("\t\t" + node.firstChild.nodeValue)


        # Begin writing new metadata to a temporary xml file which can be imported back to ArcGIS
        newdoc = doc.toxml("utf-8")
        # PrintMsg(" \n" + newdoc + " \n ", 1)

        fh = open(outputXML, "w")
        fh.write(newdoc)
        fh.close()

        # import updated metadata to the geodatabase table
        #PrintMsg("\tSkipping metatdata import \n ", 1)
        #arcpy.ImportMetadata_conversion(outputXML, "FROM_ISO_19139", outputRaster, "DISABLED")
        arcpy.MetadataImporter_conversion (outputXML, target)

        # delete the temporary xml metadata files
        #os.remove(outputXML)
        #os.remove(inputXML)
        #if os.path.isfile(midXML):
        #    os.remove(midXML)


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)

    except:
        errorMsg()

## ===================================================================================
def gSSURGO(outputWS, dsmRasterLayer, dsmDB, outputRaster):
    # main function

    try:
        # Creating the file geodatabase uses the ImportXMLWorkspaceDocument command which requires
        #
        # ArcInfo: Advanced license
        # ArcEditor: Standard license
        # ArcView: Basic license
        # licenseLevel = arcpy.ProductInfo().upper()
        # if licenseLevel == "BASIC":
        #    raise MyError, "ArcGIS License level must be Standard or Advanced to run this tool"
        env.overwriteOutput = True
        codePage = 'iso-8859-1'  # allow csv reader to handle non-ascii characters
        

        # According to Gary Spivak, SDM downloads are UTF-8 and NAIS downloads are iso-8859-1
        # cp1252 also seemed to work well
        #codePage = 'utf-16' this did not work
        #
        # http://stackoverflow.com/questions/6539881/python-converting-from-iso-8859-1-latin1-to-utf-8
        # Next need to try: string.decode('iso-8859-1').encode('utf8')

        dbVersion = 2  # This is the SSURGO version supported by this script and the gSSURGO schema (XML Workspace document)

        # Make sure that the env.scratchGDB is NOT Default.gdb. This can cause problems for
        # some unknown reason.
        if SetScratch() == False:
            raise MyError, "Invalid scratch workspace setting (" + env.scratchWorkspace + ")"

        #PrintMsg(" \nAlias and description: " + aliasName + "; " +  description, 1)

        # Get the XML Workspace Document appropriate for the specified AOI
        # inputXML = GetXML(AOI)

        #if inputXML == "":
        #    raise MyError, "Unable to set input XML Workspace Document"

        # if len(tabularFolders) > 0:  # This originally was the iteration through areasymbolList
        # Create file geodatabase for output data
        # Remove any dashes in the geodatabase name. They will cause the
        # raster conversion to fail for some reason.
        gdbName = os.path.basename(outputWS)
        outFolder = os.path.dirname(outputWS)
        gdbName = gdbName.replace("-", "_")
        outputWS = os.path.join(outFolder, gdbName)
        
        bMD = ImportMDTables(outputWS, dsmDB)  # seems to cause problems with duplicate records when
        # we import md tables from the RSS database

        if bMD == False:
            raise MyError, ""

        # import attribute data from text files in tabular folder
        bTabular = ImportTables(outputWS, dsmDB)


        if bTabular == True:
            # Successfully imported all tabular data (textfiles or Access database tables)
            PrintMsg(" \nAll tabular data imported", 0)

        else:
            PrintMsg("Failed to export all tabular data", 2)
            return False

        # Query the output SACATALOG table to get list of surveys that were exported to the gSSURGO
        #
        saTbl = os.path.join(outputWS, "sacatalog")
        expList = list()
        areasymList = list()

        with arcpy.da.SearchCursor(saTbl, ["AREASYMBOL", "SAVEREST"]) as srcCursor:
            for rec in srcCursor:
                expList.append(rec[0] + " (" + str(rec[1]).split()[0] + ")")
                areasymList.append(rec[0].encode('ascii'))
            
        expInfo = ", ".join(expList) # This is a list of areasymbol with saverest for metadata


        # Get a list of RSS mukeys
        #
        muTbl = os.path.join(dsmDB, "mapunit")
        newMukeys = list()
        wc = "musym <> 'NOTCOM'"
        
        with arcpy.da.SearchCursor(muTbl, ["MUKEY"], where_clause=wc) as muCursor:
            for rec in muCursor:
                newMukeys.append(rec[0].encode('ascii'))

        inputRaster = os.path.join(outputWS, "MuRaster")

        bMerged = MergeData(outputWS, dsmRasterLayer, outputRaster, newMukeys)


        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return True

## ===================================================================================
def SortSurveyAreaLayer(ssaLayer, surveyList):
    # For the 'Create gSSURGO DB by Map' sort the polygons by extent and use that to regenerate the surveyList
    #
    try:
        # first reformat the surveyList (soil_areasymbol.lower())
        newSurveyList = list()
        areasymList = [s[5:].upper() for s in surveyList]
        sortedSSA = os.path.join(env.scratchGDB, "sortedSSA")
        desc = arcpy.Describe(ssaLayer)
        shapeField = desc.featureclass.shapeFieldName
        arcpy.Sort_management(ssaLayer, sortedSSA, shapeField, "UR")
        #PrintMsg(" \nareasymList: " + str(areasymList), 1)

        if arcpy.Exists(sortedSSA):
            with arcpy.da.SearchCursor(sortedSSA, "areasymbol", ) as cur:
                for rec in cur:
                    areaSym = rec[0].encode('ascii')
                    #PrintMsg(areaSym, 1)
                    
                    if areaSym in areasymList and not areaSym in newSurveyList:
                        newSurveyList.append(areaSym)

        else:
            raise MyError, "Failed to produce spatial sort on survey areas"

        #PrintMsg(" \nnewSurveyList: " + str(newSurveyList), 1)
                
        return newSurveyList
                                         

    except MyError, e:
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def FindField(theInput, chkField, bVerbose = False):
    # Check table or featureclass to see if specified field exists
    # If fully qualified name is found, return that
    # Set workspace before calling FindField
    try:
        if arcpy.Exists(theInput):
            theDesc = arcpy.Describe(theInput)
            theFields = theDesc.Fields
            #theField = theFields.next()
            # Get the number of tokens in the fieldnames
            #theNameList = arcpy.ParseFieldName(theField.Name)
            #theCnt = len(theNameList.split(",")) - 1

            for theField in theFields:
                theNameList = arcpy.ParseFieldName(theField.Name)
                theCnt = len(theNameList.split(",")) - 1
                theFieldname = theNameList.split(",")[theCnt].strip()

                if theFieldname.upper() == chkField.upper():
                    return theField.Name

                #theField = theFields.next()

            if bVerbose:
                PrintMsg("Failed to find column " + chkField + " in " + theInput, 2)

            return ""

        else:
            PrintMsg("\tInput layer not found", 0)
            return ""

    except:
        errorMsg()
        return ""

## ===============================================================================================================
def CreateTableRelationships(wksp):
    # Create relationship classes between standalone attribute tables.
    # Relate parameters are pulled from the mdstatrhipdet and mdstatrshipmas tables,
    # thus it is required that the tables must have been copied from the template database.

    try:

        PrintMsg(" \nCreating table relationships and indexes on key fields...", 0)
        env.workspace = wksp
        
        if arcpy.Exists(os.path.join(wksp, "mdstatrshipdet")) and arcpy.Exists(os.path.join(wksp, "mdstatrshipmas")):

            # Create new Table View to contain results of join between relationship metadata tables

            tbl1 = os.path.join(wksp, "mdstatrshipmas")
            tbl2 = os.path.join("mdstatrshipdet")
            tblList = [tbl1, tbl2]
            queryTableName = "TblRelationships"

            sql = "mdstatrshipdet.ltabphyname = mdstatrshipmas.ltabphyname AND mdstatrshipdet.rtabphyname = mdstatrshipmas.rtabphyname AND mdstatrshipdet.relationshipname = mdstatrshipmas.relationshipname"
            fldList = [["mdstatrshipmas.ltabphyname","LTABPHYNAME"],["mdstatrshipmas.rtabphyname", "RTABPHYNAME"],["mdstatrshipdet.relationshipname", "RELATIONSHIPNAME"], ["mdstatrshipdet.ltabcolphyname", "LTABCOLPHYNAME"],["mdstatrshipdet.rtabcolphyname",  "RTABCOLPHYNAME"]]
            arcpy.MakeQueryTable_management (tblList, queryTableName, "ADD_VIRTUAL_KEY_FIELD", "", fldList, sql)

            if not arcpy.Exists(queryTableName):
                raise MyError, "Failed to create metadata table required for creation of relationshipclasses"

            tblCnt = int(arcpy.GetCount_management(queryTableName).getOutput(0))
            tblCnt += 7  # Add featureclasses to the count
            #PrintMsg(" \nQuery table has " + str(tblCnt) + " records", 1)

            # Fields in the new table view
            # OBJECTID, LTABPHYNAME, RTABPHYNAME, RELATIONSHIPNAME, LTABCOLPHYNAME, RTABCOLPHYNAME, CARDINALITY
            # Open table view, step through each record to retrieve relationshipclass parameters and use that to create the relationshipclass
            arcpy.SetProgressor("step", "Creating table relationships...", 1, tblCnt, 1)
            
            with arcpy.da.SearchCursor(queryTableName, ["mdstatrshipmas_ltabphyname", "mdstatrshipmas_rtabphyname", "mdstatrshipdet_ltabcolphyname", "mdstatrshipdet_rtabcolphyname"]) as theCursor:

                for rec in theCursor:
                    # Get relationshipclass parameters from current table row
                    # Syntax for CreateRelationshipClass_management (origin_table, destination_table, 
                    # out_relationship_class, relationship_type, forward_label, backward_label, 
                    # message_direction, cardinality, attributed, origin_primary_key, 
                    # origin_foreign_key, destination_primary_key, destination_foreign_key)
                    #
                    originTable, destinationTable, originPKey, originFKey = rec
                    originAlias = arcpy.Describe(originTable).aliasName + " Table"
                    destinationAlias = arcpy.Describe(destinationTable).aliasName + " Table"
                    originTablePath = os.path.join(wksp, originTable)
                    destinationTablePath = os.path.join(wksp, destinationTable)

                    # Use table aliases for relationship labels
                    relName = "z" + originTable.title() + "_" + destinationTable.title()

                    # create Forward Label e.g. "> Horizon AASHTO Table"
                    fwdLabel = "> " + destinationAlias

                    # create Backward Label e.g. "< Horizon Table"
                    backLabel = "< " + originAlias
                    arcpy.SetProgressorPosition()

                    if arcpy.Exists(originTablePath) and arcpy.Exists(destinationTablePath):
                        #PrintMsg("\tCreating relationship for " + originTable + " and " + destinationTable, 1)
                        #if FindField(originTablePath, originPKey) and FindField(wksp + os.sep + destinationTablePath, originFKey):
                        arcpy.CreateRelationshipClass_management(originTablePath, destinationTablePath, relName, "SIMPLE", fwdLabel, backLabel, "NONE", "ONE_TO_MANY", "NONE", originPKey, originFKey, "","")


        else:
            raise MyError, "Missing one or more of the metadata tables"

        # Establish Relationship between tables and Spatial layers
        #PrintMsg(" \nCreating Relationships between Featureclasses and Tables:", 1)
        #arcpy.SetProgressor("step", "Creating featureclass relationships...", 1, 6, 1)

        # Relationship between MUPOLYGON --> Mapunit Table            
        arcpy.CreateRelationshipClass_management(os.path.join(wksp,"MUPOLYGON"), os.path.join(wksp, "mapunit"), os.path.join(wksp, "zMUPOLYGON_Mapunit"), "SIMPLE", "> Mapunit Table", "< MUPOLYGON", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Mapunit", 1)
        arcpy.SetProgressorPosition()

        # Relationship between MUPOLYGON --> Mapunit Aggregate Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "MUPOLYGON"), os.path.join(wksp, "muaggatt"), os.path.join(wksp, "zMUPOLYGON_Muaggatt"), "SIMPLE", "> Muaggatt Table", "< MUPOLYGON", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "muaggatt" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Muaggatt", 1)
        arcpy.SetProgressorPosition()

        # Relationship between SAPOLYGON --> Legend Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "SAPOLYGON"), os.path.join(wksp, "legend"), os.path.join(wksp, "zSAPOLYGON_Legend"), "SIMPLE", "> Legend Table", "< SAPOLYGON", "NONE","ONE_TO_MANY", "NONE","LKEY","lkey", "","")
        #AddMsgAndPrint("\t" + ssaFC + formatTabLength1 + "legend" + "             --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SAPOLYGON_Legend", 1)
        arcpy.SetProgressorPosition()

        # Relationship between MULINE --> Mapunit Table          
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "MULINE"), os.path.join(wksp, "mapunit"), os.path.join(wksp, "zMULINE_Mapunit"), "SIMPLE", "> Mapunit Table", "< MULINE", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsmuLineFC + "         --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MULINE_Mapunit", 1)
        arcpy.SetProgressorPosition()

        # Relationship between MUPOINT --> Mapunit Table            
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "MUPOINT"), os.path.join(wksp, "mapunit"), os.path.join(wksp, "zMUPOINT_Mapunit"), "SIMPLE", "> Mapunit Table", "< MUPOINT", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsmuPointFC + "        --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOINT_Mapunit", 1)
        arcpy.SetProgressorPosition()

        # Relationship between FEATLINE --> Featdesc Table            
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "FEATLINE"), os.path.join(wksp, "featdesc"), os.path.join(wksp, "zFEATLINE_Featdesc"), "SIMPLE", "> Featdesc Table", "< FEATLINE", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
        #AddMsgAndPrint("\t" + specLineFC + "       --> featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SPECLINE_Featdesc", 1)
        arcpy.SetProgressorPosition()

        # Relationship between FEATPOINT --> Featdesc Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "FEATPOINT"), os.path.join(wksp, "featdesc"), os.path.join(wksp, "zFEATPOINT_Featdesc"), "SIMPLE", "> Featdesc Table", "< FEATPOINT", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
        #AddMsgAndPrint("\t" + specPointFC + formatTabLength1 + "featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SPECPOINT_Featdesc", 1)
        arcpy.SetProgressorPosition()

        #PrintMsg("\nSuccessfully Created featureclass and table relationships", 1)
        arcpy.ResetProgressor()
        arcpy.Delete_management(queryTableName)
        return True


    except:
        errorMsg()
        return False

## ===================================================================================
def GetFCType(fc):
    # Determine featureclass type  featuretype and table fields
    # Rename featureclasses from old shapefile-based name to new, shorter name
    # Returns new featureclass name using DSS convention for geodatabase
    #
    # The check for table fields is the absolute minimum

    featureType = ""

    # Look for minimum list of required fields
    #
    if FindField(fc, "MUSYM"):
        hasMusym = True

    else:
        hasMusym = False

    if FindField(fc, "LKEY"):
        hasLkey = True

    else:
        hasLkey = False

    if FindField(fc, "FEATSYM"):
        hasFeatsym = True

    else:
        hasFeatsym = False

    try:
        fcName = os.path.basename(fc)
        theDescription = arcpy.Describe(fc)
        featType = theDescription.ShapeType

        # Mapunit Features
        if hasMusym:
            if featType == "Polygon" and fcName.upper() != "MUPOINT":
                dataType = "Mapunit Polygon"

            elif featType == "Polyline":
                dataType = "Mapunit Line"

            elif featType == "Point" or featType == "Multipoint" or fcName.upper() == "MUPOINT":
                dataType = "Mapunit Point"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an MUSYM field (GetFCName)", 2)
                featureType = ""

        # Survey Area Boundary
        if hasLkey:
            if featType == "Polygon":
                dataType = "Survey Boundary"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an LKEY field (GetFCName)", 2)
                dataType = ""

        # Special Features
        if hasFeatsym:
            # Special Feature Line
            if featType == "Polyline":
                dataType = "Special Feature Line"

            # Special Feature Point
            elif featType == "Point" or featType == "Multipoint":
                dataType = "Special Feature Point"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an FEATSYM field (GetFCName)", 2)
                dataType = ""

        return dataType

    except:
        errorMsg()
        return ""
    
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time, datetime, csv
from operator import itemgetter, attrgetter
import xml.etree.cElementTree as ET
#from xml.dom import minidom
from arcpy import env
from arcpy.sa import *

try:
    if __name__ == "__main__":

        # New tool parameters
        # 0 NASIS Export Folder (where unzipped tabular text files are stored) Only one of the first two parameters is needed.
        # 1 NASIS Download URL  (URL from NASIS e-mail)
        # 2 Soil Polygon Layer  (Soil Polygon layer that will be married to the NASIS tabular data)
        # 3 Output geodatabase  (Output file geodatabase that will contain the matching spatial and attribute data)
        # 4 Geographic Region   (Determines output coordinate system)

        outputWS = arcpy.GetParameterAsText(0)            #  Existing output geodatabase (gSSURGO-gSTATSGO)
        outputRaster = arcpy.GetParameterAsText(1)        #  gNATSGO Raster
        dsmRaster = arcpy.GetParameterAsText(2)           #  RSS raster Layer (if raster dataset, switch to layer)
        #dsmDB = arcpy.GetParameterAsText(2)            #  NASIS Export Folder


        # Need to get dsmDB from dsmRaster
        # Need to create dsmRasterLayer

        dsmDesc = arcpy.Describe(dsmRaster)
        dsmPath = dsmDesc.catalogPath
        dsmDataType = dsmDesc.dataType.upper()
        dsmDB = os.path.dirname(dsmPath)                  # assume that dsmRaster is in a geodatabase

        if not dsmDB.endswith(".gdb"):
            raise MyError, "Input RSS raster must belong to a file geodatabase"

        if dsmDataType == "RASTERDATASET":
            wc = "musym <> 'NOTCOM'"
            dsmRasterLayer = "Raster Layer"
            arcpy.MakeRasterLayer_management(dsmPath, dsmRasterLayer, wc)

        else:
            dsmRasterLayer = dsmRaster
            wc = "musym <> 'NOTCOM'"
            arcpy.SelectLayerByAttribute_management(dsmRasterLayer, "NEW_SELECTION", wc)

        outputDesc = arcpy.Describe(outputRaster)
        outputPath = outputDesc.catalogPath
        outputDataType = outputDesc.dataType.upper()

        if outputDataType != "RASTERDATASET":
            outputRaster = outputPath
                                         
        # Original gSSURGO function bGood = gSSURGO(inputFolder, surveyList, outputWS, AOI, aliasName, useTextFiles, False, areasymbolList)
        # Assuming soil polygon featureclass is "MUPOLYGON" in outputWS
        bGood = gSSURGO(outputWS, dsmRasterLayer, dsmDB, outputRaster)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
