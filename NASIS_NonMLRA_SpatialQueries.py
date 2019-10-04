# NASIS_NonMLRA_SpatialQueries.py
#
# ArcGIS 10.1
#
# Steve Peaslee, August 02, 2011
#
# Generates (using Soil Data Access), a set of queries that can be used in
# NASIS to create a local database or selected set for non-MLRA soil survey areas.
# The number of survey areas in each query are limited to prevent failures in NASIS.
#
# This script uses a local SAPOLYGON featurelayer and Soil Data Access to generate
# the queries, so it will NOT work with new surveys that do not have a matching areasymbol in WSS.

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    # Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
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
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, time
import subprocess
from arcpy import env

# Create the Geoprocessor object
try:

    surveyBoundary = arcpy.GetParameter(0)          # not being used by script
    areaValues = arcpy.GetParameter(1)              # list of areasymbols and areanames
    maxAreas = arcpy.GetParameter(2)                # number of areasymbols for each query string
    outputFile = arcpy.GetParameterAsText(3)        # optional output text file to write queries to. Popup.

    queryList = list()
    masterList = list()

    PrintMsg(" \nProcessing " + Number_Format(len(areaValues), 0, True) + " survey areas \n ", 0)

    # Get areasymbol from 2nd parameter and chunk it up into individual queries for NASIS
    for areaVals in areaValues:
        #PrintMsg("\t" + str(areaVals), 1)
        vals = areaVals.split(",")
        areasymbol = vals[0].encode('ascii')
        #areaname = ", ".join(vals[1:])
        #PrintMsg("\t" + str(areasymbol), 1)

        if len(queryList) == maxAreas:
            masterList.append(queryList)
            queryList = [areasymbol]

        else:
            queryList.append(areasymbol)

    #PrintMsg(" \nLast queryList: " + str(queryList), 1)
    if len(queryList) > 0:
        masterList.append(queryList)
    
    cnt = 0

    if outputFile != "":
        fh = open(outputFile, "w")
    
    for query in masterList:
        cnt += 1
        
        if len(query) > 1:
            sQuery = ", ".join(query)

        elif len(query) == 1:
            sQuery = query[0]

        rec = sQuery + "     " + "QuerySSURGO_" + str(cnt)
        PrintMsg(rec, 0)
        
        if outputFile != "":
            fh.write(rec + "\n")

        # end of tile for loop

    if outputFile != "":
        fh.close()

        if arcpy.Exists(outputFile):
            PrintMsg(" \nOpening output query file " + outputFile, 0)
            subprocess.Popen(["notepad", outputFile])
        
    PrintMsg(" \nFinished queries \n ", 0)

except MyError, err:
    PrintMsg(str(err), 2)

except:
    errorMsg()
