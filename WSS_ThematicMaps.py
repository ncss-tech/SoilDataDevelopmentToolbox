# WSS_ThematicMaps.py
#
# Reads a WSS 3.2.0 AOI download dataset (SSURGO) and creates the selected soil maps
#
# 09-28-2016 version 1.0
#
# Dependency: "remove geoprocessing history.xlst"
#
# Fixed Bug: ClassBreaksJSON fails to create a legend when the numeric data values all fall
# within a single class break. Edwin Muniz.
#
# I noticed on 2017-02-07 that the ArcMap soil layers with 'Unique Values' symbology does not
# display the attribute field name in the TOC. I probably need to look at the JSON symbology code for Unique Values
# Wasn't able to figure this out, but I did simplify the code a bunch. Guessing it is a bug in updateLayerFromJSON.
#
# Added soil map layer to top of group. Still need to look at map scale vs label visibility and add metadata to description.
#
# Would like to add an option for NATMUSYM
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
def GetSaveRest(sdaURL, sQuery, totalAcres):
    # Get SAVEREST date for each survey area within the AOI
    # Send Post Rest query to SDM Tabular Service, returning data in JSON format
    #
    try:
        surveysEstablished = "?"

        if sQuery == "":
            raise MyError, ""

        #else:
        #   PrintMsg(" \nsQuery: " + sQuery, 1)

        # Tabular service to append to SDA URL
        url = sdaURL + "/Tabular/SDMTabularService/post.rest"

        dRequest = dict()
        dRequest["format"] = "JSON"
        dRequest["query"] = sQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        #PrintMsg(" \ndataList: " + str(dataList), 1)

        dateStamps = list()

        if len(dataList) > 0:
            for dateStamp in dataList:
                dateStamps.append(dateStamp[2] + " (" + dateStamp[0] + ", " + dateStamp[1] + ")")

        PrintMsg("Area of interest covers " + Number_Format(totalAcres, 1, True) + " acres in " + str(len(dateStamps)) + " survey area(s)", 0)

        surveysEstablished = "; ".join(dateStamps)

        return surveysEstablished

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def GetSurveyVersion(versionList):
    #
    #PrintMsg(" \nGetSurveyVersion parameter: " + str(versionList), 1)


    # Use list of areasymbols and spatialversion numbers to form the query for Soil Data Access
    # Return AREASYMBOL and SAVEREST date
    try:
        #PrintMsg(" \nversionList: " + str(versionList), 1)

        sQuery = """SELECT sc.areasymbol, sc.saverest, sc.areaname from sacatalog sc INNER JOIN saspatialver sp ON sc.areasymbol = sp.areasymbol WHERE"""
        cnt = 0

        for val in versionList:
            cnt += 1
            areasymbol = val[0]
            spatialver = val[1]

            if cnt > 1:
                sQuery = sQuery + " OR (sc.areasymbol = '" + areasymbol + "' AND sp.spatialversion = " + str(spatialver) + ") "

            else:
                sQuery = sQuery + " (sc.areasymbol = '" + areasymbol + "' AND sp.spatialversion = " + str(spatialver) + ") "

        sQuery = sQuery + " ORDER BY sc.saverest"
        #PrintMsg(" \n " + sQuery, 1)

        return sQuery

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def FieldTypes():
    # Create dictionary containing datatype conversions from SQL Server to ArcGIS
    # 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'
    try:
        dFieldTypes = dict()

        dFieldTypes["CHOICE"] = ["TEXT", 100]
        dFieldTypes["STRING"] = ["TEXT", 125]
        dFieldTypes["VTEXT"] = ["TEXT", 250]
        dFieldTypes["FLOAT"] = ["DOUBLE", 2]
        dFieldTypes["INTEGER"] = ["SHORT", 0]

        return dFieldTypes

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dFieldTypes

    except:
        errorMsg()
        return dFieldTypes

## ===================================================================================
def Units():
    # Create dictionary containing abbreviations for units of measure. These are not supplied by WSS
    #
    try:
        dUnits = {u'tons per acre per year': u'tons/acre/yr', u'grams per cubic centimeter': u'g/cm3', u'centimeters per centimeter': u'cm/cm', u'micrometers per second': u'um/s', u'percent': u'percent', u'days': u'days', u'feet': u'ft', u'pounds per acre per year': u'lbs/acre/yr', u'centimeters': u'cm', u'milliequivalents per 100 grams': u'meq/100g'}
        return dUnits

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return {}

    except:
        errorMsg()
        return {}

## ===================================================================================
def GetKeys(theInput, keyField):
    # Create bracketed list of MUKEY values from spatial layer for use in query
    #
    try:
        # Tell user how many features are being processed
        theDesc = arcpy.Describe(theInput)
        theDataType = theDesc.dataType
        PrintMsg("", 0)

        #if theDataType.upper() == "FEATURELAYER":
        # Get Featureclass and total count

        if theDataType.lower() == "featurelayer":
            theFC = theDesc.featureClass.catalogPath
            theResult = arcpy.GetCount_management(theFC)

        elif theDataType.lower() in ["featureclass", "shapefile"]:
            theResult = arcpy.GetCount_management(theInput)

        else:
            raise MyError, "Unknown data type: " + theDataType.lower()

        iTotal = int(theResult.getOutput(0))

        if iTotal > 0:
            sqlClause = ("DISTINCT " + keyField, "ORDER BY " + keyField)
            keyList = list()

            with arcpy.da.SearchCursor(theInput, [keyField], sql_clause=sqlClause) as cur:
                for rec in cur:
                    keyList.append(int(rec[0]))

            #PrintMsg("\tmukey list: " + str(keyList), 1)
            return keyList

        else:
            return []


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def MetadataDetails():
    # Dictionary containing new metadata information for the output featureclass.
    #
    try:
        dMetadata = dict()

        dMetadata["abstract"] = """Thematic soil maps and data generated by Web Soil Survey as
        part of the National Cooperative Soil Survey. Each thematic soil map dataset is
        created for a user-defined area of interest and is downloaded from a Web Soil
        Survey session. The source Soil Survey Geographic (SSURGO) database depicts
        information about the kinds and distribution of soils on the landscape. Created """

        dMetadata["purpose"] = """Duplicates the soil thematic maps created in the user's Web Soil Survey session
        that were saved as an AOI download. The downloaded soil property and interpretation
        data can be archived or used in further GIS analysis."""

        dMetadata["legal"] = """The U.S. Department of Agriculture (USDA) prohibits discrimination
        against its customers, employees, and applicants for employment on the basis of
        race, color, national origin, age, disability, sex, gender identity, religion,
        reprisal, and where applicable, political beliefs, marital status, familial or
        parental status, sexual orientation, or all or part of an individual's income
        is derived from any public assistance program, or protected genetic information
        in employment or in any program or activity conducted or funded by the Department.
        (Not all prohibited bases will apply to all programs and/or employment activities.)
        To file a complaint of discrimination, complete, sign and mail the USDA Program
        Discrimination Complaint Form (PDF), found online at
        http://www.ascr.usda.gov/complaint_filing_cust.html, or at any USDA office, or call
        (866) 632-9992 to request the form. Send your completed complaint form or letter to
        us by mail at: USDA Office of the Assistant Secretary for Civil Rights 1400
        Independence Avenue, S.W. Washington, D.C. 20250-9410 Or by email at
        program.intake@usda.gov. Individuals who are deaf, hard of hearing or have speech
        disabilities and you wish to file either an EEO or program complaint please contact
        USDA through the Federal Relay Service at (800) 877-8339 or (800) 845-6136
        (in Spanish). Persons with disabilities who wish to file a program complaint,
        please see information above on how to contact us by mail directly or by email.
        If you require alternative means of communication for program information (e.g.,
        Braille, large print, audiotape, etc.) please contact USDA's TARGET Center at
        (202) 720-2600 (voice and TDD)."""

        dMetadata["limitations"] = """Limitations of use. The U.S. Department of Agriculture, Natural
        Resources Conservation Service, should be acknowledged as the data source in
        products derived from these data.This dataset is not designed for use as a
        primary regulatory tool in permitting or siting decisions, but may be used
        as a reference source. This is public information and may be interpreted by
        organizations, agencies, units of government, or others based on needs;
        however, they are responsible for the appropriate application. Federal,
        State, or local regulatory bodies are not to reassign to the Natural Resources
        Conservation Service any authority for the decisions that they make. The Natural
        Resources Conservation Service will not perform any evaluations of these maps
        for purposes related solely to State or local regulatory programs. Digital data
        files are periodically updated. Files are dated, and users are responsible for
        obtaining the latest version of the data."""

        dMetadata["ssurgo"] = """The SSURGO dataset is a digital soil survey and generally is the most
        detailed level of soil geographic data developed by the National Cooperative Soil
        Survey. The information was prepared by digitizing maps, by compiling information
        onto a planimetric correct base and digitizing, or by revising digitized maps
        using remotely sensed and other information. This dataset consists of georeferenced
        digital map data and computerized attribute data. The map data are in a soil survey
        area extent format and include a detailed, field verified inventory of soils and
        miscellaneous areas that normally occur in a repeatable pattern on the landscape
        and that can be cartographically shown at the scale mapped. The soil map units are
        linked to attributes in the National Soil Information System (NASIS) relational
        database, which gives the proportionate extent of the component soils and their
        properties."""

        dMetadata["wss"] = """A Web Soil Survey session was used to create an area of interest download
        in the form of SSURGO shapefiles along with all thematic map and rating information."""

        dMetadata["arcmap"] = """The soil polygon shapefile and associated thematic map information were imported
        into an ESRI file geodatabase for display and analysis by a Python script (""" + scriptPath + """) using ArcGIS """ + installInfo["ProductName"] + " " + installInfo["Version"] + "."

        dMetadata["credits"] = """Web Soil Survey, USDA Natural Resources Conservation Service, National Cooperative Soil Survey"""

        return dMetadata

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def ClassBreaksJSON(legendList, dParams, dValues):
    # returns JSON string for classified break values template. Use this for numeric data.

    try:
        #PrintMsg(" \nRunning ClassBreaksJSON...", 1)

        # Initialize dictionary (return value)
        dLayerDefinition = dict()

        # Set outline symbology
        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        #PrintMsg(" \nlegendList: \n" + str(legendList), 1)
        #PrintMsg(" \ndValues: \n" + str(dValues), 1)

        # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges
        # Do I want to remove the defaultSymbol and defaultLabel if there are no null values in the data???
        #
        jsonString = """
{"type" : "classBreaks",
  "field" : "",
  "classificationMethod" : "esriClassifyManual",
  "minValue" : 0.0,
  "classBreakInfos" : [
  ]
}"""

        d = json.loads(jsonString)
        # hexVal = "#FFFF00"drawingInfo" : {"renderer" :
        # h = hexVal.lstrip('#')
        # rgb = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))

        d["field"]  = dParams["ResultColumnName"]
        d["drawingInfo"] = dict() # new
        #d["defaultSymbol"]["outline"]["color"] = outLineColor

        # Find minimum value by reading dRatings
        #
        # This creates a problem for Hydric, because the legend is in descending order (100% -> 0%). Most others are ascending.
        minValue = 999999999
        maxValue = -999999999

        for rating in dValues.values():
            try:
                ratingValue = float(rating)
                #PrintMsg("\tRating (float): " + str(ratingValue), 1)

                if rating is not None:
                    if ratingValue < minValue:
                        minValue = float(rating)

                    if ratingValue > maxValue:
                        maxValue = float(rating)

            except:
                pass

        # Add new rating field to list of layer fields
        d["field"] = dParams["ResultColumnName"]
        d["minValue"] = minValue
        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()

        lastMax = minValue

        # Somehow I need to read through the legendList and determine whether it is ascending or descending order
        if cntLegend > 1:

            # Get first and last values from legendList
            firstRating = legendList[0][0]
            lastRating = legendList[(cntLegend - 1)][0]

            if firstRating > lastRating:
                legendList.reverse()

        elif cntLegend == 1:
            #PrintMsg(" \nSingle item map legend", 1)
            firstRating = legendList[0][0]
            lastRating = legendList[0][0]

        else:
            raise MyError, "legendList problem: " + str(legendList)

        # Create standard numeric legend in Ascending Order
        #
        if cntLegend > 1:

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                rating, label, hexCode = legendList[cnt]
                if not rating is None:

                    ratingValue = float(rating)
                    #PrintMsg(" \n\t\tAdding legend values: " + str(lastMax) + "-> " + str(rating) + ", " + str(label), 1)

                    # calculate rgb colors
                    rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    rgb.append(255)  # set transparency ?
                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = lastMax
                    dLegend["classMaxValue"] = ratingValue
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = outLineColor
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    dLegend["outline"] = dOutline
                    classBreakInfos.append(dLegend)
                    lastMax = ratingValue
                    cnt += 1

        elif cntLegend == 1:

            for cnt in range(0, (cntLegend)):

                rating, label, hexCode = legendList[cnt]
                if not rating is None:
                    ratingValue = float(rating)

                    # calculate rgb colors
                    rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    rgb.append(255)  # set transparency ?
                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = lastMax
                    dLegend["classMaxValue"] = ratingValue
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = outLineColor
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    dLegend["outline"] = dOutline
                    classBreakInfos.append(dLegend)
                    lastMax = ratingValue

                    cnt += 1

        d["classBreakInfos"] = classBreakInfos

        dRenderer = dict()
        dRenderer["renderer"] = d
        dLayerDefinition["drawingInfo"] = dRenderer

        #PrintMsg(" \n1. dLayerDefinition: \n" + str(dLayerDefinition), 0)

        return dLayerDefinition

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dLayerDefinition

    except:
        errorMsg()
        return dLayerDefinition

