# WSS_CreateAOIZipfile.py
#
# Zips polygons from selected set as a package for use as a Web Soil Survey AOI.
# Note: 32 polygon limit for WSS AOI shapefiles.
#
# 11-15-2016 version 1.0
#
# Biggest issue right now is Web Soil Survey's problems handling adjacent polygons
# Switched WSS URL to HTTPS

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
def CleanShapefile(inputAOI, bDissolve):
    # Export the selected featurelayer to shapefile format used as a shapefile name
    #
    # This version of the CleanShapefile function uses the FeatureclassToCoverage_conversion tool
    # It buffers and erases the edge of polygon boundaries only where there is a neighbor. This
    # means that we also need use the RemoveIntersections function to get rid of self-intersecting points.

    try:

        # temporary shapefiles. Some may not be used.
        outputFolder = os.path.dirname(outputZipfile)
        #tmpFolder = env.scratchGDB
        tmpFolder = "IN_MEMORY"

        simpleShp = os.path.join(tmpFolder, "aoi_simple")
        dissShp = os.path.join(tmpFolder, "aoi_diss")
        lineShp = os.path.join(tmpFolder, "aoi_line")
        labelShp = os.path.join(tmpFolder, "aoi_label")
        polyShp = os.path.join(tmpFolder, "aoi_poly")
        pointShp = os.path.join(tmpFolder, "aoi_point")
        joinShp = os.path.join(tmpFolder, "aoi_join")
        cleanShp = os.path.join(tmpFolder, "aoi_clean")
        aoiCov = os.path.join(env.scratchFolder, "aoi_cov")

        outputShp = os.path.join(env.scratchFolder, "wss_aoi.shp")

        if arcpy.Exists(outputShp):
            arcpy.Delete_management(outputShp, "FEATURECLASS")

        # Create a new featureclass with just the selected polygons
        arcpy.MultipartToSinglepart_management(inputAOI, simpleShp)
        #arcpy.CopyFeatures_management(inputAOI, simpleShp)

        cnt = int(arcpy.GetCount_management(simpleShp).getOutput(0))
        if cnt == 0:
            raise MyError, "No polygon features in " + simpleShp

        # Try to eliminate small slivers using Integrate function.
        # Integrate should also add vertices so both shared boundaries are the same.
        arcpy.Integrate_management(simpleShp, "0.05 Meters")  # was 0.1 Meters. Trying to figure out why my lines snapped and caused buffer problems

        # Describe the input layer
        desc = arcpy.Describe(simpleShp)
        #dataType = desc.featureclass.dataType.upper()
        fields = desc.fields
        fldNames = [f.baseName.upper() for f in fields]
        #PrintMsg(" \nsimpleShp field names: " + ", ".join(fldNames), 1)

        if bDissolve:
            # User wants remove boundaries between adjacent polygons
            PrintMsg(" \nDissolving unneccessary polygon boundaries for Web Soil Survey AOI...", 0)
            #arcpy.Dissolve_management(simpleShp, dissShp, "", "", "SINGLE_PART") # this is the original that works
            arcpy.Dissolve_management(simpleShp, dissShp, "", "", "MULTI_PART") # this is the one to test for common points

        else:
            # Keep original boundaries, but if attribute table contains PARTNAME or LANDUNIT attributes, dissolve on that
            #

            if "LAND_UNIT_TRACT_NUMBER" in fldNames and "LAND_UNIT_LAND_UNIT_NUMBER" in fldNames:
                # Go ahead and dissolve using PartName which was previously added
                PrintMsg(" \nUsing Planned Land Unit polygons to build AOI for Web Soil Survey", 0)
                arcpy.AddField_management(simpleShp, "PARTNAME", "TEXT", "", "", 20)
                curFields = ["PARTNAME", "LAND_UNIT_TRACT_NUMBER", "LAND_UNIT_LAND_UNIT_NUMBER"]

                with arcpy.da.UpdateCursor(simpleShp, curFields) as cur:
                    for rec in cur:
                        # create stacked label for tract and field
                        partName = "T" + str(rec[1]) + "\nF" + str(rec[2])
                        rec[0] = partName
                        cur.updateRow(rec)

                #arcpy.Dissolve_management(simpleShp, dissShp, ["PARTNAME"], "", "SINGLE_PART")
                arcpy.Dissolve_management(simpleShp, dissShp, ["PARTNAME"], "", "MULTI_PART")

            elif "PARTNAME" in fldNames:
                # Regardless, dissolve any polygons on PartName
                PrintMsg(" \nUsing PartName polygon attributes to build AOI for Web Soil Survey", 0)
                #arcpy.Dissolve_management(simpleShp, dissShp, "PartName", "", "SINGLE_PART")
                arcpy.Dissolve_management(simpleShp, dissShp, "PartName", "", "MULTI_PART")

            else:
                dissShp = simpleShp
                PrintMsg(" \nUsing original polygons to build AOI for Web Soil Survey...", 0)

        env.workspace = env.scratchFolder

        if not arcpy.Exists(dissShp):
            raise MyError, "Missing " + dissShp

        if RemoveCommonBoundaries(dissShp, aoiCov, lineShp, pointShp, outputShp) == False:
            raise MyError, ""

        arcpy.RepairGeometry_management(outputShp, "DELETE_NULL")  # Need to make sure this isn't doing bad things.

        # Not sure if all these fields are present and whether the lack would cause an error.
        #arcpy.DeleteField_management(outputShp, ['Join_Count', 'TARGET_FID', 'ORIG_FID', 'PartName_1', 'ORIG_FID_1'])

        # END OF CLEAN

        return True


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False


    except:
        errorMsg()
        return False

