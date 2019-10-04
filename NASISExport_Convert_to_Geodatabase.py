# NASISExport_Convert_to_Geodatabase.py
#
# ArcGIS 10.3 - 10.5.1
#
# Steve Peaslee, National Soil Survey Center, Lincoln, Nebraska
#
# Purpose: Using a NASIS-SSURGO Export or WSS-SSURGO Download and a soil polygon featureclass with
# matching AREASYMBOL and MUSYM values, create a gSSURGO-type geodatabase for QA purposes. Also
# works with STATSGO.
# Differs from other tools in that the user has to point to the folder where the tabular text
# files are stored. Does not require the standard folder and shapefile naming conventions. This
# puts the onus on the user to make sure that the tabular and spatial data match.
#
# New functionality I want to add. 2018-09-14. Automatically search for and import any shapefiles included in the
# zip file (Staging Server download). Make note of which surveys had Staging Server spatial and then only
# import the Rest of the spatial from the other user-provided source.
#
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
                    tblName = rec[0]
                    
                    if not tblName.startswith('mdstat') and not tblName in ('mupolygon', 'muline', 'mupoint', 'featline', 'featpoint', 'sapolygon'):
                        tblList.append(rec[0])

        #PrintMsg(" \nTables to import: " + ", ".join(tblList), 0)
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
def ImportMDTables(newDB, dbList):
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

        accessDB = dbList[0] # source database for metadata table data

        # Process list of text files
        # 
        for table in tables:
            arcpy.SetProgressorLabel("Importing " + table + "...")
            inTbl = os.path.join(accessDB, table)
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

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ImportMDTabular(newDB, tabularFolder, codePage):
    # Import a single set of metadata text files from first survey area's tabular
    # These files contain table information, relationship classes and domain values
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
    #codePage = 'cp1252'

    try:
        #PrintMsg(" \nImporting metadata tables from " + tabularFolder, 1)

        # Create list of text files to be imported
        txtFiles = ['mstabcol', 'msrsdet', 'mstab', 'msrsmas', 'msdommas', 'msidxmas', 'msidxdet',  'msdomdet']

        # Create dictionary containing text filename as key, table physical name as value
        tblInfo = {u'mstabcol': u'mdstattabcols', u'msrsdet': u'mdstatrshipdet', u'mstab': u'mdstattabs', u'msrsmas': u'mdstatrshipmas', u'msdommas': u'mdstatdommas', u'msidxmas': u'mdstatidxmas', u'msidxdet': u'mdstatidxdet', u'msdomdet': u'mdstatdomdet'}

        csv.field_size_limit(128000)

        # Process list of text files
        for txtFile in txtFiles:

            # Get table name and alias from dictionary
            if txtFile in tblInfo:
                tbl = tblInfo[txtFile]

            else:
                raise MyError, "Required input textfile '" + txtFile + "' not found in " + tabularFolder

            arcpy.SetProgressorLabel("Importing " + tbl + "...")

            # Full path to SSURGO text file
            
            txtPath = os.path.join(tabularFolder, txtFile + ".txt")

            # continue import process only if the target table exists

            if arcpy.Exists(tbl):
                # Create cursor for all fields to populate the current table
                #
                # For a geodatabase, I need to remove OBJECTID from the fields list
                fldList = arcpy.Describe(tbl).fields
                fldNames = list()
                fldLengths = list()

                for fld in fldList:
                    if fld.type != "OID":
                        fldNames.append(fld.name)

                        if fld.type.lower() == "string":
                            fldLengths.append(fld.length)

                        else:
                            fldLengths.append(0)

                if len(fldNames) == 0:
                    raise MyError, "Failed to get field names for " + tbl

                with arcpy.da.InsertCursor(os.path.join(newDB, tbl), fldNames) as cursor:
                    # counter for current record number
                    iRows = 1  # input textfile line number

                    if os.path.isfile(txtPath):

                        # Use csv reader to read each line in the text file
                        #for rowInFile in csv.reader(open(txtPath, 'rb'), delimiter='|'):
                        for rowInFile in csv.reader(open(txtPath, 'r'), delimiter='|'):
                            # , quotechar="'"
                            # replace all blank values with 'None' so that the values are properly inserted
                            # into integer values otherwise insertRow fails
                            # truncate all string values that will not fit in the target field
                            newRow = list()
                            fldNo = 0
                            fixedRow = [x.decode(codePage) for x in rowInFile]  # handle non-utf8 characters
                            #.decode('iso-8859-1').encode('utf8')
                            #fixedRow = [x.decode('iso-8859-1').encode('utf8') for x in rowInFile]
                            #fixedRow = [x.decode('iso-8859-1') for x in rowInFile]

                            for val in fixedRow:  # mdstatdomdet was having problems with this 'for' loop. No idea why.
                                fldLen = fldLengths[fldNo]

                                if val == '':
                                    val = None

                                elif fldLen > 0:
                                    val = val[0:fldLen]

                                newRow.append(val)

                                fldNo += 1

                            try:
                                cursor.insertRow(newRow)

                            except:
                                raise MyError, "Error handling line " + Number_Format(iRows, 0, True) + " of " + txtPath

                            iRows += 1

                        if iRows < 63:
                            # msrmas.txt has the least number of records
                            raise MyError, tbl + " has only " + str(iRows) + " records. Check 'md*.txt' files in tabular folder"

                    else:
                        raise MyError, "Missing tabular data file (" + txtPath + ")"

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
def ImportTabular(newDB, tabularFolder, dbVersion, codePage, tblList, zipFileName):
    # Use csv reader method of importing text files into geodatabase for those
    # that do not have a populated SSURGO database
    #
    # 2015-12-16 Need to eliminate duplicate records in sdv* tables. Also need to index primary keys
    # for each of these tables.
    #
    try:
        # new code from ImportTables
        # codePage = 'cp1252'



        #iCntr = 0

        # Set up enforcement of unique keys for SDV tables
        #
        sdvTables = ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']
        dIndex = dict()  # dictionary storing field index for primary key of each SDV table
        dKeys = dict()  # dictionary containing a list of key values for each SDV table
        dFields = dict() # dictionary containing list of fields for eacha SDV table

        keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"

        for sdvTbl in sdvTables:
            #sdvTbl = os.path.join(outputWS, "sdvfolderattribute")
            #indx = keyIndx[sdvTbl]
            keyField = keyFields[sdvTbl]

            fldList = arcpy.Describe(os.path.join(newDB, sdvTbl)).fields
            fldNames = list()

            for fld in fldList:
                if fld.type != "OID":
                    fldNames.append(fld.name.lower())

            dFields[sdvTbl] = fldNames                 # store list of fields for this SDV table
            dIndex[sdvTbl] = fldNames.index(keyField)  # store field index for primary key in this SDV table
            dKeys[sdvTbl] = []                         # initialize key values list for this SDV table




        
        # Add SDV* table relationships. These aren't part of the XML workspace doc as of FY2018 gSSURGO
        # Not normally necessary, but useful for diagnostics
        arcpy.CreateRelationshipClass_management(os.path.join(newDB, "sdvattribute"), os.path.join(newDB, "sdvfolderattribute"), "zSdvattribute_Sdvfolderattribute", "SIMPLE", "> SDV Folder Attribute Table", "<  SDV Attribute Table", "NONE", "ONE_TO_MANY", "NONE", "attributekey", "attributekey", "","")
        arcpy.CreateRelationshipClass_management(os.path.join(newDB, "sdvfolder"), os.path.join(newDB, "sdvfolderattribute"), "zSdvfolder_Sdvfolderattribute", "SIMPLE", "> SDV Folder Attribute Table", "<  SDV Folder Table", "NONE", "ONE_TO_MANY", "NONE", "folderkey", "folderkey", "","")
        # End of enforce unique keys setup...

        # move to tabular folder
        env.workspace = tabularFolder

        # if the tabular directory is empty return False
        if len(os.listdir(tabularFolder)) < 1:
            raise MyError, "No text files found in the " + inputDB + " folder"

        # Make sure that input tabular data has the correct SSURGO version for this script
        ssurgoVersion = SSURGOVersionTxt(tabularFolder)

        if ssurgoVersion <> dbVersion:
            raise MyError, "Tabular data in " + tabularFolder + " (SSURGO Version " + str(ssurgoVersion) + ") is not supported"

        # Create a dictionary with table information
        tblInfo = GetTableInfo(newDB)

        # Create a list of textfiles to be imported. The import process MUST follow the
        # order in this list in order to maintain referential integrity. This list
        # will need to be updated if the SSURGO data model is changed in the future.
        #
        txtFiles = ["distmd","legend","distimd","distlmd","lareao","ltext","mapunit", \
        "comp","muaggatt","muareao","mucrpyd","mutext","chorizon","ccancov","ccrpyd", \
        "cdfeat","cecoclas","ceplants","cerosnac","cfprod","cgeomord","chydcrit", \
        "cinterp","cmonth", "cpmatgrp", "cpwndbrk","crstrcts","csfrags","ctxfmmin", \
        "ctxmoicl","ctext","ctreestm","ctxfmoth","chaashto","chconsis","chdsuffx", \
        "chfrags","chpores","chstrgrp","chtext","chtexgrp","chunifie","cfprodo","cpmat","csmoist", \
        "cstemp","csmorgc","csmorhpp","csmormr","csmorss","chstr","chtextur", \
        "chtexmod","sacatlog","sainterp","sdvalgorithm","sdvattribute","sdvfolder","sdvfolderattribute"]
        # Need to add featdesc import as a separate item (ie. spatial\soilsf_t_al001.txt: featdesc)

        # Static Metadata Table that records the metadata for all columns of all tables
        # that make up the tabular data set.
        mdstattabsTable = os.path.join(env.workspace, "mdstattabs")

        # set progressor object which allows progress information to be passed for every merge complete
        #arcpy.SetProgressor("step", "Importing " +  fnAreasymbol + " tabular  (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(dbList), 0, True) + ")" , 0, len(txtFiles) + 1, 1)

        #csv.field_size_limit(sys.maxsize)
        csv.field_size_limit(512000)

        # Need to import text files in a specific order or the MS Access database will
        # return an error due to table relationships and key violations
        for txtFile in txtFiles:

            # Get table name and alias from dictionary
            if txtFile in tblInfo:
                tbl, aliasName = tblInfo[txtFile]

            else:
                raise MyError, "Textfile reference '" + txtFile + "' not found in 'mdstattabs table'"

            #arcpy.SetProgressorLabel("Importing tabular data from " + tabularFolder + " (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(tabularFolders), 0, True) + ") :   " + tbl)

            # Full path to SSURGO text file
            txtPath = os.path.join(tabularFolder, txtFile + ".txt")

            # continue if the target table exists
            if arcpy.Exists(tbl):
                # Create cursor for all fields to populate the current table
                #
                # For a geodatabase, I need to remove OBJECTID from the fields list
                fldList = arcpy.Describe(tbl).fields
                fldNames = list()
                #fldLengths = list()

                for fld in fldList:
                    if fld.type != "OID":
                        fldNames.append(fld.name)

                if len(fldNames) == 0:
                    raise MyError, "Failed to get field names for " + tbl

                if not tbl in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
                    # Import all tables except SDV
                    #
                    arcpy.SetProgressorLabel("Importing " + zipFileName + ": " + tbl)
                    
                    with arcpy.da.InsertCursor(os.path.join(newDB, tbl), fldNames) as cursor:
                        # counter for current record number
                        iRows = 1  # input textfile line number

                        #if os.path.isfile(txtPath):
                        if arcpy.Exists(txtPath):

                            try:
                                # Use csv reader to read each line in the text file
                                time.sleep(0.5)  # trying to prevent error reading text file

                                for rowInFile in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                                    # replace all blank values with 'None' so that the values are properly inserted
                                    # into integer values otherwise insertRow fails
                                    fixedRow = [x.decode(codePage) if x else None for x in rowInFile]  # handle non-utf8 characters
                                    cursor.insertRow(fixedRow) # was fixedRow
                                    iRows += 1

                            except:
                                err = "Error writing line " + Number_Format(iRows, 0, True) + " of " + txtPath
                                #PrintMsg(err, 1)
                                #errorMsg()
                                raise MyError, err

                        else:
                            raise MyError, "Missing tabular data file (" + txtPath + ")"

                else:
                    # Import SDV tables while enforcing unique key constraints
                    # 'sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm'
                    #
                    with arcpy.da.InsertCursor(os.path.join(newDB, tbl), fldNames) as cursor:
                        # counter for current record number
                        iRows = 1

                        if os.path.isfile(txtPath):

                            try:
                                # Use csv reader to read each line in the text file
                                time.sleep(0.5)  # trying to prevent error reading text file
                                
                                for rowInFile in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                                    newRow = list()
                                    fldNo = 0
                                    keyVal = int(rowInFile[dIndex[tbl]])

                                    if not keyVal in dKeys[tbl]:
                                        # write new record to SDV table
                                        dKeys[tbl].append(keyVal)
                                        newRow = [x if x else None for x in rowInFile]
                                        cursor.insertRow(newRow)  # was newRow
                                    iRows += 1

                            except:
                                err = "Error importing line " + Number_Format(iRows, 0, True) + " from " + txtPath + " \n " + str(newRow)
                                PrintMsg(err, 1)
                                errorMsg()
                                raise MyError, "Error writing line " + Number_Format(iRows, 0, True) + " of " + txtPath

                        else:
                            raise MyError, "Missing tabular data file (" + txtPath + ")"

                # Check table count
                # This isn't correct. May need to look at accumulating total table count in a dictionary
                #if int(arcpy.GetCount_management(os.path.join(newDB, tbl)).getOutput(0)) != iRows:
                #    raise MyError, tbl + ": Failed to import all " + Number_Format(iRows, 0, True) + " records into "

            else:
                raise MyError, "Required table '" + tbl + "' not found in " + newDB


        # Populate the month table (pre-populated in the Access Template database, no text file)
        #
        monthList = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        monthTbl = os.path.join(newDB, "month")
        
        if int(arcpy.GetCount_management(monthTbl).getOutput(0)) < 12:
            #arcpy.SetProgressorLabel("Importing " +  fnAreasymbol + " tabular  (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(tabularFolders), 0, True) + ") :   " + monthTbl)
            
            with arcpy.da.InsertCursor(monthTbl, ["monthseq", "monthname"]) as cur:
                for seq, month in enumerate(monthList):
                    rec = [(seq + 1), month]
                    cur.insertRow(rec)
        
        # Import feature description file. Does this file exist in a NASIS-SSURGO download?
        # soilsf_t_al001.txt
        txtPath = "xxxx"

        if arcpy.Exists(txtPath):
            # For a geodatabase, I need to remove OBJECTID from the fields list
            fldList = arcpy.Describe(tbl).fields
            fldNames = list()
            for fld in fldList:
                if fld.type != "OID":
                    fldNames.append(fld.name)

            if len(fldNames) == 0:
                raise MyError, "Failed to get field names for " + tbl

            # Create cursor for all fields to populate the featdesc table
            with arcpy.da.InsertCursor(tbl, fldNames) as cursor:
                # counter for current record number
                iRows = 1
                #arcpy.SetProgressorLabel("Importing " +  fnAreasymbol + "  (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(dbList), 0, True) + "):   " + tbl)

                try:
                    # Use csv reader to read each line in the text file
                    for rowInFile in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                        # replace all blank values with 'None' so that the values are properly inserted
                        # into integer values otherwise insertRow fails
                        newRow = [None if value == '' else value for value in rowInFile]
                        cursor.insertRow(newRow)
                        iRows += 1

                except:
                    errorMsg()
                    raise MyError, "Error loading line no. " + Number_Format(iRows, 0, True) + " of " + txtFile + ".txt"

            #arcpy.SetProgressorPosition()  # for featdesc table
            time.sleep(1.0)


        # Set the Progressor to show completed status
        #arcpy.SetProgressorPosition()

        time.sleep(1)
        arcpy.ResetProgressor()

        # Check mapunit and sdvattribute tables. Get rid of certain records if there is no data available.
        # iacornsr IS NOT NULL OR nhiforsoigrp IS NOT NULL OR vtsepticsyscl IS NOT NULL

        # 'Soil-Based Residential Wastewater Disposal Ratings (VT)'  [vtsepticsyscl]

        # 'Iowa Corn Suitability Rating CSR2 (IA)'   [iacornsr]

        # 'NH Forest Soil Group'  [nhiforsoigrp]

        bCorn = False
        bNHFor = False
        bVTSeptic = False
        wc = "iacornsr IS NOT NULL"
        with arcpy.da.SearchCursor(os.path.join(newDB, "mapunit"), ["OID@"], where_clause=wc) as cur:
            for rec in cur:
                bCorn = True
                break

        wc = "vtsepticsyscl IS NOT NULL"
        with arcpy.da.SearchCursor(os.path.join(newDB, "mapunit"), ["OID@"], where_clause=wc) as cur:
            for rec in cur:
                bVTSeptic = True
                break

        wc = "nhiforsoigrp IS NOT NULL"
        with arcpy.da.SearchCursor(os.path.join(newDB, "mapunit"), ["OID@"], where_clause=wc) as cur:
            for rec in cur:
                bNHFor = True
                break

        if not bCorn:
            # Next open cursor on the sdvattribute table and delete any unneccessary records
            wc = "attributecolumnname = 'iacornsr'"
            with arcpy.da.UpdateCursor(os.path.join(newDB, "sdvattribute"), ["attributecolumnname"], where_clause=wc) as cur:
                for rec in cur:
                    #PrintMsg("\tDeleted row for iacornsr", 1)
                    cur.deleteRow()

        if not bVTSeptic:
            # Next open cursor on the sdvattribute table and delete any unneccessary records
            wc = "attributecolumnname = 'vtsepticsyscl'"
            with arcpy.da.UpdateCursor(os.path.join(newDB, "sdvattribute"), ["attributecolumnname"], where_clause=wc) as cur:
                for rec in cur:
                    #PrintMsg("\tDeleted row for VT septic", 1)
                    cur.deleteRow()                

        if not bNHFor:
            # Next open cursor on the sdvattribute table and delete any unneccessary records
            wc = "attributecolumnname = 'nhiforsoigrp'"
            with arcpy.da.UpdateCursor(os.path.join(newDB, "sdvattribute"), ["attributecolumnname"], where_clause=wc) as cur:
                for rec in cur:
                    #PrintMsg("\tDeleted row for NH forest group", 1)
                    cur.deleteRow()

        arcpy.SetProgressorLabel("Tabular import complete for " + zipFileName)
        time.sleep(1)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False


