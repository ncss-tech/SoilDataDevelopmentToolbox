# SDA_SpatialQuery_Custom.py
#
# Steve Peaslee, National Soil Survey Center, August 2016
#
# Purpose:  Demonstration ArcTool for ArcMap, designed to query the Soil Data Access Tabular service
# for both spatial and attribute data and then import that data into a file geodatabase featureclass.
#
# User can copy-paste SQL into the third parameter. This script will generate the list of
# mukeys from the output spatial layer and enter them into the query automatically.
#
# SELECT MUSYM, MUNAME FROM mapunit mu WHERE mu.mukey IN (xxMUKEYSxx)  - need to add validation for xxMUKEYSxx!

# A map layer based upon the last numeric attribute will be automatically created.
# The Tabular service uses a MS SQLServer database. Both spatial and attribute queries
#
# If neccessary, the script will cycle through and query multiple AOIs to better
# handle widely disparate polygons.
# Only handles coordinate systems with NAD1983 or WGS1984 datums.
#
# Maybe add Harn transformations?
#
# Need to put in a limit for input polygons. Selecting an input with a large number
# of polygons can appear to hang the system.
#
# Added MinimumBoundingGeometry to LayerDensity function. This requires
# an Advanced license which may be a problem for some users. Probably
# need to find a way of checking and go back to the old method if
# Advanced is not available.
#

# Begin TEST SQL
"""SELECT  l.areasymbol
, m.mukey
, m.musym
, m.muname
INTO #Rn
FROM mapunit m INNER JOIN legend l ON m.lkey = l.lkey and m.mukey IN (xxMUKEYSxx)
Order by l.areasymbol, m.mukey

SELECT areasymbol
, #Rn.mukey
, musym
, muname
, comppct_r
, component.cokey
, compname
, h.chkey
, h.hzdept_r
, h.hzdepb_r
, (SELECT cast(max(hzdepb_r) as integer) from component c left outer join chorizon on c.cokey = chorizon.cokey where component.cokey = c.cokey and sandtotal_r is not null) as botdepth
, (SELECT CASE when min(resdept_r) is null then 201 else cast(min(resdept_r) as int) END from component cp left outer join corestrictions on cp.cokey =
corestrictions.cokey where component.cokey = cp.cokey and reskind is not null) as soil_depth
, case when (h.hzdepb_r - h.hzdept_r) = 0 then 0 else (h.hzdepb_r - h.hzdept_r) end AS thick
, CASE when ksat_r is null then 0 else cast(ksat_r as int) END as ksat_r
, CASE when om_r is null then 0 else cast(om_r as decimal (5,2)) END as om_r
, CASE when awc_r is null then 0 else cast(awc_r as decimal(4,2)) END as awc_r
, CASE when sandtotal_r is null then 0 else cast(sandtotal_r as int) END as sandtotal_r
, CASE when silttotal_r is null then 0 else cast(silttotal_r as int) END as silttotal_r
, CASE when claytotal_r is null then 0 else cast(claytotal_r as int) END as claytotal_r
INTO #file1
FROM #Rn
INNER JOIN component on #Rn.mukey=component.mukey and majcompflag = 'Yes'
INNER JOIN chorizon h on h.cokey = component.cokey
inner join chtexturegrp chtg on h.chkey = chtg.chkey and chtg.rvindicator = 'Yes'
INNER JOIN chtexture cht ON chtg.chtgkey=cht.chtgkey
ORDER by musym, muname, comppct_r desc, hzdept_r

--gather the horizon characters by thickness
SELECT #file1.areasymbol
, #file1.musym
, #file1.mukey
, #file1.cokey
, #file1.muname
, #file1.compname
, comppct_r
, #file1.chkey
, hzdept_r
, thick
,(thick*ksat_r) as ksat
,(thick*om_r) as om
,(thick*awc_r) as awc
,(thick*sandtotal_r) as sandtotal
,(thick*silttotal_r) as silttotal
,(thick*claytotal_r) as claytotal
,(SELECT CASE when min(resdept_r) is null then botdepth else cast(min(resdept_r) as int) END from component cp left outer join corestrictions on cp.cokey =
corestrictions.cokey where #file1.cokey = cp.cokey and reskind is not null) as soildepth
, soil_depth
, botdepth
INTO #file2
FROM #file1
ORDER BY #file1.mukey, #file1.cokey, hzdepb_r

--sum the thicknesses by component
Select areasymbol, musym, mukey, muname, cokey, compname, comppct_r, soildepth
, (sum(ksat)) as hzKsatsums
, (sum(om)) as hzOMsums
, (sum(awc)) as hzawcsums
, (sum(sandtotal)) as hzsandsums
, (sum(silttotal)) as hzsiltsums
, (sum(claytotal)) as hzclaysums
INTO #file3
From #file2
WHERE #file2.soildepth is not null and #file2.soildepth != 0 and hzdept_r < soildepth
Group by areasymbol, mukey, musym, muname, cokey, compname, comppct_r, soildepth
ORDER BY mukey, cokey

--develop a weighted average for each component by using the soildepth and comppct_r
Select distinct musym
, areasymbol
, mukey
, muname
, cokey
, compname
, comppct_r
, (hzKsatsums/soildepth)*comppct_r*.01 as wtavgKsat
, (hzOMsums/soildepth)*comppct_r*.01  as wtavgOM
, (hzawcsums/soildepth)*comppct_r*.01  as wtavgAWC
, (hzsandsums/soildepth)*comppct_r*.01 as wtavgSAND
, (hzsiltsums/soildepth)*comppct_r*.01 as wtavgSILT
, (hzclaysums/soildepth)*comppct_r*.01 as wtavgCLAY
INTO #file4
FROM #file3
ORDER BY mukey, cokey, comppct_r

--sum the component percent product to aggregate to the map unit
SELECT Areasymbol, Musym, Mukey, MuName
, (sum(wtavgKsat )) as KSat_WTA
, (sum(wtavgOM )) as OM_WTA
, (sum(wtavgAWC)) as  AWC_WTA
, (sum(wtavgSAND)) as Sand_WTA
, (sum(wtavgSILT)) as Silt_WTA
, (sum(wtavgCLAY )) as Clay_WTA
FROM #file4
Group by Areasymbol, Mukey, Musym, MuName"""