## ===================================================================================
def SimpleFeaturesJSON():
    # returns JSON string for soil lines and labels layer.
    #
    try:

        outLineColor = [0, 0, 0, 255]  # black polygon outline

        d = dict()
        r = dict()

        r["type"] = "simple"
        s = {"type": "esriSFS", "style": "esriSFSNull", "color": [255,255,255,255], "outline": { "type": "esriSLS", "style": "esriSLSSolid", "color": [0, 0, 0,255], "width": 0.4 }}
        r["symbol"] = s
        d["drawingInfo"]= dict()
        d["drawingInfo"]["renderer"] = r
        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def UniqueValuesJSON(legendList, dParams):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    # Done: I need to get rid of the non-Renderer parts of the JSON so that it matches the ClassBreaksJSON function.
    # Need to implement this in the gSSURGO Mapping tools
    try:

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        d = dict()
        r = dict()
        v = dict()

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()
        #PrintMsg(" \nlegendList: " + str(legendList), 1)

        for cnt in range(0, len(legendList)):
            dSymbol = dict()
            rating, label, hexCode = legendList[cnt]

            # calculate rgb colors
            rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            rgb.append(255)  # transparency doesn't seem to work
            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}
            legendItems = dict()
            legendItems["value"] = rating
            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
            legendItems["label"] = label
            legendItems["symbol"] = symbol
            uniqueValueInfos.append(legendItems)

        v["uniqueValueInfos"] = uniqueValueInfos
        v["type"] = "uniqueValue"
        v["field1"] = dParams["ResultColumnName"]
        r["renderer"] = v
        d["drawingInfo"] = r

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def ReadSummary(summaryFile, mapLayers):
    # create summary dictionary from summary file for matching records
    # key = mapID, value = map name
    #
    # sample lines:
    #
    # ID 5851: Corrosion of Steel
    # ID 5852: Dwellings With Basements

    try:
        if not arcpy.Exists(summaryFile):
            raise MyError, "Missing " + summaryFile

        dMaps = dict()
        choiceList = dict()
        mapList = list()

        # Parse sequence number and map names from user selection
        if len(mapLayers) > 0:
            for choice in mapLayers:
                # parse the user choices for soil maps to return sequence and soil map name
                delim = choice.find(".")
                cnt = int(choice[0:delim])
                mapName = choice[delim + 1:]
                choiceList[cnt] = mapName.strip()
                #PrintMsg(" \nAdding map layer " + str(cnt) + " - " + mapName + " to dMaps dictionary", 1)

        # This code as written will only keep the last map if there are duplicate names.
        # Reason: Map name is the dictionary key value.
        # Please note! Changing code to Keep duplicate maps will cause problems later with duplicate rating field names.
        #
        fh = open(summaryFile, "r")
        rowCnt = 0

        for rec in fh:
            sData = rec.split(":")

            if sData[0].startswith("ID "):
                rowCnt += 1
                # this is the mapID data
                mapID = int(sData[0].split(" ")[1])
                mapName = sData[1].strip()
                mapList.append(mapID)

                if rowCnt in choiceList:
                    if mapName in dMaps:
                        PrintMsg(" \n\tWarning. '" + mapName + "' is a duplicate map. Only the last one will be used.", 1)

                    dMaps[mapName] = mapID

        return dMaps

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dMaps

    except:
        errorMsg()
        return dMaps

## ===================================================================================
def ReadParameters(paramsFile):
    # create parameters dictionary from parameters file
    #
    try:
        dParams = dict()

        if not arcpy.Exists(paramsFile):
            raise MyError, "Missing " + paramsFile

        # Add user name to parameter dictionary
        envUser = arcpy.GetSystemEnvironment("USERNAME")

        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = env.User.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser


        fh = open(paramsFile, "r")
        rec = fh.readline()

        while rec:
            #PrintMsg(" \n" + str(rec), 1)

            delim = rec.find(":")
            key = rec[0:delim].strip()

            if not key is None:
                val = rec[(delim + 1):].strip()
                if val == '""':
                    val = None

                if not val is None and not val.isdigit():
                    val = val[1:-1] # get rid of double quotes

                if key == "SdvAttributeDescription":
                    # continue reading into the current value
                    while rec:
                        rec = fh.readline()
                        val = val + "\n" + rec

                    dParams[key] = val
                    #PrintMsg(" \n" + key + ": " + val, 1)
                    break  # assuming this is the last attribute in the file

                dParams[key] = val
                #PrintMsg(key + ": " + str(val), 1)

            rec = fh.readline()

        fh.close()

        dParams["User"] = userName

        #PrintMsg(" \ndParams contains " + str(len(dParams)) + " items", 1)
        return dParams

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dParams

    except:
        errorMsg()
        return dParams

