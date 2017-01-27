# SDA_SpatialQuery.py
#
# Steve Peaslee, National Soil Survey Center, August 2016
#
# Purpose:  Demonstration ArcTool for ArcMap, designed to query the Soil Data Access Tabular service
# for both spatial and attribute data and then import that data into a file geodatabase featureclass.
# A map layer for available water storage will be created and added to ArcMap.
# The Tabular service uses a MS SQLServer database. Both spatial and attribute queries
#
# The script can cycle through and query for each AOI polygon so that it
# will better handle widely disparate polygons.
# Only handles coordinate systems with NAD1983 or WGS1984 datums.
#
# Maybe add Harn transformations?
#
# Need to put in a limit for input polygons. Selecting an input with a large number
# of polygons can appear to hang the system.
#
# Need to test Pipeline AOI with bends to see if convex hull will help.
#
# My initial attempt to add COLUMN and METADATA to the SDA Format failed. Need to consult with Phil.
#
# EPSG Reference
# Web Mercatur: 3857
# GCS WGS 1984: 4326
# GCS NAD 1983: 4269
# Albers USGS CONUS: 32145
#
# Input parameters
#
# theAOI = arcpy.GetParameterAsText(0)     # polygon layer (honors selected set) used to define AOI
# outputShp = arcpy.GetParameterAsText(1)  # output soil polygon featureclass (GDB)
# top = arcpy.GetParameter(2)              # top horizon depth (cm)
# bot = arcpy.GetParameter(3)              # bottom horizon depth (cm)
# transparency = arcpy.GetParameter(4)     # transparency level for the output soils layer
# maxAcres = arcpy.GetParameter(5)         # maximum allowed area for the spatial query.
# sdaURL = arcpy.GetParameterAsText(6)     # Soil Data Access URL

#
## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #print msg
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
        PrintMsg("Unhandled error in unHandledException method", 2)
        pass

## ===================================================================================
def CountVertices(theInputLayer, bUseSelected):
    # Process either the selected set or the entire featureclass into a single set of summary statistics
    # bUseSelected determines whether the featurelayer or featureclass gets processed

    try:

        # Describe input layer
        desc = arcpy.Describe(theInputLayer)
        theDataType = desc.dataType.lower()

        if theDataType == "featurelayer":
            theInputName = desc.nameString

        else:
            theInputName = desc.baseName

        theFC = desc.catalogPath
        featureType = desc.shapeType.lower()
        iVertCnt = 0
        PrintMsg(" \nProcessing input " + featureType + " " + theDataType.lower() + " '" + theInputName + "'", 0)
        iParts = 0

        if bUseSelected:
            # Process input (featurelayer?)
            # open cursor with exploded geometry
            PrintMsg("If selected set or query definition is present, only those features will be processed", 0)

            with arcpy.da.SearchCursor(theInputLayer, ["OID@","SHAPE@"], "","",False) as theCursor:
                for fid, feat in theCursor:

                    if not feat is None:
                        iVertCnt += feat.pointCount
                        iParts += feat.partCount

                    else:
                        PrintMsg("Empty geometry found for polygon #" + str(fid) + " \n ", 2)
                        return -1


            PrintMsg(" \n" + Number_Format(iVertCnt, 0, True) + " vertices in featurelayer \n " , 0)

        else:
            # Process all polygons using the source featureclass regardless of input datatype.
            # Don't really see a performance difference, but this way all features get counted.
            # Using 'exploded' geometry option for cursor

            with arcpy.da.SearchCursor(theFC, ["OID@","SHAPE@"], "","",False) as theCursor:
                for fid, feat in theCursor:

                    if not feat is None:
                      iVertCnt += feat.pointCount
                      iParts += feat.partCount

                    else:
                        raise MyError, "NULL geometry for polygon #" + str(fid)

            PrintMsg(" \n" + Number_Format(iVertCnt, 0, True) + " vertices present in the entire " + theDataType.lower() + " \n ", 0)


        return iVertCnt


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)
        return -1

    except:
        errorMsg()
        return -1

## ===================================================================================
def LayerDensity(theLayer):
    # Compare actual layer polygon size to layer extent
    # This ratio will be used to determine whether SDA spatial
    # requests will be on a per-polygon-basis or for the entire extent
    #
    # FYI. Layer coordinate systems can be different, depending upon how you reference the layer.
    # layer is an arcpy.mapping Layer
    # DF SR = GCS WGS1984
    # Layer SR = "Albers EA CONUS USGS"
    #
    # layer.getExtent() returns an extent object with GCS WGS1984 coordinates, matching the data frame
    # layer.getSelectedExtent() also returns an extent object with a GCS WGS1984 coordinates
    #
    #
    try:
        polyArea = 0.0
        polyAcres = 0.0
        polyCnt = 0
        vertCnt = 0
        desc = arcpy.Describe(theLayer)
        cs = desc.spatialReference
        dfcs = df.spatialReference

        extent = theLayer.getSelectedExtent(False)
        #extent = desc.extent

        # Get acres within the extent using the layer coordinate system
        pointArray = arcpy.Array([arcpy.Point(extent.XMin, extent.YMin), arcpy.Point(extent.XMin, extent.YMax), arcpy.Point(extent.XMax, extent.YMax), arcpy.Point(extent.XMax, extent.YMin)])
        # , arcpy.Point(extent.XMin, extent.YMin)
        #PrintMsg(" \n" + str(extent.XMin) + " " + str(extent.YMin) + ", " + str(extent.XMin) + " " + str(extent.YMax) + ", " + str(extent.XMax) + " " + str(extent.YMax) + ", " + str(extent.XMax) + " " + str(extent.YMin), 0)
        polygon = arcpy.Polygon(pointArray, dfcs, False, False)
        extentAcres = polygon.getArea("GREAT_ELLIPTIC", "ACRES")
        extentArea = polygon.area

        #PrintMsg("Input AOI extent acres using getArea() and " + dfcs.name + ": " + Number_Format(extentAcres, 1, True))

        with arcpy.da.SearchCursor(theLayer, ["SHAPE@"], "", dfcs) as cur:
            for rec in cur:
                polyCnt += 1
                polyArea += rec[0].getArea("GREAT_ELLIPTIC", "SQUAREMETERS")
                polyAcres += rec[0].getArea("GREAT_ELLIPTIC", "ACRES")
                #polyArea += rec[0].area
                vertCnt += rec[0].pointCount


        #density = extentArea / polyArea
        density = extentAcres / polyAcres
        #PrintMsg("Extent area " + Number_Format(extentArea, 1, True), 0)
        PrintMsg("\tAOI Acres: " + Number_Format(polyAcres, 0, True), 0)
        PrintMsg("\tPolygon count: " + Number_Format(polyCnt, 0, True), 0)
        PrintMsg("\tVertex count: " + Number_Format(vertCnt, 0, True), 0)
        PrintMsg("\tLayer Density: " + Number_Format(density, 0, True), 0)

        return polyArea, polyAcres, polyCnt, vertCnt, density

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0, 0, 0, 0

    except:
        errorMsg()
        return 0, 0, 0, 0


## ===================================================================================
def ClipToAOI(theAOI, outputShp):
    # Clip intersected soils layer using original AOI polygons
    #
    try:
        #
        #
        outputWS = os.path.dirname(outputShp)
        outputName = os.path.basename(outputShp)
        clippedFC = os.path.join(outputWS, "ClippedSoils")
        #
        if arcpy.Exists(clippedFC):
            arcpy.Delete_management(clippedFC)

        PrintMsg(" \nClipping initial dataset to final AOI", 0)
        arcpy.Clip_analysis(outputShp, theAOI, clippedFC)

        if arcpy.Exists(clippedFC):
            arcpy.Delete_management(outputShp)
            arcpy.Rename_management(clippedFC, outputShp)
            return outputShp

        else:
            raise MyError, "Failed to clip output featureclass"


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputShp

    except:
        errorMsg()
        return ""

## ===================================================================================
def FinalDissolve(outputShp):
    # Dissolve the final output shapefile on MUKEY
    #
    try:
        #
        #
        outputWS = os.path.dirname(outputShp)
        outputName = os.path.basename(outputShp)
        dissolvedFC = os.path.join(outputWS, "DissolvedSoils")
        #
        if arcpy.Exists(dissolvedFC):
            arcpy.Delete_management(dissolvedFC)

        PrintMsg(" \nDissolving final soil layer", 0)
        arcpy.Dissolve_management(outputShp, dissolvedFC, ["MUKEY"], "", "SINGLE_PART")

        if arcpy.Exists(dissolvedFC):
            arcpy.Delete_management(outputShp)
            arcpy.Rename_management(dissolvedFC, outputShp)
            return outputShp

        else:
            raise MyError, "Failed to dissolve output featureclass"


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputShp

    except:
        errorMsg()
        return ""

## ===================================================================================
def SimplifyAOI_Diss(theAOI, inCnt):
    # Remove any interior boundaries from the selected AOI polygons.
    # This will allow multiple AOI bounding boxes to be submitted and then
    # reassembled on the client. Should also improve clipping time.
    #
    try:
        #
        #
        if inCnt > 1:
            # Try to dissolve the input AOI to simplify the geometry
            #PrintMsg(" \nUsing Dissolve method", 1)
            dissolvedFC = os.path.join(env.scratchGDB, "DissolvedAOI")
            #
            if arcpy.Exists(dissolvedFC):
                arcpy.Delete_management(dissolvedFC)

            arcpy.Dissolve_management(theAOI, dissolvedFC, "", "", "SINGLE_PART")

            outCnt = int(arcpy.GetCount_management(dissolvedFC).getOutput(0))

            if outCnt < inCnt:
                #PrintMsg(" \nOutput AOI has " + Number_Format(outCnt, 0, True) + " polygons", 1)
                result = arcpy.MakeFeatureLayer_management(dissolvedFC, os.path.basename(dissolvedFC))
                tmpAOI = result.getOutput(0)
                return tmpAOI, outCnt

            else:
                # Same number of polygons, just keep the original AOI
                return theAOI, inCnt

        else:
            # Assuming with one polygon there is nothing to dissolve. This method fails if
            # the input AOI consists of mulipart polygons.
            return theAOI, inCnt

    except:
        errorMsg()
        return theAOI, inCnt

