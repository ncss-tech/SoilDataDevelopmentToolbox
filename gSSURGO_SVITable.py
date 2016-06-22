# gSSURGO_SVITable.py
#
# Steve Peaslee, National Soil Survey Center
# 2015-04-29

# Adapted from gSSURGO_ValuTable.py
# Pulls SVI related data from gSSURGO database
# Only the SVI column is aggregated

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
                arcpy.AddMessage("    ")
                arcpy.AddError(string)

    except:
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        #locale.setlocale(locale.LC_ALL, "")
        locale.getlocale()

        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def CreateQueryTables(inputDB, outputDB):
    #
    try:

        # Problems with query table not getting all records where join table record is null
        # FoQueryTable_CRr instance, I appear to be missing a component record when there is no chorizon data,
        # such as for 'Miscellaneous area'
        env.workspace = inputDB
        queryMU = "MU"
        queryCO = "CO"
        queryHZ = "HZ"
        queryCR = "CR"
        queryCT = "CT"
        queryTemp = "Tmp"  # empty table uses as template

        # Create an empty table using the original queryHZ as a template

        # Mapunit query
        PrintMsg(" \nReading MAPUNIT table...", 0)
        whereClause = ""
        fldMu = [["mukey", "mukey"], ["musym", "musym"], ["muname", "muname"]]
        #arcpy.MakeQueryTable_management(["mapunit"], queryMU, "USE_KEY_FIELDS", "#", fldMu, whereClause)
        fldMu2 = list()
        dMu = dict()
        #sqlClause = (None, "ORDER BY cokey, resdept_r ASC")
        sqlClause = (None, "ORDER BY mukey")

        for fld in fldMu:
            fldMu2.append(fld[0])

        muList = list()

        #with arcpy.da.SearchCursor(queryMU, fldMu2, "", "", "", sqlClause) as mcur:
        muTbl = os.path.join(inputDB, "mapunit")

        with arcpy.da.SearchCursor(muTbl, fldMu2, "", "", "", sqlClause) as mcur:
            for mrec in mcur:
                rec = list(mrec)
                mukey = int(rec[0])
                rec.pop(0)
                dMu[mukey] = rec
                muList.append(mukey)

        muList.sort()

        # Component query
        PrintMsg(" \nReading COMPONENT table...", 0)
        fldCo = [["mukey", "mukey"], ["cokey", "cokey"], ["comppct_r", "comppct_r"], ["majcompflag", "majcompflag"], \
        ["compname", "compname"], ["compkind", "compkind"], ["taxorder", "taxorder"], ["taxsubgrp", "taxsubgrp"], \
        ["localphase", "localphase"], ["otherph", "otherph"], ["slope_r", "slope_r"], ["hydgrp", "hydgrp"]]
        fldCo2 = list()
        dCo = dict()
        whereClause = "comppct_r is not NULL"
        sqlClause = (None, "ORDER BY cokey, comppct_r DESC")
        coTbl = os.path.join(inputDB, "component")

        for fld in fldCo:
            fldCo2.append(fld[0])

        with arcpy.da.SearchCursor(coTbl, fldCo2, whereClause, "", "", sqlClause) as ccur:
            for crec in ccur:
                rec = list(crec)
                mukey = int(rec.pop(0))  # get rid of mukey from component record

                try:
                    # Add next component record to list
                    dCo[mukey].append(rec)

                except:
                    # initialize list of records
                    dCo[mukey] = [rec]

        # HORIZON TABLE
        PrintMsg(" \nReading HORIZON table...", 0)
        fldHz = [["cokey", "cokey"], ["chkey", "chkey"], ["hzname", "hzname"], ["desgnmaster", "desgnmaster"], \
        ["hzdept_r", "hzdept_r"], ["hzdepb_r", "hzdepb_r"], ["om_r", "om_r"], ["kffact", "kffact"], ["sieveno10_r", "sieveno10_r"]]
        fldHz2 = list()
        dHz = dict()
        whereClause = "hzdept_r is not NULL and hzdepb_r is not NULL"
        sqlClause = (None, "ORDER BY chkey, hzdept_r ASC")

        for fld in fldHz:
            fldHz2.append(fld[0])

        hzTbl = os.path.join(inputDB, "chorizon")

        with arcpy.da.SearchCursor(hzTbl, fldHz2, whereClause, "", "", sqlClause) as hcur:
            for hrec in hcur:
                rec = list(hrec)
                cokey = int(rec.pop(0))

                try:
                    # Add next horizon record to list
                    dHz[cokey].append(rec)

                except:
                    # initialize list of horizon records
                    dHz[cokey] = [rec]

            # HORIZON TEXTURE QUERY
            #
            PrintMsg(" \nReading TEXTURE tables...", 0)
            inputTbls = list()
            tbls = ["chtexturegrp", "chtexture"]
            for tbl in tbls:
                inputTbls.append(os.path.join(inputDB, tbl))

            txList1 = [["chtexturegrp.chkey", "chkey"], ["chtexturegrp.texture", "texture"], ["chtexture.lieutex", "lieutex"]]
            whereClause = "chtexturegrp.chtgkey = chtexture.chtgkey and chtexturegrp.rvindicator = 'Yes'"
            arcpy.MakeQueryTable_management(inputTbls, queryCT, "USE_KEY_FIELDS", "#", txList1, whereClause)

            # Read texture query into dictionary
            txList2 = ["chtexturegrp.chkey", "chtexturegrp.texture", "chtexture.lieutex"]
            dTexture = dict()
            ctCnt = int(arcpy.GetCount_management(queryCT).getOutput(0))

            arcpy.SetProgressor ("step", "Getting horizon texture information...", 0, ctCnt, 1)

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
        whereClause = "mapunit.mukey = component.mukey and component.cokey = chorizon.cokey"

        outputTable = os.path.join(outputDB, "SVI_Query")
        PrintMsg(" \nJoining tables...", 0)
        arcpy.MakeQueryTable_management(['mapunit', 'component', 'chorizon'], queryTemp, "USE_KEY_FIELDS", "#", fldAll, whereClause)
        arcpy.CreateTable_management(os.path.dirname(outputTable), os.path.basename(outputTable), queryTemp)
        arcpy.AddField_management(outputTable, "texture", "TEXT", "", "", "30", "texture")
        arcpy.AddField_management(outputTable, "lieutex", "TEXT", "", "", "254", "lieutex")
        arcpy.Delete_management(queryTemp)

        # Process dictionaries and use them to write out the new SVI_Query table
        #
        # Open output table
        outFld2 = arcpy.Describe(outputTable).fields
        outFlds = list()
        for fld in outFld2:
            outFlds.append(fld.name)

        outFlds.pop(0)

        # Create empty lists to replace missing data
        missingCo = ["", None, None, None, None, None, None, None, None, None, None, None, None]
        missingHz = ["", None, None, None, None, None, None, None]
        missingTx = [None, None]

        # Save information on mapunits or components with bad or missing data
        muNoCo = list()
        dNoCo = dict()

        coNoHz = list()  # list of components with no horizons
        dNoHz = dict() # component data for those components in coNoHz

        arcpy.SetProgressor ("step", "Writing data to " + outputTable + "...", 0, len(muList), 1)

        with arcpy.da.InsertCursor(outputTable, fldAll2) as ocur:

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

                            #if not (compname in ["NOTCOM", "NOTPUB"] or compkind == 'Miscellaneous area'):
                            #    badComp = [mukey, str(cokey), compname, compkind, mjrcomp, str(comppct)]
                            #    coNoHz.append(str(cokey))   # add cokey to list of components with no horizon data
                            #    dNoHz[cokey] = badComp      # add component information to dictionary

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
                    ocur.insertRow(newrec)

                    #if not  mrec[0] in ['NOTCOM', 'NOTPUB']:
                        # skip map units that should never have component data
                        #
                    #    muNoCo.append(str(mukey))
                    #    dNoCo[str(mukey)] = [mrec[0], mrec[1]] # Save map unit name for the report

        env.workspace = outputDB
        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateOutputTableCo(sviTemp):
    # Create the component level table
    #
    try:
        # Create two output tables and add required fields
        try:
            # Try to handle existing output table if user has added it to ArcMap from a previous run
            if arcpy.Exists(sviTemp):
                arcpy.Delete_management(sviTemp)

        except:
            raise MyError, "Previous output table (" + sviTemp + ") is in use and cannot be removed"
            return False

        #PrintMsg(" \nCreating new output table (" + os.path.basename(sviTemp) + ") for component level data", 0)

        outputDB = os.path.dirname(sviTemp)
        tmpTable = os.path.join("IN_MEMORY", os.path.basename(sviTemp))

        arcpy.CreateTable_management("IN_MEMORY", os.path.basename(sviTemp))

        # Add fields appropriate for the component level restrictions
        arcpy.AddField_management(tmpTable, "COKEY", "TEXT", "", "", 30, "COKEY")
        arcpy.AddField_management(tmpTable, "COMPNAME", "TEXT", "", "", 60, "COMPNAME")
        arcpy.AddField_management(tmpTable, "COMPKIND", "TEXT", "", "", 60, "COMPKIND")
        arcpy.AddField_management(tmpTable, "MAJCOMPFLAG", "TEXT", "", "", 3)
        arcpy.AddField_management(tmpTable, "LOCALPHASE", "TEXT", "", "", 40, "LOCALPHASE")
        arcpy.AddField_management(tmpTable, "COMPPCT_R", "SHORT", "", "", "", "COMPPCT_R")
        arcpy.AddField_management(tmpTable, "SLOPE_R", "FLOAT")
        arcpy.AddField_management(tmpTable, "TAXORDER", "TEXT", "", 60)
        arcpy.AddField_management(tmpTable, "TAXSUBGRP", "TEXT", "", 60)
        arcpy.AddField_management(tmpTable, "HYDGRP", "TEXT", "", 12)
        arcpy.AddField_management(tmpTable, "DESGNMASTER", "TEXT", "", "", 254)
        arcpy.AddField_management(tmpTable, "HZDEPT_R", "SHORT")
        arcpy.AddField_management(tmpTable, "HZDEPB_R", "SHORT")
        arcpy.AddField_management(tmpTable, "OM_R", "FLOAT")
        arcpy.AddField_management(tmpTable, "TEXTURE", "TEXT", "", "", 60)
        arcpy.AddField_management(tmpTable, "LIEUTEX", "TEXT", "", "", 60)
        arcpy.AddField_management(tmpTable, "KFFACT", "TEXT", "", "", 5)
        arcpy.AddField_management(tmpTable, "SIEVENO10_R", "FLOAT")

        # Add primary key field
        arcpy.AddField_management(tmpTable, "MUKEY", "TEXT", "", "", 30, "MUKEY")

        # Add a status flag to mark the top mineral horizons for each component
        #arcpy.AddField_management(tmpTable, "TOP_MINERAL", "SHORT")

        # Convert IN_MEMORY table to a permanent table
        arcpy.CreateTable_management(outputDB, os.path.basename(sviTemp), tmpTable)

        # add attribute indexes for key fields
        arcpy.AddIndex_management(sviTemp, "MUKEY", "Indx_Res2Mukey", "NON_UNIQUE", "NON_ASCENDING")
        arcpy.AddIndex_management(sviTemp, "COKEY", "Indx_ResCokey", "UNIQUE", "NON_ASCENDING")

        return True

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
    # Is this a problem? Ending up with some deep horizons in the SVI calculations
    #

    lieuList = ['Slightly decomposed plant material', 'Moderately decomposed plant material', \
    'Highly decomposed plant material', 'Undecomposed plant material', 'Muck', 'Mucky peat', \
    'Peat', 'Coprogenous earth']  # CHTEXTURE.LIEUTEX
    txList = ["CE", "COP-MAT", "HPM", "MPM", "MPT", "MUCK", "PDOM", "PEAT", "SPM", "UDOM"] # CHTEXTUREGRP.TEXTURE

    try:
        # Histosols were used in RZAWS, but in general there is no KSAT for these components.
        # I think we will not use these
        #if str(taxorder) == 'Histosols' or str(taxsubgrp).lower().find('histic') >= 0:
            # Always treat histisols and histic components as having all mineral horizons
        #    return False


        if desgnmaster in ["O", "L"]:
            # This is an organic horizon according to CHORIZON.DESGNMASTER OR OM_R
            return True

        elif om > 19:
            # This is an organic horizon according to CHORIZON.DESGNMASTER OR OM_R
            return True

        elif str(texture) in txList:
            # This is an organic horizon according to CHTEXTUREGRP.TEXTURE
            return True

        elif str(lieutex) in lieuList:
            # This is an organic horizon according to CHTEXTURE.LIEUTEX
            return True

        else:
            # Default to mineral horizon if it doesn't match any of the criteria
            return False

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetTopHorizon(inputDB, sviTemp):
    #
    # Look at soil horizon properties and get the data for the first mineral horizon
    # Result will be one record per component.
    #
    # Components with COMPKIND = 'Miscellaneous area' or NULL are filtered out.
    #
    # Horizons with NULL hzdept_r or hzdepb_r are filtered out
    # Horizons with hzdept_r => hzdepb_r are filtered out
    #
    # O horizons or organic horizons from the surface down to the first mineral horizon
    # are filtered out.
    #

    try:
        dComp = dict()      # component level data for all component restrictions
        dComp2 = dict()     # store all component level data plus default values
        coList = list()
        queryTbl = os.path.join(env.scratchGDB, "SVI_Query")

        PrintMsg(" \nAggregating data for major components...", 0)

        sqlClause = (None, "ORDER BY cokey, hzdept_r ASC")

        # Only process major-earthy components...
        whereClause = "component.compkind <> 'Miscellaneous area' and component.compkind is not Null and component.majcompflag = 'Yes'"

        sqlClause = (None, "ORDER BY mukey, comppct_r DESC, cokey, hzdept_r ASC")
        curFlds = ["mukey", "cokey", "compname", "compkind", "localphase", "comppct_r", "majcompflag", "slope_r", "hydgrp", "taxorder", "taxsubgrp", "desgnmaster", "hzdept_r", "hzdepb_r", "om_r", "texture", "lieutex", "kffact", "sieveno10_r"]

        coFieldNames = ["mukey", "cokey", "compname", "compkind", "localphase", "comppct_r", "majcompflag", "slope_r", "hydgrp", "taxorder", "taxsubgrp", "desgnmaster", "hzdept_r", "hzdepb_r", "om_r", "texture", "lieutex", "kffact", "sieveno10_r"]

        lastCokey = "xxxx"
        lastMukey = 'xxxx'

        # Display status of processing input table containing horizon data and component restrictions
        inCnt = int(arcpy.GetCount_management(queryTbl).getOutput(0))

        if inCnt > 0:
            arcpy.SetProgressor ("step", "Processing input table...", 0, inCnt, 1)

        else:
            raise MyError, "Input table contains no data"

        hzIndex = 0

        with arcpy.da.SearchCursor(queryTbl, curFlds, whereClause, "", "", sqlClause) as cur:
            # Reading horizon-level data
            with arcpy.da.InsertCursor(sviTemp, coFieldNames) as cocur:

                for rec in cur:
                    # ********************************************************
                    #
                    # Read SVI_Query table record
                    mukey, cokey, compName, compKind, localPhase, compPct, majcompflag, slope, hydgrp, taxorder, taxsubgrp, desgnmaster, hzDept, hzDepb, om, texture, lieutex, kffact, sieveno10 = rec

                    bOrganic = CheckTexture(mukey, cokey, desgnmaster, om, texture, lieutex, taxorder, taxsubgrp)


                    if not bOrganic:

                        # Use the first record for this component (cokey)
                        if lastCokey != cokey:
                            hzIndex = 0
                            # Accumulate a list of components for future use
                            lastCokey = cokey
                            coList.append(cokey)
                            # "mukey", "cokey", "compname", "localphase", "comppct_r"
                            corec = mukey, cokey, compName, compKind, localPhase, compPct, majcompflag, slope, hydgrp, taxorder, taxsubgrp, desgnmaster, hzDept, hzDepb, om, texture, lieutex, kffact, sieveno10
                            cocur.insertRow(corec)
                            lastCokey = cokey
                            if hzDept > 100:
                                PrintMsg(str(hzIndex) + ": " + str(corec), 1)

                        #else:
                            # Mineral soil, but not the top horizon for the component
                            #pass
                            #corec = mukey, cokey, compName, compKind, localPhase, compPct, majcompflag, slope, hydgrp, taxorder, taxsubgrp, desgnmaster, hzDept, hzDepb, om, texture, lieutex, kffact, sieveno10
                            #cocur.insertRow(corec)
                            #PrintMsg(str(corec), 0)

                        #PrintMsg("\tCokey: " + cokey + " hz " + str(hzIndex), 1)
                        hzIndex += 1


                    else:
                        # Organic horizon
                        #PrintMsg("\tOrganic horizon: " + cokey + " hz " + str(hzIndex), 1)
                        pass
                        #corec = mukey, cokey, compName, compKind, localPhase, compPct, majcompflag, taxorder, taxsubgrp, desgnmaster, hzDept, hzDepb, om, texture, lieutex, kffact, sieveno10
                        #cocur.insertRow(corec)
                        #PrintMsg(str(corec), 0)

                    arcpy.SetProgressorPosition()

        arcpy.ResetProgressor()

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def RunCalculations(sviTemp):
    # Run leaching and runoff calculations based upon soil properties
    #
    # RunCalculations filters out the following data:
    #     Do not calculate SVI where hydric, kffact, slope or sieve are NULL

    # Get TopHorizon filters out the following data:
    #     Only use major components
    #     Do not calculate SVI where map unit is a 'Miscellaneous area'
    #     Do not calculate SVI where compkind or comppct_r is NULL

    #SVI rating based upon leaching and Runoff Index values
    #10 - Both high
    #9 - High and moderately high
    #8 - Both moderately high
    #7 - High and moderate
    #6 - Moderately high and moderate
    #5 - High and low
    #4 - Moderately high and low
    #3 - Both moderate
    #2 - Moderate and low
    #1 - Both low
    #0 - Undefined

    try:

        # first get path for input featureclass
        desc = arcpy.Describe(sviTemp)
        theDB = os.path.dirname(desc.catalogPath)

        # next find out if this is a workspace or a featuredataset
        desc = arcpy.Describe(theDB)
        theDataType = desc.dataType

        # get the workspace
        if theDataType.upper() == "FEATUREDATASET":
            # try going up one more level in the path to get the geodatabase
            theDB = os.path.dirname(theDB)
            PrintMsg(" \nDatabase: " + theDB, 0)

        env.workspace = theDB

        # Get the list of fields present in the SVI Table
        sviFields = [f.name for f in arcpy.ListFields(sviTemp) if f.type != "OID"]

        # If necessary, add the new output fields for the calculated data
        # LEACHING (int), RUNOFF(int)
        # PrintMsg(" \nAdding new fields to table...", 0)
        newFld = 'LEACHING'

        if not newFld in sviFields:
            arcpy.AddField_management(sviTemp, newFld, "SHORT", "", "", "", newFld)

        newFld = 'RUNOFF'

        if not newFld in sviFields:
            arcpy.AddField_management(sviTemp, newFld, "SHORT", "", "", "", newFld)

        newFld = 'SVI'

        if not newFld in sviFields:
            arcpy.AddField_management(sviTemp, newFld, "SHORT", "", "", "", newFld)

        # assign some of the field names so that they can be more easily modified to match the query output
        kfCol = "kffact"
        hydCol = "hydgrp"
        sieveCol = "sieveno10_r"
        flds = ['MUKEY', 'COKEY', 'SLOPE_R', hydCol, kfCol, sieveCol, 'LEACHING', 'RUNOFF', "SVI"]

        # Do not calculate SVI where hydric, kffact, slope or sieve are NULL
        sql = '"SLOPE_R" IS NOT NULL AND "' + hydCol + '" IS NOT NULL AND "' + sieveCol + '" IS NOT NULL AND "' + kfCol + '" IS NOT NULL'

        postFix = "ORDER BY MUKEY, COKEY, HZDEPT_R DESC"

        if arcpy.Exists(sviTemp):
            PrintMsg(" \nRunning SVI calculations...", 0)

            # Use data access update cursor to iterate through the selected records in the query table
            # for each record, run all calculations in a single pass
            with arcpy.da.UpdateCursor(sviTemp, flds, sql ) as upCursor:
                for rec in upCursor:
                    # read each of the existing soil properties into a variable
                    vMUKEY, vCOKEY, vSLOPE, vHYDGRP, vKFFACT, vSIEVE, vLEACHING, vRUNOFF, vSVI  = rec

                    # Calculate fragment volume as 100 - [sieve number 10] value
                    vFRAGVOL = 100.0 - vSIEVE

                    # Leaching Risk
                    if vHYDGRP.startswith('A'):
                        # Use slope to determine leaching for A
                        if vSLOPE <= 12:
                            vLEACHING = 4

                        else:
                            vLEACHING = 3

                        # Calculate Runoff for A
                        vRUNOFF = 1

                    elif vHYDGRP.startswith('B'):
                        # Calculate leaching for B using slope and KFactor RF
                        if vSLOPE < 3 and float(vKFFACT) < 0.24 :
                            vLEACHING = 4

                        elif 3 <= vSLOPE <= 12 and float(vKFFACT) < 0.24:
                            vLEACHING = 3

                        elif vSLOPE <= 12 and float(vKFFACT) >= 0.24 :
                            vLEACHING = 2

                        elif vSLOPE > 12:
                            vLEACHING = 2

                        else:
                            vLEACHING = None
                            PrintMsg("\tNo leaching value for mapunit " + vMUKEY + ", '" + vHYDGRP + "' hydric group, slope " + str(vSLOPE) + "%, Kfree " + str(vKFFACT), 1)

                        # Calculate Runoff for B, using slope and KFactor RF
                        if vSLOPE < 4:
                            vRUNOFF = 1

                        elif 4 <= vSLOPE <= 6 and float(vKFFACT) < 0.32 :
                            vRUNOFF = 2

                        elif 4 <= vSLOPE <= 6 and float(vKFFACT) >= 0.32:
                            vRUNOFF = 3

                        elif vSLOPE > 6:
                            vRUNOFF = 4

                        else:
                            vRUNNOFF = None
                            PrintMsg("\tNo runoff value for mapunit " + vMUKEY + ", '" + vHYDGRP + "' hydric group, slope " + str(vSLOPE) + "%, Kfree " + str(vKFFACT), 1)

                    elif vHYDGRP.startswith('C'):
                        # Calculate leaching for C
                        vLEACHING = 2

                        # Calculate runoff for C using slope and KFactor RF
                        if vSLOPE < 2:
                            vRUNOFF = 1

                        elif 2 <= vSLOPE <= 6 and float(vKFFACT) < 0.28 :
                            vRUNOFF = 2

                        elif  2 <= vSLOPE <= 6 and float(vKFFACT) >= 0.28:
                            vRUNOFF = 3

                        elif vSLOPE > 6:
                            vRUNOFF = 4

                        else:
                            vRUNOFF = None

                    elif vHYDGRP.startswith('D'):
                        # Calculate leaching for D
                        vLEACHING = 1

                        # Calculate runoff for D using slope and KFactor RF
                        if vSLOPE < 2 and float(vKFFACT) < 0.28:
                            vRUNOFF = 1

                        elif vSLOPE < 2 and float(vKFFACT) >= 0.28:
                            vRUNOFF = 2

                        elif 2 <= vSLOPE <= 4:
                            vRUNOFF = 3

                        elif vSLOPE > 4:
                            vRUNOFF = 4

                        else:
                            vRUNOFF = None
                            PrintMsg("\tNo runoff value assigned for mapunit " + vMUKEY + " with a '" + vHYDGRP + "' hydric group", 1)

                    else:
                        PrintMsg("\tNo leaching value assigned for mapunit " + vMUKEY + " with a '" + vHYDGRP + "' hydric group", 1)

                    # Increase LEACHING value for some frag volumes
                    if vLEACHING == 1:
                        if vFRAGVOL >= 30:
                            vLEACHING_C = 3

                        elif 10 <= vFRAGVOL < 30:
                            vLEACHING_C = 2

                        else:
                            vLEACHING_C = vLEACHING

                    elif vLEACHING == 2:
                        if vFRAGVOL >= 30:
                            vLEACHING_C = 4

                        elif 10 <= vFRAGVOL < 30:
                            vLEACHING_C = 3

                        else:
                            vLEACHING_C = vLEACHING

                    elif vLEACHING == 3:
                        if vFRAGVOL >= 30:
                            vLEACHING_C = 4

                        elif 10 <= vFRAGVOL < 30:
                            vLEACHING_C = 4

                        else:
                            vLEACHING_C = vLEACHING

                    else:
                        vLEACHING_C = vLEACHING

                    # Calculate combined SVI based upon LEACHING and RUNOFF
                    #
                    if vLEACHING is not None and vRUNOFF is not None:

                        if vLEACHING_C == 4 and vRUNOFF == 4:
                            vSVI = 10

                        elif (vLEACHING_C == 4 and vRUNOFF == 3) or (vLEACHING_C == 3 and vRUNOFF == 4):
                            vSVI = 9

                        elif vLEACHING_C == 3 and vRUNOFF == 3:
                            vSVI = 8

                        elif (vLEACHING_C == 4 and vRUNOFF == 2) or (vLEACHING_C == 2 and vRUNOFF == 4):
                            vSVI = 7

                        elif (vLEACHING_C == 3 and vRUNOFF == 2) or (vLEACHING_C == 2 and vRUNOFF == 3):
                            vSVI = 6

                        elif (vLEACHING_C == 4 and vRUNOFF == 1) or (vLEACHING_C == 1 and vRUNOFF == 4):
                            vSVI = 5

                        elif (vLEACHING_C == 3 and vRUNOFF == 1) or (vLEACHING_C == 1 and vRUNOFF == 3):
                            vSVI = 4

                        elif (vLEACHING_C == 2 and vRUNOFF == 2):
                            vSVI = 3

                        elif (vLEACHING_C == 2 and vRUNOFF == 1) or (vLEACHING_C == 1 and vRUNOFF == 2):
                            vSVI = 2

                        elif (vLEACHING_C == 1 and vRUNOFF == 1):
                            vSVI = 1

                        else:
                            PrintMsg("\nUnable to assign value for Leaching: " + str(vLEACHING_C) + " and Runoff: " + str(vRUNOFF), 1)

                    else:
                        vSVI = None

                    rec = [vMUKEY, vCOKEY, vSLOPE, vHYDGRP, vKFFACT, vFRAGVOL, vLEACHING_C, vRUNOFF, vSVI]
                    upCursor.updateRow(rec)

        return True

    except:
        errorMsg()
        return False
