# SDA_CreateAOI.py
#
# Steve Peaslee, USDA-NRCS, National Soil Survey Center
#
# Uses AOI in ArcMap to create a soil polygon layer from SDA PostRest service
#
# Below is an example of the type of query that this script can read from a file (Query_*.txt) that
# is stored in the same directory as this script.
#
# Please note the xxMUKEYSxx keyword is replaced by a list of mukeys obtained from the spatial
# layer and that the query MUST BE designed to return only ONE record per mukey.
# Any data returned from component or horizon-level tables must be summarized to the map unit level.
#
    # SELECT m.mukey, m.musym, m.muname, c.compname AS compnamedcp, c.comppct_r, c.taxclname, (c.nirrcapcl + c.nirrcapscl) AS nirrcapcl, m.farmlndcl, ma.hydgrpdcd, ma.hydclprs, ma.flodfreqdcd, s.saverest
    # FROM legend AS l
    # INNER JOIN mapunit m ON l.lkey = m.lkey AND m.mukey IN (xxMUKEYSxx)
    # INNER JOIN muaggatt ma ON m.mukey = ma.mukey
    # INNER JOIN sacatalog s ON l.areasymbol = s.areasymbol
    # INNER JOIN component c ON c.mukey = m.mukey AND c.majcompflag = 'Yes' AND c.cokey = 
    #    (SELECT TOP 1 co.cokey FROM component co INNER JOIN mapunit mu ON co.mukey=mu.mukey AND mu.mukey=m.mukey 
    #    ORDER BY co.comppct_r DESC)
    # ORDER BY m.musym, c.comppct_r DESC, c.cokey"""
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
        errorMsg()

        return "???"

## ===================================================================================
def PrepareAOI(inputAOI, bDissolve, bClean, aoiShp, dissShp):
    # 

    try:
        # Create a new featureclass with just the selected polygons
        #PrintMsg(" \nCreating single part polygon shapefile: " + simpleShp, 1)
        simpleShp = os.path.join(tmpFolder, "aoi_simple")
        arcpy.MultipartToSinglepart_management(inputAOI, simpleShp)

        cnt = int(arcpy.GetCount_management(simpleShp).getOutput(0))
        
        if cnt == 0:
            raise MyError, "No polygon features in " + simpleShp

        # Describe the input layer
        desc = arcpy.Describe(simpleShp)
        #dataType = desc.featureclass.dataType.upper()
        fields = desc.fields
        fldNames = [f.baseName.upper() for f in fields]
        #PrintMsg(" \nsimpleShp field names: " + ", ".join(fldNames), 1)
        bpartname = False

        if bDissolve:
            # Dissolve to single part polygons
            PrintMsg(" \nDissolving unneccessary polygon boundaries for Web Soil Survey AOI...", 0)
            arcpy.Dissolve_management(simpleShp, aoiShp, "", "", "SINGLE_PART") # this is the one to test for common points

            # Let's get a count to see how many polygons remain after the dissolve
            dissCnt = int(arcpy.GetCount_management(aoiShp).getOutput(0))
            PrintMsg(" \nAfter dissolve, " + Number_Format(dissCnt, 0, True) + " polygons remain", 0)

            if dissCnt > 0:
                # Make another copy to use a the dissolved version
                arcpy.CopyFeatures_management(aoiShp, dissShp)

        else:
            # Keep original boundaries, but if attribute table contains PARTNAME or LANDUNIT attributes, dissolve on that
            #
            # Create dissolved multipart shapefile to send to SDA, then union the results with the aoiShp
            arcpy.Dissolve_management(simpleShp, dissShp, "", "", "SINGLE_PART") # 


            if ("LAND_UNIT_TRACT_NUMBER" in fldNames and "LAND_UNIT_LAND_UNIT_NUMBER" in fldNames):
                # Planned land Unit featureclass
                # Go ahead and dissolve using partname which will be added next
                PrintMsg(" \nUsing Planned Land Unit polygons to build AOI for Web Soil Survey", 0)
                arcpy.AddField_management(simpleShp, "partname", "TEXT", "", "", 20)
                curFields = ["PARTNAME", "LAND_UNIT_TRACT_NUMBER", "LAND_UNIT_LAND_UNIT_NUMBER"]

                with arcpy.da.UpdateCursor(simpleShp, curFields) as cur:
                    for rec in cur:
                        # create stacked label for tract and field
                        partName = "T" + str(rec[1]) + "N" + str(rec[2])
                        rec[0] = partName
                        cur.updateRow(rec)

                arcpy.Dissolve_management(simpleShp, aoiShp, ["PARTNAME"], "", "MULTI_PART")
                bpartname = True

            elif "PARTNAME" in fldNames:
                # User has created a featureclass with partname attribute.
                # Regardless, dissolve any polygons on partname
                PrintMsg(" \nUsing partname polygon attributes to build AOI for Web Soil Survey", 0)
                arcpy.Dissolve_management(simpleShp, aoiShp, "partname", "", "MULTI_PART")
                bpartname = True

            elif ("CLU_NUMBER" in fldNames and "TRACT_NUMB" in fldNames and "FARM_NUMBE" in fldNames):
                # This must be a shapefile copy of CLU. Field names are truncated.
                # Keep original boundaries, but if attribute table contains LANDUNIT attributes, dissolve on that
                #
                # Go ahead and dissolve using partname which was previously added
                PrintMsg(" \nUsing CLU shapefile to build AOI for Web Soil Survey", 0)
                arcpy.AddField_management(simpleShp, "partname", "TEXT", "", "", 20)
                curFields = ["PARTNAME", "FARM_NUMBE", "TRACT_NUMB", "CLU_NUMBER"]

                with arcpy.da.UpdateCursor(simpleShp, curFields) as cur:
                    for rec in cur:
                        # create stacked label for tract and field
                        partName = "F" + str(rec[1]) + "T" + str(rec[2]) + "N" + str(rec[3])
                        rec[0] = partName
                        cur.updateRow(rec)

                arcpy.Dissolve_management(simpleShp, aoiShp, ["PARTNAME"], "", "MULTI_PART")
                bpartname = True

            elif ("TRACT_NUMBER" in fldNames and "FARM_NUMBER" in fldNames and "CLU_NUMBER" in fldNames):
                # This must be a shapefile copy of CLU. Field names are truncated.
                # Keep original boundaries, but if attribute table contains LANDUNIT attributes, dissolve on that
                #
                # Go ahead and dissolve using partname which was previously added
                PrintMsg(" \nUsing CLU shapefile to build AOI for Web Soil Survey", 0)
                arcpy.AddField_management(simpleShp, "partname", "TEXT", "", "", 20)
                curFields = ["PARTNAME", "FARM_NUMBER", "TRACT_NUMBER", "CLU_NUMBER"]

                with arcpy.da.UpdateCursor(simpleShp, curFields) as cur:
                    for rec in cur:
                        # create stacked label for tract and field
                        partName = "F" + str(rec[1]) + "T" + str(rec[2]) + "N" + str(rec[3])
                        rec[0] = partName
                        cur.updateRow(rec)

                arcpy.Dissolve_management(simpleShp, aoiShp, ["PARTNAME"], "", "MULTI_PART")
                bpartname = True

            elif ("CLUNBR" in fldNames and "TRACTNBR" in fldNames and "FARMNBR" in fldNames):
                # This must be a shapefile copy of CLU from Iowa
                # Keep original boundaries, but if attribute table contains LANDUNIT attributes, dissolve on that
                #
                # Go ahead and dissolve using partname which was previously added
                PrintMsg(" \nUsing CLU shapefile to build AOI for Web Soil Survey", 0)
                arcpy.AddField_management(simpleShp, "partname", "TEXT", "", "", 20)
                curFields = ["PARTNAME", "FARMNBR", "TRACTNBR", "CLUNBR"]

                with arcpy.da.UpdateCursor(simpleShp, curFields) as cur:
                    for rec in cur:
                        # create stacked label for tract and field
                        partName = "F" + str(rec[1]) + "T" + str(rec[2]) + "N" + str(rec[3])
                        #PrintMsg(partName, 1)
                        rec[0] = partName
                        cur.updateRow(rec)

                arcpy.Dissolve_management(simpleShp, aoiShp, ["PARTNAME"], "", "MULTI_PART")
                bpartname = True

            else:
                if arcpy.Exists(simpleShp):
                    #PrintMsg(" \nSaving " + simpleShp + " to " + aoiShp, 1)
                    arcpy.CopyFeatures_management(simpleShp, aoiShp)
                    PrintMsg(" \nUsing original polygons to build AOI for Web Soil Survey...", 0)

                else:
                    raise MyError, "Missing output " + simpleShp

        env.workspace = env.scratchFolder

        if not arcpy.Exists(aoiShp):
            raise MyError, "Missing AOI " + aoitShp

        arcpy.RepairGeometry_management(aoiShp, "DELETE_NULL")  # Need to make sure this isn't doing bad things.

        return True


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False


    except:
        errorMsg()
        return False