## ===================================================================================
def SimplifyAOI_Hull(newAOI, inCnt):
    # Create a simplified bounding box using MinimumBoundingGeometry function.
    # This can be used to create a very simple geometry for the spatial query.
    #
    try:
        #
        # Try to create a single convex hull polygon outlining the multiple AOIs.
        # This will result in a simple spatial query for Soil Data Access
        #
        #outputWS = os.path.dirname(outputShp)
        #outputName = os.path.basename(outputShp)

        #PrintMsg(" \nInput layer for SimplifyAOI_Hull is " + newAOI.name, 1)
        convexHullFC = os.path.join(env.scratchGDB, "ConvexHullAOI")
        #
        if arcpy.Exists(convexHullFC):
            arcpy.Delete_management(convexHullFC)

        #PrintMsg(" \nUsing MinimumBoundingGeometry method", 1)
        arcpy.MinimumBoundingGeometry_management(newAOI, convexHullFC, "CONVEX_HULL", "ALL")

        outCnt = int(arcpy.GetCount_management(convexHullFC).getOutput(0))

        if outCnt <= inCnt:
            # Convex hull should be a single polygon
            #
            #PrintMsg(" \nOutput AOI has " + Number_Format(outCnt, 0, True) + " polygons", 1)
            #tmpAOI = "TmpAOI"
            #
            # Create a new featureclass using the convex hull polygon
            result = arcpy.MakeFeatureLayer_management(convexHullFC, os.path.basename(convexHullFC))
            tmpAOI = result.getOutput(0)
            #return tmpAOI, outCnt

            # Calculate acres for the convex hull
            hullAcres, polyCnt, vertCnt = GetLayerAcres(tmpAOI)

            # Make sure the convex hull polygon is not too big
            if hullAcres < maxAcres:
                # convex hull polygon should be OK
                PrintMsg(" \nCreated convex hull AOI polygon having " + Number_Format(hullAcres, 0, True) + " acres", 1)
                newAOI = tmpAOI
                inCnt = polyCnt
                return tmpAOI, polyCnt

            else:
                # Use the individual dissolved polygons instead
                arcpy.Delete_management(convexHullFC)
                arcpy.Delete_management(tmpAOI)
                PrintMsg(" \nSingle convex hull polygon too big, switching back to original dissolved layer", 1)
                return None, 0

        return None, 0


    except:
        errorMsg()
        return None, 0

## ===================================================================================
def AddNewFields(outputTbl, columnNames, columnInfo):
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

        for i, fldName in enumerate(columnNames):

            vals = columnInfo[i].split(",")

            length = int(vals[1].split("=")[1])
            precision = int(vals[2].split("=")[1])
            scale = int(vals[3].split("=")[1])
            dataType = dType[vals[4].lower().split("=")[1]]

            if not fldName.lower() == "mukey":
                arcpy.AddField_management(outputTbl, fldName, dataType, precision, scale, length)

            #isLong = vals[5].split("=")[1]
            #dataType = vals[6].split("=")[1]
            #dataTypeName = vals[7].split("=")[1]
            #fieldInfo.extend([length, precision, scale, type, isLong, dataType])
            #fieldInfo.extend([length, precision, scale])
            #newFields.append(fieldInfo)
            #PrintMsg(str(fieldInfo), 1)


        # Add required attribute fields
        #arcpy.AddField_management(outputTbl, "MUKEY", "TEXT", "", "", "30")   # for outputShp
        #arcpy.AddField_management(outputTbl, "MUSYM", "TEXT", "", "", "7")    # for outputShp
        #arcpy.AddField_management(outputTbl, "AREASYMBOL", "TEXT", "", "", "10")
        #arcpy.AddField_management(outputTbl, "AREANAME", "TEXT", "", "", "135")
        #arcpy.AddField_management(outputTbl, "MUNAME", "TEXT", "", "", "175")
        #arcpy.AddField_management(outputTbl, "PCT_SUM", "SHORT", "", "", "")
        #arcpy.AddField_management(outputTbl, "AWS", "FLOAT", "", "", "")
        #arcpy.AddIndex_management(outputTbl, ["MUKEY"], "Indx_Mukey_" + os.path.basename(outputTbl))

        if arcpy.Exists(outputTbl):
            return True

        else:
            return False

    except:
        errorMsg()
        return False


## ===================================================================================
def AttributeRequest(theURL, mukeyList, top, bot, outputShp):
    # Trying to convert original SOAP request to POST REST which uses urllib and JSON
    #
    # Send query to SDM Tabular Service, returning AWC data in XML format

    try:
        outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \nSending matching tabular request for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        #arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")
        fieldList = ['AREASYMBOL', 'AREANAME', 'MUKEY', 'MUSYM', 'MUNAME', 'COKEY', 'COMPNAME', 'LOCALPHASE', 'COMPPCT_R', 'HZNAME', 'HZDEPT_R', 'HZDEPB_R', 'AWC_R']

        mukeys = ",".join(mukeyList)
        depths = str(tuple(range(top, bot)))

        hzQuery = "hzdept_r between " + str(top) + " and " + str(bot - 1) + " or hzdepb_r between " + str(top) + " and " + str(bot)
        #hzQuery = "(ch.hzdept_r in " + depths + " or ch.hzdepb_r in " + depths + ") or (ch.hzdept_r < " + str(top) + " and ch.hzdepb_r > " + str(bot) + ")"

        sQuery = """select
        l.areasymbol,
        l.areaname,
        mu.mukey,
        mu.musym,
        mu.muname,
        co.cokey,
        co.compname,
        co.localphase,
        co.comppct_r,
        ch.hzname,
        ch.hzdept_r,
        ch.hzdepb_r,
        ch.awc_r as aws
        FROM
        legend l
        INNER JOIN mapunit mu ON mu.lkey = l.lkey and mu.mukey in (""" \
        + mukeys \
        + """)
        LEFT OUTER JOIN component co ON co.mukey = mu.mukey and co.comppct_r is not null
        LEFT OUTER JOIN chorizon ch ON ch.cokey = co.cokey and (""" + hzQuery + """)
        ORDER BY mu.mukey, co.comppct_r desc, co.cokey, ch.hzdept_r"""

        #PrintMsg(" \n" + sQuery, 0)

        # Tabular service to append to SDA URL
        url = theURL + "/Tabular/SDMTabularService/post.rest"
        #url = "http://SDMDataAccess.sc.egov.usda.gov/Tabular/SDMTabularService/post.rest"

        dRequest = dict()
        #dRequest["Host"] = theURL
        #dRequest["Content-Type"] = "application/json"
        dRequest["FORMAT"] = "JSON"  # data only
        dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"  # column information + data. Has 'null' placekeeper that has to be stripped. Everything except null is a double-quoted string.
        dRequest["QUERY"] = sQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        #PrintMsg(" \n" + jsonString, 1)
        data = json.loads(jsonString)


        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        bNewFields = AddNewFields(outputShp, columnNames, columnInfo)
        if bNewFields == False:
            raise MyError, ""

        #PrintMsg(" \n" + str(dataList[0]), 1)

        del jsonString, resp, req

        # Create temporary table to contain results of SDA tabular query
        # areasymbol, areaname, mukey, muysm, cokey, comppct_r,compname,hzname,hzdept_r,hzdepb_r,awc_r
        #
        PrintMsg(" \nSaving horizon level data...", 0)
        #arcpy.SetProgressorLabel("Saving horizon level data from Soil Data Access...")
        tmpTable = os.path.join(env.scratchGDB, "SDA_QueryTable")

        if arcpy.Exists(tmpTable):
            arcpy.Delete_management(tmpTable)

        # Create table to contain component-horizon level data
        arcpy.CreateTable_management(os.path.dirname(tmpTable), os.path.basename(tmpTable))
        arcpy.AddField_management(tmpTable, "AREASYMBOL", "TEXT", "", "", "20")
        arcpy.AddField_management(tmpTable, "AREANAME", "TEXT", "", "", "135")
        arcpy.AddField_management(tmpTable, "MUKEY", "TEXT", "", "", "30")
        arcpy.AddField_management(tmpTable, "MUSYM", "TEXT", "", "", "6")
        arcpy.AddField_management(tmpTable, "MUNAME", "TEXT", "", "", "175")
        arcpy.AddField_management(tmpTable, "COKEY", "TEXT", "", "", "30")
        arcpy.AddField_management(tmpTable, "COMPNAME", "TEXT", "", "", "60")
        arcpy.AddField_management(tmpTable, "LOCALPHASE", "TEXT", "", "", "40")
        arcpy.AddField_management(tmpTable, "COMPPCT_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "HZNAME", "TEXT", "", "", "12")
        arcpy.AddField_management(tmpTable, "HZDEPT_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "HZDEPB_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "AWC_R", "FLOAT", "", "", "")

        dataTypes = ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "INTEGER", "TEXT", "INTEGER", "INTEGER", "FLOAT"]  # not using this
        iCnt = 0
        firstFld = fieldList[0]
        lastFld = fieldList[-1]
        #dData = dict()

        # Begin writing query results (component-horizon data) to a temporary table
        # Data type conversion from JSON string to correct type is very awkward. Need to fix this somehow.
        #
        # If columnname and metadata are returned, the first two records in the Table will need to be stripped out,
        # and saved.

        """rec0 = [u'areasymbol', u'areaname', u'mukey', u'musym', u'muname', u'cokey', u'compname', u'localphase', u'comppct_r', u'hzname', u'hzdept_r', u'hzdepb_r', u'awc_r']

rec1 = [u'ColumnOrdinal=0,ColumnSize=20,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=1,ColumnSize=135,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=2,ColumnSize=4,NumericPrecision=10,NumericScale=255,ProviderType=Int,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt32,DataTypeName=int', u'ColumnOrdinal=3,ColumnSize=6,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=4,ColumnSize=240,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=5,ColumnSize=4,NumericPrecision=10,NumericScale=255,ProviderType=Int,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt32,DataTypeName=int', u'ColumnOrdinal=6,ColumnSize=60,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=7,ColumnSize=40,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=8,ColumnSize=2,NumericPrecision=5,NumericScale=255,ProviderType=SmallInt,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt16,DataTypeName=smallint', u'ColumnOrdinal=9,ColumnSize=12,NumericPrecision=255,NumericScale=255,ProviderType=VarChar,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlString,DataTypeName=varchar', u'ColumnOrdinal=10,ColumnSize=2,NumericPrecision=5,NumericScale=255,ProviderType=SmallInt,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt16,DataTypeName=smallint', u'ColumnOrdinal=11,ColumnSize=2,NumericPrecision=5,NumericScale=255,ProviderType=SmallInt,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlInt16,DataTypeName=smallint', u'ColumnOrdinal=12,ColumnSize=4,NumericPrecision=7,NumericScale=255,ProviderType=Real,IsLong=False,ProviderSpecificDataType=System.Data.SqlTypes.SqlSingle,DataTypeName=real']

rec2 = [u'KS053', u'Ellsworth County, Kansas', u'2733324', u'3844', u'Geary silt loam, 3 to 7 percent slopes', u'11807777', u'Kipson', u'', u'1', u'Cr', u'46', u'200', u'']

"""

        with arcpy.da.InsertCursor(tmpTable, fieldList) as cur:

            for rec in dataList:
                areasymbol, areaname, mukey, musym, muname, cokey, compname, localphase, comppct_r, hzname, hzdept_r, hzdepb_r, awc_r = rec
                #PrintMsg(" \t" + str(rec), 1)
                comppct_r = int(comppct_r)

                # Handle numeric values that might be represented by empty strings
                #if hzdept_r != "":
                #    hzdept_r = int(hzdept_r)

                #else:
                #    hzdept_r = None

                #if hzdepb_r != "":
                #    hzdepb_r = int(hzdepb_r)

                #else:
                #    hzdepb_r = None

                #if not awc_r == "":
                #    awc_r = float(awc_r)

                #else:
                #    awc_r = None

                #if 1 == 1:

                # Handle numeric values that might be None (null)
                if not hzdept_r is None:
                    hzdept_r = int(hzdept_r)

                if not hzdepb_r is None:
                    hzdepb_r = int(hzdepb_r)

                if not awc_r is None:
                    awc_r = float(awc_r)

                rec = areasymbol, areaname, mukey, musym, muname, cokey, compname, localphase, comppct_r, hzname, hzdept_r, hzdepb_r, awc_r

                #PrintMsg(" \t" + str(rec), 0)
                cur.insertRow(rec)

        # Aggregate horizon-component data to the final map unit rating
        outputValues = AggregateHz_WTA_SUM(outputShp, "Available Water Storage", "AWS", tmpTable)
        return outputValues

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputValues

    except:
        errorMsg()
        return outputValues

