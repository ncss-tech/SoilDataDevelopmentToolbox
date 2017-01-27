# InterpDataMapping.py
#
# Steve Peaslee, National Soil Survey Center
#
# Creates tables and maps for a selected interpretation in the SDVATTRIBUTE table.
# Uses only major components and a 100% comppct base.
#
# Last revision 2015-10-07
#
# ALL: all components
# DCP: dominant component
# DCD: dominant condition

# Purpose: Generate mapunit polygon layer files based upon cointerp data
#
# Using a SSURGO geodatabase containing the COMPONENT and COINTERP tables, create a table containing
# the average values based upon the dominant component or dominant condition of each mapunit.
#
# Adapted from HorizonData Mapping
#
# component.cokey = chorizon.cokey and ( chorizon.hzdept_r BETWEEN 10 AND 40 OR chorizon.hzdepb_r BETWEEN 10 AND 40 )
#
# 09-03-2012 Adding information from sdvattribute table. NOTE! Need to add error-handling option for GetSDVAttributes function.
#
# Need to substitute aliasname for layername when sdvattribute has no record for this table-column combination
#
# 09-19-2012 Added INTERPHR column to the output component-level table
#
# 10-31-2012 Fixed problem with query table:sql that skipped 'Not Rated' rating class
#
# 12-03-2012 Added LocalPhase column to output component-level table
#
# 12-07-2012 Added Pivot table, still needs work on NULL, Not Rated and Not limited data elements. No symbology yet.
#            This table is created in the same geodatabase and is named 'Pivot' + name of the interp column. It contains
#            a column for each rating reason (as well as Not Rated) and a fuzzy value for each mapunit. It can be used to
#            create a separate map for each one of the rating reasons to show how they are spatially located.
#
# where RULEDEPTH = 0, INTERPHRC is the rating class (Very Limited, Somewhat Limited, etc) that appears in the SDV legend
#
# 05-29-2014 Need to look at arcpy.mapping for legend. Could accumulate mean fuzzy value for each rating class
# and use that to determine legend order for each class. Always put 'Not Rated' at the bottom. Would have to
# get symbology update method to work for Unique Values. Put this all into a separate function.
#
# Problem handling NCCPI. Need to look at the SDVATTRIBUTE table values to understand how
# that interp is different from others. The XML is different (colors, etc).
# Currently I can map the fuzzy values for the overall rating, but not the individual rating reasons.
# I do map each of the different NCCPI Crop ratings separately in the VALU2 table, but not the reasons.
#
# 2015-10-07 - Set visibility to False for each new layer and set overwriteOutput to True
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
        PrintMsg("Unhandled error in errorMsg method", 2)
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
        PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def GetUser():

    try:
        # Get computer login and try to format
        #
        envUser = arcpy.GetSystemEnvironment("USERNAME")

        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = env.User.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser

        return userName

    except:
        errorMsg()

        return ""

## ===================================================================================
def makeName(s):
    import re
    # create valid filename
    try:
        badchars= re.compile(r'[^A-Za-z0-9_. ]+|^\.|\.$|^ | $|^$')
        badnames= re.compile(r'(aux|com[1-9]|con|lpt[1-9]|prn)(\.|$)')
        name= badchars.sub('_', s)

        if badnames.match(name):
            name= '_' + name

        lc = "x"
        newname = ""

        for c in name:
            if c== "_" and c == lc:
                pass

            else:
                newname = newname + c

            lc = c

        return name

    except:
        errorMsg()


## ===================================================================================
def ValidateName(inputName):
    # Remove characters from file name or table name that might cause problems
    try:
        #PrintMsg(" \nValidating input table name: " + inputName, 1)

        validName = ""
        validChars = " -_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        lastChar = "."
        charList = list()

        for s in inputName:
            if s in validChars:
                if  not (s == "_" and lastChar == "_"):
                    charList.append(s)

                elif lastChar != "_":
                    lastChar = s

        validName = "".join(charList)

        return validName

    except MyError, e:
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        try:
            arcpy.RemoveJoin_management(inputLayer, outputTbl)
            return ""

        except:
            return ""

