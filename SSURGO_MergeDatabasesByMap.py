# SSURGO_MergeDatabasesbyMap.py
#
# Based directly upon SSURGO_MergeDatabases.py. Only change is parameter order.
#
# Purpose: allow batch importing of SSURGO data into a custom Template database
# The custom Template database will need to have the AutoExec macro removed and
# a BatchImport macro created so that it can be used to import multiple datasets.
#
# Naming convention of the SSURGO datasets must follow the NRCS Geospatial Standard
# where each survey has it's own folder 'soil_ne109' with spatial and tabular subfolders.
#
# 09-30-2013
# Beta version 10-31-2013
# 11-22-2013
# 01-08-2014
# 01-13-2014 Fixed bug in SetProgressorLabel. Need to better document the use of the output DB name
#            for the tool parameter.
# 2014-09-27
# 2014-2016 Major rewrite. Removed MS Access Tabular Import and now use csv reader on text files
# 2014-10-18 Modified sdv table imports to only add unique values
# 2014-10-18 Modified SYSTEM table to only include cointerp records with ruledepth=0
#
# 2015-10-30 Added proper import for tabular data. Adapted from Create_gSSURGO Tools
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
def GetTemplateDate(newDB, areaSym):
    # Get SAVEREST date from previously existing Template database
    # Use it to compare with the date from the WSS dataset
    # If the existing database is same or newer, it will be kept and the WSS version skipped
    try:
        if not arcpy.Exists(newDB):
            return 0

        saCatalog = os.path.join(newDB, "SACATALOG")
        dbDate = 0
        wc =  "[AREASYMBOL] = '" + areaSym + "'"

        if arcpy.Exists(saCatalog):
            with arcpy.da.SearchCursor(saCatalog, ("SAVEREST"), where_clause=wc) as srcCursor:
                for rec in srcCursor:
                    dbDate = str(rec[0]).split(" ")[0]

            del saCatalog
            del newDB
            return dbDate

        else:
            # unable to open SACATALOG table in existing dataset
            # return 0 which will result in the existing dataset being overwritten by a new WSS download
            return 0

    except:
        errorMsg()
        return 0