## ===================================================================================
def AttributeRequestSoap(theURL, mukeyList, top, bot, outputShp):
    # Send query to SDM Tabular Service, returning AWC data in XML format

    try:
        outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \nSending matching tabular request for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        #arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")
        fieldList = ['AREASYMBOL', 'AREANAME', 'MUKEY', 'MUSYM', 'MUNAME', 'COKEY', 'COMPNAME', 'COMPPCT_R', 'HZNAME', 'HZDEPT_R', 'HZDEPB_R', 'AWC_R']

        mukeys = ",".join(mukeyList)
        depths = str(tuple(range(top, bot)))

        hzQuery = "hzdept_r between " + str(top) + " and " + str(bot - 1) + " or hzdepb_r between " + str(top) + " and " + str(bot)
        #hzQuery = "(ch.hzdept_r in " + depths + " or ch.hzdepb_r in " + depths + ") or (ch.hzdept_r < " + str(top) + " and ch.hzdepb_r > " + str(bot) + ")"

        sQuery = """select
        l.areasymbol,
        l.areaname,
        mu.mukey,
        mu.musym,
        mu.muname,
        co.cokey,
        co.compname,
        co.localphase,
        co.comppct_r,
        ch.hzname,
        ch.hzdept_r,
        ch.hzdepb_r,
        ch.awc_r
        FROM
        legend l
        INNER JOIN mapunit mu ON mu.lkey = l.lkey and mu.mukey in (""" \
        + mukeys \
        + """)
        LEFT OUTER JOIN component co ON co.mukey = mu.mukey and co.comppct_r is not null
        LEFT OUTER JOIN chorizon ch ON ch.cokey = co.cokey and (""" + hzQuery + """)
        ORDER BY mu.mukey, co.comppct_r desc, co.cokey, ch.hzdept_r"""

        #PrintMsg(" \n" + sQuery, 0)

        # Send XML query to SDM Access service
        #
        xmlBody = """<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <RunQuery xmlns="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
          <Query>""" + sQuery + """</Query>
        </RunQuery>
      </soap12:Body>
    </soap12:Envelope>"""

        # Tabular service to append to SDA URL
        url = "/Tabular/SDMTabularService.asmx"

        dHeaders = dict()
        dHeaders["Host"] = theURL
        dHeaders["Content-Type"] = "text/xml; charset=utf-8"
        dHeaders["SOAPAction"] = "http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx/RunQuery"
        dHeaders["Content-Length"] = len(xmlBody)

        # Create SDM connection to service using HTTP
        conn = httplib.HTTPConnection(theURL, 80)

        # Send request in XML-Soap
        conn.request("POST", url, xmlBody, dHeaders)

        # Get back XML response
        response = conn.getresponse()
        xmlString = response.read()

        # Close connection to SDA
        conn.close()

        if 0:
            # Diagnostic printout
            PrintMsg(' \nconn.request("POST", url, body, dHeaders)', 0)
            PrintMsg(" \nHost: " + theURL, 0)
            PrintMsg(" \nxmlBody: " + xmlBody, 0)
            PrintMsg(" \ndHeaders: " + str(dHeaders), 0)
            PrintMsg(" \n", 1)

        if xmlString.find("mukey") == -1:
            raise MyError, "No soils data found for this location"

        # Create temporary table to contain results of SDA tabular query
        # areasymbol, areaname, mukey, muysm, cokey, comppct_r,compname,hzname,hzdept_r,hzdepb_r,awc_r
        #
        PrintMsg(" \n\tSaving horizon level data...", 0)
        #arcpy.SetProgressorLabel("Saving horizon level data from Soil Data Access...")
        tmpTable = os.path.join(env.scratchGDB, "SDA_QueryTable")

        if arcpy.Exists(tmpTable):
            arcpy.Delete_management(tmpTable)

        # Create table to contain component-horizon level data
        arcpy.CreateTable_management(os.path.dirname(tmpTable), os.path.basename(tmpTable))
        arcpy.AddField_management(tmpTable, "AREASYMBOL", "TEXT", "", "", "20")
        arcpy.AddField_management(tmpTable, "AREANAME", "TEXT", "", "", "135")
        arcpy.AddField_management(tmpTable, "MUKEY", "TEXT", "", "", "30")
        arcpy.AddField_management(tmpTable, "MUSYM", "TEXT", "", "", "6")
        arcpy.AddField_management(tmpTable, "MUNAME", "TEXT", "", "", "175")
        arcpy.AddField_management(tmpTable, "COKEY", "TEXT", "", "", "30")
        arcpy.AddField_management(tmpTable, "COMPNAME", "TEXT", "", "", "60")
        arcpy.AddField_management(tmpTable, "COMPPCT_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "HZNAME", "TEXT", "", "", "12")
        arcpy.AddField_management(tmpTable, "HZDEPT_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "HZDEPB_R", "SHORT", "", "", "")
        arcpy.AddField_management(tmpTable, "AWC_R", "FLOAT", "", "", "")

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        iCnt = 0
        firstFld = fieldList[0]
        lastFld = fieldList[-1]
        #dData = dict()

        # Begin writing query results (component-horizon data) to a temporary table
        with arcpy.da.InsertCursor(tmpTable, fieldList) as cur:

            # Iterate through XML tree, finding required elements...
            for rec in tree.iter():

                if rec.tag.upper() in fieldList:
                    tag = rec.tag.upper()

                    if tag in ['HZDEPT_R', 'HZDEPB_R', 'COMPPCT_R']:
                        # horizon depth and component percent should be integer
                        try:
                            val = int(rec.text)

                        except:
                            val = None

                    elif tag == "AWC_R":
                        # make awc_r value a float
                        try:
                            val = float(rec.text)

                        except:
                            # treat null values as zero
                            val = 0.0

                    else:
                        # assume everything else is text
                        val = rec.text

                    if tag == firstFld:
                        # First value for new record
                        iCnt += 1
                        vals = [val]

                    else:
                        vals.append(val)

                        if tag == lastFld:

                            cur.insertRow(vals)

        # Aggregate horizon-component data to the final map unit rating
        outputValues = AggregateHz_WTA_SUM(outputShp, "Available Water Storage", "AWS", tmpTable)
        return outputValues

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputValues

    except:
        errorMsg()
        return outputValues

## ===================================================================================
def AggregateHz_WTA_SUM(outputShp, sdvAtt, sdvFld, tmpTable):
    # Adapted from Map Soil Properties and Interpretations script
    #
    # Aggregate mapunit-component-horizon data to the map unit level using a weighted average
    #
    # This version uses SUM for horizon data as in AWS
    #
    try:
        #arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # match gdb
        #gdb = os.path.basename(outputShp)

        #
        # Create final output table with MUKEY, COMPPCT_R and sdvFld
        bVerbose = True
        cutOff = 0
        fldPrecision = 2

        inFlds = ["AREASYMBOL", "AREANAME", "MUKEY", "MUSYM", "MUNAME", "COKEY", "COMPPCT_R", "HZDEPT_R", "HZDEPB_R", "AWC_R"]
        outFlds = ["AREASYMBOL", "AREANAME", "MUKEY", "MUSYM", "MUNAME", "PCT_SUM", "AWS"]
        outFlds = ["AREASYMBOL", "AREANAME", "MUKEY", "MUSYM", "MUNAME", "AWS"]
        sqlClause =  (None, "ORDER BY MUKEY ASC, COMPPCT_R DESC, HZDEPT_R ASC")

        bZero = False  # Need to test this option from the other script
        whereClause = "COMPPCT_R >=  " + str(cutOff)

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMapunit = dict()
        dMu = dict()

        outCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))

        #hzCnt = int(arcpy.GetCount_management(tmpTable).getOutput(0))
        #PrintMsg(" \nComponent-horizon table has " + str(hzCnt) + " records", 1)

        with arcpy.da.SearchCursor(tmpTable, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            #PrintMsg(" \nOutputFields: " + ", ".join(outFlds), 1)

            with arcpy.da.UpdateCursor(outputShp, outFlds) as ocur:

                #arcpy.SetProgressorLabel("Reading raw input table")

                for rec in cur:
                    areasymbol, areaname, mukey, musym, muname, cokey, comppct, hzdept, hzdepb, val = rec
                    dMapunit[mukey] = [areasymbol, areaname, musym, muname]
                    #PrintMsg(str(rec), 1)
                    # td = top of range
                    # bd = bottom of range
                    if val is None:
                        val = 0

                    if not (val is None or hzdept is None or hzdepb is None):

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        if hzT > 0:
                            aws = float(hzT) * val
                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, aws]
                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dAWS = dComp[cokey]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dAWS]

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, dRec in dComp.items():
                        # get component level data  CHK
                        mukey, comppct, hzT, val = dRec

                        # get sum of component percent for the mapunit  CHK
                        try:
                            sumCompPct = float(dPct[mukey])

                        except:
                            # set the component percent to zero if it is not found in the
                            # dictionary. This is probably a 'Miscellaneous area' not included in the  CHK
                            # data or it has no horizon information.
                            sumCompPct = 0

                        # calculate component percentage adjustment

                        if sumCompPct > 0:
                            # If there is no data for any of the component horizons, could end up with 0 for
                            # sum of comppct_r
                            adjCompPct = float(comppct) / sumCompPct   # WSS method

                            # adjust the rating value down by the component percentage and by the sum of the
                            # usable horizon thickness for this component
                            aws = round((adjCompPct * val), 2) # component rating
                            hzT = hzT * adjCompPct    # Adjust component share of horizon thickness by comppct

                            # Update component values in component dictionary   CHK
                            dComp[cokey] = mukey, comppct, hzT, aws

                            # Populate dMu dictionary
                            if mukey in dMu:
                                # add new pct and aws to existing map unit value
                                val1, val3 = dMu[mukey]
                                comppct = comppct + val1
                                aws = aws + val3

                            dMu[mukey] = [comppct, aws]
                            #PrintMsg("\t+" + str(mukey) + ", " + str(comppct) + ", " + str(aws), 1)

                # Write out map unit aggregated AWS
                #
                murec = list()
                outputValues= [999999999, -9999999999]

                # Finally, write map unit ratings to the polygon featureclass
                #arcpy.SetProgressor("step", "Updating featureclass attribute data", 0, outCnt, 1)

                for rec in ocur:
                    mukey = rec[2]

                    try:
                        comppct, aws = dMu[mukey]

                    except:
                        # Missing mapunit such as Water
                        comppct, aws = None, None

                    areasymbol, areaname, musym, muname = dMapunit[mukey]

                    if not aws is None:
                        aws = round(aws, fldPrecision)

                    # AREASYMBOL, AREANAME, MUKEY, MUSYM, MUNAME, AWC_R
                    murec = [areasymbol, areaname,  mukey, musym, muname, aws]
                    #PrintMsg(str(murec), 1)
                    ocur.updateRow(murec)
                    #arcpy.SetProgressorPosition()

                    # save max-min values
                    if not aws is None:
                        outputValues[0] = min(aws, outputValues[0])
                        outputValues[1] = max(aws, outputValues[1])

        outputValues.sort()
        #PrintMsg(" \nMin-Max Values: " + str(outputValues), 1)
        return outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputShp, []

    except:
        errorMsg()
        return outputShp, []

