# SSURGO_gSSURGO_byState.py
#
# ArcGIS 10.1
#
# Steve Peaslee, August 02, 2011
#
# Revising code to work with ArcGIS 10.1 and new SSURGO Download tools
# Designed to drive "SSURGO_MergeSoilShapefilesbyAreasymbol_GDB.py"
#
# SDM Access query for getting overlap areas (that have spatial data) by state:
# SELECT legend.areasymbol FROM (legend INNER JOIN laoverlap ON legend.lkey = laoverlap.lkey)
# INNER JOIN sastatusmap ON legend.areasymbol = sastatusmap.areasymbol
# WHERE (((laoverlap.areatypename)='State or Territory') AND ((laoverlap.areaname) Like '<statename>%') AND
# ((legend.areatypename)='Non-MLRA Soil Survey Area') AND ((sastatusmap.sapubstatuscode) = 2) );
#
# 2014-01-08
# 2014-01-15  Noticed issue with Pacific Basin surveys in the legendAreaOverlap table. Someone
#             removed the [State or Territory] = 'Pacific Basin' entries so this tool will no
#             longer work for PAC Basin.
# 2014-09-27  sQuery modified to create a geodatabase with ALL surveys including the NOTCOM-only. Implemented
#             with the FY2015 production.
# 2017-09-21  Added option for state boundary clip of the MUPOLYGON featureclass. Only this one featureclass is
#             clipped. NONE of the associated data is removed or altered in the attribute tables.
#
# 2017-09-21  To do: uppercase the statename query; compact the geodatabase?; add list of island states to exclude from clip?
#             Test without setting clipping layer, or field. Update validation code for these 2 parameters; Test state clip using
#             GCS WGS1984 state boundaries; test Alaska clip; JFF, compare Guam gSSURGO clip to Guam shapefile; test missing
#             SSURGO downloads; test loss of S drive; make sure all temporary layers are cleaned up;
#
# 2017-12-21  Overlap tables fixed, so this version of the tool will now work with the Pacific Islands to create
#             individual geodatabasess by state.

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
        errorMsg()
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

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
def StateAOI():
    # Create dictionary object containing list of state abbreviations and their geographic regions

    try:
        # "Lower 48 States":
        # "Alaska":
        # "Hawaii":
        # "American Samoa":
        # "Puerto Rico and U.S. Virgin Islands"
        # "Pacific Islands Area"
        #
        dAOI = dict()
        dAOI['Alabama'] = 'Lower 48 States'
        dAOI['Alaska'] = 'Alaska'
        dAOI['American Samoa'] = 'Hawaii'
        dAOI['Arizona'] = 'Lower 48 States'
        dAOI['Arkansas'] = 'Lower 48 States'
        dAOI['California'] = 'Lower 48 States'
        dAOI['Colorado'] = 'Lower 48 States'
        dAOI['Connecticut'] = 'Lower 48 States'
        dAOI['Delaware'] = 'Lower 48 States'
        dAOI['District of Columbia'] = 'Lower 48 States'
        dAOI['Florida'] = 'Lower 48 States'
        dAOI['Georgia'] = 'Lower 48 States'
        dAOI['Hawaii'] = 'Hawaii'
        dAOI['Idaho'] = 'Lower 48 States'
        dAOI['Illinois'] = 'Lower 48 States'
        dAOI['Indiana'] = 'Lower 48 States'
        dAOI['Iowa'] = 'Lower 48 States'
        dAOI['Kansas'] = 'Lower 48 States'
        dAOI['Kentucky'] = 'Lower 48 States'
        dAOI['Louisiana'] = 'Lower 48 States'
        dAOI['Maine'] = 'Lower 48 States'
        dAOI['Maryland'] = 'Lower 48 States'
        dAOI['Massachusetts'] = 'Lower 48 States'
        dAOI['Michigan'] = 'Lower 48 States'
        dAOI['Minnesota'] = 'Lower 48 States'
        dAOI['Mississippi'] = 'Lower 48 States'
        dAOI['Missouri'] = 'Lower 48 States'
        dAOI['Montana'] = 'Lower 48 States'
        dAOI['Nebraska'] = 'Lower 48 States'
        dAOI['Nevada'] = 'Lower 48 States'
        dAOI['New Hampshire'] = 'Lower 48 States'
        dAOI['New Jersey'] = 'Lower 48 States'
        dAOI['New Mexico'] = 'Lower 48 States'
        dAOI['New York'] = 'Lower 48 States'
        dAOI['North Carolina'] = 'Lower 48 States'
        dAOI['North Dakota'] = 'Lower 48 States'
        dAOI['Ohio'] = 'Lower 48 States'
        dAOI['Oklahoma'] = 'Lower 48 States'
        dAOI['Oregon'] = 'Lower 48 States'
        dAOI['Pacific Basin'] = 'Pacific Islands Area'
        dAOI['Pennsylvania'] = 'Lower 48 States'
        dAOI['Puerto Rico and U.S. Virgin Islands'] = 'Lower 48 States'
        dAOI['Rhode Island'] = 'Lower 48 States'
        dAOI['South Carolina'] = 'Lower 48 States'
        dAOI['South Dakota'] = 'Lower 48 States'
        dAOI['Tennessee'] = 'Lower 48 States'
        dAOI['Texas'] = 'Lower 48 States'
        dAOI['Utah'] = 'Lower 48 States'
        dAOI['Vermont'] = 'Lower 48 States'
        dAOI['Virginia'] = 'Lower 48 States'
        dAOI['Washington'] = 'Lower 48 States'
        dAOI['West Virginia'] = 'Lower 48 States'
        dAOI['Wisconsin'] = 'Lower 48 States'
        dAOI['Wyoming'] = 'Lower 48 States'
        dAOI['Northern Mariana Islands'] = 'Pacific Islands Area'
        dAOI['Federated States of Micronesia'] = 'Pacific Islands Area'
        dAOI['Guam'] = 'Pacific Islands Area'
        dAOI['Palau'] = 'Pacific Islands Area'
        dAOI['Marshall Islands'] = 'Pacific Islands Area'

        return dAOI

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return dAOI

