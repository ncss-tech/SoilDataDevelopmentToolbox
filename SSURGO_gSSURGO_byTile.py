# SSURGO_gSSURGO_byTile.py
#
# Steve Peaslee, August 02, 2011
#
# Purpose: drive the SDM_Export_GDB.py script by looping through Tiles
#
# input selection layer must have user-specified tile attribute and CONUS flag to
# allow OCONUS areas to use a different output projection.
#
# Tile polygons use Select by Attribute (user-specified field and CONUS attributes)
# SSA polygons use Select by Location (intersect with tile polygons)
#
# 01-30-2012 - Revising to work with any polygon tile and a user specified
# attribute column. The ArcTool validator provides a method to get a unique
# list of attribute values and presents those to the user for
#
# 02-15-2012 Ported back to ArcGIS 9.3.1
#
# 07-02-2012 Fixed Jennifer's problem with use of featureclass for input Soil Survey Boundaries.
#
# 11-13-2012 Moved to arcpy
#
# 01-08-2014
#
# 2014-09-27

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    # Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
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
        theMsg = tbinfo + " \n" + str(sys.exc_type)+ ": " + str(sys.exc_value)
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
def CheckWSS(missingList):
    # If some of the selected soil survey downloads are not available in the download
    # folder, confirm with Soil Data Access service to make sure that WSS does not have them.
    # This could be problematic considering WSS problems as of December 2013 with zero-byte
    # zip files, etc.
    #
    # This should use SASTATUSMAP table instead of SACATALOG
    # Add 'AND SAPUBSTATUSCODE = 2' for finding spatial only
    import time, datetime, urllib2, json

    missingAS = list()

    for subFolder in missingList:
        missingAS.append(subFolder[-5:].upper())

    missingQuery = "'" + "','".join(missingAS) + "'"

    try:
        sQuery = "SELECT AREASYMBOL FROM SASTATUSMAP WHERE AREASYMBOL IN (" + missingQuery + ") AND SAPUBSTATUSCODE = 2"
        #PrintMsg(" \nQuery: " + sQuery, 1)


	# NEW POST REST REQUEST BEGINS HERE
	#
        # Uses new HTTPS URL
        # Post Rest returns
        theURL = "https://sdmdataaccess.nrcs.usda.gov"
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        # Create request using JSON, return data as JSON
        dRequest = dict()
        dRequest["format"] = "JSON"
        dRequest["query"] = sQuery
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service using urllib2 library
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        # Convert the returned JSON string into a Python dictionary.
        data = json.loads(jsonString)
        del jsonString, resp, req

        # Find data section (key='Table')
        valList = list()

        if "Table" in data:
            dataList = data["Table"]  # Data as a list of lists. All values come back as string.

            # Iterate through dataList and reformat the data to create the menu choicelist

            for rec in dataList:
                areasym = rec[0]
                valList.append(areasym)

        else:
            # No data returned for this query
            pass

        reallyMissing = list()

        for areaSym in missingAS:
            if areaSym in valList:
                # According to Soil Data Access, this survey is available for download, user needs to
                # download all missing surveys from Web Soil Survey and then rerun this tool
                reallyMissing.append(areaSym)

        if len(reallyMissing) > 0:
            PrintMsg("These missing surveys are available for download from Web Soil Survey: " + ", ".join(reallyMissing), 2)
            return False

        else:
            PrintMsg("Problem confirming missing surveys from download folder", 2)
            return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ClipMupolygon(gdb, aoiLayer, aoiField, aoiValue, aliasName):

    try:
        env.overwriteOutput = True
        operation = "CLIP"

        # Get output geodatabase
        soilsFC = os.path.join(gdb, "MUPOLYGON")
        soilsLayer = "SoilsLayer"
        arcpy.MakeFeatureLayer_management(soilsFC, soilsLayer)
        field = arcpy.ListFields(aoiLayer, aoiField)[0]
        fieldType = field.type.upper()  # STRING, DOUBLE, SMALLINTEGER, LONGINTEGER, SINGLE, FLOAT
        env.workspace = gdb

        outputClip = os.path.join(gdb, arcpy.ValidateTableName("MUPOLYGON_" + str(aoiValue), gdb))

        if fieldType in ["SMALLINTEGER", "LONGINTEGER", "SINGLE", "LONG", "INTEGER"]:
            sql = aoiField + " = " + str(int(aoiValue))

        else:
            #PrintMsg("\tTile attribute datatype: " + fieldType, 1)
            sql = aoiField + " = '" + aoiValue + "'"

        PrintMsg("Clipping soil polygons for " + sql, 0)

        arcpy.SelectLayerByAttribute_management(aoiLayer, "NEW_SELECTION", sql)

        # Allow for NAD1983 to WGS1984 datum transformation if needed
        #
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"
        arcpy.env.geographicTransformations = tm

        # Clean up temporary layers and featureclasses
        #
        selectedPolygons = "Selected_Polygons"
        extentLayer = "AOI_Extent"
        extentFC = os.path.join(env.scratchGDB, extentLayer)
        outputFC = os.path.join(env.scratchGDB, selectedPolygons)
        sortedFC = os.path.join(env.scratchGDB, "SortedPolygons")
        cleanupList = [extentLayer, extentFC, outputFC]

        for layer in cleanupList:
            if arcpy.Exists(layer):
                arcpy.Delete_management(layer)

        # Find extents of the AOI
        #
        #PrintMsg(" \nGetting extent for AOI", 0)
        xMin = 9999999999999
        yMin = 9999999999999
        xMax = -9999999999999
        yMax = -9999999999999

        # targetLayer is being used here to supply output coordinate system
        with arcpy.da.SearchCursor(aoiLayer, ["SHAPE@"], "", soilsLayer) as cur:

            for rec in cur:
                ext = rec[0].extent
                xMin = min(xMin, ext.XMin)
                yMin = min(yMin, ext.YMin)
                xMax = max(xMax, ext.XMax)
                yMax = max(yMax, ext.YMax)

        # Create temporary AOI extents featureclass
        #
        point = arcpy.Point()
        array = arcpy.Array()
        featureList = list()
        coordList = [[[xMin, yMin],[xMin, yMax],[xMax, yMax], [xMax, yMin],[xMin, yMin]]]

        for feature in coordList:
            for coordPair in feature:
                point.X = coordPair[0]
                point.Y = coordPair[1]
                array.add(point)

        polygon = arcpy.Polygon(array)
        featureList.append(polygon)

        arcpy.CopyFeatures_management([polygon], extentFC)
        arcpy.DefineProjection_management(extentFC, soilsLayer)
        #PrintMsg(" \nAOI Extent:  " + str(xMin) + "; " + str(yMin) + "; " + str(xMax) + "; " + str(yMax), 0)

        # Select target layer polygons within the AOI extent
        # in a script, the featurelayer (extentLayer) may not exist
        #
        #PrintMsg(" \nSelecting target layer polygons within AOI", 0)
        arcpy.MakeFeatureLayer_management(extentFC, extentLayer)

        inputDesc = arcpy.Describe(soilsLayer)
        inputGDB = os.path.dirname(inputDesc.catalogPath)  # assuming gSSURGO, no featuredataset
        outputGDB = os.path.dirname(outputClip)

        if not inputDesc.hasSpatialIndex:
            arcpy.AddSpatialIndex_management(soilsLayer)

        arcpy.SelectLayerByLocation_management(soilsLayer, "INTERSECT", extentLayer, "", "NEW_SELECTION")

        # Create temporary featureclass using selected target polygons
        #
        #PrintMsg(" \n\tCreating temporary featureclass", 0)
        arcpy.CopyFeatures_management(soilsLayer, outputFC)
        arcpy.SelectLayerByAttribute_management(soilsLayer, "CLEAR_SELECTION")

        # Create spatial index on temporary featureclass to see if that speeds up the clip
        arcpy.AddSpatialIndex_management(outputFC)

        # Clipping process

        # resort polygons after clip to get rid of tile artifact

        # arcpy.Sort_management(sortedFC, outputClip, [[shpField, "ASCENDING"]], "UL")  # Try sorting before clip. Not sure if this well help right here.

        if operation == "CLIP":
            #PrintMsg(" \n\tCreating final layer " + os.path.basename(outputClip) + "...", 0)
            #arcpy.Clip_analysis(outputFC, aoiLayer, outputClip)
            arcpy.Clip_analysis(outputFC, aoiLayer, sortedFC)
            fields = arcpy.Describe(sortedFC).fields
            shpField = [f.name for f in fields if f.type.upper() == "GEOMETRY"][0]
            arcpy.Sort_management(sortedFC, outputClip, [[shpField, "ASCENDING"]], "UL")  # Try sorting before clip. N
            
            arcpy.AddSpatialIndex_management(outputClip)

        elif operation == "INTERSECT":
            #PrintMsg(" \nPerforming final intersection...", 0)
            arcpy.Intersect_analysis([outputFC, aoiLayer], outputClip)

        if arcpy.Exists(outputClip) and outputGDB == inputGDB and arcpy.Exists(os.path.join(outputGDB, "mapunit")):
            # Create relationshipclass to mapunit table
            relName = "zMapunit_" + os.path.basename(outputClip)

            if not arcpy.Exists(os.path.join(outputGDB, relName)):
                arcpy.AddIndex_management(outputClip, ["mukey"], "Indx_" + os.path.basename(outputClip))
                #PrintMsg(" \n\tAdding relationship class...")
                arcpy.CreateRelationshipClass_management(os.path.join(outputGDB, "mapunit"), outputClip, os.path.join(outputGDB, relName), "SIMPLE", "> Mapunit Polygon Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

            # Add alias to featureclass
            # arcpy.AlterAliasName(outputClip, "Map Unit Polygons - " + aoiField + ":" + str(aoiValue))
            arcpy.AlterAliasName(outputClip, "Map Unit Polygons - " + aliasName)

        # Clean up temporary layers and featureclasses
        #
        cleanupList = [extentLayer, extentFC, outputFC]

        for layer in cleanupList:
            if arcpy.Exists(layer):
                arcpy.Delete_management(layer)

        # Clear selection on aoiLayer
        arcpy.SelectLayerByAttribute_management(aoiLayer, "CLEAR_SELECTION", sql)

        #PrintMsg(" \nClipping process complete for " + str(aoiValue) + " \n", 0)


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)
        return True

    except:
        errorMsg()
        return False

## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, locale, traceback, arcpy
from arcpy import env

# Create the Geoprocessor object
try:

    ssaFC = arcpy.GetParameterAsText(0)            # input Survey Area layer containing AREASYMBOL (featurelayer)
    tileFC = arcpy.GetParameterAsText(1)           # input polygon layer containing tile value
    tileField = arcpy.GetParameter(2)              # featureclass column that contains the tiling attribute (MO, MLRASYM, AREASYMBOL, etc)
    tileList = arcpy.GetParameterAsText(3)         # list of tile values to process (string or long, derived from tileField)
    tileName = arcpy.GetParameterAsText(4)         # string used to identify type of tile (MO, MLRA, SSA, etc) used in geodatabase name
    inputFolder = arcpy.GetParameterAsText(5)      # input folder containing SSURGO downloads
    outputFolder = arcpy.GetParameterAsText(6)     # output folder to contain new geodatabases (system folder)
    theAOI = arcpy.GetParameter(7)                 # geographic region for output GDB. Used to determine coordinate system.
    useTextFiles = arcpy.GetParameter(8)           # Unchecked: import tabular data from Access database. Checked: import text files
    bClipSoils = arcpy.GetParameter(9)             # Create an additional clipped soil polygon featureclass

    # import python script that actually exports the SSURGO
    import SSURGO_Convert_to_Geodatabase
    import gSSURGO_Clip2

    # Set workspace environment to the folder containing the SSURGO downloads
    # Escape back-slashes in path

    # Make sure SSA layer exists. If connection is lost, it may still show up in ArcMap TOC
    if not arcpy.Exists(ssaFC):
        err = "Input selection layer missing"
        raise MyError, err

    else:
        sDesc = arcpy.Describe(ssaFC)

    saDesc = arcpy.Describe(ssaFC)
    saDataType = saDesc.dataSetType

    if saDataType.upper() == "FEATURECLASS":
        ssaLayer = "SSA Layer"
        arcpy.MakeFeatureLayer_management(ssaFC, ssaLayer)

    tileDesc = arcpy.Describe(tileFC)
    tileDataType = tileDesc.dataSetType

    if tileDataType.upper() == "FEATURECLASS":
        tileLayer = "Tile Layer"
        arcpy.MakeFeatureLayer_management(tileFC, tileLayer)

    else:
        tileLayer = tileFC

    tileList = tileList.split(";")

    # Get tile field information
    #PrintMsg(" \nGetting input field information", 1)
    tileField = arcpy.ListFields(tileLayer, "*" + str(tileField))[0]
    fldType = tileField.type.upper()
    fldName = tileField.name
    exportList = list() # list of successfully exported gSSURGO databases

    num = 0

    for theTile in tileList:
        num += 1

        PrintMsg(" \n" + (50 * "*"), 0)
        PrintMsg(Number_Format(num, 0, True) + ". Processing " + tileName + ": " + str(theTile), 0)
        PrintMsg((50 * "*"), 0)
        #PrintMsg(" \nDataType for input field (" + fldName +  "): " + fldType, 0)

        if fldType != "STRING":
            theTile = int(theTile)
            sQuery = arcpy.AddFieldDelimiters(tileLayer, fldName) + " = " + str(theTile)

        else:
            sQuery = arcpy.AddFieldDelimiters(tileLayer, fldName) + " = '" + str(theTile) + "'"

        # Select tile polygon by the current value from the choice list
        arcpy.SelectLayerByAttribute_management(tileLayer, "NEW_SELECTION", sQuery)
        iCnt = int(arcpy.GetCount_management(tileLayer).getOutput(0))

        if iCnt == 0:
            # bailout
            err = "Attribute selection failed for " + sQuery
            raise MyError, err

        #PrintMsg(" \n\tTile layer has " + str(iCnt) + " polygons selected", 0)

        # Select Survey Area polygons that intersect this tile (CONUS)
        # The operation was attempted on an empty geometry. Occurring in every third tile with 10.1
        arcpy.SelectLayerByAttribute_management(ssaLayer, "CLEAR_SELECTION")
        arcpy.SelectLayerByLocation_management(ssaLayer, "INTERSECT", tileLayer, "", "NEW_SELECTION")
        iCnt = int(arcpy.GetCount_management(ssaLayer).getOutput(0))

        if iCnt == 0:
            # bailout
            err = "Select layer by location failed"
            raise MyError, err

        else:
            #PrintMsg(" \n\tSelected " + str(iCnt) + " survey area polygons in " + ssaLayer, 1)
            # get list of unique areasymbol values from survey boundary layer (param 1)
            fieldList = ["AREASYMBOL"]
            asList = [("soil_" + row[0].encode('ascii').lower()) for row in arcpy.da.SearchCursor(ssaLayer, fieldList)]  # This was working....
            
            asSet = set(asList)   # remove duplicate attribute values
            surveyList = list(sorted(asSet))

            # Before proceeding further, confirm the existence of each SSURGO download
            # Important note. You cannot use os.path.join with inputFolder and subFolder without escaping.
            missingList = list()
            #PrintMsg(" \nConfirming existence of SSURGO downloads in: " + inputFolder, 0)

            for subFolder in surveyList:
                if not arcpy.Exists(os.path.join(inputFolder, subFolder)):
                    #PrintMsg("\t" + os.path.join(env.workspace, inputFolder), 0)
                    missingList.append(subFolder)

            if len(missingList) > 0:

                if CheckWSS(missingList):
                    PrintMsg("\tNot all surveys were available in Web Soil Survey", 1)

                else:
                    err = ""
                    raise MyError, err

        # Create output Geodatabase for tile
        if fldType != "STRING":
            # if tile value is numeric, insert leading zeros
            if theTile < 10:
                theDB = "gSSURGO_" + tileName + "_0" + str(theTile) + ".gdb"

            else:
                theDB = "gSSURGO_" + tileName  + "_" + str(theTile) + ".gdb"

        else:
            theDB = "gSSURGO_" + tileName + "_" + theTile + ".gdb"

        outputWS = os.path.join(outputFolder, theDB)

        if arcpy.Exists(outputWS):
            arcpy.Delete_management(outputWS)

        # Call SDM Export script. Not sure what is happening with aliasName. Doesn't seem like it is being used.
        aliasName = tileName + " " + str(theTile)
        #PrintMsg("\nSurvey list: " + str(surveyList), 1)
        bExported = SSURGO_Convert_to_Geodatabase.gSSURGO(inputFolder, surveyList, outputWS, theAOI, (aliasName, aliasName), useTextFiles, bClipSoils, [])
        

        if bExported:
            exportList.append(os.path.basename(outputWS))

            # Test to see if I can add the MUPOLYGON clip to this process
            #PrintMsg(" \nClip using tile value: " + str(theTile), 1)
            if bClipSoils:
                bClipped = ClipMupolygon(outputWS, tileLayer, fldName, theTile, aliasName)

                if bClipped == False:
                    raise MyError, ""

        else:
            err = "gSSURGO export failed for " + fldName + " value: " + str(theTile)
            raise MyError, err

        # end of for loop

    arcpy.RefreshCatalog(outputFolder)
    del outputFolder

    PrintMsg(" \nFinished creating the following gSSURGO databases: " + ", ".join(exportList) + " \n ", 0)

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
