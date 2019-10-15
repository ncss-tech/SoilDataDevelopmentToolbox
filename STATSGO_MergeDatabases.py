# STATSGO_MergeDatabases.py
#
# Designed to replace gSSURGO Notcoms and Denied Access mapunits with updated STATSGO data

# TODO:  Using NASIS-SSURGO Downloads is a little more complicated than out-of-the-box STATSGO.
# Need to automate the process for importing STATSGO download into a file geodatabase. Currently
# using ArcGIS Tools for NASIS2/Create gSSURGO DB - Manual Process tool. Needs to be modified
# just to use with the custom legends and be able to update all keys to use the original STATSGO keys.

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
def GetTemplateDate(newDB, areaSym):
    # Get SAVEREST date from previously existing Template database
    # Use it to compare with the date from the WSS dataset
    # If the existing database is same or newer, it will be kept and the WSS version skipped
    try:
        if not arcpy.Exists(newDB):
            return 0

        saCatalog = os.path.join(newDB, "SACATALOG")
        dbDate = 0
        wc = "[AREASYMBOL] = '" + areaSym + "'"

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
                        tblInfo[importFileName] = physicalName.lower(), aliasName

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
                PrintMsg("Discrepancy in SSURGO Version number for Template database and SSURGO download", 1)

        else:
            # Unable to open SYSTEM table in existing dataset
            # Warn user but continue
            PrintMsg("Unable to open 'SYSTEM - Template Database Information'", 1)

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
                areaSym = rec[0]
                lkey = rec[1]
                musym = rec[2]
                mukey = rec[3]

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
        rowCnt = 0

        with arcpy.da.SearchCursor(inTbl, inFlds, where_clause=interpSQL) as sCur:
            outCur = arcpy.da.InsertCursor(outTbl, outFlds)

            for inRec in sCur:
                outCur.insertRow(inRec)
                rowCnt += 1

            #del outCur
            #del inRec
        #PrintMsg(" \nUpdated " + str(rowCnt) + " records in " + outTbl, 1)
        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

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
                tblName, aliasName = tblInfo[txtFile]
                tblList.append(tblName)

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
def ImportTables(inputMDB, newGDB, mukeyList):
    #
    # Import data from the specified STATSGO-Access Template database.
    # The  database must be populated

    # To make this work with the STATSGO merge, I need to add filter so that only
    # the selected set of STATSGO tabular data is brought across.
    #
    # For some reason cosoilmoist for US STATSGO is failing.
    #

    try:
        # NEED TO LOOK AT THESE STATSGO TABLES TO SEE IF THEY SHOULD BE IMPORTED OR SKIPPED:
        # 

        
        # Testing new order
        tblList = ['distmd', 'legend', 'distlegendmd', 'laoverlap', 'legendtext', 'mapunit', 'component', 'muaggatt', 'muaoverlap', 'mucropyld', 'mutext', 'chorizon', 'cointerp', 'cocanopycover', 'cocropyld', 'codiagfeatures', 'coecoclass', 'coeplants', 'coerosionacc', 'coforprod', 'cogeomordesc', 'cohydriccriteria', 'comonth', 'copmgrp', 'copwindbreak', 'corestrictions', 'cosurffrags', 'cotaxfmmin', 'cotaxmoistcl', 'cotext', 'cotreestomng', 'cotxfmother', 'chaashto', 'chconsistence', 'chdesgnsuffix', 'chfrags', 'chpores', 'chstructgrp', 'chtext', 'chtexturegrp', 'chunified', 'coforprodo', 'copm', 'cosoilmoist', 'cosoiltemp', 'cosurfmorphgc', 'cosurfmorphhpp', 'cosurfmorphmr', 'cosurfmorphss', 'chstruct', 'chtexture', 'chtexturemod', 'sacatalog']
        PrintMsg(" \nAppending STATSGO attribute data to the merged database...", 0)

        if len(tblList) == 0:
            raise MyError, "No tables found in " +  newGDB

        # Save key values for use in queries
        keyValues = dict() # dictionary containing a list of key field names for each SDV table
        
        # PrintMsg(" \n\tAdding " + Number_Format(len(mukeyList), 0, True) + " mukeys to keyValues dictionary", 1)
        keyValues["mukey"] = mukeyList
        tblCnt = 0
        tblName = ""

        arcpy.SetProgressor("step", "Importing attribute tables... ", 0, len(tblList), 1)
        #PrintMsg(" \nProcessing these tables: " + ", ".join(tblList), 1)

        for tblName in tblList:
            # Import data for each table
            #
            outputTbl = os.path.join(newGDB, tblName)  # gNATSGO database table
            inputTbl = os.path.join(inputMDB, tblName) # gSSURGO database table

            # Get key fields for this table
            # tbl = mdstatidxdet
            mdFields = ["tabphyname", "idxphyname", "colphyname"]
            wc = "tabphyname = '" + tblName + "'"
            
            # Table with primary and foreign key information for each table
            mdstatTbl = os.path.join(inputMDB, "mdstatidxdet")
            parentKey = ""
            foreignKey = ""
            
            with arcpy.da.SearchCursor(mdstatTbl, ["tabphyname", "idxphyname", "colphyname"], where_clause=wc) as cur:
                for rec in cur:
                    #PrintMsg("\t\t" + str(rec), 1)
                    
                    if rec[1].startswith("DI_"):
                        if rec[2].encode('ascii') in keyValues:
                            # Trying to capture cokey for cointerp with this logic
                            foreignKey = rec[2].encode('ascii')

                    elif rec[1].startswith("PK_"):
                        parentKey = rec[2].encode('ascii')
                
            if arcpy.Exists(inputTbl):
                # Problem with order? I don't think cokey query is being used for COMONTH table
                recCnt = int(arcpy.GetCount_management(inputTbl).getOutput(0))
                #PrintMsg(" \nKeys for " + tblName + ": " + parentKey + "; " + foreignKey, 1)
                
                if recCnt == 0:
                    if tblName == "mapunit":
                        raise MyError, " Input table " + tblName + " is not populated"
                    
                    else:
                        #PrintMsg("\tInput table " + tblName + " is not populated", 1)
                        tmpTbl = ""  # initialize this variable so that the del at the end won't fail.
                    
                else:
                    # Create a table view that will allow selected sets to be created
                    #
                    # Queries need to use foreignKey
                    # if not parentKey in keyValues: append each parentKey value to keyValues[parentKey]
                    #
                    tmpTbl = "TempTable"

                    if arcpy.Exists(tmpTbl):
                        arcpy.Delete_management(tmpTbl)
                        
                    iCnt = 0
                    PrintMsg("\tImporting " + tblName + "...", 0)

                    fieldNames = [fld.name for fld in arcpy.Describe(inputTbl).fields if fld.type != "OID"]  # get list of fields from MDB (no OBJECTID)
                    tblCnt += 1
                    arcpy.MakeQueryTable_management(inputTbl, tmpTbl, "ADD_VIRTUAL_KEY_FIELD")
                    arcpy.SelectLayerByAttribute_management(tmpTbl, "CLEAR_SELECTION")
                    #PrintMsg(" \n" + tblName + " fields: " + ", ".join(fieldNames), 1)

                    # Get key values for query
                    if tblName == "mapunit":
                        # Start with mapunit table for now, rather than legend table.
                        keys = keyValues["mukey"]
                        fieldName = "mukey"

                    else:
                        if foreignKey in keyValues:
                            # Base query on foreign key
                            keys = keyValues[foreignKey]
                            fieldName = foreignKey

                        else:
                            fieldName = parentKey

                            if parentKey in keyValues:
                                # Base query on primary key
                                keys = keyValues[parentKey]

                            else:
                                # Read all records for this table and add all primary key values
                                keyValues[parentKey] = []
                                keys = []

                    if len(keys) > 0:
                        # Split the list of key values into bite-sized chunks
                        n = 1000
                        keyList = [keys[i:i + n] for i in xrange(0, len(keys), n)]

                    else:
                        keyList = [[]]

                    recCnt = int(arcpy.GetCount_management(tmpTbl).getOutput(0))
                            
                    # LOOP QUERIES HERE TO HANDLE VERY LONG QUERY STRINGS (PRIMARILY CONUS PROBLEM)
                    for keys in keyList:

                        if len(keys) > 1:
                            wc = fieldName + " IN " + str(tuple(keys))
                            
                        elif len(keys) == 1:
                            wc = fieldName + " = '"  + keys[0] + "'"

                        else:
                            wc = ""

                        arcpy.SetProgressorLabel("Importing from " + tblName + "  ( contains " + Number_Format(recCnt, 0, True) + " records )...")
                        arcpy.SetProgressorPosition()

                        # get indices for primary and foreign keys
                        if foreignKey != "" and foreignKey in fieldNames:
                            fIndx = fieldNames.index(foreignKey)

                        if parentKey != "" and parentKey in fieldNames:
                            pIndx = fieldNames.index(parentKey)
                        
                        sdvCur = arcpy.da.SearchCursor(tmpTbl, fieldNames, where_clause=wc, sql_clause=("DISTINCT " + fieldName, None))
                        outCur = arcpy.da.InsertCursor(outputTbl, fieldNames)
                        
                        if foreignKey != "":
                            # foreignKey is identified and being used in the query

                            if not parentKey in keyValues:
                                # capture parent key values
                                pKeyValues = list()

                                for rec in sdvCur:
                                    pKeyValues.append(rec[pIndx].encode('ascii'))  # pKey
                                    outCur.insertRow(rec)
                                    iCnt += 1

                                if len(pKeyValues) > 0:
                                    pKeyValues = list(set(pKeyValues))
                                    keyValues[parentKey] = pKeyValues
                                    del pKeyValues
                                    
                            else:
                                # no need to capture any key values

                                for rec in sdvCur:
                                    outCur.insertRow(rec)
                                    iCnt += 1
         
                        elif parentKey != "" and not parentKey in keyValues:
                            # No foreign key identified
                            # capture parent key values instead
                            pKeyValues = list()

                            for rec in sdvCur:
                                pKeyValues.append(rec[pIndx].encode('ascii'))  # pKey
                                outCur.insertRow(rec)
                                iCnt += 1

                            if len(pKeyValues) > 0:
                                pKeyValues = list(set(pKeyValues))
                                keyValues[parentKey] = pKeyValues
                                del pKeyValues

                        elif parentKey != "" and parentKey in keyValues:
                            # No foreign key identified
                            # keyValues dictionary already has parent key values

                            for rec in sdvCur:
                                outCur.insertRow(rec)
                                iCnt += 1

                        else:
                            raise MyError, "Bad logic for key values on " + tblName

                    if iCnt > 0:
                        PrintMsg("\t\tImported " + Number_Format(iCnt, 0, True) + " records to " + tblName, 0)

                    else:
                        PrintMsg("\t\tImported " + Number_Format(iCnt, 0, True) + " records to " + tblName, 1)
                        
                    del sdvCur, outCur
                    #PrintMsg("\t" +  Number_Format(iCnt, 0, True) + " written records", 1)

            else:
               PrintMsg(" \nSkipping table " + tblName, 1)


        arcpy.RefreshCatalog(newGDB)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===============================================================================================================