## ===================================================================================
def GetFieldList(tbi_1):
    # Create field list for MakeQueryTable

    try:
        fldList = ""

        pFld = arcpy.ParseTableName(os.path.basename(tbi_1)).split(",")
        db = pFld[0].strip()
        dbo = pFld[1].strip()
        tbl = pFld[2].strip()
        fldList = ""  # intialize fields string for MakeQuery Table
        # Create list of fields for export
        #PrintMsg("\nGetting fields for " + theTbl, 0)
        flds = arcpy.ListFields(tbi_1) # 9.3

        for fld in flds:              # 9.3
            fldp = fld.name
            fldq = db + "." + dbo + "."  + tbl + "." + fldp

            if fld.type != "OID":
                #PrintMsg("\nGetting name for field " + fldp, 0)

                if fldList != "":
                    fldList = fldList + ";" + fldq + " " + fldp

                else:
                    fldList = fldq + " " + fldp

        #PrintMsg(" \nOutput Fields: " + fldList, 0)
        return fldList

    except:
        errorMsg()
        return ""

## ===================================================================================
def GetAreasymbols(attName, theTile):
    # Pass a query (from GetSDMCount function) to Soil Data Access designed to get the count of the selected records
    import httplib, urllib2, json, socket

    try:

        # Now using this query to retrieve All surve areas including NOTCOM-only
        #sQuery = "SELECT legend.areasymbol FROM (legend INNER JOIN laoverlap ON legend.lkey = laoverlap.lkey) " + \
        #"INNER JOIN sastatusmap ON legend.areasymbol = sastatusmap.areasymbol " + \
        #"WHERE (((laoverlap.areatypename)='State or Territory') AND ((laoverlap.areaname) Like '" + theTile + "%') AND " + \
        #"((legend.areatypename)='Non-MLRA Soil Survey Area')) ;"

        sQuery = "SELECT legend.areasymbol FROM (legend INNER JOIN laoverlap ON legend.lkey = laoverlap.lkey) \
        INNER JOIN sastatusmap ON legend.areasymbol = sastatusmap.areasymbol \
        WHERE laoverlap.areatypename = 'State or Territory' AND laoverlap.areaname = '" + theTile + "' AND \
        legend.areatypename = 'Non-MLRA Soil Survey Area'"

        # Create empty value list to contain the count
        # Normally the list should only contain one item
        valList = list()

        # PrintMsg("\tQuery for " + theTile + ":  " + sQuery + " \n", 0)

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
            val = rec[0]
            valList.append(val)

        else:
          # No data returned for this query
          raise MyError, "SDA query failed to return requested information: " + sQuery

        if len(valList) == 0:
            raise MyError, "SDA query failed: " + sQuery

        return valList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except httplib.HTTPException, e:
        PrintMsg("HTTP Error: " + str(e), 2)
        return []

    except socket.error, e:
        raise MyError, "Soil Data Access problem: " + str(e)
        return []

    except:
        #PrintMsg(" \nSDA query failed: " + sQuery, 1)
        errorMsg()
        return []

