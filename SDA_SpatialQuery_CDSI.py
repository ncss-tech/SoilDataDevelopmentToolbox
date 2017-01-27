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
# outputField = arcpy.GetParameterAsText(2)
# transparency = arcpy.GetParameter(3)     # transparency level for the output soils layer
# maxAcres = arcpy.GetParameter(4)         # maximum allowed area for the spatial query.
# sdaURL = arcpy.GetParameterAsText(5)     # Soil Data Access URL

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
        outputTbl = os.path.join("IN_MEMORY", "CDSI_Tmp")
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
            #PrintMsg(" \nBegin JoinField", 1)
            arcpy.JoinField_management(outputShp, "mukey", outputTbl, "mukey", joinFields)
            #PrintMsg(" \nCompleted JoinField", 1)
            return True

        else:
            return False

    except:
        errorMsg()
        return False

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
def FormAttributeQuery(mukeys):
    #
    # Given a simplified polygon layer, use vertices to form the spatial query for a Tabular request
    # Coordinates are GCS WGS1984 and format is WKT.
    # Returns spatial query (string) and clipPolygon (geometry)
    #
    # input parameter 'mukeys' is a comma-delimited and single quoted list of mukey values
    #
    try:


        sQuery = """--all fields are based on the representative values of the dominant component (dcp) unless otherwise noted (_dcd) for dominant condition of the map unit
--Begin SQL
SELECT
-- grab survey area data
LEFT((areasymbol), 2) as state
, l.areasymbol
, l.areaname

--grab map unit level information

, mu.mukey
, mu.musym
, mu.nationalmusym
, mu.muname
, mukind
, mu.muacres
, farmlndcl
--take the worst case R and C factor for resource planning if multiples appear in a survey area
, (SELECT TOP 1 (CAST (laoverlap.areasymbol AS int)) FROM laoverlap WHERE laoverlap.areatypename Like 'Rainfall Factor Area%' and l.lkey=laoverlap.lkey GROUP BY laoverlap.areasymbol ORDER BY laoverlap.areasymbol desc) as Rfact
, (SELECT TOP 1 (CAST (laoverlap.areasymbol AS int)) FROM laoverlap WHERE laoverlap.areatypename Like 'Climate Factor Area%' and l.lkey=laoverlap.lkey GROUP BY laoverlap.areasymbol ORDER BY laoverlap.areasymbol desc) as Cfact

--grab component level information

, c.majcompflag
, c.comppct_r
, c.compname
, compkind
, (mu.muacres*c.comppct_r/100) AS compacres
, localphase
, slope_l
, slope_r
, slope_h
, CASE WHEN slopelenusle_r is not null Then (slopelenusle_r * 3.28)
       WHEN slope_r >= 0 And slope_r < 0.75 Then 100
       WHEN slope_r >= 0.75 And slope_r < 1.5 Then 200
       WHEN slope_r >= 1.5 And slope_r < 2.5 Then 300
       WHEN slope_r >= 2.5 And slope_r < 3.5 Then 200
       WHEN slope_r >= 3.5 And slope_r < 4.5 Then 180
       WHEN slope_r >= 4.5 And slope_r < 5.5 Then 160
       WHEN slope_r >= 5.5 And slope_r < 6.5 Then 150
       WHEN slope_r >= 6.5 And slope_r < 7.5 Then 140
       WHEN slope_r >= 7.5 And slope_r < 8.5 Then 130
       WHEN slope_r >= 8.5 And slope_r < 9.5 Then 125
       WHEN slope_r >= 9.5 And slope_r < 10.5 Then 120
       WHEN slope_r >= 10.5 And slope_r < 11.5 Then 110
       WHEN slope_r >= 11.5 And slope_r < 12.5 Then 100
       WHEN slope_r >= 12.5 And slope_r < 13.5 Then 90
       WHEN slope_r >= 13.5 And slope_r < 14.5 Then 80
       WHEN slope_r >= 14.5 And slope_r < 15.5 Then 70
       WHEN slope_r >= 15.5 And slope_r < 17.5 Then 60
       Else 50 END as slopelenusle_r
, (slopelenusle_r*3.25) AS slopelengthFT
, (SELECT CASE
        WHEN slope_r <1 THEN 0.2223
        WHEN slope_r <2 THEN 0.2684
        WHEN slope_r <3 THEN 0.3348
        WHEN slope_r <4 THEN 0.4001
        WHEN slope_r <5 THEN 0.4465
        WHEN slope_r <6 THEN 0.4732
        WHEN slope_r <7 THEN 0.4869
        WHEN slope_r <8 THEN 0.4936
        WHEN slope_r <9 THEN 0.4969
        WHEN slope_r <10 THEN 0.4985
        ELSE 0.5
        END) AS mexp_h
, case when nirrcapscl is null then nirrcapcl else nirrcapcl + nirrcapscl end as nirrcapclass
, case when nirrcapscl is null then irrcapcl else irrcapcl + irrcapscl end as irrcapclass
, drainagecl
, runoff
, hydgrp
, hydgrpdcd
, hydricrating
, hydclprs
, (SELECT TOP 1 hydriccriterion FROM cohydriccriteria WHERE c.cokey = cohydriccriteria.cokey) as hydric_criteria
, corsteel
, corcon
, frostact
, tfact
, weg
, wei
, (SELECT TOP 1 coecoclass.ecoclassid FROM component LEFT OUTER JOIN coecoclass on component.cokey = coecoclass.cokey WHERE coecoclass.cokey = c.cokey) as ecositeID
, (SELECT TOP 1 coecoclass.ecoclassname FROM component LEFT OUTER JOIN coecoclass on component.cokey = coecoclass.cokey WHERE coecoclass.cokey = c.cokey) as ecositename
, constreeshrubgrp
, (SELECT TOP 1 coecoclass.ecoclassid FROM component INNER JOIN coecoclass on component.cokey = coecoclass.cokey and ecoclasstypename like '%forage%' WHERE coecoclass.cokey = c.cokey ) as foragesuitgroupid
, foragesuitgrpid
, rsprod_r
, taxclname
, taxorder
, taxsuborder
, taxgrtgroup
, taxsubgrp
, taxtempregime
, taxpartsize

--parent material and geomorphology information

, (SELECT TOP 1 copmgrp.pmgroupname FROM copmgrp WHERE c.cokey = copmgrp.cokey AND copmgrp.rvindicator='yes') as pm
, (SELECT TOP 1 cogeomordesc.geomfname FROM cogeomordesc WHERE c.cokey = cogeomordesc.cokey AND cogeomordesc.rvindicator='yes' and cogeomordesc.geomftname = 'Landform')  as landform

--water table data for annual and for growing season

,(select CAST(min(soimoistdept_r/2.54) as integer) from component left outer join comonth left outer join cosoilmoist
            on comonth.comonthkey = cosoilmoist.comonthkey
            on comonth.cokey = component.cokey
        where component.cokey = c.cokey
          and soimoiststat = 'Wet'
          and ((taxtempregime in ('Cryic', 'Pergelic') and comonth.month in ('July', 'August'))
          or (taxtempregime in ('Frigid', 'Mesic', 'Isofrigid') and comonth.month in ('May', 'June',  'July', 'August', 'September'))
          or (taxtempregime in ('Thermic', 'Hyperthermic') and comonth.month in ('April', 'May', 'June',  'July', 'August', 'September', 'October'))
          or (taxtempregime in ('Isothermic', 'Isohyperthermic', 'Isomesic')
          and comonth.month in ('March', 'April', 'May', 'June',  'July', 'August', 'September', 'October', 'November')))) as watertablemings_r

, (select CAST(max(soimoistdept_r/2.54) as int)
          from component left outer join comonth left outer join cosoilmoist
            on comonth.comonthkey = cosoilmoist.comonthkey
            on comonth.cokey = component.cokey
        where component.cokey = c.cokey
          and soimoiststat = 'Wet'
         and ((taxtempregime in ('Cryic', 'Pergelic') and comonth.month in ('July', 'August'))
         or (taxtempregime in ('Frigid', 'Mesic', 'Isofrigid') and comonth.month in ('May', 'June',  'July', 'August', 'September'))
         or (taxtempregime in ('Thermic', 'Hyperthermic') and comonth.month in ('April', 'May', 'June',  'July', 'August', 'September', 'October'))
         or (taxtempregime in ('Isothermic', 'Isohyperthermic', 'Isomesic')
         and comonth.month in ('March', 'April', 'May', 'June',  'July', 'August', 'September', 'October', 'November')))) as watertablemaxgs_r

, (select CAST(min(soimoistdept_r/2.54) as int)
          from component left outer join comonth left outer join cosoilmoist
            on comonth.comonthkey = cosoilmoist.comonthkey
            on comonth.cokey = component.cokey
        where component.cokey = c.cokey
          and soimoiststat = 'Wet') as watertableminan_r

, (select CAST(max(soimoistdept_r/2.54) as int)
          from component left outer join comonth left outer join cosoilmoist
            on comonth.comonthkey = cosoilmoist.comonthkey
            on comonth.cokey = component.cokey
        where component.cokey = c.cokey
          and soimoiststat = 'Wet') as watertablemaxan_r


--the first annual flooding and ponding events populated in the month table sorted by worst case

,(select top 1 flodfreqcl from comonth, MetadataDomainMaster dm, MetadataDomainDetail dd where comonth.cokey = c.cokey and flodfreqcl = ChoiceLabel and DomainName = 'flooding_frequency_class' and
dm.DomainID = dd.DomainID order by choicesequence desc) as annflodfreq
, (select top 1 floddurcl from comonth, MetadataDomainMaster dm, MetadataDomainDetail dd where comonth.cokey = c.cokey and floddurcl = ChoiceLabel and DomainName = 'flooding_duration_class' and
dm.DomainID = dd.DomainID order by choicesequence desc) as annfloddur
,(select top 1 pondfreqcl from comonth, MetadataDomainMaster dm, MetadataDomainDetail dd where comonth.cokey = c.cokey and pondfreqcl = ChoiceLabel and DomainName = 'ponding_frequency_class' and
dm.DomainID = dd.DomainID order by choicesequence desc) as annpondfreq
,(select top 1 ponddurcl from comonth, MetadataDomainMaster dm, MetadataDomainDetail dd where comonth.cokey = c.cokey and ponddurcl = ChoiceLabel and DomainName = 'ponding_duration_class' and
dm.DomainID = dd.DomainID order by choicesequence desc) as annponddur

--grab the first restriction I still need to take the restriction_In query and do the same for all those that put 500 or 0 in the result
--- need to set a default restriction depth - trying to make it ithe max hzdepb_r and got an error

,(SELECT cast(min(resdept_r) as integer) from component left outer join corestrictions on component.cokey = corestrictions.cokey where component.cokey = c.cokey and reskind is not null) as restrictiondepth

,(SELECT CASE when min(resdept_r) is null then '200' else cast(min(resdept_r) as int) END from component left outer join corestrictions on component.cokey = corestrictions.cokey where component.cokey = c.cokey and reskind is not null) as restrictiodepth

,(SELECT TOP 1  reskind  from component left outer join corestrictions on component.cokey = corestrictions.cokey where component.cokey = c.cokey and reskind is not null) as TOPrestriction
, c.cokey

--grab selected interpretations
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'NCCPI - National Commodity Crop Productivity Index (Ver 2.0)') as NCCPI_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'NCCPI - National Commodity Crop Productivity Index (Ver 2.0)') as NCCPI_Value
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 1 AND
rulename like 'NCCPI - NCCPI Corn and Soybeans Submodel (II)') as Nccpi_Corn_Value
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 1 AND
rulename like 'NCCPI - NCCPI Small Grains Submodel (II)') as Nccpi_Wheat_Value
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 1 AND
rulename like 'NCCPI - NCCPI Cotton Submodel (II)') as Nccpi_Cotton_Value
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'ENG - Shallow Excavations') as DShal_Excav_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'ENG - Shallow Excavations') as DShal_Excav_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'DHS - Catastrophic Mortality, Large Animal Disposal, Pit') as DHS_Pit_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'DHS - Catastrophic Mortality, Large Animal Disposal, Pit') as DHS_Pit_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'Ground Penetrating Radar Penetration') as GPR_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'Ground Penetrating Radar Penetration') as GPR_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'ENG - Septic Tank Absorption Fields') as Septic_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'ENG - Septic Tank Absorption Fields') as Septic_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Fire Damage Hazard') as Fire_Haz_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Fire Damage Hazard') as Fire_Haz_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'WMS - Irrigation, Sprinkler (general)') as Sprinkler_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'WMS - Irrigation, Sprinkler (general)') as Sprinkler_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'DHS - Suitability for Clay Liner Material') as Liner_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'DHS - Suitability for Clay Liner Material') as Liner_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Erosion Hazard (Off-Road/Off-Trail)') as Off_Trail_Erosion_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Erosion Hazard (Off-Road/Off-Trail)') as Off_Trail_Erosion_Rating
, (SELECT interphrc FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Erosion Hazard (Road/Trail)') as Trail_Erosion_Class
, (SELECT interphr FROM component left outer join cointerp ON component.cokey = cointerp.cokey WHERE component.cokey = c.cokey AND ruledepth = 0 AND
mrulename like 'FOR - Potential Erosion Hazard (Road/Trail)') as Trail_Erosion_Rating

---begin selection of horizon properties
, hzname
, hzdept_r
, hzdepb_r
, case when (hzdepb_r - hzdept_r) is null then '0' else cast((hzdepb_r - hzdept_r)  as int) END as thickness  --thickness in inches
, (select CASE when sum(cf.fragvol_r) is null then '0' else cast(sum(cf.fragvol_r) as INT) END FROM chfrags cf WHERE cf.chkey = ch.chkey) as fragvol
, texture
, (select top 1 unifiedcl from chorizon left outer join chunified on chorizon.chkey = chunified.chkey where chorizon.chkey = ch.chkey order by chunified.rvindicator desc) as unified
, (select top 1 aashtocl from chorizon left outer join chaashto on chorizon.chkey = chaashto.chkey where chorizon.chkey = ch.chkey order by chaashto.rvindicator desc) as aashto
, kffact
, kwfact
, sandtotal_r
, sandvc_r
, sandco_r
, sandmed_r
, sandfine_r
, sandvf_r
, silttotal_r
, claytotal_r
, pi_r
, ll_r
, om_r
, awc_r
, ksat_r
, dbthirdbar_r
, dbovendry_r
, lep_r
, wtenthbar_r
, wthirdbar_r
, wfifteenbar_r
, ph1to1h2o_r
, ph01mcacl2_r
, caco3_r
, cec7_r
, ecec_r
, ec_r
, sar_r
, gypsum_r
, aws025wta
, aws050wta
, aws0100wta
, aws0150wta
, brockdepmin
, wtdepannmin
, wtdepaprjunmin
, ch.chkey
INTO #cdsi
FROM legend l
INNER JOIN mapunit AS mu ON mu.lkey = l.lkey and mu.mukey in (""" \
+ mukeys \
+ """)
INNER JOIN muaggatt mt on mu.mukey=mt.mukey
INNER JOIN component c ON c.mukey = mu.mukey and majcompflag = 'Yes' AND c.cokey = (SELECT TOP 1 c.cokey FROM component c WHERE c.mukey=mu.mukey and compkind not like 'miscellaneous area' ORDER BY c.comppct_r DESC )
INNER JOIN chorizon ch ON ch.cokey = c.cokey
INNER JOIN chtexturegrp ct ON ch.chkey=ct.chkey and ct.rvindicator = 'yes'
ORDER by l.areasymbol, mu.musym, hzdept_r

---grab top depth for the mineral soil and will use it later to get mineral surface properties

SELECT compname, cokey, MIN(hzdept_r) AS min_t
INTO #hortopdepth
FROM #cdsi
WHERE texture NOT LIKE '%PM%' and texture NOT LIKE 'UDOM' and texture NOT LIKE '%MPT%' and texture NOT LIKE '%MUCK' and texture NOT LIKE '%PEAT%'
GROUP BY compname, cokey

---combine the mineral surface to grab surface mineral properties

Select #hortopdepth.cokey
, hzname
, hzdept_r
, hzdepb_r
, thickness
, fragvol as fragvol_surf
, texture as texture_surf
, unified  as unified_surf
, aashto as aashto_surf
, kffact as Kffact_surf
, kwfact as kwfact_surf
, sandtotal_r as sandtotal_surf
, sandvc_r as sandvc_surf
, sandco_r as sandco_surf
, sandmed_r as sandmed_surf
, sandfine_r as sandfine_surf
, sandvf_r as sandvf_surf
, silttotal_r as silttotal_surf
, claytotal_r as claytotal_surf
, pi_r as pi_surf
, ll_r as ll_surf
, om_r as om_surf
, awc_r as awc_surf
, ksat_r as ksat_surf
, dbthirdbar_r as dbthirdbar_surf
, dbovendry_r as dbovendry_surf
, lep_r as lep_surf
, wtenthbar_r as wtenthbar_surf
, wthirdbar_r as wthirdbar_surf
, wfifteenbar_r as wfifteenbar_surf
, ph1to1h2o_r as ph1to1h2o_surf
, ph01mcacl2_r as ph01mcacl2_surf
, caco3_r as caco3_surf
, cec7_r as cec7_surf
, ecec_r as ecec_surf
, ec_r as ec_surf
, sar_r as sar_surf
, gypsum_r as gypsum_surf
, chkey
INTO #cdsi2
FROM #hortopdepth
INNER JOIN #cdsi on #hortopdepth.cokey=#cdsi.cokey AND #hortopdepth.min_t = #cdsi.hzdept_r
ORDER BY #hortopdepth.cokey, hzname


---good to here, now to build master the quote HEL unquote query, found top mineral horizon and grabbed the first horion data


SELECT ((0.065 + (0.0456 * slope_r) + (0.006541*Power(slope_r, 2)))*Power((slopelenusle_r / 22.1) , mexp_h)) AS LS_r, k.cokey, k.mukey
INTO #LS
FROM #cdsi k

SELECT LS_R, (LS_R * Rfact * Kwfact_surf)/tfact as EI, #LS.cokey, #LS.mukey
INTO #EIByComp
From #LS
INNER JOIN #cdsi ON #LS.cokey = #cdsi.cokey
INNER JOIN #cdsi2 on #LS.cokey = #cdsi2.cokey

Select Max(EI) as MostLimitingEI, m.mukey, m.muname, l.areasymbol, LS_R
INTO #EIFinal
From Legend l
inner join mapunit m on m.lkey = l.lkey
inner join #eibycomp ei on ei.mukey = m.mukey
Group by m.mukey, m.mukey, m.muname, l.areasymbol, LS_R

-- HEL data is finished, now time to gather the select max values from the profile ---



--the next step is to build weighted averages of the properties and to do that I have to make null values zero sql

--horizon data

SELECT
mukey
, cokey
, hzname
, case when restrictiodepth = 0 then 10 else restrictiodepth END as restrictiodepth
, hzdept_r
, hzdepb_r
, case when (hzdepb_r-hzdept_r) is null then 0 else cast((hzdepb_r-hzdept_r)  as int) END as thickness
, (select CASE when sum(fragvol) is null then 0 else cast(sum(fragvol) as varchar) END FROM #cdsi)  as fragvol
, texture
, unified
, kffact
, kwfact
, CASE when sandtotal_r is null then 0 else sandtotal_r end as sandtotal_r
, CASE when sandvc_r is null then 0 else sandvc_r end as sandvc_r
, CASE when sandco_r is null then 0 else sandco_r end as sandco_r
, CASE when sandmed_r is null then 0 else sandmed_r end as sandmed_r
, CASE when sandfine_r is null then 0 else sandfine_r end as sandfine_r
, CASE when sandvf_r is null then 0 else sandvf_r end as sandvf_r
, CASE when silttotal_r is null then 0 else silttotal_r end as silttotal_r
, CASE when claytotal_r is null then 0 else claytotal_r end as claytotal_r
, CASE when pi_r is null then 0 else pi_r end as pi_r
, CASE when ll_r is null then 0 else ll_r end as ll_r
, CASE when om_r is null then 0 else om_r end as om_r
, CASE when awc_r is null then 0 else awc_r end as awc_r
, CASE when ksat_r is null then 0 else ksat_r end as ksat_r
, CASE when dbthirdbar_r is null then 0 else dbthirdbar_r end as dbthirdbar_r
, CASE when dbovendry_r is null then 0 else dbovendry_r end as dbovendry_r
, CASE when lep_r is null then 0 else lep_r end as lep_r
, CASE when wtenthbar_r is null then 0 else wtenthbar_r end as wtenthbar_r
, CASE when wthirdbar_r is null then 0 else wthirdbar_r end as wthirdbar_r
, CASE when wfifteenbar_r is null then 0 else wfifteenbar_r end as wfifteenbar_r
, CASE when ph1to1h2o_r is null then 0 else ph1to1h2o_r end as ph1to1h2o_r
, CASE when ph01mcacl2_r is null then 0 else ph01mcacl2_r end as ph01mcacl2_r
, CASE when caco3_r is null then 0 else caco3_r end as caco3_r
, CASE when cec7_r is null then 0 else cec7_r end as cec7_r
, CASE when ecec_r is null then 0 else ecec_r end as ecec_r
, CASE when ec_r is null then 0 else ec_r end as ec_r
, CASE when sar_r is null then 0 else sar_r end as sar_r
, CASE when gypsum_r is null then 0 else gypsum_r end as gypsum_r
, chkey
INTO #cdsihzn
FROM #cdsi

--- depth ranges for AWS ----

Select
CASE	WHEN hzdepb_r <= 100 THEN hzdepb_r
	WHEN hzdepb_r > 100 and hzdept_r < 100 THEN 100
	ELSE 0
	END AS InRangeBot,
CASE 	WHEN hzdept_r < 100 then hzdept_r
	ELSE 0
	END as InRangeTop, awc_r, cokey, mukey
INTO #aws
FROM #cdsi
order by cokey

select mukey, cokey, SUM((InRangeBot - InRangeTop)*awc_r) as AWS100
INTO #aws100
FROM #aws
group by mukey, cokey

---return to weighted averages, using the thickness times the non-null horizon properties

SELECT mukey, cokey, chkey
, thickness
, restrictiodepth
, ( fragvol*thickness) as th_fragvol
, (sandtotal_r*thickness) as th_sand_r
, (sandvc_r*thickness) as th_vcos_r
, (sandco_r*thickness) as th_cos_r
, (sandmed_r*thickness) as th_meds_r
, (sandfine_r*thickness) as th_fines_r
, (sandvf_r*thickness) as th_vfines_r
, (silttotal_r*thickness) as th_silt_r
, (claytotal_r*thickness) as th_clay_r
, (om_r*thickness) as th_om_r
, (awc_r*thickness) as th_awc_r
, (ksat_r*thickness) as th_ksat_r
, (dbthirdbar_r*thickness) as th_dbthirdbar_r
, (dbovendry_r*thickness) as th_dbovendry_r
, (lep_r*thickness) as th_lep_r
, (pi_r*thickness) as th_pi_r
, (ll_r*thickness) as th_ll_r
, (wtenthbar_r*thickness) as th_wtenthbar_r
, (wthirdbar_r*thickness) as th_wthirdbar_r
, (wfifteenbar_r*thickness) as th_wfifteenbar_r
, (ph1to1h2o_r*thickness) as th_ph1to1h2o_r
, (ph01mcacl2_r*thickness) as th_ph01mcacl2_r
, (caco3_r*thickness) as th_caco3_r
, (cec7_r*thickness) as th_cec7_r
, (ecec_r*thickness) as th_ecec_r
, (ec_r*thickness) as th_ec_r
, (sar_r*thickness) as th_sar_r
, (gypsum_r*thickness) as th_gypsum_r
INTO #cdsi3
FROM #cdsihzn
ORDER BY mukey, cokey, chkey

---sum all horizon properties to gather the final product for the component

select mukey, cokey, restrictiodepth
, cast(sum(thickness) as float(2)) as sum_thickness
, cast(sum(th_fragvol) as float(2)) as sum_fragvol_r
, cast(sum(th_sand_r) as float(2)) as sum_sand_r
, cast(sum(th_vcos_r) as float(2)) as sum_vcos_r
, cast(sum(th_cos_r) as float(2)) as sum_cos_r
, cast(sum(th_meds_r) as float(2)) as sum_meds_r
, cast(sum(th_fines_r) as float(2)) as sum_fines_r
, cast(sum(th_vfines_r) as float(2)) as sum_vfines_r
, cast(sum(th_silt_r) as float(2)) as sum_silt_r
, cast(sum(th_clay_r) as float(2)) as sum_clay_r
, cast(sum(th_om_r) as float(2)) as sum_om_r
, cast(sum(th_awc_r) as float(2)) as sum_awc_r
, cast(sum(th_ksat_r) as float(2)) as sum_ksat_r
, cast(sum(th_dbthirdbar_r) as float(2)) as sum_dbthirdbar_r
, cast(sum(th_dbovendry_r) as float(2)) as sum_dbovendry_r
, cast(sum(th_lep_r) as float(2)) as sum_lep_r
, cast(sum(th_pi_r) as float(2)) as sum_pi_r
, cast(sum(th_ll_r) as float(2)) as sum_ll_r
, cast(sum(th_wtenthbar_r) as float(2)) as sum_wtenthbar_r
, cast(sum(th_wthirdbar_r) as float(2)) as sum_wthirdbar_r
, cast(sum(th_wfifteenbar_r) as float(2)) as sum_wfifteenbar_r
, cast(sum(th_ph1to1h2o_r) as float(2)) as sum_ph1to1h2o_r
, cast(sum(th_ph01mcacl2_r) as float(2)) as sum_ph01mcacl2_r
, cast(sum(th_caco3_r) as float(2)) as sum_caco3_r
, cast(sum(th_cec7_r) as float(2)) as sum_cec7_r
, cast(sum(th_ecec_r) as float(2)) as sum_ecec_r
, cast(sum(th_ec_r) as float(2)) as sum_ec_r
, cast(sum(th_sar_r) as float(2)) as sum_sar_r
, cast(sum(th_gypsum_r) as float(2)) as sum_gypsum_r
INTO #cdsi4
FROM #cdsi3
GROUP BY mukey, cokey, restrictiodepth
ORDER BY mukey

---sql to create weighted average by dividing by the restriction depth found in the first query

select #cdsi4.mukey, #cdsi4.cokey
, (sum_fragvol_r/restrictiodepth) as wtavg_fragvol_r
, (sum_sand_r/sum_thickness) as wtavg_sand_r
, (sum_vcos_r/restrictiodepth) as wtavg_vcos_r
, (sum_cos_r/restrictiodepth) as wtavg_cos_r
, (sum_meds_r/restrictiodepth) as wtavg_meds_r
, (sum_fines_r/restrictiodepth) as wtavg_fines_r
, (sum_vfines_r/restrictiodepth) as wtavg_vfines_r
, (sum_silt_r/sum_thickness) as wtavg_silt_r
, (sum_clay_r/sum_thickness) as wtavg_clay_r
, (sum_om_r/sum_thickness) as wtavg_om_r
, (sum_awc_r) as profile_Waterstorage
, (sum_awc_r/restrictiodepth) as wtavg_awc_r_to_restrict
, (sum_ksat_r/sum_thickness) as wtavg_ksat_r
, (sum_dbthirdbar_r/restrictiodepth) as wtavg_dbthirdbar_r
, (sum_dbovendry_r/restrictiodepth) as wtavg_dbovendry_r
, (sum_lep_r/sum_thickness) as wtavg_lep_r
, (sum_pi_r/restrictiodepth) as wtavg_pi_r
, (sum_ll_r/restrictiodepth) as wtavg_ll_r
, (sum_wtenthbar_r/restrictiodepth) as wtavg_wtenthbar_r
, (sum_wthirdbar_r/restrictiodepth) as wtavg_wthirdbar_r
, (sum_wfifteenbar_r/restrictiodepth) as wtavg_wfifteenbar_r
, (sum_ph1to1h2o_r/sum_thickness) as wtavg_phH2O_r
, (sum_ph01mcacl2_r/sum_thickness) as wtavg_phCACL_r
, (sum_caco3_r/restrictiodepth) as wtavg_caco3_r
, (sum_cec7_r/restrictiodepth) as wtavg_cec7_r
, (sum_ecec_r/restrictiodepth) as wtavg_ecec_r
, (sum_ec_r/restrictiodepth) as wtavg_ec_r
, (sum_sar_r/restrictiodepth) as wtavg_sar_r
, (sum_gypsum_r/restrictiodepth) as wtavg_gypsum_r
INTO #CDSIwtavg
FROM #cdsi4
ORDER by #cdsi4.mukey, #cdsi4.cokey

--time to put it all together using a lot of casts to change the data to reflect the way I want it to appear

Select DISTINCT
#cdsi.mukey
, #cdsi.state
, #cdsi.areasymbol
, #cdsi.areaname
, #cdsi.musym
, #cdsi.muname
, nationalmusym
, mukind
, majcompflag
, comppct_r
, compname
, compkind
, localphase
, #cdsi.rfact
, #cdsi.cfact
, slope_l
, slope_r
, slope_h
, farmlndcl
, nirrcapclass
, irrcapclass
, CAST(MostLimitingEI as Decimal(5,1)) as erodibilityindex
, CAST((((Cfact*wei)/tfact)/100) as Decimal(5, 1)) as winderodindex
, nccpi_class
, nccpi_value
, nccpi_corn_value
, nccpi_wheat_value
, nccpi_cotton_value
, dshal_excav_class
, dshal_excav_rating
, dhs_pit_class
, dhs_pit_rating
, gpr_class
, gpr_rating
, septic_class
, septic_rating
, fire_haz_class
, fire_haz_rating
, liner_class
, liner_rating
, sprinkler_class
, sprinkler_rating
, trail_erosion_class
, trail_erosion_rating
, off_trail_erosion_class
, off_trail_erosion_rating
, corsteel
, corcon
, drainagecl
, runoff
, hydgrp
, hydgrpdcd
, CAST(AWS100 AS Decimal(5,1)) as aws100
, CAST(profile_Waterstorage AS Decimal(5,1)) as aws_profile
, CAST(wtavg_awc_r_to_restrict AS Decimal(5,1)) as aws_restrict
, hydricrating
, hydric_criteria
, hydclprs
, ecositeid
, ecositename
, rsprod_r
, constreeshrubgrp
, foragesuitgrpid
, foragesuitgroupid
, taxclname
, taxorder
, taxsuborder
, taxgrtgroup
, taxsubgrp
, taxtempregime
, taxpartsize
, pm
, landform
, cast(restrictiondepth/2.54 as int) restrictiondepth_in
, toprestriction
, watertablemaxan_r
, watertableminan_r
, watertablemaxgs_r
, watertablemings_r
, annflodfreq
, annfloddur
, annpondfreq
, annponddur
, frostact
, #cdsi2.hzname
, cast(#cdsi2.hzdept_r/2.54 as int) as hzdept_r
, cast(#cdsi2.hzdepb_r/2.54 as int) as hzdeb_r
, texture_surf
, unified_surf
, kffact_surf
, kwfact_surf
, tfact
, fragvol_surf
, CAST(sandtotal_surf AS INT) as sandtotal_surf
, CAST(wtavg_sand_r AS INT) as sand_wtavg_r
, CAST(silttotal_surf  AS INT) as silttotal_surf
, CAST(wtavg_silt_r AS INT) as silt_wtavg_r
, CAST(claytotal_surf  AS INT) as claytotal_surf
, CAST(wtavg_clay_r AS INT) as clay_wtavg_r
, CAST(wtavg_lep_r AS INT) as lep_wtavg_r
, om_surf
, CAST(wtavg_om_r as Decimal(5,1)) as om_wtavg_r
, CAST(ksat_surf * 0.1417 as Decimal(7,2)) as ksat_surf_in_hr
, CAST(wtavg_ksat_r * 0.1417 as Decimal(7,2)) as ksat_wtavg_r_in_hr
, ph1to1h2o_surf
, CAST(wtavg_phH2O_r as decimal(7,1)) as pH_wtavg_r
, caco3_surf
, CAST(wtavg_caco3_r as decimal(7,1)) as caco3_wtavg_r
, cec7_surf
, CAST(wtavg_cec7_r as decimal(5,1)) as cec7_wtavg_r
, ec_surf
, CAST(wtavg_ec_r as decimal(5,1)) as ec_wtavg_r
, sar_surf
, CAST(wtavg_sar_r as decimal(5,1)) as sar_wtavg_r
, gypsum_surf
, CAST(wtavg_gypsum_r as decimal(5,1)) as gypsum_wtavg_r
FROM #cdsi2
INNER JOIN #cdsi on #cdsi.cokey = #cdsi2.cokey
LEFT OUTER JOIN #EIFinal on #cdsi.mukey = #EIFinal.mukey
LEFT OUTER JOIN #aws100 on #cdsi.cokey = #aws100.cokey
LEFT OUTER JOIN #CDSIwtavg on #cdsi.cokey = #CDSIwtavg.cokey
ORDER BY #cdsi.state, #cdsi.areasymbol, #cdsi.areaname, #cdsi.mukey, #cdsi.musym

--end of SQL"""


        return sQuery

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def AttributeRequest(theURL, mukeyList, outputShp, ratingField):
    # POST REST which uses urllib and JSON
    #
    # Send query to SDM Tabular Service, returning data in JSON format

    try:
        outputValues = []  # initialize return values (min-max list)

        PrintMsg(" \nRequesting tabular data for " + Number_Format(len(mukeyList), 0, True) + " map units...")
        #arcpy.SetProgressorLabel("Sending tabular request to Soil Data Access...")

        mukeys = ",".join(mukeyList)

        sQuery = FormAttributeQuery(mukeys)

        # Tabular service to append to SDA URL
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        #PrintMsg(" \nURL: " + url, 1)
        #PrintMsg(" \n" + sQuery, 0)

        dRequest = dict()
        dRequest["FORMAT"] = "JSON+COLUMNNAME+METADATA"
        dRequest["QUERY"] = sQuery

        # Create SDM connection to service using HTTP
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        #PrintMsg(" \njsonString: " + str(jsonString), 1)
        data = json.loads(jsonString)
        del jsonString, resp, req

        dataList = data["Table"]     # Data as a list of lists. Service returns everything as string.

        # Get column metadata from first two records
        columnNames = dataList.pop(0)
        columnInfo = dataList.pop(0)

        if len(mukeyList) != len(dataList):
            PrintMsg(" \nWarning! Only returned data for " + str(len(dataList)) + " mapunits", 1)

        PrintMsg(" \nImporting attribute data...", 0)
        bNewFields = AddNewFields(outputShp, columnNames, columnInfo)
        if bNewFields == False:
            raise MyError, ""

        # Create list of outputShp fields to populate (everything but OID)
        desc = arcpy.Describe(outputShp)

        fields = desc.fields
        fieldList = list()

        for fld in fields:
            fldName = fld.name.upper()

            if not fld.type == "OID" and not fldName.startswith("SHAPE"):
                fieldList.append(fld.name)

        # The rating field must be included in the query output or the script will fail. This
        # is a weak spot, but it is mostly for demonstration of symbology and map legends.
        if ratingField in fieldList:
            outputIndx = fieldList.index(ratingField)  # Use to identify attribute that will be mapped

        else:
            raise MyError, "Failed to find output field '" + ratingField + "' in " + ", ".join(fieldList)


        # Need to develop list of integer and floating point values from attribute table
        arcpy.SetProgressorLabel("Importing attribute data...")

        dMapunitInfo = dict()
        n = len(fieldList) - 1
        #PrintMsg(" \n" + str(fieldList), 1)
        noMatch = list()
        cnt = 0

        for rec in dataList:
            try:
                dMapunitInfo[rec[0]] = rec

            except:
                errorMsg()
                PrintMsg(" \n" + ", ".join(columnNames), 1)
                PrintMsg(" \n" + str(rec) + " \n ", 1)
                raise MyError, "Failed to save " + str(fieldList[i]) + " (" + str(i) + ") : " + str(rec[i])

        #PrintMsg(" \nUsing fields: " + ", ".join(fieldList), 1)
        maxminValues = list()
        #maxAn = fieldList.index('maxanwatertable_r')

        with arcpy.da.UpdateCursor(outputShp, fieldList) as cur:
            for rec in cur:
                try:
                    mukey = rec[0]
                    newrec = dMapunitInfo[mukey]
                    #PrintMsg("\t" + str(maxAn) + ". maxanwatertable_r: '" + str(newrec[maxAn]) + " of type " + str(type(newrec[maxAn])), 1)
                    cur.updateRow(newrec)
                    maxminValues.append(newrec[outputIndx])

                except:
                    if not mukey in noMatch:
                        noMatch.append(mukey)

        if len(noMatch) > 0:
            PrintMsg(" \nNo attribute data for mukeys: " + ", ".join(noMatch), 1)

        if len(maxminValues) > 1:
            distinctValues = set(maxminValues)
            outputValues = list()

            try:
                distinctValues.remove(None)

            except:
                pass

            outputValues.append(float(min(maxminValues)))
            outputValues.append(float(max(maxminValues)))
            PrintMsg(" \n" + ratingField + " range values: " + str(outputValues), 1)

        else:
            raise MyError, ratingField + " values: " + str(outputValues)

        arcpy.SetProgressorLabel("Finished importing attribute data")

        return outputValues

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return outputValues

    except:
        errorMsg()
        return outputValues

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
def AddAttributeFields(outputShp):
    try:
        outputTbl = os.path.join("IN_MEMORY", "CDSI_Data")

        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))


        arcpy.AddField_management(outputTbl,"mukey", "TEXT", "", "", "30")   # for outputShp
        arcpy.AddField_management(outputTbl,"state", "Text", 0, 0, 2, "State", "True", "False")
        arcpy.AddField_management(outputTbl,"areasymbol", "Text", 0, 0, 10, "Areasymbol", "True", "False")
        arcpy.AddField_management(outputTbl,"areaname", "Text", 0, 0, 255, "Areaname", "True", "False")

        arcpy.AddField_management(outputTbl,"musym", "Text", 0, 0, 7, "Musym", "True", "False")
        arcpy.AddField_management(outputTbl,"muname", "Text", 0, 0, 70, "Muname", "True", "False")
        arcpy.AddField_management(outputTbl,"nationalmusym", "Text", 0, 0, 255, "Nationalmusym", "True", "False")
        arcpy.AddField_management(outputTbl,"mukind", "Text", 0, 0, 50, "Mukind", "True", "False")
        #arcpy.AddField_management(outputTbl,"muacres", "Double", 0, 0, 8, "Muacres", "True", "False")
        #arcpy.AddField_management(outputTbl,"cokey", "Double", 0, 0, 8, "cokey", "True", "False")
        arcpy.AddField_management(outputTbl,"majcompflag", "Text", 0, 0, 255, "MajCompFlag", "True", "False")
        arcpy.AddField_management(outputTbl,"comppct_r", "Short", 0, 0, 0, "Comppct_r", "True", "False")
        arcpy.AddField_management(outputTbl,"compname", "Text", 0, 0, 255, "Compname", "True", "False")
        arcpy.AddField_management(outputTbl,"compkind", "Text", 0, 0, 255, "Compkind", "True", "False")
        #arcpy.AddField_management(outputTbl,"compacres", "Double", 0, 0, 8, "Compacres", "True", "False")
        arcpy.AddField_management(outputTbl,"localphase", "Text", 0, 0, 255, "LocalPhase", "True", "False")
        arcpy.AddField_management(outputTbl,"rfact", "Short", 0, 0, 0, "RFact", "True", "False")
        arcpy.AddField_management(outputTbl,"cfact", "Text", 0, 0, 255, "CFact", "True", "False")
        arcpy.AddField_management(outputTbl,"slope_l", "Double", 0, 0, 8, "Slope_l", "True", "False")
        arcpy.AddField_management(outputTbl,"slope_r", "Double", 0, 0, 8, "Slope_r", "True", "False")
        arcpy.AddField_management(outputTbl,"slope_h", "Double", 0, 0, 8, "Slope_h", "True", "False")
        arcpy.AddField_management(outputTbl,"farmlndcl", "Text", 0, 0, 255, "FarmLndCl", "True", "False")
        arcpy.AddField_management(outputTbl,"nirrcapclass", "Text", 0, 0, 255, "NirrCapClass", "True", "False")
        arcpy.AddField_management(outputTbl,"irrcapclass", "Text", 0, 0, 255, "IrrCapClass", "True", "False")
        arcpy.AddField_management(outputTbl,"erodibilityindex", "Float", 0, 0, 0, "ErodibilityIndex", "True", "False")
        arcpy.AddField_management(outputTbl,"winderodindex", "Text", 0, 0, 2, "WindErodIndex", "True", "False")
        arcpy.AddField_management(outputTbl,"nccpi_class", "Text", 0, 0, 60, "NCCPI_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"nccpi_value", "Float", 0, 0, 0, "NCCPI_Value", "True", "False")
        arcpy.AddField_management(outputTbl,"nccpi_corn_value", "Float", 0, 0, 0, "NCCPI_Corn_Value", "True", "False")
        arcpy.AddField_management(outputTbl,"nccpi_wheat_value", "Float", 0, 0, 0, "NCCPI_Wheat_Value", "True", "False")
        arcpy.AddField_management(outputTbl,"nccpi_cotton_value", "Float", 0, 0, 0, "NCCPI_Cotton_Value", "True", "False")
        arcpy.AddField_management(outputTbl,"dshal_excav_class", "Text", 0, 0, 60, "DShal_Excav_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"dshal_excav_rating", "Float", 0, 0, 0, "DShal_Excav_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"dhs_pit_class", "Text", 0, 0, 60, "DHS_Pit_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"dhs_pit_rating", "Float", 0, 0, 0, "DHS_Pit_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"gpr_class", "Text", 0, 0, 60, "GPR_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"gpr_rating", "Float", 0, 0, 0, "GPR_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"septic_class", "Text", 0, 0, 60, "Septic_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"septic_rating", "Float", 0, 0, 0, "Septic_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"fire_haz_class", "Text", 0, 0, 60, "Fire_Haz_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"fire_haz_rating", "Float", 0, 0, 0, "Fire_Haz_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"liner_class", "Text", 0, 0, 60, "Liner_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"liner_rating", "Float", 0, 0, 0, "Liner_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"sprinkler_class", "Text", 0, 0, 60, "Sprinkler_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"sprinkler_rating", "Float", 0, 0, 0, "Sprinkler_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"trail_erosion_class", "Text", 0, 0, 60, "Trail_Erosion_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"trail_erosion_rating", "Float", 0, 0, 0, "Trail_Erosion_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"off_trail_erosion_class", "Text", 0, 0, 60, "Off_Trail_Erosion_Class", "True", "False")
        arcpy.AddField_management(outputTbl,"off_trail_erosion_rating", "Float", 0, 0, 0, "Off_Trail_Erosion_Rating", "True", "False")
        arcpy.AddField_management(outputTbl,"corsteel", "Text", 0, 0, 60, "Corsteel", "True", "False")
        arcpy.AddField_management(outputTbl,"corcon", "Text", 0, 0, 60, "Corcon", "True", "False")
        arcpy.AddField_management(outputTbl,"drainagecl", "Text", 0, 0, 60, "DrainageClass", "True", "False")
        arcpy.AddField_management(outputTbl,"runoff", "Text", 0, 0, 60, "Runoff", "True", "False")
        arcpy.AddField_management(outputTbl,"hydgrp", "Text", 0, 0, 30, "Hydgrp", "True", "False")
        arcpy.AddField_management(outputTbl,"hydgrpdcd", "Text", 0, 0, 30, "HydGrpDcd", "True", "False")
        arcpy.AddField_management(outputTbl,"aws100", "Float", 0, 0, 0, "AWS100", "True", "False")
        arcpy.AddField_management(outputTbl,"aws_profile", "Float", 0, 0, 0, "AWS_profile", "True", "False")
        arcpy.AddField_management(outputTbl,"aws_restrict", "Float", 0, 0, 0, "AWS_restrict", "True", "False")
        arcpy.AddField_management(outputTbl,"hydricrating", "Text", 0, 0, 30, "HydricRating", "True", "False")
        arcpy.AddField_management(outputTbl,"hydric_criteria", "Text", 0, 0, 60, "HydricCriteria", "True", "False")
        arcpy.AddField_management(outputTbl,"hydclprs", "Float", 0, 0, 0, "Hydclprs", "True", "False")
        arcpy.AddField_management(outputTbl,"ecositeid", "Text", 0, 0, 40, "EcositeID", "True", "False")
        arcpy.AddField_management(outputTbl,"ecositename", "Text", 0, 0, 255, "EcositeName", "True", "False")
        arcpy.AddField_management(outputTbl,"rsprod_r", "Short", 0, 0, 0, "RsProd_r", "True", "False")
        arcpy.AddField_management(outputTbl,"constreeshrubgrp", "Text", 0, 0, 80, "ConsTreeSshrubgrp", "True", "False")
        arcpy.AddField_management(outputTbl,"foragesuitgrpid", "Text", 0, 0, 60, "ForageSuitGrpid", "True", "False")
        arcpy.AddField_management(outputTbl,"foragesuitgroupid", "Text", 0, 0, 60, "ForageSuitGroupid", "True", "False")
        arcpy.AddField_management(outputTbl,"taxclname", "Text", 0, 0, 255, "TaxClName", "True", "False")
        arcpy.AddField_management(outputTbl,"taxorder", "Text", 0, 0, 255, "TaxOrder", "True", "False")
        arcpy.AddField_management(outputTbl,"taxsuborder", "Text", 0, 0, 255, "TaxSuborder", "True", "False")
        arcpy.AddField_management(outputTbl,"taxgrtgroup", "Text", 0, 0, 255, "TaxGrtGroup", "True", "False")
        arcpy.AddField_management(outputTbl,"taxsubgrp", "Text", 0, 0, 255, "TaxSubGrp", "True", "False")
        arcpy.AddField_management(outputTbl,"taxtempregime", "Text", 0, 0, 255, "TaxTempRegime", "True", "False")
        arcpy.AddField_management(outputTbl,"taxpartsize", "Text", 0, 0, 255, "TaxPartSize", "True", "False")
        arcpy.AddField_management(outputTbl,"pm", "Text", 0, 0, 255, "ParentMaterial", "True", "False")
        arcpy.AddField_management(outputTbl,"landform", "Text", 0, 0, 255, "LandForm", "True", "False")
        arcpy.AddField_management(outputTbl,"restrictiondepth_IN", "short", 0, 0, 0, "RestrictionDepth_IN", "True", "False")
        arcpy.AddField_management(outputTbl,"toprestriction", "String", 0, 0, 100, "TopRestriction", "True", "False")
        arcpy.AddField_management(outputTbl,"maxanwatertable_r", "Short", 0, 0, 0, "AnnualWatertableMax", "True", "False")
        arcpy.AddField_management(outputTbl,"minanwatertable_r", "Short", 0, 0, 0, "AnnualWatertableMin", "True", "False")
        arcpy.AddField_management(outputTbl,"maxgswatertable_r", "Short", 0, 0, 0, "WaterTableGSMax", "True", "False")
        arcpy.AddField_management(outputTbl,"mingswatertable_r", "Short", 0, 0, 0, "WaterTableGSMin", "True", "False")
        arcpy.AddField_management(outputTbl,"annflodfreq", "Text", 0, 0, 60, "FloodFreqAnnual", "True", "False")
        arcpy.AddField_management(outputTbl,"annfloddur", "Text", 0, 0, 60, "FloodDurAnnual", "True", "False")
        arcpy.AddField_management(outputTbl,"annpondfreq", "Text", 0, 0, 60, "PondingFreqAnnual", "True", "False")
        arcpy.AddField_management(outputTbl,"annponddur", "Text", 0, 0, 60, "PondingDurAnnual", "True", "False")
        arcpy.AddField_management(outputTbl,"frostact", "Text", 0, 0, 30, "FrostAct", "True", "False")
        #arcpy.AddField_management(outputTbl,"chkey", "Text", 0, 0, 30, "chkey", "True", "False")
        arcpy.AddField_management(outputTbl,"hzname", "Text", 0, 0, 30, "HzName", "True", "False")
        arcpy.AddField_management(outputTbl,"hzdept_r", "Short", 0, 0, 8, "HzDepTop", "True", "False")
        arcpy.AddField_management(outputTbl,"hzdeb_r", "Short", 0, 0, 8, "HzDepBot", "True", "False")
        arcpy.AddField_management(outputTbl,"texture_surf", "Text", 0, 0, 255, "TextureSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"unified_surf", "Text", 0, 0, 255, "UnifiedSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"kffact_surf", "Float", 0, 0, 0, "KfFactSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"kwfact_surf", "Float", 0, 0, 0, "kwFactSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"tfact", "Short", 0, 0, 8, "TFact", "True", "False")
        arcpy.AddField_management(outputTbl,"fragvol_surf", "Short", 0, 0, 0, "FragVolSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"sandtotal_surf", "Short", 0, 0, 0, "SandTotalSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"sand_wtavg_r", "Float", 0, 0, 0, "SandWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"silttotal_surf", "Short", 0, 0, 0, "SiltTotalSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"silt_wtavg_r", "Float", 0, 0, 0, "SiltWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"claytotal_surf", "Short", 0, 0, 0, "ClayTotalSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"clay_wtavg_r", "Float", 0, 0, 0, "ClayWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"lep_wtavg_r", "Float", 0, 0, 0, "LEPWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"om_surf", "Short", 0, 0, 0, "OMSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"om_wtavg_r", "Float", 0, 0, 0, "OMWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"ksat_surf_in_hr", "Float", 0, 0, 0, "KSatSurf_inchhr", "True", "False")
        arcpy.AddField_management(outputTbl,"ksat_wtavg_r_in_hr", "Float", 0, 0, 0, "KSatWtdAvg_in_hr", "True", "False")
        arcpy.AddField_management(outputTbl,"ph1to1h2o_surf", "Float", 0, 0, 0, "pH1to1h2oSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"pH_wtavg_r", "Float", 0, 0, 0, "pHWtAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"caco3_surf", "Double", 0, 0, 0, "CaCO3Surf", "True", "False")
        arcpy.AddField_management(outputTbl,"caco3_wtavg_r", "Double", 0, 0, 0, "CaCO3WtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"cec7_surf", "Float", 0, 0, 0, "CEC7Surf", "True", "False")
        arcpy.AddField_management(outputTbl,"cec7_wtavg_r", "Float", 0, 0, 0, "CEC7WtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"ec_surf", "Float", 0, 0, 8, "ECSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"ec_wtavg_r", "Float", 0, 0, 0, "ECWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"sar_surf", "Float", 0, 0, 8, "SarSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"sar_wtavg_r", "Float", 0, 0, 0, "SarWtdAvg", "True", "False")
        arcpy.AddField_management(outputTbl,"gypsum_surf", "Float", 0, 0, 0, "GypsumSurf", "True", "False")
        arcpy.AddField_management(outputTbl,"gypsum_wtavg_r", "Float", 0, 0, 0, "GypsumWtdAvg", "True", "False")

        # Use JoinField to add fields from IN_MEMORY table
        #
        # Create a list without MUKEY so that we don't end up with duplicates in the output featureclass

        tmpFields = arcpy.Describe(outputTbl).fields
        fieldList = list()

        for fld in tmpFields:
            if not fld.name.upper() == "MUKEY":
                fieldList.append(fld.name)

        arcpy.JoinField_management(outputShp, "MUKEY", outputTbl, "MUKEY", fieldList)

        tmpFields = arcpy.Describe(outputShp).fields
        fieldList = list()

        for fld in tmpFields:
            fieldList.append(fld.name)

        #PrintMsg(" \nOutput fields: " + ", ".join(fieldList), 1)

        return outputShp

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

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
    # JSON
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
def RunSpatialQueryXML(theURL, spatialQuery, outputShp, clipPolygon, showStatus):
    # Old SOAP request will not work
    # XML
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
        PrintMsg(" \nProcessing spatial request using " + url + " with XML output", 1)

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

        PrintMsg(" \nReturned an estimated " + Number_Format(polys, 0, True) + " polygons...", 1)


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

                    if showStatus:
                        arcpy.SetProgressorPosition()

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
            dLayerDefinition = ClassBreaksJSON(ratingValues, drawOutlines, ratingField)

            newLayer.updateLayerFromJSON(dLayerDefinition)
            newLayer.name = "CDSI " + ratingField.title()
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
        d["field"] = ratingField
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
    ratingField = arcpy.GetParameterAsText(2)    # Attribute Field to be mapped
    transparency = arcpy.GetParameter(3)     # transparency level for the output soils layer
    maxAcres = arcpy.GetParameter(4)         # maximum allowed area for the output EXTENT.
    sdaURL = arcpy.GetParameterAsText(5)   # Soil Data Access URL


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
                #
                #
                spatialQuery, clipPolygon = FormSpatialQuery(newAOI)
                #
                #
                #

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
        PrintMsg(" \nOutput soils layer has " + Number_Format(outCnt, 0, True) + " polygons", 0)

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
        prec = 2
        units = "cm"


        #if AddAttributeFields(outputShp) == "":
        #    raise MyError, ""


        ratingValues = AttributeRequest(sdaURL, mukeyList, outputShp, ratingField)


        if len(ratingValues) == 0:
            raise MyError, ""


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
