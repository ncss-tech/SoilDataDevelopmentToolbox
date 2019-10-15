# gSSURGO_KFactor.py
#
# Uses the SVI_Horizon table to calculate component-level KFactor rock free.
# Criteria:
#           Major components = 'Yes'
#           Hzdept_r is not null
#           Comppct_r > 0
#           Taxorder = 'Histosols' set KFFACT_RUSLE to '.02'
#           Taxsubgrp like 'Histic%', set KFFACT_RUSLE to '.02'
#           Skip horizons with texture of 'HPM', 'MPM' or 'SPM'. if this goes down past 25cm, set to '.02'
#
# Intermediate tables: KF_Horizons, KF_Component

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
def CreateQueryTables(inputDB, tempDB, KfHorizons):
    #
    try:

        # Problems with ArcGIS query table not getting all records where join table record is null
        env.workspace = inputDB
        env.workspace = inputDB
        queryMU = "MU"
        queryCO = "CO"
        queryHZ = "HZ"
        queryCR = "CR"
        queryCT = "CT"
        queryTemp = "Tmp"  # empty table uses as template

        # Get table record counts for status
        PrintMsg(" \nPreparing to read input tables...", 0)
        muTbl = os.path.join(inputDB, "mapunit")
        muCnt = int(arcpy.GetCount_management(muTbl).getOutput(0))
        coTbl = os.path.join(inputDB, "component")
        coCnt = int(arcpy.GetCount_management(coTbl).getOutput(0))
        hzTbl = os.path.join(inputDB, "chorizon")
        hzCnt = int(arcpy.GetCount_management(hzTbl).getOutput(0))

        # Create an empty table using the original queryHZ as a template

        # Mapunit query
        PrintMsg(" \n\tMAPUNIT table...", 0)
        arcpy.ResetProgressor()
        arcpy.SetProgressor ("step", "Getting map unit information...", 0, muCnt, 1)
        whereClause = ""
        fldMu = [["MUKEY", "MUKEY"], ["MUSYM", "MUSYM"], ["MUNAME", "MUNAME"]]
        fldMu2 = list()
        dMu = dict()
        sqlClause = (None, "ORDER BY mukey")

        for fld in fldMu:
            fldMu2.append(fld[0])

        muList = list()

        with arcpy.da.SearchCursor(muTbl, fldMu2, "", "", "", sqlClause) as mcur:
            for mrec in mcur:
                rec = list(mrec)
                mukey = int(rec[0])
                rec.pop(0)
                dMu[mukey] = rec
                muList.append(mukey)
                arcpy.SetProgressorPosition()

        muList.sort()

        # Component query
        PrintMsg(" \n\tCOMPONENT table...", 0)
        arcpy.ResetProgressor()
        arcpy.SetProgressor ("step", "Getting component information...", 0, coCnt, 1)

        fldCo = [["MUKEY", "MUKEY"], ["COKEY", "COKEY"], ["COMPPCT_R", "COMPPCT_R"], ["MAJCOMPFLAG", "MAJCOMPFLAG"], \
        ["COMPNAME", "COMPNAME"], ["COMPKIND", "COMPKIND"], ["TAXORDER", "TAXORDER"], ["TAXSUBGRP", "TAXSUBGRP"], \
        ["LOCALPHASE", "LOCALPHASE"], ["SLOPE_R", "SLOPE_R"], ["NIRRCAPCL", "NIRRCAPCL"], ["HYDGRP", "HYDGRP"], ["DRAINAGECL", "DRAINAGECL"]]
        fldCo2 = list()
        dCo = dict()
        dPct = dict()

        #whereClause = "comppct_r is not NULL and majcompflag = 'Yes'"
        whereClause = "comppct_r is not NULL"

        sqlClause = (None, "ORDER BY cokey, comppct_r DESC")

        # Note. About 2% of the component records are non-major components or 'Miscellaneous areas' and will not be processed

        for fld in fldCo:
            fldCo2.append(fld[0])

        with arcpy.da.SearchCursor(coTbl, fldCo2, whereClause, "", "", sqlClause) as ccur:
            for crec in ccur:
                rec = list(crec)
                mukey = int(rec.pop(0))  # get rid of mukey from component record
                arcpy.SetProgressorPosition()

                try:
                    # Add next component record to list
                    dCo[mukey].append(rec)
                    dPct[mukey] += rec[1]

                except:
                    # initialize list of records
                    dCo[mukey] = [rec]
                    dPct[mukey] = rec[1]

        # HORIZON TABLE
        PrintMsg(" \n\tHORIZON table...", 0)
        fldHz = [["COKEY", "COKEY"], ["CHKEY", "CHKEY"], ["HZNAME", "HZNAME"], ["DESGNMASTER", "DESGNMASTER"], \
        ["HZDEPT_R", "HZDEPT_R"], ["HZDEPB_R", "HZDEPB_R"], ["OM_R", "OM_R"], ["KFFACT", "KFFACT"]]

        fldHz2 = list()
        dHz = dict()
        whereClause = "hzdept_r is not NULL and hzdepb_r is not NULL"
        sqlClause = (None, "ORDER BY chkey, hzdept_r ASC")

        for fld in fldHz:
            fldHz2.append(fld[0])

        arcpy.ResetProgressor()
        arcpy.SetProgressor ("step", "Getting horizon information...", 0, hzCnt, 1)

        with arcpy.da.SearchCursor(hzTbl, fldHz2, whereClause, "", "", sqlClause) as hcur:
            for hrec in hcur:
                rec = list(hrec)
                cokey = int(rec.pop(0))
                arcpy.SetProgressorPosition()

                try:
                    # Add next horizon record to list
                    dHz[cokey].append(rec)

                except:
                    # initialize list of horizon records
                    dHz[cokey] = [rec]


            # HORIZON TEXTURE QUERY
            #
            PrintMsg(" \n\tTEXTURE tables...", 0)
            inputTbls = list()
            tbls = ["chtexturegrp", "chtexture"]
            for tbl in tbls:
                inputTbls.append(os.path.join(inputDB, tbl))

            txList1 = [["chtexturegrp.chkey", "CHKEY"], ["chtexturegrp.texture", "TEXTURE"], ["chtexture.lieutex", "LIEUTEX"]]
            whereClause = "chtexturegrp.chtgkey = chtexture.chtgkey and chtexturegrp.rvindicator = 'Yes'"
            arcpy.ResetProgressor()
            arcpy.SetProgressorLabel("Reading horizon texture tables...")
            arcpy.MakeQueryTable_management(inputTbls, queryCT, "USE_KEY_FIELDS", "#", txList1, whereClause)
            ctCnt = int(arcpy.GetCount_management(queryCT).getOutput(0))
            arcpy.SetProgressor ("step", "Saving horizon texture information...", 0, ctCnt, 1)

            # Read texture query into dictionary
            txList2 = ["chtexturegrp.chkey", "chtexturegrp.texture", "chtexture.lieutex"]
            dTexture = dict()

            with arcpy.da.SearchCursor(queryCT, txList2) as cur:
                for rec in cur:
                    dTexture[int(rec[0])] = [rec[1], rec[2]]
                    arcpy.SetProgressorPosition()

            arcpy.Delete_management(queryCT)

        fldCo.pop(0)
        fldCo2.pop(0)
        fldHz.pop(0)
        fldHz2.pop(0)

        # Create list of fields for query table
        fldAll = list()
        # Create list of fields for output cursor
        fldAll2 = list()

        for fld in fldMu:
            fldAll.append(["mapunit." + fld[0], fld[1]])
            fldAll2.append(fld[1])

        for fld in fldCo:
            fldAll.append(["component." + fld[0], fld[1]])
            fldAll2.append(fld[1])

        for fld in fldHz:
            fldAll.append(["chorizon." + fld[0], fld[1]])
            fldAll2.append(fld[1])

        # Texture fields:
        fldAll2.append("texture")
        fldAll2.append("lieutex")

        # Create initial table containing component-horizon data for ALL components that have
        # horizon data. Lack of horizon data will cause some components to be missing from the output
        #
        whereClause = "mapunit.objectid = 1 and mapunit.mukey = component.mukey and component.cokey = chorizon.cokey"

        PrintMsg(" \nJoining tables...", 0)
        arcpy.MakeQueryTable_management([os.path.join(inputDB, 'mapunit'), os.path.join(inputDB, 'component'), os.path.join(inputDB, 'chorizon')], queryTemp, "USE_KEY_FIELDS", "#", fldAll, whereClause)
        arcpy.CreateTable_management(os.path.dirname(KfHorizons), os.path.basename(KfHorizons), queryTemp)
        arcpy.AddField_management(KfHorizons, "TEXTURE", "TEXT", "", "", "30", "Texture")
        arcpy.AddField_management(KfHorizons, "LIEUTEX", "TEXT", "", "", "254", "Lieutex")
        arcpy.AddField_management(KfHorizons, "KFFACT_RUSLE", "TEXT", "", "", "5", "KFactorTop")
        arcpy.Delete_management(queryTemp)
        arcpy.AlterField_management (KfHorizons, "CHKEY", "CHKEY", field_is_nullable="NULLABLE")

        # Process dictionaries and use them to write out the new SVI_Query table
        #
        # Open output table
        outFld2 = arcpy.Describe(KfHorizons).fields
        outFlds = list()
        for fld in outFld2:
            outFlds.append(fld.name)

        outFlds.pop(0)

        # Create lists of null values to replace missing data at the component, horizon or texture levels
        missingCo = ["", None, None, None, None, None, None, None, None, None, None, None, None]   # 13 values with drainagecl
        #missingHz = ["", None, None, None, None, None, None, None]
        missingHz = ["", None, None, None, None, None]
        missingTx = [None, None]

        # Save information on mapunits or components with bad or missing data
        muNoCo = list()
        dNoCo = dict()

        coNoHz = list()  # list of components with no horizons
        dNoHz = dict() # component data for those components in coNoHz

        arcpy.SetProgressor ("step", "Writing data to " + KfHorizons + "...", 0, len(muList), 1)

        #PrintMsg(" \nOutput record should have " + str(len(fldAll2)) + " records", 1)
        #PrintMsg("\t" + ", ".join(fldAll2), 1)

        with arcpy.da.InsertCursor(KfHorizons, fldAll2) as ocur:

            for mukey in muList:
                mrec = dMu[mukey]
                arcpy.SetProgressorPosition()

                try:
                    coVals = dCo[mukey]  # got component records for this mapunit

                    # Sort lists by comppct_r
                    coList = sorted(coVals, key = lambda x: int(x[1]))

                    for corec in coList:
                        cokey = int(corec[0])

                        try:
                            hzVals = dHz[cokey]  # horizon records for this component
                            # Sort record by hzdept_r
                            hzList = sorted(hzVals, key = lambda x: int(x[3]))

                            for hzrec in hzList:
                                chkey = int(hzrec[0])

                                try:
                                    # Get horizon texture
                                    txrec = dTexture[chkey]

                                except:
                                    txrec = missingTx

                                # Combine all records and write to table
                                newrec = [mukey]
                                newrec.extend(mrec)
                                newrec.extend(corec)
                                newrec.extend(hzrec)
                                newrec.extend(txrec)
                                ocur.insertRow(newrec)

                        except KeyError:
                            # No horizon records for this component
                            comppct = corec[1]
                            mjrcomp = corec[2]
                            compname = corec[3]
                            compkind = corec[4]
                            hzrec = missingHz
                            txrec = missingTx
                            newrec = [mukey]
                            newrec.extend(mrec)
                            newrec.extend(corec)
                            newrec.extend(hzrec)
                            newrec.extend(txrec)
                            ocur.insertRow(newrec)

                        except:
                            PrintMsg(" \nhzVals error for " + str(mukey) + ":" + str(cokey) + ": " + str(txrec), 2)
                            PrintMsg(" \n" + str(fldAll2), 1)
                            errorMsg()

                except:
                    # No component records for this map unit
                    corec = missingCo
                    hzrec = missingHz
                    txrec = missingTx
                    newrec = [mukey]
                    newrec.extend(mrec)
                    newrec.extend(corec)
                    newrec.extend(hzrec)
                    newrec.extend(txrec)
                    #PrintMsg(" \n" + KfHorizons + ": list length: " + str(len(newrec)) + "; cursor length: " + str(len(fldAll2)), 1)
                    ocur.insertRow(newrec)


        # Check sum of comppct_r for each map unit
        overList = list()

        for mukey, comppct in dPct.items():
            if comppct != 100:
                #PrintMsg("\tMukey " + str(mukey) + " has a component percentage of " + str(comppct), 1)
                overList.append(str(mukey))

        if len(overList) > 0:
            PrintMsg(" \nDiscovered " + Number_Format(len(overList), 0, True) + " map units have components whose sum is <> 100%", 1)
            #PrintMsg(" \nThe following map unit (mukeys) have sum comppct_r <> 0: " + ", ".join(overList), 1)

        del muTbl, coTbl, hzTbl, KfHorizons
        env.workspace = inputDB
        return dPct

    except MyError, e:
        # Example: raise MyError("this is an error message")

        PrintMsg(str(e) + " \n", 2)
        return {}

    except:
        errorMsg()
        return {}