## ===================================================================================
def CreateGroupLayer(grpLayerName):
    # create output table and read the rating file into it
    # header: MapUnitKey, MapUnitRatingString, MapUnitRatingNumeric, RgbString
    # SDV dataTypes: 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'
    #
    # Probably need to use csv reader for this

    try:
        # Use template lyr file stored in current script directory to create new Group Layer
        # This SDVGroupLayer.lyr file must be part of the install package along with
        # any used for symbology. The name property will be changed later.
        grpLayerFile = os.path.join(scriptPath, "SDV_GroupLayer.lyr")

        if not arcpy.Exists(grpLayerFile):
            raise MyError, "Missing group layer file (" + grpLayerFile + ")"

        #grpLayerName = "WSS Thematic Soil Maps"
        testLayers = arcpy.mapping.ListLayers(mxd, grpLayerName, df)

        if len(testLayers) > 0:
            # If it exists, remove an existing group layer from previous run
            grpLayer = testLayers[0]
            #PrintMsg(" \nRemoving old group layer", 1)
            arcpy.mapping.RemoveLayer(df, grpLayer)

        grpLayer = arcpy.mapping.Layer(grpLayerFile)
        grpLayer.visible = True
        grpLayer.name = grpLayerName
        grpLayer.description = "Group layer containing individual WSS thematic soil map layers described in " + thematicPath
        arcpy.mapping.AddLayer(df, grpLayer, "TOP")
        grpLayer = arcpy.mapping.ListLayers(mxd, grpLayerName, df)[0]
        grpDesc = arcpy.Describe(grpLayer)

        if grpDesc.dataType.lower() != "grouplayer":
            raise MyError, "Problem with group layer"

        #PrintMsg(" \nAdding group layer: " + str(grpLayer.name), 0)

        return grpLayer

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def ReadRatings(ratingFile, dataType, dFieldTypes):
    # create output table and read the rating file into it
    # header: MapUnitKey, MapUnitRatingString, MapUnitRatingNumeric, RgbString
    # SDV dataTypes: 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'
    #
    # Probably need to use csv reader for this

    try:
        dRatings = dict()  # hexcode, rating
        dValues = dict()  # mukey, rating

        if not arcpy.Exists(ratingFile):
            raise MyError, "Missing " + paramsFile

        csv.QUOTE_NONNUMERIC

        codePage = 'iso-8859-1'

        if dataType in ("FLOAT", "INTEGER"):
            # read the 0, 2, 3 columns from the rating.csv file
            iPop = 1 # cols = [0, 2, 3]

        else:
            # CHOICE, STRING or VTEXT data
            iPop = 2 # cols = [0, 1, 3]

        # hardcoded field lengths used to truncate rating value if it is too long to fit in the table

        # Track 'Not rated' for Interps
        notRated = ""

        # Process String data for unique values
        if dFieldTypes[dataType.upper()][0] == "TEXT":
            # Set field length for string-rating to actual field width because the value may not fit
            fldLengths = [30, dFieldTypes[dataType.upper()][1], 8]  # mukey, rating, hexcode

            # Open output table for string data
            iRow = 0  # record counter. Skip column header and first dummy record

            for rowInFile in csv.reader(open(ratingFile, 'r'), delimiter=',', quotechar='"'):

                if iRow > 1:

                    newRow = list()
                    fldNo = 0
                    fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                    fixedRow.pop(iPop)  # lose the data from the column that is not populated


                    for value in fixedRow:
                        # convert blank strings to null
                        fldLen = fldLengths[fldNo]

                        if value == '': # only works for FGDB output table
                            value = None

                        elif fldLen > 0: # . Truncate values that won't fit in the defined output column.
                            value = value[0:fldLen]

                        newRow.append(value)
                        fldNo += 1

                    mukey, rating, hexCode = newRow

                    if not hexCode in dRatings and not rating is None:
                        # save hex value as key and rating as value to dRatings dictionary
                        dRatings[hexCode] = rating  # dRatings[hexcode] = rating
                        #PrintMsg("\tAdded hexcode:" + hexCode + " to dRatings with a rating of " + str(rating), 0)
                        if rating.upper() == "NOT RATED":
                            notRated = rating

                    dValues[mukey] = rating  # dValues[mukey] = rating value

                iRow += 1

        else:
            # Process Numeric data for class breaks
            #
            # Set field length to zero so that we do not truncate a numeric rating
            # Open output table for numeric data
            iRow = 0  # record counter. Skip first dummy record
            for rowInFile in csv.reader(open(ratingFile, 'r'), delimiter=',', quotechar='"'):

                if iRow > 1:
                    fldNo = 0
                    fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                    fixedRow.pop(iPop)  # lose the data from the column that is not populated
                    mukey, rating, hexCode = fixedRow

                    try:
                        rating = float(rating)

                        if not hexCode in dRatings:
                            # save hex value as key and rating as value to dRatings dictionary
                            dRatings[hexCode] = rating  # dRatings[hexcode] = rating

                        else:
                            if rating > dRatings[hexCode]:
                                dRatings[hexCode] = rating

                            else:
                                #PrintMsg(" \nIgnoring rating value for color (" + hexCode + "): " + str(rating), 1)
                                pass

                        if not mukey in dValues:
                            # save mukey as key and rating
                            dValues[mukey] = rating

                    except:
                        pass

                iRow += 1

        return dRatings, dValues, notRated

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dRatings, dValues

    except:
        errorMsg()
        return dRatings, dValues

## ===================================================================================
def ReadLegend(legendFile, dataType, dParams):
    # create a dictionary containing hexcode(key) and rating label for string values
    # create a list of colors (should be unique)
    #
    try:
        # Create two dictionaries. One uses the hex color as key, the other the legend label
        dColors = dict()
        dLegendLabels = dict()
        colorList = list()    # ordered list for legend, based upon hex value
        codePage = 'iso-8859-1'
        iRow = 0

        for rowInFile in csv.reader(open(legendFile, 'rb'), delimiter=',', quotechar='"'):
            iRow += 1

            if iRow > 1:
                newRow = list()
                fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                label, color = fixedRow

                if iRow == 2 and not dParams["UnitsofMeasure"] is None:
                    if dParams["UnitsofMeasure"] in dUnits:
                        # Add abbreviation for rating units to first legend label
                        label = label + "  (" + dUnits[dParams["UnitsofMeasure"]] + ")"

                    else:
                        # Add rating units to first legend label
                        label = label + "  (" + dParams["UnitsofMeasure"] + ")"

                dColors[color] = label
                colorList.append(color)

        return dColors, colorList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dColors, colorList

    except:
        errorMsg()
        return dColors, colorList

## ===================================================================================
def CreateDescription(dParams, surveysEstablished):
    # Create layer description string using parameter file and survey dates from Soil Data Access
    #
    try:
        description = ""
        dList1 = ["AoiSoilThematicMapID", "CreationDateTime", "ResultColumnName", "AggregationMethod", "TiebreakRule",
        "UnitsofMeasure", "ComponentPercentCutoff", "InterpretNullsAsZero", "BeginningMonth",
        "EndingMonth", "LayerOption", "TopDepth", "BottomDepth", "DepthUnits"]

        # Update layer description
        description = dParams["SdvAttributeDescription"] + "\r\nMap ID: " + str(dMaps[dParams["SdvAttributeName"]]) + "\r\nSpatial archived: " + surveysEstablished
        description = description + "\r\nImported to ArcGIS by " + dParams["User"] + "; " + datetime.date.today().isoformat() + " using " + scriptPath

        for key in dList1:
            param = dParams[key]
            if not param is None and not param == "":

                if key in ["TopDepth", "BottomDepth", "DepthUnits"] and (dParams["TopDepth"] == '0' and dParams["BottomDepth"] == '0'):
                    # Skip depth values if set to zero for both top and bottom. Need to make sure that some of the surface properties
                    # don't get included by this filter.
                    pass

                else:
                    #PrintMsg("\tKey: " + key + ", " + str(param), 1)
                    description = description + "\r\n" + key + ": " + param

        if not dParams["PrimaryDataSelectOptionLabel"] is None:
            description = description + "\r\n" + dParams["PrimaryDataSelectOptionLabel"] + ": " + str(dParams["PrimaryDataSelectOption"])

        if not dParams["SecondaryDataSelectOptionLabel"] is None:
            description = description + "\r\n" + dParams["SecondaryDataSelectOptionLabel"] + ": " + str(dParams["SecondaryDataSelectOption"])

        return description

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return description

    except:
        errorMsg()
        return description

## ===================================================================================
def AggregationMethod(aggDescription, tieBreakRule):
    # Get aggregation method abbreviation for use in layer name
    try:

        aggMethod = ""
        dAggMethod = dict()
        dAggMethod["Dominant Component"] = "(DCP)"
        dAggMethod["Dominant Condition"] = "(DCD)"
        dAggMethod["Weighted Average"] = "(WTA)"

        if aggDescription in dAggMethod:
            aggMethod = dAggMethod[aggDescription]

        elif aggDescription == "Minimum or Maximum":
            if  tieBreakRule == "&gt;":
                aggMethod = "(Max)"

            elif tieBreakRule == "&lt;":
                aggMethod = "(Min)"

        return aggMethod

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return aggMethod

    except:
        errorMsg()
        return aggMethod

