# gSSURGO_ExportRasters.py
#
# Steve Peaslee, National Soil Survey Center
# 2019-10-07
#
# Purpose: Batch mode conversion of multiple gSSURGO soil maps into raster (TIFF or FGDB raster).
#
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
                arcpy.AddMessage("    ")
                arcpy.AddError(string)

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

        return "???"


## ===================================================================================
def get_random_color(pastel_factor=0.5):
    # Part of generate_random_color
    try:
        newColor = [int(255 *(x + pastel_factor)/(1.0 + pastel_factor)) for x in [random.uniform(0,1.0) for i in [1,2,3]]]

        return newColor

    except:
        errorMsg()
        return [0,0,0]

## ===================================================================================
def color_distance(c1,c2):
    # Part of generate_random_color
    return sum([abs(x[0] - x[1]) for x in zip(c1,c2)])

## ===================================================================================
def generate_new_color(existing_colors, pastel_factor=0.5):
    # Part of generate_random_color
    try:
        #PrintMsg(" \nExisting colors: " + str(existing_colors) + "; PF: " + str(pastel_factor), 1)

        max_distance = None
        best_color = None

        for i in range(0,100):
            color = get_random_color(pastel_factor)


            if not color in existing_colors:
                color.append(255) # add transparency level
                return color

            best_distance = min([color_distance(color,c) for c in existing_colors])

            if not max_distance or best_distance > max_distance:
                max_distance = best_distance
                best_color = color
                best_color.append(255)

            return best_color

    except:
        errorMsg()
        return None

## ===================================================================================
def rand_rgb_colors(num):
    # Generate a random list of rgb values
    # 2nd argument in generate_new_colors is the pastel factor. 0 to 1. Higher value -> more pastel.

    try:
        colors = []
        # PrintMsg(" \nGenerating " + str(num - 1) + " new colors", 1)

        for i in range(0, num):
            newColor = generate_new_color(colors, 0.1)
            colors.append(newColor)

        # PrintMsg(" \nColors: " + str(colors), 1)

        return colors

    except:
        errorMsg()
        return []

