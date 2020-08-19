# gSSURGO_ExportRasters.py
#
# Steve Peaslee, National Soil Survey Center
# 2019-10-07
#
# Purpose: Batch mode conversion of multiple gSSURGO soil maps into raster (TIFF or FGDB raster).
#
# Looking at option to automatically identify a soil map layer with the
# associated sdvattribute.resultcolumnname record in the correct geodatabase.
#
# Examples of qualified fieldnames for ratings:
#    SDV_pHwater_DCP_0to5.pHwater_DCP
#    SDV_pHwater_DCP_5to15.pHwater_DCP
#    SDV_NCCPI_WTA.NCCPI_WTA
#    SDV_KfactWS_DCD_0to1.KFACTWS_DCD
#    SDV_EcoSiteNm_DCD_NRCS_Rangeland_Site.ECOSITENM_DCD
#
# Will need to incorporate some code from Create Soil Map script. This may be a burden for
# map legends that do not have values or breaks stored in xml.
# dLayerDefinition['drawingInfo']['renderer']
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
def GetMapLegend(dAtts, bFuzzy):
    # From gSSURGO_CreateSoilMap script...
    #
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    # Problem with Farmland Classification. It is defined as a choice, but

    try:
        #bVerbose = True  # This function seems to work well, but prints a lot of messages.
        global dLegend
        dLegend = dict()
        dLabels = dict()

        #if bFuzzy and not dAtts["attributename"].startswith("National Commodity Crop Productivity Index"):
        #    # Skip map legend because the fuzzy values will not match the XML legend.
        #    return dict()

        arcpy.SetProgressorLabel("Getting map legend information")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        xmlString = dAtts["maplegendxml"]

        #if bVerbose:
        #    PrintMsg(" \nxmlString: " + xmlString + " \n ", 1)

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        # Iterate through XML tree, finding required elements...
        i = 0
        dColors = dict()
        legendList = list()
        legendKey = ""
        legendType = ""
        legendName = ""

        # Notes: dictionary items will vary according to legend type
        # Looks like order should be dictionary key for at least the labels section
        #
        for rec in tree.iter():

            if rec.tag == "Map_Legend":
                dLegend["maplegendkey"] = rec.attrib["maplegendkey"]

            if rec.tag == "ColorRampType":
                dLegend["type"] = rec.attrib["type"]
                dLegend["name"] = rec.attrib["name"]

                if rec.attrib["name"] == "Progressive":
                    dLegend["count"] = int(rec.attrib["count"])

            if "name" in dLegend and dLegend["name"] == "Progressive":

                if rec.tag == "LowerColor":
                    # 'part' is zero-based and related to count
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Lower Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)

                if rec.tag == "UpperColor":
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Upper Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)


            if rec.tag == "Labels":
                order = int(rec.attrib["order"])

                if dSDV["attributelogicaldatatype"].lower() == "integer":
                    # get dictionary values and convert values to integer
                    try:
                        val = int(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = int(rec.attrib["upper_value"])
                        lowerVal = int(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                elif dSDV["attributelogicaldatatype"].lower() == "float" and not bFuzzy:
                    # get dictionary values and convert values to float
                    try:
                        val = float(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = float(rec.attrib["upper_value"])
                        lowerVal = float(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                else:
                    dLabels[order] = rec.attrib   # for each label, save dictionary of values

            if rec.tag == "Color":
                # Save RGB Colors for each legend item

                # get dictionary values and convert values to integer
                red = int(rec.attrib["red"])
                green = int(rec.attrib["green"])
                blue = int(rec.attrib["blue"])
                dColors[order] = rec.attrib

            if rec.tag == "Legend_Elements":
                try:
                    dLegend["classes"] = rec.attrib["classes"]   # save number of classes (also is a dSDV value)

                except:
                    pass

        # Add the labels dictionary to the legend dictionary
        dLegend["labels"] = dLabels
        dLegend["colors"] = dColors

        # Test iteration methods on dLegend
        #PrintMsg(" \n" + dAtts["attributename"] + " Legend Key: " + dLegend["maplegendkey"] + ", Type: " + dLegend["type"] + ", Name: " + dLegend["name"] , 1)

        if bVerbose:
            PrintMsg(" \n" + dAtts["attributename"] + "; MapLegendKey: " + dLegend["maplegendkey"] + ",; Type: " + dLegend["type"] , 1)

            for order, vals in dLabels.items():
                PrintMsg("\tNew " + str(order) + ": ", 1)

                for key, val in vals.items():
                    PrintMsg("\t\t" + key + ": " + str(val), 1)

                try:
                    r = int(dColors[order]["red"])
                    g = int(dColors[order]["green"])
                    b = int(dColors[order]["blue"])
                    rgb = (r,g,b)
                    #PrintMsg("\t\tRGB: " + str(rgb), 1)

                except:
                    pass

        if bVerbose:
            PrintMsg(" \ndLegend: " + str(dLegend), 1)

        return dLegend

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

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
def StateNames():
    # Create dictionary object containing list of state abbreviations and their names that
    # will be used to name the file geodatabase.
    # For some areas such as Puerto Rico, U.S. Virgin Islands, Pacific Islands Area the
    # abbrevation is

    # NEED TO UPDATE THIS FUNCTION TO USE THE LAOVERLAP TABLE AREANAME. AREASYMBOL IS STATE ABBREV

    try:
        stDict = dict()
        stDict["Alabama"] = "AL"
        stDict["Alaska"] = "AK"
        stDict["American Samoa"] = "AS"
        stDict["Arizona"] =  "AZ"
        stDict["Arkansas"] = "AR"
        stDict["California"] = "CA"
        stDict["Colorado"] = "CO"
        stDict["Connecticut"] = "CT"
        stDict["District of Columbia"] = "DC"
        stDict["Delaware"] = "DE"
        stDict["Florida"] = "FL"
        stDict["Georgia"] = "GA"
        stDict["Territory of Guam"] = "GU"
        stDict["Guam"] = "GU"
        stDict["Hawaii"] = "HI"
        stDict["Idaho"] = "ID"
        stDict["Illinois"] = "IL"
        stDict["Indiana"] = "IN"
        stDict["Iowa"] = "IA"
        stDict["Kansas"] = "KS"
        stDict["Kentucky"] = "KY"
        stDict["Louisiana"] = "LA"
        stDict["Maine"] = "ME"
        stDict["Northern Mariana Islands"] = "MP"
        stDict["Marshall Islands"] = "MH"
        stDict["Maryland"] = "MD"
        stDict["Massachusetts"] = "MA"
        stDict["Michigan"] = "MI"
        stDict["Federated States of Micronesia"] ="FM"
        stDict["Minnesota"] = "MN"
        stDict["Mississippi"] = "MS"
        stDict["Missouri"] = "MO"
        stDict["Montana"] = "MT"
        stDict["Nebraska"] = "NE"
        stDict["Nevada"] = "NV"
        stDict["New Hampshire"] = "NH"
        stDict["New Jersey"] = "NJ"
        stDict["New Mexico"] = "NM"
        stDict["New York"] = "NY"
        stDict["North Carolina"] = "NC"
        stDict["North Dakota"] = "ND"
        stDict["Ohio"] = "OH"
        stDict["Oklahoma"] = "OK"
        stDict["Oregon"] = "OR"
        stDict["Palau"] = "PW"
        stDict["Pacific Basin"] = "PB"
        stDict["Pennsylvania"] = "PA"
        stDict["Puerto Rico and U.S. Virgin Islands"] = "PRUSVI"
        stDict["Rhode Island"] = "RI"
        stDict["South Carolina"] = "SC"
        stDict["South Dakota"] = "SD"
        stDict["Tennessee"] = "TN"
        stDict["Texas"] = "TX"
        stDict["Utah"] = "UT"
        stDict["Vermont"] = "VT"
        stDict["Virginia"] = "VA"
        stDict["Washington"] = "WA"
        stDict["West Virginia"] = "WV"
        stDict["Wisconsin"] = "WI"
        stDict["Wyoming"] = "WY"
        return stDict

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return None

## ===================================================================================
def GetSDVAtts(gdb, resultcolumnname):
    # GetSDVAtts(gdb, sdvAtt, aggMethod, tieBreaker, bFuzzy, sRV):
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    try:
        # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        oid = flds.pop(0)
        sql1 = "UPPER(resultcolumnname) = '" + resultcolumnname + "'"
        #PrintMsg("\tresultcolumnname: " + resultcolumnname, 1)

        if bVerbose:
            PrintMsg(" \nReading sdvattribute table into dSDV dictionary", 1)

        with arcpy.da.SearchCursor(sdvattTable, flds, where_clause=sql1) as cur:
            for rec in cur:  # just reading first record
                i = 0
                for val in rec:
                    dSDV[flds[i].lower()] = val
                    #PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                    i += 1

        # Revise some attributes to accomodate fuzzy number mapping code
        #
        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number

        if dSDV["interpnullsaszeroflag"]:
            bZero = True

        if dSDV["attributetype"].lower() == "interpretation" and (dSDV["effectivelogicaldatatype"].lower() == "float" or bFuzzy == True):
            #PrintMsg(" \nOver-riding attributecolumnname for " + sdvAtt, 1)
            dSDV["attributecolumnname"] = "INTERPHR"

            # WHAT HAPPENS IF I SKIP THIS NEXT SECTION. DOES IT BREAK EVERYTHING ELSE WHEN THE USER SETS bFuzzy TO True?
            # Test is ND035, Salinity Risk%
            # Answer: It breaks my map legend.

            if dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() == "string" and dSDV["effectivelogicaldatatype"].lower() == "float":
                #PrintMsg("\tIdentified " + sdvAtt + " as being an interp with a numeric rating", 1)
                pass

            else:
            #if dSDV["nasisrulename"][0:5] != "NCCPI":
                # This comes into play when user selects option to create soil map using interp fuzzy values instead of rating classes.
                dSDV["effectivelogicaldatatype"] = 'float'
                dSDV["attributelogicaldatatype"] = 'float'
                dSDV["maplegendkey"] = 3
                dSDV["maplegendclasses"] = 5
                dSDV["attributeprecision"] = 2


        #else:
            # Diagnostic for batch mode NCCPI
            #PrintMsg(" \n" + dSDV["attributetype"].lower() + "; " + dSDV["effectivelogicaldatatype"] + "; " + str(bFuzzy), 1)


        # Workaround for sql whereclause stored in sdvattribute table. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = 'UPPER("' + sqlParts[0] + '") = ' + sqlParts[1].upper()

        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False and dSDV["notratedphrase"] is None:
            # Add 'Not rated' to choice list
            dSDV["notratedphrase"] = "Not rated" # should not have to do this, but this is not always set in Rule Manager

        if dSDV["secondaryconcolname"] is not None and dSDV["secondaryconcolname"].lower() == "yldunits":
            # then this would be units for legend (component crop yield)
            #PrintMsg(" \nSetting units of measure to: " + secCst, 1)
            dSDV["attributeuomabbrev"] = secCst

##        if dSDV["attributecolumnname"].endswith("_r") and sRV in ["Low", "High"]:
##            # This functionality is not available with SDV or WSS. Does not work with interps.
##            #
##            if sRV == "Low":
##                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_l")
##
##            elif sRV == "High":
##                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_h")

            #PrintMsg(" \nUsing attribute column " + dSDV["attributecolumnname"], 1)

        # Working with sdvattribute tiebreak attributes:
        # tiebreakruleoptionflag (0=cannot change, 1=can change)
        # tiebreaklowlabel - if null, defaults to 'Lower'
        # tiebreaklowlabel - if null, defaults to 'Higher'
        # tiebreakrule -1=use lower  1=use higher
        if dSDV["tiebreaklowlabel"] is None:
            dSDV["tiebreaklowlabel"] = "Lower"

        if dSDV["tiebreakhighlabel"] is None:
            dSDV["tiebreakhighlabel"] = "Higher"

        if dSDV["tiebreakrule"] == -1:
            tieBreaker = dSDV["tiebreaklowlabel"]

        else:
            tieBreaker = dSDV["tiebreakhighlabel"]

        #dAgg = dict()

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            #PrintMsg(" \nUpdating dAgg", 1)
            dAgg["Minimum or Maximum"] = "Max"

        else:
            dAgg["Minimum or Maximum"] = "Min"
            #PrintMsg(" \nUpdating dAgg", 1)

        #if aggMethod == "":
        aggMethod = dSDV["algorithmname"]

        if dAgg[aggMethod] != "":
            dSDV["resultcolumnname"] = dSDV["resultcolumnname"] + "_" + dAgg[aggMethod]

        #PrintMsg(" \nSetting resultcolumn name to: '" + dSDV["resultcolumnname"] + "'", 1)



        return dSDV

    except:
        errorMsg()
        return dSDV

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
def CreateRasterLayers(sdvLayers, inputRaster, outputFolder, bPyramids, cellFactor, outputRes, bOverwrite, mxd, df, grpLayer):
    # Merge rating tables from for the selected soilmap layers to create a single, mapunit-level table
    #
    try:
        global bVerbose
        bVerbose = False
        global bFuzzy
        bFuzzy = False
        
        if os.path.basename(env.scratchGDB) == "Default.gdb" or os.path.basename(env.scratchWorkspace) == "Default.gdb":
            # Problems occur with raster geoprocessing when both the current and scratch geodatabases point to the
            # same Default.gdb. Create a new scratch geodatabase for this script to use.
            #if os.path.basename(env.scratchGDB) == "Default.gdb":
            scrFolder = env.scratchFolder

            if arcpy.Exists(os.path.join(os.path.dirname(scrFolder), "scratch.gdb")):
                scrGDB = os.path.join(os.path.dirname(scrFolder), "scratch.gdb")

            else:        
                scrGDB = os.path.join(scrFolder, "scratch.gdb")
            
            if not arcpy.Exists(scrGDB):
                arcpy.CreateFileGDB_management(scrFolder, "scratch.gdb", "CURRENT")

            if arcpy.Exists(scrGDB):
                env.scratchWorkspace = scrGDB    

            else:
                raise MyError, "Failed to create " + scrGDB

        if outputFolder != "":
            # if the outputFolder exists, create TIF files instead of file geodatabase rasters
            if not arcpy.Exists(outputFolder):
                outputFolder = ""
                
        env.overwriteOutput = True # Overwrite existing output tables
        env.pyramid = "NONE"
        arcpy.env.compression = "LZ77"

        env.pyramid = "NONE"

        # Dictionary for aggregation method abbreviations
        #
        global dAgg
        dAgg = dict()
        dAgg["Dominant Component"] = "DCP"
        dAgg["Dominant Condition"] = "DCD"
        dAgg["No Aggregation Necessary"] = ""
        dAgg["Percent Present"] = "PP"
        dAgg["Weighted Average"] = "WTA"
        dAgg["Most Limiting"] = "ML"
        dAgg["Least Limiting"] = "LL"
        dAgg[""] = ""        

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
        rasterDB = os.path.dirname(rDesc.catalogPath)  # should check to make sure each sdvLayer is from the same fgdb
                    
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

            if not gdb == rasterDB:
                raise MyError, "Map layer " + sdvLayer + " does belong to the same geodatabase as the input raster"

            allFields = desc.fields
            ratingField = allFields[-1]  # rating field should be the last one in the table
            fName = ratingField.name.encode('ascii')       # fully qualified name
            bName = ratingField.baseName.encode('ascii')   # physical name
            resultcolumnname = bName.split("_")[0]         # Original SDV resultcolumnname. Use this to get matching sdvattribute record.
            clipLen = (-1 * (len(bName))) - 1
            sdvTblName = fName[0:clipLen]                  # rating table joined to map layer
            sdvTbl = os.path.join(gdb, sdvTblName)
            fldType = ratingField.type
            fldLen = ratingField.length
            dLayerFields[sdvLayer] = (sdvTblName, fName, bName, fldType, fldLen)
            chkFields.append(bName)

            # alternative would be to get attributes from sdvattributetable using the resultcolumnname value
            # work on this more later. dSDV = GetSDVAtts(gdb, resultcolumnname)

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
            # Set initialize output resolution to same as input
            env.cellSize = iRaster


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
                if outputFolder.endswith(".gdb"):
                    # FGDB Raster
                        
                    if sdvTblName[-1].isdigit():
                        newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "cm_" + str(outputRes) + str(linearUnit))  # Temporary placement of this line

                    else:
                        newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "_" + str(outputRes) + str(linearUnit))  # Temporary placement of this line


                else:
                    # TIFF
                        
                    if sdvTblName[-1].isdigit():
                        newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "cm_" + str(outputRes) + str(linearUnit) + ".tif")  # Temporary placement of this line

                    else:
                        newRaster = os.path.join(outputFolder, "SoilRas_" + sdvTblName.replace("SDV_", "") + "_" + str(outputRes) + str(linearUnit) + ".tif")  # Temporary placement of this line
                
            # PrintMsg("\tOutput raster will be '" + newRaster + "'", 0)


            # Check raster output overwrite option here before proceeding
            # Skip raster conversion if output already exists and bOverwrite = False (default)
            if (bOverwrite and arcpy.Exists(newRaster)) or not arcpy.Exists(newRaster):
                if bOverwrite and arcpy.Exists(newRaster):
                    try:
                        # try regardless of lock results
                        arcpy.Delete_management(newRaster)
                        
                    except:
                        raise MyError, "Unable to overwrite existing raster: " + newRaster
            
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
                            # Example K Factor (whole soils)
                            #
                            PrintMsg("\tBuilding Lookup table from map layer information", 0)
                            with arcpy.da.InsertCursor(lu, ["CELLVALUE", bName, "LABEL"]) as cur:

                                row = 0
                                remapList = list()
                                #PrintMsg(" \nuniqueValueInfos: " + str(rendererInfo['uniqueValueInfos']), 1)
                                         
                                for valInfos in rendererInfo['uniqueValueInfos']:
                                    row += 1
                                    cRed, cGreen, cBlue, opacity = valInfos['symbol']['color']
                                    lab = valInfos['label']
                                    val = valInfos['value']
                                    dLegendInfo[row] = (val, lab, (float(cRed) / 255.0), (float(cGreen) / 255.0), (float(cBlue) / 255.0), 1)
                                    remapList.append([row, row])
                                    
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
                            # Example 'Soil Taxonomy Classification' layer
                            #
                            PrintMsg("\tBuilding Lookup table from scratch using SDV table, " + bName + " column", 0)
                            whereClause = bName + " IS NOT NULL"
                            sqlClause = ("DISTINCT", "ORDER BY " + bName)
                            row = 0
                            remapList = list()

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
                                    remapList.append([row, row])
                                    
                                    try:
                                        cur.insertRow(newrec)
                                        
                                    except:
                                        PrintMsg("\tFailed to handle '" + str(newrec), 1)

                            arcpy.AddIndex_management(lu, [bName], "Indx_" + bName)

                    elif rendererType == 'classBreaks':
                        dLegendInfo = dict() # work on class breaks later? Probably won't need it.

                    else:
                        dLegendInfo = dict()

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

                # Join sdv rating table to tmpRaster
                arcpy.AddJoin_management (tmpRaster, "MUKEY", os.path.join(gdb, sdvTblName), "MUKEY", "KEEP_COMMON")
                # bName = [fld.name.upper() for fld in arcpy.Describe(tmpRaster).fields if fld.name.upper().endswith(bName)][0]
                
                if rendererType == 'uniqueValue':
                    
                    # Add CELLVALUE for Lookup and join on the rating field. This is to maintain the correct legend order
                    #
                    # Seeing some instant memory allocation errors for Alaska gNATSGO when trying to run Lookup.
                    # Manually creating the Raster layer with 2 joins and running Lookup does not cause this error,
                    # but Alaska gNATSGO Lookup runs for 2 hours in Background mode even though it completes successfully.
                    # There are only 4 integer values in the resulting raster which originally had 2984 mukeys and 366,894 X 197,946 cells (~ 72.6 billion).

                    #
                    # Note to self. If there was no LegendInfo the order will be random.
                    #
                    #PrintMsg("\tJoining " + lu + " to raster on " + fName + " = " + bName, 1)
                    luCnt = int(arcpy.GetCount_management(lu).getOutput(0))   
                    arcpy.AddJoin_management(tmpRaster, fName, lu, bName, "KEEP_COMMON")
                    jDesc = arcpy.Describe(tmpRaster)
                    jFields = jDesc.fields

                # Qualifying the fieldname can cause problems when referring to the Lookup table
                rFldNames = [fld.name.upper() for fld in arcpy.Describe(tmpRaster).fields]
                bName = [fld for fld in rFldNames if fld.endswith(bName)][0]
                
                if not fldType in ("Single", "Double"):  # Going to try running everything with BlockStatistics

                    # Get list of fields in Temp_Raster
                    #PrintMsg(" \nTemp_Raster fields: " + ", ".join(rFldNames), 1)

                    if cellFactor > 1:

                        if rendererType == 'uniqueValue':
                            method = "Using Lookup tool against the CELLVALUE column."
                            newMethod = "\n\rRaster Processing: " + method
                            PrintMsg("\t" + method, 0)
                            arcpy.SetProgressorLabel(method)
                            arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup.CELLVALUE IS NOT NULL")
                            rCnt = int(arcpy.GetCount_management(tmpRaster).getOutput(0))

                            try:
                                tmpRas = Lookup(tmpRaster, "Lookup.CELLVALUE")

                            except:
                                # probably memory error exception
                                method = "Switching to Reclass against Lookup.CELLVALUE column."
                                PrintMsg("\t" + method, 0)
                                arcpy.SetProgressorLabel(method)
                                tmpRas = Reclassify(tmpRaster, "Lookup.CELLVALUE", RemapRange(remapList), "NODATA")

                            time.sleep(1)
                            arcpy.Delete_management(tmpRaster)

                        else:
                            # Problem with HydricRating
                            hydFlds = arcpy.Describe(tmpRaster).fields
                            hydFldNames = [fld.name for fld in hydFlds]
                            #PrintMsg(" \n\Hydric tmpRaster fields: " + ", ".join(hydFldNames), 1)
                            method = "Using Lookup tool against the " + bName + " column (" + fldType + ")."
                            newMethod = "\n\rRaster Processing: " + method
                            PrintMsg("\t" + method, 0)
                            arcpy.SetProgressorLabel(method)
                            #arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup." + bName + " IS NOT NULL")
                            tmpRas = Lookup(tmpRaster, bName)
                            time.sleep(1)
                            arcpy.Delete_management(tmpRaster)
                        
                        method = "Using BlockStatistics with " + aggMethod + " option to resample to " + str(outputRes) + " " + linearUnit.lower() + " resolution."
                        newMethod += " " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SetProgressorLabel(method)
                        time.sleep(2)
                        nbr = NbrRectangle(cellFactor, cellFactor, "CELL")
                        holyRas = BlockStatistics(tmpRas, nbr, aggMethod, "DATA")  # the majority value calculated by BlockStatistics will be NoData for ties.

                        if arcpy.Exists(holyRas):
                            #PrintMsg("\tFilling NoData cells in holyRas", 1)
                            time.sleep(1)
                            env.cellSize = outputRes
                            filledRas = Con(IsNull(holyRas), tmpRas, holyRas)  # Try filling the NoData holes in the aggregate raster using data from the 30m input raster
                            del tmpRas, holyRas

                            if arcpy.Exists(filledRas):
                                #PrintMsg("\tCreating final output raster", 0) 
                                time.sleep(1)
                                filledRas.save(newRaster)
                                finalDesc = arcpy.Describe(newRaster)
                                finalRez = finalDesc.meanCellHeight

                                if finalRez != outputRes:
                                    PrintMsg("\tError in final output resolution: " + str(finalRez) + " " + linearUnit, 1)
                                
                                # still have filledRas?

                            else:
                                raise MyError, "Missing filledRas raster"
     

                        else:
                            raise MyError, "Missing holyRas raster"

                    else:
                        # Input and output resolution is the same, no resampling.

                        # I need to get name of RAT fields and match with bName
                        bName = [fld.name.upper() for fld in arcpy.Describe(tmpRaster).fields if fld.name.upper().endswith(bName)][0]
                        
                        if rendererType == 'uniqueValue':
                            method = "Using Lookup tool against the CELLVALUE column (" + fldType + ")."
                            newMethod = "\n\rRaster Processing: " + method
                            PrintMsg("\t" + method, 0)
                            arcpy.SetProgressorLabel(method)
                            arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", "Lookup.CELLVALUE IS NOT NULL")

                            try:
                                tmpRas = Lookup(tmpRaster, "Lookup.CELLVALUE")

                            except:
                                # probably memory error exception
                                method = "Switching to Reclass against Lookup.CELLVALUE column."
                                PrintMsg("\t" + method, 0)
                                PrintMsg(" \nremapList: " + str(remapList), 1)
                                arcpy.SetProgressorLabel(method)
                                tmpRas = Reclassify(tmpRaster, "Lookup.CELLVALUE", RemapRange(remapList), "NODATA")

                            time.sleep(2)
                            arcpy.Delete_management(tmpRaster)

                        else:
                            method = "Using Lookup tool against the " + bName + " column (" + fldType + ")."
                            newMethod = "\n\rRaster Processing: " + method
                            PrintMsg("\t" + method, 0)
                            arcpy.SetProgressorLabel(method)
                            arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", bName + " IS NOT NULL")
                            tmpRas = Lookup(tmpRaster, bName)
                            
                            time.sleep(1)
                            arcpy.Delete_management(tmpRaster)
                            
                            
                        #PrintMsg("\tCreating final output raster", 0)
                        time.sleep(1)
                        tmpRas.save(newRaster)
                        finalDesc = arcpy.Describe(newRaster)
                        finalRez = finalDesc.meanCellHeight
                        
                        if finalRez != outputRes:
                            PrintMsg("\tError in final output resolution: " + str(finalRez) + " " + linearUnit, 1)
                                

                else:
                    # Floating point data
                    #
                    # Note: these may have an attribute table, but won't necessarily have the attribute columns
                    if cellFactor > 1:
                        # Need to resample
                        method = "Using Aggregate tool with " + aggMethod + " option against the " + fName + " column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SetProgressorLabel(method)

                        #luRas = os.path.join(env.scratchGDB, "xxluras")
                        #luRas = Lookup(tmpRaster, fName)  # failing to allocate memory on AK 10meter raster. Perhaps this is env workspace setting?

                        # Try to break the previous pprocess into two steps
                        outRas = Aggregate(Lookup(tmpRaster, fName), cellFactor, aggMethod, "EXPAND", "DATA")
                        time.sleep(2)
                        arcpy.Delete_management(tmpRaster)   
                        outRas.save(newRaster)
                        finalDesc = arcpy.Describe(newRaster)
                        finalRez = finalDesc.meanCellHeight

                        if finalRez != outputRes:
                            PrintMsg("\tError in final output resolution: " + str(finalRez) + " " + linearUnit, 1)
                                
                        del outRas

                    else:
                        # No resampling needed
                        method = "Using Lookup tool against the " + fName + " column (" + fldType + ")."
                        newMethod = "\n\rRaster Processing: " + method
                        PrintMsg("\t" + method, 0)
                        arcpy.SetProgressorLabel(method)
                        arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", fName + " IS NOT NULL")
                        outRas = Lookup(tmpRaster, fName)
                        time.sleep(2)

                        arcpy.Delete_management(tmpRaster)
                            
                        outRas.save(newRaster)

                        finalDesc = arcpy.Describe(newRaster)
                        finalRez = finalDesc.meanCellHeight

                        if finalRez != outputRes:
                            PrintMsg("\tError in final output resolution: " + str(finalRez) + " " + linearUnit, 1)
                                
                        time.sleep(1)
                        del outRas

                    if len(finalDesc.fields) > 0:
                        newFields = [fld.name for fld in finalDesc.fields]
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
                    
                if arcpy.Exists(tmpRaster):
                    # clean up any previous runs
                    time.sleep(1)
                    arcpy.Delete_management(tmpRaster)
                    arcpy.Delete_management(tmpLayerFile)
                    #del tmpRaster
        
                if bPyramids:
                    method = "Creating statistics and pyramids..."
                    PrintMsg("\t" + method, 0)
                    arcpy.SetProgressorLabel(method)
                    env.pyramid = "PYRAMIDS -1 NEAREST LZ77 # NO_SKIP"
                    arcpy.BuildPyramidsandStatistics_management(newRaster, "NONE", "BUILD_PYRAMIDS", "CALCULATE_STATISTICS", "NONE", "", "NONE", 1, 1, "", -1, "NONE", "NEAREST", "LZ77")

                if rendererType == 'uniqueValue':
                    # This could also include integer data like TFactor
                    try:
                        # Add RGB attributes for unique values. Will fail if output raster does not have a VAT
                        sdvTblName, xName, bName, fldType, fldLen = dLayerFields[sdvLayer]
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
                            newLayerFile = os.path.join(os.path.dirname(gdb), "SoilRas_" + newLayerName + ".lyr")

                        else:
                            if outputFolder.endswith(".gdb"):
                                newLayerFile = os.path.join(os.path.dirname(outputFolder), "SoilRas_" + newLayerName + ".lyr")

                            else:    
                                newLayerFile = os.path.join(outputFolder, "SoilRas_" + newLayerName + ".lyr")

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
                        #arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
                        arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")
                        # PrintMsg("\tAdded new map layer '" + newLayerName + "' to ArcMap in the UniqueValue section", 1)

                        # Cleanup layers
                        #PrintMsg("\tCleaning up temporary rasters", 1)
                        time.sleep(1)
                        arcpy.Delete_management(tmpLayerFile)
                        arcpy.Delete_management(tmpRaster)

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
                            newLayerFile = os.path.join(os.path.dirname(gdb), "SoilRas_" + newLayerName + ".lyr")

                        else:
                            newLayerFile = os.path.join(outputFolder, "SoilRas_" + newLayerName + ".lyr")
            
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
                            #arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
                            arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")
                            #PrintMsg("\tAdded new map layer '" + newLayerName + "' to ArcMap in the ClassifiedBreaks section", 1)
                            # Cleanup layers
                            #PrintMsg("\tCleaning up temporary rasters", 1)
                            time.sleep(1)
                            arcpy.Delete_management(tmpLayerFile)
                            arcpy.Delete_management(tmpRaster)

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
                        newLayerFile = os.path.join(os.path.dirname(gdb), "SoilRas_" + newLayerName + ".lyr")

                    else:
                        newLayerFile = os.path.join(outputFolder, "SoilRas_" + newLayerName + ".lyr")
                    
                    tmpLayerFile = os.path.join(env.scratchFolder, newLayerName + ".lyr")
                    tmpRaster = arcpy.MakeRasterLayer_management(newRaster, tmpRaster)
                    arcpy.SaveToLayerFile_management(tmpRaster, tmpLayerFile, "RELATIVE", "10.3")
                    finalMapLayer = arcpy.mapping.Layer(tmpLayerFile)

                    # Update raster map layer description
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
                    #arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
                    arcpy.SaveToLayerFile_management(finalMapLayer, newLayerFile, "RELATIVE", "10.3")

                    # Cleanup layers
                    #PrintMsg("\tCleaning up temporary rasters", 1)
                    time.sleep(1)
                    arcpy.Delete_management(tmpLayerFile)
                    arcpy.Delete_management(tmpRaster)

                    
                bMetadata = UpdateMetadata(gdb, newRaster, sdvLayer, newDescription, iRaster)
                #arcpy.SetProgressorPosition()

                # Clean up variables for each map layer here:
                PrintMsg("\tOutput raster:  " + newRaster, 0)
                del sdvTblName, fName, bName, fldType, fldLen, newDescription, newLayerName, symTbl, finalMapLayer, newRaster
                #arcpy.Compact_management(env.scratchGDB)
            
            elif arcpy.Exists(newRaster):
                PrintMsg("\tSkipping this map layer because output raster already exists", 1)


        grpLayerFile = os.path.join(outputFolder, os.path.basename(gdb).replace(".gdb", ".lyr"))
        arcpy.SaveToLayerFile_management(grpLayer, grpLayerFile, "RELATIVE", "10.3")
        
        PrintMsg(" \nCreateRasterLayers Function complete", 0)
        time.sleep(5)
        PrintMsg(" \nReturning to Main", 0)
##        try:
##            del sdvLayers, sdvLayer
##
##        except:
##            pass

        return grpLayer

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





# ====================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, traceback, arcpy, json, random
from arcpy import env
from arcpy.sa import *
import xml.etree.cElementTree as ET

try:


    if __name__ == "__main__":
        # Create a single table that contains
        sdvLayers = arcpy.GetParameter(0)                  # List of string values representing SDV layers from ArcMap TOC
        inputRaster = arcpy.GetParameterAsText(1)          # gSSURGO raster that will be used to create individual rasters based upon selected attributes
        outputFolder = arcpy.GetParameterAsText(2)         # If other than file geodatabase raster is desired, specify this folder path
        cellFactor = arcpy.GetParameter(3)                 # cellFactor multiplies the input resolution by this factor to aggregate to a larger cellsize
        outputRes = arcpy.GetParameter(4)                  # output raster resolution (input resolution * cellFactor
        bPyramids = arcpy.GetParameter(5)                  # Sets environment for raster post-processing
        # Skipping input resolution. It is information not needed for runtime
        bOverwrite = arcpy.GetParameter(7)                 # Overwrite output rasters

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

        # Get arcpy mapping objects
        global mxd, df, grpLayer
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        
        grpLayerName = "RASTER SOIL MAPS"

        grpLayers = arcpy.mapping.ListLayers(mxd, grpLayerName, df)
        
        if len(grpLayers) > 0:
            grpLayer = grpLayers[0]

        else:      
            grpLayer = CreateGroupLayer(grpLayerName, mxd, df)

        if grpLayer is None:
            raise MyError, ""
            
        grpLayer = arcpy.mapping.ListLayers(mxd, grpLayerName, df)[0]
        
        grpLayer = CreateRasterLayers(sdvLayers, inputRaster, outputFolder, bPyramids, cellFactor, outputRes, bOverwrite, mxd, df, grpLayer)


        time.sleep(3)
        PrintMsg(" \nRaster proccessing complete", 0)

except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

finally:
    arcpy.CheckInExtension("Spatial")