## ===================================================================================
def CreateOutputTableCo(sviTop):
    # Create the component level table (SVI_Top)
    #
    try:
        # Create two output tables and add required fields
        try:
            # Try to handle existing output table if user has added it to ArcMap from a previous run
            if arcpy.Exists(sviTop):
                arcpy.Delete_management(sviTop)

        except:
            raise MyError, "Previous output table (" + sviTop + ") is in use and cannot be removed"
            return False

        PrintMsg(" \nCreating new output table (" + os.path.basename(sviTop) + ") for component level data", 0)

        outputDB = os.path.dirname(sviTop)
        #sviTop = os.path.join("IN_MEMORY", os.path.basename(sviTop))
        tmpTable = sviTop

        arcpy.CreateTable_management(os.path.dirname(sviTop), os.path.basename(sviTop))

        # Add fields appropriate for the component level restrictions
        arcpy.AddField_management(sviTop, "COKEY", "TEXT", "", "", 30, "Cokey")
        arcpy.AddField_management(sviTop, "MUSYM", "TEXT", "", "", 7, "Musym")
        arcpy.AddField_management(sviTop, "MUNAME", "TEXT", "", "", 240, "Mapunit_Name")
        arcpy.AddField_management(sviTop, "COMPNAME", "TEXT", "", "", 60, "Component_Name")
        arcpy.AddField_management(sviTop, "COMPKIND", "TEXT", "", "", 60, "Component_Kind")
        arcpy.AddField_management(sviTop, "MAJCOMPFLAG", "TEXT", "", "", 3, "Major_Component")
        arcpy.AddField_management(sviTop, "LOCALPHASE", "TEXT", "", "", 40, "Local_Phase")
        arcpy.AddField_management(sviTop, "COMPPCT_R", "SHORT", "", "", "", "Component_Pct")
        arcpy.AddField_management(sviTop, "SLOPE_R", "FLOAT", "", "", "", "Slope")
        arcpy.AddField_management(sviTop, "TAXORDER", "TEXT", "", "", 60, "Taxonomic_Order")
        arcpy.AddField_management(sviTop, "TAXSUBGRP", "TEXT", "", "", 60, "Taxonomic_SubGroup")
        arcpy.AddField_management(sviTop, "NIRRCAPCL", "TEXT", "", "", 4, "NonIrr_Capability_Class ")
        arcpy.AddField_management(sviTop, "HYDGRP", "TEXT", "", "", 12, "Hydrologic_Group")
        arcpy.AddField_management(sviTop, "CHKEY", "TEXT", "", "", 30, "Chkey", field_is_nullable="NULLABLE")
        arcpy.AddField_management(sviTop, "HZNAME", "TEXT", "", "", 12, "Horizon Name")
        arcpy.AddField_management(sviTop, "DESGNMASTER", "TEXT", "", "", 254, "Horizon")
        arcpy.AddField_management(sviTop, "HZDEPT_R", "SHORT", "", "", "", "Top_Depth")
        arcpy.AddField_management(sviTop, "HZDEPB_R", "SHORT", "", "", "", "Bottom_Depth")
        arcpy.AddField_management(sviTop, "OM_R", "FLOAT", "", "", "", "Organic_Matter")
        arcpy.AddField_management(sviTop, "TEXTURE", "TEXT", "", "", 60, "Texture")
        arcpy.AddField_management(sviTop, "LIEUTEX", "TEXT", "", "", 60, "InLieu_Texture")
        arcpy.AddField_management(sviTop, "KFFACT", "TEXT", "", "", 5, "KFactor_Rockfree")
        #arcpy.AddField_management(sviTop, "ROCKFRAG", "FLOAT", "", "", "", "Rock Frag Vol")
        #arcpy.AddField_management(sviTop, "SIEVENO10_R", "FLOAT", "", "", "", "Rock Frag Vol")
        arcpy.AddField_management(sviTop, "DRAINAGECL", "TEXT", "", "", 254, "Drainage Class")
        arcpy.AddField_management(sviTop, "KFFACT_RUSLE", "TEXT", "", "", 5, "KFactor RUSLE")

        # Add primary key field
        arcpy.AddField_management(sviTop, "MUKEY", "TEXT", "", "", 30, "Mukey")

        # Add a status flag to mark the top mineral horizons for each component
        #arcpy.AddField_management(sviTop, "TOP_MINERAL", "SHORT")

        # Convert IN_MEMORY table to a permanent table
        # arcpy.CreateTable_management(outputDB, os.path.basename(sviTop), sviTop)

        # add attribute indexes for key fields
        arcpy.AddIndex_management(sviTop, "MUKEY", "Indx_Res2Mukey", "UNIQUE", "NON_ASCENDING")
        arcpy.AddIndex_management(sviTop, "COKEY", "Indx_ResCokey", "UNIQUE", "NON_ASCENDING")

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def SortData(muVals, a, b, sortA, sortB):
    # Input muVals is a list of lists to be sorted. Each list must have contain at least two items.
    # Input 'a' is the first item index in the sort order (integer)
    # Item 'b' is the second item index in the sort order (integer)
    # Item sortA is a bookean for reverse sort
    # Item sortB is a boolean for reverse sort
    # Perform a 2-level sort by then by item i, then by item j.
    # Return a single list

    try:
        #PrintMsg(" \nmuVals: " + str(muVals), 1)

        if len(muVals) > 0:
            muVal = sorted(sorted(muVals, key = lambda x : x[b], reverse=sortB), key = lambda x : x[a], reverse=sortA)[0]

        else:
            muVal = muVals[0]

        #PrintMsg(str(muVal) + " <- " + str(muVals), 1)

        return muVal

    except:
        errorMsg()
        return (None, None)
    