## ===================================================================================
def UpdateMetadata(theGDB, target, sdvLayer, description, iRaster):
    #
    # Used for non-ISO metadata
    #
    # Process:
    #     1. Read gSSURGO_MapunitRaster.xml
    #     2. Replace 'XX" keywords with updated information
    #     3. Write new file xxImport.xml
    #     4. Import xxImport.xml to raster
    #
    # Problem with ImportMetadata_conversion command. Started failing with an error.
    # Possible Windows 10 or ArcGIS 10.5 problem?? Later had to switch back because the
    # alternative ImportMetadata_conversion started for failing with the FY2018 rasters without any error.
    #
    # Search for keywords:  xxSTATExx, xxSURVEYSxx, xxTODAYxx, xxFYxx
    #
    try:
        PrintMsg("\tUpdating raster metadata...")
        arcpy.SetProgressor("default", "Updating raster metadata")

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        mdTranslator = os.path.join(installPath, prod)  # This file is not being used

        # Define input and output XML files
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info
        xmlPath = os.path.dirname(sys.argv[0])
        mdExport = os.path.join(xmlPath, "gSSURGO_PropertyRaster.xml") # original template metadata in script directory
        #PrintMsg(" \nParsing gSSURGO template metadata file: " + mdExport, 1)

        #PrintMsg(" \nUsing SurveyInfo: " + str(surveyInfo), 1)

        # Cleanup output XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        # Get replacement value for the search words
        #
        stDict = StateNames()
        st = os.path.basename(theGDB)[8:-4]

        if st in stDict:
            # Get state name from the geodatabase
            mdState = stDict[st]

        else:
            # Leave state name blank. In the future it would be nice to include a tile name when appropriate
            mdState = ""

        # Update metadata file for the geodatabase
        #
        # Query the output SACATALOG table to get list of surveys that were exported to the gSSURGO
        #
        saTbl = os.path.join(theGDB, "sacatalog")
        expList = list()

        with arcpy.da.SearchCursor(saTbl, ("AREASYMBOL", "SAVEREST")) as srcCursor:
            for rec in srcCursor:
                expList.append(rec[0] + " (" + str(rec[1]).split()[0] + ")")
                
        surveyInfo = ", ".join(expList)
        
        #PrintMsg(" \nUsing this string as a substitute for xxSTATExx: '" + mdState + "'", 1)
        
        # Set date strings for metadata, based upon today's date
        #
        d = datetime.date.today()
        today = str(d.isoformat().replace("-",""))
        #PrintMsg(" \nToday replacement string: " + today, 1)

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        #PrintMsg(" \nFY replacement string: " + str(fy), 1)

        # Process gSSURGO_MapunitRaster.xml from script directory
        tree = ET.parse(mdExport)
        root = tree.getroot()

        # new citeInfo has title.text, edition.text, serinfo/issue.text
        citeInfo = root.findall('idinfo/citation/citeinfo/')

        if not citeInfo is None:
            # Process citation elements
            # title, edition, issue
            #
            for child in citeInfo:
                PrintMsg("\t\t" + str(child.tag), 0)
                
                if child.tag == "title":
                    if child.text.find('xxTITLExx') >= 0:
                        # Insert layer name here

                        if mdState != "":
                            newTitle = sdvLayer + " - " + mdState
                            #PrintMsg("\t\tUpdating title to: " + newTitle, 1)
                            #child.text = child.text.replace('xxSTATExx', mdState)
                            child.text = newTitle

                        else:
                            child.text = sdvLayer

                    else:
                        child.text = "Map Unit Raster " + str(iRaster) + "m"

                elif child.tag == "edition":
                    if child.text == 'xxFYxx':
                        #PrintMsg("\t\tReplacing xxFYxx", 1)
                        child.text = fy

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            #PrintMsg("\t\tReplacing xxFYxx", 1)
                            subchild.text = fy

        # Update place keywords
        ePlace = root.find('idinfo/keywords/place')

        if not ePlace is None:
            PrintMsg("\t\tplace keywords", 0)

            for child in ePlace.iter('placekey'):
                if child.text == "xxSTATExx":
                    #PrintMsg("\t\tReplacing xxSTATExx", 1)
                    child.text = mdState

                elif child.text == "xxSURVEYSxx":
                    #PrintMsg("\t\tReplacing xxSURVEYSxx", 1)
                    child.text = surveyInfo

        # Update credits
        eIdInfo = root.find('idinfo')
        if not eIdInfo is None:
            PrintMsg("\t\tcredits", 0)

            for child in eIdInfo.iter('datacred'):
                sCreds = child.text

                if sCreds.find("xxSTATExx") >= 0:
                    #PrintMsg("\t\tcredits " + mdState, 0)
                    child.text = child.text.replace("xxSTATExx", mdState)
                    #PrintMsg("\t\tReplacing xxSTATExx", 1)

                if sCreds.find("xxFYxx") >= 0:
                    #PrintMsg("\t\tcredits " + fy, 0)
                    child.text = child.text.replace("xxFYxx", fy)
                    #PrintMsg("\t\tReplacing xxFYxx", 1)

                if sCreds.find("xxTODAYxx") >= 0:
                    #PrintMsg("\t\tcredits " + today, 0)
                    child.text = child.text.replace("xxTODAYxx", today)
                    #PrintMsg("\t\tReplacing xxTODAYxx", 1)


        idAbstract = root.find('idinfo/descript/abstract')
        
        if not idAbstract is None:
            PrintMsg("\t\tabstract", 0)
            
            ip = idAbstract.text

            if ip.find("xxABSTRACTxx") >= 0:
                description = description
                idAbstract.text = ip.replace("xxABSTRACTxx", description)
                #PrintMsg("\t\tReplacing xxABSTRACTxx", 1)

        idPurpose = root.find('idinfo/descript/purpose')
        
        if not idPurpose is None:
            PrintMsg("\t\tpurpose", 0)
            
            ip = idPurpose.text

            if ip.find("xxFYxx") >= 0:
                idPurpose.text = ip.replace("xxFYxx", fy)
                #PrintMsg("\t\tReplacing xxFYxx", 1)
                

        #PrintMsg(" \nSaving template metadata to " + mdImport, 1)

        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        # Using three different methods with the same XML file works for ArcGIS 10.1
        #
        #PrintMsg(" \nImporting metadata " + mdImport + " to " + target, 1)
        arcpy.MetadataImporter_conversion(mdImport, target)  # This works. Raster now has metadata with 'XX keywords'. Is this step neccessary to update the source information?

        #PrintMsg(" \nUpdating metadata for " + target + " using file " + mdImport, 1)
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")  # Tool Validate problem here
        #arcpy.MetadataImporter_conversion(target, mdImport) # Try this alternate tool with Windows 10.

        # delete the temporary xml metadata file
        if os.path.isfile(mdImport):
            os.remove(mdImport)
            #pass

        # delete metadata tool logs
        logFolder = os.path.dirname(env.scratchFolder)
        logFile = os.path.basename(mdImport).split(".")[0] + "*"

        currentWS = env.workspace
        env.workspace = logFolder
        logList = arcpy.ListFiles(logFile)

        for lg in logList:
            arcpy.Delete_management(lg)

        env.workspace = currentWS

        return True

    except:
        errorMsg()
        False