## ===============================================================================================================
def GetTableInfo(newDB):
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
def GetTableList(outputWS):
    # Create an ordered list of files (tabular) and output tables
    #
    # Skip all 'MDSTAT' tables. They are static.
    #
    try:
        # Another method using order in textfile list

        # Create a dictionary with table information
        tblInfo = GetTableInfo(outputWS)

        # list of tables
        tblList = list()

        # Create a list of textfiles to be imported. The import process MUST follow the
        # order in this list in order to maintain referential integrity. This list
        # will need to be updated if the SSURGO data model is changed in the future.
        # This list of tables and their schema is related to the SSURGO version.
        txtFiles = ["distmd","legend","distimd","distlmd","lareao","ltext","mapunit", \
        "comp","muaggatt","muareao","mucrpyd","mutext","chorizon","ccancov","ccrpyd", \
        "cdfeat","cecoclas","ceplants","cerosnac","cfprod","cgeomord","chydcrit", \
        "cinterp","cmonth", "cpmatgrp", "cpwndbrk","crstrcts","csfrags","ctxfmmin", \
        "ctxmoicl","ctext","ctreestm","ctxfmoth","chaashto","chconsis","chdsuffx", \
        "chfrags","chpores","chstrgrp","chtext","chtexgrp","chunifie","cfprodo","cpmat","csmoist", \
        "cstemp","csmorgc","csmorhpp","csmormr","csmorss","chstr","chtextur", \
        "chtexmod","sacatlog","sainterp","sdvalgorithm","sdvattribute","sdvfolder","sdvfolderattribute"]
        # Need to add featdesc import as a separate item (ie. spatial\soilsf_t_al001.txt: featdesc)

        for txtFile in txtFiles:

            # Get table name and alias from dictionary
            if txtFile in tblInfo:

                # Get the table name from the dictionary
                tbl, aliasName = tblInfo[txtFile]
                tblList.append(tbl)

            else:
                raise MyError, "Textfile reference '" + txtFile + "' not found in 'mdstattabs table'"

        return tblList
        # End of other method using textfiles

    except MyError, e:
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def SSURGOVersion(newDB, tabularFolder):
    # Get SSURGO version from the Template database "SYSTEM Template Database Information" table
    #
    # Ideally we want to compare with the value in version.txt with the version in
    # the "SYSTEM - Template Database Information" table. If they are not the same
    # the tabular import should be aborted. There are some more specifics about the
    # SSURGO version.txt valu in one of the Import macros of the Template database.
    # Need to follow up and research this more.
    # At this time we are only checking the first 'digit' of the string value.
    #
    # Should be able to get this to work using wildcard for fields and then
    # use the version.txt as an alternative or failover.
    try:
        # Valid SSURGO version for data model. Ensures
        # compatibility between template database and SSURGO download.
        versionTxt = os.path.join(tabularFolder, "version.txt")

        if not arcpy.Exists(newDB):
            raise MyError, "Missing input database (" + newDB + ")"

        if arcpy.Exists(versionTxt):
            # read just the first line of the version.txt file
            fh = open(versionTxt, "r")
            txtVersion = fh.readline().split(".")[0]
            fh.close()

        else:
            # Unable to compare versions. Warn user but continue
            PrintMsg("Unable to find file: version.txt", 1)
            return True

        systemInfo = os.path.join(newDB, "SYSTEM - Template Database Information")

        if arcpy.Exists(systemInfo):
            # Get SSURGO Version from template database
            dbVersion = 0

            with arcpy.da.SearchCursor(systemInfo, "*") as srcCursor:
                for rec in srcCursor:
                    if rec[0] == "SSURGO Version":
                        dbVersion = str(rec[2]).split(".")[0]
                        #PrintMsg("\tSSURGO Version from DB: " + dbVersion, 1)

            del systemInfo
            del newDB

            if txtVersion != dbVersion:
                # SSURGO Versions do not match. Warn user but continue
                PrintMsg("Discrepancy between Template database version (" + str(dbVersion) + " and SSURGO download (" + txtVersion + ")", 1)

        else:
            # Unable to open SYSTEM table in existing dataset
            # Warn user but continue
            PrintMsg("Unable to find Template database table: " + systemInfo, 1)
            return False

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def SortMapunits(newDB):
    # Populate table 'SYSTEM - Mapunit Sort Specifications'. Required for Soil Data Viewer
    #
    # Populate table "SYSTEM - INTERP DEPTH SEQUENCE" from COINTERP using cointerpkey and seqnum
    #
    try:
        # Make query table using MAPUNIT and LEGEND tables and use it to assemble all
        # of the data elements required to create the "SYSTEM - Mapunit Sort Specification" table
        inputTbls = ["legend", "mapunit"]

        fldList = "legend.areasymbol areasymbol;legend.lkey lkey; mapunit.musym musym; mapunit.mukey mukey"
        sqlJoin = "mapunit.lkey = legend.lkey"
        queryTbl = "musorted"

        # Cleanup
        if arcpy.Exists(queryTbl):
            arcpy.Delete_management(queryTbl)

        # Find output SYSTEM table
        sysFields = ["lseq", "museq", "lkey", "mukey"]
        sysTbl = os.path.join(newDB, "SYSTEM - Mapunit Sort Specifications")
        if not arcpy.Exists(sysTbl):
            raise MyError, "Could not find " + sysTbl

        # Clear the table
        arcpy.TruncateTable_management(sysTbl)

        arcpy.MakeQueryTable_management(inputTbls, queryTbl, "ADD_VIRTUAL_KEY_FIELD", "", fldList, sqlJoin)

        # Open the query table, sorting on areasymbol
        #sqlClause = [None, "order by legend_areasymbol asc"]
        dMapunitSort = dict()  # dictionary to contain list of musyms for each survey. Will be sorted
        dMapunitData = dict()  # dictionary for containing all neccessary data for SYSTEM -Map Unit Sort Specification
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key)]

        with arcpy.da.SearchCursor(queryTbl, ["legend_areasymbol", "legend_lkey", "mapunit_musym", "mapunit_mukey"]) as cur:
            for rec in cur:
                areaSym = rec[0].encode('ascii')
                lkey = rec[1].encode('ascii')
                musym = rec[2].encode('ascii')
                mukey = rec[3].encode('ascii')

                # Append muysm values to dictionary by areasymbol key
                if areaSym in dMapunitSort:
                    musymList = dMapunitSort[areaSym]
                    musymList.append(musym)
                    dMapunitSort[areaSym] = musymList

                else:
                    dMapunitSort[areaSym] = [musym]

                # store legend and map unit keys by areasymbol and map unit symbol
                dMapunitData[(areaSym, musym)] = (lkey, mukey)

        # Iterate through dMapunitSort dictionary, sorting muysm values
        areaList = sorted(dMapunitSort.keys())  # sorted list of areasymbols
        lseq = 0
        mseq = 0

        # Now read the dictionary back out in sorted order and populate the SYSTEM - Mapunit Sort Specifications table
        #
        with arcpy.da.InsertCursor(sysTbl, "*") as outCur:

            for areaSym in areaList:
                #PrintMsg(" \nProcessing survey: " + areaSym, 1)
                lseq += 1
                musymList = sorted(dMapunitSort[areaSym], key = alphanum_key)

                for musym in musymList:
                    mseq += 1
                    mKey = (areaSym, musym)
                    lkey, mukey = dMapunitData[(areaSym, musym)]
                    outrec = lseq, mseq, lkey, mukey
                    outCur.insertRow(outrec)


        # Populate "SYSTEM - INTERP DEPTH SEQUENCE" fields: cointerpkey and depthseq
        # from COINTERP fields: cointerpkey and seqnum
        # I am assuming that the cointerp table is already sorted. Is that safe??
        #
        #PrintMsg("\tUpdating SYSTEM - Interp Depth Sequence", 1)
        inTbl = os.path.join(newDB, "cointerp")
        inFlds = ["cointerpkey", "seqnum"]
        outTbl = os.path.join(newDB, "SYSTEM - INTERP DEPTH SEQUENCE")
        outFlds = ["cointerpkey", "depthseq"]
        interpSQL = "ruledepth = 1"

        with arcpy.da.SearchCursor(inTbl, inFlds, interpSQL) as sCur:
            outCur = arcpy.da.InsertCursor(outTbl, outFlds)

            for inRec in sCur:
                outCur.insertRow(inRec)

            del outCur
            del inRec

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ImportTabular(inputFolder, subFolder, newDB, areaSym, iCnt):
    # This function is designed to import tabular data from the text files
    # If the text files have been deleted this won't work!

    # Need to update this function to include the string value truncation!!!

    try:
        # move to tabular folder for the current SSURGO dataset
        env.workspace = os.path.join(inputFolder, subFolder)

        # import the tabular data from text files in the tabular folder
        PrintMsg("\tImporting textfiles from tabular folder...", 0)
        tabularFolder = os.path.join(env.workspace, "tabular")

        # if the tabular directory is empty return False
        if len(os.listdir(tabularFolder)) < 1:
            raise MyError, "No text files found in the tabular folder"

        # Make sure tha the tabular data (version.txt) matches the Access database version
        if not SSURGOVersion(newDB, tabularFolder):
            raise MyError, ""

        # Create a dictionary with table information
        tblInfo = GetTableInfo(newDB)

        # Create a list of textfiles to be imported. The import process MUST follow the
        # order in this list in order to maintain referential integrity. This list
        # will need to be updated if the SSURGO data model is changed in the future.
        # This list of tables and their schema is related to the SSURGO version.
        txtFiles = ["distmd","legend","distimd","distlmd","lareao","ltext","mapunit", \
        "comp","muaggatt","muareao","mucrpyd","mutext","chorizon","ccancov","ccrpyd", \
        "cdfeat","cecoclas","ceplants","cerosnac","cfprod","cgeomord","chydcrit", \
        "cinterp","cmonth", "cpmatgrp", "cpwndbrk","crstrcts","csfrags","ctxfmmin", \
        "ctxmoicl","ctext","ctreestm","ctxfmoth","chaashto","chconsis","chdsuffx", \
        "chfrags","chpores","chstrgrp","chtext","chtexgrp","chunifie","cfprodo","cpmat","csmoist", \
        "cstemp","csmorgc","csmorhpp","csmormr","csmorss","chstr","chtextur", \
        "chtexmod","sacatlog","sainterp","sdvalgorithm","sdvattribute","sdvfolder","sdvfolderattribute"]
        # Need to add featdesc import as a separate item (ie. spatial\soilsf_t_al001.txt: featdesc)

        # set progressor object which allows progress information to be passed for every merge complete
        #arcpy.SetProgressor("step", "Importing tabular data", 0, len(txtFiles) + 1, 1)

        # Problem with length of some memo fields, need to allocate more memory
        csv.field_size_limit(512000)

        dKeys = dict() # dictionary containing a list of key values for each SDV table

        keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyIndx['sdvfolderattribute'] = 1
        keyIndx['sdvattribute'] = 0
        keyIndx['sdvfolder'] = 3
        keyIndx['sdvalgorithm'] = 0
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"

        # Create lists of key values to use in preventing duplicate keys in some SDV* tables
        #
        for sdvTbl in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
            #sdvTbl = os.path.join(outputWS, "sdvfolderattribute")
            indx = keyIndx[sdvTbl]
            fldName = keyFields[sdvTbl]
            attKeys = list()

            with arcpy.da.SearchCursor(os.path.join(newDB, sdvTbl), [keyFields[sdvTbl]]) as sdvCur:
                for rec in sdvCur:
                    attKeys.append(rec[0])  # integer key value

            dKeys[sdvTbl] = attKeys

        # End of sdv keys method
        #PrintMsg(" \nExisting key values for sdvalgorithm: " + str(dKeys["sdvalgorithm"]), 1)

        for txtFile in txtFiles:

            # Get table name and alias from dictionary
            if txtFile in tblInfo:

                # Get the table name from the dictionary
                tblName, aliasName = tblInfo[txtFile]

            else:
                raise MyError, "Textfile reference '" + txtFile + "' not found in 'mdstattabs table'"

            #arcpy.SetProgressorLabel("Importing " + tblName + "...")

            # Full path to SSURGO text file
            txtPath = os.path.join(tabularFolder, txtFile + ".txt")
            if not arcpy.Exists(txtPath):
                raise MyError, "Could not find textfile: " + txtPath

            # Process existing table
            if arcpy.Exists(os.path.join(newDB, tblName)):
                arcpy.SetProgressorLabel("Importing " +  areaSym.upper() + "  (" + Number_Format(iCnt, 0, True) + " of " + Number_Format(len(tabList), 0, True) + "): " + tblName)
                # Get the length for each string field and use to truncate values
                # as they are inserted into the Access database table
                fldList = arcpy.Describe(os.path.join(newDB, tblName)).fields
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

                with arcpy.da.InsertCursor(os.path.join(newDB, tblName), fldNames) as cursor:

                    if tblName.lower() in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
                        # Process the 'SDV' tables separately to prevent key errors from duplicate records
                        #
                        indx = keyIndx[tblName]

                        for rec in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                            keyVals = dKeys[tblName]
                            keyVal = int(rec[indx])  # important that the .csv key value be converted to integer at this point

                            if not keyVal in keyVals:

                                dKeys[tblName].append(rec[indx])
                                newRow = list()
                                fldNo = 0

                                for value in rec:
                                    fldLen = fldLengths[fldNo]

                                    if value == '':
                                        value = None

                                    elif fldLen > 0:
                                        value = value[0:fldLen]

                                    newRow.append(value)
                                    fldNo += 1

                                cursor.insertRow(newRow)

                    else:
                        # Process non-sdv tables. These should all be unique records. If
                        # somehow the record is not unique and exception will be thrown.
                        try:
                            # Use csv reader to read each line in the text file
                            for row in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                                # replace all blank values with 'None' so that the values are properly inserted
                                # into integer values otherwise insertRow fails

                                fldNo = 0
                                newRow = list()

                                for value in row:
                                    fldLen = fldLengths[fldNo]

                                    if value == '':
                                        value = None

                                    elif fldLen > 0:
                                        value = value[0:fldLen]

                                    newRow.append(value)
                                    fldNo += 1

                                cursor.insertRow(newRow)

                        except:
                            errorMsg()
                            PrintMsg("\t" + tbl + ": error reading line for " + txtFile + ".txt", 1)

            else:
                raise MyError, "Required table '" + tbl + "' not found in " + newDB

            arcpy.SetProgressorPosition()

        # Import feature description file located in spatial folder
        #
        # ex. soilsf_t_al001.txt
        spatialFolder = os.path.join(os.path.dirname(tabularFolder), "spatial")
        txtFile ="soilsf_t_" + areaSym
        txtPath = os.path.join(spatialFolder, txtFile + ".txt")
        tbl = "featdesc"
        if arcpy.Exists(txtPath):

            # Create cursor for all fields to populate the featdesc table
            with arcpy.da.InsertCursor(tbl, "*") as cursor:

                arcpy.SetProgressorLabel(tbl + "...")

                try:
                    # Use csv reader to read each line in the text file
                    for rowInFile in csv.reader(open(txtPath, 'rb'), delimiter='|', quotechar='"'):
                        # replace all blank values with 'None' so that the values are properly inserted
                        # into integer values otherwise insertRow fails
                        newRow = [None if value == '' else value for value in rowInFile]
                        cursor.insertRow(newRow)

                except:
                    errorMsg()
                    raise MyError, "Error loading " + txtFile + ".txt"

        arcpy.SetProgressorPosition()  # for featdesc table

        # Check the database to make sure that it completed properly, with at least the
        # SAVEREST date populated in the SACATALOG table. Added this primarily to halt
        # processing when the user forgets to set the Trusted Location in MS Access.
        dbDate = GetTemplateDate(newDB, areaSym)

        if dbDate == 0:
            # With this error, it would be best to bailout and fix the problem before proceeding
            raise MyError, "Failed to import tabular data"

        else:
            # Compact database (~30% reduction in mdb filesize)
            try:
                arcpy.SetProgressorLabel("Compacting database ...")
                sleep(1)
                arcpy.Compact_management(newDB)
                PrintMsg("\tCompacted database", 0)

            except:
                # Sometimes ArcGIS is unable to compact (locked database?)
                # Usually restarting the ArcGIS application fixes this problem
                PrintMsg("\tUnable to compact database", 1)

            # Set the Progressor to show completed status
            arcpy.ResetProgressor()
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
def ImportTables(outputWS, dbList):
    #
    # Import tables from an Access Template database. Does not require text files, but
    # the Access database must be populated and it must reside in the tabular folder and
    # it must be named 'soil_d_<AREASYMBOL>.mdb'
    # Origin: SSURGO_Convert_to_Geodatabase.py

    try:
        tblList = GetTableList(outputWS)

        if len(tblList) == 0:
            raise MyError, "No tables found in " +  outputWS

        arcpy.SetProgressor("step", "Importing tabular data...",  0, len(dbList), 1)


        PrintMsg(" \nImporting tabular data from SSURGO Template databases...", 0)

        # Create lists of key values to use in preventing duplicate keys in some SDV* tables
        #
        dKeys = dict() # dictionary containing a list of key values for each SDV table

        keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyIndx['sdvfolderattribute'] = 1
        keyIndx['sdvattribute'] = 0
        keyIndx['sdvfolder'] = 3
        keyIndx['sdvalgorithm'] = 0
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        keyFields['sdvfolderattribute'] = "attributekey"
        keyFields['sdvattribute'] = "attributekey"
        keyFields['sdvfolder'] = "folderkey"
        keyFields['sdvalgorithm'] = "algorithmsequence"

        for sdvTbl in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
            #sdvTbl = os.path.join(outputWS, "sdvfolderattribute")
            indx = keyIndx[sdvTbl]
            fldName = keyFields[sdvTbl]
            attKeys = list()

            with arcpy.da.SearchCursor(sdvTbl, (keyFields[sdvTbl])) as sdvCur:
                for rec in sdvCur:
                    attKeys.append(rec[indx])

            dKeys[sdvTbl] = attKeys

        # End of sdv keys

        iCntr = 0

        for inputDB in dbList:
            iCntr += 1

            # Check the input Template database to make sure it contains data from the Import process
            # Really only checking last record (normally only one record in table). Multiple surveys would fail.
            saCatalog = os.path.join(inputDB, "sacatalog")

            if arcpy.Exists(saCatalog):
                # parse Areasymbol from database name. If the geospatial naming convention isn't followed,
                # then this will not work.
                fnAreasymbol = inputDB[-9:][0:5].upper()
                dbAreaSymbol = ""

                with arcpy.da.SearchCursor(saCatalog, ("AREASYMBOL")) as srcCursor:
                    for rec in srcCursor:
                        # Get Areasymbol from SACATALOG table, assuming just one survey is present in the database
                        dbAreaSymbol = rec[0]

                if dbAreaSymbol != fnAreasymbol:
                    if dbAreaSymbol != "":
                        raise MyError, "Survey data in " + os.path.basename(inputDB) + " does not match filename"

                    else:
                        raise MyError, "Unable to get survey area information from " + os.path.basename(inputDB)

            else:
                # unable to open SACATALOG table in existing dataset
                # return False which will result in the existing dataset being overwritten by a new WSS download
                PrintMsg("SACATALOG table not found in " + os.path.basename(inputDB), 2)
                return False

            for tblName in tblList:
                # Import data for each table
                #
                outputTbl = os.path.join(outputWS, tblName)
                inputTbl = os.path.join(inputDB, tblName)

                if arcpy.Exists(inputTbl):
                    #PrintMsg("\t" + tblName, 0)

                    with arcpy.da.SearchCursor(inputTbl, "*") as sdvCur:
                        outCur = arcpy.da.InsertCursor(outputTbl, "*")

                        arcpy.SetProgressorLabel("Importing " +  dbAreaSymbol.upper() + "  (" + Number_Format(iCntr, 0, True) + " of " + Number_Format(len(dbList), 0, True) + "): " + tblName)

                        if tblName.lower() in ['sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']:
                            # Process the 'SDV' tables separately to prevent key errors from duplicate records
                            #
                            indx = keyIndx[tblName]

                            for rec in sdvCur:
                                if not rec[indx] in dKeys[tblName]:
                                    dKeys[tblName].append(rec[indx])
                                    outCur.insertRow(rec)

                        else:
                            # Process the rest of the 'non-SDV' tables
                            #
                            for rec in sdvCur:
                                outCur.insertRow(rec)

                else:
                    err = "\tError. Could not find table " + tblName
                    raise MyError, err

            arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()

        arcpy.RefreshCatalog(outputWS)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, tempfile, time, shutil, subprocess, csv, re