## ===================================================================================
def AggregateCo_DCD_Domain(gdb, sdvFld, initialTbl, bNulls, cutOff, tblName):
    #
    # Flooding or ponding frequency, dominant condition
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition.
    # Use domain values to determine sort order for tiebreaker
    #

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        bVerbose = False

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        # Check input table fields
        initialFlds = [fld.name.upper() for fld in arcpy.Describe(initialTbl).fields]

        inFlds = ["MUKEY", "COKEY", "COMPPCT_R", "KFFACT_RUSLE"]

        for fld in inFlds:
            if not fld in initialFlds:
                PrintMsg(" \n" + initialTbl + " is missing field: " + fld, 1)
                
        

        # Default setting is to include Null values as part of the aggregation process
        if bNulls:
            #PrintMsg(" \nIncluding components with null rating values...", 1)
            whereClause = "COMPPCT_R >=  " + str(cutOff)

        else:
            #PrintMsg(" \nSkipping components with null rating values...", 1)
            whereClause = "COMPPCT_R >=  " + str(cutOff) + " AND KFFACT_RUSLE IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY MUKEY ASC, COMPPCT_R DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        #arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl), initialTbl)
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))  # Just the basic 3 fields in this version
        arcpy.AddField_management(outputTbl, "MUKEY", "TEXT", "", "", 30, "Mukey")
        arcpy.AddField_management(outputTbl, "COMPPCT_R", "SHORT", "", "", "", "Component_Pct")
        arcpy.AddField_management(outputTbl, "KFFACT_RUSLE", "TEXT", "", "", 5, "KFactor RUSLE")
        

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dCase = dict()

        # PrintMsg(" \ntiebreakdomainname: " + str(dSDV["tiebreakdomainname"]), 1)

        # Read initial table for non-numeric data types. Capture domain values and all component ratings.
        #
        if bVerbose:
            PrintMsg(" \nReading initial data...", 1)
            PrintMsg(whereClause, 1)

        #
        # if dSDV["tiebreakdomainname"] is not None:  # this is a test to see if there are true domain values
        # Use this to compare dValues to output values
        #
        domainValues = ['.02', '.05', '.10', '.15', '.17', '.20', '.24', '.28', '.32', '.37', '.43', '.49', '.55', '.64' , None]

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            for rec in cur:
                mukey, cokey, compPct, rating = rec

                # save list of components for each mapunit
                try:
                    dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                # this is a new component record. create a new dictionary item.
                #
                if not cokey in dComp:
                    #dCase[str(rating).upper()] = rating

                    #dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                    dComp[cokey] = domainValues.index(rating)
                    dCompPct[cokey] = compPct

                    # compare actual rating value to domainValues to make sure case is correct
                    if not rating in domainValues: # this is a case problem
                        # replace the original dValue item
                        dValues[str(rating).upper()][1] = rating

                        # replace the value in domainValues list
                        for i in range(len(domainValues)):
                            if str(domainValues[i]).upper() == str(rating).upper():
                                domainValues[i] = rating

        del cur

        PrintMsg(" \nPopulating output table: " + outputTbl + " \n ", 1)
        outFlds = ["MUKEY", "COMPPCT_R", "KFFACT_RUSLE"]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            for mukey, cokeys in dMapunit.items():
                dRating = dict()  # save sum of comppct for each rating within a mapunit
                muVals = list()   # may not need this for DCD

                for cokey in cokeys:
                    try:
                        #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                        compPct = dCompPct[cokey]
                        ratingIndx = dComp[cokey]

                        if ratingIndx in dRating:
                            sumPct = dRating[ratingIndx] + compPct
                            dRating[ratingIndx] = sumPct  # this part could be compacted

                        else:
                            dRating[ratingIndx] = compPct

                    except:
                        pass

                for ratingIndx, compPct in dRating.items():
                    muVals.append([compPct, ratingIndx])  # This muVal is not being populated

                #This is the final aggregation from component to map unit rating

                #PrintMsg("\t" + str(dRating), 1)
                if len(muVals) > 0:
                    muVal = SortData(muVals, 0, 1, True, True)
                    compPct, ratingIndx = muVal
                    rating = domainValues[ratingIndx]

                else:
                    rating = None
                    compPct = None

                #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                newrec = [mukey, compPct, rating]

                ocur.insertRow(newrec)

        # Add attribute indexes for mukey and perhaps kffact_rusle
        arcpy.AddIndex_management(outputTbl, "MUKEY", "Indx_" + os.path.basename(outputTbl) + "_MUKEY", "UNIQUE", "NON_ASCENDING")
        arcpy.AddIndex_management(outputTbl, "KFFACT_RUSLE", "Indx_" + os.path.basename(outputTbl) + "_KFFACT_RUSLE", "UNIQUE", "NON_ASCENDING")

        
        return outputTbl

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl

    except:
        errorMsg()
        return outputTbl