## ===================================================================================
def MakeZipFile(outputZipfile):
    # Export the selected featurelayer to shapefile format used as a shapefile name
    import zipfile

    try:
        # Using env.workspace location. Assuming output shapefile is named 'wss_aoi.shp'
        #
        shpExtensions = ['.shp', '.shx', '.prj', '.dbf', '.sbn']

        if arcpy.Exists(outputZipfile):
            PrintMsg(" \nDeleting zipfile " + outputZipfile, 1)
            arcpy.Delete_management(outputZipfile, "FILE")

        shpFiles = arcpy.ListFiles("wss_aoi.*")
        if len(shpFiles) == 0:
            raise MyError, "Output shapefile wss_aoi.shp not found"

        #PrintMsg(" \nFound " + str(len(shpFiles)) + " matching shapefiles to zip", 1)
        PrintMsg(" \n", 1)

        with zipfile.ZipFile(outputZipfile, 'a', zipfile.ZIP_DEFLATED) as myZip:
            for shp in shpFiles:
                fn, ext = os.path.splitext(shp)

                if ext.lower() in shpExtensions:
                    # archive each individual file ('.shp', '.shx', '.prj', '.dbf')
                    #PrintMsg("\tAdding " + shp + " to zip archive", 0)
                    myZip.write(os.path.join(env.workspace, shp), os.path.basename(shp))


        PrintMsg(" \nSaved final Web Soil Survey AOI shapefile to: \n" + outputZipfile + " \n ", 0 )

        bWSS = OpenWSS(os.path.join(env.workspace, "wss_aoi.shp"))


        return True


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def RemoveCommonBoundaries(inLayer, aoiCov, lineShp, pointShp, outputShp):

    # Given a polygon featurelayer and a line coverage, remove all coincident boundaries.
    # Should I assume a projected coordinate system for the data frame?

    try:
        # Get spatial reference for input layer
        desc = arcpy.Describe(inLayer)
        featureType = desc.shapeType
        inputSR = desc.spatialReference

        # Create some more temporary shapefiles within this function. Need to make these scratchGDB featureclasses instead.
        #
        tmpFolder = "IN_MEMORY"
        #tmpFolder = env.scratchFolder

        clipShp = os.path.join(tmpFolder, "aoi_clip")
        convexShp = os.path.join(tmpFolder, "aoi_convex")
        buffShp = os.path.join(tmpFolder, "aoi_buffer")

        if inputSR.type.upper() == "GEOGRAPHIC":
            # Use Web Mercatur coordinate system for buffers when input coordinate system is Geographic
            epsgWM = 3857
            buffSR = arcpy.SpatialReference(epsgWM)
            weedTol = 0.000001

        else:
            buffSR = inputSR
            weedTol = 0.1

        #env.outputCoordinateSystem = buffSR    # Make sure that buffers are created with a projected coordinate system
        #env.geographicTransformations =  "WGS_1984_(ITRF00)_To_NAD_1983"

        # Convert the AOI polygons to a line shapefile an ArcInfo coverage.
        # The line shapefile is used along with 'label' points to create a new, cleaner polygon shapefile
        # that has vertices from adjacent polygons.
        #PrintMsg(" \nConverting " + featureType +  " layer '" + inLayer + "' to coverage " + aoiCov, 1)
        layers = [[inLayer, "POLYGON"]]

        arcpy.FeatureclassToCoverage_conversion(layers, aoiCov, weedTol, "DOUBLE")  # requires Advanced license

        arcCnt = int(arcpy.GetCount_management(os.path.join(aoiCov, "arc")).getOutput(0))

        if arcCnt == 0:
            raise MyError, "Conversion to coverage failed"

        env.outputCoordinateSystem = buffSR    # Make sure that buffers are created with a projected coordinate system
        env.geographicTransformations =  "WGS_1984_(ITRF00)_To_NAD_1983"

        # Check identify coincident boundaries in line coverage
        #
        # Create a featureclass from the coverage that consists of just the common boundaries
        wc = '"$LEFTPOLYGON" <> 1 AND "$RIGHTPOLYGON" <> 1'
        arcpy.MakeFeatureLayer_management(os.path.join(aoiCov, "arc"), "CommonBnd", wc)

        # NEED NEW CODE HERE. CONVERT THESE COVERAGE LINES TO lineShp and buffer that instead of directly
        if arcpy.Exists(lineShp):
            arcpy.Delete_management(lineShp)

        # Need to do a count here to make sure that there are common boundaries to buffer
        bndCnt = int(arcpy.GetCount_management("CommonBnd").getOutput(0))

        if bndCnt > 0:
            #PrintMsg(" \nCreating " + str(bndCnt) + " boundary buffers as " + buffShp, 1)
            arcpy.CopyFeatures_management("CommonBnd", lineShp)  # uses outputCoordinateSystem setting

            # Buffer interior boundaries to create buffShp, a multipart polygon featureclass
            arcpy.Buffer_analysis(lineShp, buffShp, "0.1 Meters", "FULL", "ROUND", "ALL", "", "GEODESIC")  # should use outputCoordinateSystem setting
            buffCnt = int(arcpy.GetCount_management(buffShp).getOutput(0))

            if buffCnt == 0:
                raise MyError, "Failed to create boundary buffers (" + buffShp + ")"
            #else:
            #    PrintMsg(" \n" + buffShp + " has " + str(buffCnt) + " polygon buffers", 1)

        else:
            #PrintMsg(" \nNo interior boundaries found", 0)
            pass

        # Begin looking for polygons that self-intersect at a point. These are OK in ArcGIS, but not Web Soil Survey.
        # I have an issue. For some data I will be processing aoi_diss which has no multipart polygons. Catty-corner
        # polygons that intersect at a single point don't seem to bother WSS though. If that changes in the future,
        # I should probably change the Dissolve command to allow multipart polygons and see if the routine below
        # will start flagging those points and cleaning them up.
        #
        iCnt = 0
        dDups = dict()
        flds = ["OID@","SHAPE@"]

        with arcpy.da.SearchCursor(inLayer, flds, "", buffSR) as cursor:
            polyNum = 0
            #PrintMsg(" \nFinding self-intersections in " + inLayer, 0)

            for row in cursor:
                pntList = list()  # clear point list for the new polygon
                dupList = list()  # clear duplicate point list for the new polygon
                fid = row[0]
                #PrintMsg("\tChecking polygon " + str(fid), 1)
                polyNum += 1
                partNum = 0

                for part in row[1]:
                    # look for duplicate points within each polygon part
                    #
                    #PrintMsg(" \nPolygon " + str(polyNum) + " part " + str(partNum), 1)
                    partNum += 1
                    bRing = True  # helps prevent from-node from being counted as a duplicate of to-node

                    for pnt in part:
                        if pnt:
                            if not bRing:
                                # add vertice or to-node coordinates to list
                                #PrintMsg("\tPart " + str(partNum) + " point " + str(pnt.X) + ", " + str(pnt.Y), 1)
                                pntList.append((pnt.X,pnt.Y))

                            bRing = False

                        else:
                            # interior ring encountered
                            ring = pntList.pop()  # removes first node from list
                            bRing = True  # prevents island from-node from being identified as a duplicate of the to-node

                # get duplicate coordinate pairs within the list of vertices for the current attribute value
                #PrintMsg(" \nPointList: " + str(pntList), 0)
                dupList = [x for x, y in collections.Counter(pntList).items() if y > 1]

                if len(dupList) > 0:
                    #PrintMsg(" \nDuplicate points found", 1)
                    dDups[fid] = dupList
                    iCnt += len(dupList)

        if len(dDups) > 0:
            # Self-intersecting points were found
            #
            if bndCnt == 0:
                # If no adjacent polygon boundaries exist, then we will need to create a featureclass to contain the point buffers

                if arcpy.Exists(buffShp):
                    # Remove featureclass from previous run
                    arcpy.Delete_management(buffShp)

                arcpy.CreateFeatureclass_management(os.path.dirname(buffShp), os.path.basename(buffShp), "POLYGON", "", "DISABLED", "DISABLED", buffSR)


            # open buffer featureclass and add common point locations
            #
            # Other thoughts. I wonder if I could use buffers to clip from lineShp and use those clipped lines to
            # create a convex hull which would then be added to the buffShp. This might be a cleaner clip on the self-intersection.

            # The buffer function on point geometry does not allow for units. Do I need to specify a projected coordinate
            # system for the InsertCursor or do I need to change my tolerance from 0.1 to 0.000001 when GCS????????
            #
            arcpy.CreateFeatureclass_management(os.path.dirname(pointShp), os.path.basename(pointShp), "POLYGON", "", "DISABLED", "DISABLED", buffSR)

            tol = 0.12
            pntCnt = 0

            with arcpy.da.InsertCursor(pointShp, ["SHAPE@"]) as cursor:
                # for each value that has a reported common-point, get the list of coordinates from
                # the dDups dictionary and write to the output Common_Points featureclass
                for val, coords in dDups.items():

                    for coord in coords:
                        #PrintMsg("\tAdding point buffer to point buffer featureclass " + str(pointShp) + " (" + str(coord) + ")", 1)
                        newPoint = arcpy.Point(coord[0], coord[1])

                        newBuffer = arcpy.PointGeometry(newPoint).buffer(tol)  # 1.5, 1.1, 1.0, 0.1
                        if newBuffer.type == "polygon":
                            cursor.insertRow([newBuffer]) # write buffer to featureclass
                            pntCnt += 1

                        else:
                            raise MyError, "Input buffer geometry is a " + newBuffer.type + " instead of polygon"

            tol = "0.01 Meters"

            # Create clipping polygons for each point of self-intersection
            # clip lines around self-intersection
            #arcpy.Clip_analysis(lineShp, pointShp, clipShp, tol)   # clip interior lines around self-intersection
            arcpy.Clip_analysis(os.path.join(aoiCov, "arc"), pointShp, clipShp, tol)   # clip ALL lines around self-intersection

            clipCnt = int(arcpy.GetCount_management(clipShp).getOutput(0))

            if clipCnt == 0:
                raise MyError, "Failed to clip any lines with point buffer"

            #else:
            #    PrintMsg(" \nPoint clip contains " + str(clipCnt) + " lines", 1)

            # create convex hull polygons for each set of clipped lines
            arcpy.MinimumBoundingGeometry_management(clipShp, convexShp, "CONVEX_HULL", "LIST", "F_LEFTPOLYGON")
            # add convex hull polygons to buffer featureclass
            #PrintMsg(" \nAdding " + str(pntCnt) + " buffered points to " + buffShp, 1)
            arcpy.Append_management(convexShp, buffShp, "NO_TEST")

        # Set final output coordinate system to match that of Web Soil Survey (GCS_WGS_1984)
        # Failure to do so may result in WSS applying a datum transformation and shifting the data when it imports the AOI.
        env.outputCoordinateSystem = arcpy.SpatialReference(4326)    # GCS_WGS_1984
        env.geographicTransformations =  "WGS_1984_(ITRF00)_To_NAD_1983"

        if len(dDups) > 0 or bndCnt > 0:
            # Erase the buffered areas from the input AOI featureclass
            #PrintMsg(" \nRunning erase on " + inLayer + " using " + buffShp, 0)
            arcpy.Erase_analysis(inLayer, buffShp, outputShp, "0.01 Meters")  # these will snap back together when set to 0.1 meters

            if arcpy.Exists(outputShp):
                #PrintMsg(" \nCreated final output featureclass with clean boundary: \n" + outputShp, 0)
                pass

            else:
                raise MyError, "Failed to create output featureclass: " + outputShp

        else:
            arcpy.CopyFeatures_management(inLayer, outputShp)

            if arcpy.Exists(outputShp):
                #PrintMsg(" \nCreated final output featureclass with original boundaries: \n" + outputShp, 0)
                pass

            else:
                raise MyError, "Failed to create output featureclass: " + outputShp

        # End of self-intersections

        # Run integrate one more time. Had an AOI fail. Perhaps too many close vertices at buffer corners?
        arcpy.Integrate_management(outputShp, "0.05 Meters")

        # Clean up IN_MEMORY workspace
        arcpy.Delete_management("IN_MEMORY")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        arcpy.Delete_management("IN_MEMORY")
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def FormSpatialQuery(theAOI):
    #
    # Create a simplified WKT version of the AOI with coordinates rounded off to 6 places.
    # This function will not work with WSS 3.2.1 because it allows multiple polygons and interior rings.

    try:

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

        gcs = arcpy.SpatialReference(epsgWGS)
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
def OpenWSS(outputShp):

    # Try to open WSS to the extent of the AOI

    try:
        # Get extent for the output shapefile and try to open WSS to that location
        # The output shapefile will be GCS WGS 1984

        import webbrowser

        aoiCnt = int(arcpy.GetCount_management(outputShp).getOutput(0))
        if aoiCnt > 32:
            raise MyError, "AOI shapefile has " + Number_Format(aoiCnt, 0, True) + " polygons, exceeding the WSS limit of 32"

        x = arcpy.Describe(arcpy.Describe(outputShp).catalogPath).extent

        # AOICOORDS: Sets overall extent of the AOI and creates a temporary AOI polygon (hatched layer in WSS)
        #sExtent = str(x.XMin) + " " + str(x.YMin) + "," + str(x.XMin) + " " + str(x.YMax) + "," + str(x.XMax) + " " + str(x.YMax) + "," + str(x.XMax) + " " + str(x.YMin) + "," + str(x.XMin) + " " + str(x.YMin)
        #aoiURL = "http://websoilsurvey.sc.egov.usda.gov/App/WebSoilSurvey.aspx?aoicoords=((" + sExtent + "))"

        #wkt = FormSpatialQuery(outputShp)
        #sExtent = wkt  # try using actual polygon AOI coordinates. This will not work with multiple polygons or interior rings. Also very limited number of coordinates allowed.
        #aoiURL = "http://websoilsurvey.sc.egov.usda.gov/App/WebSoilSurvey.aspx?aoicoords=" + wkt

        # LOCATION: Sets overall extent of the AOI (plus 10%) without creating an AOI polygon in WSS
        xDiff = (x.XMax - x.XMin) / 10.0
        yDiff = (x.YMax - x.YMin) / 10.0
        sExtent = str(x.XMin - xDiff) + " " + str(x.YMin - yDiff) + "," + str(x.XMax + xDiff) + " " + str(x.YMax + yDiff)


        # Production WSS
        aoiURL = "https://websoilsurvey.sc.egov.usda.gov/App/WebSoilSurvey.aspx?location=(" + sExtent + ")"

        # Dev WSS
        #aoiURL = "http://websoilsurvey-dev.dev.sc.egov.usda.gov/App//WebSoilSurvey.aspx?location=(" + sExtent + ")"

        #PrintMsg(" \n" + aoiURL, 1)
        #PrintMsg(" \n" + sExtent, 1)
        webbrowser.open_new_tab(aoiURL)


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## main
##

import os, sys, traceback, collections
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
    inputAOI = arcpy.GetParameterAsText(0)                   # input AOI feature layer
    featureCnt = arcpy.GetParameter(1)                        # String. Number of polygons selected of total features in the AOI featureclass.
    outputZipfile = arcpy.GetParameterAsText(2)               # AOI zip file for WSS
    bDissolve = arcpy.GetParameter(3)                         # User does not want to keep individual polygon or field boundaries

    env.overwriteOutput= True

    licenseLevel = arcpy.ProductInfo().upper()
    if licenseLevel != "ARCINFO":
        raise MyError, "License level must be Advanced to run this tool"


    bClean = CleanShapefile(inputAOI, bDissolve)

    if bClean:
        bZipped = MakeZipFile(outputZipfile)




except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
