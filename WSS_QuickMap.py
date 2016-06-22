# WSS_QuickMap.py
#
# Reads a WSS download dataset and creates the selected soil maps
#
# 05-03-2016
#
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
def FieldTypes():
    # Create dictionary containing datatype conversions
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
def ClassBreaksJSON(legendList):
    # returns JSON string for classified break values template. Use this for numeric data.
    # need to set:
    # d.minValue as a number
    # d.classBreakInfos which is a list containing at least two slightly different dictionaries.
    # The last one contains an additional classMinValue item
    #
    # d.classBreakInfos[0]:
    #    classMaxValue: 1000
    #    symbol: {u'color': [236, 252, 204, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 10 to 1000
    #    label: 10.0 - 1000.000000

    # d.classBreakInfos[n - 1]:  # where n = number of breaks
    #    classMaxValue: 10000
    #    classMinValue: 8000
    #    symbol: {u'color': [255, 255, 0, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 1000 to 5000
    #    label: 8000.000001 - 10000.000000
    #
    # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges



    try:
        #d = dict()
        jsonString = """
{"type" : "classBreaks",
  "field" : "",
  "classificationMethod" : "esriClassifyManual",
  "defaultLabel": "Not rated or not available",
  "defaultSymbol": {
    "type": "esriSFS",
    "style": "esriSFSSolid",
    "color": [110,110,110,255],
    "outline": {
      "type": "esriSLS",
      "style": "esriSLSSolid",
      "color": [110,110,110,255],
      "width": 0.5
    }
  },
  "minValue" : 0.0,
  "classBreakInfos" : [
  ]
}"""


        d = json.loads(jsonString)
        # hexVal = "#FFFF00"drawingInfo" : {"renderer" :
        # h = hexVal.lstrip('#')
        # rgb = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))

        #PrintMsg(" \nTesting JSON string values in dictionary: " + str(d["currentVersion"]), 1)

        d["field"]  = dParams["ResultColumnName"]
        d["drawingInfo"] = dict() # new

        # Find minimum value by reading dRatings
        minValue = 999999999
        for rating in dValues.values():
            try:
                ratingValue = float(rating)
                #PrintMsg("\tRating (float): " + str(ratingValue), 1)

                if rating is not None and ratingValue < minValue:
                    minValue = float(rating)
            except:
                pass

        # Add new rating field to list of layer fields
        d["field"] = dParams["ResultColumnName"]
        d["minValue"] = minValue

        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()
        #PrintMsg(" \nlegendList: " + str(legendList), 1)
        PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        lastMax = minValue

        if cntLegend > 1:

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                rating, label, hexCode = legendList[cnt]
                if not rating is None:
                    PrintMsg(" \n\t\tAdding legend values: " + str(lastMax) + "-> " + str(rating) + ", " + str(label), 1)
                    ratingValue = float(rating)
                    # calculate rgb colors
                    rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    rgb.append(255)  # transparency hardcoded for now
                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = lastMax
                    dLegend["classMaxValue"] = ratingValue
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = [110,110,110,255]
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    classBreakInfos.append(dLegend)
                    #classBreakInfos.append(dLegend)
                    lastMax = ratingValue

                    cnt += 1

                else:
                    # Skipping null values
                    break


            #cnt = len(legendList) - 1
            #lastMax = ratingValue # previous legend item's max value
            # last legend item has both a minimum and maximum value

            #rating, label, hexCode = legendList[cnt] # skip for a test

            if 1 == 2: # skip this for a test
            #if not rating is None and not rating == "":
                try:
                    #PrintMsg(" \nLegend values: " + str(rating) + ", " + str(label) + ", " + str(rgb), 1)
                    ratingValue = float(rating)
                    # calculate rgb colors
                    rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    rgb.append(255)  # transparency hardcoded for now


                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = lastMax
                    dLegend["classMaxValue"] = ratingValue
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = [110,110,110,255]
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    classBreakInfos.append(dLegend)
                    PrintMsg(" \n\t\tAdding final legend value: " + str(ratingValue) + ", " + str(label) + ", " + str(rgb), 1)

                except:
                    errorMsg()

        d["classBreakInfos"] = classBreakInfos

        PrintMsg(" \n1. dLayerDefinition: " + '"' + str(d) + '"', 0)

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return d

    except:
        errorMsg()
        return d