# End TEST SQL
#
#
# EPSG Reference
# Web Mercatur: 3857
# GCS WGS 1984: 4326
# GCS NAD 1983: 4269
# Albers USGS CONUS: 32145
#
# Input parameters
#
""" theAOI = arcpy.GetParameterAsText(0)     # polygon layer (honors selected set) used to define AOI
    outputShp = arcpy.GetParameterAsText(1)  # output soil polygon featureclass (GDB)
    sQuery = arcpy.GetParameterAsText(2)     # User SQL
    transparency = arcpy.GetParameter(3)     # transparency level for the output soils layer
    maxAcres = arcpy.GetParameter(4)         # maximum allowed area for the output EXTENT.
    sdaURL = arcpy.GetParameterAsText(5)     # Soil Data Access URL
"""

# At some point, it would be nice to store queries in a manner similar to the SDV tables.
# Since the SQL could return multiple types of data, it would be most appropriate to use
# JSON strings containing dictionaries and lists for items such as:
# field names, field aliases, field short description, field full metadata, description, field data type, field units, field aggregation method, field symbology,
# group name, group data level (mapunit, component, horizon), group description, group metadata,
# sql metadata, sql creation date, sql author(s)

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
    # requests will be on a per-polygon-basis or a single request for the entire extent
    #
    try:
        polyArea = 0.0
        polyAcres = 0.0
        polyCnt = 0
        vertCnt = 0
        desc = arcpy.Describe(theLayer)
        cs = desc.spatialReference
        dfcs = df.spatialReference

        # Method for general AOI area using Minimum Bounding Coordinates as a single convex hull
        # Warning! This method requires an Advanced license. Is that going to be a problem for some folks?
        #
        testAOI = os.path.join(env.scratchGDB, "testAOI")
        arcpy.MinimumBoundingGeometry_management(theLayer, testAOI, "CONVEX_HULL", "ALL", "", "NO_MBG_FIELDS")
        # get convex hull polygon geometry
        with arcpy.da.SearchCursor(testAOI, ["SHAPE@"]) as cur:
            for rec in cur:
                convexHull = rec[0]
                extentArea = convexHull.area
                extentAcres = convexHull.getArea("GREAT_ELLIPTIC", "ACRES")

        #PrintMsg("Input AOI extent acres using getArea() and " + dfcs.name + ": " + Number_Format(extentAcres, 1, True))

        with arcpy.da.SearchCursor(theLayer, ["SHAPE@"], "", dfcs) as cur:
            for rec in cur:
                polyCnt += 1
                polyArea += rec[0].getArea("GREAT_ELLIPTIC", "SQUAREMETERS")
                polyAcres += rec[0].getArea("GREAT_ELLIPTIC", "ACRES")
                #polyArea += rec[0].area
                vertCnt += rec[0].pointCount

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
        return 0, 0, 0, 0, 0

    except:
        errorMsg()
        return 0, 0, 0, 0, 0

