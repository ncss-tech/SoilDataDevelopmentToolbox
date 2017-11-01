# gSSURGO_Clip2.py
#
# Steve Peaslee, USDA-NRCS NCSS
#
# Designed to be used to clip the MUPOLYGON featureclass in a 'tiled' gSSURGO database.
# The clipped soil polygon featureclass would also reside in the gSSURGO database and include
# the tile attribute as part of its name.

# Original coding 2017-08-21

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
def ProcessLayer(gdb, aoiLayer, aoiField, aoiValue):

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

        if fieldType in ["SMALLINTEGER", "LONGINTEGER", "SINGLE"]:
            sql = aoiField + " = " + int(aoiValue)

        else:
            sql = aoiField + " = '" + aoiValue + "'"

        PrintMsg(" \nClipping soil polygons for " + sql, 0)

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
        PrintMsg(" \nAOI Extent:  " + str(xMin) + "; " + str(yMin) + "; " + str(xMax) + "; " + str(yMax), 0)

        # Select target layer polygons within the AOI extent
        # in a script, the featurelayer (extentLayer) may not exist
        #
        PrintMsg(" \nSelecting target layer polygons within AOI", 0)
        arcpy.MakeFeatureLayer_management(extentFC, extentLayer)

        inputDesc = arcpy.Describe(soilsLayer)
        inputGDB = os.path.dirname(inputDesc.catalogPath)  # assuming gSSURGO, no featuredataset
        outputGDB = os.path.dirname(outputClip)

        if not inputDesc.hasSpatialIndex:
            arcpy.AddSpatialIndex_management(soilsLayer)

        arcpy.SelectLayerByLocation_management(soilsLayer, "INTERSECT", extentLayer, "", "NEW_SELECTION")

        # Create temporary featureclass using selected target polygons
        #
        PrintMsg(" \n\tCreating temporary featureclass", 0)
        arcpy.CopyFeatures_management(soilsLayer, outputFC)
        #arcpy.MakeFeatureLayer_management(outputFC, selectedPolygons)
        arcpy.SelectLayerByAttribute_management(soilsLayer, "CLEAR_SELECTION")

        # Create spatial index on temporary featureclass to see if that speeds up the clip
        arcpy.AddSpatialIndex_management(outputFC)

        # Clipping process
        if operation == "CLIP":
            PrintMsg(" \n\tCreating final layer " + os.path.basename(outputClip) + "...", 0)
            arcpy.Clip_analysis(outputFC, aoiLayer, outputClip)
            arcpy.AddSpatialIndex_management(outputClip)

        elif operation == "INTERSECT":
            PrintMsg(" \nPerforming final intersection...", 0)
            arcpy.Intersect_analysis([outputFC, aoiLayer], outputClip)

        if arcpy.Exists(outputClip) and outputGDB == inputGDB and arcpy.Exists(os.path.join(outputGDB, "mapunit")):
            # Create relationshipclass to mapunit table
            relName = "zMapunit_" + os.path.basename(outputClip)

            if not arcpy.Exists(os.path.join(outputGDB, relName)):
                arcpy.AddIndex_management(outputClip, ["mukey"], "Indx_" + os.path.basename(outputClip))
                #PrintMsg(" \n\tAdding relationship class...")
                arcpy.CreateRelationshipClass_management(os.path.join(outputGDB, "mapunit"), outputClip, os.path.join(outputGDB, relName), "SIMPLE", "> Mapunit Polygon Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

        # Clean up temporary layers and featureclasses
        #
        cleanupList = [extentLayer, extentFC, outputFC]

        for layer in cleanupList:
            if arcpy.Exists(layer):
                arcpy.Delete_management(layer)

        # Clear selection on aoiLayer
        arcpy.SelectLayerByAttribute_management(aoiLayer, "CLEAR_SELECTION", sql)

        PrintMsg(" \nClipping process complete for " + str(aoiValue) + " \n", 0)


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n", 2)
        return True

    except:
        errorMsg()
        return False


## ===================================================================================
# main
import string, os, sys, traceback, locale, arcpy, time

from arcpy import env

try:
    if __name__ == "__main__":
        # Script arguments...
        gdb = arcpy.GetParameterAsText(0)          # e.g. gSSURGO database
        aoiLayer = arcpy.GetParameterAsText(1)     # e.g. HUC12 featureclass
        aoiField = arcpy.GetParameterAsText(2)     # HUC12 column
        aoiValue = arcpy.GetParameter(3)           # HUC12 code


        #bProcessed = ProcessLayer(soilsLayer, aoiLayer, outputClip, operation)
        bProcessed = ProcessLayer(gdb, aoiLayer, aoiField, aoiValue)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