## ===================================================================================
def AddTableIndexes(newDB):
    # Add attribute indexes for sdv tables

    try:
        # Set up enforcement of unique keys for SDV tables
        #
        sdvTables = ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']
        dIndex = dict()  # dictionary storing field index for primary key of each SDV table
        dKeys = dict()  # dictionary containing a list of key values for each SDV table
        dFields = dict() # dictionary containing list of fields for eacha SDV table

        keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"

        for sdvTbl in sdvTables:
            #sdvTbl = os.path.join(outputWS, "sdvfolderattribute")
            #indx = keyIndx[sdvTbl]
            keyField = keyFields[sdvTbl]

            fldList = arcpy.Describe(os.path.join(newDB, sdvTbl)).fields
            fldNames = list()

            for fld in fldList:
                if fld.type != "OID":
                    fldNames.append(fld.name.lower())

            dFields[sdvTbl] = fldNames                 # store list of fields for this SDV table
            dIndex[sdvTbl] = fldNames.index(keyField)  # store field index for primary key in this SDV table
            dKeys[sdvTbl] = []                         # initialize key values list for this SDV table


        
        for tblName in sdvTables:
            sdvTbl = os.path.join(newDB, tblName)
            indexName = "Indx_" + tblName
            arcpy.SetProgressorLabel("Adding attribute index (" + indexName + ") for " + tblName)
            arcpy.AddIndex_management(sdvTbl, keyFields[tblName], indexName)
            
        # Add additional attribute indexes for cointerp table.
        # According to documentation, a file geodatabase does not use multi-column indexes
        arcpy.SetProgressorLabel("Adding attribute index for cointerp table")

        try:
            indxName = "Indx_CointerpRulekey"
            indxList = arcpy.ListIndexes(os.path.join(newDB, "cointerp"), indxName)
            
            if len(indxList) == 0: 
                arcpy.SetProgressorLabel("\tAdding attribute index on rulekey for cointerp table")
                # Tried to add this Cointerp index to the XML workspace document, but slowed down data import.
                arcpy.AddIndex_management(os.path.join(newDB, "COINTERP"), "RULEKEY", indxName)
                #arcpy.SetProgressorPosition()

        except:
            errorMsg()
            PrintMsg(" \nUnable to create new index on the cointerp table", 1)
            
        arcpy.SetProgressorLabel("Tabular import complete")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetSoilPolygons(outputWS, AOI, soilPolygons, featCnt, bValidation, bUpdateMukeys, areasymList, tmpFolder):
    # outputWS, AOI, soilPolygons, featCnt
    # Merge all spatial layers into a set of file geodatabase featureclasses
    # Compare shapefile feature count to GDB feature count
    # featCnt:  0 mupoly, 1 muline, 2 mupoint, 3 sfline, 4 sfpoint, 5 sapoly
    #
    # Not being used right now for the NASIS-SSURGO Export process
    
    try:
        missingMapunits = list()
        # Set output workspace
        env.workspace = outputWS

        # Put datum transformation methods in place
        #AOI = "CONUS"
        PrintMsg(" \nImporting spatial data for " + Number_Format(len(areasymList), 0, True) + " survey areas...", 0)

        #PrintMsg(" \nsoilPolygons variable = " + str(soilPolygons), 1)
        #raise MyError, "EARLY OUT"

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

        # See if there are any shapefiles from Staging Server present in the tmpTabular folder.
        # If there are, Append those first and remove the associated areasymbol from the where_clause.
        PrintMsg(" \nChecking folder " + tmpFolder + " to see if there are any shapefiles that need to be appended", 1)
        env.workspace = tmpFolder
        muShpFiles = list()
        saShpFiles = list()
        muType = list()

        for areasym in areasymList:
            muShp = os.path.join(tmpFolder, areasym.upper() + "_a.shp")
            saShp = os.path.join(tmpFolder, areasym.upper() + "_b.shp")
            
            if arcpy.Exists(muShp):
                muShpFiles.append(muShp)
                areasymList.remove(areasym)

            if arcpy.Exists(saShp):
                saShpFiles.append(saShp)


        if len(areasymList) == 0:
            wc = ""

        elif len(areasymList) == 1:
            wc = "areasymbol = '" + areasymList[0] + "'"

        else:
            wc = "areasymbol IN " + str(tuple(areasymList))

                        
        if len(areasymList) > 0:
            if  soilPolygons != "":
                PrintMsg(" \n\tAppending matching soil mapunit polygons from layer '" + soilPolygons + "'", 0)
                arcpy.SetProgressorLabel("Appending features to MUPOLYGON layer")
                #PrintMsg(" \nAreasymbol query: " + wc, 1)
                env.workspace = outputWS

                muDesc = arcpy.Describe(soilPolygons)
                muType = muDesc.dataType
                soilLayer = "InputSoils"
                arcpy.MakeFeatureLayer_management(soilPolygons, soilLayer, wc)

                selCnt = int(arcpy.GetCount_management(soilLayer).getOutput(0))
                missingMapunits = list()

                if selCnt == 0:
                    raise MyError, "Failed to find matching survey areas (by areasymbol) in " + soilPolygons + " layer"

                muShpFiles.append(soilLayer)

            else:
                muType = ""


        #elif 


        if len(muShpFiles) > 0:
            PrintMsg(" \nAppending muShpFiles: " + ", ".join(muShpFiles) + "...", 1)
            
            arcpy.Append_management(muShpFiles,  os.path.join(outputWS, "MUPOLYGON"), "NO_TEST", fieldmappings )
            
            if len(areasymList) > 0:
                arcpy.Delete_management(soilLayer)

            if bUpdateMukeys:
                # Using draft soil polygon layer that has missing or out-of-date mukeys
                missingMapunits = UpdateMukeys(outputWS)


            #
            # Try to get survey boundaries as well
            saFC = None
            
            if muType == "FeatureLayer":
                # get datapath for source
                muPath = muDesc.catalogPath
                # get source type
                sourceType = arcpy.Describe(muPath).dataType

                if sourceType == "ShapeFile":
                    # now look for soilsa_a*.shp
                    saShp = muPath.replace("soilmu_a", "soilsa_a")

                    if arcpy.Exists(saShp):
                        saFC = saShp

                    else:
                        saFC = None 

                elif sourceType == "FeatureClass":
                    # now look for SAPOLYGON in geodatabase or featuredataset
                    sourcePath = os.path.dirname(muPath)

                    if arcpy.Exists(os.path.join(sourcePath, "SAPOLYGON")):
                        saFC = os.path.join(sourcePath, "SAPOLYGON")


                    else:
                        saFC = None

            elif muType == "FeatureClass":
                # now look for SAPOLYGON in geodatabase or featuredataset
                sourcePath = os.path.dirname(soilPolygons)

                if arcpy.Exists(os.path.join(sourcePath, "SAPOLYGON")):
                    saFC = os.path.join(sourcePath, "SAPOLYGON")

                else:
                    saFC = None
                        
            if not saFC is None:
                
                saLayer = "SurveyBoundaries"
                arcpy.MakeFeatureLayer_management(saFC, saLayer, wc)
                selCnt = int(arcpy.GetCount_management(saLayer).getOutput(0))

                saShpFiles.append(saLayer)

                if selCnt > 0:
                    PrintMsg(" \n\tUpdating survey boundaries with " + Number_Format(selCnt, 0, True) + " polygons...", 0)
                    arcpy.Append_management([saLayer],  os.path.join(outputWS, "SAPOLYGON"), "NO_TEST", fieldmappings )
                    arcpy.Delete_management(saLayer)

                else:
                    PrintMsg(" \n\tFailed to select survey boundaries from " + saFC + " using query: ", 1)
                    PrintMsg(wc, 1)


            if len(saShpFiles) > 0:
                PrintMsg(" \n\tAppending matching survey boundary polygons...", 0)
                arcpy.SetProgressorLabel("Appending features to SAPOLYGON layer")
                arcpy.Append_management(saShpFiles,  os.path.join(outputWS, "SAPOLYGON"), "NO_TEST", fieldmappings )
                
           
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

            # Add spatial index
            arcpy.SetProgressorLabel("Adding spatial indexes...")
            arcpy.AddSpatialIndex_management (os.path.join(outputWS, "MUPOLYGON"))
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUKEY", "Indx_MupolyMukey")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "MUSYM", "Indx_MupolyMusym")
            arcpy.AddIndex_management(os.path.join(outputWS, "MUPOLYGON"), "AREASYMBOL", "Indx_MupolyAreasymbol")
            arcpy.RefreshCatalog(outputWS)

        return missingMapunits

    except MyError, e:
        PrintMsg(str(e), 1)
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

        legendTbl = os.path.join(outputWS, "legend")
        #areasymList = list()
        dLegend = dict() # key = lkey, value = areasymbol

        with arcpy.da.SearchCursor(legendTbl, ["lkey", "areasymbol"]) as cur:
            
            for rec in cur:
                if not rec[0] in dLegend:
                    dLegend[rec[0]] = rec[1]
                    #areasymList.append(rec[1].encode('ascii'))
                    
        mapunitTbl = os.path.join(outputWS, "mapunit")
        mupolygonTbl = os.path.join(outputWS, "mupolygon")
        dMapunitInfo = dict()
        mapunitList = list()
        mupolygonList = list()

        with arcpy.da.SearchCursor(mapunitTbl, ["mukey", "musym", "muname", "lkey"]) as cur:
            # should generate a unique list of mukeys
            for rec in cur:
                mukey, musym, muname, lkey = rec
                mapunitList.append(mukey.encode('ascii'))
                areasym = dLegend[lkey]
                # PrintMsg("\tMissing spatial mapunit for " + mukey + " | " + musym + " | " + muname, 1)
                dMapunitInfo[mukey.encode('ascii')] = [musym, muname, areasym]

        with arcpy.da.SearchCursor(mupolygonTbl, ["mukey"]) as cur:
            # should generate a non-unique list of mukeys
            for rec in cur:
                if not rec[0] is None:
                    mupolygonList.append(rec[0].encode('ascii'))
                    

        mupolygonList = list(set(mupolygonList)) # now make this list unique
                                   
        missingMupolygon = set(mapunitList) - set(mupolygonList)
        missingMapunit = set(mupolygonList) - set(mapunitList)
        

        if len(missingMupolygon) > 0:
            PrintMsg(" \n\tSoil polygon layer has " + Number_Format(len(missingMupolygon), 0, True) + " mapunit(s) with no match to the NASIS export", 0)

            for mukey in missingMupolygon:
                musym, muname, areasym = dMapunitInfo[mukey]
                PrintMsg("\t\tNo match for spatial mapunit: " + areasym + " | " + mukey + " | " + musym + " | " + muname, 1)

                
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

        with arcpy.da.SearchCursor(mapunitTbl, ["lkey", "musym", "mukey", "muname"]) as cur:
                            
            for rec in cur:
                lkey, musym, mukey, muname = rec
                areasym = dLegend[lkey]
                newkey = areasym + ":" + musym
                
                if not newkey in dMapunit:
                    dMapunit[newkey] = [mukey, muname]

        # Do I need a whereclause to kickout records with missing areasymbol or musym,
        # or should I just keep a list of bad records and report them?
        if len(areasymList) == 0:
            wc = ""

        elif len(areasymList) == 1:
            wc = "areasymbol = '" + areasymList[0] + "'"

        else:
            wc = "areasymbol IN " + str(tuple(areasymList))

        missingMapunits = list()  # This will be a list of mukeys not 
                                    
        with arcpy.da.UpdateCursor(newMupolygon, ["areasymbol", "musym", "mukey"], where_clause=wc) as cur:
            # Reading each mupolygon record and updating the mukey
            #
            for rec in cur:
                areasym, musym, mukey = rec
                newkey = str(areasym) + ":" + str(musym)
                
                try:
                    mukey, muname = dMapunit[newkey]  # find areasymbol:musym from mapunit table
                    rec[2] = mukey
                    #PrintMsg("\t" + str(rec), 1)
                    cur.updateRow(rec)

                except KeyError:
                    if not newkey in missingMapunits:
                        PrintMsg("\t\tNo match for tabular mapunit:  " + str(areasym) + " | " + str(musym) + " | " + str(muname), 1)
                        missingMapunits.append(newkey)  # add this areasymbol:musym to the list of mapunits that exist in spatial but not in NASIS export

                except:
                    errorMsg()


        #if len(missingMapunits) > 0:
        #    PrintMsg(" \n\tFailed to find tabular match for the following map units:  " + ", ".join(missingMapunits), 1)
                            
        return missingMapunits  # list of mapunits that exist in spatial but not in NASIS export
    
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
def UpdateMetadata(outputWS, target, surveyInfo, remove_gp_history_xslt, dateRange):
    #
    # Used for featureclass and geodatabase metadata. Does not do individual tables
    # Reads and edits the original metadata object and then exports the edited version
    # back to the featureclass or database.

    # Need to substitute for xxSTATExx, xxSURVEYsxx, xxFYxx, xxTODAYxx
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

        # Clear geoprocessing history from the target metadata
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        arcpy.XSLTransform_conversion(target, remove_gp_history_xslt, out_xml, "")  # out_xml is the clean metadata
        arcpy.MetadataImporter_conversion(out_xml, target)

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
        
        arcpy.ExportMetadata_conversion(target, mdTranslator, mdExport)

        if outputWS == target:
            arcpy.ExportMetadata_conversion (target, mdTranslator, os.path.join(env.scratchFolder, "xxGDBExport.xml"))

        # Get replacement value for the search words
        #

        mdState = "NASIS-SSURGO Export"

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
                        
                        if outputWS == target:
                            # geodatabase title
                            child.text = "gSSURGO from NASIS-SSURGO Export"

                        else:
                            child.text = child.text.replace('xxSTATExx', mdState)

                    elif mdState != "":
                        child.text = child.text + " - " + mdState

                elif child.tag == "edition":
                    if child.text == 'xxFYxx':
                        child.text = dateRange

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            subchild.text = dateRange

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
                child.text = child.text.replace("xxFYxx", dateRange)

            if sCreds.find("xxTODAYxx") >= 0:
                #PrintMsg("\t\tcredits " + today, 0)
                child.text = child.text.replace("xxTODAYxx", d.isoformat())

        idPurpose = root.find('idinfo/descript/purpose')
        if not idPurpose is None:
            ip = idPurpose.text
            #PrintMsg("\tip: " + ip, 1)
            if ip.find("xxFYxx") >= 0:
                #PrintMsg("\t\tip", 1)
                idPurpose.text = ip.replace("xxFYxx", dateRange)

        procDates = root.find('dataqual/lineage')
        if not procDates is None:
            #PrintMsg(" \nUpdating process step dates", 1)
            for child in procDates.iter('procdate'):

                sDate = child.text
                #PrintMsg("\tFound process date: " + sDate, 1)
                if sDate.find('xxTODAYxx'):
                    #PrintMsg("\tReplacing process date: " + sDate + " with " + lastDate, 1)
                    child.text = d.isoformat()

        else:
            PrintMsg("\nNo find process date", 1)


        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")

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
def gSSURGO(zipFolder, zipFileNames, soilPolygons, outputWS, AOI, bValidation, bMukeys):
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
        # codePage = 'utf-16' this did not work
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
        inputXML = GetXML(AOI)

        if inputXML == "":
            raise MyError, "Unable to set input XML Workspace Document"

        if len(zipFileNames) > 0:  
            # Create file geodatabase for output data
            # Remove any dashes in the geodatabase name. They will cause the
            # raster conversion to fail for some reason.
            gdbName = os.path.basename(outputWS)
            outFolder = os.path.dirname(outputWS)
            gdbName = gdbName.replace("-", "_")
            outputWS = os.path.join(outFolder, gdbName)
            tmpFolder = os.path.join(env.scratchFolder, "xxTabular")
            
            bGeodatabase = CreateSSURGO_DB(outputWS, inputXML, "", "")

            arcpy.CreateFolder_management(os.path.dirname(tmpFolder), os.path.basename(tmpFolder))


            if bGeodatabase:

                pCntr = 0
                arcpy.SetProgressor("step", "Importing tabular data...",  0, len(zipFileNames), 1)
                PrintMsg(" \nImporting tabular data from NASIS-SSURGO exports...", 0)

                for zipFileName in zipFileNames:
                    # Unzip tabular data to a temporary folder and then append tabular data to the file geodatabase
                    #
                    #PrintMsg(" \ntabularFolders: " + str(tabularFolders), 1)

                    pCntr += 1
                    local_zip = os.path.join(zipFolder, zipFileName)

                    if not arcpy.Exists(local_zip):
                        raise MyError, "Missing zip file " + local_zip

                    zipfile.ZipFile.debug = 3

                    if os.path.isfile(local_zip):
                        # got a zip file, go ahead and extract it

                        zipSize = (os.stat(local_zip).st_size / (1024.0 * 1024.0))

                        if zipSize > 0:
                            
                            arcpy.SetProgressorLabel("Unzipping " + zipFileName + " (" + Number_Format(zipSize, 3, True) + " MB) to " + tmpFolder + "...")

                            try:
                                z = zipfile.ZipFile(local_zip, "r")
                                z.extractall(tmpFolder)
                                z.close()

                            except zipfile.BadZipfile:
                                PrintMsg("Bad zip file?", 2)
                                return False

                            except:
                                PrintMsg(" \nUnhandled error unzipping " + local_zip, 2)
                                return False

                        else:
                            # Downloaded a zero-byte zip file
                            # download for this survey failed, may try again
                            PrintMsg("\tEmpty zip file downloaded for " + areaSym + ": " + surveyName, 1)
                            os.remove(local_zip)


                    #   
                    if pCntr == 1:
                        # Import metadata tables from first NASIS export. This may not work. Check these tables.
                        bMD = ImportMDTabular(outputWS, tmpFolder, codePage)  # new, import md tables from text files of last survey area

                        if bMD == False:
                            raise MyError, ""

                        tblList = GetTableList(outputWS)

                        if len(tblList) == 0:
                            raise MyError, "No tables found in " +  outputWS


                    # import attribute data from the freshly unzipped text files in tabular folder
                    bTabular = ImportTabular(outputWS, tmpFolder, dbVersion, codePage, tblList, zipFileName)

                    if bTabular == True:
                        # Successfully imported all tabular data (textfiles or Access database tables)
                        

                        # Make sure that the sdv* tables have all the downloaded interps listed
                        # If any are missing, add them to the sdv* tables
                        dInterps = IdentifyNewInterps(outputWS)

                    else:
                        PrintMsg("Failed to export all data to gSSURGO. Tabular export error.", 2)
                        return False


                    arcpy.SetProgressorPosition()

                # After importing all tabular data, add indexes
                PrintMsg(" \nAll tabular data imported", 0)
                bIndexed = AddTableIndexes(outputWS)    

            else:
                # Problem creating gSSURGO database
                return False

            # Query the output SACATALOG table to get list of surveys that were exported to the gSSURGO db
            #
            saTbl = os.path.join(outputWS, "sacatalog")
            #expList = list()
            areasymList = list()

            with arcpy.da.SearchCursor(saTbl, ["AREASYMBOL", "SAVEREST"]) as srcCursor:
                for rec in srcCursor:
                    #expList.append(rec[0] + " (" + str(rec[1]).split()[0] + ")")
                    areasymList.append(rec[0].encode('ascii'))

            expInfo = ", ".join(areasymList) # This is a list of areasymbol with saverest for metadata
                
            #expInfo = ", ".join(expList) # This is a list of areasymbol with saverest for metadata
                    

            if len(areasymList) == 0:
                wc = ""

            elif len(areasymList) == 1:
                wc = "areasymbol = '" + areasymList[0] + "'"

            else:
                wc = "areasymbol IN " + str(tuple(areasymList))

            
            # PrintMsg(" \nsurveyInfo: " + expInfo, 1)
            # PrintMsg(" \nQuery: " + wc, 1)

            # Handle soilPolygons layer now. Use mapunit table to determine which will be copied to
            # the new geodatabase.
            #
            # What is the best way to select the matching polygons? Query by mukey or areasymbol? Do I
            # need to check to make sure mukey and areasymbol are populated? Do I need to add that
            # as a separate tool?

            if str(soilPolygons) == "":
                featCnt = 0

            else:
                featCnt = int(arcpy.GetCount_management(soilPolygons).getOutput(0))

            if 1 == 1:  # process spatial data (soilPolygons or shapefiles included in Staging Server download
                missingMapunits = GetSoilPolygons(outputWS, AOI, soilPolygons, featCnt, bValidation, bUpdateMukeys, areasymList, tmpFolder)

                #if len(missingMapunits) > 0:
                    # list of mapunits that exist in the NASIS export, but not the spatial
                #    PrintMsg(" \n\tThese mapunits exist in the NASIS export(s) but not the spatial:  " + ", ".join(missingMapunits), 1)
  
                # Create table relationships and indexes
                bRL = CreateTableRelationships(outputWS)



                # For metadata, get the distinct list of download generation date-timestamps
                # from distmd.distgendate column
                #
                distmdTbl = os.path.join(outputWS, "distmd")
                genDates = list()
                
                with arcpy.da.SearchCursor(distmdTbl, ["distgendate"]) as cur:
                    for rec in cur:
                        if not rec[0] in genDates:
                            genDates.append(rec[0])

                if len(genDates) > 1:
                    genDates.sort()
                    dateRange = genDates[0].isoformat() + " -> " + genDates[-1].isoformat()

                else:
                    dateRange = genDates[0].isoformat()

                PrintMsg(" \nNASIS Download: " + dateRange, 1)

    

                # Update metadata for the geodatabase and all featureclasses
                PrintMsg(" \nUpdating metadata...", 0)
                arcpy.SetProgressorLabel("Updating metadata...")
                mdList = [outputWS, os.path.join(outputWS, "FEATLINE"), os.path.join(outputWS, "FEATPOINT"), \
                os.path.join(outputWS, "MUPOINT"), os.path.join(outputWS, "MULINE"), os.path.join(outputWS, "MUPOLYGON"), \
                os.path.join(outputWS, "SAPOLYGON")]
                remove_gp_history_xslt = os.path.join(os.path.dirname(sys.argv[0]), "remove geoprocessing history.xslt")

                if not arcpy.Exists(remove_gp_history_xslt):
                    raise MyError, "Missing required file: " + remove_gp_history_xslt

                #PrintMsg(" \nSurveyInfo: " + str(expInfo), 1)
                PrintMsg(" \nSkipping medatadata for now", 1)

                #for target in mdList:
                #    bMetadata = UpdateMetadata(outputWS, target, expInfo, remove_gp_history_xslt, dateRange)

                env.workspace = os.path.dirname(env.scratchFolder)
                #PrintMsg(" \nCleaning log files from " + env.workspace, 1)

                logFiles = arcpy.ListFiles("xxImport*.log")

                if len(logFiles) > 0:
                    #PrintMsg(" \nFound " + str(len(logFiles)) + " log files in " + env.workspace, 1)
                    for logFile in logFiles:
                        #PrintMsg("\t\tDeleting " + logFile, 1)
                        arcpy.Delete_management(logFile)

                if arcpy.Exists(tmpFolder):
                    arcpy.Delete_management(tmpFolder)
                    
                #PrintMsg(" \nProcessing complete", 0)
                PrintMsg(" \nSuccessfully created a geodatabase containing the following surveys: " + ", ".join(areasymList), 0)

                PrintMsg(" \nOutput file geodatabase:  " + outputWS + "  \n ", 0)
                    
                #else:
                #    PrintMsg("Failed to export all data to gSSURGO. Spatial export error", 2)
                #    return False


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

