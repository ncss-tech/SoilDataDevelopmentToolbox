# gSSURGO_Tolerances.py
#
# Script to alter XYResolution and XYTolerance in gSSURGO template databases
# 2019-10-18 Steve Peaslee

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
import os, sys, locale, traceback
from arcpy import env

gdb = arcpy.GetParameterAsText(0)  # input gSSURGO database

try:
    env.workspace = gdb

    # List of featureclasses to process
    fcList = ["SAPOLYGON", "MUPOLYGON", "MULINE", "MUPOINT", "FEATLINE", "FEATPOINT"]

    PrintMsg(" \nUpdating featureclass tolerances using Degrees", 0)
    env.XYResolution = "0.000000001 Degrees"
    env.XYTolerance =  "0.00000001 Degrees"
    #env.XYResolution = "0.001 Meters"
    #env.XYTolerance =  "0.01 Meters"

    for fc in fcList:
        PrintMsg(" \nUpdating tolerances for " + fc, 0)
        tmpFC = fc + "2"
        arcpy.CopyFeatures_management(fc, tmpFC)
        arcpy.Delete_management(fc)
        arcpy.Rename_management(tmpFC, fc)
    
    PrintMsg(" \nFinished updating " + gdb, 0)

except:
    errorMsg()