## ===================================================================================
def FormSpatialQueryJSON(theAOI):
    #
    # Create a simplified polygon from the input polygon using convex-hull.
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    # The clipPolygon will be used to clip the soil polygons back to the original AOI polygon
    #
    # Note. SDA will accept WKT requests for MULTIPOLYGON if you make these changes:
    #     Need to switch the initial query AOI to use STGeomFromText and remove the
    #     WKT search and replace for "MULTIPOLYGON" --> "POLYGON".
    #
    # I tried using the MULTIPOLYGON option for the original AOI polygons but SDA would
    # fail when submitting AOI requests with large numbers of vertices. Easiest just to
    # using convex hull polygons and clip the results on the client side.

    try:
        import json

        aoicoords = dict()
        i = 0
        # Commonly used EPSG numbers
        #epsgWM = 3857 # Web Mercatur
        #epsgWGS = 4326 # GCS WGS 1984
        #epsgNAD83 = 4269 # GCS NAD 1983
        #epsgAlbers = 102039 # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
        #tm = "WGS_1984_(ITRF00)_To_NAD_1983"  # datum transformation supported by this script

        #gcs = arcpy.SpatialReference(epsgWGS84)

        # Compare AOI coordinate system with that returned by Soil Data Access. The queries are
        # currently all set to return WGS 1984, geographic.

        # Get geographic coordinate system information for input and output layers
        validDatums = ["D_WGS_1984", "D_North_American_1983"]
        aoiCS = arcpy.Describe(theAOI).spatialReference

        if not aoiCS.GCS.datumName in validDatums:
            raise MyError, "AOI coordinate system not supported: " + aoiCS.name + ", " + aoiCS.GCS.datumName

        if aoiCS.GCS.datumName == "D_WGS_1984":
            tm = ""  # no datum transformation required

        elif aoiCS.GCS.datumName == "D_North_American_1983":
            tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        else:
            raise MyError, "AOI CS datum name: " + aoiCS.GCS.datumName

        env.geographicTransformations = tm
        sdaCS = arcpy.SpatialReference(epsgWGS84)

        # Determine whether
        if aoiCS.PCSName != "":
            # AOI layer has a projected coordinate system, so geometry will always have to be projected
            bProjected = True

        elif aoiCS.GCS.name != sdaCS.GCS.name:
            # AOI must be NAD 1983
            bProjected = True

        else:
            bProjected = False


        # Get list of field names
        desc = arcpy.Describe(theAOI)
        fields = desc.fields
        fldNames = [f.baseName.upper() for f in fields]
        i = 0

        features = list()

        aoicoords["type"] = 'FeatureCollection'
        aoicoords['features'] = list()


        if "PARTNAME" in fldNames:
            curFlds = ["SHAPE@", "partName"]

            if bProjected:
                # UnProject geometry from AOI to GCS WGS1984

                with arcpy.da.SearchCursor(theAOI, curFlds) as cur:
                    for rec in cur:
                        dFeat = {'type':'Feature', 'properties': {'partName': rec[1].encode('ascii')}, 'geometry': {'type':'Polygon'}}
                        polygon = rec[0].projectAs(sdaCS, tm)        # simplified geometry, projected to WGS 1984
                        sJSON = polygon.JSON
                        dJSON = json.loads(sJSON)

                        coordList = dJSON['rings']
                        newCoords = list()

                        for features in coordList:
                            newfeatures = list()

                            for ring in features:
                                x = round(ring[0], 6)
                                y = round(ring[1], 6)
                                newfeatures.append([x, y])

                            newCoords.append(newfeatures)

                        dFeat['geometry']['coordinates'] = newCoords
                        aoicoords['features'].append(dFeat)
                        i += 1

            else:
                # No projection required. AOI must be GCS WGS 1984

                with arcpy.da.SearchCursor(theAOI, curFlds) as cur:
                    for rec in cur:
                        # original geometry
                        dFeat = {'type':'Feature', 'properties': {'partName': rec[1].encode('ascii')}, 'geometry': {'type':'Polygon' }}
                        sJSON = rec[0].JSON
                        dJSON = json.loads(sJSON)
                        coordList = dJSON['rings']
                        newCoords = list()

                        for features in coordList:
                            newfeatures = list()

                            for ring in features:
                                x = round(ring[0], 6)
                                y = round(ring[1], 6)
                                newfeatures.append([x, y])

                            newCoords.append(newfeatures)

                        dFeat['geometry']['coordinates'] = newCoords
                        aoicoords['features'].append(dFeat)
                        i += 1

        else:
            # No partname attribute

            curFlds = ["SHAPE@"]

            if bProjected:
                # UnProject geometry from AOI to GCS WGS1984

                with arcpy.da.SearchCursor(theAOI, curFlds) as cur:
                    for rec in cur:
                        dFeat = {'type':'Feature', 'geometry': {'type':'Polygon' }}
                        polygon = rec[0].projectAs(sdaCS, tm)        # simplified geometry, projected to WGS 1984
                        sJSON = polygon.JSON
                        dJSON = json.loads(sJSON)

                        coordList = dJSON['rings']
                        newCoords = list()

                        for features in coordList:
                            newfeatures = list()

                            for ring in features:
                                x = round(ring[0], 6)
                                y = round(ring[1], 6)
                                newfeatures.append([x, y])

                            newCoords.append(newfeatures)

                        dFeat['geometry']['coordinates'] = newCoords
                        aoicoords['features'].append(dFeat)
                        i += 1

            else:
                # No projection required. AOI must be GCS WGS 1984

                with arcpy.da.SearchCursor(theAOI, curFlds) as cur:
                    for rec in cur:
                        # original geometry
                        dFeat = {'type':'Feature', 'geometry': {'type':'Polygon' }}
                        sJSON = rec[0].JSON
                        dJSON = json.loads(sJSON)
                        coordList = dJSON['rings']
                        newCoords = list()

                        for features in coordList:
                            newfeatures = list()

                            for ring in features:
                                #PrintMsg("\nring: " + str(ring), 1)
                                x = round(ring[0], 6)
                                y = round(ring[1], 6)
                                newfeatures.append([x, y])

                            newCoords.append(newfeatures)

                        dFeat['geometry']['coordinates'] = newCoords
                        aoicoords['features'].append(dFeat)
                        i += 1

        sAOI = json.dumps(aoicoords)

        #PrintMsg(" \naoicoords: " + str(aoicoords), 1)
        return aoicoords

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return aoicoords

    except:
        errorMsg()
        return aoicoords