## ===================================================================================
def IdentifyNewInterps(outputWS):
    # Generate list of unpublished interps not found in sdvattribute table, but do exist
    # in the sainterp and cointerp tables of this NASIS-SSURGO download
    # Adding this information will help make these interps 'mappable'.

    try:
        saInterps = list()
        sdvInterps = list()
        missingInterps = list()
        dInterps = dict()
        
        # create pointers to tables being used
        sainterpTbl = os.path.join(outputWS, "sainterp")
        sdvattTbl = os.path.join(outputWS, "sdvattribute")
        sdvfolderattTbl = os.path.join(outputWS, "sdvfolderattribute")
        sdvfolderTbl = os.path.join(outputWS, "sdvfolder")

        with arcpy.da.SearchCursor(sdvattTbl, ["nasisrulename"], where_clause="attributetablename = 'cointerp'") as cur:
            for rec in cur:
                interpName = rec[0].encode('ascii')
                
                if not interpName in sdvInterps:
                    sdvInterps.append(interpName)
              
        with arcpy.da.SearchCursor(sainterpTbl, ["interpname", "interpdesc"]) as cur:
            for rec in cur:
                interpName = rec[0].encode('ascii')

                if not interpName in sdvInterps and not interpName in missingInterps:
                    interpDesc = str(rec[1])
                    dInterps[interpName] = interpDesc 
                    missingInterps.append(interpName)

        # I think I can add a new set of attributekeys (begin 10000) to sdvattribute
        # and folderkey (get max + 1) and foldersequence (get max + 1), foldername, folderdescription to the sdvfolder
        # and folderkey with attributekey for each interp to the sdvfolderattribute table
        #
        if len(missingInterps) > 0:
            PrintMsg(" \nNew, unpublished interpretations found in NASIS export: \n\t", 0)
            PrintMsg("\t" + ("\n\t").join(missingInterps), 0)

            # Get max folderkey and max sequence from original sdvfolder table
            maxFolderKey = 0
            maxSequence = 0
            attributeKey = 5000  # start missing interps at 5000 rather than MAX. Not sure if this is a good idea.
            maplegendXML = '<Map_Legend maplegendkey="4"><ColorRampType type="0" name="Random"><Values min="50" max="99" /><Saturation min="33" max="66" /><Hue start="0" end="360" /></ColorRampType><Legend_Symbols shapeType="polygon"><Styles fillStyle="esriSFSSolid" /><Font type="Times New Roman" size="8" red="0" green="0" blue="0" /><Line type="outline" width="0.4" red="0" green="0" blue="0" /></Legend_Symbols><Legend_Elements transparency="0" /></Map_Legend>'
            

            with arcpy.da.SearchCursor(sdvfolderTbl, ["foldersequence", "folderkey"]) as cur:
                for rec in cur:
                    seq, key = rec
                    maxFolderKey = max(key, maxFolderKey)
                    maxSequence = max(seq, maxSequence)

            maxFolderKey += 1  # Only adding one new folder for all missing interps
            maxSequence += 1

            # sdvfolder table
            with arcpy.da.InsertCursor(sdvfolderTbl, ["foldersequence", "foldername", "folderdescription", "folderkey"]) as cur:
                rec = [maxSequence, "New Interps", "Interpretations that have not yet been published to the Soil Data Warehouse, Web Soil Survey", maxFolderKey]
                cur.insertRow(rec)

            for interpName in missingInterps:
                attributeKey += 1

                # sdvfolderattribute table 
                with arcpy.da.InsertCursor(sdvfolderattTbl, ["folderkey", "attributekey"]) as cur:
                    rec = [maxFolderKey, attributeKey]
                    cur.insertRow(rec)
            
                # sdvattribute table
                attFlds = ["attributekey", "attributename", "attributetablename", "attributecolumnname", "attributelogicaldatatype", \
                           "attributefieldsize", "attributedescription", "attributetype", "nasisrulename", "ruledesign", "notratedphrase", \
                           "mapunitlevelattribflag", "complevelattribflag", "cmonthlevelattribflag", "horzlevelattribflag", \
                           "resultcolumnname", "dqmodeoptionflag", "maplegendkey", "maplegendclasses", "maplegendxml", "algorithmname", \
                           "effectivelogicaldatatype"]
                
                with arcpy.da.InsertCursor(sdvattTbl, attFlds) as cur:
                    resultColumn = "interp" + str(attributeKey)
                    rec = [attributeKey, interpName, "cointerp", "interphrc", "String", 254, dInterps[interpName], "Interpretation", interpName, 1, None, 0, 1, 0, 0, resultColumn, 0, 5, None, maplegendXML, "Dominant Condition", "String"]
                    cur.insertRow(rec)

        return dInterps

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()
        
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
import arcpy, sys, string, os, traceback, locale, time, datetime, csv, zipfile
from operator import itemgetter, attrgetter
import xml.etree.cElementTree as ET
from arcpy import env