## ===================================================================================
def UniqueValuesJSON(legendList):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    try:
        d = dict()

        jsonString = """
{
  "currentVersion" : 10.01,
  "id" : 0,
  "name" : "Soil Map",
  "type" : "Feature Layer",
  "description" : "",
  "definitionExpression" : "",
  "geometryType" : "esriGeometryPolygon",
  "parentLayer" : null,
  "subLayers" : [],
  "minScale" : 0,
  "maxScale" : 0,
  "defaultVisibility" : true,
  "hasAttachments" : false,
  "htmlPopupType" : "esriServerHTMLPopupTypeNone",
  "drawingInfo" : {"renderer" :
    {
      "type" : "uniqueValue",
      "field1" : null,
      "field2" : null,
      "field3" : null,
      "fieldDelimiter" : ", ",
      "defaultSymbol" : null,
      "defaultLabel" : "All other values",
      "uniqueValueInfos" : []
    },
    "transparency" : 0,
    "labelingInfo" : null},
  "displayField" : null,
  "fields" : [
    {
      "name" : "FID",
      "type" : "esriFieldTypeOID",
      "alias" : "FID"},
    {
      "name" : "Shape",
      "type" : "esriFieldTypeGeometry",
      "alias" : "Shape"},
    {
      "name" : "AREASYMBOL",
      "type" : "esriFieldTypeString",
      "alias" : "AREASYMBOL",
      "length" : 20},
    {
      "name" : "SPATIALVER",
      "type" : "esriFieldTypeInteger",
      "alias" : "SPATIALVER"},
    {
      "name" : "MUSYM",
      "type" : "esriFieldTypeString",
      "alias" : "MUSYM",
      "length" : 6},
    {
      "name" : "MUKEY",
      "type" : "esriFieldTypeString",
      "alias" : "MUKEY",
      "length" : 30}
  ],
  "typeIdField" : null,
  "types" : null,
  "relationships" : [],
  "capabilities" : "Map,Query,Data"
}"""

        d = json.loads(jsonString)

        d["currentVersion"] = 10.01
        d["id"] = 1
        d["name"] = dParams["SdvAttributeName"]
        d["description"] = "Web Soil Survey Thematic Map"
        d["definitionExpression"] = ""
        d["geometryType"] = "esriGeometryPolygon"
        d["parentLayer"] = None
        d["subLayers"] = []
        d["defaultVisibility"] = True
        d["hasAttachments"] = False
        d["htmlPopupType"] = "esriServerHTMLPopupTypeNone"
        d["drawingInfo"]["renderer"]["type"] = "uniqueValue"
        d["drawingInfo"]["renderer"]["field1"] = dParams["ResultColumnName"]
        d["displayField"] = dParams["ResultColumnName"]
        PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)

        # Add new rating field to list of layer fields
        dAtt = dict()
        dAtt["name"] = dParams["ResultColumnName"]
        dAtt["alias"] = dParams["ResultColumnName"]
        dAtt["type"] = "esriFieldTypeString"
        d["fields"].append(dAtt)

        try:
            length = dFieldTypes["ResultDataType"].upper()[1]

        except:
            length = 254
        dAtt["length"] = length


        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        for cnt in range(0, len(legendList)):
            dSymbol = dict()
            rating, label, hexCode = legendList[cnt]
            #PrintMsg(" \tAdding to legend: " + label + "; " + rating + "; " + hexCode, 1)
            # calculate rgb colors
            rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            rgb.append(255)  # transparency hardcoded for now
            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": [110, 110, 110, 255], "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}

            #
            legendItems = dict()
            legendItems["value"] = rating

            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
            #dValue = {"value" : rating}

            if not dParams["UnitsofMeasure"] is None:
                #dLabel = {"label" : label + " " + dParams["UnitsofMeasure"]}
                legendItems["label"] = label + " " + dParams["UnitsofMeasure"]

            else:
                #dLabel = {"label" : label}
                legendItems["label"] = label

            legendItems["symbol"] = symbol
            #d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : dParams["ResultColumnName"], "field2" : None, "field3" : None, "defaultSymbol" : None, "defaultLabel" : "All other values"}
            d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : dParams["ResultColumnName"], "field2" : None, "field3" : None}
            uniqueValueInfos.append(legendItems)

        d["drawingInfo"]["renderer"]["uniqueValueInfos"] = uniqueValueInfos
        #PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)
        #PrintMsg(" \nuniqueValueInfos: " + str(d["drawingInfo"]["renderer"]["uniqueValueInfos"]), 1)



        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return d

    except:
        errorMsg()
        return d

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
        dMaps = dict()

        if not arcpy.Exists(summaryFile):
            raise MyError, "Missing " + summaryFile

        # skip any that aren't in the mapLayers list
        fh = open(summaryFile, "r")

        for rec in fh:
            sData = rec.split(":")

            if sData[0].startswith("ID "):
                # this is the mapID data
                mapID = int(sData[0].split(" ")[1])
                mapName = sData[1].strip()

                if mapName in mapLayers:
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

        fh = open(paramsFile, "r")
        rec = fh.readline()

        while rec:

            delim = rec.find(":")
            key = rec[0:delim].strip()

            if not key is None:
                val = rec[delim + 1:].strip()
                if val == '""':
                    val = None

                if type(val) == str:
                    val = val[1:-1] # get rid of double quotes

                if key == "SdvAttributeDescription":
                    # continue reading into the current value
                    while rec:
                        rec = fh.readline()
                        val = val + "\n" + rec

                    dParams[key] = val
                    #PrintMsg(" \n" + key, 1)
                    break  # assuming this is the last attribute in the file

                dParams[key] = val
                #PrintMsg(" \n" + key, 1)

            rec = fh.readline()

        fh.close()

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
def CreateTable(tblName, ratingFile, dataType, mapID):
    # NOT USING THIS FUNCTION ANYMORE
    #
    # create output table and read the rating file into it
    # header: MapUnitKey, MapUnitRatingString, MapUnitRatingNumeric, RgbString
    # SDV dataTypes: 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'

    try:
        #for key, val in dFieldTypes.items():
        #    PrintMsg(" \t" + key + ": " + val[0] + ", " + str(val[1]), 1)

        tblName = dParams["SdvAttributeName"].replace(" ", "_").replace(",","").replace("(","").replace(")", "") + str(mapID)
        outputTbl = os.path.join(env.scratchGDB, tblName)
        arcpy.CreateTable_management(env.scratchGDB, tblName)
        arcpy.AddField_management(outputTbl, "MUKEY", "TEXT", "", "", 30)
        addType, addWidth = dFieldTypes[dataType]
        arcpy.AddField_management(outputTbl, dParams["ResultColumnName"], addType, "", "", addWidth)
        arcpy.AddField_management(outputTbl, "RGBCOLOR", "TEXT", "", "", 7)
        return outputTbl

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputTbl

    except:
        errorMsg()
        return outputTbl