## ===================================================================================
def FormSpatialQueryWKT(theAOI):
    #
    # Create a simplified WKT version of the AOI with coordinates rounded off to 6 places.
    # This function will not work with WSS 3.2.1 because it allows multiple polygons and interior rings.

    try:

        # Commonly used EPSG numbers
        #epsgWM = 3857 # Web Mercatur
        #epsgWGS = 4326 # GCS WGS 1984
        #epsgNAD83 = 4269 # GCS NAD 1983
        #epsgAlbers = 102039 # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
        #tm = "WGS_1984_(ITRF00)_To_NAD_1983"  # datum transformation supported by this script

        # Compare AOI coordinate system with that returned by Soil Data Access. The queries are
        # currently all set to return WGS 1984, geographic.

        # Get geographiccoordinate system information for input and output layers
        validDatums = ["D_WGS_1984", "D_North_American_1983"]
        aoiCS = arcpy.Describe(theAOI).spatialReference

        if not aoiCS.GCS.datumName in validDatums:
            raise MyError, "AOI coordinate system not supported: " + aoiCS.name + ", " + aoiCS.GCS.datumName

        if aoiCS.GCS.datumName == "D_WGS_1984":
            tm = ""  # no datum transformation required

        elif aoiCS.GCS.datumName == "D_North_American_1983":
            tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        else:
            raise MyError, "AOI CS datum name: " + aoiCS.GCS.datumName

        sdaCS = arcpy.SpatialReference(epsgWGS84)

        # Determine whether
        if aoiCS.PCSName != "":
            # AOI layer has a projected coordinate system, so geometry will always have to be projected
            bProjected = True

        elif aoiCS.GCS.name != sdaCS.GCS.name:
            # AOI must be NAD 1983
            bProjected = True

        else:
            bProjected = False

        gcs = arcpy.SpatialReference(epsgWGS84)
        i = 0

        # Reformat coordinates to 6 decimal places. GCS WGS 1984
        #
        # Initialize reformatted WKT string
        #newWKT = "("  # first of 3 opening brackets
        newWKT = "POLYGON "

        with arcpy.da.SearchCursor(theAOI, ["SHAPE@"]) as cur:
            for rec in cur:
                newWKT += "("
                wkt = rec[0].WKT
                cs = wkt[wkt.find("(") + 3:-2]
                rings = cs.split("(")

                i = 0

                for ring in rings:
                    i += 1

                    if i == 1:
                        # Outer ring
                        newWKT += "("
                        j =  0
                        #PrintMsg("OuterRing: " + ring[:-3], 1)
                        wktCoords = ring[:-3].split(",")

                        for coord in wktCoords:
                            j += 1
                            #PrintMsg("\tOuter coord: " + coord, 1)
                            a, b = coord.strip().split(" ")
                            X = str(round(float(a), 10))
                            Y = str(round(float(b), 10))
                            if j > 1:
                                newWKT += "," + X + " " + Y

                            else:
                                newWKT += X + " " + Y

                        newWKT += ")"


                    else:
                        # Inner rings
                        newWKT = newWKT + ",("
                        #PrintMsg("InnerRing: " + ring[:-1], 1)
                        wktCoords = ring[:-1].split(",")
                        k = 0

                        for coord in wktCoords:
                            k += 1
                            #PrintMsg("\tInner coord: " + coord, 1)
                            a, b = coord.strip().split(" ")
                            X = str(round(float(a), 10))
                            Y = str(round(float(b), 10))
                            if k > 1:
                                newWKT += "," + X + " " + Y

                            else:
                                newWKT += X + " " + Y

                        newWKT += ")"

                newWKT += ")"


        #newWKT += ")"  # third closing bracket

        #PrintMsg(" \nWKT:  " + newWKT + " (" + str(len(newWKT)) + " chars)", 1)

        return newWKT

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""


## ===================================================================================
def AddNewFields(outputShp, columnNames, columnInfo):
    # Create the empty output table that will contain the map unit AWS
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

        joinFields = list()
        outputTbl = os.path.join("IN_MEMORY", "QueryResults")
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        for i, fldName in enumerate(columnNames):
            vals = columnInfo[i].split(",")
            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if not fldName.lower() == "mukey":
                joinFields.append(fldName)

            arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)

        if arcpy.Exists(outputTbl):
            arcpy.JoinField_management(outputShp, "mukey", outputTbl, "mukey", joinFields)
            return columnNames

        else:
            return []

    except:
        errorMsg()
        return []