## ===================================================================================
def CreateMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile):
    # Setup new K Factor map layer with appropriate symbology and add it to the table of contents.

    try:
        # bVerbose = True
        msg = "Preparing soil map layer..."
        arcpy.SetProgressorLabel(msg)
        PrintMsg("\t" + msg, 0)

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        hasJoin = False
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame

        envUser = arcpy.GetSystemEnvironment("USERNAME")
        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = envUser.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser

        # Get today's date
        d = datetime.date.today()
        toDay = d.isoformat()
        #today = datetime.date.today().isoformat()

        parameterString = "KFactor rockfree (DCD) for top mineral soil horizon\r\nGeoDatabase: " + os.path.dirname(fc) + "\r\n" + muDesc.dataType.title() + ": " + \
        os.path.basename(fc) + "\r\nRating Table: " + os.path.basename(outputTbl) + \
        "\r\nLayer File: " + outputLayerFile

        creditsString = "\r\nCreated by " + userName + " on " + toDay + " using script " + os.path.basename(sys.argv[0])

        

        # Create initial map layer using MakeQueryTable. Need to add code to make
        # sure that a join doesn't already exist, thus changind field names
        tableList = [inputLayer, outputTbl]
        joinSQL = os.path.basename(fc) + '.MUKEY = ' + os.path.basename(outputTbl) + '.MUKEY'

        # Create fieldInfo string
        dupFields = list()
        keyField = os.path.basename(fc) + ".OBJECTID"
        fieldInfo = list()
        sFields = ""

        # first get list of fields from mupolygon layer
        for fld in muDesc.fields:
            dupFields.append(fld.baseName)
            fieldInfo.append([os.path.basename(fc) + "." + fld.name, ''])

            if sFields == "":
                sFields = os.path.basename(fc) + "." + fld.name + " " + fld.baseName + " VISIBLE; "
            else:
                sFields = sFields + os.path.basename(fc) + "." + fld.name + " " + fld.baseName + " VISIBLE; "

        # then get non-duplicate fields from output table
        tblDesc = arcpy.Describe(outputTbl)
        
        for fld in tblDesc.fields:
            if not fld.baseName in dupFields:
                dupFields.append(fld.baseName)
                fieldInfo.append([os.path.basename(outputTbl) + "." + fld.name, ''])
                sFields = sFields + os.path.basename(outputTbl) + "." + fld.name + " " + fld.baseName + " VISIBLE; "
                #PrintMsg("\tAdding output table field '" + fld.baseName + "' to field info", 1)

            else:
                # Use this next line for MakeFeatureLayer field info string
                sFields = sFields + os.path.basename(outputTbl) + "." + fld.name + " " + fld.baseName + " HIDDEN; "

        # Alternative is to use MakeFeatureLayer to create initial layer with join
        # PrintMsg(" \nJoining " + inputLayer + " with " + outputTbl + " to create " + outputLayer, 1)
        arcpy.AddJoin_management (inputLayer, "MUKEY", outputTbl, "MUKEY", "KEEP_ALL")
        hasJoin = True
        arcpy.MakeFeatureLayer_management(inputLayer, outputLayer, "", "", sFields)

        sdvLyrFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_PolygonKFactor.lyr")
        #arcpy.ApplySymbologyFromLayer_management(outputLayer, sdvLyrFile)
        #

        #symLayer = arcpy.mapping.Layer(sdvLyrFile)

        if bVerbose:
            PrintMsg(" \nCreating symLayer using SDV symbology from '" + sdvLyrFile + "'", 1)

        if arcpy.Exists(outputLayer):
            
            fDesc = arcpy.Describe(outputLayer)
            arcpy.SetParameter(1, fDesc.nameString)
            PrintMsg(" \noutputLayer data type: " + fDesc.dataType, 1)
            fFields = fDesc.fields
            outputFields = [fld.name for fld in fFields]  # assuming last field is rating 
            PrintMsg(" \noutputFields: " + ", ".join(outputFields), 1)

            if arcpy.Exists(outputLayerFile):
                arcpy.Delete_management(outputLayerFile)

            #if bVerbose:
            PrintMsg(" \nSaving map layer '" + outputLayer + "' to " + outputLayerFile, 1)

            arcpy.SaveToLayerFile_management(outputLayer, outputLayerFile, "ABSOLUTE")

            try:
                arcpy.Delete_management(outputLayer)

            except:
                PrintMsg(" \nFailed to remove " + outputLayer, 1)

            if bVerbose:
                PrintMsg(" \nSaved map to layerfile: " + outputLayerFile, 0)

        else:
            raise MyError, "\tFailed to create temporary layer: " + outputLayer + " from " + inputLayer


        # Remove join on original map unit polygon layer
        arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))


        finalMapLayer = arcpy.mapping.Layer(outputLayerFile)  # recreate the outputlayer
        #arcpy.mapping.UpdateLayer(df, finalMapLayer, symLayer, True)
        arcpy.ApplySymbologyFromLayer_management(finalMapLayer, sdvLyrFile)
        finalMapLayer.symbology.valueField = os.path.basename(outputTbl) + "." + outputFields[-1]

        if finalMapLayer.symbologyType.upper() == 'UNIQUE_VALUES':

            #PrintMsg(" \nRating field: " +os.path.basename(outputTbl) + "." + outputFields[-1] , 1)
            finalMapLayer.symbology.valueField = os.path.basename(outputTbl) + "." + outputFields[-1]

        

        #arcpy.SetParameter(1, finalMapLayer)
        # Add layer file path to layer description property
        # parameterString = parameterString + "\r\n" + "LayerFile: " + outputLayerFile

        envUser = arcpy.GetSystemEnvironment("USERNAME")
        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = envUser.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser

        kfDescription = """Erosion factor K indicates the susceptibility of a soil to sheet and rill erosion by water. Factor K is one of six factors used in the Universal Soil Loss Equation (USLE) and the Revised Universal Soil Loss Equation (RUSLE) to predict the average annual rate of soil loss by sheet and rill erosion in tons per acre per year. The estimates are based primarily on percentage of silt, sand, and organic matter and on soil structure and saturated hydraulic conductivity (Ksat). Values of K range from 0.02 to 0.69. Other factors being equal, the higher the value, the more susceptible the soil is to sheet and rill erosion by water.

"Erosion factor Kf (rock free)" indicates the erodibility of the fine-earth fraction, or the material less than 2 millimeters in size.
"""
        finalMapLayer.description = kfDescription + "\r\n\r\n" + parameterString
        finalMapLayer.credits = creditsString
        finalMapLayer.visible = False
        arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
        arcpy.RefreshTOC()
        arcpy.SaveToLayerFile_management(finalMapLayer.name, outputLayerFile, "RELATIVE", "10.3")

        if __name__ == "__main__":
            PrintMsg("\tSaved map to layer file: " + outputLayerFile + " \n ", 0)

        else:
            PrintMsg("\tSaved map to layer file: " + outputLayerFile, 0)

        del mxd, df

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        try:
            if hasJoin:
            #    PrintMsg("\tRemoving join", 1)
                arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))

        except:
            pass

        return False

    except:
        errorMsg()
        try:
            if hasJoin:
                arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))

        except:
            pass
        
        return False

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time