## ===================================================================================
def GetBoundingBox(theAOI):
    #
    # Given an AOI (polygon layer), return the bounding extents as a string

    try:
        xMax = -360.0
        yMax = -360.0
        xMin = 360.0
        yMin = 360.0
        gcs = arcpy.SpatialReference(epsgWGS)
        aoiArea = 0.0

        with arcpy.da.SearchCursor(theAOI, ["SHAPE@"], "", gcs) as cur:
            for rec in cur:
                extent = rec[0].extent
                xMin = min(extent.XMin, xMin)
                yMin = min(extent.YMin, yMin)
                xMax = max(extent.XMax, xMax)
                yMax = max(extent.YMax, yMax)

        theCoords = str(xMin) + "," + str(yMin) + "," + str(xMax) + "," + str(yMax)
        #PrintMsg(" \n" + theCoords, 1)

        return theCoords

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def GetLayerAcres(layerName):
    #
    # Given a polygon layer, return the area in acres, polygon count, vertex count
    # Used

    try:
        acres = 0.0
        polyCnt = 0
        vertCnt = 0
        cs = arcpy.Describe(layerName).spatialReference

        with arcpy.da.SearchCursor(layerName, ["SHAPE@"], "", cs) as cur:
            for rec in cur:
                polygon = rec[0]
                if not polygon is None:
                    acres += polygon.getArea("GREAT_ELLIPTIC", "ACRES")

                    #PrintMsg("\tAOI polygon " + str(rec[1]) + " has " + Number_Format(acres, 0, True) + " acres", 1)
                    vertCnt += rec[0].pointCount
                    polyCnt += 1

        return acres, polyCnt, vertCnt

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0, 0, 0

    except:
        errorMsg()
        return 0, 0, 0

## ===================================================================================
def CreateOutputFC(outputShp, theAOI):
    #
    # Given the path for the new output featureclass, create it as polygon and required fields
    # Later it will be populated using a cursor

    try:
        # Setup output coordinate system (same as input AOI) and datum transformation.
        # Please note! Only handles WGS1984 and NAD1983 datums.
        outputCS = arcpy.Describe(theAOI).spatialReference
        # These next two lines set the output coordinate system environment

        env.geographicTransformations = tm

        # Create empty polygon featureclass
        arcpy.CreateFeatureclass_management(os.path.dirname(outputShp), os.path.basename(outputShp), "POLYGON", "", "DISABLED", "DISABLED", outputCS)

        # Add required fields (MUKEY for now. Add the rest later after the attribute query has come back)
        arcpy.AddField_management(outputShp, "MUKEY", "TEXT", "", "", "30")   # for outputShp

        #bFields = AddNewFields(outputShp)

        return outputShp

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def FormSpatialQuery(theAOI):
    #
    # Given a simplified polygon layer, use vertices to form the spatial query for a Tabular request
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    try:

        gcs = arcpy.SpatialReference(epsgWGS)
        i = 0

        if bProjected:
            # Project geometry from AOI

            with arcpy.da.SearchCursor(theAOI, ["SHAPE@"]) as cur:
                for rec in cur:
                    polygon = rec[0].convexHull()                     # simplified geometry
                    outputPolygon = polygon.projectAs(gcs, tm)        # simplified geometry, projected to WGS 1984
                    clipPolygon = rec[0].projectAs(gcs, tm)           # original geometry projected to WGS 1984
                    wkt = outputPolygon.WKT
                    i += 1

        else:
            # No projection required. AOI must be GCS WGS 1984

            with arcpy.da.SearchCursor(theAOI, ["SHAPE@"]) as cur:
                for rec in cur:
                    polygon = rec[0].convexHull()                     # simplified geometry
                    clipPolygon = rec[0]                              # original geometry
                    wkt = polygon.WKT
                    i += 1

        if i != 1:
            raise MyError, "Found " + Number_Format(i, 0, True) +" polygons in AOI, expected only 1"

        sdaQuery = """
 ~DeclareGeometry(@aoi)~
 select @aoi = geometry::STPolyFromText('
 xxCoordsxx
 ', 4326)

 --   Extract all intersected polygons
 ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
 ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

 --   Convert geometries to geographies so we can get areas
 ~DeclareIdGeogTable(@intersectedPolygonGeographies)~
 ~GetGeogFromGeomWgs84(@intersectedPolygonGeometries,@intersectedPolygonGeographies)~

 --   Return WKT for the polygonal geometries
 select * from @intersectedPolygonGeographies
 where geog.STGeometryType() = 'Polygon'"""

        # Strip "MULTI" off as well as leading and trailing (). Not sure why SDA doesn't like MULTIPOLYGON.
        wkt = wkt.replace("MULTIPOLYGON (", "POLYGON ")[:-1]

        # Insert single polygon coordinates to spatial query
        sdaQuery = sdaQuery.replace("xxCoordsxx", wkt)

        #PrintMsg(" \nsdaQuery: \n" + sdaQuery, 1)

        return sdaQuery, clipPolygon

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return "", None

    except:
        errorMsg()
        return "", None

