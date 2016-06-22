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
# main
import string, os, sys, traceback, locale, arcpy, time

from arcpy import env

try:

    # Script arguments...
    targetLayer = arcpy.GetParameterAsText(0)  # e.g. Soil Polygons
    aoiLayer = arcpy.GetParameterAsText(1)     # e.g. CLU polygons
    outputClip = arcpy.GetParameterAsText(2)   # clipped soil polygons
    operation = arcpy.GetParameter(3)          # CLIP or INTERSECT

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
    cleanupList = [extentLayer, extentFC, outputFC]

    for layer in cleanupList:
        if arcpy.Exists(layer):
            arcpy.Delete_management(layer)

    # Find extents of the AOI
    #
    PrintMsg(" \nGetting extent for AOI", 0)
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
    PrintMsg(" \nExtent:  " + str(xMin) + "; " + str(yMin) + "; " + str(xMax) + "; " + str(yMax), 0)

    # Select target layer polygons within the AOI extent
    # in a script, the featurelayer (extentLayer) may not exist
    #
    PrintMsg(" \nSelecting target layer polygons within AOI", 0)
    arcpy.MakeFeatureLayer_management(extentFC, extentLayer)
    arcpy.SelectLayerByLocation_management(targetLayer, "INTERSECT", extentLayer, "", "NEW_SELECTION")

    # Create temporary featureclass using selected target polygons
    #
    PrintMsg(" \nCreating temporary featureclass", 0)
    arcpy.CopyFeatures_management(targetLayer, outputFC)
    #arcpy.MakeFeatureLayer_management(outputFC, selectedPolygons)
    arcpy.SelectLayerByAttribute_management(targetLayer, "CLEAR_SELECTION")

    # Clipping process
    if operation == "CLIP":
        PrintMsg(" \nPerforming final clip...", 0)
        arcpy.Clip_analysis(outputFC, aoiLayer, outputClip)

    elif operation == "INTERSECT":
        PrintMsg(" \nPerforming final intersection...", 0)
        arcpy.Intersect_analysis([outputFC, aoiLayer], outputClip)

    # Clean up temporary layers and featureclasses
    #
    cleanupList = [extentLayer, extentFC, outputFC]

    for layer in cleanupList:
        if arcpy.Exists(layer):
            arcpy.Delete_management(layer)

    arcpy.SetParameter(2, outputClip)
    PrintMsg(" \nFinished", 0)

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