## ===================================================================================
def ClipToAOI(theAOI, outputShp):
    # Clip intersected soils layer using original AOI polygons
    #
    try:
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
        sQuery = bQuery.replace("xxMUKEYSxx", mukeys)
        #PrintMsg(" \n" + sQuery, 1)


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
        outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \nRequesting tabular data for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        mukeys = ",".join(mukeyList)

        sQuery = FormAttributeQuery(sQuery, mukeys)  # Combine user query with list of mukeys from spatial layer.
        if sQuery == "":
            raise MyError, ""

        # Tabular service to append to SDA URL
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"
        dRequest["QUERY"] = sQuery

        PrintMsg(" \nURL: " + url)
        PrintMsg("FORMAT: " + "JSON")
        PrintMsg("QUERY: " + sQuery)

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        #PrintMsg(" \njsonString: " + str(jsonString), 1)
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        if len(mukeyList) != len(dataList):
            PrintMsg(" \nWarning! Only returned data for " + str(len(dataList)) + " mapunits", 1)

        PrintMsg(" \nImporting attribute data...", 0)
        newFields = AddNewFields(outputShp, columnNames, columnInfo)
        if len(newFields) == 0:
            raise MyError, ""

        ratingField = newFields[-1]  # last field in query will be used to symbolize output layer

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
        if ratingField in columnNames:
            outputIndx = columnNames.index(ratingField)  # Use to identify attribute that will be mapped

        else:
            raise MyError, "Failed to find output field '" + ratingField + "' in " + ", ".join(columnNames)


        # Reading the attribute information returned from SDA Tabular service
        #
        arcpy.SetProgressorLabel("Importing attribute data...")

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
        maxminValues = list()



        # Write the attribute data to the featureclass table
        #
        if ratingType.upper() in ['FLOAT', 'DOUBLE']:
            #PrintMsg(" \nSaving data, floating point values", 1)
            #PrintMsg(" \n" + ", ".join(columnNames), 1)

            with arcpy.da.UpdateCursor(outputShp, columnNames) as cur:
                for rec in cur:
                    try:
                        mukey = rec[mukeyIndx]
                        newrec = dMapunitInfo[mukey]
                        #PrintMsg(str(newrec), 0)
                        cur.updateRow(newrec)
                        maxminValues.append(float(newrec[outputIndx]))

                    except:
                        if not mukey in noMatch:
                            noMatch.append(mukey)

            if len(noMatch) > 0:
                PrintMsg(" \nNo attribute data for mukeys: " + str(noMatch), 1)

            if len(maxminValues) == 0:
                raise MyError, "No data for this property"

            elif len(maxminValues) > 1:
                distinctValues = set(maxminValues)
                outputValues = list()

                try:
                    distinctValues.remove(None)

                except:
                    pass

                outputValues.append(min(distinctValues))
                outputValues.append(max(distinctValues))

            else:
                # Only a single value for the selected property
                outputValues = [maxminValues[0], maxminValues[0]]

            # End of Floating point data

        elif ratingType.upper() in ['INTEGER', 'SMALLINTEGER']:
            #PrintMsg(" \nSaving data, integer values", 1)
            #PrintMsg(" \n" + ", ".join(columnNames), 1)

            with arcpy.da.UpdateCursor(outputShp, columnNames) as cur:
                for rec in cur:
                    mukey = rec[mukeyIndx]  # get mukey from polygon attribute

                    if mukey in dMapunitInfo:
                        newrec = dMapunitInfo[mukey]  # get attribute data from dictionary
                        cur.updateRow(newrec)         # update the other polygon attributes from the dictionary data
                        value = newrec[outputIndx]    # get the rating value from the attribute data
                        #PrintMsg("\tAdding data " + str(newrec), 0)
                        if not value is None:
                            maxminValues.append(int(value))

                    else:
                        # Probably a spatial map unit that does not have a corresponding
                        # mukey in the attribute data.
                        #PrintMsg("\tSkipping integer data record " + str(rec), 1)
                        if not mukey in noMatch:
                            noMatch.append(mukey)

            if len(noMatch) > 0:
                PrintMsg(" \nNo attribute data for mukeys: " + str(noMatch), 1)

            if len(maxminValues) > 0:
                distinctValues = set(maxminValues)
                outputValues = list()

                try:
                    distinctValues.remove(None)

                except:
                    pass

                #

                # Need to take a closer look at the way I am getting min-max values!!!!!
                #
                if ratingType.upper() in ['FLOAT', 'DOUBLE']:
                    # Return just the min-max values
                    outputValues.append(min(distinctValues))
                    outputValues.append(max(distinctValues))

                elif ratingType.upper() in ['INTEGER', 'SMALLINTEGER']:
                    # return a list of integer values
                    outputValues = list(distinctValues)
                    outputValues.sort()

            else:
                # Only one unique value found
                outputValues = [maxminValues[0], maxminValues[0]]


            # End of Integer data

        elif ratingType.upper() == 'STRING':
            #PrintMsg(" \nSaving data, string values", 1)

            with arcpy.da.UpdateCursor(outputShp, columnNames) as cur:
                for rec in cur:
                    try:
                        mukey = rec[mukeyIndx]
                        newrec = dMapunitInfo[mukey]
                        #PrintMsg(str(newrec), 0)
                        cur.updateRow(newrec)
                        maxminValues.append(newrec[outputIndx])

                    except:
                        if not mukey in noMatch:
                            noMatch.append(mukey)

            if len(noMatch) > 0:
                PrintMsg(" \nNo attribute data for mukeys: " + str(noMatch), 1)

            if len(maxminValues) > 1:
                distinctValues = set(maxminValues)

                try:
                    distinctValues.remove(None)

                except:
                    pass

                outputValues = list(distinctValues)
                outputValues.sort()
                #PrintMsg(" \n" + ratingField + " range values: " + str(distinctValues), 1)

            # End of String data

        else:
            raise MyError, "Unmatched data type: " + dataType.upper()


        PrintMsg(" \n" + ratingField + " range values: " + str(outputValues), 1)

        arcpy.SetProgressorLabel("Finished importing attribute data")

        return outputValues

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputValues

    except urllib2.HTTPError:
        errorMsg()
        PrintMsg(" \n" + sQuery, 1)
        return outputValues

    except:
        errorMsg()
        return outputValues