def GetClipPolygons(fcName, newGDB, inputMDB, shpFile, newMukeys, inputRaster):
    #

    try:

        # Get list of NOTCOM, NOTPUB and Denied Access map unit keys
        env.workspace = newGDB
        env.outputCoordinateSystem = inputRaster
        mapunitTbl = os.path.join(newGDB, "mapunit")
        compTbl = os.path.join(newGDB, "component")
        hzTbl = os.path.join(newGDB, "chorizon")
        
        mukeyList = list()  # list of mukeys for those gSSURGO mapunit polygons that need to be replaced by STATSGO

        # Kyle's query to identify Notcoms and Denied access mapunits in SSURGO
        wc = "musym IN ('NOTCOM', 'NOTPUB') Or UPPER (muname) LIKE '%DENIED%' Or UPPER (muname) LIKE '%ACCESS%' Or UPPER ( muname) LIKE '%NO SOILS DATA%' Or UPPER(muname) LIKE '%NOT SURVEY%' Or UPPER (muname) LIKE '%NO DATA%'" 

        with arcpy.da.SearchCursor(mapunitTbl, ["mukey"], where_clause=wc) as cur:
            for rec in cur:
                mukeyList.append(rec[0].encode('ascii'))     

        #shpFile = shpFiles[0]
        inputCS = arcpy.Describe(shpFile).spatialReference
        inputLayer = "gSSURGO Polygons"
        
        outputFC = os.path.join(newGDB, fcName)
        outputCS = arcpy.Describe(outputFC).spatialReference
        env.outputCoordinateSystem = outputCS
        env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"

        if len(mukeyList) == 0:
            raise MyError, "No NOTCOM mapunits identified"

        elif len(mukeyList) == 1:
             wc = "mukey = '" + mukeyList[0] + "'"

        else:
            wc = "mukey IN " + str(tuple(mukeyList))

        #PrintMsg(" \nWhereClause: " + wc, 1)

        # Create gSSURGO soil polygon featurelayer for NOTCOMs
                                             
        arcpy.MakeFeatureLayer_management(outputFC, inputLayer, wc)
        cnt = int(arcpy.GetCount_management(inputLayer).getOutput(0))

        if cnt > 0:
            # Make a new featureclass: NOTCOMS. Skipping this step for now...
            # STATSGO polygons will have either 'US' or STPO areasymbol
            PrintMsg(" \nSelected " + Number_Format(cnt, 0, True) + " associated gSSURGO soil polygons for replacement", 0)
            arcpy.CopyFeatures_management(inputLayer, os.path.join(newGDB, "NOTCOMS"))
            arcpy.SetProgressorLabel("Clip layer created")

            # Clip STATSGO polygons by NOTCOMs
            statsgoLayer = "STATSGO Layer"
            arcpy.MakeFeatureLayer_management(shpFile, statsgoLayer)
            tmpFC = os.path.join(env.scratchGDB, "STATSGO2")
            newFC = os.path.join(env.scratchGDB, "STATSGO")
            arcpy.SetProgressorLabel("Clipping out replacement STATSGO polygons")
            arcpy.Clip_analysis(statsgoLayer, inputLayer, tmpFC)
            arcpy.MultipartToSinglepart_management(tmpFC, newFC)

            if arcpy.Exists(newFC):
                cnt2 = int(arcpy.GetCount_management(newFC).getOutput(0))

            else:
                raise MyError, "Failed to create clipped STATSGO polygons"

            # Create STATSGO survey boundary ('US') polygons to update the gNATSGO SAPOLYGON featureclass
            # 15970 is the LKEY for STATSGO
            #PrintMsg(" \nNeed to get LKEY for STATSGO survey area of 'US'", 1)
            statsgoSA = os.path.join(env.scratchGDB, "xxSA_Statsgo")
            outputSA = os.path.join(newGDB, "SAPOLYGON")
            tmpSA = os.path.join(newGDB, "newSAPOLYGON")
            arcpy.Dissolve_management(newFC, statsgoSA, ["AREASYMBOL", "SPATIALVER"], "", "SINGLE_PART")
            # Need to add LKEY column to statsgoSA featureclass
            arcpy.AddField_management(statsgoSA, "LKEY", "TEXT", "#", "#", "30")
            arcpy.AddField_management(statsgoSA, "SOURCE", "TEXT", "#", "#", "30")
            arcpy.AddField_management(outputSA, "SOURCE", "TEXT", "#", "#", "30")

            legendTbl = os.path.join(inputMDB, "legend")
            dLegend = dict()
            dAreasymbol = dict()

            # Need to make sure that all replacement attribute data have a 'US' areasymbol.

            with arcpy.da.SearchCursor(legendTbl, ["lkey"]) as cur:
                for rec in cur:
                    statsgoLkey = rec[0]

            with arcpy.da.UpdateCursor(statsgoSA, ["lkey", "source"]) as cur:
                for rec in cur:
                    rec = [statsgoLkey, "STATSGO2"]
                    cur.updateRow(rec)

            # Update gNATSGO using STATSGO SAPOLYGONs
            arcpy.Update_analysis(outputSA, statsgoSA, tmpSA, "BORDERS", 0)

            if arcpy.Exists(tmpSA):
                arcpy.TruncateTable_management(outputSA)

                with arcpy.da.InsertCursor(outputSA, ["shape@", "areasymbol", "spatialver", "lkey", "source"]) as udCur:
                    sCur = arcpy.da.SearchCursor(tmpSA, ["shape@", "areasymbol", "spatialver", "lkey", "source"])
                    
                    for rec in sCur:
                        newRec = list(rec)
                        if newRec[-1] is None:
                            newRec[-1] = "SSURGO"
                        udCur.insertRow(newRec)

                    del sCur

                arcpy.Delete_management(tmpSA)
                del tmpSA
                
            PrintMsg(" \nSurvey Boundary featureclass attributes updated...", 0)

            # Delete the NOTCOM polygons from MUPOLYGON featureclass
            #PrintMsg(" \nDeleting NOTCOM polygons from output MUPOLYGON featureclass...", 1)
            arcpy.SetProgressorLabel("Deleting NOTCOM polygons from " + inputLayer)
            arcpy.DeleteFeatures_management(inputLayer)

            arcpy.Delete_management(inputLayer) # just getting rid of featurelayer
            del inputLayer

            # Append clipped STATSGO soil polygons to gSSURGO MUPOLYGON
            #
            fields = arcpy.Describe(outputFC).fields
            fieldList = [fld.name.upper() for fld in fields if fld.type != "OID" and not fld.name.upper().startswith("SHAPE")]
            fieldList.insert(0, "SHAPE@")
            fieldList.insert(0, "OID@")
            mukeyIndx = fieldList.index("MUKEY")
            PrintMsg(" \nAppending STATSGO replacement polygons to " + outputFC + "...", 1)
            arcpy.SetProgressorLabel("Appending STATSGO replacement polygons to " + outputFC + "...")

            updateCnt = 0
			
            with arcpy.da.InsertCursor(outputFC, fieldList) as outCur:  # output MUPOLYGONS
                inCur = arcpy.da.SearchCursor(newFC, fieldList)         # input STATSGO. Need to confirm that fieldLists match.
				
                for rec in inCur:
                    mukey = rec[mukeyIndx].encode('ascii')
                    #oid = str(rec[0])
                    #geom = rec[1]
                    #acres = geom.getArea("PLANAR", "ACRES")

                    if not mukey in newMukeys:
                        newMukeys.append(mukey)

                    outCur.insertRow(rec)
                    updateCnt += 1
                    #PrintMsg("\tAdding STATSGO soil polygon " + oid + ": " + str(mukey) + " with area of " + str(round(acres, 2)) + " acres", 1)

            if not updateCnt == cnt2:
                PrintMsg(" \nProblem with appending STATSGO polygons to new MUPOLYGON featureclass, only " + str(updateCnt) + " polygons were transferred", 1)
            
            else:
                PrintMsg(" \nSuccessfully appended " + str(updateCnt) + " STATSGO soil polygons to the new MUPOLYGON featureclass", 1)

        else:
            raise MyError, "Failed to select NOTCOMS..."

        # Create raster for replacement STATSGO mapunit polygons
        bMerged = MergeRasters(newGDB, newFC, inputRaster, newMukeys)

        if bMerged == False:
            return False

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False