## ===================================================================================
def CreateGroupLayer(grpLayerName, mxd, df):
    try:
        # Use template lyr file stored in current script directory to create new Group Layer
        # This SDVGroupLayer.lyr file must be part of the install package along with
        # any used for symbology. The name property will be changed later.
        #
        # arcpy.mapping.AddLayerToGroup(df, grpLayer, dInterpLayers[sdvAtt], "BOTTOM")
        #
        grpLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_GroupLayer.lyr")

        if not arcpy.Exists(grpLayerFile):
            raise MyError, "Missing group layer file (" + grpLayerFile + ")"

        testLayers = arcpy.mapping.ListLayers(mxd, grpLayerName, df)

        if len(testLayers) > 0:
            # Using existing group layer
            grpLayer = testLayers[0]

        else:
            # Group layer does not exist, make a new one
            grpLayer = arcpy.mapping.Layer(grpLayerFile)  # template group layer file
            grpLayer.visible = False
            grpLayer.name = grpLayerName
            grpLayer.description = "Group layer containing raster conversions from gSSURGO vector soil maps"
            grpLayer.visible = True
            arcpy.mapping.AddLayer(df, grpLayer, "TOP")

        #PrintMsg(" \nAdding group layer: " + str(grpLayer.name), 0)

        return grpLayer

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def CreateRasterLayers(sdvLayers, inputRaster, outputFolder, bPyramids, cellFactor, outputRes):
    # Merge rating tables from for the selected soilmap layers to create a single, mapunit-level table
    #
    try:
        # Get arcpy mapping objects
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        
        grpLayerName = "RASTER SOIL MAP CONVERSIONS"
        
        grpLayer = CreateGroupLayer(grpLayerName, mxd, df)

        if grpLayer is None:
            raise MyError, ""
            
        grpLayer = arcpy.mapping.ListLayers(mxd, grpLayerName, df)[0]  # ValueError'>: DataFrameObject: Unexpected error 
        
        if outputFolder != "":
            # if the outputFolder exists, create TIF files instead of file geodatabase rasters
            if not arcpy.Exists(outputFolder):
                outputFolder = ""
                
        env.overwriteOutput = True # Overwrite existing output tables
        env.pyramid = "NONE"
        arcpy.env.compression = "LZ77"

        env.pyramid = "NONE"

        # Tool validation code is supposed to prevent duplicate output tables

        # Get description and credits for each existing map layer
        mLayers = arcpy.mapping.ListLayers(mxd, "*", df)
        dMetadata = dict()  # Save original soil map description so that it can passed on to the raster layer

        for mLayer in mLayers:
            dMetadata[mLayer.name] = (mLayer.description, mLayer.credits)

        del mLayer, mLayers
        
        # Probably should make sure all of these input layers have the same featureclass
        #
        # first get path where input SDV shapefiles are located (using last one in list)
        # hopefully each layer is based upon the same set of polygons
        #
        # First check each input table to make sure there are no duplicate rating fields
        # Begin by getting adding fields from the input shapefile (lastShp). This is necessary
        # to avoid duplication such as MUNAME which may often exist in a county shapefile.

        chkFields = list()  # list of rating fields from SDV soil map layers (basenames). Use this to count dups.
        dLayerFields = dict()
        maxRecords = 0  # use this to determine which table has the most records and put it first
        maxTable = ""

        # Get FGDB raster from inputLayer
        rDesc = arcpy.Describe(inputRaster)
        iRaster = rDesc.meanCellHeight
        rSR = rDesc.spatialReference
        linearUnit = rSR.linearUnitName
                    
        # Iterate through each of the map layers and get the name of rating field from the join table
        #
        sdvLayers.reverse()
        
        for sdvLayer in sdvLayers:

            if sdvLayer.startswith("'") and sdvLayer.endswith("'"):
                sdvLayer = sdvLayers[i][1:-1]  # this is dropping first and last char in name for RUSLE2 maps..

            desc = arcpy.Describe(sdvLayer)
            dataType = desc.dataType

            if dataType == "FeatureLayer":
                gdb = os.path.dirname(desc.featureclass.catalogPath)

            elif dataType == "RasterLayer":
                gdb = os.path.dirname(desc.catalogPath)

            else:
                raise MyError, "Soil map datatype (" + dataType + ") not valid"

            allFields = desc.fields
            ratingField = allFields[-1]  # rating field should be the last one in the table
            fName = ratingField.name.encode('ascii')       # fully qualified name
            bName = ratingField.baseName.encode('ascii')   # physical name
            clipLen = (-1 * (len(bName))) - 1
            sdvTblName = fName[0:clipLen]
            sdvTbl = os.path.join(gdb, sdvTblName)
            fldType = ratingField.type
            fldLen = ratingField.length
            dLayerFields[sdvLayer] = (sdvTblName, fName, bName, fldType, fldLen)
            chkFields.append(bName)

        # Get information used in metadata
        i = 0
        layerIndx = 0
        layerCnt = len(sdvLayers)
        
        # Get user name and today's date for credits
        envUser = arcpy.GetSystemEnvironment("USERNAME")
        
        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = envUser.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser
                    
        d = datetime.date.today()
        toDay = d.isoformat()
        newCredits = "\r\nCreated by " + userName + " on " + toDay + " using script " + os.path.basename(sys.argv[0])

        # Process each map layer. This is the beginning of the big loop.
        #
        for sdvLayer in sdvLayers:
            layerIndx += 1
            arcpy.SetProgressorLabel("Creating raster layer from '" + sdvLayer + "'  (" + str(layerIndx) + " of " + str(layerCnt) + ")")
            PrintMsg(" \nCreating raster layer from '" + sdvLayer + "'  (" + str(layerIndx) + " of " + str(layerCnt) + ")", 0)
            sdvTblName, fName, bName, fldType, fldLen = dLayerFields[sdvLayer]
            newDescription = dMetadata[sdvLayer][0]
            newLayerName = sdvLayer + " (" + str(outputRes) + " " + linearUnit.lower() + " raster)"
            symTbl = os.path.join(gdb, "SDV_Symbology")
            
            if arcpy.Exists(symTbl):
                wc = "layername = '" + sdvLayer +"'"
                rendererInfo = ""

                with arcpy.da.SearchCursor(symTbl, ['maplegend'], where_clause=wc) as cur:
                    for rec in cur:
                        rendererInfo = json.loads(rec[0])
            
            if len(rendererInfo) > 0:
                rendererType = rendererInfo['type']
                #PrintMsg(" \nrendererType: " + rendererType, 1)

            else:
                if fldType == "String":
                    rendererType = "uniqueValue"

                else:
                    rendererType = ""

            dLegendInfo = dict()
                        
            if rendererType == 'uniqueValue':
                # Let's try writing a Lookup table that we can use later
                # Failing for non-irr cap class
                #
                lu = os.path.join(gdb, "Lookup")
                
                if arcpy.Exists(lu):
                    arcpy.Delete_management(lu)
                    
                arcpy.CreateTable_management(os.path.dirname(lu), os.path.basename(lu))
                arcpy.AddField_management(lu, "CELLVALUE", "LONG")
                arcpy.AddField_management(lu, bName, fldType, "#", "#", fldLen)  # join on this column, but add LABEL to class_name
                arcpy.AddField_management(lu, "LABEL", "TEXT", "#", "#", fldLen)

                if len(rendererInfo) > 0:
                    # Create Lookup table with color information
                    PrintMsg("\tBuilding Lookup table from map layer information", 0)
                    with arcpy.da.InsertCursor(lu, ["CELLVALUE", bName, "LABEL"]) as cur:

                        row = 0
                        #PrintMsg(" \nuniqueValueInfos: " + str(rendererInfo['uniqueValueInfos']), 1)
                                 
                        for valInfos in rendererInfo['uniqueValueInfos']:
                            row += 1
                            cRed, cGreen, cBlue, opacity = valInfos['symbol']['color']
                            lab = valInfos['label']
                            val = valInfos['value']
                            dLegendInfo[row] = (val, lab, (float(cRed) / 255.0), (float(cGreen) / 255.0), (float(cBlue) / 255.0), 1)
                            
                            try:
                                cur.insertRow([row, val, lab])

                            except:
                                # Need to leave NULL values out of Lookup
                                pass

                    #PrintMsg(" \ndLegendInfo: " + str(dLegendInfo), 1)
                    arcpy.AddIndex_management(lu, [bName], "Indx_" + bName)

                else:
                    # Create Lookup table without color information
                    # This may be slow for large map layers with a lot of polygons
                    PrintMsg(" \nBuilding Lookup table from scratch using SDV table " + bName + " column", 1)
                    whereClause = bName + " IS NOT NULL"
                    sqlClause = ("DISTINCT", "ORDER BY " + bName)
                    row = 0

                    # val, label, red, green, blue, opacity = dLegendInfo[cellValue]
                    # Get a list of random RGB colors to assign to each legend value
                    sdvCnt = int(arcpy.GetCount_management(os.path.join(gdb, sdvTblName)).getOutput(0))

                    # Get random RGB colors for use in this unique values legend        
                    rgbColors = rand_rgb_colors(sdvCnt)

                    with arcpy.da.SearchCursor(os.path.join(gdb, sdvTblName), [bName], sql_clause=sqlClause, where_clause=whereClause) as sdvCur:
                        
                        cur = arcpy.da.InsertCursor(lu, ["CELLVALUE", bName, "LABEL"])

                        for rec in sdvCur:
                            row += 1
                            val = rec[0]
                            cRed, cGreen, cBlue, opacity = rgbColors[row]  
                            dLegendInfo[row] = [val, val, (float(cRed) / 255.0), (float(cGreen) / 255.0), (float(cBlue) / 255.0), (float(opacity) / 255.0)]
                            newrec = [row, val, val]
                            
                            try:
                                cur.insertRow(newrec)
                                
                            except:
                                PrintMsg("\tFailed to handle '" + str(newrec), 1)

                    arcpy.AddIndex_management(lu, [bName], "Indx_" + bName)


            elif rendererType == 'classBreaks':
                dLegendInfo = dict() # work on class breaks later? Probably won't need it.

            else:
                dLegendInfo = dict()

            #PrintMsg("\tRenderer Type: '" + rendererType + "'", 1)
            
            # End of symbology import         

            # Get data type from sdv table and use this value to set output raster data type
            # pH is described as a SINGLE; Hydric Pct is SmallInteger;


            if fldType in ["Double", "Single"]:
                bitDepth = "32_BIT_FLOAT"
                aggMethod = "MEAN"

            elif fldType in ["SmallInteger", "Integer"]:
                bitDepth = "8_BIT_UNSIGNED"
                #aggMethod = "MEDIAN"
                aggMethod = "MAJORITY"        # Test for using BlockStatistics instead of Aggregate
                

            elif fldType in ["String"]:
                bitDepth = "8_BIT_UNSIGNED"
                #aggMethod = "MEDIAN"        # Why did I not use 'MAJORITY' here?
                aggMethod = "MAJORITY"        # Test
            

            tmpRaster = "Temp_Raster"
            
            if arcpy.Exists(tmpRaster):
                # clean up any previous runs
                arcpy.Delete_management(tmpRaster)

            if rDesc.dataType == "RasterLayer":
                inputDataset = arcpy.Describe(inputRaster).catalogPath
                arcpy.MakeRasterLayer_management(inputDataset, tmpRaster)
                gdb = os.path.dirname(inputDataset)

            elif rDesc.dataType == "RasterDataset":
                arcpy.MakeRasterLayer_management(inputRaster, tmpRaster)
                gdb = os.path.dirname(inputRaster)
                
            if not arcpy.Exists(tmpRaster):
                raise MyError, "Missing raster map layer"

            arcpy.AddJoin_management (tmpRaster, "MUKEY", os.path.join(gdb, sdvTblName), "MUKEY", "KEEP_ALL")
            
            if rendererType == 'uniqueValue':
                
                # Add CELLVALUE for Lookup. This is to maintain the correct legend order
                # Note to self. If there was no LegendInfo the order will be random.
                luCnt = int(arcpy.GetCount_management(lu).getOutput(0))
                #PrintMsg(" \n\tFound " + str(luCnt) + " records in " + lu + " table", 1)
                
                #PrintMsg("\tJoining " + lu + " to raster on " + fName + " to " + bName, 1)
    
                arcpy.AddJoin_management(tmpRaster, fName, lu, bName, "KEEP_COMMON")  # This damn thing is not bringing any data with the join.
                jDesc = arcpy.Describe(tmpRaster)
                jFields = jDesc.fields

                    
            # Create raster using Lookup_sa
            # Select non-Null values when fldType in ('Single', 'Double')
            # Note: the CopyRaster command has a bit-depth setting.
            #

            # Set output file name (FGDB Raster or TIFF)
            if outputFolder == "":
                if sdvTblName[-1].isdigit():
                    newRaster = os.path.join(gdb, "SoilRas_" + sdvTblName.replace("SDV_", "") + "_" + str(outputRes) + str(linearUnit))  # Temporary placement of this line

                else:
                    if sdvTblName[-1].isdigit():
                        newRaster = os.path.join(gdb, "SoilRas_" + sdvTblName.replace("SDV_", "") + "cm_" + str(outputRes) + str(linearUnit))  # Temporary placement of this line

                    else:
                        newRaster = os.path.join(gdb, "SoilRas_" + sdvTblName.replace("SDV_", "") + "_" + str(outputRes) + str(linearUnit))  # Temporary placement of this line

            else:
                if sdvTblName[-1].isdigit():
                    newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "cm_" + str(outputRes) + str(linearUnit) + ".tif")  # Temporary placement of this line

                else:
                    newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "_" + str(outputRes) + str(linearUnit) + ".tif")  # Temporary placement of this line
            
            PrintMsg("\tOutput raster will be '" + newRaster + "'", 0)
            
            if not fldType in ("Single", "Double"):  # Going to try running everything with BlockStatistics

                if cellFactor > 1:
                    env.cellSize = iRaster
                    
                    if rendererType == 'uniqueValue':
                        method = rendererType + ": " + "Using Lookup tool against the CELLVALUE column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup.CELLVALUE IS NOT NULL")
                        rCnt = int(arcpy.GetCount_management(tmpRaster).getOutput(0))
                        #PrintMsg(" \n\tSelected " + str(rCnt) + " records in tmpRaster for use with Lookup", 1)
                        
                        tmpRas = Lookup(tmpRaster, "Lookup.CELLVALUE")

                        time.sleep(1)
                        arcpy.Delete_management(tmpRaster)

                    else:
                        method = rendererType + ": " + "Using Lookup tool against the " + bName + " column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        #arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup." + bName + " IS NOT NULL")
                        tmpRas = Lookup(tmpRaster, bName)
                        
                        time.sleep(1)
                        arcpy.Delete_management(tmpRaster)
                    
                    method = "Using BlockStatistics with " + aggMethod + " option to resample to " + str(outputRes) + " " + linearUnit.lower() + " resolution."
                    newMethod += " " + method
                    PrintMsg("\t" + method, 0)
                    time.sleep(1)
                    nbr = NbrRectangle(outputRes, outputRes, "MAP")
                    env.cellSize = outputRes
                    holyRas = BlockStatistics(tmpRas, nbr, aggMethod, "DATA")  # the majority value calculated by BlockStatistics will be NoData for ties.

                    if arcpy.Exists(holyRas):
                        #PrintMsg("\tFilling NoData cells in holyRas", 1)
                        time.sleep(1)
                        filledRas = Con(IsNull(holyRas), tmpRas, holyRas)  # Try filling the NoData holes in the aggregate raster using data from the 30m input raster
                        del tmpRas, holyRas

                        if arcpy.Exists(filledRas):
                            PrintMsg("\tCreating final output raster", 0) 
                            time.sleep(1)
                            filledRas.save(newRaster)
                            # still have filledRas?

                        else:
                            raise MyError, "Missing filledRas raster"
 

                    else:
                        raise MyError, "Missing holyRas raster"

                else:
                    # Input and output resolution is the same, no resampling.
                    
                    if rendererType == 'uniqueValue':
                        method = rendererType + ": " + "Using Lookup tool against the CELLVALUE column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup.CELLVALUE IS NOT NULL")
                        tmpRas = Lookup(tmpRaster, "Lookup.CELLVALUE")

                        time.sleep(1)
                        arcpy.Delete_management(tmpRaster)

                    else:
                        method = rendererType + ": " + "Using Lookup tool against the " + bName + " column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", bName + " IS NOT NULL")

                        tmpRas = Lookup(tmpRaster, bName)
                        
                        time.sleep(1)
                        arcpy.Delete_management(tmpRaster)
                        
                        
                    PrintMsg("\tCreating final output raster", 0)
                    time.sleep(1)
                    tmpRas.save(newRaster)

            else:
                # All non-floating point data )
                #
                # Note: these may have an attribute table, but won't necessarily have the attribute columns
                if cellFactor > 1:
                    # Need to resample
                    method = "Using Aggregate tool with " + aggMethod + " option against the " + fName + " column (" + fldType + ")."
                    newMethod = "\n\rRaster Processing: " + method
                    PrintMsg("\t" + method, 0)
                    env.cellSize = outputRes
                    outRas = Aggregate(Lookup(tmpRaster, fName), cellFactor, aggMethod, "EXPAND", "DATA")
                    time.sleep(1)

                    arcpy.Delete_management(tmpRaster)
                        
                    outRas.save(newRaster)
                    #PrintMsg("\tResampling output to " + str(outputRes) + " " + linearUnit.lower() + " resolution", 0)
                    #arcpy.Resample_management(outRas, newRaster, outputRes , "NEAREST")
                    time.sleep(1)
                    del outRas

                else:
                    # No resampling needed
                    method = "Using Lookup tool against the " + fName + " column (" + fldType + ")."
                    newMethod = "\n\rRaster Processing: " + method
                    PrintMsg("\tSaving results of Lookup to " + newRaster, 0)
                    arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", fName + " IS NOT NULL")
                    outRas = Lookup(tmpRaster, fName)
                    time.sleep(1)

                    arcpy.Delete_management(tmpRaster)
                        
                    outRas.save(newRaster)
                    time.sleep(1)
                    del outRas

                newDesc = arcpy.Describe(newRaster)

                if len(newDesc.fields) > 0:
                    newFields = [fld.name for fld in newDesc.fields]
                    # sdvTblName, fName, bName, fldType, fldLen = dLayerFields[sdvLayer]

                    # Get the original SDV resultcolumn name
                    fName = fName.split(".")[1].split("_")[0]

                    if newFields[-1].upper() == "COUNT":
                        #PrintMsg(" \n\tAdding attribute fields (" + fName + ", CLASS_NAME, RED, GREEN, BLUE, OPACITY) to raster attribute table", 1)

                        # Add fName field and calculate it equal to the cell VALUE
                        if fldType == "SmallInteger":
                            #PrintMsg(" \nAdding " + fName + " as SHORT", 1)
                            arcpy.AddField_management(newRaster, fName, "SHORT")

                        elif fldType == "LongInteger":
                            #PrintMsg(" \nAdding " + fName + " as LONG", 1)
                            arcpy.AddField_management(newRaster, fName, "LONG")

                        else:
                            PrintMsg(" \nUnhandled field type for " + fName + ": " + fldType, 1)

                        # Populate RGB color attributes using soil map legend
                        with arcpy.da.UpdateCursor(newRaster, ["value", fName]) as cur:
                            #PrintMsg(" \nAdding RGB info to raster attribute table", 1)
                            
                            for rec in cur:
                                val = rec[0]
                                rec = [val, val]
                                cur.updateRow(rec)


                #else:
                #    PrintMsg(" \nnewRaster has no fields", 1)
                
            if arcpy.Exists(tmpRaster):
                # clean up any previous runs
                arcpy.Delete_management(tmpRaster)
                #del tmpRaster

                
            if bPyramids:
                PrintMsg("\tCreating statistics and pyramids...", 0)
                env.pyramid = "PYRAMIDS -1 NEAREST LZ77 # NO_SKIP"

                # BuildPyramidsandStatistics_management (in_workspace, {include_subdirectories}, {build_pyramids}, {calculate_statistics}, {BUILD_ON_SOURCE}, {block_field}, {estimate_statistics}, {x_skip_factor}, {y_skip_factor}, {ignore_values}, {pyramid_level}, {SKIP_FIRST}, {resample_technique}, {compression_type}, {compression_quality}, {skip_existing}, {where_clause})
                arcpy.BuildPyramidsandStatistics_management(newRaster, "NONE", "BUILD_PYRAMIDS", "CALCULATE_STATISTICS", "NONE", "", "NONE", 1, 1, "", -1, "NONE", "NEAREST", "LZ77")

            if rendererType == 'uniqueValue':
                # This could also include integer data like TFactor
                try:
                    # Add RGB attributes for unique values. Will fail if output raster does not have a VAT
                    sdvTblName, xName, bName, fldType, fldLen = dLayerFields[sdvLayer]
                    #try:
                    #    arcpy.AddField_management(newRaster, fName, "TEXT", "", "", fldLen)
                    #except:
                    #    pass
                    
                    arcpy.AddField_management(newRaster, "CLASS_NAME", "TEXT", "", "", fldLen)
                    arcpy.AddField_management(newRaster, "RED", "FLOAT")
                    arcpy.AddField_management(newRaster, "GREEN", "FLOAT")
                    arcpy.AddField_management(newRaster, "BLUE", "FLOAT")
                    arcpy.AddField_management(newRaster, "OPACITY", "SHORT")

                except:
                    PrintMsg("\tNo raster attribute table?", 1)

                try:
                    # Populate RGB color attributes using soil map legend
                    with arcpy.da.UpdateCursor(newRaster, ["value", "class_name", "red", "green", "blue", "opacity"]) as cur:
                    #with arcpy.da.UpdateCursor(newRaster, [fName, "class_name", "red", "green", "blue", "opacity"]) as cur:
                        #PrintMsg(" \nAdding RGB info to raster attribute table", 1)
                        
                        for rec in cur:
                            cellValue = rec[0]
                             
                            if cellValue in dLegendInfo:
                                val, label, red, green, blue, opacity = dLegendInfo[cellValue]
                                rec = [cellValue, label, red, green, blue, opacity]
                                cur.updateRow(rec)

                    # Add new raster layer to ArcMap
                    tmpRaster = "Temp_Raster"
            
                    if arcpy.Exists(tmpRaster):
                        # clean up any previous runs
                        arcpy.Delete_management(tmpRaster)

                    if outputFolder == "":
                        newLayerFile = os.path.join(os.path.dirname(gdb), "Ras_" + newLayerName + ".lyr")

                    else:
                        newLayerFile = os.path.join(outputFolder, "Ras_" + newLayerName + ".lyr")

                    # Update description
                    for line in newDescription.splitlines():
                        if line.startswith("Featurelayer:"):
                            #PrintMsg(line, 1)
                            newDescription = newDescription.replace(line, "Input Raster: " + inputRaster)

                        elif line.startswith("Layer File:"):
                            newDescription = newDescription.replace(line, "Layer File: " + newLayerFile)

                        elif line.startswith("Aggregation Method:"):
                            # Add raster aggregation and resampling methods here
                            newLine = line.replace("Aggregation Method:", "Mapunit Aggregation:") + "\n\r" + newMethod
                            newDescription = newDescription.replace(line, newLine)
                        
                    tmpLayerFile = os.path.join(env.scratchFolder, newLayerName + ".lyr")
                    tmpRaster = arcpy.MakeRasterLayer_management(newRaster, tmpRaster)
                    arcpy.SaveToLayerFile_management(tmpRaster, tmpLayerFile, "RELATIVE", "10.3")
                    finalMapLayer = arcpy.mapping.Layer(tmpLayerFile)
                    finalMapLayer.name = newLayerName
                    finalMapLayer.description = newDescription
                    finalMapLayer.credits = newCredits
                    finalMapLayer.visible = False
                    arcpy.mapping.AddLayerToGroup(df, grpLayer, finalMapLayer, "TOP")
                    arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")
                    # PrintMsg("\tAdded new map layer '" + newLayerName + "' to ArcMap in the UniqueValue section", 1)

                    # Cleanup layers
                    #PrintMsg("\tCleaning up temporary rasters", 1)
                    #time.sleep(1)
                    #arcpy.Delete_management(tmpLayerFile)
                    #arcpy.Delete_management(tmpRaster)

 
                except:
                    # Integer rasters such as TFactor may have an attribute table but no rating field
                    #
                    errorMsg()

                    raise MyError, ""
                    
            elif rendererType == 'classBreaks':
                # Should only be numeric data.

                # Determine which layer file to use
                #
                cbInfo = rendererInfo['classBreakInfos']
                dBreakFirst = cbInfo[0]
                dBreakLast = cbInfo[-1]

                if dBreakFirst["symbol"]["color"] == [0, 255, 0, 255] and dBreakLast["symbol"]["color"] == [255,0, 0, 255]:
                    # Hydric
                    # [0,255,0],[150,255,150],[255,255,0],[255,150,0],[255,0,0]
                    classLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterClassified_MedGreenRed.lyr")
                    classLayer = arcpy.mapping.Layer(classLayerFile)
                    #PrintMsg("\tShould be using Med Green to Red legend for this layer", 1)

                elif dBreakFirst["symbol"]["color"] == [255, 0, 0, 255] and dBreakLast["symbol"]["color"] == [0, 255, 0, 255]:
                    #PrintMsg("\tShould be using Red to Med Green legend for this layer", 1)
                    classLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterClassified_RedMedGreen.lyr")
                    classLayer = arcpy.mapping.Layer(classLayerFile)

                elif dBreakFirst["symbol"]["color"] == [0, 128, 0, 255] and dBreakLast["symbol"]["color"] ==  [255, 0, 0, 255]:
                    #PrintMsg("\tShould be using Dark Green to Red legend for this layer", 1)
                    classLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterClassified_DkGreenRed.lyr")
                    classLayer = arcpy.mapping.Layer(classLayerFile)

                elif dBreakFirst["symbol"]["color"] == [255, 0, 0, 255] and dBreakLast["symbol"]["color"] ==  [0, 0, 255, 255]:
                    #PrintMsg("\tShould be using Red to Blue legend for this layer", 1)
                    classLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_RasterClassified_RedBlue.lyr")
                    classLayer = arcpy.mapping.Layer(classLayerFile)

                else:
                    PrintMsg(" \nLegend problem. First legend color is: " + str(dBreakFirst["symbol"]["color"]) + " and last color is " + str(dBreakLast["symbol"]["color"]), 1)

                # Create lists for symbology break values and label values
                classBV = list()
                classBL = list()

                for cb in cbInfo:
                    classBV.append(cb['classMaxValue'])
                    classBL.append(cb['label'])

                if arcpy.Exists(classLayerFile):
                    tmpLayerFile = os.path.join(env.scratchFolder, "tmpSDVLayer.lyr")

                    if arcpy.Exists(tmpLayerFile):
                        arcpy.Delete_management(tmpLayerFile)

                    tmpRasterLayer = "Raster_Layer"
                    
                    if arcpy.Exists(tmpRasterLayer):
                        # clean up any previous runs
                        arcpy.Delete_management(tmpRasterLayer)

                    arcpy.MakeRasterLayer_management(newRaster, tmpRasterLayer)

                    if not arcpy.Exists(tmpRasterLayer):
                        raise MyError, "Missing raster map layer 1"

                    # Create final mapping layer from input raster layer.
                    #
                    time.sleep(1)
                    finalMapLayer = arcpy.mapping.Layer(tmpRasterLayer)  # create arcpy.mapping
                    finalMapLayer.name = newLayerName
                    
                    if outputFolder == "":
                        newLayerFile = os.path.join(os.path.dirname(gdb), "Ras_" + newLayerName + ".lyr")

                    else:
                        newLayerFile = os.path.join(outputFolder, "Ras_" + newLayerName + ".lyr")
        
                    arcpy.mapping.UpdateLayer(df, finalMapLayer, classLayer, True)

                    # Set symbology properties using information from GetNumericLegend
                    finalMapLayer.symbology.valueField = "VALUE"

                    if len(classBV) == len(classBL):
                        # For numeric legends using class break values, there needs to be a starting value in addition
                        # to the class breaks. This means that there are one more value than there are labels
                        #PrintMsg(" \nInserting zero into class break values", 1)
                        classBV.insert(0, 0)

                    finalMapLayer.symbology.classBreakValues = classBV

                    if len(classBL)> 0:

                        # Update description
                        for line in newDescription.splitlines():
                            if line.startswith("Featurelayer:"):
                                #PrintMsg(line, 1)
                                newDescription = newDescription.replace(line, "Input Raster: " + inputRaster)

                            elif line.startswith("Layer File:"):
                                newDescription = newDescription.replace(line, "Layer File: " + newLayerFile)

                            elif line.startswith("Aggregation Method:"):
                                # Add raster aggregation and resampling methods here
                                newLine = line.replace("Aggregation Method:", "Mapunit Aggregation:") + "\n\r" + newMethod
                                newDescription = newDescription.replace(line, newLine)
                                
                        finalMapLayer.symbology.classBreakLabels = classBL # Got comppct symbology without this line
                        finalMapLayer.description = newDescription
                        finalMapLayer.credits = newCredits
                        finalMapLayer.visible = False
                        arcpy.mapping.AddLayerToGroup(df, grpLayer, finalMapLayer, "TOP") 
                        arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")
                        #PrintMsg("\tAdded new map layer '" + newLayerName + "' to ArcMap in the ClassifiedBreaks section", 1)
                        # Cleanup layers
                        #PrintMsg("\tCleaning up temporary rasters", 1)
                        time.sleep(1)
                        #arcpy.Delete_management(tmpLayerFile)
                        #arcpy.Delete_management(tmpRaster)

                    else:
                        PrintMsg("\tSkipping addition of new map layer '" + newLayerName + "' to ArcMap in the ClassifiedBreaks section", 1)
                        
                        
                # end of classBreaks
            
            else:
                #PrintMsg("\tLayer won't be added if it ends up here because rendererType is '" + rendererType + "'", 1)
                tmpRaster = "Temp_Raster"
            
                if arcpy.Exists(tmpRaster):
                    # clean up any previous runs
                    arcpy.Delete_management(tmpRaster)
                        
                if outputFolder == "":
                    newLayerFile = os.path.join(os.path.dirname(gdb), "Ras_" + newLayerName + ".lyr")

                else:
                    newLayerFile = os.path.join(outputFolder, "Ras_" + newLayerName + ".lyr")
                
                tmpLayerFile = os.path.join(env.scratchFolder, newLayerName + ".lyr")
                tmpRaster = arcpy.MakeRasterLayer_management(newRaster, tmpRaster)
                arcpy.SaveToLayerFile_management(tmpRaster, tmpLayerFile, "RELATIVE", "10.3")
                finalMapLayer = arcpy.mapping.Layer(tmpLayerFile)

                # Update description
                for line in newDescription.splitlines():
                    if line.startswith("Featurelayer:"):
                        #PrintMsg(line, 1)
                        newDescription = newDescription.replace(line, "Input Raster: " + inputRaster)

                    elif line.startswith("Layer File:"):
                        newDescription = newDescription.replace(line, "Layer File: " + newLayerFile)

                    elif line.startswith("Aggregation Method:"):
                        # Add raster aggregation and resampling methods here

                        newLine = line.replace("Aggregation Method:", "Mapunit Aggregation:") + "\n\r" + newMethod
                        newDescription = newDescription.replace(line, newLine)
                            
                finalMapLayer.name = newLayerName
                finalMapLayer.description = newDescription
                finalMapLayer.credits = newCredits
                finalMapLayer.visible = False
                arcpy.mapping.AddLayerToGroup(df, grpLayer, finalMapLayer, "TOP")
                arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")

                # Cleanup layers
                #PrintMsg("\tCleaning up temporary rasters", 1)
                time.sleep(1)
                #arcpy.Delete_management(tmpLayerFile)
                #arcpy.Delete_management(tmpRaster)

                
            #bMetadata = UpdateMetadata(gdb, newRaster, sdvLayer, description, iRaster)
            #arcpy.SetProgressorPosition()

            # Clean up variables for each map layer here:
            #del sdvTblName, fName, bName, fldType, fldLen, newDescription, newLayerName, symTbl, lu, finalMapLayer, newRaster
            
        PrintMsg(" \n", 0)
        #del sdvLayers, sdvLayer
        


            
        return True

    except MyError, e:
        PrintMsg(str(e) + " \n", 2)
        try:
            del mxd
        except:
            pass
        return False

    except:
        errorMsg()
        try:
            del mxd
        except:
            pass
        return False

    #finally:
    #    arcpy.CheckInExtension("Spatial")