## ===================================================================================
def GetMukeys(theInput):
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
            sqlClause = (None, "ORDER BY MUKEY")
            mukeyList = list()

            with arcpy.da.SearchCursor(theInput, ["MUKEY"], sql_clause=sqlClause) as cur:
                for rec in cur:
                    mukey = rec[0].encode('ascii')
                    
                    if not mukey == '' and not mukey in mukeyList:
                        mukeyList.append(mukey)


            #PrintMsg("\tmukey list: " + str(mukeyList), 1)
            return mukeyList

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
def FormAttributeQuery(sQuery, mukeys):
    #
    # Given a simplified polygon layer, use vertices to form the spatial query for a Tabular request
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    #
    # input parameter 'mukeys' is a comma-delimited and single quoted list of mukey values
    #
    try:


        aQuery = sQuery.split(r"\n")
        bQuery = ""
        
        for s in aQuery:
            if not s.strip().startswith("--"):
                bQuery = bQuery + " " + s

        #PrintMsg(" \nSplit query into " + str(len(aQuery)) + " lines", 1)
        #bQuery = " ".join(aQuery)
        #PrintMsg(" \n" + bQuery, 1)

        if len(mukeys) == 0:
            raise MyError, ""

        elif len(mukeys) == 1:
            mukeyString = mukeys[1]

        else:
            mukeyString = ",".join(mukeys)

        sQuery = bQuery.replace("xxMUKEYSxx", mukeyString)

        if bVerbose:
            PrintMsg(" \n" + sQuery, 1)

        return sQuery

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def AttributeRequest(theURL, mukeyList, outputShp, sQuery):
    # POST REST which uses urllib and JSON
    #
    # Send query to SDM Tabular Service, returning data in JSON format

    try:
        #outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \n\tRequesting tabular data for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        mukeys = ",".join(mukeyList)

        sQuery = FormAttributeQuery(sQuery, mukeys)  # Combine user query with list of mukeys from spatial layer.
        if sQuery == "":
            raise MyError, "Missing query string"

        # Tabular service to append to SDA URL
        #url = theURL + "/Tabular/SDMTabularService/post.rest"
        url = theURL + "/Tabular/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["format"] = "JSON+COLUMNNAME+METADATA"
        dRequest["query"] = sQuery

        if bVerbose:
            PrintMsg(" \nURL: " + url)
            PrintMsg("format: " + str(dRequest["format"]))
            PrintMsg("query: " + sQuery)

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        if bVerbose:
            PrintMsg(" \nSDA attribute data in JSON format: \n " + str(jsonString), 1)

        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        #if len(mukeyList) != len(dataList):
        #    PrintMsg(" \nWarning! Only returned data for " + str(len(dataList)) + " mapunits", 1)

        PrintMsg(" \n\tImporting attribute data...", 0)
        newFields = AddNewFields(outputShp, columnNames, columnInfo)
        arcpy.AddField_management(outputShp, "acres", "DOUBLE")

        if len(newFields) == 0:
            raise MyError, ""

        #ratingField = newFields[-1]  # last field in query will be used to symbolize output layer

        if len(newFields) == 0:
            raise MyError, ""

        # Create list of outputShp fields to populate (everything but OID)
        desc = arcpy.Describe(outputShp)

        fields = desc.fields
        fieldList = list()

        for fld in fields:
            fldName = fld.name.upper()
            ratingType = fld.type

            if not fld.type == "OID" and not fldName.startswith("SHAPE"):
                fieldList.append(fld.name)

        # The rating field must be included in the query output or the script will fail. This
        # is a weak spot, but it is mostly for demonstration of symbology and map legends.
        #if ratingField in columnNames:
        #    outputIndx = columnNames.index(ratingField)  # Use to identify attribute that will be mapped

        #else:
        #    raise MyError, "Failed to find output field '" + ratingField + "' in " + ", ".join(columnNames)


        # Reading the attribute information returned from SDA Tabular service
        #
        arcpy.SetProgressorLabel("Importing attribute data...")
        featureCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))

        dMapunitInfo = dict()
        mukeyIndx = -1
        for i, fld in enumerate(columnNames):
            if fld.upper() == "MUKEY":
                mukeyIndx = i
                break

        if mukeyIndx == -1:
            raise MyError, "MUKEY column not found in query data"

        #PrintMsg(" \nColumnNames (" + str(mukeyIndx) + ") : " + ", ".join(columnNames))
        #PrintMsg(" \n" + str(fieldList), 1)
        noMatch = list()
        cnt = 0

        for rec in dataList:
            try:
                mukey = rec[mukeyIndx]
                dMapunitInfo[mukey] = rec
                #PrintMsg("\t" + mukey + ":  " + str(rec), 1)

            except:
                errorMsg()
                PrintMsg(" \n" + ", ".join(columnNames), 1)
                PrintMsg(" \n" + str(rec) + " \n ", 1)
                raise MyError, "Failed to save " + str(columnNames[i]) + " (" + str(i) + ") : " + str(rec[i])

        #PrintMsg(" \nUsing fields: " + ", ".join(fieldList), 1)

        # Write the attribute data to the featureclass table
        #
        step = featureCnt / 10
        arcpy.SetProgressor("step", "Importing attribute data for " + Number_Format(featureCnt, 0, True) + " polygons", 0, featureCnt, step)

        columnNames.insert(0, "SHAPE@AREA")
        columnNames.append("acres")
        outputSR = arcpy.SpatialReference(epsgWM)
        mukeyIndx += 1  # allow for addition of SHAPE@AREA

        #PrintMsg(" \nNumber of items in the input record: " + str(len(columnNames)), 1)

        with arcpy.da.UpdateCursor(outputShp, columnNames, spatial_reference=outputSR) as cur:
            for rec in cur:
                cnt += 1
                try:
                    mukey = rec[mukeyIndx]
                    
                    if not mukey == "":
                        areaM = rec[0]
                        newRec = [rec[0]]
                        newRec.extend(dMapunitInfo[mukey])
                        newRec.append(round((areaM / 4046.875), 1))  #
                        cur.updateRow(newRec)
                        #PrintMsg("\tOutput has " + str(len(rec)) + " values", 1)
                        #PrintMsg("\t" + str(newRec), 0)

                    #else:
                    #    PrintMsg(" \n\tFound nodata polygon in final layer", 0)

                    arcpy.SetProgressorPosition()

                except KeyError:
                    if not mukey in noMatch:
                        noMatch.append(mukey)

                except:
                    errorMsg()

        if len(noMatch) > 0:
            PrintMsg(" \nNo attribute data for mukeys: " + str(noMatch), 1)

        msg = "\n\tFinished importing attribute data"
        arcpy.SetProgressorLabel(msg)
        PrintMsg(msg, 0)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return False

    except:
        errorMsg()
        return False