## ===================================================================================
def FormSpatialQueryBox(theAOI):
    #
    # Given a polygon layer, return the spatial bounding-box-type query for a Tabular request
    # Coordinates are GCS WGS1984
    try:
        xMax = -360.0
        yMax = -360.0
        xMin = 360.0
        yMin = 360.0
        gcs = arcpy.SpatialReference(epsgWGS)

        with arcpy.da.SearchCursor(theAOI, ["SHAPE@"], "", gcs) as cur:
            for rec in cur:
                extent = rec[0].extent
                xMin = min(extent.XMin, xMin)
                yMin = min(extent.YMin, yMin)
                xMax = max(extent.XMax, xMax)
                yMax = max(extent.YMax, yMax)

        theCoords = str(xMin) + "," + str(yMin) + "," + str(xMax) + "," + str(yMax)
        PrintMsg(" \n" + theCoords, 1)

        # Expand the AOI just a hair to make sure the edges don't get clipped
        exp = 0.000001
        xMin -= exp
        yMin -= exp
        xMax += exp
        yMax += exp

        # Make WKT polygon box that could be used in Advanced Spatial Query against the Tabular Service
        #
        wktBox = str(xMin) + " " + str(yMin) + ",\n" + \
        str(xMin) + " " + str(yMax) + ",\n" + \
        str(xMax) + " " + str(yMax) + ",\n" + \
        str(xMax) + " " + str(yMin) + ",\n" + \
        str(xMin) + " " + str(yMin)

        sdaQuery = """
 ~DeclareGeometry(@aoi)~
 select @aoi = geometry::STPolyFromText('polygon((
 xxCoordsxx
 ))', 4326)

 --   Extract all intersected polygons
 ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
 ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

 --   Convert geometries to geographies so we can get areas
 ~DeclareIdGeogTable(@intersectedPolygonGeographies)~
 ~GetGeogFromGeomWgs84(@intersectedPolygonGeometries,@intersectedPolygonGeographies)~

 --   Return WKT the polygonal geometries
 select * from @intersectedPolygonGeographies
 where geog.STGeometryType() = 'Polygon'"""

        sdaQuery = sdaQuery.replace("xxCoordsxx", wktBox)
        #PrintMsg(" \nWKT Box: \n" + wktBox, 1)
        PrintMsg(" \nsdaQuery: \n" + sdaQuery, 1)

        return sdaQuery

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def RunSpatialQueryWKT(theURL, spatialQuery, outputShp, clipPolygon):
    # Send spatial query to SDA Tabular Service
    # Read XML returned by SDA and convert WKT data to a polygon featureclass

    try:

        #arcpy.SetProgressor("default", "Requesting spatial data for polygon " + Number_Format(polyNum, 0, True))
        # Tabular service to append to SDA URL
        #url = "http://SDMDataAccess.sc.egov.usda.gov/Tabular/SDMTabularService/post.rest" # worked
        #url = "sdmdataaccess-dev.dev.sc.egov.usda.gov/Tabular/SDMTabularService/post.rest"
        url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        #PrintMsg(" \n\tProcessing spatial request using " + url + " with XML output", 1)
        PrintMsg(" \n" + spatialQuery, 1)

        dRequest = dict()
        dRequest["FORMAT"] = "XML"
        dRequest["QUERY"] = spatialQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)

        responseStatus = resp.getcode()
        responseMsg = resp.msg

        if responseStatus != 200 :
            raise MyError, "HTTP Error: " + responseMsg

        xmlString = resp.read()

        # See if I can get an estimated polygon count from the XML string

        # Convert XML to tree format
        root = ET.fromstring(xmlString)

        desc = arcpy.Describe(outputShp)
        outputCS = desc.spatialReference
        outputFields = ["SHAPE@", "MUKEY"]

        # input cs from SDA = GCS WGS 1984
        inputCS = arcpy.SpatialReference(epsgWGS)

        # These next two lines set the output coordinate system environment
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        PrintMsg(" \n\tImporting spatial data...", 0)

        polyCnt = 0

        if inputCS.name != outputCS.name:
            # Project geometry
            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for geog in root.iter():
                    if geog.tag == "id":
                        #PrintMsg("\tID: " + str(geog.text), 0)
                        mukey = geog.text

                    if geog.tag == "geog":
                        #PrintMsg("\t" + str(id) + ", " + str(geog.text), 0)
                        wktPoly = geog.text

                        # immediately create polygon from WKT
                        newPolygon = arcpy.FromWKT(wktPoly, inputCS)

                        # Try to clip newPolygon by clipPolygon
                        clippedPolygon = newPolygon.intersect(clipPolygon, 4)


                        outputPolygon = clippedPolygon.projectAs(outputCS, tm)
                        if outputPolygon is None:
                            PrintMsg(" \nFound null geometry...", 1)

                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                    #arcpy.SetProgressorPosition()

        else:
            # Input and output coordinate system is the same. No projection.

            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for geog in root.iter():
                    if geog.tag == "id":
                        #PrintMsg("\tID: " + str(geog.text), 0)
                        mukey = geog.text

                    if geog.tag == "geog":
                        #PrintMsg("\tGEOG: " + str(geog.text), 0)
                        wktPoly = geog.text
                        #PrintMsg(cString, 1)

                        # immediately create polygon from WKT
                        outputPolygon = arcpy.FromWKT(wktPoly, inputCS)

                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                    #arcpy.SetProgressorPosition()

        if polyCnt > 0:
            # successful completion, return polyCnt here.
            return polyCnt

        else:
            # Try to print messages
            hasFault = False

            for geog in root.iter():
                if geog.tag.endswith("Fault"):
                    hasFault = True

                if geog.tag.endswith("Text") and hasFault:
                    raise MyError, "Fault; " + geog.text

            return 0


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def RunSpatialQuery(theURL, spatialQuery, outputShp, clipPolygon, showStatus):
    # Send spatial query to SDA Tabular Service
    # Read JSON table containing records with MUKEY and WKT Polygons to a polygon featureclass
    #
    # Currently problems with JSON format using POST REST.
    # MaxJsonLength is appparently set to the default value of 102,400 characters. Need to set to Int32.MaxValue?
    # This limit does not affect the XML option.

    try:
        # Tabular service to append to SDA URL
        url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        #PrintMsg(" \n\tProcessing spatial request using " + url + " with JSON output", 1)
        PrintMsg(" \n" + spatialQuery, 1)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON"
        #dRequest["FORMAT"] = "'JSON + METADATA + COLUMN"
        dRequest["QUERY"] = spatialQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

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

        except:
            errorMsg()
            raise MyError, "Spatial Request failed"

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        #PrintMsg(" \nJSON from SDA: \n " + str(data), 1 )

        del jsonString, resp, req

        # Get coordinate system information for input and output layers
        outputCS = arcpy.Describe(outputShp).spatialReference

        # The input coordinate system for data from SDA is GCS WGS 1984.
        # My understanding is that ArcGIS will not use it if it is not needed.
        inputCS = arcpy.SpatialReference(epsgWGS)

        # Currently limited to GCS WGS1984 or NAD1983 datums
        validDatums = ["D_WGS_1984", "D_North_American_1983"]

        if not (inputCS.GCS.datumName in validDatums and outputCS.GCS.datumName in validDatums):
            raise MyError, "Valid coordinate system datums are: " + ", ".join(validDatums)

        # Only two fields are used initially, the geometry and MUKEY
        outputFields = ["SHAPE@", "MUKEY"]

        PrintMsg("\tImporting " + Number_Format(len(dataList), 0, True) + " soil polygons...", 0)

        polyCnt = 0

        if showStatus:
            step = 1
            end = len(dataList)
            arcpy.SetProgressor("step", "Importing spatial data", 0, end, step)

        else:
            step = 0
            end = 0

        if bProjected:
            # Project geometry to match input AOI layer
            #
            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for rec in dataList:
                    #PrintMsg("\trec: " + str(rec), 1)
                    mukey, wktPoly = rec
                    # immediately create GCS WGS 1984 polygon from WKT
                    newPolygon = arcpy.FromWKT(wktPoly, inputCS)

                    # and then project the polygon
                    outputPolygon = newPolygon.projectAs(outputCS, tm)

                    # Clip the generalized SDA polygon by the original AOI polygon.
                    clippedPolygon = newPolygon.intersect(clipPolygon, 4)

                    # Write geometry and mukey to output featureclass
                    rec = [clippedPolygon, mukey]
                    cur.insertRow(rec)
                    polyCnt += 1

                    if showStatus:
                        arcpy.SetProgressorPosition()

        else:
            # No projection necessary. Input and output coordinate systems are the same.
            #
            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for rec in dataList:
                    #PrintMsg("\trec: " + str(rec), 1)
                    mukey, wktPoly = rec

                    # immediately create polygon from WKT
                    newPolygon = arcpy.FromWKT(wktPoly, inputCS)

                    # Clip newPolygon by the original AOI polygon
                    outputPolygon = newPolygon.intersect(clipPolygon, 4)

                    rec = [outputPolygon, mukey]
                    cur.insertRow(rec)
                    polyCnt += 1

                    if showStatus:
                        arcpy.SetProgressorPosition()

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
def RunSpatialQuerySOAP(theURL, spatialQuery, outputShp, clipPolygon):
    # Send spatial query to SDA Tabular Service
    # Read XML returned by SDA and convert WKT data to a polygon featureclass

    try:
        #PrintMsg(" \n\tProcessing spatial request on " + theURL)
        #arcpy.SetProgressor("default", "Requesting spatial data for polygon " + Number_Format(polyNum, 0, True))

        #PrintMsg(" \n" + spatialQuery, 0)

        # Send XML query to SDM Access service
        #
        url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        PrintMsg(" \n\tProcessing spatial request using " + url + " with JSON output", 1)

        xmlBody = """<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <RunQuery xmlns="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
          <Query>""" + spatialQuery + """</Query>
        </RunQuery>
      </soap12:Body>
    </soap12:Envelope>"""

        url = "/Tabular/SDMTabularService.asmx"

        dHeaders = dict()
        dHeaders["Host"] = theURL
        dHeaders["Content-Type"] = "text/xml; charset=utf-8"
        dHeaders["SOAPAction"] = "http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx/RunQuery"
        dHeaders["Content-Length"] = len(xmlBody)

        # Create SDM connection to service using HTTP

        conn = httplib.HTTPConnection(theURL, 80)

        # Send request in XML-Soap
        conn.request("POST", url, xmlBody, dHeaders)

        # Get back XML response
        response = conn.getresponse()
        xmlString = response.read()
        #PrintMsg(" \n" + xmlString + " \n ", 1)

        # Close connection to SDA
        conn.close()

        # See if I can get an estimated polygon count from the XML string

        # Convert XML to tree format
        root = ET.fromstring(xmlString)
        #PrintMsg(" \n" + xmlString, 1)
        #polys = xmlString.count("POLYGON")

        #PrintMsg(" \nReturned an estimated " + Number_Format(polys, 0, True) + " polygons...", 1)

        desc = arcpy.Describe(outputShp)
        outputCS = desc.spatialReference
        outputFields = ["SHAPE@", "MUKEY"]

        # input cs from SDA = GCS WGS 1984
        inputCS = arcpy.SpatialReference(epsgWGS)

        # These next two lines set the output coordinate system environment
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        #PrintMsg(" \n\tImporting spatial data...", 0)
        #arcpy.SetProgressorLabel("Importing spatial data for polygon " + Number_Format(polys, 0, True))

        polyCnt = 0

        if inputCS.name != outputCS.name:
            # Project geometry
            #arcpy.SetProgressor("step", "Importing spatial data", 0, polys, 1)
            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for geog in root.iter():
                    if geog.tag == "id":
                        #PrintMsg("\tID: " + str(geog.text), 0)
                        mukey = geog.text

                    if geog.tag == "geog":
                        #PrintMsg("\t" + str(id) + ", " + str(geog.text), 0)
                        wktPoly = geog.text

                        # immediately create polygon from WKT
                        newPolygon = arcpy.FromWKT(wktPoly, inputCS)

                        # Try to clip newPolygon by clipPolygon
                        clippedPolygon = newPolygon.intersect(clipPolygon, 4)


                        outputPolygon = clippedPolygon.projectAs(outputCS, tm)
                        if outputPolygon is None:
                            PrintMsg(" \nFound null geometry...", 1)

                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                    #arcpy.SetProgressorPosition()

        else:
            # Input and output coordinate system is the same. No projection.
            #arcpy.SetProgressor("step", "Importing spatial data", 0, polys, 1)

            with arcpy.da.InsertCursor(outputShp, outputFields) as cur:

                for geog in root.iter():
                    if geog.tag == "id":
                        #PrintMsg("\tID: " + str(geog.text), 0)
                        mukey = geog.text

                    if geog.tag == "geog":
                        #PrintMsg("\tGEOG: " + str(geog.text), 0)
                        wktPoly = geog.text
                        #PrintMsg(cString, 1)

                        # immediately create polygon from WKT
                        outputPolygon = arcpy.FromWKT(wktPoly, inputCS)

                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                    #arcpy.SetProgressorPosition()

        if polyCnt > 0:
            # successful completion, return polyCnt here.
            return polyCnt

        else:
            # Try to print messages
            hasFault = False

            for geog in root.iter():
                if geog.tag.endswith("Fault"):
                    hasFault = True

                if geog.tag.endswith("Text") and hasFault:
                    raise MyError, "Fault; " + geog.text

            return 0


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def GetBoundingBoxAcres(theCoords):
    #
    # Given a polygon layer, return the bounding extents as a string
    # Note that rotating the original AOI from straight N-S or E-W can
    # cause the calculated acres for the bounding box to increase dramatically.

    try:
        coordList = theCoords.split(",")
        xMin = float(coordList[0])
        yMin = float(coordList[1])
        xMax = float(coordList[2])
        yMax = float(coordList[3])

        # Get acres for bounding box
        pointArray = arcpy.Array([arcpy.Point(xMin, yMin), arcpy.Point(xMin, yMax), arcpy.Point(xMax, yMax), arcpy.Point(xMax, yMin), arcpy.Point(xMax, yMin)])

        gcs = arcpy.SpatialReference(epsgWGS)
        polygon = arcpy.Polygon(pointArray, gcs, False, False)
        #arcpy.CopyFeatures_management(polygon, os.path.join(env.scratchGDB, "BndPolygon"))

        boxAcres = polygon.getArea("GREAT_ELLIPTIC", "ACRES")
        #PrintMsg(" \nBox acres (great elleptic): " + Number_Format(boxAcres, 1, True), 1)

        # Alternative acres using Albers USGS CONUS
        albersCS = arcpy.SpatialReference(epsgAlbers)
        tm = "WGS_1984_(ITRF00)_To_NAD_1983"
        albersPolygon = polygon.projectAs(albersCS, tm)
        albersAcres = albersPolygon.area * 0.00024711

        return boxAcres

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def CreateScratchFileName(thePath, thePrefix, theExtension):
    # Create unique filename using prefix and file extension (include dot)

    try:
        theOutputName = ""

        for i in xrange(1000):
            theOutputName = thePath + "\\" + thePrefix + str(i) + theExtension

            if not arcpy.Exists(theOutputName):
                return theOutputName

    except:
        errorMsg()
        return ""