## ===================================================================================
def UpdateLayer(newLayer, dValues, dParams):
    # Create layer description string
    try:

        # Add current rating data to output featureclass and collect information for report
        #
        dataType = dParams["ResultDataType"]

        with arcpy.da.UpdateCursor(newLayer, ["mukey", dParams["ResultColumnName"], "acres"]) as cur:
            for rec in cur:
                mukey = rec[0]
                acres = rec[2]

                if mukey in dValues:
                    rating = dValues[mukey]

                else:
                    rating = None

                rec[1] = rating
                cur.updateRow(rec)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ClearHistory(inputFC, remove_gp_history_xslt):
    # Clear GP history from output featureclass
    try:

       # Clear geoprocessing history from the target metadata
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        arcpy.XSLTransform_conversion(outputFC, remove_gp_history_xslt, out_xml, "")

        arcpy.MetadataImporter_conversion(out_xml, outputFC)

        # delete the temporary xml metadata files
        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def UpdateLayerwithStats(newLayer, dValues, dParams):
    # Create layer description string
    try:

        # Add current rating data to output featureclass and collect information for report
        #
        dRatingAcres = dict()  # use this dictionary for text or integer values
        wtdAcres = 0.0
        totalAcres = 0.0
        dataType = dParams["ResultDataType"]

        with arcpy.da.UpdateCursor(newLayer, ["mukey", dParams["ResultColumnName"], "acres"]) as cur:
            for rec in cur:
                mukey = rec[0]
                acres = rec[2]

                if not acres is None:
                    totalAcres += acres
                #PrintMsg("\t" + mukey + " " + str(acres), 1)

                if mukey in dValues:
                    rating = dValues[mukey]

                else:
                    rating = None

                rec[1] = rating
                cur.updateRow(rec)

                # Summary
                if not acres is None:
                    if dataType.upper() in ['CHOICE', 'STRING', 'VTEXT', 'INTEGER']:
                        #PrintMsg(" \nGetting unique values legend", 1)

                        if rating in dRatingAcres:
                            dRatingAcres[rating] += acres

                        else:
                            dRatingAcres[rating] = acres

                    elif dataType.upper() in ['FLOAT']:
                        #PrintMsg(" \nGetting class breaks legend", 1)

                        if rating is not None:
                            wtdAcres += acres * rating

        return dRatingAcres, wtdAcres, totalAcres

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dRatingAcres, wtdAcres, totalAcres

    except:
        errorMsg()
        return dRatingAcres, wtdAcres, totalAcres

## ===================================================================================
def AddFirstSoilMap(outputFC, summary, surveyInfo):
    # Create the top layer which will be simple black outline, no fill with MUSYM labels, visible
    # Run SDA query to add NATMUSYM and MAPUNIT NAME to featureclass
    try:

        mapLayerName = "Soil Labels"

        # Remove existing map layers with same name
        existingLayers = arcpy.mapping.ListLayers(mxd, mapLayerName, df)

        for soilMap in existingLayers:
            if soilMap.longName == os.path.join(grpLayerName, mapLayerName):
                arcpy.mapping.RemoveLayer(df, soilMap)

        # 5. Update layerDefinition dictionary for this map layer
        newLayer = arcpy.mapping.Layer(wssLayerFile)
        newLayer.name = mapLayerName
        newLayer.description = summary
        newLayer.visible = True
        newLayer.transparency = fillTransparency
        newLayer.showLabels = True

        # Update layer symbology using JSON dictionary
        if version[0:4] in ["10.3", "10.4", "10.5"]:
            #PrintMsg(" \nUpdating symbology using JSON string", 1)

            # Update layer symbology using JSON
            dLayerDefinition = SimpleFeaturesJSON()
            newLayer.updateLayerFromJSON(dLayerDefinition)
            #PrintMsg(" \n" + str(dLayerDefinition), 1)

        # Try adding musym labels to each soil map and see how annoying that is
        bZoomed = ZoomToExtent(newLayer)
        bLabeled = AddLabels(newLayer, True)
        #newLayer.showLabels = True

        arcpy.mapping.AddLayerToGroup(df, grpLayer, newLayer, "TOP")  # add soil map layer to group layer

        mapLayerFile = os.path.join(basePath, newLayer.name + ".lyr")
        arcpy.SaveToLayerFile_management(newLayer, mapLayerFile, "RELATIVE", "10.1")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def AttributeRequest(sdaURL, outputTable, sQuery, keyField):
    # POST REST which uses urllib and JSON
    #
    # Uses an InsertCursor to populate the new outputTable
    #
    # Send query to SDM Tabular Service, returning data in JSON format,
    # creates a new table and loads the data into a new Table in the geodatabase
    # Returns a list of key values and if keyField = "mukey", returns a dictionary like the output table

    try:
        #outputValues = []  # initialize return values (min-max list)
        dMapunitInfo = dict()

        #PrintMsg(" \n2. Requesting tabular data for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")
        #PrintMsg(" \n" + "Sending tabular request to Soil Data Access...", 0)


        if sQuery == "":
            raise MyError, "Missing query string"

        # Tabular service to append to SDA URL
        url = sdaURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["format"] = "JSON+COLUMNNAME+METADATA"
        dRequest["query"] = sQuery

        #PrintMsg(" \nURL: " + url)
        #PrintMsg("QUERY: " + sQuery)

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        if outputTable == "":
            raise MyError, ""

        # Find the key field and set an index
        keyIndx = columnNames.index(keyField)

        with arcpy.da.SearchCursor(outputTable, columnNames) as cur:
            for rec in dataList:
                key = rec[keyIndx]
                dMapunitInfo[key] = rec

        arcpy.SetProgressorLabel("Finished importing attribute data")

        return dMapunitInfo

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dMapunitInfo

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return dMapunitInfo

    except:
        errorMsg()
        return MapunitInfo

## ===================================================================================
def GetMapunitInformation(outputFC):
    #
    # Create 'Soil Labels' layer description string including map unit summaries from SDA
    #
    try:

        # Polygon acres are already calculated by the UpdateLayerwithStats function. Just
        # need to get a map unit total.
        #
        # Look for code containing 'Spatial archived:' to find list of Areasymbols for this dataset.
        #
        # Run SDA query to get NATMUSYM, AREASYMBOL, MUNAME for this dataset

        # Using mapunit and legend table for the selected mapunits.

        keyList = GetKeys(outputFC, "mukey")

        mukeys = str(keyList)[1:-1]

        sQuery = """SELECT M.mukey, M.nationalmusym as natmusym, M.muname
        FROM mapunit M WITH (nolock)
        INNER JOIN legend L ON L.lkey = M.lkey AND M.mukey in (""" + mukeys + """)
        ORDER BY mukey"""

        dMapunitInfo = AttributeRequest(sdaURL, outputFC, sQuery, "mukey")  # Need to get ratingField here
        #PrintMsg(" \n" + str(dMapunitInfo), 1)

        dMapunit = dict()  # key=mukey, acres, areasymbol, musym, muname
        totalAcres = 0
        fields = ["SHAPE@", "MUKEY", "MUSYM", "NATMUSYM", "MUNAME", "ACRES", "AREASYMBOL", "SPATIALVER"]
        versionList = list()

        with arcpy.da.UpdateCursor(outputFC, fields) as cur:
            for rec in cur:
            #for mukey in dMapunit:
                mukey = rec[1]
                musym = rec[2]
                areasymbol = rec[6]
                spatialver = rec[7]
                muInfo = dMapunitInfo[mukey]
                junk, natmusym, muname = muInfo
                acres = rec[0].getArea("GEODESIC", "ACRES")
                rec[3] = natmusym
                rec[4] = muname
                rec[5] = acres
                cur.updateRow(rec)

                if not acres is None:
                    totalAcres += acres

                    if mukey in dMapunit:
                        dMapunit[mukey][0] += acres

                    else:
                        dMapunit[mukey] = [acres, areasymbol, musym, muname]

                    version = (areasymbol, spatialver)

                    if not version in versionList:
                        versionList.append(version)


            sQuery = GetSurveyVersion(versionList)  # Problem here??
            PrintMsg(" \n")

            surveyInfo = GetSaveRest(sdaURL, sQuery, totalAcres)

            # version list is a list of tuples made up of areasymbol and spatialver
            #
            soilSummary = "Soil survey areas include: " + surveyInfo + "\r\n\r\nTotal acres within AOI: " + Number_Format(totalAcres, 1, True) + "\r\n\r\nAREASYMBOL| MUSYM| MUNAME| ACRES"

            for mukey in sorted(dMapunit.keys()):
                acres, areasymbol, musym, muname = dMapunit[mukey]
                soilSummary = soilSummary + " \r\n" + areasymbol + "| " + musym + "| " + muname + "| " + Number_Format(acres, 1, True)

        return soilSummary, surveyInfo

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return soilSummary

    except:
        errorMsg()
        return soilSummary