## ===================================================================================
def CreateOutputFC(theAOI):
    #
    # Given the path for the new output featureclass, create it as polygon and add required fields
    # Later it will be populated using a cursor

    try:
        # Setup output coordinate system (same as input AOI) and datum transformation.
        # Please note! Only handles WGS1984 and NAD1983 datums.
        outputCS = arcpy.Describe(theAOI).spatialReference
        # These next two lines set the output coordinate system environment

        env.geographicTransformations = tm

        outputSoils = os.path.join("IN_MEMORY", "SoilPoly")

        # Create empty polygon featureclass
        arcpy.CreateFeatureclass_management(os.path.dirname(outputSoils), os.path.basename(outputSoils), "POLYGON", "", "DISABLED", "DISABLED", outputCS)

        arcpy.AddField_management(outputSoils,"mukey", "TEXT", "", "", "30")   # for outputShp

        #tmpFields = arcpy.Describe(outputShp).fields
        #tmpList = list()
        #for fld in tmpFields:
        #    tmpList.append(fld.name)

        #PrintMsg(" \nPermanent fields: " + ", ".join(tmpList), 1)
        if not arcpy.Exists(outputSoils):
            raise MyError, "Failed to create " + outputSoils

        return outputSoils

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def FormSpatialQuery(aoiDiss, x):
    #
    # Create a simplified polygon from the input polygon using convex-hull.
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    # The clipPolygon will be used to clip the soil polygons back to the original AOI polygon
    #
    # Note. SDA will accept WKT requests for MULTIPOLYGON if you make these changes:
    #     Need to switch the initial query AOI to use STGeomFromText and remove the
    #     WKT search and replace for "MULTIPOLYGON" --> "POLYGON".
    #
    # I tried using the MULTIPOLYGON option for the original AOI polygons but SDA would
    # fail when submitting AOI requests with large numbers of vertices. Easiest just to
    # using convex hull polygons and clip the results on the client side.

    try:
        bParts = False  

        gcs = arcpy.SpatialReference(epsgWGS84)
        i = 0
        wkt = ""
        partName = ""
        bParts = False  # FIX THIS LATER IF UNION WORKS

        if bParts:
            if bProjected:
                # Project geometry from AOI

                with arcpy.da.SearchCursor(theAOI, ["SHAPE@", "PARTNAME"]) as cur:
                    for rec in cur:
                        if i == x:
                            #polygon = rec[0].convexHull()                    # simplified geometry
                            polygon, partName = rec                                  # original geometry
                            outputPolygon = polygon.projectAs(gcs, tm)        # simplified geometry, projected to WGS 1984
                            #clipPolygon = rec[0].projectAs(gcs, tm)           # original geometry projected to WGS 1984
                            wkt = outputPolygon.WKT
                            break
                        
                        i += 1

            else:
                # No projection required. AOI must be GCS WGS 1984

                with arcpy.da.SearchCursor(theAOI, ["SHAPE@", "PARTNAME"]) as cur:
                    for rec in cur:
                        if i == x:
                            #polygon = rec[0].convexHull()                     # simplified geometry
                            polygon, partName = rec                                  # try original geometry instead of convex hull
                            #clipPolygon = rec[0]                              # original geometry
                            wkt = polygon.WKT
                            break
                        
                        i += 1

        else:

            if bProjected:
                # Project geometry from AOI

                with arcpy.da.SearchCursor(aoiDiss, ["SHAPE@"]) as cur:
                    for rec in cur:
                        if i == x:
                            #polygon = rec[0].convexHull()                    # simplified geometry
                            polygon = rec[0]                                  # original geometry
                            outputPolygon = polygon.projectAs(gcs, tm)        # simplified geometry, projected to WGS 1984
                            #clipPolygon = rec[0].projectAs(gcs, tm)           # original geometry projected to WGS 1984
                            wkt = outputPolygon.WKT
                            break
                        
                        i += 1

            else:
                # No projection required. AOI must be GCS WGS 1984

                with arcpy.da.SearchCursor(aoiDiss, ["SHAPE@"]) as cur:
                    for rec in cur:
                        if i == x:
                            #polygon = rec[0].convexHull()                     # simplified geometry
                            polygon = rec[0]                                  # try original geometry instead of convex hull
                            #clipPolygon = rec[0]                              # original geometry
                            wkt = polygon.WKT
                            break
                        
                        i += 1


            
        if wkt == "":
            raise MyError, "Failed to create WKT coordinates"

        # Strip "MULTI" off as well as leading and trailing (). Not sure why SDA doesn't like MULTIPOLYGON.
        wkt = wkt.replace("MULTIPOLYGON (", "POLYGON ")[:-1]

        #PrintMsg(" \nOriginal wkt: \n " + wkt , 1)
        
        # Testing multiple polygons with partname
        # Required parameters:
        

        sdaQuery2 = """
~DeclareGeometry(@aoi)~
select @aoi = geometry::STPolyFromText('""" + wkt + """', 4326)

-- Extract all intersected polygons
~DeclareIdGeomTable(@intersectedPolygonGeometries)~
~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

-- Return WKT for the polygonal geometries
select * from @intersectedPolygonGeometries where geom.STGeometryType() = 'Polygon'
"""

        #if bVerbose:
        #    PrintMsg(" \nSpatial Query: \n" + sdaQuery, 1)

        return sdaQuery2

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return "", None

    except:
        errorMsg()
        return "", None