## ===================================================================================
def DominantComponent(sviTemp, tieBreaker, outputTbl, fieldList, ratCol):
    # Create output table with values for dominant component
    # Note: this function creates an output table with the same fields as the input
    # Only one record per mapunit (MUKEY) is output.
    #
    try:

        # Cursor fields. Note, COMPNAME is included for dominant component
        ratCol2 = ratCol +"_DCP"
        muCol = "MUKEY"
        pctCol = "COMPPCT_R"

        desc = arcpy.Describe(sviTemp)
        inputFields = desc.fields

        for fld in inputFields:
            if fld.name.upper() == ratCol.upper():
                fldType = fld.type
                fldLen = fld.length
                fldPrec = fld.precision
                fldScale = fld.scale

        # Create final output table and write aggregate data
        #
        sql = arcpy.AddFieldDelimiters(sviTemp, pctCol) + " > 0 AND NOT " + arcpy.AddFieldDelimiters(sviTemp, ratCol) + " IS NULL"

        if tieBreaker == 'High':
            # Hopefully this will present the higher rating in the event there is a tie for comppct_r
            postFix = "ORDER BY " + muCol + ", " + pctCol + " DESC, " + ratCol + " DESC"

        else:
            postFix = "ORDER BY " + muCol + ", " + pctCol + " DESC, " + ratCol + " ASC"

        # Third step is to create the new output table
        #
        # Get data type for rating column so that it can be used
        # when creating the output table
        #PrintMsg(" \nCreating output table...", 0)

        # If I decide not to duplicate the input table, here is the code needed to manually
        # recreate a minimum set of fields in a new table

        #desc = arcpy.Describe(sviTemp)
        #inputFields = desc.fields

        #for fld in inputFields:
        #    if fld.name == ratCol:
        #       fldType = fld.type
        #        fldLen = fld.length
        #        fldPrec = fld.precision
        #        fldScale = fld.scale

        # Adding 'MUKEY'
        #arcpy.AddField_management(outputTbl, 'MUKEY', "TEXT", "", "", 30, 'MUKEY')

        # Adding 'COMPNAME'
        #arcpy.AddField_management(outputTbl, 'COMPNAME', "TEXT", "", "", 60, 'MUKEY')

        # Adding 'COMPPCT'
        #arcpy.AddField_management(outputTbl, 'COMPPCT_R', "SHORT", "", "", "", 'COMPPCT')

        # Adding selected rating column
        #arcpy.AddField_management(outputTbl, ratCol2, fldType, fldPrec, fldScale, fldLen, ratCol2)

        #if outputTbl.endswith(".dbf"):
        #    arcpy.DeleteField_management(outputTbl, "Field1")

        # Create a new table using the input table as a template
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl), sviTemp)

        iCnt = int(arcpy.GetCount_management(sviTemp).getOutput(0))
        inCur = arcpy.da.SearchCursor(sviTemp, fieldList, sql, "", False, (None, postFix))
        outCur = arcpy.da.InsertCursor(outputTbl, fieldList )

        arcpy.SetProgressor("step", "Writing data to new table...",  0, iCnt, 1)

        lastMukey = 'x'

        # Get index values for MUKEY
        iMukey = fieldList.index('mukey')

        for rec in inCur:
            # read each input record...
            mukey = rec[iMukey]

            if mukey != lastMukey:
                # Write out just first sorted record which will be the dominant component
                outCur.insertRow(rec)

            lastMukey = mukey
            arcpy.SetProgressorPosition()

        arcpy.AddIndex_management(outputTbl, "MUKEY", os.path.basename(outputTbl) + "_MUKEY")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def DominantCondtion(sviTemp, tieBreaker, outputTbl, fieldList, ratCol):
    # Create output table with values for the dominant condition
    #
    try:

        # First step is to calculate the sum of comppct for
        # each combination of MUKEY and the selected rating column

        dSum = dict()
        dMaxPct = dict()
        dDCD = dict()

        # input Cursor fields. Note, COMPNAME not needed for dominant condition
        muCol = "MUKEY"
        pctCol = "COMPPCT_R"
        inFlds = (muCol, pctCol, ratCol)
        ratCol2 = ratCol + "_DCD"
        outFlds = (muCol, pctCol, ratCol2)

        # Remove component or horizon fields not used for dominant condition
        if 'hzdept_r' in fieldList:
            fieldList.remove("compname")

        if 'hzdept_r' in fieldList:
            fieldList.remove('hzdept_r')

        if 'hzdepb_r' in fieldList:
            fieldList.remove('hzdepb_r')

        # Open table and
        sql = arcpy.AddFieldDelimiters(sviTemp, pctCol) + " > 0 AND NOT " + arcpy.AddFieldDelimiters(sviTemp, ratCol) + " IS NULL"

        if tieBreaker == 'High':
            # Hopefully this will present the higher rating in the event there is a tie for comppct_r
            postFix = "ORDER BY " + muCol + ", " + pctCol + " DESC, " + ratCol + " DESC"

        else:
            postFix = "ORDER BY " + muCol + ", " + pctCol + " DESC, " + ratCol + " ASC"

        iCnt = int(arcpy.GetCount_management(sviTemp).getOutput(0))
        inCur = arcpy.da.SearchCursor(sviTemp, inFlds, sql, "", False, (None, postFix))
        arcpy.SetProgressor("step", "Reading data from input table...",  0, iCnt, 1)

        for rec in inCur:
            mukey, pct, val = rec

            key = mukey + ":" + str(val)

            if key in dSum:
                # At least one component record belonging to this mapunit has
                # already been processed.
                # add to pct
                sumPct = dSum[key] + pct
                dSum[key] = sumPct

                if mukey in dMaxPct:
                    if sumPct > dMaxPct[mukey]:
                        dMaxPct[mukey] = sumPct

                else:
                    dMaxPct[mukey] = sumPct

            else:
                dSum[key] = pct
                sumPct = pct
                if mukey in dMaxPct:
                    if sumPct > dMaxPct[mukey]:
                        dMaxPct[mukey] = sumPct

                else:
                    dMaxPct[mukey] = sumPct

            arcpy.SetProgressorPosition()

        # Second step is to find the dominant condition for each mukey
        #
        iCnt = len(dSum)
        arcpy.SetProgressor("step", "Finding dominant condition for each map unit...",  0, iCnt, 1)

        for key, pct in dSum.items():
            mukey, val = key.split(":")

            if pct == dMaxPct[mukey]:
                dDCD[mukey] = (pct, val)

            arcpy.SetProgressorPosition()

        # Third step is to create the new output table
        #
        #PrintMsg(" \nCreating output table...", 0)

        # Get data type for rating column so that it can be added to the output table
        desc = arcpy.Describe(sviTemp)
        inputFields = desc.fields

        for fld in inputFields:
            if fld.name.upper() == ratCol.upper():
                fldType = fld.type
                fldLen = fld.length
                fldPrec = fld.precision
                fldScale = fld.scale

        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        # Adding 'MUKEY'
        arcpy.AddField_management(outputTbl, 'mukey', "TEXT", "", "", 30, 'mukey')

        # Adding 'COMPPCT'
        arcpy.AddField_management(outputTbl, 'comppct_r', "SHORT", "", "", "", 'comppct_r')

        # Adding selected rating column
        arcpy.AddField_management(outputTbl, ratCol2, fldType, fldPrec, fldScale, fldLen, ratCol2)

        if outputTbl.endswith(".dbf"):
            arcpy.DeleteField_management(outputTbl, "Field1")

        # Fourth step is to write the aggregate data to the output table
        #
        #PrintMsg(" \nWriting data to final output table...", 0)

        with arcpy.da.InsertCursor(outputTbl, outFlds ) as outCur:
            iCnt = len(dDCD)
            arcpy.SetProgressor("step", "Writing data to output table...",  0, iCnt, 1)

            for mukey, vals in dDCD.items():
                rec =(mukey, vals[0], vals[1])
                outCur.insertRow(rec)
                arcpy.SetProgressorPosition()

        arcpy.AddIndex_management(outputTbl, "MUKEY", os.path.basename(outputTbl) + "_MUKEY")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import os, sys, string, re, locale, arcpy, traceback, collections