## ===================================================================================
def AddNewFields(outputTable, columnNames, columnInfo):
    # Create new table. Start with in-memory and then export to geodatabase table
    #
    # ColumnNames and columnInfo come from the Attribute query JSON string
    # MUKEY would normally be included in the list, but it should already exist in the output featureclass
    #
    try:
        # Dictionary: SQL Server to FGDB
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

        #joinFields = list()

        for i, fldName in enumerate(columnNames):
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if fldName.lower().endswith("key"):
                # Per SSURGO standards, key fields should be string. They come from Soil Data Access as long integer.
                dataType = 'text'
                length = 30

            arcpy.AddField_management(outputTable, fldName, dataType, precision, scale, length)

        return outputTable

    except:
        errorMsg()
        return ""

## ===================================================================================
def AddSoilMap(mapID, surveysEstablished, dParams):
    # Create each new soil map layer
    #
    try:

        # Name each input file to be read for this map
        paramsFile = os.path.join(thematicPath, "parameters" + str(mapID) + ".txt")
        ratingFile = os.path.join(thematicPath, "rating" + str(mapID) + ".csv")
        legendFile = os.path.join(thematicPath, "filteredLegend" + str(mapID) + ".csv")

        # Create dictionaries from thematic text and csv files
        #
        aggMethod = AggregationMethod(dParams["AggregationMethod"], dParams["TiebreakRule"])
        if aggMethod == "":
            mapLayerName = dParams["SdvAttributeName"]

        else:
            mapLayerName = dParams["SdvAttributeName"] + " " + aggMethod

        if not dParams["DepthUnits"] is None:
            mapLayerName = mapLayerName + " " + dParams["TopDepth"] + "-" + dParams["BottomDepth"] + dParams["DepthUnits"]

        dataType = dParams["ResultDataType"]  # current domain: 'Choice', 'Float','Integer', 'string', 'VText'
        tblName = mapLayerName
        title = mapLayerName + " (Map ID: " + str(mapID) + ")"
        PrintMsg(" \n" + title, 0)

        # Remove existing map layers with same name
        # NOTE! Isn't this now done in the AddSoilLabels function???
        #
        #
        #PrintMsg(" \nSee if the RemoveLayer section can be deleted from 'AddSoilMap' function", 1)
        existingLayers = arcpy.mapping.ListLayers(mxd, mapLayerName, df)

        for soilMap in existingLayers:
            if soilMap.longName == os.path.join(grpLayerName, mapLayerName):
                arcpy.mapping.RemoveLayer(df, soilMap)

        #
        # 2. Legend
        dLegend, colorList = ReadLegend(legendFile, dataType, dParams)
        #PrintMsg(" \nReturned colorList: " + str(colorList), 1)

        if dLegend is None or len(dLegend) == 0:
            raise MyError, "Failed to get legend file information"

        #
        # 3. Ratings. Get field definitions and rating datatype before hand.
        dFieldTypes = FieldTypes()
        dRatings, dValues, notRated = ReadRatings(ratingFile, dataType.upper(), dFieldTypes)

        if dRatings is None or len(dRatings) == 0:
            raise MyError, ""

        # 4. Assemble all required legend information into a single, ordered list
        legendList = list()

        for clr in colorList:
            try:
                #PrintMsg("\tGetting legend info for " + clr, 1)
                rating = dRatings[clr]  # Failing here
                legendLabel = dLegend[clr]
                legendList.append([rating, legendLabel, clr])
                #PrintMsg(" \nAppend to legendList: " + str(rating) + ": " + str(legendLabel) + "; " + clr, 1)

            except:
                pass  # If the legend contains items for data that does not exist in this AOI, skip adding it to the legend

        # For soil interpretations, preserve 'Not rated' and assign gray
        if notRated:
            legendList.append([notRated, notRated, "#DCDCDC"])
        #PrintMsg(" \nlegendList: " + str(legendList), 1)

        # 5. Create layer definition using JSON string

        if dataType.upper() in ['CHOICE', 'STRING', 'VTEXT']:
            #PrintMsg(" \nGetting unique values legend", 1)
            dLayerDefinition = UniqueValuesJSON(legendList, dParams)

        elif dataType.upper() in ['FLOAT','INTEGER']:
            #PrintMsg(" \nGetting class breaks legend", 1)
            dLayerDefinition = ClassBreaksJSON(legendList, dParams, dValues)

        else:
            raise MyError, "Cannot handle data type: " + dataType.upper()

        if dLayerDefinition is None or len(dLayerDefinition) == 0:
            raise MyError, ""

        # 5. Update layerDefinition dictionary for this map layer
        newLayer = arcpy.mapping.Layer(wssLayerFile)
        newLayer.name = mapLayerName
        layerDescription = CreateDescription(dParams, surveysEstablished)
        newLayer.description = layerDescription
        newLayer.visible = False
        newLayer.transparency = fillTransparency
        newLayer.showLabels = False

        # Add rating attribute field to geodatabase featureclass
        #
        desc = arcpy.Describe(inputShp)
        fields = desc.fields
        fieldList = [fld.name.upper() for fld in fields]

        if not dParams["ResultColumnName"].upper() in fieldList:
            addType, addWidth = dFieldTypes[dataType.upper()]
            resultColumn = dParams["ResultColumnName"]

        if bStatistics:
            dRatingAcres, wtdAcres, totalAcres = UpdateLayerwithStats(newLayer, dValues, dParams)


            if dataType.upper() in ['CHOICE', 'STRING', 'VTEXT', 'INTEGER']:
                PrintMsg(("-" * len(title)), 0)
                PrintMsg(" \n" + dParams["ResultColumnName"] + "| Percent| Acres")

                for rating, acres in sorted(dRatingAcres.items()):
                    if str(rating) == "None":
                        rating = "Not rated or not available"

                    pct = round((acres / totalAcres * 100.0), 1)

                    PrintMsg(str(rating) + "| " + str(pct) + "| " + str(round(acres, 2)), 0)

            elif dataType.upper() in ['FLOAT']:
                PrintMsg(("-" * len(title)), 0)
                wtdAvg = wtdAcres / totalAcres

                if not dParams["UnitsofMeasure"] is None:
                    PrintMsg("Weighted average: " + Number_Format(wtdAvg, int(dParams["ResultPrecision"]), True) + " " + dParams["UnitsofMeasure"] + " for " + Number_Format(totalAcres, 2, True) + " acres", 0)

                else:
                    PrintMsg("Weighted average: " + Number_Format(wtdAvg, int(dParams["ResultPrecision"]), True)  + " for " + Number_Format(totalAcres, 2, True) + " acres", 0)

        else:
            bUpdated = UpdateLayer(newLayer, dValues, dParams)

        # Update layer symbology using JSON dictionary. Only for ArcGIS Desktop 10.3 or later.
        if version >= 10.3:

            # Update layer symbology using JSON
            newLayer.updateLayerFromJSON(dLayerDefinition)


        # Try adding musym labels to each soil map and see how annoying that is
        bLabeled = AddLabels(newLayer, False)

        arcpy.mapping.AddLayerToGroup(df, grpLayer, newLayer, "BOTTOM")  # add soil map layer to group layer

        mapLayerFile = os.path.join(basePath, newLayer.name + ".lyr")
        arcpy.SaveToLayerFile_management(newLayer, mapLayerFile, "RELATIVE", "10.1")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ZoomToExtent(inputLayer):
    # Create layer description string
    try:

        # zoom to new layer extent
        #
        # Describing a map layer extent always returns coordinates in the data frame coordinate system
        try:
            # Only the original, input soil shapefile layer will be used to
            # define the mapscale and extent. The thematic maplayer will fail over to
            # the next section which will go ahead and set the labels to MUSYM, but
            # leave the soil map labels turned off.

            newExtent = arcpy.Describe(inputLayer.name).extent

            # Expand the extent by 10%
            xOffset = (newExtent.XMax - newExtent.XMin) * 0.05
            yOffset = (newExtent.YMax - newExtent.YMin) * 0.05
            newExtent.XMin = newExtent.XMin - xOffset
            newExtent.XMax = newExtent.XMax + xOffset
            newExtent.YMin = newExtent.YMin - yOffset
            newExtent.YMax = newExtent.YMax + yOffset

            df.extent = newExtent
            dfScale = df.scale
            #PrintMsg(" \nData frame scale is  1:" + Number_Format(df.scale, 0, True), 1)

        except:
            # Leave labels turned off for thematic map layers
            dfScale = 30000

        if dfScale <= 24000:
            inputLayer.showLabels = True

        else:
            inputLayer.showLabels = False

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False