## ===================================================================================
def RunSpatialQueryJSON(theURL, spatialQuery, outputSoils):
    #
    # JSON format
    #
    # Send spatial query to SDA Tabular Service
    #
    # Format JSON table containing records with MUKEY and WKT Polygons to a polygon featureclass
    #
    # Currently problems with JSON format using POST REST.
    # MaxJsonLength is appparently set to the default value of 102,400 characters. Need to set to Int32.MaxValue?
    # This limit does not affect the XML option.

    try:
        # Tabular service to append to SDA URL
        # https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest
        #url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        url = theURL + "/" + "Tabular/post.rest"

        #PrintMsg(" \n\tProcessing spatial request using " + url + " with JSON output", 1)
        #PrintMsg(" \n" + spatialQuery, 1)

        dRequest = dict()
        dRequest["format"] = "JSON"
        #dRequest["format"] = "'JSON + METADATA + COLUMN"
        dRequest["query"] = spatialQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)
        if bVerbose:
            PrintMsg(" \nURL: " + url)
            PrintMsg("format: " + "JSON")
            PrintMsg("query: " + spatialQuery)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)

        #try:
        resp = urllib2.urlopen(req)  # A failure here will probably throw an HTTP exception

        #except:
        responseStatus = resp.getcode()
        responseMsg = resp.msg

        jsonString = resp.read()
        resp.close()

        try:
            data = json.loads(jsonString)
            #PrintMsg(" \n" + str(data) + " \n ", 1)

        except:
            errorMsg()
            raise MyError, "Spatial Request failed"

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        if bVerbose:
            PrintMsg(" \nGeometry in JSON format from SDA: \n " + str(data), 1 )

        del jsonString, resp, req

        # Get coordinate system information for input and output layers
        outputCS = arcpy.Describe(outputSoils).spatialReference

        # The input coordinate system for data from SDA is GCS WGS 1984.
        # My understanding is that ArcGIS will not use it if it is not needed.
        inputCS = arcpy.SpatialReference(epsgWGS84)

        # Currently limited to GCS WGS1984 or NAD1983 datums
        validDatums = ["D_WGS_1984", "D_North_American_1983"]

        if not (inputCS.GCS.datumName in validDatums and outputCS.GCS.datumName in validDatums):
            raise MyError, "Valid coordinate system datums are: " + ", ".join(validDatums)

        # Only two fields are used initially, the geometry and MUKEY
        outputFields = ["SHAPE@", "MUKEY"]

        # Problem with output polygon featureclass. Being overwritten?
        #inCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        #PrintMsg(" \n\tOutput featureclass has " + Number_Format(inCnt, 0, True) + " polygons", 1)

        PrintMsg(" \n\tImporting " + Number_Format(len(dataList), 0, True) + " soil polygons...", 0)

        polyCnt = 0
        
        if len(dataList) > 20:
            step = len(dataList) / 10

        else:
            step = 1

        arcpy.SetProgressor("step", "Importing spatial data ", 0, len(dataList), step)


        if bProjected:
            # Project geometry to match input AOI layer
            #
            with arcpy.da.InsertCursor(outputSoils, outputFields) as cur:

                for rec in dataList:
                    #PrintMsg("\tOutput record " + str(polyCnt) + ": ", 0)
                    #PrintMsg(str(rec), 1)
                    mukey, wktPoly = rec
                    
                    if mukey is None:
                        PrintMsg(" \nFound nodata polygon in soils layer", 1)

                    if not mukey is None and not mukey == '':
                        # immediately create GCS WGS 1984 polygon from WKT
                        newPolygon = arcpy.FromWKT(wktPoly, inputCS)
                        outputPolygon = newPolygon.projectAs(outputCS, tm)

                        # Write geometry and mukey to output featureclass
                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                        #if showStatus:
                        arcpy.SetProgressorPosition()

        else:
            # No projection necessary. Input and output coordinate systems are the same.
            #
            with arcpy.da.InsertCursor(outputSoils, outputFields) as cur:

                for rec in dataList:
                    #PrintMsg("\trec: " + str(rec), 1)
                    mukey, wktPoly = rec
                    
                    if mukey is None:
                        PrintMsg(" \nFound nodata polygon in soils layer", 1)
                        
                    if not mukey is None and not mukey == '':

                        # immediately create polygon from WKT
                        newPolygon = arcpy.FromWKT(wktPoly, inputCS)
                        rec = [newPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1
                        #arcpy.SetProgressorLabel("Imported polygon " +  str(polyCnt))

                        #if showStatus:
                        arcpy.SetProgressorPosition()

            
        # Problem with output polygon featureclass. Being overwritten?
        #inCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        #PrintMsg(" \n\tOutput featureclass now has " + Number_Format(inCnt, 0, True) + " polygons", 1)

        time.sleep(1)
        #arcpy.ResetProgressor()
        arcpy.SetProgressorLabel("")


        return polyCnt


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except urllib2.HTTPError, e:
        # Currently the messages coming back from the server are not very helpful.
        # Bad Request could mean that the query timed out or tried to return too many JSON characters.
        #
        if hasattr(e, 'msg'):
            PrintMsg("HTTP Error: " + str(e.msg), 2)
            return 0

        elif hasattr(e, 'code'):
            PrintMsg("HTTP Error: " + str(e.code), 2)
            return 0

        else:
            PrintMsg("HTTP Error? ", 2)
            return 0

    except:
        errorMsg()
        return 0


## ===================================================================================
def AddFirstSoilMap(outputFC, newLayerFile, musyms):
    # Create the top layer which will be simple black outline, no fill with MUSYM labels, visible
    # Run SDA query to add NATMUSYM and MAPUNIT NAME to featureclass
    try:

        #mapLayerName = "Soil Map"
        labelField = "musym"

        # 5. Update layerDefinition dictionary for this map layer


        #mapLayers = arcpy.mapping.ListLayers(mxd, "*", df)

        #for layer in mapLayers:
        #    PrintMsg(" \tMap Layer: " + layer.name, 1)

        newLayer = arcpy.mapping.Layer(newLayerFile)  #fix this
        newLayer.name = newLayerName  # from global variable

        #newLayer.description = summary
        newLayer.visible = True
        newLayer.transparency = 50
        #newLayer.showLabels = False

        bZoomed = ZoomToExtent(newLayer)

        # Update soilmap layer symbology using JSON dictionary
        installInfo = arcpy.GetInstallInfo()
        version = str(installInfo["Version"])
        bLabeled = AddLabels(newLayer, labelField, True, 10)
        
        if version[0:4] in ["10.3", "10.4", "10.5"]:
            #PrintMsg(" \n\tUpdating symbology using JSON string", 1)

            # Update layer symbology using JSON
            #dLayerDefinition = SimpleFeaturesJSON()  # polygon outlines only
            dLayerDefinition = UniqueValuesJSON(musyms, True, labelField) # polygon fill, semi-transparent
            newLayer.updateLayerFromJSON(dLayerDefinition)
            #PrintMsg(" \n" + str(dLayerDefinition), 1)

        arcpy.mapping.AddLayer(df, newLayer, "TOP")  # add soil map layer to group layer

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

            newExtent = inputLayer.getExtent()

            # Expand the extent by 10%
            xOffset = (newExtent.XMax - newExtent.XMin) * 0.05
            yOffset = (newExtent.YMax - newExtent.YMin) * 0.05
            newExtent.XMin = newExtent.XMin - xOffset
            newExtent.XMax = newExtent.XMax + xOffset
            newExtent.YMin = newExtent.YMin - yOffset
            newExtent.YMax = newExtent.YMax + yOffset

            df.extent = newExtent
            #dfScale = df.scale
            #PrintMsg(" \nZoomToExtent Data frame scale is  1:" + Number_Format(df.scale, 0, True), 1)

        except:
            # Leave labels turned off for thematic map layers
            errorMsg()
            return False

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def AddLabels(inputLayer, labelField, bLabeled, fontSize):
    # Set layer label properties to use MUSYM
    # Some layers we just want to set the label properties to use MUSYM, but
    # we don't want to display the labels.

    try:

        # Add mapunit symbol (MUSYM) labels
        desc = arcpy.Describe(inputLayer)
        fields = desc.fields
        fieldNames = [fld.name.lower() for fld in fields]

        if not labelField.lower() in fieldNames:
            raise MyError, labelField + " not found in " + inputLayer
        
        if inputLayer.supports("LABELCLASSES"):
            inputLayer.showClassLabels = True
            labelCls = inputLayer.labelClasses[0]
            oldLabel = labelCls.expression

            if fontSize > 0:
                #labelCls.expression = "<BOL> & [" + labelField + "] & </BOL>"
                # "<FNT size= '15'>" & [partname] & "</FNT>"
                s1 = '"<FNT size=' + "'" + str(fontSize) + "'>\""
                s2 = " & [" + labelField + "] & " + '"</FNT>"'
                labelString = '"<FNT size=' + "'" + str(fontSize) + "'>\"" + " & [" + labelField + "] & " + '"</FNT>"'
                labelCls.expression = labelString
                #labelCls.expression = "<FNT size= '" + str(fontSize) + "'> & [" + labelField + "] & </FNT>"

            else:
                labelCls.expression = "[" + labelField + "]"

        else:
            PrintMsg(" \n\tLayer " + inputLayer.name + " does not support labelclasses", 1)

        if df.scale <= 18000 and bLabeled:
            #PrintMsg(" \n\tTurning labels on at display scale of 1:" + str(Number_Format(df.scale, 0, True)), 1)
            inputLayer.showLabels = True

        else:
            #PrintMsg(" \n\tTurning labels off at display scale of 1:" + str(Number_Format(df.scale, 0, True)), 1)
            inputLayer.showLabels = False
            
        #PrintMsg(" \nIn AddLabels, the scale is: " + str(df.scale), 1)


        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def SimpleFeaturesJSON():
    # returns JSON string for soil lines and labels layer.
    #
    try:

        outLineColor = [0, 0, 0, 255]  # black polygon outline

        d = dict()
        r = dict()

        r["type"] = "simple"
        s = {"type": "esriSFS", "style": "esriSFSNull", "color": [255,255,255,255], "outline": { "type": "esriSLS", "style": "esriSLSSolid", "color": [0, 0, 0,255], "width": 2.0 }}
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
def UniqueValuesJSON(ratingValues, drawOutlines, ratingField):
    # returns Python dictionary for unique values template. Use this for text, choice, vtext.
    #
    # Problem: Feature layer does not display the field name in the table of contents just below
    # the layer name. Possible bug in UpdateLayerFromJSON method?
    try:
        d = dict() # initialize return value

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]
            waterColor = [64, 101, 235, 100]

        else:
            outLineColor = [110, 110, 110, 255]
            waterColor = [64, 101, 235, 255]

        ratingValues.sort()
            

        d = dict()
        #d["currentVersion"] = 10.1
        #d["id"] = 0
        #d["name"] = ""
        #d["type"] = "Feature Layer"
        d["drawingInfo"] = dict()
        d["drawingInfo"]["renderer"] = dict()
        d["fields"] = list()
        #d["name"] = ratingField.title()
        d["displayField"] = ratingField  # This doesn't seem to work

        d["drawingInfo"]["renderer"]["fieldDelimiter"] = ", "
        d["drawingInfo"]["renderer"]["defaultSymbol"] = None
        d["drawingInfo"]["renderer"]["defaultLabel"] = None

        d["drawingInfo"]["renderer"]["type"] = "uniqueValue"
        d["drawingInfo"]["renderer"]["field1"] = ratingField
        d["drawingInfo"]["renderer"]["field2"] = None
        d["drawingInfo"]["renderer"]["field3"] = None
        d["displayField"] = ratingField       # This doesn't seem to work
        #PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)

        # Add new rating field to list of layer fields
        dAtt = dict()
        dAtt["name"] = ratingField
        dAtt["alias"] = ratingField + " alias"
        dAtt["type"] = "esriFieldTypeString"
        d["fields"].append(dAtt)              # This doesn't seem to work

        #try:
        #    length = ratingLength

        #except:
        #    length = 254

        #dAtt["length"] = length

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        for cnt in range(0, len(ratingValues)):
            rating = ratingValues[cnt]

            if rating == 'W':
                # Water symbol
                rgb = [151,219,242,255]
                #PrintMsg(" \nRGB: " + str(rgb), 1)
                legendItems = dict()
                legendItems["value"] = rating
                legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
                legendItems["label"] = str(rating)
                symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": waterColor, "width": 1.5, "style": "esriSLSSolid", "type": "esriSLS"}}
                legendItems["symbol"] = symbol
                #d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : ratingField, "field2" : None, "field3" : None}
                uniqueValueInfos.append(legendItems)       

            else:
                # calculate rgb colors
                rgb = [randint(0, 255), randint(0, 255), randint(0, 255), 255]

                #PrintMsg(" \nRGB: " + str(rgb), 1)
                legendItems = dict()
                legendItems["value"] = rating
                legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
                legendItems["label"] = str(rating)
                symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}
                legendItems["symbol"] = symbol
                #d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : ratingField, "field2" : None, "field3" : None}
                uniqueValueInfos.append(legendItems)

        d["drawingInfo"]["renderer"]["uniqueValueInfos"] = uniqueValueInfos
        #PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)
        #PrintMsg(" \nuniqueValueInfos: " + str(d["drawingInfo"]["renderer"]["uniqueValueInfos"]), 1)
        #PrintMsg(" \n" + str(d), 1)

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return d

    except:
        errorMsg()
        return d