try:
    if __name__ == "__main__":

        # New tool parameters
        # 0 NASIS Export Folder (where unzipped tabular text files are stored) Only one of the first two parameters is needed.
        # 1 Soil Polygon Layer  (Soil Polygon layer that will be married to the NASIS tabular data)
        # 2 Output geodatabase  (Output file geodatabase that will contain the matching spatial and attribute data)
        # 3 Geographic Region   (Determines output coordinate system)

        zipFolder = arcpy.GetParameterAsText(0)            #  NASIS Export Folder
        zipFileNames = arcpy.GetParameter(1)
        soilPolygons = arcpy.GetParameterAsText(2)   #  Soil Polygon Layer
        outputWS = arcpy.GetParameterAsText(3)       #  Output geodatabase
        AOI = arcpy.GetParameterAsText(4)            #  Geographic Region
        bUpdateMukeys = arcpy.GetParameter(5)        #  Get mukeys from mapunit-legend tables and apply to spatial
        bValidation = arcpy.GetParameter(6)          #  Compare mapunit check

                                         
        # Original gSSURGO function bGood = gSSURGO(inputFolder, surveyList, outputWS, AOI, aliasName, useTextFiles, False, areasymbolList)
        bGood = gSSURGO(zipFolder, zipFileNames, soilPolygons, outputWS, AOI, bValidation, bUpdateMukeys)


except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