## ===================================================================================
def AddLabels(inputLayer, bLabeled):
    # Set layer label properties to use MUSYM
    # Some layers we just want to set the label properties to use MUSYM, but
    # we don't want to display the labels.

    try:

        # Add mapunit symbol (MUSYM) labels
        if inputLayer.supports("LABELCLASSES"):
            labelCls = inputLayer.labelClasses[0]
            labelCls.expression = "[MUSYM]"

        if df.scale <= 24000 and bLabeled:
            inputLayer.showLabels = True
            drawOutlines = True #??

        else:
            inputLayer.showLabels = False

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def GetMetadata(outputFC):
    # Create layer description string
    try:
        arcpy.SynchronizeMetadata_conversion(outputFC)

        outputGDB = os.path.dirname(outputFC)
        fcName = os.path.basename(outputFC)
        mdTable = os.path.join(outputGDB, "GDB_Items")
        #wc = "UPPER(PhysicalName) = '" + fcName.upper() + "'"

        xmlMD = ""
        cnt = 0

        with arcpy.da.SearchCursor(mdTable, ["PhysicalName", "Documentation"]) as cur:
            for rec in cur:
                xmlMD = str(rec[0])
                cnt += 1
                PrintMsg("\t" + str(rec), 1)

        PrintMsg(" \nMetadata XML length for record " + str(cnt) + " : " + str(xmlMD), 1)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
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
def UpdateMetadata(outputWS, target, surveyInfo, description, dParams, dColumns):
    #
    # Used for featureclass and geodatabase metadata. Does not do individual tables
    # Reads and edits the original metadata object and then exports the edited version
    # back to the featureclass or database.
    #
    try:
        PrintMsg(" \nUpdating metadata for new featureclass...", 0)
        # Get update information for metadata
        dMetadata = MetadataDetails()

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ArcGIS2ISO19139.xml"
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        #prod = r"Metadata/Translator/ARCGIS2ISO19139gml321.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Define input and output XML files
        #mdExport = os.path.join(env.scratchFolder, "xxExport.xml")  # initial metadata exported from current MUPOLYGON featureclass
        mdExport = os.path.join(scriptPath, "WSS_ThematicMetadata.xml")
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        # Import the template metadata with the 'xx' keywords
        if not arcpy.Exists(mdExport):
            raise MyError, "XML file (" + mdExport + ") not found"

        arcpy.ImportMetadata_conversion(mdExport, "FROM_FGDC", target, "ENABLED")

        # Export metadata to an xml file that can be edited
        arcpy.ExportMetadata_conversion (target, mdTranslator, mdExport)

        # Cleanup XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        # Set date strings for metadata, based upon the date that WSS created the thematic map layers

        # Get WSS thematic map creation date for metdata
        mmddyyyy = dParams["CreationDateTime"].split(" ")[0]
        mm, dd, yyyy = mmddyyyy.split("/")
        if len(mm) < 2:
            mm = "0" + mm

        if len(dd) < 2:
            dd = "0" + dd

        creationDate = yyyy + "-" + mm + "-" + dd

        # Get today's date for use in ArcMap process step
        arcmapDate = datetime.date.today().isoformat().replace("-", "")

        # Get most recent survey area SAVEREST date from surveyInfo string
        surveyInfos = surveyInfo.split(";")
        lastSurvey = surveyInfos[-1]
        ssurgoDate1 = lastSurvey[lastSurvey.find("(") + 1: lastSurvey.find(")")].split()
        mm, dm, yyyy = ssurgoDate1[1].split("/")

        if len(mm) < 2:
            mm = "0" + mm

        if len(dd) < 2:
            dd = "0" + dd

        ssurgoDate = yyyy + "-" + mm + "-" + dd

        # Parse exported XML metadata file
        # Convert XML to tree format
        tree = ET.parse(mdExport)
        root = tree.getroot()

        # Title
        citeInfo = root.findall('idinfo/citation/citeinfo/')  # old

        if not citeInfo is None:
            # Process citation elements
            # title
            #
            # PrintMsg("citeInfo with " + str(len(citeInfo)) + " elements : " + str(citeInfo), 1)
            for child in citeInfo:
                #PrintMsg("\t\t" + str(child.tag), 0)
                if child.tag == "title":
                    newTitle = "WSS AOI " + os.path.basename(target)
                    #PrintMsg(" \nChanging " + child.tag + " from '" + child.text + "' to '" + newTitle + "'", 1)
                    child.text = newTitle
                    break

        # Abstract and Purpose
        citeInfo = root.findall('idinfo/descript/')  # old

        if not citeInfo is None:
            # Process citation elements
            # Abstract
            for child in citeInfo:
                #PrintMsg("\t\t" + str(child.tag), 0)
                if child.tag == "abstract":
                    if child.text.find('xxABSTRACTxx') >= 0:
                        child.text = dMetadata["abstract"] + creationDate  + ". This soils featureclass includes parts of the following soil survey areas: " + surveyInfo

                if child.tag == "purpose":
                    if child.text.find('xxPURPOSExx') >= 0:
                        child.text = dMetadata["purpose"]

        # Update limitations
        limitations = root.findall('idinfo/useconst')

        if not limitations is None:
            #PrintMsg("\t\tlimitations")

            for limitation in limitations:
                if limitation.text == "xxLIMITATIONSxx":
                    limitation.text = dMetadata["limitations"]

        # Update credits
        credits = root.findall('idinfo/datacred')
        if not credits is None:
            for credit in credits:
                if credit.text == "xxCREDITSxx":
                    #PrintMsg("\t\tcredits")
                    credit.text = dMetadata["credits"] + ", " + dParams["User"]

        # Update process steps
        processes = root.findall('dataqual/lineage/procstep')

        if not processes is None:

            lastText = ""

            for procstep in processes:
                for child in procstep:
                    #PrintMsg("\t\t" + str(child.tag), 0)
                    if child.tag == "procdesc" and child.text == "xxSSURGOxx":
                        lastTxt = child.text
                        child.text = dMetadata["ssurgo"]

                    if child.tag == "procdesc" and child.text == "xxWSSAOIxx":
                        lastTxt = child.text
                        child.text = dMetadata["wss"]

                    if child.tag == "procdesc" and child.text == "xxARCMAPxx":
                        lastTxt = child.text
                        child.text = dMetadata["arcmap"]

                    if child.tag == "procdate":
                        #PrintMsg("\t\t" + lastTxt, 0)

                        if lastTxt == "xxSSURGOxx":
                            #PrintMsg("\nGet date: " + lastTxt)
                            child.text = ssurgoDate

                        elif lastTxt == "xxWSSAOIxx":
                            #PrintMsg("\nGet date: " + lastTxt)
                            child.text = creationDate

                        elif lastTxt == "xxARCMAPxx":
                            #PrintMsg("\nGet date: " + lastTxt)
                            child.text = arcmapDate

        # Update legal
        distInfo = root.findall('distinfo/distliab')
        #PrintMsg("\t\tcredits", 0)

        if not distInfo is None:

            for child in distInfo:
                child.text = dMetadata["legal"]
                break

        # Update table column descriptions
        # PROBLEM! I am now using the static metadata file which does not include the new columns
        columns = root.findall('eainfo/detailed/attr')

        if not columns is None:
            lastColumn = ""

            for attr in columns:
                for child in attr:

                    if child.tag == "attrlabl":
                        #PrintMsg("\t\tMetadata column: " + str(child.text), 0)

                        if child.text in dColumns:
                            lastColumn = child.text
                            colDef = dColumns[child.text]
                            #PrintMsg("\t\tMatch found " + str(child.tag), 0)

                            childDef = ET.XML("<attrdef>" + colDef+ "</attrdef>")
                            childDef.attrib = {}
                            attr.append(childDef)


        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")


        # delete the temporary xml metadata files
        if os.path.isfile(mdImport):
            os.remove(mdImport)
            #pass

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        return True


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def UpdateMetadata_WorksMostly(outputWS, target, surveyInfo, description, remove_gp_history_xslt, dParams):
    #
    # Used for featureclass and geodatabase metadata. Does not do individual tables
    # Reads and edits the original metadata object and then exports the edited version
    # back to the featureclass or database.
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


        # Gather new metadata information into a dictionary
        # dictionary key will be namespace key and value will be text
        dMetadata = dict()


        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        #prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        prod = r"Metadata/Translator/ARCGIS2ISO19139.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Define input and output XML files
        mdExport = os.path.join(env.scratchFolder, "xxExport.xml")  # initial metadata exported from current MUPOLYGON featureclass
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info
        out_xml = os.path.join(env.scratchFolder, "xxClean.xml")

        # Cleanup XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        if os.path.isfile(mdExport):
            os.remove(mdExport)

        # Clear this geoprocessing history from the target metadata

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        arcpy.XSLTransform_conversion(target, remove_gp_history_xslt, out_xml, "")
        arcpy.MetadataImporter_conversion(out_xml, target)

        # delete the temporary xml metadata files
        if os.path.isfile(mdImport):
            #os.remove(mdImport)
            pass

        if os.path.isfile(mdExport):
            #os.remove(mdExport)
            pass
            PrintMsg(" \nKeeping temporary medatafiles: " + mdExport, 1)
            #time.sleep(5)

        if arcpy.Exists(out_xml):
            arcpy.Delete_management(out_xml)

        # Get creation date for metdata
        mmddyyyy = dParams["CreationDateTime"].split(" ")[0]
        mm, dd, yyyy = mmddyyyy.split("/")
        if len(mm) < 2:
            mm = "0" + mm

        if len(dd) < 2:
            dd = "0" + dd

        creationDate = yyyy + "-" + mm + "-" + dd

        # Get abstract text for metadata
        abstractText = 'Web Soil Survey thematic map data created ' + creationDate + ' using SSURGO data from the following soil survey areas: ' + surveyInfo +"."
        abstractText = abstractText + " \r\nThe following soil map layers were generated from this data: " + ", ".join(dMaps.keys())
        purposeText = "Web Soil Survey thematic map featureclass using SSURGO soil polygon data"

        arcpy.ExportMetadata_conversion (target, mdTranslator, mdExport)

        # Parse exported XML metadata file
        #
        # Convert XML to tree format
        tree = ET.parse(mdExport)
        root = tree.getroot()

        #    PrintMsg("\t" + child.tag + ": " + str(child.attrib), 1)

        dNS = dict()
        dNS[""] = "http://www.isotc211.org/2005/gmd"
        dNS["gco"] = "http://www.isotc211.org/2005/gco"
        dNS["gts"] = "http://www.isotc211.org/2005/gts"
        dNS["srv"] = "http://www.isotc211.org/2005/srv"
        dNS["gml"] = "http://www.opengis.net/gml"
        dNS["xlink"] = "http://www.w3.org/1999/xlink"

        mdItems = ["dateStamp", "identificationInfo", "distributionInfo"]
        #mdItems = ["title", "Date"]
        #mdItems = ["skip"]  # using this to skip the following process steps.
        #mdItems = ["title", "Date", "language", "characterSet", "hierarchyLevel", "hierarchyLevelName", "dateStamp", "identificationInfo", "distributionInfo"]

        for prefix, uri in dNS.items():
            ET.register_namespace(prefix, uri)

        nsKey0 = ""
        ns = dNS[nsKey0]
        ns2 = "{" + ns + "}"
        PrintMsg(" \nSearching namespace: " + ns, 1)

        for md in mdItems:
            src = ns2 + md

            for item in root.findall(src):
                PrintMsg(" \n\tNamespace key: " + md, 1)

                for child0 in item:
                    if child0.tag.startswith("{"):
                        # this is the beginning of another namespace...
                        child0NS = child0.tag[(1 + child0.tag.find("}")):]
                        nsKey1 = child0.tag[(child0.tag.rfind("/") + 1):child0.tag.rfind("}")]

                        if child0.text.strip() == "":
                            PrintMsg("\t\tChild0 with namespace - " + nsKey1 + ":" + child0NS, 1)

                            # Try to get next level below
                            level = 0
                            keyLevel = 0

                            for child1 in child0:
                                child1NS = child1.tag[(1 + child1.tag.find("}")):]
                                nsKey2 = child1.tag[(child1.tag.rfind("/") + 1):child1.tag.rfind("}")]
                                keyNS = nsKey2  + ":" + child1NS
                                PrintMsg("\t\t\tChild1: " + nsKey2  + ":" + child1NS + " " + str(child1.text).strip(), 1)

                                if keyNS == "gmd:abstract" and level == 0:
                                    child1.attrib = {}
                                    child1.text = abstractText
                                    childPurpose = ET.XML("<purpose>" + purposeText + "</purpose>")
                                    childPurpose.attrib = {}
                                    child0.insert((level + 1), childPurpose)
                                    PrintMsg(" \n\t\t\tAdded Purpose child to " + child0.tag + " at level " + str(level + 1), 1)
                                    level += 1

                                if keyNS == "gmd:abstract" and level == 1:
                                    #child1.attrib = {}
                                    #child1.text = abstractText
                                    childCredit = ET.XML("<credit>" + dParams["User"] + "</credit>")
                                    childCredit.attrib = {}
                                    child0.insert((level + 1), childCredit)
                                    PrintMsg(" \n\t\t\tAdded Credit child to " + child0.tag + " at level " + str(level + 1), 1)
                                    level += 1

                                if keyNS == "gmd:descriptiveKeywords" and keyLevel == 0:
                                    keyLevel += 1
                                    keyTree = deepcopy(child1)
                                    #childKey.text = "SSURGO"
                                    for keyElem in keyTree:

                                        child0.append(childKey)


                                if len(child1) > 0:
                                    for child2 in child1:
                                        child2NS = child2.tag[(1 + child2.tag.find("}")):]
                                        nsKey3 = child2.tag[(child2.tag.rfind("/") + 1):child2.tag.rfind("}")]
                                        PrintMsg("\t\t\t\tChild2: " + nsKey3  + ":" + child2NS + " " + str(child2.text).strip(), 1)

                                        dItems = child2.attrib

                                        if len(dItems) > 0:
                                            for key, val in dItems.items():
                                                PrintMsg("\t\t\t\t\tChild2 attributes: " + key + ": " + str(val), 1)


                                    if len(child2) > 0:
                                        for child3 in child2:
                                            child3NS = child3.tag[(1 + child3.tag.find("}")):]
                                            nsKey4 = child3.tag[(child3.tag.rfind("/") + 1):child3.tag.rfind("}")]
                                            PrintMsg("\t\t\t\t\tChild3: " + nsKey4  + ":" + child3NS + " " + str(child3.text).strip(), 1)

                                            dItems = child3.attrib

                                            if len(dItems) > 0:
                                                for key, val in dItems.items():
                                                    #PrintMsg("\t\t\t\t\t\tChild3 attributes: " + key + ": " + str(val), 1)
                                                    # See if I can break down the attribute key
                                                    keyNS = key[(key.rfind("/") + 1):key.rfind("}")] + ":" + key[(1 + key.find("}")):]
                                                    PrintMsg("\t\t\t\t\t\tChild3 attributes: " + keyNS + ": " + str(val), 1)
                                                    if keyNS == "gco:nilReason":
                                                        child3.attrib = {}

                                            if nsKey4 + ":" + child3NS == "gmd:date":
                                                child3.text = creationDate



                                            if len(child3) > 0:
                                                for child4 in child3:
                                                    child4NS = child4.tag[(1 + child4.tag.find("}")):]
                                                    nsKey5 = child4.tag[(child4.tag.rfind("/") + 1):child4.tag.rfind("}")]
                                                    PrintMsg("\t\t\t\t\t\tChild4: " + nsKey5  + ":" + child4NS + " " + str(child4.text).strip(), 1)

                                                    if child3.tag.endswith("title") and nsKey5 + ":" + child4NS == "gco:CharacterString":
                                                        #PrintMsg("\nSearching child3.tag (" + child3.tag + ") for title", 0 )
                                                        title = child4.text + " - WSS Thematic Data"
                                                        child4.text = title


                                                    dItems = child4.attrib

                                                    if len(dItems) > 0:
                                                        for key, val in dItems.items():
                                                            PrintMsg("\t\t\t\t\t\t\tChild4 attributes: " + key + ": " + str(val), 1)


                                #raise MyError, "EARLY OUT"


                        else:
                            PrintMsg("\t\tChild0 with namespace - " + nsKey1 + ":" + child0NS + " = '" + child0.text + "'", 1)

                    else:
                        PrintMsg("\t\tChild0: " + child0.tag + ": " + str(child0.text), 1)


                    dItems = child0.attrib

                    if len(dItems) > 0:
                        for key, val in dItems.items():
                            PrintMsg("\t\t\tChild0 attributes: " + key + ": " + str(val), 1)


        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, method="xml")

        # 1. import updated metadata to the geodatabase table
        arcpy.ImportMetadata_conversion(mdImport, "FROM_ISO_19139", target, "DISABLED")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, json, csv,  urllib2, httplib