## ===================================================================================
def GetFolders(inputFolder, valList, bRequired, theTile):
    # get a list of all matching folders under the input folder, assuming 'soil_' naming convention

    try:
        env.workspace = inputFolder
        surveyList = list()
        #folderList = arcpy.ListWorkspaces("soil_*", "Folder") # fullpath of all soil_* folders
        missingList = list()
        #PrintMsg(" \nFound "+ Number_Format(len(folderList), 0, True) + " soil folders", 1)

        # check each subfolder to make sure it is a valid SSURGO dataset
        # validation: has 'soil_' prefix and contains a spatial folder and a soilsmu_a shapefile
        # and matches one of the AREASYMBOL values in the legend table
        #PrintMsg(" \nLooking for these SSURGO datasets: " + ", ".join(valList), 0)

        for shpAS in valList:
            # this should be one of the target SSURGO dataset folder
            # add it to the choice list
            subFolder = "soil_" + shpAS.lower()
            shpName = "soilmu_a_" + shpAS.lower() + ".shp"
            shpPath = os.path.join( os.path.join( inputFolder, os.path.join(subFolder, "spatial")), shpName)

            if arcpy.Exists(shpPath):
                surveyList.append(subFolder)

            else:
                # Missing soil polygon shapefile for a required SSURGO dataset
                #PrintMsg("\t" + shpPath, 1)
                missingList.append(shpAS)

        if len(missingList) > 0 and bRequired:
            raise MyError, "Failed to find one or more required SSURGO datasets for " + theTile + ": " + ", ".join(missingList)

        return surveyList

    except MyError, err:
        PrintMsg(str(err), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def ClipMuPolygons(targetLayer, aoiLayer, outputClip, theTile):

    try:
        PrintMsg("Clipping MUPOLYGON featureclass to the " + theTile + " state boundary", 0)

        arcpy.OverwriteOutput = True

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
        with arcpy.da.SearchCursor(aoiLayer, ["SHAPE@"], "", targetLayer) as cur:

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
        arcpy.DefineProjection_management(extentFC, targetLayer)
        #PrintMsg(" \nExtent:  " + str(xMin) + "; " + str(yMin) + "; " + str(xMax) + "; " + str(yMax), 0)

        # Select target layer polygons within the AOI extent
        # in a script, the featurelayer (extentLayer) may not exist
        #
        #PrintMsg(" \nSelecting target layer polygons within AOI", 0)
        arcpy.MakeFeatureLayer_management(extentFC, extentLayer)

        inputDesc = arcpy.Describe(targetLayer)
        inputGDB = os.path.dirname(inputDesc.catalogPath)  # assuming gSSURGO, no featuredataset
        outputGDB = os.path.dirname(outputClip)

        if not inputDesc.hasSpatialIndex:
            arcpy.AddSpatialIndex_management(targetLayer)

        if inputDesc.dataType.upper() == "FEATURECLASS":
            # swap the input featureclass with a featurelayer.
            fcPath = inputDesc.catalogPath
            targetLayer = inputDesc.aliasName
            arcpy.MakeFeatureLayer_management(fcPath, targetLayer)

        arcpy.SelectLayerByLocation_management(targetLayer, "INTERSECT", extentLayer, "", "NEW_SELECTION")

        # Create temporary featureclass using selected target polygons
        #

        arcpy.CopyFeatures_management(targetLayer, outputFC)

        #arcpy.MakeFeatureLayer_management(outputFC, selectedPolygons)
        arcpy.SelectLayerByAttribute_management(targetLayer, "CLEAR_SELECTION")

        # Create spatial index on temporary featureclass to see if that speeds up the clip
        #arcpy.AddSpatialIndex_management(outputFC)

        # Clipping process
        #if operation == "CLIP":
        #PrintMsg(" \nClipping " + outputFC + " to create final layer " + os.path.basename(outputClip) + "...", 1)
        arcpy.Clip_analysis(outputFC, aoiLayer, sortedFC)
        #PrintMsg(" \n\tCreating temporary featureclass", 0)
        fields = arcpy.Describe(sortedFC).fields
        shpField = [f.name for f in fields if f.type.upper() == "GEOMETRY"][0]
        PrintMsg(" \nUpdating spatial index for clipped polygon featureclass... ", 0)

        # resort polygons after clip to get rid of tile artifact
        arcpy.Sort_management(sortedFC, outputClip, [[shpField, "ASCENDING"]], "UL")  # Try sorting before clip. Not sure if this well help right here.

        arcpy.AddSpatialIndex_management(outputClip)

        # Delete original MUPOLYGON featureclass and rename outputCLip to MUPOLYGON
        if arcpy.Exists(fcPath):
            arcpy.Delete_management(fcPath)
            if arcpy.Exists(fcPath):
                raise MyError, "Failed to delete " + fcPath

            time.sleep(1)
            arcpy.Rename_management(outputClip, fcPath)  # error here 'table already exists
            #outputClip = oldFC


        if arcpy.Exists(fcPath) and outputGDB == inputGDB and arcpy.Exists(os.path.join(outputGDB, "mapunit")):
            # Create relationshipclass to mapunit table
            relName = "zMapunit_" + os.path.basename(fcPath)

            if not arcpy.Exists(os.path.join(outputGDB, relName)):
                arcpy.AddIndex_management(fcPath, ["mukey"], "Indx_" + os.path.basename(fcPath))
                #PrintMsg(" \n\tAdding relationship class...")
                arcpy.CreateRelationshipClass_management(os.path.join(outputGDB, "mapunit"), fcPath, os.path.join(outputGDB, relName), "SIMPLE", "> Mapunit Polygon Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

        # Clean up temporary layers and featureclasses
        #
        cleanupList = [extentLayer, extentFC, outputFC, sortedFC]

        for layer in cleanupList:
            if arcpy.Exists(layer):
                arcpy.Delete_management(layer)

        arcpy.SetParameter(2, outputClip)
        #PrintMsg(" \nFinished \n", 0)

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)

    except:
        errorMsg()



## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, time
from arcpy import env

# Create the Geoprocessor object
try:
    inputFolder = arcpy.GetParameterAsText(0)      # Change this to the SSURGO Download folder (inputFolder)
    outputFolder = arcpy.GetParameterAsText(1)     # output folder to contain new geodatabases
    theTileValues = arcpy.GetParameter(2)          # list of state names
    bOverwriteOutput = arcpy.GetParameter(3)       # overwrite existing geodatabases
    bRequired = arcpy.GetParameter(4)              # require that all available SSURGO be present in the input folder
    useTextFiles = arcpy.GetParameter(5)           # checked: use text files for attributes; unchecked: use Access database for attributes
    aoiLayer = arcpy.GetParameterAsText(6)         # optional state layer used for clipping
    aoiField = arcpy.GetParameterAsText(7)         # optional state name field used to query for AOI


    #import SSURGO_MergeSoilShapefilesbyAreasymbol_GDB
    import SSURGO_Convert_to_Geodatabase

    # Get dictionary containing 'state abbreviations'
    stDict = StateNames()

    # Get dictionary containing the geographic region for each state
    dAOI = StateAOI()

    # Target attribute. Note that is this case it is lowercase. Thought it was uppercase for SAVEREST?
    # Used for XML parser
    attName = "areasymbol"

    # Track success or failure for each exported geodatabase
    goodExports = list()
    badExports = list()

    for theTile in theTileValues:
        stAbbrev = stDict[theTile]
        tileInfo = (stAbbrev, theTile)

        PrintMsg(" \n***************************************************************", 0)
        PrintMsg("Processing state: " + theTile, 0)
        PrintMsg("***************************************************************", 0)

        if not arcpy.Exists(inputFolder):
            raise MyError, "Unable to connect to folder containing SSURGO downloads (" + inputFolder + ")"

        # Get list of AREASYMBOLs for this state tile from LAOVERLAP table in Soil Data Mart DB
        if theTile == "Puerto Rico and U.S. Virgin Islands":
            valList = GetAreasymbols(attName, "Puerto Rico")
            valList = valList + GetAreasymbols(attName, "Virgin Islands")

        else:
            valList = GetAreasymbols(attName, theTile)

        if len(valList) == 0:
            raise MyError, "Soil Data Access web service failed to retrieve list of areasymbols for " + theTile

        # If the state tile is "Pacific Basin", remove the Areasymbol for "American Samoa"
        # from the list. American Samoa will not be grouped with the rest of the PAC Basin
        if theTile == "Pacific Basin":
            #PrintMsg(" \nRemoving  areasymbol for American Samoa", 1)
            rmVal = GetAreasymbols(attName, "American Samoa")[0]
            PrintMsg(" \nAreaSymbol for American Samoa: " + rmVal, 1)

            if rmVal in valList:
                valList.remove(rmVal)

        # PrintMsg(" \nFinal Areasymbol List: " + ", ".join(valList), 0)

        # Get the AOI for this state. This is needed later to set the correct XML and coordinate system
        theAOI = dAOI[theTile]

        # Get list of matching folders containing SSURGO downloads
        surveyList = GetFolders(inputFolder, valList, bRequired, theTile)
        valList = list() # empty list or the spatial sort won't get used later on

        if len(surveyList) > 0:

            # Set path and name of Geodatabase for this state tile
            outputWS = os.path.join(outputFolder, "gSSURGO_" + stAbbrev + ".gdb")

            if arcpy.Exists(outputWS):
                if bOverwriteOutput:
                    PrintMsg(" \nRemoving existing geodatabase for " + theTile, 0)
                    try:
                        arcpy.Delete_management(outputWS)
                        time.sleep(1)
                        
                    except:
                        pass

                    if arcpy.Exists(outputWS):
                        # Failed to delete existing geodatabase
                        raise MyError, "Unable to delete existing database: " + outputWS

            # Call SDM Export script
            # 12-25-2013 try passing more info through the stAbbrev parameter
            #
            # PrintMsg(" \nPassing list of survey areas to 'SSURGO_Convert_to_Geodatabase' script: " + ", ".join(surveyList), 1)
            bExported = SSURGO_Convert_to_Geodatabase.gSSURGO(inputFolder, surveyList, outputWS, theAOI, tileInfo, useTextFiles, False, valList)

            if bExported == False:
                PrintMsg("\tAdding " + theTile + " to list if failed conversions", 0)
                badExports.append(theTile)
                err = "Passed - Export failed for " + theTile

            else:
                # Successful export of the current tile
                #PrintMsg("\tAdding " + theTile + " to good list", 0)

                # Perhaps add the state-clip here???
                #
                if aoiLayer != "" and aoiField != "" and not theTile in ['Pacific Basin', 'Puerto Rico and U.S. Virgin Islands', 'Northern Mariana Islands', 'Federated States of Micronesia', 'Guam','Hawaii']:
                    # Apply selection to AOI layer
                    sql = "UPPER(" + aoiField + ") = '" + theTile.upper() + "'"
                    arcpy.SelectLayerByAttribute_management(aoiLayer, "NEW_SELECTION", sql)
                    bClipped = ClipMuPolygons(os.path.join(outputWS, "MUPOLYGON"), aoiLayer, os.path.join(outputWS, "MUPOLYGON_" + stAbbrev), theTile)

                # End of state clip

                goodExports.append(theTile)

        else:
            # Failed to find any SSURGO downloads for this tile
            #PrintMsg("None of the input surveys (" + ", ".join(valList) + ") were found for " + theTile, 2)
            badExports.append(theTile)

        # end of tile for loop

    PrintMsg(" \n" + (60 * "*"), 0)
    PrintMsg(" \n" + (60 * "*"), 0)
    PrintMsg("\nFinshed state exports", 0)

    if len(goodExports) > 0:
        PrintMsg(" \nSuccessfully created geodatabases for the following areas: " + ", ".join(goodExports) + " \n ", 0)

    if len(badExports) > 0:
        PrintMsg("Failed to create geodatabases for the following areas: " + ", ".join(badExports) + " \n ", 2)

except MyError, err:
    PrintMsg(str(err), 2)

except:
    errorMsg()