# ====================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, traceback, arcpy, json, random
from arcpy import env
import xml.etree.cElementTree as ET

try:


    if __name__ == "__main__":
        # Create a single table that contains
        #sdvLayers = arcpy.GetParameterAsText(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        sdvLayers = arcpy.GetParameter(0)                  # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        inputRaster = arcpy.GetParameterAsText(1)          # gSSURGO raster that will be used to create individual rasters based upon selected attributes
        outputFolder = arcpy.GetParameterAsText(2)         # If other than file geodatabase raster is desired, specify this folder path
        cellFactor = arcpy.GetParameter(3)                 # cellFactor multiplies the input resolution by this factor to aggregate to a larger cellsize
        outputRes = arcpy.GetParameter(4)                  # output raster resolution (input resolution * cellFactor
        bPyramids = arcpy.GetParameter(5)                  # Sets environment for raster post-processing

        try:
            if arcpy.CheckExtension("Spatial") == "Available":
                arcpy.CheckOutExtension("Spatial")
                from arcpy.sa import *
                
            else:
                # Raise a custom exception
                #
                raise LicenseError
            
            
        except:
            raise MyError, "Spatial Analyst license is unavailable"

    
        bRasters = CreateRasterLayers(sdvLayers, inputRaster, outputFolder, bPyramids, cellFactor, outputRes)


except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

#finally:
#    arcpy.CheckInExtension("Spatial")