## ===============================================================================================================
def MergeRasters(newGDB, statsgoPolys, inputRaster, newMukeys):
    #
    # Replace NOTCOM areas in raster with STATSGO raster
    # Use NOTCOM featureclass in newGDB

    try:
        PrintMsg(" \nUpdating raster layer....", 0)
        # Create featurelayer for replacement STATSGO polygons
        #PrintMsg(" \nNew polygon featurelayer...", 0)
        tmpPolys = "STATSGO Polygons"
        arcpy.MakeFeatureLayer_management(statsgoPolys, tmpPolys)

        # Create lookup table for mukey values to facilitate raster conversion
        # and addition of mukey column to raster attribute table.
        lu = os.path.join(env.scratchGDB, "Lookup")

        if arcpy.Exists(lu):
            arcpy.Delete_management(lu)

        # The Lookup table contains both MUKEY and its integer counterpart (CELLVALUE).
        # Using the joined lookup table creates a raster with CellValues that are the
        # same as MUKEY (but integer). This will maintain correct MUKEY values
        # during a moscaic or clip.
        #
        PrintMsg("\tCreating Lookup table...", 0)
        arcpy.CreateTable_management(os.path.dirname(lu), os.path.basename(lu))
        arcpy.AddField_management(lu, "CELLVALUE", "LONG")
        arcpy.AddField_management(lu, "MUKEY", "TEXT", "#", "#", "30")

        with arcpy.da.InsertCursor(lu, ("CELLVALUE", "MUKEY") ) as inCursor:
            for mukey in newMukeys:
                rec = mukey, mukey
                inCursor.insertRow(rec)

        # Add MUKEY attribute index to Lookup table
        arcpy.AddIndex_management(lu, ["mukey"], "Indx_LU")
        #PrintMsg(" \nJoining Lookup table...", 1)
        arcpy.AddJoin_management (tmpPolys, "MUKEY", lu, "MUKEY", "KEEP_ALL")

        arcpy.SetProgressor("default", "Running PolygonToRaster conversion...")
        #env.extent = fullExtent

        # Need to make sure that the join was successful
        time.sleep(1)
        rasterFields = arcpy.ListFields(tmpPolys)
        rasterFieldNames = list()

        for rFld in rasterFields:
            rasterFieldNames.append(rFld.name.upper())

        if not "LOOKUP.CELLVALUE" in rasterFieldNames:
            raise MyError, "Join failed for Lookup table (CELLVALUE)"

        if (os.path.basename(statsgoPolys) + ".SPATIALVERSION") in rasterFieldNames:
            #raise MyError, "Join failed for Lookup table (SPATIALVERSION)"
            priorityFld = os.path.basename(statsgoPolys) + ".SPATIALVERSION"

        else:
            priorityFld = os.path.basename(statsgoPolys) + ".SPATIALVER"


        #ListEnv()
        env.pyramid = "PYRAMIDS 0 NEAREST"
        
        statsgoRas = os.path.join(env.scratchGDB, "statsgo_ras")
        rasDesc = arcpy.Describe(os.path.join(newGDB, inputRaster))
        iRaster = rasDesc.meanCellHeight
        rasPrj = rasDesc.spatialReference
        PrintMsg("\tConverting replacement STATSGO polygons to a temporary raster (" + statsgoRas + "...", 0)
        arcpy.PolygonToRaster_conversion(tmpPolys, "Lookup.CELLVALUE", statsgoRas, "MAXIMUM_COMBINED_AREA", priorityFld, iRaster) # No priority field for single raster

        # immediately delete temporary polygon layer to free up memory for the rest of the process
        time.sleep(1)
        arcpy.Delete_management(tmpPolys)


        # ****************************************************
        # Build pyramids and statistics
        # ****************************************************
        #
        # DO I NEED TO HAVE STATISTICS FOR THIS INTERIM RASTER?
        #
        #
        if arcpy.Exists(statsgoRas):
            time.sleep(3)

            # ****************************************************
            # Add MUKEY to final raster
            # ****************************************************
            # Build attribute table for final output raster. Sometimes it fails to automatically build.
            #PrintMsg("\tBuilding raster attribute table and updating MUKEY values", )
            #arcpy.SetProgressor("default", "Building raster attribute table...")
            arcpy.BuildRasterAttributeTable_management(statsgoRas)

        else:
            err = "Missing output raster (" + statsgoRas + ")"
            raise MyError, err


        # Merge the gSSURGO raster and statsgo_ras using Mosaic
        arcpy.ResetProgressor()
        newRaster = os.path.join(newGDB, "MergedRaster")
        ssurgoRaster = os.path.join(newGDB, inputRaster)
        #PrintMsg(" \nssurgoRaster: " + ssurgoRaster, 1)
        
        
        arcpy.SetProgressor("default", "Merging STATSGO raster with gSSURGO raster...")
        pixType = "32_BIT_UNSIGNED"
        #cellSize = 10
        nBands = 1
        mosaicMethod = "LAST"

        #PrintMsg("\tMerging the gSSURGO and STATSGO rasters to " + newRaster + "...", 0)
        #arcpy.MosaicToNewRaster_management([ssurgoRaster, statsgoRas], os.path.dirname(newRaster), os.path.basename(newRaster), rasPrj, pixType, iRaster, nBands, mosaicMethod)

        PrintMsg("\tMerging the gSSURGO and STATSGO rasters to " + ssurgoRaster + "...", 0)
        arcpy.Mosaic_management([statsgoRas], ssurgoRaster, "LAST", "", "", "", "NONE", 0.5, "NONE")
        PrintMsg("\tBuilding attribute table for the new combined raster (" + ssurgoRaster + ")", 0)
        arcpy.SetProgressor("default", "Building raster attribute table for the new combined raster...")
        #arcpy.BuildRasterAttributeTable_management(newRaster)
        arcpy.BuildRasterAttributeTable_management(ssurgoRaster)

        #with arcpy.da.UpdateCursor(newRaster, ["VALUE", "MUKEY"]) as cur:
        with arcpy.da.UpdateCursor(ssurgoRaster, ["VALUE", "MUKEY"]) as cur:
            for rec in cur:
                rec[1] = rec[0]
                cur.updateRow(rec)

        arcpy.CalculateStatistics_management (ssurgoRaster, 1, 1, "", "OVERWRITE" )
        arcpy.SetProgressor("default", "Building pyramids for new raster...")
        PrintMsg("\tBuilding pyramids for new raster", 0)
        arcpy.BuildPyramids_management(ssurgoRaster, "-1", "NONE", "NEAREST", "DEFAULT", "", "SKIP_EXISTING")
        arcpy.ResetProgressor()

        #PrintMsg("\tUpdating " + ssurgoRaster + " with STATSGO information...", 0)
        # arcpy.Delete_management(ssurgoRaster)

        #if not arcpy.Exists(ssurgoRaster):
        #    arcpy.Rename_management(newRaster, ssurgoRaster)
        #    #PrintMsg(" \nCompacting database...", 1)
        #    arcpy.SetProgressorLabel("Compacting database...")
        arcpy.Compact_management(newGDB)
        #    #PrintMsg(" \nFinished compacting database...", 1)

        #else:
        #    PrintMsg("\tUnable to update " + ssurgoRaster + ", changes saved instead to " + newRaster, 1)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CheckStatistics(outputRaster):
    # For no apparent reason, ArcGIS sometimes fails to build statistics. Might work one
    # time and then the next time it may fail without any error message.
    #
    try:
        #PrintMsg(" \n\tChecking raster statistics", 0)

        for propType in ['MINIMUM', 'MAXIMUM', 'MEAN', 'STD']:
            statVal = arcpy.GetRasterProperties_management (outputRaster, propType).getOutput(0)
            #PrintMsg("\t\t" + propType + ": " + statVal, 1)

        return True

    except:
        return False

## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, tempfile, time, shutil, subprocess, csv, re

# Create the Geoprocessor object
from arcpy import env
from time import sleep
#from _winreg import *

try:
    #inputFolder = arcpy.GetParameterAsText(0)           # location of SSURGO datasets containing tabular folders
    #tabList = arcpy.GetParameter(1)                     # list of SSURGO folder names to be proccessed
    #inputDB = arcpy.GetParameterAsText(2)               # custom Template SSURGO database (check version date?)
    #bImportTxt = arcpy.GetParameter(4)                  # boolean. If true, import textfiles. if false, import from Access db.
    inputLayer = arcpy.GetParameterAsText(0)             # original gSSURGO polygons (copy will be made)
    inputRaster = arcpy.GetParameterAsText(1)            # original gSSURGO raster name. This raster will be the mosaic target in the output GDB.
    inputMDB = arcpy.GetParameterAsText(2)               # original STATSGO Template database (mdb or gdb), read only
    inputStatsgoPolygons = arcpy.GetParameterAsText(3)   # 
    newGDB = arcpy.GetParameterAsText(4)                 # new fullpath for output merged geodatabase


    # copy archive version of gSSURGO database to newGDB

    layerDesc = arcpy.Describe(inputLayer)

    if layerDesc.dataType.upper() == "FEATURECLASS":
        inputGDB = os.path.dirname(inputLayer)
        fcName = os.path.basename(inputLayer)

    else:
        inputGDB = os.path.dirname(layerDesc.catalogPath)
        fcName = os.path.basename(layerDesc.catalogPath)

    PrintMsg(" \nCreating new geodatabase based upon " + os.path.basename(inputGDB), 0)
    arcpy.Copy_management(inputGDB, newGDB)
    #PrintMsg(" \nFinished creating new database", 0)

    # process each selected soil survey
    arcpy.SetProgressorLabel("Merging gSSURGO and STATSGO databases...")
    global newMukeys
    newMukeys = list()
    bClipped = GetClipPolygons(fcName, newGDB, inputMDB, inputStatsgoPolygons, newMukeys, inputRaster)

    if bClipped == False:
        raise MyError, ""

    #PrintMsg(" \nNew mukeys: " + str(tuple(newMukeys)), 1)

    # Import all data from Access databases
    if len(newMukeys) > 0:
        #PrintMsg(" \nImporting STATSGO tabular data...", 1)
        bProcessed = ImportTables(inputMDB, newGDB, newMukeys)

        if bProcessed == False:
            raise MyError, ""

    else:
        raise MyError, "No template databases in dbList"


    PrintMsg(" \nCompleted database merge to " + newGDB + " \n ", 0)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