## ===================================================================================
def FindField(theTable, chkField):
    # Check table or featureclass to see if specified field exists
    # Set workspace before calling FindField
    try:
        if arcpy.Exists(theTable):
            theDesc = arcpy.Describe(theTable)
            theFields = theDesc.fields
            fieldList = list()

            for fld in theFields:
                fieldList.append(fld.basename.upper())

            if chkField.upper() in fieldList:
                return True

            else:
                return False

        else:
            PrintMsg("    Table or featureclass " + os.path.basename(theTable) + " does not exist", 0)
            return False

    except:
        errorMsg()
        return False

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
                    mukey = "'" + rec[0] + "'"
                    if not mukey in mukeyList:
                        mukeyList.append(mukey)


            #PrintMsg("\tmukey list: " + str(mukeyList), 1)
            return mukeyList

        else:
            return []


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return list()

    except:
        errorMsg()
        return []

## ===================================================================================
def AddLayerToMap(outputShp, ratingField):
    #
    # Add new featureclass and define symbology
    try:
        arcpy.MakeFeatureLayer_management(outputShp, "Temp Layer")
        layerFile = r"c:\temp\SDA.lyr"
        arcpy.SaveToLayerFile_management("Temp Layer", layerFile)
        arcpy.Delete_management("Temp Layer")

        newLayer = arcpy.mapping.Layer(layerFile)
        newLayer.visibility = False

        # Update layer symbology using JSON dictionary
        installInfo = arcpy.GetInstallInfo()
        version = float(installInfo["Version"])

        # zoom to new layer extent
        #
        # Describing a map layer extent always returns coordinates in the data frame coordinate system
        newExtent = arcpy.Describe(newLayer).extent

        # Expand the extent by 10%
        xOffset = (newExtent.XMax - newExtent.XMin) * 0.05
        yOffset = (newExtent.YMax - newExtent.YMin) * 0.05
        newExtent.XMin = newExtent.XMin - xOffset
        newExtent.XMax = newExtent.XMax + xOffset
        newExtent.YMin = newExtent.YMin - yOffset
        newExtent.YMax = newExtent.YMax + yOffset

        df.extent = newExtent
        #df.extent = aoiExtent

        if df.scale <= 24000:
            newLayer.showLabels = True
            drawOutlines = True

        else:
            newLayer.showLabels = False
            drawOutlines = False

        if version >= 10.3:
            #PrintMsg(" \nUpdating symbology using JSON string", 1)
            # Originally loaded the entire dictionary. Try instead converting dictionary to string and using json.loads(jString)
            #PrintMsg(" \nUpdating layer symbology", 1)

            # Create map legend information
            dLayerDefinition = ClassBreaksJSON(ratingValues, drawOutlines)

            newLayer.updateLayerFromJSON(dLayerDefinition)
            newLayer.name = "Available Water Storage " + str(top) + " to " + str(bot) + units
            newLayer.description = """Available water supply (AWS) is the total volume of water (in centimeters) that should be available to plants when the soil, inclusive of rock fragments, is at field capacity. It is commonly estimated as the amount of water held between field capacity and the wilting point, with corrections for salinity, rock fragments, and rooting depth. AWS is reported as a single value (in centimeters) of water for the specified depth of the soil. AWS is calculated as the available water capacity times the thickness of each soil horizon to a specified depth.
For each soil layer, available water capacity, used in the computation of AWS, is recorded as three separate values in the database. A low value and a high value indicate the range of this attribute for the soil component. A "representative" value indicates the expected value of this attribute for the component. For the derivation of AWS, only the representative value for available water capacity is used.
The available water supply for each map unit component is computed as described above and then aggregated to a single value for the map unit by the process described below.
A map unit typically consists of one or more "components." A component is either some type of soil or some nonsoil entity, e.g., rock outcrop. For the attribute being aggregated (e.g., available water supply), the first step of the aggregation process is to derive one attribute value for each of a map unit's components. From this set of component attributes, the next step of the process is to derive a single value that represents the map unit as a whole. Once a single value for each map unit is derived, a thematic map for the map units can be generated. Aggregation is needed because map units rather than components are delineated on the soil maps.
The composition of each component in a map unit is recorded as a percentage. A composition of 60 indicates that the component typically makes up approximately 60 percent of the map unit.
For the available water supply, when a weighted average of all component values is computed, percent composition is the weighting factor."""

        # Set the output layer transparency
        newLayer.transparency = transparency

        # Add mapunit symbol (MUSYM) labels
        if newLayer.supports("LABELCLASSES"):
            labelCls = newLayer.labelClasses[0]
            labelCls.expression = "[MUSYM]"
            #newLayer.showLabels = False



        PrintMsg(" \nAdding new layer to ArcMap", 0)
        arcpy.mapping.AddLayer(df, newLayer, "TOP")
        newLayer.visibility = True

        # Create layer file for soils layer. Save to the same folder where the output geodatabase is stored.
        arcpy.SetParameter(1, "")
        layerName = newLayer.name.replace(" ", "_")
        layerPath = os.path.dirname(os.path.dirname(outputShp))
        layerFile = os.path.join(layerPath, layerName)
        arcpy.SaveToLayerFile_management(newLayer, layerFile)

        # Try getting acres from featurelayer instead of featureclass
        outputAcres, polyCnt, vertCnt = GetLayerAcres(newLayer)
        #PrintMsg(" \nOutput soils estimated at " + Number_Format(outputAcres, 0, True) + " acres", 0)

        return outputAcres

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return 0

    except:
        errorMsg()
        return 0

