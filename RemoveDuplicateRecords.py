# RemoveDuplicateRecords.py
#
# Steve Peaslee August 02, 2011
#
# Creates hard-coded table relationshipclasses in a geodatabase. If SSURGO featureclasses
# are present, featureclass to table relationshipclasses will also be built. All
# tables must be registered and have OBJECTID fields. Geodatabase must have been created
# using ArcGIS 9.2 or ArcGIS 9.3. Saving back to a 9.2 version from ArcGIS 10 also seems to
# work. Not so for saving back as 9.3 version (bug?)
#
# Also sets table and field aliases using the metadata tables in the output geodatabase.
#
# Tried to fix problem where empty MUPOINT featureclass is identified as Polygon



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
        PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

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
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, arcpy, traceback, math, time
from arcpy import env

try:
    if __name__ == "__main__":
        # Create geoprocessor object
        #gp = arcgisscripting.create(9.3)
        #arcpy.OverwriteOutput = 1

        scriptname = sys.argv[0]
        inputTable = arcpy.GetParameterAsText(0)   # input geodatabase containing SSURGO tables and featureclasses
        keyFields = arcpy.GetParameterAsText(1)   # overwrite option independant of gp environment setting

        PrintMsg(" \nRemoving duplicate records from " + inputTable, 0)
        fields = list()
        
        for fld in keyFields.split(";"):
            PrintMsg("\t" + fld, 1)
            fields.append(fld)

        valList = list()
        delCnt = 0

        with arcpy.da.UpdateCursor(inputTable, fields) as cur:

            if len(fields) == 1:
                for rec in cur:
                    val = str(rec[0])

                    if not val in valList:
                        valList.append(val)
                        PrintMsg("\t" + val, 0)

                    else:
                        cur.deleteRow()
                        delCnt += 1

            elif len(fields) > 1:
                for rec in cur:
                    vals = [str(val) for val in rec]
                    key = ":".join(vals)
                    

                    if not key in valList:
                        valList.append(key)
                        PrintMsg("\t" + ", ".join(vals), 0)

                    else:
                        cur.deleteRow()
                        delCnt += 1
                
          
        PrintMsg(" \nFinished removing " + Number_Format(delCnt, 0, True) + " duplicate records from table \n ", 0)
        
except:
    errorMsg()