from arcpy import env
from copy import deepcopy
import xml.etree.cElementTree as ET

try:
    # Read input parameters
    inputShp = arcpy.GetParameterAsText(0)                   # input soil_mu_aoi layer. Will not handle multiple layers with same name
    mapLayers = arcpy.GetParameter(1)                        # list of selected soil maps from the thematic folder
    outputFolder = arcpy.GetParameterAsText(2)               # folder location for output geodatabase
    drawOutlines = arcpy.GetParameter(3)                     # boolean to draw polygon outlines
    fillTransparency = arcpy.GetParameter(4)                 # percent transparency (integer, convert to 255 as opaque)
    bStatistics = arcpy.GetParameter(5)                      # boolean, generate layer statistics
    bTabular = arcpy.GetParameter(6)                         # boolean, convert shapefiles and tabular data to gSSURGO database

    scriptPath = os.path.dirname(sys.argv[0])

    env.overwriteOutput= True
    installInfo = arcpy.GetInstallInfo()
    version = installInfo["Version"][0:4]                
    sdaURL = r"https://sdmdataaccess.sc.egov.usda.gov"
    
    if not SetScratch():
        raise MyError, "Unable to set scratch workspace"

    # Get data folders from input layer
    # probably should validate the inputShp as soil polygon
    desc = arcpy.Describe(inputShp)
    spatialFolder = os.path.dirname(desc.catalogPath)  # spatial folder
    sr = desc.spatialReference
    projType = sr.type
    basePath = os.path.dirname(spatialFolder)
    thematicPath = os.path.join(basePath, "thematic")
    remove_gp_history_xslt = os.path.join(scriptPath, "remove geoprocessing history.xslt")

    if os.path.basename(basePath).startswith("wss_aoi_"):
        # this is an original WSS AOI dataset folder
        fcID = os.path.basename(basePath)[8:]

    else:
        fcID = ""

    # Make sure that the 'thematic' folder exists.
    if not arcpy.Exists(thematicPath):
        # make sure the thematic folder exists.
        raise MyError, "Thematic data path " + thematicPath + " does not exist"

    PrintMsg(" \nCreating WSS thematic maps for " + os.path.basename(basePath), 0)

    # Create arcpy.mapping objects. Duplicate layer names will cause a problem here.
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame
    inputLayer = arcpy.mapping.ListLayers(mxd, inputShp, df)[0]

    # Read summary.txt to create a dictionary containing map layer names (item values)
    # and map ids (item keys)
    dMaps = ReadSummary(os.path.join(thematicPath, "summary.txt"), mapLayers)

    # Create sorted list of map ids to iterate by
    mapList = list()

    #for mapID in sorted(dMaps.values()):
    for mapName, mapID in sorted(dMaps.items()):
        #PrintMsg(" \nAdding new layer " + mapName + " to mapList...", 1)
        mapList.append(mapID)

    # Get SQL Server to ArcGIS field mapping
    dFieldTypes = FieldTypes()

    # Get dictionary of units of measure abbreviations
    dUnits = Units()

    gdbName =  arcpy.ValidateTableName( "WSS_ThematicMaps_" + fcID) + ".gdb"
    outputGDB = os.path.join(outputFolder, gdbName)
    outputFC = os.path.join(outputGDB, "MUPOLYGON")

    if bTabular:
        # Create a gSSURGO-styled geodatabase, importing all tabular and spatial data
        desc = arcpy.Describe(inputShp)
        inputFolder = os.path.dirname(os.path.dirname(desc.catalogPath))
        aliasName = os.path.basename(inputFolder)[8:]
        AOI = "World"
        useTextFiles = True
        import WSSThematic_gSSURGO
        bGood = WSSThematic_gSSURGO.gSSURGO(inputFolder, outputGDB, AOI, aliasName, useTextFiles)

    else:
        # Create a simple file geodatabase and import just the soil polygon shapefile

        if not arcpy.Exists(outputGDB):
            arcpy.CreateFileGDB_management(os.path.dirname(outputGDB), os.path.basename(outputGDB), "CURRENT")

        if arcpy.Exists(outputFC):
            arcpy.Delete_management(outputFC)




    # Seem to be having problems copying polygons when 0 are selected
    # Try switching selection (unless there already is one)
    iSel = int(arcpy.GetCount_management(inputShp).getOutput(0))

    if iSel == 0:
        arcpy.SelectLayerByAttribute_management(inputShp, "SWITCH_SELECTION")

    if bTabular:
        # Add fields to MUPOLYGON featureclass
        fieldList = [fld.name.upper() for fld in arcpy.Describe(outputFC).fields]
        if not "NATMUSYM" in fieldList:
            arcpy.AddField_management(outputFC, "NATMUSYM", "TEXT", "", "", 6)

        if not "MUNAME" in fieldList:
            arcpy.AddField_management(outputFC, "MUNAME", "TEXT", "", "", 240)

        if not "ACRES" in fieldList:
            arcpy.AddField_management(outputFC, "ACRES", "DOUBLE")


    else:
        # Add fields to original soilmu shapefile. Doing this to ensure the best field order in the output featureclass
        fieldList = [fld.name.upper() for fld in desc.fields]

        if not "NATMUSYM" in fieldList:
            arcpy.AddField_management(inputShp, "NATMUSYM", "TEXT", "", "", 6)

        if not "MUNAME" in fieldList:
            arcpy.AddField_management(inputShp, "MUNAME", "TEXT", "", "", 240)

        if not "ACRES" in fieldList:
            arcpy.AddField_management(inputShp, "ACRES", "DOUBLE")

        arcpy.CopyFeatures_management(inputShp, outputFC)  # Seeing some issues with CopyFeatures. ObjectID is labeled FID and is out-of-order
        arcpy.AlterField_management(outputFC, "OBJECTID", "#", "OBJECTID", "#", 4, "NON_NULLABLE", False)
        arcpy.AlterAliasName(outputFC, "Soils - " + fcID)

    if iSel == 0:
        arcpy.SelectLayerByAttribute_management(inputShp, "CLEAR_SELECTION")



    description, surveyInfo = GetMapunitInformation(outputFC)

    # Initialize list of rating column names and column definitions. Not sure what this is being used for
    #
    dColumns = {"Acres":"acres calculated using geodesic area method", "natmusm":"The symbol used to uniquely identify the soil mapunit nationally.  The value is generated by NASIS, and is the based on the muiid from the Mapunit table, expressed in base 36.  It is a combination of numeric and lowercase alphabetic characters."}

    # Initialize dictionary with parameters for each map
    dMapInfo = dict()

    # Get list of field that already exist in the input shapefile
    desc = arcpy.Describe(inputShp)
    fields = desc.fields
    fieldList = [fld.name.upper() for fld in fields]

    for mapID in mapList:
        # for each soil map:
        #    save the rating column name and description
        #    save all other SDV map information
        paramsFile = os.path.join(thematicPath, "parameters" + str(mapID) + ".txt")
        dParams = ReadParameters(paramsFile)

        if len(dParams) == 0:
            raise MyError, ""

        dMapInfo[mapID] = dParams

        if not dParams["UnitsofMeasure"] is None:
            dColumns[dParams["ResultColumnName"]] = str(dParams["SdvAttributeName"]) + " (" + str(dParams["UnitsofMeasure"]) + ")"  # save rating column info for metadata (has units)

        else:
            dColumns[dParams["ResultColumnName"]] = str(dParams["SdvAttributeName"])  # save rating column info for metadata (no units)

        # Add rating attribute field to geodatabase featureclass unless it already exists
        #
        if not dParams["ResultColumnName"].upper() in fieldList:
            dataType = dParams["ResultDataType"]
            addType, addWidth = dFieldTypes[dataType.upper()]
            resultColumn = dParams["ResultColumnName"]

            #PrintMsg(" \nAdding new column " + resultColumn + " to output featureclass...", 1)
            arcpy.AddField_management(outputFC, resultColumn, addType, "", "", addWidth)

        else:
            PrintMsg(" \nColumn " + resultColumn + " already exists in output featureclass...", 1)




    #description = "SSURGO data from WSS AOI download"

    # get creation date from last map and use it to populate featureclass metadata
    mapID = sorted(dMaps.values())[-1]
    dParams = dMapInfo[mapID]

    # Update featureclass metadata
    # Clear geoprocessing history for output featureclass
    bClear = ClearHistory(outputFC, remove_gp_history_xslt)

    if not bTabular:
        bMetadata = UpdateMetadata(outputGDB, outputFC, surveyInfo, description, dParams, dColumns)

    # Create map layer object from inputShp and turn off labels so that the rest of the new map layers
    # aren't all showing labels

    # Create layer file from input shapefile, need to have labels turned off at this point
    # or the setting will be propogated to all the new soil map layers.
    wssLayerFile = os.path.join(env.scratchFolder, "wss_thematicmap.lyr")
    arcpy.SaveToLayerFile_management(inputShp, wssLayerFile, "ABSOLUTE", 10.1)
    baseLayer = arcpy.mapping.Layer(wssLayerFile)

    # Replace layer file data source with the outputFC
    baseLayer.replaceDataSource(os.path.dirname(outputFC), "FILEGDB_WORKSPACE", os.path.basename(outputFC))
    arcpy.SaveToLayerFile_management(baseLayer, wssLayerFile, "ABSOLUTE", 10.1)

    # Create group layer for organizing individual soil maps under
    grpLayerName = "WSS Thematic Soil Maps - " + fcID
    grpLayer = CreateGroupLayer(grpLayerName)

    # Define new output group layer file (.lyr) to permanently save all map layers to
    grpFile = os.path.join(basePath, grpLayer.name) + ".lyr"

    # Create first soil map layer (lines and labels, no fill).
    bMapped = AddFirstSoilMap(outputFC, description, surveyInfo)

    for mapID in mapList:
        # for each soil map:
        #    read the rating file, parameter file and legend file into dictionaries
        #    create output table
        #    dump sorted dictionary contents into output table
        #    read appropriate JSON file into layerDefinition dictionary
        #    update layerDefinition dictionary using other dictionaries

        #paramsFile = os.path.join(thematicPath, "parameters" + str(mapID) + ".txt")
        #dParams = ReadParameters(paramsFile)

        dParams = dMapInfo[mapID]
        bMapped = AddSoilMap(mapID, surveyInfo, dParams)  # Add each thematic map layer to ArcMap

    if bMapped == False:
        raise MyError, "Failed to map " + str(mapID)

    # Clear geoprocessing history for output featureclass
    # bClear = ClearHistory(outputFC, remove_gp_history_xslt)


    # Update featureclass metadata including column definitions. Why is this update causing the map layer to delete?
    # bMetadata = UpdateMetadata(outputGDB, outputFC, surveyInfo, description, dParams, dColumns)


    grpLayer.visible = True
    inputLayer.visible = False
    arcpy.SaveToLayerFile_management(grpLayer, grpFile)
    #PrintMsg(" \nSaved group layer to " + grpFile, 0)
    bZoomed = ZoomToExtent(inputLayer)
    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

    PrintMsg(" \nFinished creating thematic soil map layers \n ", 0)
    #PrintMsg(" \nOutput featureclass: " + outputFC, 0)
    del mxd


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