## ===================================================================================
def ClassBreaksJSON(ratingValues, drawOutlines):
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

    # RGB colors:
    # 255, 0, 0 = red
    # 255, 255, 0 = yellow
    # 0, 255, 0 = green
    # 0, 255, 255 = cyan
    # 0, 0, 255 = blue

    try:
        # Set outline symbology according to map scale. Small scale u
        if drawOutlines == False:
            # Black outline, transparent
            outLineColor = [0, 0, 0, 0]

        else:
            # Black outline, opaque
            outLineColor = [0, 0, 0, 255]

        # Initialize JSON string
        jsonString = """
{"type" : "classBreaks",
  "field" : "",
  "classificationMethod" : "esriClassifyManual",
  "minValue" : 0.0,
  "classBreakInfos" : [
  ]
}"""
        # Convert the JSON string to a Python dictionary and add additional required information
        d = json.loads(jsonString)
        d["field"] = "AWS"
        d["drawingInfo"] = dict() # new
        #d["defaultSymbol"]["outline"]["color"] = outLineColor

        minValue = ratingValues[0]
        maxValue = ratingValues[1]

        if minValue == maxValue:
            # Only have a single value to base the map legend on
            # Use a single symbol, yellow fill
            PrintMsg(" \nSingle value legend", 1)
            d["minValue"] = (minValue - 0.1)
            colorList = [(255,255,0,255)]

        else:
            d["minValue"] = minValue - 0.1  # set the floor value. Subtracted 0.1 because the bottom value wasn't being mapped. Roundoff???
            colorList = [(255,34,0,255), (255,153,0,255), (255,255,0,255), (122,171,0,255), (0,97,0,255)]  # RGB, Red to Green, 5 colors

        classBreakInfos = list()

        #PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        #PrintMsg(" \n\t\tLegend maximum value: " + str(maxValue), 1)
        lastMax = minValue

        # Need to create legendList with equal interval rating, rating as string, rgb list
        interval = round((maxValue - minValue) / len(colorList), 2)
        legendList = list()
        lastVal = minValue

        for cnt in range(0, len(colorList)):
            val = lastVal + interval
            legendList.append([val, str(val), colorList[cnt]])
            lastVal = val

        #PrintMsg(" \nLegendList has " + str(len(legendList)) + " members", 1)
        # Create standard numeric legend in Ascending Order
        #
        lastMax = minValue

        for cnt in range(0, len(colorList)):

            # Get information from legendList and add to dictionary
            ratingValue, label, rgb = legendList[cnt]

            if not ratingValue is None:

                # calculate rgb colors
                dLegend = dict()
                dSymbol = dict()

                if cnt > 0:
                    label = str(lastMax) + "-> " + str(ratingValue)

                    if cnt == (len(legendList) - 1):
                        ratingValue += 0.1
                        #PrintMsg(" \nLast rating value: " + str(ratingValue), 1)

                else:
                    label = str(lastMax) + "-> " + str(ratingValue) + " " + units
                    lastMax -= 0.1

                #PrintMsg(" \n" + str(cnt) + ". Adding legend values: " + str(lastMax) + "-> " + str(ratingValue) + ", " + str(label), 1)

                if minValue == maxValue:
                    # For some reason single value legends don't display properly. Expand the class by 0.1.
                    ratingValue += 0.1

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


        d["classBreakInfos"] = classBreakInfos

        dLayerDefinition = dict()
        dRenderer = dict()
        dRenderer["renderer"] = d
        dLayerDefinition["drawingInfo"] = dRenderer

        #PrintMsg(" \n1. dLayerDefinition: " + '"' + str(dLayerDefinition) + '"', 0)

        return dLayerDefinition

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return d

    except:
        errorMsg()
        return d

## ===================================================================================
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed secondss[17:-18]
        eTotal = end - start

        # day = 86400 seconds
        # hour = 3600 seconds
        # minute = 60 seconds

        eMsg = ""

        # calculate elapsed days
        eDay1 = eTotal / 86400
        eDay2 = math.modf(eDay1)
        eDay = int(eDay2[1])
        eDayR = eDay2[0]

        if eDay > 1:
          eMsg = eMsg + str(eDay) + " days "
        elif eDay == 1:
          eMsg = eMsg + str(eDay) + " day "

        # Calculated elapsed hours
        eHour1 = eDayR * 24
        eHour2 = math.modf(eHour1)
        eHour = int(eHour2[1])
        eHourR = eHour2[0]

        if eDay > 0 or eHour > 0:
            if eHour > 1:
                eMsg = eMsg + str(eHour) + " hours "
            else:
                eMsg = eMsg + str(eHour) + " hour "

        # Calculate elapsed minutes
        eMinute1 = eHourR * 60
        eMinute2 = math.modf(eMinute1)
        eMinute = int(eMinute2[1])
        eMinuteR = eMinute2[0]

        if eDay > 0 or eHour > 0 or eMinute > 0:
            if eMinute > 1:
                eMsg = eMsg + str(eMinute) + " minutes "
            else:
                eMsg = eMsg + str(eMinute) + " minute "

        # Calculate elapsed secons
        eSeconds = "%.1f" % (eMinuteR * 60)

        if eSeconds == "1.00":
            eMsg = eMsg + eSeconds + " second "
        else:
            eMsg = eMsg + eSeconds + " seconds "

        return eMsg

    except:
        errorMsg()
        return ""

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
        return False

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, arcpy, traceback, urllib2, httplib, json
import xml.etree.cElementTree as ET
from arcpy import env