# Create the Geoprocessor object
from arcpy import env
from time import sleep
#from _winreg import *

try:
    inputFolder = arcpy.GetParameterAsText(0)  # location of SSURGO datasets containing tabular folders
    tabList = arcpy.GetParameter(2)            # list of SSURGO folder names to be proccessed
    inputDB = arcpy.GetParameterAsText(3)      # custom Template SSURGO database (check version date?)
    newDB = arcpy.GetParameterAsText(4)        # new name for final ouput Template database
    bImportTxt = arcpy.GetParameter(5)         # boolean. If true, import textfiles. if false, import from Access db.

    #newDB = os.path.join(inputFolder, newDB)

    if newDB == inputDB:
        raise MyError, "Place input Template database in a different folder"

    if arcpy.Exists(newDB):
        raise MyError, "Template database already exists in the output folder"

    # copy archive version of custom Template DB to a local copy in the input folder
    PrintMsg(" \nCreating new database...", 0)
    shutil.copy2(inputDB, newDB)
    #lastDB = newDB
    iCnt = 0

    # Keep track of any surveys that are skipped
    skippedList = list()

    # process each selected soil survey
    arcpy.SetProgressor("default", "Merging SSURGO databases...")
    PrintMsg(" \nMerging " + str(len(tabList)) + " soil survey datasets", 0)
    dbList = list()

    for subFolder in tabList:

        if not subFolder.encode('ascii').startswith("soil_"):
            raise MyError, subFolder + " is not a valid SSURGO folder name"

        # assume that last 5 characters represent the areasymbol
        areaSym = subFolder[-5:]

        # Need to make sure that this survey does not already exist in the new database
        if GetTemplateDate(newDB, areaSym) == 0:
            # OK. this survey does not yet exist in the new database

            if bImportTxt:
                iCnt += 1
                PrintMsg(" \nProcessing " + subFolder + "...", 0)
                arcpy.SetProgressorLabel("Processing " + subFolder + "   (" + str(iCnt) + " of " + str(len(tabList)) + ")")
                time.sleep(1)
                bProcessed = ImportTabular(inputFolder, subFolder, newDB, areaSym, iCnt)

                # cancel entire process if an import fails
                if bProcessed == False:
                    raise MyError, ""

            else:
                # Create list of individual Access database tables and
                # process after all have been checked

                tabWS = os.path.join(inputFolder, os.path.join(subFolder, "tabular"))
                env.workspace = tabWS
                templateDBs = arcpy.ListWorkspaces("soil_*", "Access")

                if templateDBs is not None:
                    if len(templateDBs) > 0:
                        templateDB = templateDBs[0]
                        dbList.append(templateDB)

                    else:
                        raise MyError, "Template database missing for " + subFolder

                else:
                    raise MyError, "Template database missing for " + subFolder

        else:
            PrintMsg(" \nSkipping survey " + areaSym + " because it already exists in the new database", 1)
            skippedList.append(areaSym)

    if bImportTxt == False:
        # Import all data from Access databases
        if len(dbList) > 0:
            #PrintMsg(" \nImporting list of Template databases...", 1)
            bProcessed = ImportTables(newDB, dbList)

            if bProcessed == False:
                raise MyError, ""

        else:
            raise MyError, "No template databases in dbList"

    # move database from last folder processed back to original location
    # Some how I need to put that SYSTEM table sort at the end
    #
    # Sort map units for Soil Data Viewer SYSTEM table
    arcpy.SetProgressorLabel("Sorting SYSTEM tables...")
    bSorted = SortMapunits(newDB)

    if len(skippedList) > 0:
        PrintMsg(" \nThe following surveys already existed in the new database: " + ", ".join(skippedList), 1)

    PrintMsg(" \nCompleted database merge to " + newDB + " \n ", 0)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