## ===================================================================================
def GetSDVAtts(theURL, outputFields):
    #
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    # This function is a work in progress. It is only useful when the output fields
    # match the original field names in the database. I can't think of any easy way to
    # to do this.
    #
    try:

        # Create two dictionaries, one for properties and another for interps
        dProperties = dict()  # key is attributecolumnname
        dInterps = dict()     # key is attributename


        # convert list of output fields from spatial layer to a comma-delimited list
        columns = "('" + "', '".join(outputFields) + "')"

        # Cannot read this entire table using JSON format. Too long.
        #
        sdvQuery = """select sdvfolder.foldername,
        attributekey, attributename, attributetablename, attributecolumnname,
        attributelogicaldatatype, attributefieldsize, attributeprecision,
        attributedescription, attributeuom, attributeuomabbrev, attributetype,
        nasisrulename, ruledesign, notratedphrase, mapunitlevelattribflag,
        complevelattribflag, cmonthlevelattribflag, horzlevelattribflag,
        tiebreakdomainname, tiebreakruleoptionflag, tiebreaklowlabel,
        tiebreakhighlabel, tiebreakrule, resultcolumnname, sqlwhereclause,
        primaryconcolname, pcclogicaldatatype, primaryconstraintlabel,
        secondaryconcolname, scclogicaldatatype, secondaryconstraintlabel,
        dqmodeoptionflag, depthqualifiermode, layerdepthtotop, layerdepthtobottom,
        layerdepthuom, monthrangeoptionflag, beginningmonth, endingmonth,
        horzaggmeth, interpnullsaszerooptionflag, interpnullsaszeroflag,
        nullratingreplacementvalue, rptnullratingreplacevalue, basicmodeflag,
        maplegendkey, maplegendclasses, maplegendxml, nasissiteid, sdvfolder.wlupdated,
        algorithmname, componentpercentcutoff, readytodistribute,
        effectivelogicaldatatype, reviewrequested, editnotes from sdvattribute
        inner join sdvfolder on sdvattribute.folderkey = sdvfolder.folderkey
        where sdvattribute.attributecolumnname in xxCOLUMNSxx"""
        sdvQuery = sdvQuery.replace("xxCOLUMNSxx", columns)

        PrintMsg(" \nRequesting tabular data for SDV attribute information...", 0)
        #PrintMsg(" \n" + sdvQuery, 1)
        arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        # Tabular service to append to SDA URL
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"
        #dRequest["FORMAT"] = "XML"
        dRequest["QUERY"] = sdvQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        #PrintMsg(" \njsonString: " + str(jsonString), 1)
        data = json.loads(jsonString)
        del jsonString, resp, req

        if not "Table" in data:
            raise MyError, "Query failed to select anything: \n " + sdvQuery

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        typeIndex = columnNames.index("attributetype")
        attIndex = columnNames.index("attributename")
        colIndex = columnNames.index("attributecolumnname")

        for sdvInfo in dataList:
            # Read through requested data and load into the proper dictionary
            dProperties[sdvInfo[colIndex]] = sdvInfo

            if sdvInfo[typeIndex].lower() == "property":
                # Interp
                dInterps[sdvInfo[attIndex]] = sdvInfo


        PrintMsg(" \nGot tabular data for " + str(len(dProperties)) + " SDV Attribute records...")
        return dProperties

    except:
        errorMsg()
        return dProperties

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
    # Given the path for the new output featureclass, create it as polygon and add required fields
    # Later it will be populated using a cursor

    try:
        # Setup output coordinate system (same as input AOI) and datum transformation.
        # Please note! Only handles WGS1984 and NAD1983 datums.
        outputCS = arcpy.Describe(theAOI).spatialReference
        # These next two lines set the output coordinate system environment

        env.geographicTransformations = tm

        outputTbl = os.path.join("IN_MEMORY", os.path.basename(outputShp))

        # Create empty polygon featureclass
        arcpy.CreateFeatureclass_management(os.path.dirname(outputShp), os.path.basename(outputShp), "POLYGON", "", "DISABLED", "DISABLED", outputCS)

        arcpy.AddField_management(outputShp,"mukey", "TEXT", "", "", "30")   # for outputShp

        #tmpFields = arcpy.Describe(outputShp).fields
        #tmpList = list()
        #for fld in tmpFields:
        #    tmpList.append(fld.name)

        #PrintMsg(" \nPermanent fields: " + ", ".join(tmpList), 1)

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

        # Strip "MULTI" off as well as leading and trailing (). Not sure why SDA doesn't like MULTIPOLYGON.
        wkt = wkt.replace("MULTIPOLYGON (", "POLYGON ")[:-1]

        sdaQuery = """
 ~DeclareGeometry(@aoi)~
 select @aoi = geometry::STPolyFromText('""" + wkt + """', 4326)

 --   Extract all intersected polygons
 ~DeclareIdGeomTable(@intersectedPolygonGeometries)~
 ~GetClippedMapunits(@aoi,polygon,geo,@intersectedPolygonGeometries)~

 --   Convert geometries to geographies so we can get areas
 ~DeclareIdGeogTable(@intersectedPolygonGeographies)~
 ~GetGeogFromGeomWgs84(@intersectedPolygonGeometries,@intersectedPolygonGeographies)~

 --   Return WKT for the polygonal geometries
 select * from @intersectedPolygonGeographies
 where geog.STGeometryType() = 'Polygon'"""

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
def RunSpatialQuery(theURL, spatialQuery, outputShp, clipPolygon, showStatus):
    # XML format
    # Send spatial query to SDA Tabular Service
    #
    # XML format returned. Converts WKT data to a polygon featureclass
    # The 2016 version of SDA has a limit on JSON formatted data, but the XML version does not.

    try:
        #PrintMsg(" \n\tProcessing spatial request on " + theURL)
        #arcpy.SetProgressor("default", "Requesting spatial data for polygon " + Number_Format(polyNum, 0, True))

        #PrintMsg(" \n" + spatialQuery, 0)

        # Send XML query to SDM Access service
        #
        url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        #PrintMsg(" \nProcessing spatial request using " + url + " with XML output", 1)

        dRequest = dict()
        dRequest["FORMAT"] = "XML"
        dRequest["QUERY"] = spatialQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)

        resp = urllib2.urlopen(req)  # A failure here will probably throw an HTTP exception

        responseStatus = resp.getcode()
        responseMsg = resp.msg

        xmlString = resp.read()
        resp.close()
        #PrintMsg(" \n" + xmlString + " \n ", 1)


        # See if I can get an estimated polygon count from the XML string

        # Convert XML to tree format
        root = ET.fromstring(xmlString)
        #PrintMsg(" \n" + xmlString, 1)
        polys = xmlString.count("POLYGON")

        PrintMsg("\tRequest returned " + Number_Format(polys, 0, True) + " soil polygons...", 0)


        if showStatus:
            step = 1
            arcpy.SetProgressor("step", "Importing spatial data", 0, polys, step)

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

                        if showStatus:
                            arcpy.SetProgressorPosition()
                            #arcpy.SetProgressorLabel("Polygon " + Number_Format(polyCnt, 0, True))

            arcpy.SetProgressorLabel("Completed spatial import")
            #PrintMsg("Completed spatial import", 1)

        else:
            # Input and output coordinate system is the same. No projection
            # from original GCS WGS 1984.
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

                        if outputPolygon is None:
                            PrintMsg(" \nFound null geometry...", 1)

                        rec = [outputPolygon, mukey]
                        cur.insertRow(rec)
                        polyCnt += 1

                        if showStatus:
                            arcpy.SetProgressorPosition()
                            #arcpy.SetProgressorLabel("Polygon " + Number_Format(polyCnt, 0, True))

            arcpy.SetProgressorLabel("Completed spatial import")
            #PrintMsg("Completed spatial import", 1)

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
def RunSpatialQueryJSON(theURL, spatialQuery, outputShp, clipPolygon, showStatus):
    # JSON format
    # Send spatial query to SDA Tabular Service
    #
    # Format JSON table containing records with MUKEY and WKT Polygons to a polygon featureclass
    #
    # Currently problems with JSON format using POST REST.
    # MaxJsonLength is appparently set to the default value of 102,400 characters. Need to set to Int32.MaxValue?
    # This limit does not affect the XML option.

    try:
        # Tabular service to append to SDA URL
        url = theURL + "/" + "Tabular/SDMTabularService/post.rest"
        #PrintMsg(" \n\tProcessing spatial request using " + url + " with JSON output", 1)
        #PrintMsg(" \n" + spatialQuery, 1)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON"
        #dRequest["FORMAT"] = "'JSON + METADATA + COLUMN"
        dRequest["QUERY"] = spatialQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)
        PrintMsg(" \nURL: " + url)
        PrintMsg("FORMAT: " + "JSON")
        PrintMsg("QUERY: " + spatialQuery)

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

        time.sleep(1)
        arcpy.ResetProgressor()
        arcpy.SetProgressorLabel("Completed spatial import")


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
                    if not rec[0] in mukeyList:
                        mukeyList.append(rec[0])


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
def AddLayerToMap(outputShp, ratingField, ratingType, ratingLength):
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
        #PrintMsg(" \nData frame scale is  1:" + Number_Format(df.scale, 0, True), 1)

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

            if ratingType.upper() in ['FLOAT', 'DOUBLE']:
                #PrintMsg(" \nGetting unique values legend", 1)
                dLayerDefinition = ClassBreaksJSON(ratingValues, drawOutlines, ratingField)

            elif ratingType.upper() in ['INTEGER', 'SMALLINTEGER']:
                #PrintMsg(" \nGetting unique values legend", 1)
                #dLayerDefinition = UniqueValuesJSON(ratingValues, drawOutlines, ratingField, ratingLength)
                dLayerDefinition = IntegerValuesJSON(ratingValues, drawOutlines, ratingField, ratingLength)

            elif ratingType.upper() == 'STRING':
                #PrintMsg(" \nGetting class breaks legend", 1)
                dLayerDefinition = UniqueValuesJSON(ratingValues, drawOutlines, ratingField, ratingLength)

            else:
                raise MyError, "Unmatched data type: " + ratingType.upper()

            if dLayerDefinition is None or len(dLayerDefinition) == 0:
                raise MyError, ""



            newLayer.updateLayerFromJSON(dLayerDefinition)
            newLayer.name = "SDM " + ratingField.title()
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
def ClassBreaksJSON(ratingValues, drawOutlines, ratingField):
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

    # Seems to be a problem when creating a legend for integer values? My percent sand ranges from 5 to 17, but my legend is created for 5 - 15.
    # Simple fix. Converted the two min-max values to float in the AttributeRequest function.


    try:
        # Set outline symbology according to map scale. Small scale
        d = dict() # initialize return value

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
        d["field"] = ratingField
        d["drawingInfo"] = dict() # new
        #d["defaultSymbol"]["outline"]["color"] = outLineColor

        # Set minimum and maximum values for legend
        minValue = ratingValues[0]

        if len(ratingValues) == 1:
            # Only a single value in the data. Make min and max the same.
            maxValue = minValue

        else:
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
                    label = str(lastMax) + "-> " + str(ratingValue)
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
def UniqueValuesJSON(ratingValues, drawOutlines, ratingField, ratingLength):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    try:
        d = dict() # initialize return value

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

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
        d["name"] = ratingField.title()
        d["description"] = "Web Soil Survey Thematic Map"
        d["definitionExpression"] = ""
        d["geometryType"] = "esriGeometryPolygon"
        d["parentLayer"] = None
        d["subLayers"] = []
        d["defaultVisibility"] = True
        d["hasAttachments"] = False
        d["htmlPopupType"] = "esriServerHTMLPopupTypeNone"
        d["drawingInfo"]["renderer"]["type"] = "uniqueValue"
        d["drawingInfo"]["renderer"]["field1"] = ratingField
        d["displayField"] = ratingField
        #PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)

        # Add new rating field to list of layer fields
        dAtt = dict()
        dAtt["name"] = ratingField
        dAtt["alias"] = ratingField
        dAtt["type"] = "esriFieldTypeString"
        d["fields"].append(ratingField)

        try:
            length = ratingLength

        except:
            length = 254

        dAtt["length"] = length

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        for cnt in range(0, len(ratingValues)):
            dSymbol = dict()

            rating = ratingValues[cnt]

            #PrintMsg(" \tAdding to legend: " + label + "; " + rating + "; " + hexCode, 1)
            # calculate rgb colors
            #rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            rgb = [randint(0, 255), randint(0, 255), randint(0, 255), 255]

            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}

            legendItems = dict()
            legendItems["value"] = rating

            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating

            legendItems["label"] = str(rating)

            legendItems["symbol"] = symbol
            d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : ratingField, "field2" : None, "field3" : None}
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
def IntegerValuesJSON(ratingValues, drawOutlines, ratingField, ratingLength):
    # returns JSON string for integer values template. Use this for Integer and SmallInteger
    #
    try:
        d = dict() # initialize return value

        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        colorList = CreateColorRamp(ratingValues)

        if len(colorList) == 0:
            raise MyError, ""

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
        d["name"] = ratingField.title()
        d["description"] = "Web Soil Survey Thematic Map"
        d["definitionExpression"] = ""
        d["geometryType"] = "esriGeometryPolygon"
        d["parentLayer"] = None
        d["subLayers"] = []
        d["defaultVisibility"] = True
        d["hasAttachments"] = False
        d["htmlPopupType"] = "esriServerHTMLPopupTypeNone"
        d["drawingInfo"]["renderer"]["type"] = "uniqueValue"
        d["drawingInfo"]["renderer"]["field1"] = ratingField
        d["displayField"] = ratingField
        #PrintMsg(" \n[drawingInfo][renderer][field1]: " + str(d["drawingInfo"]["renderer"]["field1"]) + " \n ",  1)

        # Add new rating field to list of layer fields
        dAtt = dict()
        dAtt["name"] = ratingField
        dAtt["alias"] = ratingField
        dAtt["type"] = "esriFieldTypeString"
        d["fields"].append(ratingField)

        try:
            length = ratingLength

        except:
            length = 254

        dAtt["length"] = length

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        for cnt in range(0, len(ratingValues)):
            dSymbol = dict()

            rating = ratingValues[cnt]
            rgb = colorList[cnt]

            #PrintMsg(" \tAdding to legend: " + label + "; " + rating + "; " + hexCode, 1)
            # calculate rgb colors
            #rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            #rgb = [randint(0, 255), randint(0, 255), randint(0, 255), 255]

            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}

            legendItems = dict()
            legendItems["value"] = rating

            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating

            legendItems["label"] = str(rating)

            legendItems["symbol"] = symbol
            d["drawingInfo"]["renderer"] = {"type" : "uniqueValue", "field1" : ratingField, "field2" : None, "field3" : None}
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
def CreateColorRamp(outputValues):
    # Given a list of integer values, return an ordered list of RGB colors in hex

    try:
        # Sort first
        outputValues.sort()  # low to high, same as ArcMap legend
        #
        # Example of colorList
        # colorList = [(255,34,0,255), (255,153,0,255), (255,255,0,255), (122,171,0,255), (0,97,0,255)]  # RGB, Red to Green, 5 colors

        cmin = outputValues[0]
        cmax = outputValues[-1]
        colorList = list()

        for value in outputValues:

            try:
                x = float(value-cmin)/(cmax-cmin)

            except ZeroDivisionError:
                x = 0.5 # cmax == cmin

            # floating point values 0.0 - 1.0

            red   = int(255 * min((max((4*(x-0.25), 0.)), 1.)))
            green = int(255 * min((max((4*math.fabs(x-0.5)-1., 0.)), 1.)))
            blue  = int(255 * min((max((4*(0.75-x), 0.)), 1.)))
            colorList.append((red, green, blue, 255))

            #hex = "#%02x%02x%02x" % red, green, blue
        #PrintMsg(" \n" + str(colorList))

        return colorList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)

    except:
        errorMsg()

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
from random import randint

