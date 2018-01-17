# gSSURGO_Clip.py
#
# Steve Peaslee, USDA-NRCS NCSS
#
# Designed to be used for clipping soil polygons from a very large featureclass

# Original coding 2016-01-04

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
def ProcessLayer(targetLayer, aoiLayer, outputClip, operation):
    # output featureclass is outputClip
    try:

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
        if operation == "CLIP":
            # PrintMsg(" \n\tCreating final layer " + os.path.basename(outputClip) + "...", 0)
            arcpy.Clip_analysis(outputFC, aoiLayer, sortedFC)
            outCnt = int(arcpy.GetCount_management(sortedFC).getOutput(0))

            if outCnt > 0:
                #PrintMsg(" \n\t\tCreating temporary featureclass", 0)
                fields = arcpy.Describe(targetLayer).fields
                shpField = [f.name for f in fields if f.type.upper() == "GEOMETRY"][0]

                # re-sort polygons after clip to get rid of tile artifact
                if bOverwrite and arcpy.Exists(outputClip):
                    arcpy.Delete_management(outputClip)

                arcpy.Sort_management(sortedFC, outputClip, [[shpField, "ASCENDING"]], "UL")  # Try sorting before clip. Not sure if this well help right here.
                PrintMsg(" \n\tCreating final layer " + os.path.basename(outputClip) + "...", 0)
                arcpy.AddSpatialIndex_management(outputClip)

                if arcpy.Exists(outputClip) and outputGDB == inputGDB and arcpy.Exists(os.path.join(outputGDB, "mapunit")):
                    # Create relationshipclass to mapunit table
                    relName = "zMapunit_" + os.path.basename(sortedFC)

                    if not arcpy.Exists(os.path.join(outputGDB, relName)):
                        arcpy.AddIndex_management(outputClip, ["mukey"], "Indx_" + os.path.basename(outputClip))
                        #PrintMsg(" \n\tAdding relationship class...")
                        arcpy.CreateRelationshipClass_management(os.path.join(outputGDB, "mapunit"), outputClip, os.path.join(outputGDB, relName), "SIMPLE", "> Mapunit Polygon Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                # Clean up temporary layers and featureclasses
                #
                cleanupList = [extentLayer, extentFC, outputFC, sortedFC]

                for layer in cleanupList:
                    if arcpy.Exists(layer):
                        arcpy.Delete_management(layer)

                del extentLayer, extentFC, outputFC, sortedFC
                arcpy.SetParameter(2, outputClip)
                #PrintMsg(" \nFinished \n", 0)

            else:
                if arcpy.Exists(sortedFC):
                    PrintMsg("\tCreated empty clipped soils layer", 1)

                else:
                    PrintMsg("\tFailed to create clipped soils layer", 1)

                # Clean up temporary layers and featureclasses
                #
                cleanupList = [extentLayer, extentFC, outputFC, sortedFC]

                for layer in cleanupList:
                    if arcpy.Exists(layer):
                        arcpy.Delete_management(layer)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False


## ===================================================================================
# main
import string, os, sys, traceback, locale, arcpy, time

from arcpy import env

try:

    # Script arguments...
    soilsLayer = arcpy.GetParameterAsText(0)  # e.g. Soil Polygons
    aoiLayer = arcpy.GetParameterAsText(1)     # e.g. CLU polygons
    aoiField = arcpy.GetParameterAsText(2)     # attribute fieldname
    aoiValues = arcpy.GetParameter(3)          # attribute values
    bOverwrite = arcpy.GetParameter(4)   # overwrite existing featureclasses

    env.overwriteOutput = True
    operation = "CLIP"

    # Get output geodatabase
    desc = arcpy.Describe(soilsLayer)
    field = arcpy.ListFields(aoiLayer, aoiField)[0]
    fieldType = field.type.upper()  # STRING, DOUBLE, SMALLINTEGER, LONGINTEGER, SINGLE, FLOAT
    #PrintMsg(" \nAOI field type: " + fieldType, 1)
    
    catalogPath = desc.catalogPath
    gdb = os.path.dirname(catalogPath)
    env.workspace = gdb

    if not gdb.endswith(".gdb"):
        gdb = os.path.dirname(gdb)

    aoiDesc = arcpy.Describe(aoiLayer)

    if aoiDesc.dataType.upper() == "FEATURECLASS":
        # swap the input featureclass with a featurelayer.
        fcPath = inputDesc.catalogPath
        aoiLayer = inputDesc.aliasName
        arcpy.MakeFeatureLayer_management(fcPath, aoiLayer)

    if aoiField == "":
        # Process in batch mode
        field = field.name

        existingLayers = arcpy.ListFeatureClasses("MUPOLYGON_Clip*")

        if not "MUPOLYGON_Clip" in existingLayers:
            outputClip = os.path.join(gdb, "MUPOLYGON_Clip")

        else:
            for i in range(1, 100):
                outputClip = os.path.join(gdb, "MUPOLYGON_Clip" + "%02d" % (i,))
                if not arcpy.Exists(outputClip):
                    break

        bProcessed = ProcessLayer(soilsLayer, aoiLayer, outputClip, operation)

    else:
        # This method creates featureclasses named by the tile attribute value
        attrList = list()
        arcpy.SetProgressor("step", "Clipping soils layer...", 1, len(aoiValues), 1)
        pos = 1
        cnt = len(aoiValues)

        for attr in sorted(aoiValues):
            arcpy.SetProgressorPosition(pos)
            outputClip = os.path.join(gdb, arcpy.ValidateTableName("MUPOLYGON_" + str(attr), gdb))
            arcpy.SetProgressorLabel("Creating featureclass " + os.path.basename(outputClip) + "  ( " + str(pos) + " of " + str(cnt) + " )")

            if fieldType in ["SMALLINTEGER", "LONGINTEGER", "SINGLE", "INTEGER", "LONG"]:
                sql = aoiField + " = " + attr
                attrList.append(int(attr))

            else:
                sql = aoiField + " = '" + attr + "'"
                attrList.append(attr.encode('ascii') )

            #PrintMsg(" \nClipping soil polygons for " + sql, 0)
            if not arcpy.Exists(outputClip) or bOverwrite:

                arcpy.SelectLayerByAttribute_management(aoiLayer, "NEW_SELECTION", sql)
                bProcessed = ProcessLayer(soilsLayer, aoiLayer, outputClip, operation)
                if bProcessed == False:
                    raise MyError, ""

            else:
                PrintMsg(" \nSkipping existing featureclass " + os.path.basename(outputClip), 1)

            pos += 1

        # Re-apply the original selection to the aoiLayer
        if len(attrList) > 1:
            sql = aoiField + " in " + str(tuple(attrList))

        else:
            if fieldType in ["SMALLINTEGER", "LONGINTEGER", "SINGLE", "INTEGER", "LONG"]:
                sql = aoiField + " = " + str(attrList[0])

            else:
                sql = aoiField + " = '" + attrList[0] + "'"

        PrintMsg(" \nResetting aoi selection using " + sql + " \n", 0)
        arcpy.SelectLayerByAttribute_management(aoiLayer, "NEW_SELECTION", sql)

    PrintMsg(" \nClipping process complete for " + gdb + " \n", 0)



except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