# Create the environment
from arcpy import env

try:
    bVerbose = False
    
    #
    inputLayer = arcpy.GetParameter(0)          # only allow featurelayer (soil polygons)
    outputLayer = arcpy.GetParameter(1)
    muDesc = arcpy.Describe(inputLayer)

    if muDesc.dataType.upper() == "FEATURELAYER":
        fc = muDesc.featureClass.catalogPath

    elif muDesc.dataType.upper() == "FEATURECLASS":
        fc = inputLayer

    inputDB = os.path.dirname(fc)
    env.overwriteOutput = True

    # Check the outputLayer. Having problems.
    fDesc = arcpy.Describe(outputLayer)
    fType = fDesc.dataType
    PrintMsg(" \nOutputLayer (" + fDesc.nameString + "): " + fType, 1)

    # Set output workspace to same as the input table
    env.workspace = inputDB
    env.overwriteOutput = True
    KfComp = os.path.join(inputDB, "KF_Component")
    KfHorizons = os.path.join(env.scratchGDB, "KF_Horizons")

    # Clean up previous runs
    dPct = CreateQueryTables(inputDB, env.scratchGDB, KfHorizons)

    if len(dPct):
        # Query tables were created and dPct was populated with total comppct_r for each map unit

        if not CreateOutputTableCo(KfComp):
            raise MyError, ""

    lastKey = "xxxxx"
    flds = arcpy.Describe(KfHorizons).fields
    fldList = [fld.name.encode('ascii') for fld in flds]
    fldList.pop(0)  # Remove objectid from list of fields
    lastKey = "xxxx"
    whereClause = "majcompflag = 'Yes' and comppct_r > 0"
    sqlClause = (None, "ORDER BY mukey, comppct_r DESC, cokey, hzdept_r ASC, kffact DESC")

    cnt = int(arcpy.GetCount_management(KfHorizons).getOutput(0))
    arcpy.SetProgressor("step", "Processing input table " + KfHorizons + "...", 1, cnt, 1)

    with arcpy.da.SearchCursor(KfHorizons, fldList, where_clause=whereClause, sql_clause=sqlClause) as inCur:

        with arcpy.da.InsertCursor(KfComp, fldList) as outCur:

            PrintMsg(" \nCreating " + KfComp, 1)
            #PrintMsg("\tLength of field list: " + str(len(fldList)), 1)
            
            for rec in inCur:
                mukey, musym, muname, cokey, comppct_r, majcompflag, compname, compkind, taxorder, taxsubgrp, localphase, slope_r, nirrcapcl, hydgrp, drainagecl, chkey, hzname, desgnmaster, hzdept_r, hzdepb_r, om_r, kffact,  texture, lieutex, kffact_rusle = rec
                s = str(texture)
                key = mukey + ":" + cokey
                arcpy.SetProgressorPosition()

                if str(taxorder) == 'Histosols' or str(taxsubgrp).startswith('Histic'):
                    # Assign '.02' to kffact per RUSLE2 standards
                    kffact_rusle = '.02'

                    if key != lastKey:
                        lastKey = key  # 
                        rec = [mukey, musym, muname, cokey, comppct_r, majcompflag, compname, compkind, taxorder, taxsubgrp, localphase, slope_r, nirrcapcl, hydgrp, drainagecl, chkey, hzname, desgnmaster, hzdept_r, hzdepb_r, om_r, kffact, texture, lieutex, kffact_rusle]
                        outCur.insertRow(rec)

                elif max((s.find("HPM"), s.find("MPM"), s.find("SPM"))) == -1:
                    # not an organic horizon
                     
                    if key != lastKey:
                        # this should be the first mineral soil for this component
                        lastKey = key


                        if hzdept_r is None:
                            kffact_rusle = None
                            
                        elif hzdept_r <= 25:
                            kffact_rusle = kffact

                        else:
                            # probably a data population error
                            kffact_rusle = ".02"
                            
                        rec = [mukey, musym, muname, cokey, comppct_r, majcompflag, compname, compkind, taxorder, taxsubgrp, localphase, slope_r, nirrcapcl, hydgrp, drainagecl, chkey, hzname, desgnmaster, hzdept_r, hzdepb_r, om_r, kffact, texture, lieutex, kffact_rusle]
                        #PrintMsg("\tLength of rec: " + str(len(rec)), 1)
                        outCur.insertRow(rec)

    # Creating Mapunit KFactor rock free; dominant condition
    bNulls = True
    sdvFld = "KFFACT_RUSLE"
    cutOff = 0
    KfMapunit = "KF_Mapunit"

    outputTbl = AggregateCo_DCD_Domain(inputDB, sdvFld, KfComp, bNulls, cutOff, KfMapunit)

    outputLayerName = "K Factor rockfree (DCD) for the top mineral horizon"
    outputLayerFile = os.path.join(os.path.dirname(inputDB), "KFFactor_RUSLE.lyr")
    PrintMsg(" \nSetting output layer file to: " + outputLayerFile, 1)

    if outputTbl != "":
        # Add KFactor map layer to display
        bMap = CreateMapLayer(inputLayer, outputTbl, fDesc.nameString, outputLayerFile)
        
        #outputLayer.name = outputLayerName
    
    
except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
