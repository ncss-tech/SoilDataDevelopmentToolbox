# STATSGO_MergeDatabases.py
#
# Based directly upon SSURGO_MergeDatabases.py.

# Things yet to do.
# 1. Skip importing tables that have no corresponding STATSGO data such as cointerp?
# 2. Should I allow user to name merged output raster?
# 3. Is there any way to purge related NOTCOM table records? Might be able to adapt that
#    functionality to an remove-and-replace old MLRA survey area data.
#
#
# 
#
"""
# Get dominant component by comppct_r and join to component table
component.compkind <>'Miscellaneous area' AND DominantComponent.OBJECTID is not null
AND
hzdept_r = 0 AND (om_r is null or awc_r is null)
"""

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
    # The Access database must be populated, reside in the tabular folder and
    # be named 'soil_d_<AREASYMBOL>.mdb'
    # Origin: SSURGO_Convert_to_Geodatabase.py

    # To make this work with the STATSGO merge, I need to add filter so that only
    # the selected set of STATSGO tabular data is brought across.
    #
    # For some reason cosoilmoist for US STATSGO is failing.
    #

    try:
        # NEED TO LOOK AT THESE STATSGO TABLES TO SEE IF THEY SHOULD BE IMPORTED OR SKIPPED:
        # 

        
        #tblList = GetTableList(newGDB)  # Original

        # Testing new order
        tblList = ['distmd', 'legend', 'distlegendmd', 'laoverlap', 'legendtext', 'mapunit', 'component', 'muaggatt', 'muaoverlap', 'mucropyld', 'mutext', 'chorizon', 'cocanopycover', 'cocropyld', 'codiagfeatures', 'coecoclass', 'coeplants', 'coerosionacc', 'coforprod', 'cogeomordesc', 'cohydriccriteria', 'comonth', 'copmgrp', 'copwindbreak', 'corestrictions', 'cosurffrags', 'cotaxfmmin', 'cotaxmoistcl', 'cotext', 'cotreestomng', 'cotxfmother', 'chaashto', 'chconsistence', 'chdesgnsuffix', 'chfrags', 'chpores', 'chstructgrp', 'chtext', 'chtexturegrp', 'chunified', 'coforprodo', 'copm', 'cosoilmoist', 'cosoiltemp', 'cosurfmorphgc', 'cosurfmorphhpp', 'cosurfmorphmr', 'cosurfmorphss', 'chstruct', 'chtexture', 'chtexturemod', 'sacatalog']

        
        PrintMsg(" \nAppending STATSGO attributes to tabular side of new database...", 0)

        # Handle mapunit, component, chorizon tables first. Skip STATSGO tables that aren't populated.
        #rmTables = ['mapunit', 'component', 'chorizon', 'cointerp', 'sainterp', 'distinterpmd', 'sdvfolderattribute', 'sdvattribute', 'sdvfolder', 'sdvalgorithm']
        #for tbl in rmTables:
        #    tblList.remove(tbl)

        #tblList.insert(0, 'chorizon')
        #tblList.insert(0, 'component')
        #tblList.insert(0, 'mapunit')

        if len(tblList) == 0:
            raise MyError, "No tables found in " +  newGDB

        # Save key values for use in queries
        #keyIndx = dict()  # dictionary containing key field index number for each SDV table
        keyFields = dict() # dictionary containing a list of key field names for each SDV table
        primaryKeys = dict()
        # PrintMsg(" \n\tAdding " + Number_Format(len(mukeyList), 0, True) + " mukeys to primaryKeys dictionary", 1)
        primaryKeys["mukey"] = mukeyList
        tblCnt = 0
        tblName = ""

        arcpy.SetProgressor("step", "Importing attribute tables... ", 0, len(tblList), 1)
        #PrintMsg(" \nProcessing these tables: " + ", ".join(tblList), 1)

        for tblName in tblList:
            # Import data for each table
            #
            outputTbl = os.path.join(newGDB, tblName)  # gSTURGO database table
            inputTbl = os.path.join(inputMDB, tblName) # gSSURGO database table

            if arcpy.Exists(inputTbl):

                #PrintMsg(" \n" + tblName + " (" + Number_Format(len(keys), 0, True) + " " + keyField + " values)", 1)
                #PrintMsg(wc, 0)

                # Problem with order? I don't think cokey query is being used for COMONTH table
                recCnt = int(arcpy.GetCount_management(inputTbl).getOutput(0))
                
                if recCnt == 0:
                    if tblName == "mapunit":
                        raise MyError, " Input table " + tblName + " is not populated"
                    
                    else:
                        PrintMsg("\tInput table " + tblName + " is not populated", 1)
                        tmpTbl = ""  # initialize this variable so that the del at the end won't fail.
                    
                else:
                    # Import this table
                    #
                    tmpTbl = "TempTable"
                    #PrintMsg("\tImporting " + tblName + "...", 0)

                    fieldNames = [fld.name for fld in arcpy.Describe(inputTbl).fields]  # get list of fields from MDB (no OBJECTID)
                    tblCnt += 1
                    # PrintMsg("\t" + str(tblCnt) + ". " + tblName + ": primary key: " + fieldNames[-1] + ", foreign key: " + fieldNames[-2], 1)
                    #PrintMsg(" \nprimaryKeys: " + ", ".join(primaryKeys.keys()), 1)
                    
                    #PrintMsg(" \nUsing query: " + wc, 1)
                    # PrintMsg(" \nprimaryKeys items: " + str(primaryKeys.keys()), 1)
                    #if fieldName != "":
                    #    PrintMsg("\t\tQuery for " + tblName + " uses " + fieldName + " and " + Number_Format(len(keys), 0, True) + " key values", 1)

                    #else:
                    #    PrintMsg("\t\tNo Query for " + tblName, 1)

                        
                    arcpy.MakeQueryTable_management(inputTbl, tmpTbl, "ADD_VIRTUAL_KEY_FIELD")


                    # Need to split up very large queries
                    # Begin by clearing selection (is this really necessary?)
                    # arcpy.SelectLayerByAttribute_management(tmpTbl, "CLEAR_SELECTION")

                    if tblName == "mapunit":
                        keys = primaryKeys["mukey"]
                        fieldName = "mukey"

                    else:

                        if fieldNames[-2] in primaryKeys:
                            # use list of primary key values to build query
                            keys = primaryKeys[fieldNames[-2]]
                            fieldName = fieldNames[-2]
                            
                            #if len(keys) > 1:
                            #    wc = fieldNames[-2] + " IN "

                            #else:
                            #    wc = fieldNames[-2] + " = '"

                        elif fieldNames[-1] in primaryKeys:
                            # use list of foreign key values to build query
                            keys = primaryKeys[fieldNames[-1]]
                            fieldName = fieldNames[-1]

                        else:
                            recCnt = int(arcpy.GetCount_management(tmpTbl).getOutput(0))
                            PrintMsg("\tImporting all " + Number_Format(recCnt, 0, True) + " records for " + tblName, 1)
                            wc = ""
                            fieldName = ""
                            keys = []

                    # Split the list of key values into bite-sized chunks
                    if len(keys) > 0:
                        n = 1000
                        keyList = [keys[i:i + n] for i in xrange(0, len(keys), n)]

                    else:
                        keyList = [[]]
                        arcpy.SelectLayerByAttribute_management(tmpTbl, "ADD_TO_SELECTION", wc)
                        recCnt = int(arcpy.GetCount_management(tmpTbl).getOutput(0))
                            
                    # LOOP QUERIES HERE TO HANDLE VERY LONG QUERY STRINGS (PRIMARILY CONUS PROBLEM)
                    for keys in keyList:

                        if len(keys) > 1:
                            wc = fieldName + " IN " + str(tuple(keys))
                            #PrintMsg("\t\tnumber of keys: " + str(len(keys)), 1)

                        elif len(keys) == 1:
                            #wc = fieldNames[-1] + " = '" + keys[0] + "'"
                            wc = fieldName + " = '"  + keys[0] + "'"
                            #PrintMsg("\t\tnumber of keys: " + str(len(keys)), 1)

                        else:
                            wc = ""
                            #PrintMsg("\t\tnumber of keys: " + str(len(keys)), 1)

                        try:
                            arcpy.SelectLayerByAttribute_management(tmpTbl, "ADD_TO_SELECTION", wc)

                        except:
                            raise MyError, "\t\tBad query: " + wc

                    recCnt = int(arcpy.GetCount_management(tmpTbl).getOutput(0))

                    if recCnt > 0:
                        # Skip importing this table if the query failed to select anything
                        # PrintMsg("Selected " + Number_Format(recCnt, 0, True) + " records in " + tblName, 1)
                        arcpy.SetProgressorLabel("Importing " + tblName + "  (" + Number_Format(recCnt, 0, True) + " records)...")
                        arcpy.SetProgressorPosition()
                        sdvCur = arcpy.da.SearchCursor(tmpTbl, fieldNames)
                        outCur = arcpy.da.InsertCursor(outputTbl, fieldNames)
                        iCnt = 0

                        if (fieldNames[-1].endswith("key") and not fieldNames[-1] in primaryKeys) and (fieldNames[-2].endswith("key") and not fieldNames[-2] in primaryKeys):
                            pKeyValues = list()
                            fKeyValues = list()
                            #PrintMsg(" \nAdding key values for " + fieldNames[-2] + " and " + fieldNames[-1], 1)

                            for rec in sdvCur:
                                fKeyValues.append(rec[-2].encode('ascii'))  # fKey
                                pKeyValues.append(rec[-1].encode('ascii'))  # pKey
                                outCur.insertRow(rec)
                                iCnt += 1

                            if len(fKeyValues) > 0 or len(pKeyValues) > 0:
                                
                                if len(fKeyValues) > 0:
                                    fKeyValues = list(set(fKeyValues))
                                    #PrintMsg("\tSaving foreign key (" + fieldNames[-2] + " - " + Number_Format(len(fKeyValues), 0, True) + " values) from " + tblName, 0)
                                    primaryKeys[str(fieldNames[-2])] = fKeyValues

                                if len(pKeyValues) > 0:
                                    pKeyValues = list(set(pKeyValues))
                                    #PrintMsg("\tSaving primary key (" + fieldNames[-1] + " - " + Number_Format(len(pKeyValues), 0, True) + " values) from " + tblName, 0)
                                    primaryKeys[str(fieldNames[-1])] = pKeyValues
                                
                            else:
                                PrintMsg(" \nNo keyValues found for " + tblName + ": " + primKey, 1)

                        elif fieldNames[-2].endswith("key") and not fieldNames[-2] in primaryKeys:
                            keyValues = list()

                            for rec in sdvCur:
                                keyValues.append(rec[-2].encode('ascii'))
                                outCur.insertRow(rec)
                                iCnt += 1
                                #PrintMsg("\ta. " + str(rec), 1)

                            if len(keyValues) > 0:
                                #PrintMsg("\t1. Saving foreign key (" + fieldNames[-2] + " - " + Number_Format(len(keyValues), 0, True) + " values) from " + tblName, 0)
                                keyValues = list(set(keyValues))
                                primaryKeys[str(fieldNames[-2])] = keyValues
                                
                            else:
                                PrintMsg(" \nNo " + fieldNames[-2] + " key values found for " + tblName, 1)

                        elif not fieldNames[-1] in primaryKeys:
                            keyValues = list()

                            for rec in sdvCur:
                                keyValues.append(rec[-1].encode('ascii'))
                                outCur.insertRow(rec)
                                iCnt += 1
                                #PrintMsg("\ta. " + str(rec), 1)

                            if len(keyValues) > 0:
                                keyValues = list(set(keyValues))
                                #PrintMsg("\t1. Saving primary key (" + fieldNames[-1] + " " + Number_Format(len(keyValues), 0, True) + " values) from " + tblName + " values", 0)
                                primaryKeys[str(fieldNames[-1])] = keyValues
                                
                            else:
                                PrintMsg(" \nNo " + fieldNames[-2] + " key values found for " + tblName, 1)

                        else:
                            for rec in sdvCur:
                                outCur.insertRow(rec)
                                iCnt += 1
                                #PrintMsg("\tb. " + str(rec), 1)

                        PrintMsg("\tImported " + Number_Format(iCnt, 0, True) + " records to " + tblName, 1)
                        del sdvCur, outCur, tmpTbl
                        #PrintMsg("\t" +  Number_Format(iCnt, 0, True) + " written records", 1)

                    else:
                        PrintMsg(" \nQuery returned no records for " + tblName, 1)
                        PrintMsg(" \n" + wc, 1)
                        #raise MyError, "Query failed. Nothing selected for " + tblName
                        del tmpTbl


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
def GetClipPolygons(fcName, newGDB, inputMDB, newMukeys, inputRaster):
    #

    try:
        """
        # Get dominant component by comppct_r and join to component table
        component.compkind <>'Miscellaneous area' AND DominantComponent.OBJECTID is not null
        AND
        hzdept_r = 0 AND (om_r is null or awc_r is null)
        """

        # Get list of NOTCOM, NOTPUB and Denied Access map unit keys
        env.workspace = newGDB
        mapunitTbl = os.path.join(newGDB, "mapunit")
        compTbl = os.path.join(newGDB, "component")
        hzTbl = os.path.join(newGDB, "chorizon")
        
        mukeyList = list()  # list of mukeys for those gSSURGO mapunit polygons that need to be replaced by STATSGO

        wc = "musym IN ('NOTCOM', 'NOTPUB') OR (UPPER(muname) LIKE '%DENIED%' AND UPPER(muname) LIKE '%ACCESS%')"

        with arcpy.da.SearchCursor(mapunitTbl, ["mukey"], where_clause=wc) as cur:
            for rec in cur:
                mukeyList.append(rec[0].encode('ascii'))

        # Determine whether the first horizon for each component has data
        sqlClause = (None, "ORDER BY cokey")
        whereClause = "hzdept_r = 0 AND (om_r IS NULL OR awc_r IS NULL)"
        dComponents = dict()

        with arcpy.da.SearchCursor(hzTbl, ["cokey"], sql_clause=sqlClause, where_clause=whereClause) as cur:
            for rec in cur:
                dComponents[rec[0]] = 1

        # Find the dominant component based upon comppct_r and add to the list
        sqlClause = (None, "ORDER BY mukey, comppct_r DESC, cokey")
        lastKey = "xxxxxx"
        
        with arcpy.da.SearchCursor(compTbl, ["mukey", "cokey", "comppct_r", "compkind"], sql_clause=sqlClause) as cur:
            for rec in cur:
                mukey, cokey, comppct, compkind = rec
                
                if not mukey == lastKey:
                    # this is the dominant component
                    lastKey = mukey

                    if cokey in dComponents:
                        # this component has little or no horizon data
                        if compkind != "Miscellaneous area":
                            # Add it to the list
                            mukeyList.append(mukey.encode('ascii'))


        PrintMsg(" \nIdentified " + Number_Format(len(mukeyList), 0, True) + " map units lacking horizon data or labeled as NOTCOM...", 0)

        # Get the STATSGO soil polygon featureclass
        # Start with folder where mdb is stored
        mdbPath = os.path.dirname(inputMDB)

        if arcpy.Exists(os.path.join(mdbPath, "spatial")):
            # database is in the soil_???? folder
            shpPath = os.path.join(mdbPath, "spatial")
            #PrintMsg(" \n1. Found " + shpPath + " folder", 1)
            

        elif os.path.basename(mdbPath) == "tabular":
            # go up one directory to find spatial folder
            shpPath = os.path.join(os.path.dirname(mdbPath), "spatial")
            #PrintMsg(" \n2. Assuming " + shpPath, 1)

        else:
            # assume that mdb is in the parent directory
            shpPath = os.path.join(os.path.dirname(mdbPath), "spatial")
            #PrintMsg(" \n3. Assuming " +  shpPath, 1)

        if arcpy.Exists(shpPath):
            #PrintMsg(" \nSTATSGO Shapefile is in " + shpPath, 1)
            pass

        else:
            raise MyError, "Could not find STATSGO shapefile associated with " + inputMDB + " database"

        # find STATSGO polygon shapefile
        env.workspace = shpPath
        shpFiles = arcpy.ListFeatureClasses("gsmsoilmu_a*.shp", "POLYGON")
        #PrintMsg(" \nNeed to improve the STATSGO shapefile search method...", 1)

        if len(shpFiles) == 0:
            shpFiles = arcpy.ListFeatureClasses("soilmu_a*.shp", "POLYGON")

        if len(shpFiles) <> 1:
            raise MyError, Number_Format(len(shpFiles), 0, True) + " STATSGO polygon shapefiles were found at " + shpPath

        shpFile = shpFiles[0]
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
            PrintMsg(" \nSelected " + Number_Format(cnt, 0, True) + " associated gSSURGO polygons for replacement", 0)
            arcpy.CopyFeatures_management(inputLayer, os.path.join(newGDB, "NOTCOMS"))
            arcpy.SetProgressorLabel("Clip layer created")

            # Clip STATSGO polygons by NOTCOMs
            statsgoLayer = "STATSGO Layer"
            arcpy.MakeFeatureLayer_management(shpFile, statsgoLayer)
            newFC = os.path.join(env.scratchGDB, "STATSGO")
            arcpy.SetProgressorLabel("Clipping out replacement STATSGO polygons")
            arcpy.Clip_analysis(statsgoLayer, inputLayer, newFC)

            if arcpy.Exists(newFC):
                cnt2 = int(arcpy.GetCount_management(newFC).getOutput(0))

            else:
                raise MyError, "Failed to create clipped STATSGO polygons"

            # Delete the NOTCOM polygons from MUPOLYGON featureclass
            #PrintMsg(" \nDeleting NOTCOM polygons from output MUPOLYGON featureclass...", 1)
            arcpy.SetProgressorLabel("Deleting 'bad data' polygons")
            arcpy.DeleteFeatures_management(inputLayer)

            arcpy.Delete_management(inputLayer) # just getting rid of featurelayer
            del inputLayer

            # Append STATSGO polygons to gSSURGO MUPOLYGON
            #
            fields = arcpy.Describe(outputFC).fields
            fieldList = [fld.name.upper() for fld in fields if fld.type != "OID" and not fld.name.upper().startswith("SHAPE")]
            fieldList.insert(0, "SHAPE@")
            mukeyIndx = fieldList.index("MUKEY")
            #PrintMsg(" \nUsing fields: " + ", ".join(fieldList), 1)
            arcpy.SetProgressorLabel("Appending STATSGO replacement polygons...")

            with arcpy.da.InsertCursor(outputFC, fieldList) as outCur:  # output MUPOLYGONS
                inCur = arcpy.da.SearchCursor(newFC, fieldList)         # input STATSGO. Need to confirm that fieldLists match.
                for rec in inCur:
                    mukey = rec[mukeyIndx].encode('ascii')
                    if not mukey in newMukeys:
                        newMukeys.append(mukey)

                    outCur.insertRow(rec)


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
        PrintMsg("\tConverting replacement STATSGO polygons to a temporary raster...", 0)
        statsgoRas = os.path.join(env.scratchGDB, "statsgo_ras")
        rasDesc = arcpy.Describe(os.path.join(newGDB, inputRaster))
        iRaster = rasDesc.meanCellHeight
        rasPrj = rasDesc.spatialReference
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
        PrintMsg("\tMerging the gSSURGO and STATSGO rasters...", 0)
        arcpy.SetProgressor("default", "Merging statsgo raster with gSSURGO raster...")
        pixType = "32_BIT_UNSIGNED"
        #cellSize = 10
        nBands = 1
        mosaicMethod = "LAST"

        arcpy.MosaicToNewRaster_management([ssurgoRaster, statsgoRas], os.path.dirname(newRaster), os.path.basename(newRaster), rasPrj, pixType, iRaster, nBands, mosaicMethod)
        PrintMsg("\tBuilding attribute table for new raster", 0)
        arcpy.SetProgressor("default", "Building raster attribute table...")
        arcpy.BuildRasterAttributeTable_management(newRaster)

        with arcpy.da.UpdateCursor(newRaster, ["VALUE", "MUKEY"]) as cur:
            for rec in cur:
                rec[1] = rec[0]
                cur.updateRow(rec)

        arcpy.CalculateStatistics_management (newRaster, 1, 1, "", "OVERWRITE" )
        arcpy.SetProgressor("default", "Building pyramids for new raster...")
        PrintMsg("\tBuilding pyramids for new raster", 0)
        arcpy.BuildPyramids_management(newRaster, "-1", "NONE", "NEAREST", "DEFAULT", "", "SKIP_EXISTING")
        arcpy.ResetProgressor()

        PrintMsg("\tUpdating " + ssurgoRaster + " with STATSGO information...", 0)
        arcpy.Delete_management(ssurgoRaster)

        if not arcpy.Exists(ssurgoRaster):
            arcpy.Rename_management(newRaster, ssurgoRaster)
            #PrintMsg(" \nCompacting database...", 1)
            arcpy.SetProgressorLabel("Compacting database...")
            arcpy.Compact_management(newGDB)
            #PrintMsg(" \nFinished compacting database...", 1)

        else:
            PrintMsg("\tUnable to update " + ssurgoRaster + ", changes saved instead to " + newRaster, 1)

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
    #inputFolder = arcpy.GetParameterAsText(0)   # location of SSURGO datasets containing tabular folders
    #tabList = arcpy.GetParameter(1)             # list of SSURGO folder names to be proccessed
    #inputDB = arcpy.GetParameterAsText(2)       # custom Template SSURGO database (check version date?)
    #bImportTxt = arcpy.GetParameter(4)          # boolean. If true, import textfiles. if false, import from Access db.
    inputLayer = arcpy.GetParameterAsText(0)       # original gSSURGO database (copy will be made)
    inputRaster = arcpy.GetParameterAsText(1)    # original gSSURGO raster name. This raster will be the mosaic target in the output GDB.
    inputMDB = arcpy.GetParameterAsText(2)       # original STATSGO Template database (mdb), read only
    newGDB = arcpy.GetParameterAsText(3)         # new fullpath for output merged geodatabase


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
    bClipped = GetClipPolygons(fcName, newGDB, inputMDB, newMukeys, inputRaster)

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
