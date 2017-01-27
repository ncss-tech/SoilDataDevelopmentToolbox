# gSSURGO_ValidateData.py
#
# Steve Peaslee, National Soil Survey Center
# 2014-09-27

# Adapted from gSSURGO_ValuTable.py
#
# Checks for some basic data population problems at the mapunit, component and horizon levels


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
def GetLastDate(inputDB):
    # Get the most recent date 'YYYYMMDD' from SACATALOG.SAVEREST and use it to populate metadata
    #
    try:
        tbl = os.path.join(inputDB, "SACATALOG")
        today = ""
        sqlClause = [None, "ORDER_BY SAVEREST DESC"]

        with arcpy.da.SearchCursor(tbl, ['SAVEREST'], sql_clause=sqlClause) as cur:
            for rec in cur:
                #lastDate = rec[0].split(" ")[0].replace("-", "")
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
def GetSumPct(inputDB):
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
        pctFlds = ["mukey", "compkind", "majcompflag", "comppct_r"]

        dPct = dict()

        with arcpy.da.SearchCursor(os.path.join(inputDB, "component"), pctFlds, where_clause=pctSQL) as pctCur:
            for rec in pctCur:
                mukey, compkind, flag, comppct = rec
                m = 0     # major component percent
                me = 0    # major-earthy component percent
                e = 0     # earthy component percent

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

        return dPct

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def CreateQueryTables(inputDB, outputDB, maxD, dPct):
    # Assemble a table containing mapunit, component and horizon data.
    # ArcGIS cannot perform a proper outer join, so it has to be done the hard way.
    #
    try:
        env.workspace = inputDB
        #queryMU = "MU"
        #queryCO = "CO"
        #queryHZ = "HZ"
        #queryCR = "CR"
        #queryCT = "CT"
        queryTemp = "Tmp"  # empty table uses as template

        # Mapunit query
        PrintMsg(" \nReading MAPUNIT table...", 0)
        whereClause = ""
        fldMu = [["mukey", "mukey"], ["musym", "musym"], ["muname", "muname"]]
        fldMu2 = list()
        dMu = dict()
        sqlClause = (None, "ORDER BY mukey")

        for fld in fldMu:
            fldMu2.append(fld[0])

        muList = list()

        muTbl = os.path.join(inputDB, "mapunit")

        with arcpy.da.SearchCursor(muTbl, fldMu2, sql_clause=sqlClause) as mcur:
            for mrec in mcur:
                rec = list(mrec)
                mukey = rec[0]
                rec.pop(0)
                dMu[mukey] = rec
                muList.append(mukey)

        muList.sort()

        # Component query
        PrintMsg(" \nReading COMPONENT table...", 0)
        fldCo = [["mukey", "mukey"], ["cokey", "cokey"], ["comppct_r", "comppct_r"], ["majcompflag", "majcompflag"], \
        ["compname", "compname"], ["compkind", "compkind"], ["taxorder", "taxorder"], ["taxsubgrp", "taxsubgrp"], \
        ["localphase", "localphase"], ["otherph", "otherph"], ["hydricrating", "hydricrating"], ["drainagecl", "drainagecl"]]
        fldCo2 = list()
        dCo = dict()
        whereClause = "comppct_r is not NULL"
        sqlClause = (None, "ORDER BY cokey, comppct_r DESC")
        coTbl = os.path.join(inputDB, "component")

        for fld in fldCo:
            fldCo2.append(fld[0])

        with arcpy.da.SearchCursor(coTbl, fldCo2, where_clause=whereClause, sql_clause=sqlClause) as ccur:
            for crec in ccur:
                rec = list(crec)
                mukey = rec.pop(0)  # get rid of mukey from component record

                try:
                    # Add next component record to list
                    dCo[mukey].append(rec)

                except:
                    # initialize list of records
                    dCo[mukey] = [rec]

        # HORIZON TABLE
        PrintMsg(" \nReading HORIZON table...", 0)
        fldHz = [["cokey", "cokey"], ["chkey", "chkey"], ["hzname", "hzname"], ["desgnmaster", "desgnmaster"], \
        ["hzdept_r", "hzdept_r"], ["hzdepb_r", "hzdepb_r"], ["sandtotal_r", "sandtotal_r"], \
        ["silttotal_r", "silttotal_r"], ["claytotal_r", "claytotal_r"], ["om_r", "om_r"], \
        ["dbthirdbar_r", "dbthirdbar_r"], ["ec_r", "ec_r"], ["ph1to1h2o_r", "ph1to1h2o_r"], \
        ["awc_r", "awc_r"]]
        fldHz2 = list()
        dHz = dict()
        whereClause = "hzdept_r is not NULL and hzdepb_r is not NULL"
        sqlClause = (None, "ORDER BY chkey, hzdept_r ASC")

        for fld in fldHz:
            fldHz2.append(fld[0])

        hzTbl = os.path.join(inputDB, "chorizon")

        with arcpy.da.SearchCursor(hzTbl, fldHz2, where_clause=whereClause, sql_clause=sqlClause) as hcur:
            for hrec in hcur:
                rec = list(hrec)
                cokey = rec.pop(0)

                try:
                    # Add next horizon record to list
                    dHz[cokey].append(rec)

                except:
                    # initialize list of horizon records
                    dHz[cokey] = [rec]

            # HORIZON TEXTURE QUERY
            #
            # Not using horizon texture data in validation. All related code has been commented out, but kept for future use.
            #
            #PrintMsg(" \nMaking query table (CT) for texture information", 0)
            #inputTbls = list()
            #tbls = ["chtexturegrp", "chtexture"]
            #for tbl in tbls:
            #    inputTbls.append(os.path.join(inputDB, tbl))

            #txList1 = [["chtexturegrp.chkey", "chkey"], ["chtexturegrp.texture", "texture"], ["chtexture.lieutex", "lieutex"]]
            #whereClause = "chtexturegrp.chtgkey = chtexture.chtgkey and chtexturegrp.rvindicator = 'Yes'"
            #arcpy.MakeQueryTable_management(inputTbls, queryCT, "USE_KEY_FIELDS", "#", txList1, whereClause)

            # Read texture query into dictionary
            #txList2 = ["chtexturegrp.chkey", "chtexturegrp.texture", "chtexture.lieutex"]
            #dTexture = dict()
            #ctCnt = int(arcpy.GetCount_management(queryCT).getOutput(0))

            #arcpy.SetProgressor ("step", "Getting horizon texture information for QueryTable_HZ...", 0, ctCnt, 1)

            # Have been running out of memory here if other applications are running. 5.66GB

            #with arcpy.da.SearchCursor(queryCT, txList2) as cur:
            #    for rec in cur:
            #        dTexture[int(rec[0])] = [rec[1], rec[2]]
            #        arcpy.SetProgressorPosition()

            #arcpy.Delete_management(queryCT)

        # COMPONENT RESTRICTIONS depths will be saved to a dictionary for later comparison to the CHORIZON table
        #
        crTbl = os.path.join(inputDB, "corestrictions")
        PrintMsg(" \nWriting component restrictions to " + os.path.join(outputDB, "QueryTable_CR"), 0)
        #fldCr = [["cokey", "cokey"], ["resdept_r", "resdept_r"]]
        #["reskind", "reskind"],\
        #["reshard", "reshard"],\
        #["resdept_r", "resdept_r"]]
        #whereClause = "OBJECTID = 1"
        #arcpy.MakeQueryTable_management(crTbl, queryCR, "USE_KEY_FIELDS", "#", fldCr, whereClause)
        #if arcpy.Exists(os.path.join(outputDB, "QueryTable_CR")):
        #    arcpy.Delete_management(os.path.join(outputDB, "QueryTable_CR"))

        #arcpy.CreateTable_management(outputDB, "QueryTable_CR", queryCR)
        #arcpy.Delete_management(queryCR)

        fldCr2 = ["cokey", "resdept_r"]
        dCr = dict()
        sqlClause = (None, "ORDER BY cokey, resdept_r ASC")
        whereClause = "resdept_r is not NULL"
        #crList = list() # list of components with a restriction
        crCnt = int(arcpy.GetCount_management(crTbl).getOutput(0))
        arcpy.SetProgressor ("step", "Saving component restriction information...", 0, crCnt, 1)

        with arcpy.da.SearchCursor(crTbl, fldCr2, where_clause=whereClause, sql_clause=sqlClause) as crcur:

            for crrec in crcur:
                #rec = list(crrec)
                #cokey = int(crrec[0])
                cokey = crrec[0]
                arcpy.SetProgressorPosition()

                try:
                    dCr[cokey].append(crrec[1])

                except:
                    dCr[cokey] = [crrec[1]]

        PrintMsg(" \nCreating QueryTable_HZ in " + outputDB, 0)
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
        #fldAll2.append("texture")
        #fldAll2.append("lieutex")

        # Select component-horizon data for ALL components that have horizon data. Lack of horizon data
        # will cause some components to be missing from the PWSL.
        #
        # Later on in the actual calculations for RZAWS, only the major-earthy components will be used. But
        # all components are in this table!

        whereClause = "mapunit.mukey = component.mukey and component.cokey = chorizon.cokey and mapunit.objectid = 1"

        outputTable = os.path.join(outputDB, "QueryTable_HZ")
        #PrintMsg(" \nCreating table " + outputTable + " with fields: " + str(fldAll), 0)
        arcpy.MakeQueryTable_management(['mapunit', 'component', 'chorizon'], queryTemp, "USE_KEY_FIELDS", "#", fldAll, whereClause)

        if arcpy.Exists(outputTable):
            arcpy.Delete_management(outputTable)

        arcpy.CreateTable_management(outputDB, "QueryTable_HZ", queryTemp)
        #arcpy.AddField_management(outputTable, "texture", "TEXT", "", "", "30", "texture")
        #arcpy.AddField_management(outputTable, "lieutex", "TEXT", "", "", "254", "lieutex")
        arcpy.Delete_management(queryTemp)
        del queryTemp

        # Process dictionaries and use them to write out the new QueryTable_HZ table
        #
        # Open output table
        outFld2 = arcpy.Describe(outputTable).fields
        outFlds = list()
        for fld in outFld2:
            outFlds.append(fld.name)

        outFlds.pop(0)

        # Create empty lists to replace missing data
        missingCo = ["", None, None, None, None, None, None, None, None, None, None]
        missingHz = ["", None, None, None, None, None, None, None, None, None, None, None, None]
        #missingTx = [None, None]

        # Save information on mapunits or components with bad or missing data
        #badMu = list()   # list of mapunits with no components
        muNoCo = list()
        dNoCo = dict()
        muNotCom = list()

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
                        cokey = corec[0]

                        try:
                            hzVals = dHz[cokey]  # horizon records for this component
                            # Sort record by hzdept_r
                            hzList = sorted(hzVals, key = lambda x: int(x[3]))

                            for hzrec in hzList:
                                chkey = hzrec[0]

                                #try:
                                    # Get horizon texture
                                #    txrec = dTexture[chkey]

                                #except:
                                #    txrec = missingTx

                                # Combine all records and write to table
                                newrec = [mukey]
                                newrec.extend(mrec)
                                newrec.extend(corec)
                                newrec.extend(hzrec)
                                #newrec.extend(txrec)
                                ocur.insertRow(newrec)

                        except KeyError:
                            # No horizon records for this component
                            comppct = corec[1]
                            compname = corec[3]
                            compkind = corec[4]
                            mjrcomp = corec[2]
                            #PrintMsg("Major compflag = " + str(corec), 1)

                            hzrec = missingHz
                            #txrec = missingTx
                            newrec = [mukey]
                            newrec.extend(mrec)
                            newrec.extend(corec)
                            newrec.extend(hzrec)
                            #newrec.extend(txrec)
                            ocur.insertRow(newrec)

                            if not (compname in ["NOTCOM", "NOTPUB"] or compkind == 'Miscellaneous area'):
                                # The 'Miscellaneous area' criteria is not always an indicator of no HZ data
                                #
                                badComp = [mukey, cokey, compname, compkind, mjrcomp, str(comppct)]
                                coNoHz.append(cokey)   # add cokey to list of components with no horizon data
                                dNoHz[cokey] = badComp      # add component information to dictionary
                                #PrintMsg(" \nMissing horizon data: " + str(corec), 1)

                        except:
                            PrintMsg(" \nhzVals error for " + mukey + ":" + cokey, 2)
                            PrintMsg(" \n" + str(fldAll2), 1)
                            errorMsg()

                except:
                    # No component records for this map unit
                    corec = missingCo
                    hzrec = missingHz
                    #txrec = missingTx
                    newrec = [mukey]
                    newrec.extend(mrec)
                    newrec.extend(corec)
                    newrec.extend(hzrec)
                    #newrec.extend(txrec)
                    ocur.insertRow(newrec)

                    if mrec[0] in ['NOTCOM', 'NOTPUB']:
                        # skip map units that should never have component data
                        #
                        muNotCom.append(mukey)

                    else:
                        muNoCo.append(mukey)
                        dNoCo[mukey] = [mrec[0], mrec[1]] # Save map unit name for the report
                        #PrintMsg(" \n\n** No component data for " + str(mrec[1]), 2)

        # Run through QueryTbl_HZ table, checking for inconsistencies in horizon depths
        # Create a dictionary containing a list of top and bottom of each horizon in each component
        # dictionary key = cokey
        # list contains tuples of hzdept_r, hzdepb_r, hzname, mukey, compname, localphase

        # What about components that have no horizon data?

        dHZ = dict()

        # Exclude horizon data with null hzdep with whereclause
        wc = "hzdept_r is not null and hzdepb_r is not null"
        arcpy.ResetProgressor()
        arcpy.SetProgressorLabel("Looking for inconsistencies in horizon depths...")

        with arcpy.da.SearchCursor(outputTable, ['mukey', 'cokey','hzdept_r','hzdepb_r', 'hzname', 'compname', 'localphase', 'majcompflag'], where_clause=wc) as cur:
            for rec in cur:
                mukey, cokey, top, bot, hzname, compname, localphase, majcomp = rec
                #cokey = int(cokey)

                if cokey in dHZ:
                    vals = dHZ[cokey]
                    vals.append([top, bot, hzname, mukey, compname, localphase, majcomp])
                    dHZ[cokey] = vals

                else:
                    dHZ[cokey] = [[top, bot, hzname, mukey, compname, localphase, majcomp]]

                try:
                    if top in dCr[cokey]:
                        # remove top horizon depth from list of component restriction depths
                        # in the end, those left in the dictionary should be ones that don't match the CHORIZON table hzdept_r values
                        #dCr[cokey].remove(top)
                        dCr[cokey] = [t for t in dCr[cokey] if t != top]

                except:
                    pass

        # This should be the end of any reference to 'outputTable'
        arcpy.Delete_management(outputTable)
        del outputTable


        # Number of items in each component value = len(rec)
        # top of first horizon = rec[0][0]
        # bottom of last horizon = rec[len(rec) - 1][1]
        # component thickness #1 = rec[len(rec) - 1][1] - rec[0][0]
        # Read each entry in the dictionary and check for gaps and overlaps in the horizons
        #
        badCoHz = list()
        badHorizons = list()

        for cokey, vals in dHZ.items():
            # Process each component
            #
            hzSum = 0                     # itialize sum of horizon thicknesses
            lb = vals[0][0]               # initialize last bottom to the top of the first horizon
            localphase = vals[0][5]

            if localphase is None:
                localphase = ""

            else:
                localphase = " " + localphase

            for v in vals:
                # Process each horizon in the component record
                #
                # sum of bottom - top for each horizon
                hzSum += (v[1] - v[0])

        		# Check for consistency between tops and bottoms for each consecutive horizon
                if v[0] != lb:
                    diff = v[0] - lb
                    badCoHz.append(cokey)
                    badHorizons.append(v[3] + ", " + cokey + ", " + v[4] + localphase + ", " + majcomp + ", " + str(v[2]) + ", " + str(v[0]) + ", " + str(diff) )

                lb = v[1] # update last bottom depth

        PrintMsg(" \nIdentifying component restrictions with horizon depth discrepancies", 0)
        arcpy.SetProgressor ("step", "Identifying component restrictions with horizon depth discrepancies", 0, len(dCr), 1)

        for cokey, crDepths in dCr.items():
            if len(crDepths) == 0:
                dCr.pop(cokey, None)
                #if cokey in coNoHz:
                #    PrintMsg("\tcokey " + cokey + " has restriction but no horizon data", 1)

            #else:
            #    PrintMsg(" \n" + str(cokey) + ": " + str(crDepths), 1)

        # Check for sum of comppct_r > 100 or missing
        muBadPct = list()

        for mukey in muList:
            try:
                sumPct = dPct[str(mukey)][0]

                if sumPct < 75 or sumPct > 100:
                    muBadPct.append(mukey)

            except KeyError:
                if not str(mukey) in muNotCom:
                    muBadPct.append(mukey)

        # Report data validation failures...
        #
        # Save data issues to permanent files for later review
        if len(muNoCo) or len(coNoHz) or len(badCoHz) or len(muBadPct) or len(dCr):
            PrintMsg(" \nCreating log file: " + logFile, 1)
            now = datetime.now()
            fh = open(logFile, "w")
            fh.write("\n" + inputDB + "\n")
            fh.write("\nProcessed on " + now.strftime('%A %x  %X') + "\n\n")
            fh.write("This log file contains record of any basic data inconsistencies found in the gSSURGO database \n ")
            fh.close()

            # Report map units with sum of all components > 100 or < 75
            # These data are stored in dPct where mukey is text but mukey is integer in muList
            #
            if len(muBadPct) > 0:
                fh = open(logFile, "a")
                fh.write("\nQuery for map units with sum of comppct_r < 75 or > 100\n")
                fh.write("====================================================================================\n")
                fh.write("MUKEY IN ('" + "', '".join(muBadPct) + "') \n\n")
                fh.close()
                PrintMsg(" \nMap units (" + Number_Format(len(muBadPct), 0, True) + ") with sum of comppct_r less than 75 or greater than 100 saved to log file", 0)

            # Save data issues (mapunits with no components) to log file for later review
            # Some of these will be NOTCOMs
            if len(muNoCo) > 0:
                fh = open(logFile, "a")
                #fh.write(inputDB + "\n")
                fh.write("\nQuery for map units missing component data\n")
                fh.write("====================================================================================\n")
                fh.write("MUKEY IN ('" + "', '".join(muNoCo) + "') \n\n")
                fh.write("\n\nTable of map units missing component data\n")
                fh.write("\nMUKEY, MUSYM, MUNAME\n")
                for mukey in muNoCo:
                    fh.write(mukey + ", " + dNoCo[mukey][0] + ", " + dNoCo[mukey][1] + "\n")

                fh.close()
                PrintMsg(" \nMap units missing component data (" + Number_Format(len(muNoCo), 0, True) + ") saved to logfile", 0)

            # Save data issues (components with no horizons) to log file for later review
            # Note; these COKEYs will work with gSSURGO but not Soil Data Access
            # Some of these may be NOTCOMs
            if len(coNoHz) > 0:
                PrintMsg(" \nQuery for components missing horizon data (" + Number_Format(len(coNoHz), 0, True) + ") saved to logfile", 0)
                fh = open(logFile, "a")
                fh.write("\n\nQuery for components with no horizon data\n")
                fh.write("====================================================================================\n")
                fh.write("COKEY IN ('" + "', '".join(coNoHz) + "') \n\n")

                fh.write("Table of components that are completely missing horizon data\n")
                fh.write("\nMUKEY, COKEY, COMPNAME, MAJCOMPFLAG, COMPKIND, MAJCOMPFLAG, COMPPCT, COMPKIND\n")

                for mukey, compInfo in dNoHz.items():
                    # mukey, str(cokey), compname, compkind, mjrcomp, str(comppct)
                    mukey, cokey, compname, compkind, majcomp, comppct = compInfo
                    #compInfo = mukey, str(cokey), compname, compkind, str(comppct)
                    fh.write(mukey + ", " + cokey + ", " + compname + ", " + str(compkind) + ", "  + majcomp + ", " + str(comppct) + ", " + str(compkind) + "\n")

                fh.close()

            # These components have inconsistent horizon depths that overlap or gap.
            # Note; these COKEYs will work with gSSURGO but not Soil Data Access
            if len(badCoHz) > 0:
                PrintMsg(" \nComponents with horizon gaps or overlaps (" + Number_Format(len(badCoHz), 0, True) + ") saved to:\t" + logFile, 0)
                fh = open(logFile, "a")
                fh.write("\n\nQuery for components with horizon gaps or overlaps\n")
                fh.write("====================================================================================\n")
                fh.write("COKEY IN ('" + "', '".join(badCoHz) + "') \n\n")
                fh.write("\nTable of components with horizon gaps or overlaps\n")
                fh.write("MUKEY, COKEY, COMPNAME, MJRCOMP, HZNAME, HZDEPT, DIFF\n")

                for h in badHorizons:
                    fh.write(h + "\n")

                fh.close()

            # These components have restriction depths that are inconsistent with horizon depths
            # Note; these COKEYs will work with gSSURGO but not Soil Data Access or NASIS
            # If a component has restrictions but no horizon data, they will get flagged even if zero depth.
            #
            if len(dCr) > 0:
                PrintMsg(" \nComponents with horizon restriction discrepancies (" + Number_Format(len(dCr), 0, True) + ") saved to:\t" + logFile, 0)
                fh = open(logFile, "a")
                fh.write("\n\nQuery for components with horizon restriction discrepancies\n")
                fh.write("====================================================================================\n")
                fh.write("COKEY IN ('" + "', '".join(dCr.keys()) + "') \n\n")
                fh.write("\nTable of components with restriction depth discrepancies\n")
                fh.write("COKEY, HZDEPT\n")

                for cokey, hzdept in dCr.items():
                    fh.write(cokey + ", " + str(hzdept) + "\n")

                fh.close()

            os.startfile(logFile)

        else:
            PrintMsg(" \nNo data validation issues detected", 0)

        arcpy.ResetProgressor()
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
## ====================================== Main Body ==================================
# Import modules
import os, sys, string, re, locale, arcpy, traceback, collections
from arcpy import env
from datetime import datetime

try:
    arcpy.OverwriteOutput = True

    inputDB = arcpy.GetParameterAsText(0)            # Input gSSURGO database

    # Set location for temporary tables
    #outputDB = "IN_MEMORY"
    outputDB = env.scratchGDB

    # Name of mapunit level output table (global variable)
    theMuTable = os.path.join(inputDB, "MuTest")

    # Name of component level output table (global variable)
    theCompTable = os.path.join(inputDB, "Co_Test")

    # Set output workspace to same as the input table
    #env.workspace = os.path.dirname(arcpy.Describe(queryTbl).catalogPath)
    env.workspace = inputDB

    # Save record of any issues to a text file
    logFile = os.path.basename(inputDB)[:-4] + "_Problems.txt"  # filename based upon input gdb name
    logFile = os.path.join(os.path.dirname(inputDB), logFile)   # full path

    # Get the mapunit - sum of component percent for calculations
    dPct = GetSumPct(inputDB)
    if len(dPct) == 0:
        raise MyError, ""

    # Create initial set of query tables used for RZAWS, AWS and SOC
    if CreateQueryTables(inputDB, outputDB, 150.0, dPct) == False:
        raise MyError, ""


    PrintMsg(" \nValidation process complete for " + inputDB, 0)

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