try:
    # Create geoprocessor object
    #gp = arcgisscripting.create(9.3)

    # Get input parameters
    #
    theAOI = arcpy.GetParameterAsText(0)     # polygon layer (honors selected set) used to define AOI
    outputShp = arcpy.GetParameterAsText(1)  # output soil polygon featureclass (GDB)
    sQuery = arcpy.GetParameterAsText(2)     # User SQL
    transparency = arcpy.GetParameter(3)     # transparency level for the output soils layer
    maxAcres = arcpy.GetParameter(4)         # maximum allowed area for the output EXTENT.
    sdaURL = arcpy.GetParameterAsText(5)     # Soil Data Access URL

    # ratingField should be the last column in the output table.

    # I noticed that when I pasted a long query string in the menu that it was truncated at 2930 characters
    # Need to confirm this through more testing
    #
    maxString = 250000

    if len(sQuery) > maxString:
        raise MyError, "Check input query string for truncation beyond " + Number_Format(maxString, 0, True)


    # Commonly used EPSG numbers
    epsgWM = 3857 # Web Mercatur
    epsgWGS = 4326 # GCS WGS 1984
    epsgNAD83 = 4269 # GCS NAD 1983
    epsgAlbers = 102039 # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
    #tm = "WGS_1984_(ITRF00)_To_NAD_1983"  # datum transformation supported by this script

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

    if density == 0:
        raise MyError, ""

    #if aoiAcres > maxAcres:
    #    raise MyError, "Selected area exceeds set limit for number of acres in the AOI"

    maxPolys = 16000

    if aoiCnt > maxPolys:
        raise MyError, "Selected number of polygons exceeds limit of " + Number_Format(maxPolys, 0, True) + " polygons"

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
        # Single polygon AOI, use original AOI to generate spatial request

        if aoiAcres > maxAcres:
            raise MyError, "Selected area exceeds set limit for number of acres in the AOI"

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
        # Muliple polygons present in the original AOI layer
        #
        # Start by dissolving AOI and getting a new polygon count
        # Go ahead and create dissolved layer for use in clipping
        dissAOI, inCnt = SimplifyAOI_Diss(theAOI, inCnt)
        PrintMsg(" \nCreated dissolved layer with " + Number_Format(inCnt, 0, True) + " polygons", 1)

        #if aoiAcres > maxAcres or density > 1000:   # trying to get bent pipeline to process as multiple AOIs

        if aoiAcres > maxAcres:
            # A single convex hull AOI would be too big, try using individual dissolved polygons

            if inCnt == 1:
                # This is a too big area that dissolved to a single polygon or a widely spread, multipolygon area
                #
                if density < 2:
                    PrintMsg(" \nSingle dissolved AOI would be too large, switching back to individual AOIs", 1)
                    newAOI = aoiLayer
                    iCnt = 0

                    with arcpy.da.SearchCursor(newAOI, ["OID@", "SHAPE@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])

                            if rec[1].getArea("GREAT_ELLIPTIC", "ACRES") > maxAcres:
                                raise MyError, "Selected AOI polygon " + str(iCnt) + " exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                            iCnt += 1

                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

                else:
                    # Dissolved AOI might work
                    #raise MyError, "Overall extent of AOI polygon exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                    PrintMsg(" \nUsing dissolved big AOI", 1)
                    newAOI = dissAOI

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])
                            #PrintMsg("\t" + newAOI.name + ": " + Number_Format(rec[0], 0, False), 1)

            elif inCnt > 1 and density < 1.5:
                if density > 1.5 or aoiAcres > maxAcres:
                    # Dissolved AOI would be too big or too widespread. Use the original AOI
                    PrintMsg(" \nSingle dissolved AOI would be too large, switching back to original AOI polygons", 1)
                    newAOI = aoiLayer
                    iCnt = 0

                    with arcpy.da.SearchCursor(newAOI, ["OID@", "SHAPE@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])

                            if rec[1].getArea("GREAT_ELLIPTIC", "ACRES") > maxAcres:
                                raise MyError, "Selected AOI polygon " + str(iCnt) + " exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

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
                iCnt = 0

                if ((aoiAcres / inCnt) < maxAcres):
                    # Use the multiple, dissolved polygons to generate spatial request
                    PrintMsg(" \nUsing multiple, dissolved AOI polygons", 1)
                    newAOI = dissAOI

                    with arcpy.da.SearchCursor(newAOI, ["OID@", "SHAPE@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])

                            if rec[1].getArea("GREAT_ELLIPTIC", "ACRES") > maxAcres:
                                raise MyError, "Selected AOI polygon " + str(iCnt) + " exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                            iCnt += 1

                            #PrintMsg("\tdissAOI: " + Number_Format(rec[0], 0, False), 1)

                else:
                    # Individual AOI polygons may still exceed the limit
                    # Use the original AOI polygons
                    PrintMsg(" \nUsing multiple, original AOI polygons", 1)
                    iCnt = 0
                    newAOI = aoiLayer

                    with arcpy.da.SearchCursor(newAOI, ["OID@"]) as cur:
                        for rec in cur:
                            oidList.append(rec[0])

                            if rec[1].getArea("GREAT_ELLIPTIC", "ACRES") > maxAcres:
                                raise MyError, "Selected AOI polygon " + str(iCnt) + " exceeds " + Number_Format(maxAcres, 0, True) + " acre limit \n "

                            iCnt += 1
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
                        PrintMsg(" \nUsing single, convex hull polygon", 1)

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


    #
    # Once the most effecient AOI layer has been created (original, dissolved or convex hull), form the spatial query and
    # send it to SDA.
    #
    #
    totalAOIAcres, simpleCnt, simpleVert = GetLayerAcres(newAOI)

    PrintMsg(" \nRequesting spatial data for " + Number_Format(len(oidList), 0, True) + " AOI polygon(s), estimated at " + Number_Format(totalAOIAcres, 0, True) + " acres", 0)

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
                #
                #
                spatialQuery, clipPolygon = FormSpatialQuery(newAOI)
                #

                if spatialQuery != "":
                    # Send spatial query and use results to populate outputShp featureclass
                    outCnt = RunSpatialQueryJSON(sdaURL, spatialQuery, outputShp, clipPolygon, False)

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
        arcpy.SetProgressorLabel("Clipping output soil polygons to AOI...")
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
        arcpy.SetProgressorLabel("Removing overlap areas...")
        outputShp = FinalDissolve(outputShp)
        outCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        PrintMsg(" \nOutput soils layer has " + Number_Format(outCnt, 0, True) + " polygons", 0)

    outCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))

    if outCnt == 0:
        raise MyError, "No output found in " + outputShp

    if outCnt > 0:
        # Got spatial data...


        # Get list of mukeys for use in tabular request
        mukeyList = GetMukeys(outputShp)

        ratingValues = AttributeRequest(sdaURL, mukeyList, outputShp, sQuery)  # Need to get ratingField here

        outputFields = arcpy.Describe(outputShp).fields
        fieldList = list()

        for lastField in outputFields:
            ratingField = lastField.name
            ratingType = lastField.type
            ratingLength = lastField.length
            fieldList.append(ratingField)


        if len(ratingValues) == 0:
            raise MyError, ""

        # Get SDV information
        dProperties = GetSDVAtts(sdaURL, fieldList)

        # Create spatial index for output featureclass
        arcpy.AddSpatialIndex_management (outputShp)

        # Add new map layer to ArcMap TOC
        aoiLayer.visible = False
        outputAcres = AddLayerToMap(outputShp, ratingField, ratingType, ratingLength)

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
    #arcpy.RefreshTOC()
    #arcpy.RefreshActiveView()

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