## ===================================================================================
def AddFieldMap(aoiPolys, mxd, df):
    # Add AOI layer with PartName labels to ArcMap display
    #
    try:
        PrintMsg(" \naoiPolys: " + aoiPolys, 1)
        
        boundaryLayerName = "AOI_Boundaries"
        boundaryLayerFile = os.path.join(env.scratchFolder, "AOI_Boundary.lyr")
        arcpy.MakeFeatureLayer_management(aoiPolys, boundaryLayerName)
        arcpy.SaveToLayerFile_management(boundaryLayerName, boundaryLayerFile, "ABSOLUTE")
        aoiLayer = arcpy.mapping.Layer(boundaryLayerFile)
        dLayerDefinition = SimpleFeaturesJSON()
        aoiLayer.updateLayerFromJSON(dLayerDefinition)
        bLabeled = AddLabels(aoiLayer, "partname", True, 14)
        #arcpy.Delete_management(boundaryLayerName)

        if bLabeled:
            #arcpy.mapping.AddLayer(df, aoiLayer, "TOP")
            return True

        else:
            return False
    
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
import sys, string, os, arcpy, locale, traceback, urllib2, httplib, webbrowser, subprocess, json, collections

from arcpy import env
from copy import deepcopy
from random import randint

try:
    # Read input parameters
    inputAOI = arcpy.GetParameterAsText(0)                   # input AOI feature layer
    featureCnt = arcpy.GetParameter(1)                        # String. Number of polygons selected of total features in the AOI featureclass.
    sQueryFile = arcpy.GetParameterAsText(2)   # Text file containing FSA soils
    bDissolve = arcpy.GetParameter(3)                         # User does not want to keep individual polygon or field boundaries
    outputShp = arcpy.GetParameterAsText(4)                         # Output soils featureclass
    bVerbose = False

    sdaURL = r"https://sdmdataaccess.sc.egov.usda.gov"
    #outputZipfile = r"c:\temp"
    bClean = False  # hardcode this for now
    timeOut = 0
    env.overwriteOutput= True
    env.addOutputsToMap = False

    # Read SQL query from file. Use 'xxMUKEYSxx' to represent a list of mukey values
    PrintMsg(" \nUsing query in file: " + sQueryFile, 0)
    dirName = os.path.dirname(sQueryFile)
    
    if dirName == "":
        sQueryFile = os.path.join(os.path.dirname(sys.argv[0]), sQueryFile)

    if arcpy.Exists(sQueryFile):
        fh = open(sQueryFile, "r")
        sQuery = fh.read()
        fh.close()
        #PrintMsg(" \nsQuery: " + sQuery + " \n ", 1)

    else:
        raise MyError, "Query file not found: " + sQueryFile
    
    maxString = 250000

    if len(sQuery) > maxString:
        raise MyError, "Check input query string for truncation beyond " + Number_Format(maxString, 0, True)
    

    # Commonly used EPSG numbers
    epsgWM = 3857 # Web Mercatur
    epsgWGS84 = 4326 # GCS WGS 1984
    epsgNAD83 = 4269 # GCS NAD 1983
    epsgAlbers = 102039 # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
    #tm = "WGS_1984_(ITRF00)_To_NAD_1983"  # datum transformation supported by this script



    # Get geographic coordinate system information for input and output layers
    validDatums = ["D_WGS_1984", "D_North_American_1983"]
    desc = arcpy.Describe(inputAOI)
    aoiCS = desc.spatialReference
    aoiName = os.path.basename(desc.nameString)

    if not aoiCS.GCS.datumName in validDatums:
        raise MyError, "AOI coordinate system not supported: " + aoiCS.name + ", " + aoiCS.GCS.datumName

    if aoiCS.GCS.datumName == "D_WGS_1984":
        tm = ""  # no datum transformation required

    elif aoiCS.GCS.datumName == "D_North_American_1983":
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"

    else:
        raise MyError, "AOI CS datum name: " + aoiCS.GCS.datumName

    sdaCS = arcpy.SpatialReference(epsgWGS84)

    # Determine whether
    if aoiCS.PCSName != "":
        # AOI layer has a projected coordinate system, so geometry will always have to be projected
        bProjected = True

    elif aoiCS.GCS.name != sdaCS.GCS.name:
        # AOI must be NAD 1983
        bProjected = True

    else:
        bProjected = False

        

    licenseLevel = arcpy.ProductInfo().upper()
    
    if licenseLevel != "ARCINFO":
        raise MyError, "License level must be Advanced to run this tool"


    # Create empty output featureclass
    outputSoils = CreateOutputFC(inputAOI)

    if outputSoils == "":
        raise MyError, ""

    # Define temporary featureclasses
    aoiShp = os.path.join(env.scratchFolder, "myaoi.shp")

    if arcpy.Exists(aoiShp):
        arcpy.Delete_management(aoiShp, "FEATURECLASS")

    tmpFolder = "IN_MEMORY"
    dissShp = os.path.join(tmpFolder, "aoi_diss")

    # Reformat AOI layer if needed and create a version with just the outer boundary (dissShp)
    # This simpler shapefile will be used to send the spatial request to SDA,
    # and then if partname exists, the aoiShp will be unioned with the outputSoils layer.
    #
    bReady = PrepareAOI(inputAOI, bDissolve, bClean, aoiShp, dissShp)

    if bReady:
        polyCnt = int(arcpy.GetCount_management(dissShp).getOutput(0))
        fieldNames = [fld.name.upper() for fld in arcpy.Describe(aoiShp).fields]
                                                    
        if "PARTNAME" in fieldNames:
            bParts = True
            #PrintMsg(" \naoi shapefile has partname, skipping", 1)
            #arcpy.AddField_management(outputShp, "partname", "TEXT", "", "", 20)
                                        
        else:
            bParts = False

        PrintMsg(" \nCreating AOI layer with " + str(polyCnt) + " polygons", 0)

        for i in range(polyCnt):
            #PrintMsg(" \nUsing " + aoiShp + " to request soils data from SDA", 0)
            # Create spatial query string using simplified polygon coordinates
            spatialQuery = FormSpatialQuery(dissShp, i)

            if spatialQuery != "":
                # Send spatial query and use results to populate outputShp featureclass
                outCnt = RunSpatialQueryJSON(sdaURL, spatialQuery, outputSoils)

                if outCnt == 0:
                    PrintMsg(" \nFailed spatial query: \n " + spatialQuery, 1)
                    raise MyError, ""

            else:
                raise MyError, "Empty spatial query, unable to retrieve soil polygons"

        env.addOutputsToMap = False


        
        if bParts:
            # Union new soils layer with AOI boundary layer to incorporate partname attribute
            #
            aoiPolys = os.path.join(os.path.dirname(outputShp), "aoiPolys")
            arcpy.CopyFeatures_management(aoiShp, aoiPolys)
            PrintMsg(" \n\tAdding AOI attributes to soils layer...", 0)
            arcpy.Union_analysis([outputSoils, aoiShp], outputShp, "ALL", "", "NO_GAPS")
            desc = arcpy.Describe(outputShp)
            fieldNames = [fld.name.upper() for fld in desc.fields]

            # Delete extraneous fields from gdb featureclass
            if "FID_SOILPOLY" in fieldNames:
                #PrintMsg("Fld1", 1)
                arcpy.DeleteField_management(outputShp, "FID_SOILPOLY")

            if "FID_MYAOI" in fieldNames:
                #PrintMsg("Fld2", 1)
                arcpy.DeleteField_management(outputShp, "FID_MYAOI")

                
            # Delete extraneous fields from shapefile
            if "FID_SOILPO" in fieldNames:
                #PrintMsg("Fld3", 1)
                arcpy.DeleteField_management(outputShp, "FID_SOILPO")

        else:
            arcpy.CopyFeatures_management(outputSoils, outputShp)

        desc = arcpy.Describe(outputShp)

        # I wonder if I should be creating this layerfile further down, after the attributes have been added?
        #
        newLayerName = "SDA Soil Map"
        #PrintMsg(" \nNew featurelayer name: " + newLayerName, 1)
        arcpy.MakeFeatureLayer_management(outputShp, newLayerName)
        arcpy.SetParameter(3, "")
        #time.sleep(10)
        layerFile = os.path.join(env.scratchFolder, "soilmaplayer.lyr")
        arcpy.SaveToLayerFile_management(newLayerName, layerFile, "ABSOLUTE")
        arcpy.Delete_management(newLayerName)
        arcpy.Delete_management(outputSoils)

        if arcpy.Exists(dissShp):
            arcpy.Delete_management(dissShp)

        if arcpy.Exists(aoiShp):
            arcpy.Delete_management(aoiShp)

        # Get attribute data from Soil Data Access0
        # Get list of mukeys for the attribute query
        mukeys = GetMukeys(outputShp)

        if len(mukeys) > 0:
            sQuery = FormAttributeQuery(sQuery, mukeys)
        
            if sQuery != "":
                #time.sleep(10)
                bAtts = AttributeRequest(sdaURL, mukeys, outputShp, sQuery)

                if bAtts:
                    try:
                        # Get list of musyms for map legend
                        musyms = list()
                        
                        with arcpy.da.SearchCursor(outputShp, ["musym"]) as cur:
                            for rec in cur:
                                if not rec[0] is None:
                                    musym = rec[0].encode('ascii')
                                    
                                    if not musym == "" and not musym in musyms:
                                        musyms.append(musym)

                        # Add new map layers
                        #
                        # Try to turn off off highlighted AOI layer so they don't obscure the new output layers
                        PrintMsg(" \nAdding new map layers...", 0)
                        mxd = arcpy.mapping.MapDocument("CURRENT")
                        df = mxd.activeDataFrame
                  
                        selLayer = arcpy.mapping.ListLayers(mxd, inputAOI, df)[0]
                        #selLayer.setVisible = False  # This method does not seem to work with Web Feature Service??
                        arcpy.SelectLayerByAttribute_management(selLayer, "CLEAR_SELECTION")
                        selLayer.visible = False

                        # New soil map layer
                        PrintMsg("\tSoil map", 0)
                        bMapped = AddFirstSoilMap(newLayerName, layerFile, musyms)

                        # Create aoi boundary map layer using aoiPolys featureclass
                        if bMapped and bParts:
                            if arcpy.Exists(aoiPolys):
                                # new AOI layer
                                PrintMsg("\tAOI layer", 0)
                                bFields = AddFieldMap(aoiPolys, mxd, df)

                    except:
                        errorMsg()
                        del mxd, df
        
    PrintMsg(" \n ", 0)
                    
except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