## ===================================================================================
def CreateGroupLayer():
    # create output table and read the rating file into it
    # header: MapUnitKey, MapUnitRatingString, MapUnitRatingNumeric, RgbString
    # SDV dataTypes: 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'
    #
    # Probably need to use csv reader for this

    try:
        # Use template lyr file stored in current script directory to create new Group Layer
        # This SDVGroupLayer.lyr file must be part of the install package along with
        # any used for symbology. The name property will be changed later.
        grpLayerFile = os.path.join(os.path.dirname(sys.argv[0]), "SDV_GroupLayer.lyr")

        if not arcpy.Exists(grpLayerFile):
            raise MyError, "Missing group layer file (" + grpLayerFile + ")"

        grpLayerName = "WSS Thematic Soil Maps"
        testLayers = arcpy.mapping.ListLayers(mxd, grpLayerName, df)

        if len(testLayers) > 0:
            # If it exists, remove an existing group layer from previous run
            grpLayer = testLayers[0]
            #PrintMsg(" \nRemoving old group layer", 1)
            arcpy.mapping.RemoveLayer(df, grpLayer)


        grpLayer = arcpy.mapping.Layer(grpLayerFile)
        grpLayer.visible = False
        grpLayer.name = grpLayerName
        grpLayer.description = "Group layer containing individual WSS thematic soil map layers described in " + thematicPath
        arcpy.mapping.AddLayer(df, grpLayer, "TOP")
        grpLayer = arcpy.mapping.ListLayers(mxd, grpLayerName, df)[0]
        grpDesc = arcpy.Describe(grpLayer)

        if grpDesc.dataType.lower() != "grouplayer":
            raise MyError, "Problem with group layer"

        PrintMsg(" \nAdding group layer: " + str(grpLayer.name), 0)

        return grpLayer

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
# def ReadRatings(ratingFile, outputTbl, dataType):
def ReadRatings(ratingFile, dataType):
    # create output table and read the rating file into it
    # header: MapUnitKey, MapUnitRatingString, MapUnitRatingNumeric, RgbString
    # SDV dataTypes: 'CHOICE', 'FLOAT','INTEGER', 'STRING', 'VTEXT'
    #
    # Probably need to use csv reader for this

    try:
        dRatings = dict()  # hexcode, rating
        dValues = dict()  # mukey, rating

        if arcpy.Exists(ratingFile):
            #PrintMsg(" \nReading data from: " + ratingFile, 1)
            pass

        else:
            raise MyError, "Missing " + paramsFile

        #csv.field_size_limit(128000)
        csv.QUOTE_NONNUMERIC

        codePage = 'iso-8859-1'

        if dataType in ("FLOAT", "INTEGER"):
            # read the 0, 2, 3 columns from the rating.csv file
            PrintMsg(" \nData Type: " + dataType, 1)
            iPop = 1 # cols = [0, 2, 3]

        else:
            #PrintMsg(" \nData Type: " + dataType.upper() + " with a length of " + str(dFieldTypes[dataType.upper()][1]) + " characters", 1)
            iPop = 2 # cols = [0, 1, 3]

        #PrintMsg(" \n" + " If statement: " + str(dFieldTypes[dataType.upper()][0]), 1)

        # hardcoded field lengths used to truncate rating value if it is too long to fit in the table
        if dFieldTypes[dataType.upper()][0] == "TEXT":
            # Set field length for string-rating to actual field width because the value may not fit
            fldLengths = [30, dFieldTypes[dataType.upper()][1], 8]  # mukey, rating, hexcode
            #PrintMsg(" \nData Type: " + dataType + " with a length of " + str(dFieldTypes[dataType.upper()][1]) + " characters", 1)

            # Open output table for string data
            iRow = 0  # record counter. Skip first dummy record
            for rowInFile in csv.reader(open(ratingFile, 'r'), delimiter=',', quotechar='"'):
                #PrintMsg(str(iRow) + ". " + str(rowInFile), 1)
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

                    if not rating in dRatings and not rating is None:
                        # save hex value as key and rating as value to dRatings dictionary
                        dRatings[hexCode] = rating  # dRatings[hexcode] = rating
                        #PrintMsg("\tAdding hexcode " + hexCode + " to dRatings with a rating of " + str(rating), 1)

                    #PrintMsg("\tAdding mukey " + mukey + " to dValues with a rating of " + str(rating), 1)
                    dValues[mukey] = rating  # dValues[mukey] = rating value
                    #PrintMsg(str(newRow), 1)

                iRow += 1

        else:
            # Process numeric data for class breaks
            #
            # Set field length to zero so that we do not truncate a numeric rating
            # Open output table for numeric data
            iRow = 0  # record counter. Skip first dummy record
            for rowInFile in csv.reader(open(ratingFile, 'r'), delimiter=',', quotechar='"'):

                if iRow > 1:
                    #newRow = list()
                    fldNo = 0
                    fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                    fixedRow.pop(iPop)  # lose the data from the column that is not populated
                    mukey, rating, hexCode = fixedRow
                    try:
                        rating = float(rating)

                        if not hexCode in dRatings:
                            # save hex value as key and rating as value to dRatings dictionary
                            dRatings[hexCode] = rating  # dRatings[hexcode] = rating
                            #PrintMsg(" \nSetting rating value for color (" + hexCode + ") to " + str(rating), 1)

                        else:
                            if rating > dRatings[hexCode]:
                                dRatings[hexCode] = rating
                                #PrintMsg(" \nUpdating rating value for color (" + hexCode + ") to " + str(rating), 1)

                            else:
                                #PrintMsg(" \nIgnoring rating value for color (" + hexCode + "): " + str(rating), 1)
                                pass

                        if not mukey in dValues:
                            # save mukey as key and rating
                            dValues[mukey] = rating

                    except:
                        pass

                iRow += 1

        return dRatings, dValues

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dRatings, dValues

    except:
        errorMsg()
        return dRatings, dValues