try:
    # Create geoprocessor object
    #gp = arcgisscripting.create(9.3)

    # Get input parameters
    #
    theAOI = arcpy.GetParameterAsText(0)     # polygon layer (honors selected set) used to define AOI
    outputShp = arcpy.GetParameterAsText(1)  # output soil polygon featureclass (GDB)
    top = arcpy.GetParameter(2)              # top depth (cm)
    bot = arcpy.GetParameter(3)              # bottom depth (cm)
    transparency = arcpy.GetParameter(4)     # transparency level for the output soils layer
    maxAcres = arcpy.GetParameter(5)         # maximum allowed area for the output EXTENT.
    sdaURL = arcpy.GetParameterAsText(6)   # Soil Data Access URL


    # Commonly used EPSG numbers
    epsgWM = 3857 # Web Mercatur
    epsgWGS = 4326 # GCS WGS 1984
    epsgNAD83 = 4269 # GCS NAD 1983
    epsgAlbers = 102039 # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
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

    sdaCS = arcpy.SpatialReference(epsgWGS)

    # Determine whether
    if aoiCS.PCSName != "":
        # AOI layer has a projected coordinate system, so geometry will always have to be projected
        bProjected = True

    elif aoiCS.GCS.name != sdaCS.GCS.name:
        # AOI must be NAD 1983
        bProjected = True

    else:
        bProjected = False

    env.overWriteOutput = True
    env.addOutputsToMap = False
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame

    # Create arcpy.mapping layer object for original AOI
    # and save selected set
    aoiLayer = arcpy.mapping.ListLayers(mxd, theAOI, df)[0]
    aoiSelection = aoiLayer.getSelectionSet()

    # Get OID field for input layer
    #desc = arcpy.Describe(theAOI)
    #oidField = desc.OIDFieldName

    PrintMsg( " \nAnalyzing input AOI...", 0)
    aoiArea, aoiAcres, aoiCnt, aoiVert, density = LayerDensity(aoiLayer)

    if aoiAcres > maxAcres:
        raise MyError, "Selected area exceeds set limit for number of acres in the AOI"

    maxPolys = 1500

    if aoiCnt > maxPolys:
        raise MyError, "Selected number of polygons exceeds limit of" + Number_Format(maxPolys, 0, True) + " polygons"

    if os.path.dirname(outputShp) == "":
        # convert this to a featureclass in the scratch geodatabase
        outputShp = os.path.join(env.scratchGDB, outputShp)

    else:
        ws = os.path.dirname(outputShp)
        desc = arcpy.Describe(ws)

        if desc.workspaceType.upper() != "LOCALDATABASE":
            # Switch the output location to a file geodatabase so that null values aren't a problem
            outputShp = os.path.join(env.scratchGDB, os.path.basename(outputShp))

        else:
            # This should be correct. A geodatabase featureclass.
            pass

    # Create empty output featureclass
    outputShp = CreateOutputFC(outputShp, theAOI)

    # Start timer
    begin = time.time()

    inCnt = int(arcpy.GetCount_management(theAOI).getOutput(0))
    oidList = list()

    hullCnt = 0  # Initialize value that indicates that a single convex hull AOI was NOT sent to SDA

    # Begin performance logic
    #
    if aoiCnt == 1:
        # Single polygon, use original AOI to generate spatial request
        PrintMsg(" \nUsing original AOI polygons", 1)
        #PrintMsg(" \nOriginal AOI estimated to be " + Number_Format(aoiAcres, 0, True) + " acres in " + Number_Format(inCnt, 0, True) + " polygons", 0)
        idList = oidList
        newAOI = theAOI
        oidList = list()

        with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
            for rec in cur:
                oidList.append(rec[0])
                #PrintMsg("\t" + os.path.basename(newAOI) + ": " + Number_Format(rec[0], 0, False), 1)

    else:
        # Muliple polygons present in AOI layer
        #
        # Start by dissolving AOI and getting a new polygon count
        # Go ahead and create dissolved layer for use in clipping
        dissAOI, inCnt = SimplifyAOI_Diss(theAOI, inCnt)
        PrintMsg(" \nCreated dissolved layer with " + Number_Format(inCnt, 0, True) + " polygons", 1)

        if aoiAcres > maxAcres or density > 1000:   # trying to get bent pipeline to process as multiple AOIs
            # A single convex hull AOI would be too big, try using individual dissolved polygons

            if inCnt == 1 or density > 1000:
                if density > 1000:
                    # Dissolved AOI would be too big or too widespread. Use the original AOI
                    PrintMsg(" \nSingle dissolved AOI would be too large, switching back to original AOI", 1)
                    newAOI = aoiLayer
                    iCnt = 0

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            iCnt += 1
                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

                else:
                    # Dissolved AOI might work
                    PrintMsg(" \nUsing dissolved AOI", 1)
                    newAOI = dissAOI

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)



            elif inCnt > 1:
                if ((aoiAcres / inCnt) < maxAcres):
                    # Use the multiple, dissolved polygons to generate spatial request
                    newAOI = dissAOI

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            #PrintMsg("\tdissAOI: " + Number_Format(rec[0], 0, False), 1)

                else:
                    # Individual AOI polygons may still exceed the limit
                    # Use the original AOI polygons
                    newAOI = aoiLayer

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)



        else:
            # Multiple polygons and aoi acres is less than maximum.
            # Try sending a single convex hull spatial request

            if inCnt > 1:


                #if aoiAcres < maxAcres:
                if density < 15:
                    # Trying to come up with a factor that accounts for lower density and higher polygon count that
                    # would favor the single convex hull AOI.

                    # If the polygons are close together and not too huge, try a single convex hull
                    # If the convex hull is too large, the original dissolved featurelayer will be used instead

                    hullAOI, hullCnt = SimplifyAOI_Hull(dissAOI, inCnt)  # hullCnt should always be 1 or 0
                    if hullCnt == 1:
                        # Use single hullAOI polygon for spatial query
                        inCnt = 1
                        newAOI = hullAOI
                        PrintMsg(" \nShould be using convex hull polygon", 1)

                        with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                            for rec in cur:
                                oidList.append(rec[0])
                                #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

                    else:
                        # Using dissolved AOI instead of convex hull
                        newAOI = dissAOI
                        # I see that my Progress counter is not working correctly for this method

                        with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                            for rec in cur:
                                oidList.append(rec[0])
                                #PrintMsg("\tdissAOI: " + Number_Format(rec[0], 0, False), 1)

                else:
                    # polygons are widely spread, send dissolved featureclass one polygon at a time
                    PrintMsg(" \nUsing dissolved AOI layer with multiple, widely distributed polygons", 1)
                    newAOI = dissAOI

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

            else:
                # Send dissolved featureclass with a single polygon
                PrintMsg(" \nUsing dissolved layer having a single polygon", 1)
                newAOI = dissAOI

                with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                    for rec in cur:
                        oidList.append(rec[0])
                        #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

    totalAOIAcres, simpleAcres, simpleVert = GetLayerAcres(newAOI)

    PrintMsg(" \nRetrieving spatial data for " + Number_Format(len(oidList), 0, True) + " AOI polygon(s) with a total estimated area of " + Number_Format(totalAOIAcres, 0, True) + " acres", 0)

    idFieldName = arcpy.Describe(newAOI).oidFieldName

    if len(oidList) == 1 and totalAOIAcres > 5000:
        # Use single progressor with per polygon count
        #
        for id in oidList:
            # Process the single polygon in the AOI and display import progress
            wc = idFieldName + " = " + str(id)
            arcpy.SelectLayerByAttribute_management(newAOI, "NEW_SELECTION", wc)

            # Get information about the AOI
            polyAcres, xCnt, xVert = GetLayerAcres(newAOI) # for a single AOI polygon
            #PrintMsg(" \n\tSending request for AOI polygon number " + Number_Format(id, 0, False) + " (~" + Number_Format(polyAcres, 0, True) + " acres)", 0)

            if polyAcres == 0:
                raise MyError, "Selected extent is too small"

            if polyAcres <= maxAcres:
                # If selected AOI and overall extent is less than maxAcres, send request to SDA

                # Create spatial query string using simplified polygon coordinates
                spatialQuery, clipPolygon = FormSpatialQuery(newAOI)

                if spatialQuery != "":
                    # Send spatial query and use results to populate outputShp featureclass
                    outCnt = RunSpatialQuery(sdaURL, spatialQuery, outputShp, clipPolygon, True)

                    if outCnt == 0:
                        raise MyError, ""

            else:
                if polyAcres >= maxAcres:
                    raise MyError, "Overall extent of AOI polygon exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                else:
                    raise MyError, "Selected AOI polygon exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "


    else:
        # Processing small areas or multiple AOIs
        #
        arcpy.SetProgressor("step", "Importing spatial data for multiple AOIs", 0, len(oidList), 1)

        for id in oidList:
            # Begin polygon loop can be used to handle multiple polygon AOIs. Progress will be per AOI.
            wc = idFieldName + " = " + str(id)
            arcpy.SelectLayerByAttribute_management(newAOI, "NEW_SELECTION", wc)

            # Get information about the AOI
            polyAcres, xCnt, xVert = GetLayerAcres(newAOI) # for a single AOI polygon
            #PrintMsg(" \n\tSending request for AOI polygon number " + Number_Format(id, 0, False) + " (~" + Number_Format(polyAcres, 0, True) + " acres)", 0)

            if polyAcres == 0:
                raise MyError, "Selected extent is too small"

            if polyAcres <= maxAcres:
                # If selected AOI and overall extent is less than maxAcres, send request to SDA

                # Create spatial query string using simplified polygon coordinates
                spatialQuery, clipPolygon = FormSpatialQuery(newAOI)

                if spatialQuery != "":
                    # Send spatial query and use results to populate outputShp featureclass
                    outCnt = RunSpatialQuery(sdaURL, spatialQuery, outputShp, clipPolygon, False)

                    if outCnt == 0:
                        raise MyError, ""

                    else:
                        arcpy.SetProgressorPosition()

            else:
                if polyAcres >= maxAcres:
                    raise MyError, "Overall extent of AOI polygon exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                else:
                    raise MyError, "Selected AOI polygon exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "



    if hullCnt == 1:
        # Need to clip the output featureclass
        outputShp = ClipToAOI(dissAOI, outputShp)
    #
    # End of spatial requests
    #

    # Restore the original selected in the AOI layer
    if not aoiSelection is None:
        aoiLayer.setSelectionSet("NEW", aoiSelection)

    # Finished processing individual AOI polygons.
    # Dissolve any AOI boundaries and get a new polygon count.
    if aoiCnt > 1 and hullCnt <> 1:
        # If more than one AOI polygon, assume that the output soils need to be dissolved to remove
        # any clipping boundaries.
        #
        outputShp = FinalDissolve(outputShp)
        outCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        PrintMsg(" \nOutput soils layera has " + Number_Format(outCnt, 0, True) + " polygons", 0)

    outCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))

    if outCnt == 0:
        raise MyError, "No output found in " + outputShp

    if outCnt > 0:
        # Got spatial data...
        # Get list of mukeys for use in tabular request
        mukeyList = GetMukeys(outputShp)

        # Add necessary attribute fields to featureclass
        #if not AddNewFields(outputShp):
        #    raise MyError, "Problems adding new fields to " + output.Shp

        # Get attribute data (AWS) from SDA Tabular service
        ratingField ="AWS"
        prec = 2
        units = "cm"

        ratingValues = AttributeRequest(sdaURL, mukeyList, top, bot, outputShp)

        if len(ratingValues) == 0:
            raise MyError, ""

        arcpy.SetProgressorPosition()

        # Create spatial index for output featureclass
        arcpy.AddSpatialIndex_management (outputShp)

        # Add new map layer to ArcMap TOC
        aoiLayer.visible = False
        outputAcres = AddLayerToMap(outputShp, ratingField)

        if outputAcres > 0:
            # Compare AOI and output mapunit acres. If output acres is less,
            # assume that part of the AOI does not have SSURGO data. Warn user.
            #PrintMsg(" \nOutput acres: " + Number_Format(outputAcres, 0, True), 1)
            diffAcres = aoiAcres - outputAcres

            if diffAcres > 1.0:
                PrintMsg(" \nWarning. Output soils layer has " + Number_Format(diffAcres, 1, True) + " fewer acres than the AOI", 1 )

            elif diffAcres < -1.0:
                PrintMsg(" \nWarning! Output soils layer has " + Number_Format(abs(diffAcres), 1, True) + " more acres than the AOI", 1 )
                PrintMsg(" \nOverlapping soil polygons, need to move clip inside loop using newAOI layer", 1)

    else:
        raise MyError, "Failed to create output"

    # Return the AOI layer selection set back to original and turn the layer off
    #
    #aoiLayer.visible = False
    arcpy.RefreshTOC()
    arcpy.RefreshActiveView()

    if not aoiSelection is None:
        aoiLayer.setSelectionSet("NEW", aoiSelection)

    else:
        arcpy.SelectLayerByAttribute_management(aoiLayer, "CLEAR_SELECTION")

    if len(mukeyList) > 0:
        #PrintMsg(" \nOutput GML file: " + theGMLFile, 0)

        eMsg = elapsedTime(begin)

        PrintMsg(" \nElapsed time for SDA request: " + eMsg + " \n ", 0)

    else:
        PrintMsg("Failed to get spatial data from SDA", 2)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
