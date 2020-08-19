# SSURGO_ExportMuRaster_Batch.py
#
# Batch mode conversion of MUPOLYGON featureclass to raster for the specified
# SSURGO geodatabases.
#
# Input mupolygon featureclass must have a projected coordinate system or it will skip.
# Input databases and featureclasses must use naming convention established by the
# 'SDM Export By State' tool.
#
# Current version of tool tries to use the output coordinate system to set
# the cell alignment. This effectively acts as a snapraster to try and align
# the raster to the NLCD landcover raster. If a snapraster is specified,
# this does not apply.
#
# 10-31-2013 Added gap fill method
#
# 01-08-2014
# 2014-09-27
# 2015-03-10 Added tile option. AREASYMBOL attribute required for the input polygon featureclass (MUPOLYGON)
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
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed seconds
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
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, math, time
from arcpy import env
from arcpy.sa import *

# Create the Geoprocessor object
try:
    # get parameters
    dataType = arcpy.GetParameter(0)                      # 'All MUPOLYGON layers' or 'Standard MUPOLYGON layer'. Only used in the Validation code.
    inputFolder = arcpy.GetParameterAsText(1)             # Folder containing all geodatabases to be processed
    gdbList = arcpy.GetParameter(2)                     # list of geodatabase names to be processed
    iRaster = arcpy.GetParameter(3)                       # output raster resolution
    bTiled = arcpy.GetParameter(4)                        # breakup raster conversion using AREASYMBOL attribute to tile the process

    import SSURGO_ExportMuRaster

    env.overwriteOutput = True
    arcpy.CheckOutExtension("Spatial")

    start = time.time()
    arcpy.SetProgressor("default", "Converting soil polygon layers to raster...")

    for gdb in gdbList:
        # gdb could be a geodatabase or an mupolygon featureclass
        arcpy.SetProgressorLabel("Creating map unit raster for " + gdb)

        PrintMsg(" \n" + (65 * "*"), 0)
        PrintMsg("Processing " + gdb, 0)
        PrintMsg(" \n" + (65 * "*"), 0)
        bRaster = SSURGO_ExportMuRaster.ConvertToRaster(gdb,"MUPOLYGON", iRaster, bTiled)

    theMsg = " \nTotal processing time for " + str(len(gdbList)) + " rasters: " + elapsedTime(start) + " \n "
    PrintMsg(theMsg, 0)

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()