## ===================================================================================
def ReadLegendNumeric(legendFile, dataType):
    # create a dictionary containing hexcode(key) and label
    # create an ordered list of colors (should be unique)
    #
    try:
        # Create twp dictionaries. One uses the hex color as key, the other the legend label
        dColors = dict()
        dLegendLabels = dict()
        colorList = list()    # ordered list for legend, based upon hex value
        #csv.field_size_limit(512000)
        codePage = 'iso-8859-1'
        iRow = 0

        for rowInFile in csv.reader(open(legendFile, 'rb'), delimiter=',', quotechar='"'):
            if iRow > 0:
                newRow = list()
                fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                label, color = fixedRow

                # 2 lines of code to convert hex code to rgb
                # need to incorporate 4th value for transparency
                #h = color.lstrip('#')
                #rgb = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))

                dColors[color] = label
                #dLegendLabels[label] = color
                #PrintMsg(" \ndLabels " + color + ": " + label, 1)
                colorList.append(color)

            iRow += 1

        return dColors, colorList


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dColors

    except:
        errorMsg()
        return dColors

## ===================================================================================
def ReadLegend(legendFile, dataType):
    # create a dictionary containing hexcode(key) and rating label
    # create a list of colors (should be unique)
    #
    try:
        # Create twp dictionaries. One uses the hex color as key, the other the legend label
        dColors = dict()
        dLegendLabels = dict()
        colorList = list()    # ordered list for legend, based upon hex value
        #csv.field_size_limit(512000)
        codePage = 'iso-8859-1'
        iRow = 0

        for rowInFile in csv.reader(open(legendFile, 'rb'), delimiter=',', quotechar='"'):
            if iRow > 0:
                newRow = list()
                fixedRow = [x.decode(codePage) for x in rowInFile]  # fix non-utf8 characters
                label, color = fixedRow

                # 2 lines of code to convert hex code to rgb
                # need to incorporate 4th value for transparency
                #h = color.lstrip('#')
                #rgb = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))

                dColors[color] = label
                #dLegendLabels[label] = color
                #PrintMsg(" \ndLabels " + color + ": " + label, 1)
                colorList.append(color)

            iRow += 1

        return dColors, colorList


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dColors

    except:
        errorMsg()
        return dColors

