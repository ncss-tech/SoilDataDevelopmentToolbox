# SSURGO_CheckgSSURGO.py
#
# Steve Peaslee, USDA-NRCS NCSS
#
# Check the status map polygon layer to ensure that there are no overlapping polygons
#

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

        return "???"

## ===================================================================================
def ProcessSurveyArea(ssaLayer, areasym):
    # New function
    try:

        epsgWM = 3857 # Web Mercatur
        wmSR = arcpy.SpatialReference(epsgWM)
        #tm = "WGS_1984_(ITRF00)_To_NAD_1983"

        tmpPolys = os.path.join(env.scratchGDB, "tmpPolys")
        tmpClip = os.path.join(env.scratchGDB, "tmpClip")
        dOverlap = dict()

        wc = "AREASYMBOL = '" + areasym + "'"
        arcpy.SelectLayerByAttribute_management(ssaLayer, "NEW_SELECTION", wc)
        arcpy.CopyFeatures_management(ssaLayer, tmpPolys)
        arcpy.SelectLayerByAttribute_management(ssaLayer, "CLEAR_SELECTION", "")
        arcpy.Clip_analysis(ssaLayer, tmpPolys, tmpClip)
        dAreas = dict()
        areaList = list()
        cur2 = arcpy.da.SearchCursor(tmpClip, ["AREASYMBOL", "SHAPE@AREA"], "", wmSR)

        for rec2 in cur2:
            sym, area = rec2
            areaList.append(area)

            if sym in dAreas:
                dAreas[sym] += area
            else:
                dAreas[sym] = area

        del rec2, cur2
        #PrintMsg(" \n" + areasym, 0)

        dAreas2 = dict()

        for sym, area in dAreas.items():
            dAreas2[area] = sym
            #PrintMsg("\t" + sym + ", " + str(area), 1)

        totalArea = sum(areaList)

        i = 0
        dOverlap[areasym] = 0.0

        for area in sorted(dAreas2, reverse=True):
            sym = dAreas2[area]
            pct = 100.0 * (area / totalArea)

            if sym != areasym:
                dOverlap[areasym] += area

            if pct > 0.01 and sym != areasym:
                PrintMsg("\t" + sym + ", " + str(area), 1)

        PrintMsg(areasym + ", " + str(dOverlap[areasym]), 0)

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
# main
import string, os, sys, traceback, locale, arcpy
from arcpy import env


try:
    ssaLayer = arcpy.GetParameter(0)
    arcpy.overwriteOutput = True
    from arcpy import env

    # Script arguments...
    statusMapLayer = arcpy.GetParameter(0)               # input status map layer



    # Begin by creating a unique list of areasymbols
    arcpy.SelectLayerByAttribute_management(ssaLayer, "CLEAR_SELECTION", "")
    areasyms = list()

    with arcpy.da.SearchCursor(ssaLayer, ["AREASYMBOL"]) as cur1:
        for rec in cur1:
            areasym = rec[0]

            if not areasym is None and not areasym in areasyms:
                areasyms.append(areasym)

    for areasym in sorted(areasyms):
        if ProcessSurveyArea(ssaLayer, areasym) == False:
            raise MyError, ""

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n ", 2)

except:
    errorMsg()