## ===================================================================================
def FindField(theInput, chkField, bVerbose = False):
    # Check table or featureclass to see if specified field exists

    # 07-19-2011. Ran into problems working with a joined table with fully qualified field names.
    # My chkField is already fully qualified.

    try:
        if arcpy.Exists(theInput):
            #PrintMsg("\nGetting fields for " + theInput, 0)
            theDesc = arcpy.Describe(theInput)
            theFields = theDesc.Fields
            #theField = theFields.next()    # 9.2

            #while theField:    # 9.2
            for theField in theFields:  # 9.3
                # Get unqualified field name
                theNameList = arcpy.ParseFieldName(theField.Name)
                theCnt = len(theNameList.split(",")) - 1
                theFieldname = theNameList.split(",")[theCnt].strip()

                if theFieldname.upper() == chkField.upper() or theField.Name.upper() == chkField.upper():
                    return True

            if bVerbose:
                PrintMsg("Failed to find column " + chkField + " in " + theInput, 2)
                return False

        else:
            PrintMsg("\tInput layer not found", 0)
            return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateOutputTables(wksp, theMuTable, theCompTable, qTable, sdvAtt, outputField, aggregationMethod, dSDV):
    # Create the mapunit level and the component level tables
    # The new input field is created using adaptive code from another script.
    #
    try:
        # Create two output tables and add required fields
        try:
            # Try to handle existing output table if user has added it to ArcMap from a previous run
            if arcpy.Exists(theMuTable):
                arcpy.Delete_management(theMuTable)

            if arcpy.Exists(theCompTable):
                arcpy.Delete_management(theCompTable)

        except:
            PrintMsg("Output tables are in use and cannot be removed", 2)
            return False

        # get output workspace
        wksp = env.workspace

        #PrintMsg(" \nCreating lookup tables: " + theMuTable + " and " + theCompTable, 0)

        if os.path.dirname(theMuTable) == "":
            # create MapunitDC table in current workspace
            arcpy.CreateTable_management (wksp, theMuTable)
            arcpy.CreateTable_management(wksp, theCompTable)

        else:
            # create MapunitDC table in the geodatabase of the input layer
            arcpy.CreateTable_management(os.path.dirname(theMuTable), os.path.basename(theMuTable))
            arcpy.CreateTable_management(os.path.dirname(theCompTable), os.path.basename(theCompTable))

        # Get SDV information for this attribute
        theAlias = dSDV["attributename"]
        #PrintMsg(" \nSetting " + theInputField + " field precision to " + str(sdvPrecision) + " decimal places", 0)

        #arcpy.AddField_management(theCompTable, outputField, "TEXT", "", "", 254, theAlias)  # attempting to reorder Identify list
        arcpy.AddField_management(theMuTable, "MUKEY", "TEXT", "", "", "30", "Mapunit Key")
        arcpy.AddField_management(theCompTable, "MUKEY", "TEXT", "", "", "30", "Mapunit Key")
        arcpy.AddField_management(theMuTable, "COMPPCT_R", "SHORT", "", "", "", "Component Percent")
        arcpy.AddField_management(theCompTable, "COMPPCT_R", "SHORT", "", "", "", "Component Percent")

        if aggregationMethod == "Dominant Component":
            arcpy.AddField_management(theMuTable, "COMPNAME", "TEXT", "", "", "60", "Component Name")

        arcpy.AddField_management(theCompTable, "COMPNAME", "TEXT", "", "", "60", "Component Name")
        arcpy.AddField_management(theCompTable, "LOCALPHASE", "TEXT", "", "", 40, "Local Phase")

        arcpy.AddField_management(theMuTable, outputField, "TEXT", "", "", 254, theAlias)
        arcpy.AddField_management(theCompTable, outputField, "TEXT", "", "", 254, theAlias)
        arcpy.AddField_management(theMuTable, "INTERPHR", "FLOAT", "", "", "", "Fuzzy Number")
        arcpy.AddField_management(theCompTable, "INTERPHR", "FLOAT", "", "", "", "Fuzzy Number")

        if FindField(theMuTable, "Field1"):
            arcpy.DeleteField_management(theMuTable, "Field1")

        if FindField(theCompTable, "Field1"):
            arcpy.DeleteField_management(theCompTable, "Field1")

        arcpy.AddIndex_management(theMuTable, "MUKEY", outputField + "_Indx")
        arcpy.AddIndex_management(theCompTable, "MUKEY", outputField + "_Indx")

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def AddColumns(theMuTable, theCompTable, outputField, dRatingClasses):
    # Add columns to mu table for each unique rating reason
    # These will be populated with the sum of the component percent that have this limitation

    try:

        # create MapunitDC table in the geodatabase of the input layer
        #PrintMsg(" \nAdding new columns for rating reasons...", 0)

        i = 1
        rcs = dRatingClasses.keys()
        rcs.sort()

        for rc in rcs:
            #PrintMsg("\t" + str(rc), 0)

            if i < 10:
                v = "0" + str(i)

            else:
                v = str(i)

            newField = outputField + v
            dRatingClasses[rc] = newField
            rc = rc.replace(",","")
            #arcpy.AddField_management(theMuTable, newField, "SHORT", "", "", "", rc)  # Keep this for comppct only
            arcpy.AddField_management(theMuTable, newField, "SHORT", "", "", "", newField)  # Keep this for comppct only
            i += 1

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def MapRatingReasons(theDB, theMapunitLayer, theCompTable, cFlds, outputField, dRatingClasses):
    # Create a set of map layers based upon rating reasons
    #
    try:

        # First create Group Layer under which to store individual rating class map layers
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame

        grpLayerName = sdvAtt + " - Rating Reasons"
        testLayers = arcpy.mapping.ListLayers(mxd, grpLayerName, df)

        if len(testLayers) > 0:
            # If it exists, remove an existing group layer from previous run
            grpLayer = testLayers[0]
            PrintMsg(" \nRemoving old group layer", 1)
            arcpy.mapping.RemoveLayer(df, grpLayer)

        # Define new output group layer file (.lyr) to permanently save output
        grpFile = os.path.join(os.path.dirname(theDB), "Group_" + grpLayerName) + ".lyr"

        if arcpy.Exists(grpFile):
            arcpy.Delete_management(grpFile)

        # Use template lyr file stored in current script directory to create new Group Layer
        # This SDVGroupLayer.lyr file must be part of the install package along with
        # any used for symbology.
        grpLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_GroupLayer.lyr")

        if not arcpy.Exists(grpLayerFile):
            raise MyError, "Missing group layer file (" + grpLayerFile + ")"

        grpLayer = arcpy.mapping.Layer(grpLayerFile)
        grpLayer.visible = False
        grpLayer.name = grpLayerName
        grpLayer.description = "Group layer containing individual rating-reason layers for '" + sdvAtt + "'" \
        + "\r\nGreen means that a lower component percentage of the map unit has this condition. Red means a higher percentage."
        # dSDV["attributedescription"]
        arcpy.mapping.AddLayer(df, grpLayer, "TOP")
        grpLayer = arcpy.mapping.ListLayers(mxd, grpLayerName, df)[0]
        grpDesc = arcpy.Describe(grpLayer)

        if grpDesc.dataType.lower() != "grouplayer":
            raise MyError, "Problem with group layer"

        #PrintMsg(" \nAdded group layer...", 0)

        dPivotValues = dict()
        dPct = dict()
        # Create map layer files for each Rating Class

        desc = arcpy.Describe(theMapunitLayer)
        theFC = desc.baseName
        theFields = desc.fields
        PrintMsg(" \nSummarizing rating reasons...", 0)

        # Create relate between Component level rating table and MUPOLYGON featureclass
        #
        PrintMsg(" \nCreating relationshipclass using " + theFC + " and " + theCompTable, 0)
        env.workspace = theDB
        #time.sleep(1)
        rcName = "x" + theCompTable.title() + "_" + theFC
        arcpy.CreateRelationshipClass_management(theFC, theCompTable, rcName, "SIMPLE", "> " + sdvAtt + " (" + suffix + ")", "< " + theCompTable, "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

        with arcpy.da.SearchCursor(theCompTable, cFlds) as cCursor:
            # Use cursor to load component-level interp data into a dictionary

            for cRec in cCursor:
                mukey, compPct, compName, localPhase, rClass, fuzzyRating = cRec
                # dictionary keys are a tuple of the mukey and the rating reason
                key = (mukey, rClass)

                # accumulate sum of comppct for each mapunit-limitation combination in the dPct dictionary
                try:
                    pct = dPct[key]
                    dPct[key] = pct + compPct

                except:
                    dPct[key] = compPct

        #
        # Create Pivot table using Rating Reasons

        bPivot = AddColumns(theMuTable, theCompTable, outputField, dRatingClasses)

        if bPivot == False:
            raise MyError, ""

        flds = arcpy.ListFields(theMuTable, outputField + "*")
        pFlds = ["mukey"]

        for fld in flds:
            if fld.type != "OID":
                if len(fld.name) > len(outputField):
                    #PrintMsg("\t" + fld.name, 1)
                    pFlds.append(fld.name)

        iFlds = len(pFlds)

        # Load dictionary data into sort of Pivot Table

        with arcpy.da.UpdateCursor(theMuTable, pFlds) as pCursor:

            for pRec in pCursor:
                # Process each map unit in the table
                #
                interp_sum = None
                bNotLimited = False
                theMukey = pRec[0]

                for theRating in dRatingClasses:
                    # Loop through each field
                    #PrintMsg("\t" + theRating, 1)
                    fieldName = dRatingClasses[theRating]
                    fldIndx = pFlds.index(fieldName)

                    if (theMukey, theRating) in dPct:
                        # this means that there is at least one value for the mapunit
                        sumPct = round(dPct[(theMukey, theRating)], 3)  #

                        if theRating == "Not limited":
                            bNotLimited = True

                        if interp_sum is not None:
                            if theRating != "Not limited":
                                interp_sum += sumPct

                        else:
                            if theRating != "Not limited":
                                interp_sum = sumPct

                        pRec[fldIndx] = sumPct

                if interp_sum is not None:
                    interp_sum = round(interp_sum, 3)

                elif bNotLimited:
                    interp_sum = 0

                pCursor.updateRow(pRec)

        PrintMsg(" \n", 0)

        # Try making query view
        inputTables = [theMapunitLayer,  os.path.join(theDB, theMuTable)]

        for theRating in sorted(dRatingClasses):
            # failing to create some layers. Try validating layer name...
            cleanRating = ValidateName(theRating)

            # assuming that the dRatingClasses dictionary is storing the field names in correct order
            theFieldName = dRatingClasses[theRating]      # this is actual field name for that rating class

            # Name the table after the original rating field that SDV uses (modified to remove some chars)
            layerTitle = outputField.title() + " - " + cleanRating
            #theLayerFileName = os.path.join(os.path.dirname(theDB), outputField.title() + " " + cleanRating) + ".lyr"

            #if arcpy.Exists(theLayerFileName):
            #    arcpy.Delete_management(theLayerFileName)

            if arcpy.Exists(layerTitle):
                # Cleanup previous layer from TOC
                arcpy.Delete_management(layerTitle)

            # Create list of fieldinfo for the input mapunit polygon layer
            mapunitFields = list()

            for theField in theFields:
                #PrintMsg("\tField " + theField.name + " - " + theField.aliasName, 0)
                if theField.type != "OID":
                    mapunitFields.append((theFC + "." + theField.name, theField.aliasName))

            theQueryFields = list()
            for fldinfo in mapunitFields:
                theQueryFields.append(fldinfo)

            #PrintMsg(" \nRating field: " + theMuTable + "." + theFieldName, 1)
            theQueryFields.append((theMuTable + "." + theFieldName, theRating))
            theSQL =  theFC + ".MUKEY = " + theMuTable + ".MUKEY AND " + theMuTable + "." + theFieldName + " > 0"

            #PrintMsg("\tCreating map layer: " + layerTitle, 0)
            arcpy.MakeQueryTable_management(inputTables, layerTitle, "USE_KEY_FIELDS", "", theQueryFields, theSQL)
            layerCnt = int(arcpy.GetCount_management(layerTitle).getOutput(0))

            if layerCnt > 0:
                layerDesc = arcpy.Describe(layerTitle)  # bug workaround to make the new featurelayer visible to arcpy.mapping
                PrintMsg("\tCreated '" + layerTitle + "' with " + Number_Format(layerCnt, 0, True) + " features", 0)
                lyr = arcpy.mapping.Layer(layerTitle)
                lyr.visible = False

                # Adding symbology for graduated colors
                stopLight = os.path.join(os.path.dirname(sys.argv[0]), "SDV_StopLight0to100.lyr")
                symLayer = arcpy.mapping.Layer(stopLight)
                arcpy.mapping.UpdateLayer(df, lyr, symLayer, True)
                lyr.symbology.valueField = os.path.basename(theMuTable) + "." + theFieldName
                arcpy.mapping.AddLayerToGroup(df, grpLayer, lyr, "BOTTOM")


        arcpy.SaveToLayerFile_management(grpLayer, grpFile)
        PrintMsg(" \nSaved group layer to " + grpFile, 0)

        return True

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

## =============================================================================
def GetSDVAttributes(sdvAtt):
    # query sdvattribute table for settings
    try:
        dSDV = dict()

       # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(theDB, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        sql1 = "attributename = '" + sdvAtt + "'"

        with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
            rec = cur.next()  # just reading first record
            i = 0
            for val in rec:
                dSDV[flds[i]] = val
                #PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                i += 1

        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        if dSDV["nasisrulename"] is not None and dSDV["nasisrulename"][0:5] == "NCCPI":
            dSDV["attributecolumnname"] = "interphr"

        # Temporary workaround for sql whereclause. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = "UPPER(" + sqlParts[0] + ") = " + sqlParts[1].upper()

        return dSDV

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def MaketheQueryTable(theDB, sdvAtt):
    # For major components, create query table containing information from
    # component and chorizon tables
    # return name of querytable. Failure returns an empty string for the table name.

    try:
        # Join chorizon table with component table
        # MakeQueryTable_management <in_table;in_table...> <out_table> <USE KEY FIELDS | ADD VIRTUAL KEY FIELD | NO KEY FIELD> {in_key_field;in_key_field...} <Field {Alias};Field {Alias}...> {where_clause}
        interpTable = os.path.join(theDB, "cointerp")
        compTable = os.path.join(theDB, "component")

        muTable = os.path.join(theDB, "mapunit")
        legendTable = os.path.join(theDB, "legend")

        inTables = [legendTable, muTable, compTable, interpTable]

        PrintMsg(" \nGetting data from component and cointerp tables...", 0)

        # interphr is the fuzzy value being used
        theFields = "LEGEND.AREASYMBOL AREASYMBOL;" + \
        "MAPUNIT.MUSYM MUSYM; MAPUNIT.MUNAME MUNAME;" + \
        "COMPONENT.MUKEY MUKEY;COMPONENT.COKEY COKEY;COMPONENT.COMPPCT_R COMPPCT_R;COMPONENT.COMPNAME COMPNAME;COMPONENT.LOCALPHASE LOCALPHASE;" + \
        "COINTERP.SEQNUM SEQNUM;" + \
        "COINTERP.RULENAME RULENAME;" + \
        "COINTERP.RULEDEPTH RULEDEPTH;" + \
        "COINTERP.INTERPHR INTERPHR;" + \
        "COINTERP.INTERPHRC INTERPHRC"

        qTable = "InterpQuery"

        #if arcpy.Exists(qTable):
        #    PrintMsg(" \nRemoving query table " + qTable, 1)
        #    arcpy.Delete_management(qTable)

        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)

        for tableView in tableViews:
            if tableView.datasetName == qTable or tableView.name == qTable:
                PrintMsg(" \nRemoving query table " + tableView.name, 1)
                #arcpy.mapping.RemoveTableView(df, tableView)
                arcpy.Delete_management(tableView.name)

        if bMajor == True:
            theSQL = "COMPONENT.COMPPCT_R > 0 AND COMPONENT.MAJCOMPFLAG = 'Yes' AND LEGEND.LKEY = MAPUNIT.LKEY AND MAPUNIT.MUKEY = COMPONENT.MUKEY AND COMPONENT.COKEY = COINTERP.COKEY AND COINTERP.MRULENAME = '" + dSDV["nasisrulename"]  + "'"

        else:
            theSQL = "COMPONENT.COMPPCT_R > 0 AND LEGEND.LKEY = MAPUNIT.LKEY AND MAPUNIT.MUKEY = COMPONENT.MUKEY AND COMPONENT.COKEY = COINTERP.COKEY     AND COINTERP.MRULENAME = '" + dSDV["nasisrulename"]  + "'"

        # PrintMsg(" \ntheSQL: " + theSQL, 0)
        # Things to be aware of with MakeQueryTable:
        # USE_KEY_FIELDS does not create OBJECTID field. Lack of OBJECTID precludes sorting on Mukey.
        # ADD_VIRTUAL_KEY_FIELD creates OBJECTID, but qualifies field names using underscore (eg. COMPONENT_COKEY)
        #
        arcpy.MakeQueryTable_management(inTables, qTable, "ADD_VIRTUAL_KEY_FIELD","",theFields, theSQL)

        return qTable

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def MakeReport(tableView):
    # Take InterpQuery table and create a report

    try:

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame

        tblName = "InterpQuery"  # table containing pre-aggregated data in gSSURGO database
        #legendTbl = os.path.join(gdb, "legend")    # table containing legend.areaname

        # Get SDV Rating table information
        fmFields = list()
        tblDesc = arcpy.Describe(tableView)
        ratingFields = tblDesc.fields
        gdb = os.path.dirname(tblDesc.catalogPath)
        ratingField = ratingFields[-1]  # assume the last field is the rating
        ratingType = ratingFields[-1].type.lower()
        ratingFieldName = ratingField.name.upper().encode('ascii')

        # Get the path for the template MXD being used to create the cover page
        mxdName = "SDV_MapDescription_Landscape.mxd"
        mxdFile = os.path.join(os.path.dirname(sys.argv[0]), mxdName)

        # Get SDV narrative and settings used from the soil map layer
        layerDesc = dSDV["attributedescription"]

        # Open mxd with text box and update with layer description
        textMXD = arcpy.mapping.MapDocument(mxdFile)
        textDF = textMXD.activeDataFrame
        textBox = arcpy.mapping.ListLayoutElements(textMXD, "TEXT_ELEMENT", "Description Text Box*")[0]
        textMXD.title = dSDV["attributename"]
        textBox.text = layerDesc
        textPDF = os.path.join(env.scratchFolder, "description.pdf")
        arcpy.mapping.ExportToPDF(textMXD, textPDF)

        # Get report template file fullpath (.rlf) and import current SDV_Data table into it
        templateName = "SDV_InterpReasons.rlf"
        template = os.path.join(os.path.dirname(sys.argv[0]), templateName)
        reportPDF = os.path.join(os.path.dirname(gdb), dSDV["attributename"] + "_Interp.pdf")

        if arcpy.Exists(reportPDF):
            arcpy.Delete_management(reportPDF, "FILE")

        # Set some of the parameters for the ExportReport command
        dso = "DEFINITION_QUERY"
        title = dSDV["attributename"] + " Rating Reasons"
        start = None
        range = None
        extent = None
        fm = {"LEGEND_AREASYMBOL":"LEGEND_AREASYMBOL","COMPONENT_MUKEY":"COMPONENT_MUKEY", "MAPUNIT_MUSYM":"MAPUNIT_MUSYM", "MAPUNIT_MUNAME":"MAPUNIT_MUNAME", "COMPONENT_COMPNAME":"COMPONENT_COMPNAME", "COMPONENT_COMPPCT_R":"COMPONENT_COMPPCT_R", "COMPONENT_LOCALPHASE":"COMPONENT_LOCALPHASE", "COINTERP_RULENAME":"COINTERP_RULENAME", "COINTERP_INTERPHR":"COINTERP_INTERPHR"}
        #report_definition_query
        rdq = "COINTERP_RULEDEPTH > 0 AND COINTERP_INTERPHR IS NOT NULL"

        PrintMsg(" \nUsing report template: " + template, 0)
        #PrintMsg(" \nUsing field mapping: " + str(fm), 0)
        PrintMsg(" \nRating data type: " + ratingType, 0)

        #PrintMsg(" \nSkipping report...", 1)
        #return True


        arcpy.SetProgressorLabel("Running report for '" + title + "' ....")
        PrintMsg(" \nImporting table into report template...", 0)

        # Create PDF for tabular report
        arcpy.mapping.ExportReport(tableView, template, reportPDF, dataset_option=dso, report_definition_query=rdq, report_title=title, field_map=fm)

        # Open the report PDF for editing
        pdfDoc = arcpy.mapping.PDFDocumentOpen(reportPDF)

        # Insert the title page PDF with narrative that created using the MXD layout
        pdfDoc.insertPages(textPDF, 1)

        # Update some of the PDF settings and metadata properties
        keyWords = 'gSSURGO;soil interpretation'
        userName = GetUser()

        pdfDoc.updateDocProperties(pdf_title=title, pdf_author=userName, pdf_subject="Soil Map", pdf_keywords=keyWords, pdf_layout="SINGLE_PAGE", pdf_open_view="USE_NONE")
        pdfDoc.saveAndClose()

        # Remove the 'SDV_Data' table view
        #arcpy.mapping.RemoveTableView(df, tableView)

        if arcpy.Exists(reportPDF):
            arcpy.SetProgressorLabel("Report complete")
            PrintMsg(" \nReport complete (" + reportPDF + ")\n ", 0)
            os.startfile(reportPDF)

        return True


    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False


## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import arcpy, sys, string, os, re, locale, traceback, time
from arcpy import env

try:
    # Create geoprocessor object
    env.overwriteOutput = True

    theMapunitLayer = arcpy.GetParameterAsText(0)          # mapunit polygon layer used as basis for join and layers
    sdvAtt = arcpy.GetParameter(2)                      # input field to categorize (ECOCLASSNAME or ECOCLASSID...)
    aggregationMethod = arcpy.GetParameter(3)              # Dominant Condition or Dominant Component
    bMajor = arcpy.GetParameter(4)                         # Use only major components (default = False)

    #
    # first get path for input featureclass
    desc = arcpy.Describe(theMapunitLayer)
    theDB = os.path.dirname(desc.CatalogPath)

    # next find out if this is a workspace or a featuredataset
    desc = arcpy.Describe(theDB)
    theDataType = desc.DataType

    # get the workspace
    if theDataType.upper() == "FEATUREDATASET":
      # try going up one more level in the path to get the geodatabase
      theDB = os.path.dirname(theDB)

    # if featureclass workspace is not a geodatabase, bail out
    if not (theDB.endswith(".gdb") or theDB.endswith(".mdb")):
      errMsg = "Invalid workspace for input mapunit polygon featureclass"
      raise MyError, errMsg

    # Setup arcpy.mapping object
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame


    env.workspace = theDB


    # Try to set output field parameters according to information in the SDVATTRIBUTE table
    # If the interp is not found in the SDVATTRIBUTE table, use the outputFieldName
    dSDV = GetSDVAttributes(sdvAtt)

    # Create query table using component and chorizon tables
    qTable = MaketheQueryTable(theDB, sdvAtt)

    if qTable == "":
        # bailout of script. there should be an error message generated by MaketheQueryTable
        raise MyError, "Failed to get query table"



    outputField = dSDV["resultcolumnname"]
    attributeName = dSDV["attributename"]
    xmlString = dSDV["maplegendxml"]

    #PrintMsg(" \nOutput Field: " + str(outputField) + ": " + str(attributeName), 1)

    dRatingClasses = dict()  # unique list of rating classes which will be used to create a layer for each limitation
    iRC = 1

    # Create output tables, one for mapunit summary and one for all components
    if aggregationMethod == "Dominant Condition":
        suffix = "DCD"

    elif aggregationMethod == "Dominant Component":
        suffix = "DCP"

    theMuTable = "Mu_" + outputField + "_" + suffix
    theMuTable = theMuTable.replace(".","_")

    # output table name for component information
    theCompTable = "Co_" + outputField + "_" + suffix
    theCompTable = theCompTable.replace(".","_")

    if CreateOutputTables(theDB,theMuTable, theCompTable, qTable, sdvAtt, outputField, aggregationMethod, dSDV) == False:
        # should be an error message generated by CreateOutputTables
        raise MyError, ""

    # Create MapunitDCD table containing dominant condition rating for each mapunit
    #
    PrintMsg(" \nAggegating data to the mapunit level...", 0)

    flds = arcpy.ListFields(theCompTable)
    cFlds = list()
    for fld in flds:
        if fld.type != "OID":
            cFlds.append(fld.name)

    flds = arcpy.ListFields(theMuTable)
    mFlds = list()
    for fld in flds:
        if fld.type != "OID":
            mFlds.append(fld.name)

    # Check fields in qTable
    qDesc = arcpy.Describe(qTable)
    #qFields = qDesc.fields
    #for qFld in qFields:
    #    PrintMsg("\t" + qFld.name, 1)

    # Dominant Condtion Aggregation Section
    #
    if aggregationMethod == "Dominant Condition":

        # Create dictionary key as MUKEY:INTERPHRC
        # Need to look through the component rating class for ruledepth = 0
        # and sum up COMPPCT_R for each key value
        #
        dVals = dict()  # dictionary containing sum of comppct for each MUKEY:RATING combination
        dDCD  = dict()  # dictionary containing dominant condition percent for each MUKEY
        dFuzzy = dict()

        qFields = ["COMPONENT_MUKEY", "COMPONENT_COMPPCT_R", "COMPONENT_COMPNAME", "COMPONENT_LOCALPHASE", "COINTERP_RULEDEPTH", "COINTERP_INTERPHR", "COINTERP_INTERPHRC", "COMPONENT_COKEY"]
        sortFields = "ORDER BY COMPONENT_COKEY ASC, COMPONENT_COMPPCT_R DESC"
        sqlClause = (None, sortFields)

        # Create 'Co' table containing component-level interp data
        # Fields: MUKEY, COMPPCT_R, COMPNAME, LOCALPHASE, outputField, INTERPHR
        # data comes from query table
        #
        # At this point, qTable is a string
        #
        with arcpy.da.SearchCursor(qTable, qFields, sql_clause=sqlClause) as qCursor:
            cCursor = arcpy.da.InsertCursor(theCompTable, cFlds)

            for qRec in qCursor:
                theMukey, compPct, compName, localPhase, ruleDepth, fuzzyValue, ratingClass, theCokey = qRec
                key = (theMukey, ratingClass)

                if ruleDepth == 0:
                    # This record contains the component rating class (INTERPHRC) such as 'Not limited'
                    # It is defined by ruledepth = 0
                    # This is where the the mapunit ratings are summarized

                    # Need to investigate this value
                    # I think I'm only saving the last value because there are more than one ruledepth zero records
                    dFuzzy[key] = fuzzyValue  # store fuzzy value for ruledepth zero

                    if key in dVals:
                        sumPct = dVals[key]
                        dVals[key] = sumPct + compPct

                    else:
                        # initialize the mapunit rating
                        dVals[key] = compPct

                    if ratingClass == "Not limited":
                        # MUKEY, COMPPCT_R, COMPNAME, LOCALPHASE, [RATING], INTERPHR
                        cRec = theMukey, compPct, compName, localPhase, ratingClass, 0.00
                        cCursor.insertRow(cRec)

                else:
                    # these are the reasons, write them to the component table
                    # the rating classes will NOT be written to the table
                    if not fuzzyValue is None:
                        fuzzyValue = round(fuzzyValue, 3)

                    cRec = theMukey, compPct, compName, localPhase, ratingClass, fuzzyValue
                    cCursor.insertRow(cRec)
                    #PrintMsg("\t" + theMukey + ", " + ratingClass + ", " + str(fuzzyValue), 1)

                    # Creating list of Interp Rating Classes found in this database and the name of the
                    # indexed field that will be used to store the fuzzy value in.
                    if not ratingClass in dRatingClasses and not ratingClass.startswith("Not rated;"):
                        #PrintMsg("\tNew entry for dRatingClasses: " + str(ratingClass), 1)
                        dRatingClasses[ratingClass] = outputField + str(iRC)
                        iRC += 1

        # Aggregation (dominant condtion) iteration
        #
        # Iterate through the dVals dictionary, find the Dominant rating class for each mukey
        # and add it to the dDCD dictionary

        #PrintMsg(" \nFound " + Number_Format(len(dVals), 0, True) + " combinations of mapunit:rating class", 0)

        for key, thePct in dVals.items():
            theMukey, ratingClass = key
            #thePct = dVals[key]
            fuzzyValue = dFuzzy[key]

            if theMukey in dDCD:
                # dDCD dictionary already has an initial value for dominant rating class
                # Check to see if the current percentage is higher

                if thePct > dDCD[theMukey][0]:
                    # Found a new dominant rating for this mapunit
                    dDCD[theMukey] = (thePct, ratingClass, fuzzyValue)

            else:
                # Initializing the dominant rating using the first encountered
                dDCD[theMukey] = (thePct, ratingClass, fuzzyValue)

        # Create 'Mu' table using aggregate data from dictionary
        #
        del qCursor
        del cCursor

        with arcpy.da.InsertCursor(theMuTable, mFlds) as mCursor:
            iComps = len(dDCD)

            for key in dDCD.keys():
                # Write to the mapunit table which will then be joined to the polygon featurelayer
                thePct, ratingClass, fuzzyValue = dDCD[key]
                # Print results of dominant condition - mapunit information

                try:
                    fuzzyValue = round(fuzzyValue, 2)

                except:
                    pass

                #PrintMsg("\t" + key + "," + str(dDCD[key][0]) + "," +  ratingClass + "," + str(fuzzyValue), 1)
                newRec = key, thePct, ratingClass, fuzzyValue
                mCursor.insertRow(newRec)

    # Dominant Component Aggregation
    #
    elif aggregationMethod == "Dominant Component":
        #
        # Dominant condition aggregation
        # An edit session is required because two cursors are open at once
        #
        qFields = ["COMPONENT_MUKEY", "COMPONENT_COMPPCT_R", "COMPONENT_COMPNAME", "COMPONENT_LOCALPHASE", "COINTERP_RULEDEPTH", "COINTERP_INTERPHR", "COINTERP_INTERPHRC"]

        PrintMsg(" \nDominant component aggregation. Need to add dRatingClasses dictionary...", 0)

        with arcpy.da.Editor(theDB):
            sortFields = "ORDER BY COMPONENT_MUKEY ASC, COMPONENT_COMPPCT_R DESC"
            sqlClause = (None, sortFields)
            qCursor = arcpy.da.SearchCursor(qTable, qFields, sql_clause=sqlClause)
            mCursor = arcpy.da.InsertCursor(theMuTable, mFlds)
            cCursor = arcpy.da.InsertCursor(theCompTable, cFlds)
            lastMukey = "xxxxxx"
            dDCD  = dict()  # just to store list of mukeys

            for qRec in qCursor:
                # first cokey encountered for each mapunit should be the dominant one
                theMukey, compPct, compName, localPhase, ruleDepth, fuzzyValue, ratingClass = qRec

                if ruleDepth == 0:
                    # this is the rating class, work on mapunit interp table

                    if theMukey != lastMukey:
                        lastMukey = theMukey
                        # MUKEY,COMPPCT_R,COMPNAME,DwellWB,INTERPHR
                        newRec = theMukey, compPct, compName, ratingClass, fuzzyValue
                        dDCD[theMukey] = 0
                        mCursor.insertRow(newRec)

                else:
                    # these are the reasons, write them to the component interp table
                    # MUKEY,COMPPCT_R,COMPNAME,LOCALPHASE,DwellWB,INTERPHR
                    cRec = theMukey, compPct, compName, localPhase, ratingClass, fuzzyValue
                    cCursor.insertRow(cRec)
                    #if fuzzyValue == "Not rated":
                    #PrintMsg("\t" + theMukey + ", " + ratingClass + ", " + str(fuzzyValue), 1)

    else:
        err = "Invalid aggregation method"
        raise MyError, err

    # Reset reference to group layer. Having problems...
    # Create 'Pivot table' from component level data
    #
    # Map rating reasons as individual layers based upon sum of component percent
    bPivotMaps = MapRatingReasons(theDB, theMapunitLayer, theCompTable, cFlds, outputField, dRatingClasses)

    if bPivotMaps:
        # Check to make sure the query table has data
        # at this point, qTable is a string
        theResult = arcpy.GetCount_management(qTable)
        iCnt = int(theResult.getOutput(0))

        if iCnt > 0:
            # Try to get the Query table through arcpy.mapping
            xDesc = arcpy.Describe(qTable)
            tableView = arcpy.mapping.TableView(qTable)
            tableView.name = dSDV["attributename"]  # table name is attribute name
            arcpy.mapping.AddTableView(df, tableView)
            PrintMsg(" \nAdded table '" + tableView.name + "'", 0)

        else:
            raise MyError, "Failed to retrieve any records for the query table"

        #arcpy.mapping.RemoveTableView(tableView)
        #arcpy.Delete_management(qTable)

    PrintMsg(" \n", 0)

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