from operator import itemgetter, attrgetter
import xml.etree.cElementTree as ET
from datetime import datetime
from arcpy import env

# Dobos - NASIS lieutext matches: mpm, mpt, muck, peat, spm, udom, pdom, hpm
#
# Paul's organic horizon filters:  chtexturegrp.texture <> 'SPM', <>'UDOM'???, NOT LIKE: '%MPT%', '%MUCK', '%PEAT%' (from SVI query)
#
# Desgnmaster filter:  hzdesn IN ["O", "O'", "L"]
#
# Taxonomic Order filter:  upper(taxorder) LIKE 'HISTOSOLS'. Is this being used?
# Perhaps I should be using taxsubgrp.lower() like '%histic%' or use both!!!

#
# compkind filter for earthy components:  <> 'Miscellaneous area'


try:
    arcpy.OverwriteOutput = True

    inputDB = arcpy.GetParameterAsText(0)              # Input gSSURGO database
    sviTable = arcpy.GetParameterAsText(1)         # Name of temporary output table (stored in the scratchGDB)
    aggMethod = arcpy.GetParameterAsText(2)            # Dominant Condition or Dominant Component method
    tieBreaker = arcpy.GetParameterAsText(3)           # Sort order for ratings, default is to take the higher value in a tie

    sviTemp = os.path.join(env.scratchGDB, "sviTemp")  # temporary table containing non-aggregated data
    ratCol = "SVI"                                     # input field that will be aggregated in the sviTable

    # Set output workspace to same as the input table
    env.workspace = inputDB

    # Clean up previous runs
    #sviTable = os.path.join(inputDB, sviTableName)

    if arcpy.Exists(sviTable):
        arcpy.Delete_management(sviTable)

    if arcpy.Exists(sviTemp):
        arcpy.Delete_management(sviTemp)

    # Create initial set of query tables used for RZAWS, AWS and SOC
    if CreateQueryTables(inputDB, env.scratchGDB):

        if CreateOutputTableCo(sviTemp):

            if GetTopHorizon(inputDB, sviTemp):
                # Find the top restriction for each component, both from the corestrictions table and the horizon properties

                if RunCalculations(sviTemp):
                    # Summarize component-horizon data to a single value
                    # Please note that some fields are required for the query to work (MUKEY, COKEY, COMPPCT_R, HZDEPT_R)
                    flds = arcpy.Describe(sviTemp).fields
                    fieldList = list()

                    for fld in flds:
                        if fld.type != "OID":
                            fieldList.append(fld.name.lower())

                    if aggMethod == 'Dominant Component':
                        bAggregated = DominantComponent(sviTemp, tieBreaker, sviTable, fieldList, ratCol)

                    else:
                        bAggregated = DominantCondtion(sviTemp, tieBreaker, sviTable, fieldList, ratCol)

                    if bAggregated:
                        PrintMsg(" \nCompleted " + aggMethod.lower() + " export to new table (" + sviTable + ") \n ")

                    else:
                        PrintMsg(" \nFailed to create SVI rating table 1 \n ", 2)

                else:
                    PrintMsg(" \nFailed to create SVI rating table 2 \n ", 2)

            else:
                PrintMsg(" \nFailed to create SVI rating table 3 \n ", 2)

        else:
            PrintMsg(" \nFailed to create SVI rating table 4 \n ", 2)

    else:
        PrintMsg(" \nFailed to create SVI rating table 5 \n ", 2)


except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