## ===================================================================================
def CreateMapLegend(dLayerDefinition):
    # Create Map Legend dictionary from JSON string and thematic information
    #
    # hexVal = "#FFFF00"
    # h = hexVal.lstrip('#')
    # rgb = tuple(int(h[i:i+2], 16) for i in (0, 2 ,4))

    try:
        pass


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)

    except:
        errorMsg()

## ===================================================================================
def CreateDescription(dParams):
    # Create layer description string
    try:
        description = ""
        dList1 = ["CreationDateTime", "ResultColumnName", "AggregationMethod", "TiebreakRule",
        "UnitsofMeasure", "ComponentPercentCutoff", "InterpretNullsAsZero", "BeginningMonth",
        "EndingMonth", "LayerOption", "TopDepth", "BottomDepth", "DepthUnits"]

        # PrimaryDataSelectOptionLabel, PrimaryDataSelectOption
        # SecondaryDataSelectOptionLabel, SecondaryDataSelectOption

        # Update layer description
        description = dParams["SdvAttributeDescription"] + "\r\n"

        for key in dList1:
            param = dParams[key]
            if not param is None and not param == "":
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
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, json, csv
from arcpy import env

try:
    # Read input parameters
    inputShp = arcpy.GetParameterAsText(0)                   # input soil_mu shapefile from WSS as text
    mapLayers = arcpy.GetParameter(1)                        # list of selected soil maps from the thematic folder
    fillTransparency = arcpy.GetParameter(2)                 # percent transparency (integer, convert to 255 as opaque)
    drawOutlines = arcpy.GetParameter(3)                     # boolean to draw polygon outlines

    env.overwriteOutput= True

    installInfo = arcpy.GetInstallInfo()
    version = float(installInfo["Version"])

    # Get data folders from input layer
    # probably should validate the inputShp as soil polygon
    desc = arcpy.Describe(inputShp)
    spatialFolder = os.path.dirname(desc.catalogPath)  # spatial folder
    basePath = os.path.dirname(spatialFolder)
    thematicPath = os.path.join(basePath, "thematic")

    # Make sure that the 'thematic' folder exists.
    if not arcpy.Exists(thematicPath):
        # make sure the thematic folder exists.
        raise MyError, "Thematic data path " + thematicPath + " does not exist"


    # Create file geodatabase in base folder
    outputGDB = os.path.join(basePath, "WSS_ThematicMaps.gdb")
    if not arcpy.Exists(outputGDB):
        arcpy.CreateFileGDB_management(os.path.dirname(outputGDB), os.path.basename(outputGDB), "10.0")

    # Copy original shapefile to a filegeodatabase featureclass
    outputFC = os.path.join(outputGDB, inputShp)

    if arcpy.Exists(outputFC):
        arcpy.Delete_management(outputFC)

    # Seem to be having problems copying polygons when 0 are selected
    # Try switching selection (unless there already is one)
    iSel = int(arcpy.GetCount_management(inputShp).getOutput(0))
    if iSel == 0:
        arcpy.SelectLayerByAttribute_management(inputShp, "SWITCH_SELECTION")

    arcpy.CopyFeatures_management(inputShp, outputFC)

    if iSel == 0:
        arcpy.SelectLayerByAttribute_management(inputShp, "CLEAR_SELECTION")


    # Create layer file from input shapefile
    wssLayerFile = os.path.join(env.scratchFolder, "wss_thematicmap.lyr")
    arcpy.SaveToLayerFile_management(inputShp, wssLayerFile, "ABSOLUTE", 10.1)
    baseLayer = arcpy.mapping.Layer(wssLayerFile)

    # Replace layer file data source with the outputFC
    baseLayer.replaceDataSource(os.path.dirname(outputFC), "FILEGDB_WORKSPACE", os.path.basename(outputFC))
    arcpy.SaveToLayerFile_management(baseLayer, wssLayerFile, "ABSOLUTE", 10.1)

    # Create arcpy.mapping objects
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame

    # Create group layer for organizing individual soil maps under
    grpLayer = CreateGroupLayer()

    # Read summary.txt to create adictionary containing map layer names (item values)
    # and map ids (item keys)
    dMaps = ReadSummary(os.path.join(thematicPath, "summary.txt"), mapLayers)

    # Create sorted list of map ids to iterate by
    mapList = list()

    for mapID in sorted(dMaps.values()):
        mapList.append(mapID)

    for mapID in mapList:
        # for each soil map:
        #    read the rating file, parameter file and legend file into dictionaries
        #    create output table
        #    dump sorted dictionary contents into output table
        #    read appropriate json file into layerDefinition dictionary
        #    update layerDefinition dictionary using other dictionaries

        # Name each input file to be read for this map
        paramsFile = os.path.join(thematicPath, "parameters" + str(mapID) + ".txt")
        ratingFile = os.path.join(thematicPath, "rating" + str(mapID) + ".csv")
        legendFile = os.path.join(thematicPath, "filteredLegend" + str(mapID) + ".csv")

        # Create dictionaries from thematic text and csv files
        # 1. Parameters
        #
        dParams = ReadParameters(paramsFile)

        if len(dParams) == 0:
            raise MyError, ""


        mapLayerName = dParams["SdvAttributeName"]

        dataType = dParams["ResultDataType"]  # current domain: 'Choice', 'Float','Integer', 'string', 'VText'
        tblName = dParams["SdvAttributeName"].replace(" ", "_") + str(mapID)
        PrintMsg("\tCreating soil map layer: " + mapLayerName, 0)

        # Remove existing map layers with same name
        existingLayers = arcpy.mapping.ListLayers(mxd, mapLayerName, df)
        for soilMap in existingLayers:
            if soilMap.longName == os.path.join("WSS Thematic Soil Map", mapLayerName):
                arcpy.mapping.RemoveLayer(df, soilMap)

        #
        #
        #
        # 2. Legend
        dLegend, colorList = ReadLegend(legendFile, dataType)

        if dLegend is None or len(dLegend) == 0:
            raise MyError, ""
        #


        # 3. Ratings. Get field definitions and rating datatype before hand.
        dFieldTypes = FieldTypes()
        dRatings, dValues = ReadRatings(ratingFile, dataType.upper())

        if dRatings is None or len(dRatings) == 0:
            raise MyError, ""

        # 4. Assemble all required legend information into a single, ordered list
        legendList = list()
        #PrintMsg(" \ndRatings: " + str(dRatings), 1)

        for clr in colorList:
            try:
                #PrintMsg("\tGetting legend info for " + clr, 1)
                rating = dRatings[clr]
                legendLabel = dLegend[clr]
                legendList.append([rating, legendLabel, clr])
                #PrintMsg(" \n" + str(rating) + ": " + str(legendLabel) + "; " + clr, 1)

            except:
                pass
                #errorMsg()

        #PrintMsg(" \nlegendList: " + str(legendList), 1)

        # 5. Create layer definition using JSON string
        #if version >= 10.3:
        if version >= 10.1:
            if dataType.upper() in ['CHOICE', 'STRING', 'VTEXT']:
                PrintMsg(" \nGetting unique values legend", 1)
                dLayerDefinition = UniqueValuesJSON(legendList)

            elif dataType.upper() in ['FLOAT','INTEGER']:
                PrintMsg(" \nGetting class breaks legend", 1)
                dLayerDefinition = ClassBreaksJSON(legendList)

            else:
                raise MyError, "Unmatched data type: " + dataType.upper()

            if dLayerDefinition is None or len(dLayerDefinition) == 0:
                raise MyError, ""

            #else:
            #    PrintMsg(" \n2. dLayerDefinition: " + '"' + str(dLayerDefinition) + '"', 1)

        # 5. Update layerDefinition dictionary for this map layer
        newLayer = arcpy.mapping.Layer(wssLayerFile)
        newLayer.name = dParams["SdvAttributeName"]
        newLayer.description = CreateDescription(dParams)

        # Try adding attribute directly to shapefile
        #
        # Big drawback to this option. Writing null numeric data to DBF converts to zero.
        #
        desc = arcpy.Describe(inputShp)
        fields = desc.fields
        fieldList = [fld.name.upper() for fld in fields]

        if not dParams["ResultColumnName"].upper() in fieldList:
            addType, addWidth = dFieldTypes[dataType.upper()]
            arcpy.AddField_management(newLayer, dParams["ResultColumnName"], addType, "", "", addWidth)

        #for mukey, rating in dValues.items():
        #    PrintMsg("\tUpdating table for mukey " + mukey + " with rating: " + str(rating), 1)

        with arcpy.da.UpdateCursor(newLayer, ["mukey", dParams["ResultColumnName"]]) as cur:
            for rec in cur:
                mukey = rec[0]
                if mukey in dValues:
                    rating = dValues[mukey]

                else:
                    rating = None

                rec[1] = rating
                cur.updateRow(rec)

        # Update layer symbology using JSON dictionary
        if version >= 10.3:
            PrintMsg(" \nUpdating symbology using JSON string", 1)

            # Originally loaded the entire dictionary. Try instead converting dictionary to string and using json.loads(jString)
            #obj = json.loads(sJSON)
            #newLayer.updateLayerFromJSON(dLayerDefinition)
            newLayer.updateLayerFromJSON(dLayerDefinition)

        arcpy.mapping.AddLayerToGroup(df, grpLayer, newLayer, "BOTTOM")  # add soil map layer to group layer

        mapLayerFile = os.path.join(basePath, tblName + ".lyr")
        arcpy.SaveToLayerFile_management(newLayer, mapLayerFile, "RELATIVE", "10.1")

    # Define new output group layer file (.lyr) to permanently save all map layers to
    grpFile = os.path.join(basePath, grpLayer.name) + ".lyr"

    #if arcpy.Exists(grpFile):
    #    arcpy.Delete_management(grpFile)

    arcpy.SaveToLayerFile_management(grpLayer, grpFile)
    PrintMsg(" \nSaved group layer to " + grpFile, 0)

    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

    PrintMsg(" \nFinished running \n ", 0)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
