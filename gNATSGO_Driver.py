# gNATSGO_Driver.py
#
# Runs STATSGO_MergeDatabases.py in batch mode
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
                arcpy.AddError(" \n" + string)

    except:
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    try:
    # Format a number according to locality and given places
        locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"


## ===================================================================================
## main

import arcpy, sys, string, os, traceback, locale


try:

    stList = arcpy.GetParameter(2)
    gssurgoFolder = arcpy.GetParameterAsText(3)
    statsgoDB = arcpy.GetParameterAsText(4)
    statsgoPolygons = arcpy.GetParameterAsText(5)
    gnatsgoFolder = arcpy.GetParameterAsText(6)

    inputRaster = "MapunitRaster_10m"  # assuming same 10 meter raster will be used for each gSSURGO database
    
    import STATSGO_MergeDatabases

    PrintMsg(" \nChecking input parameter stList: " + str(stList), 1)
             
    for st in stList:
        PrintMsg(" \nMerging gSSURGO and STATSGO for: " + st, 0)
    
        #inputLayer = r"Z:\Soil_Scientists\Peaslee_Share\Geodata\FY2020\gSSURGO_States_FY2020\gSSURGO_" + st + ".gdb\MUPOLYGON"
        #newGDB = r"Z:\Soil_Scientists\Peaslee_Share\Geodata\FY2020\gNATSGO\Test\gNATSGO_" + st + ".gdb"

        # muPolygons = gSSURGO MUPOLYGON featureclass
        # muRaster = gSSURGO MapunitRaster_10m
        # statsgoDB = STATSGO attribute database
        # statsgoPolygons = STATSGO soil polygon featureclass
        # gnatsgoDB = new gNATSGO database full path

        gssurgoDB = os.path.join(gssurgoFolder, "gSSURGO_" + st + ".gdb")
        muPolygons = os.path.join(gssurgoDB, "MUPOLYGON")
        muRaster = os.path.join(gssurgoDB, "MapunitRaster_10m")
        gnatsgoDB = os.path.join(gnatsgoFolder, "gNATSGO_" + st + ".gdb")
        
        bMerged = STATSGO_MergeDatabases.ProcessData(muPolygons, muRaster, statsgoDB, statsgoPolygons, gnatsgoDB)

        if not bMerged:
            raise MyError, "Failed to merge gSSURGO and STATSGO for " + st


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)


except:
    errorMsg()
