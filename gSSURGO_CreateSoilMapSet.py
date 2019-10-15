# gSSURGO_CreateSoilMapSet.py
#
# Creates a set of soil maps for horizon properties at multiple depth ranges.
# Uses mdstatrship* tables and sdvattribute table to populate menu
#
# 2017-07-27
#
# THINGS TO DO:
#
# Test the input MUPOLYGON featurelayer to see how many polygons are selected when compared
# to the total in the source featureclass. If there is a significant difference, consider
# applying a query filter using AREASYMBOL to limit the size of the master query table.
#
#
#
# 1.  Aggregation method "Weighted Average" can now be used for non-class soil interpretations.
#
#
# 2.   "Minimum or Maximum" and its use is now restricted to numeric attributes or attributes
#   with a corresponding domain that is logically ordered.
#
# 3.  Aggregation method "Absence/Presence" was replaced with a more generalized version
# thereof, which is referred to as "Percent Present".  Up to now, aggregation method
# "Absence/Presence" was supported for one and only one attribute, component.hydricrating.
# Percent Present is a powerful new aggregation method that opens up a lot of new possibilities,
# e.g. "bedrock within two feel of the surface".
#
# 4.  The merged aggregation engine now supports two different kinds of horizon aggregation,
# "weighted average" and "weighted sum".  For the vast majority of horizon level attributes,
# "weighted average" is used.  At the current time, the only case where "weighted sum" is used is
# for Available Water Capacity, where the water holding capacity needs to be summed rather than
# averaged.

# 5.  The aggregation process now always returns two values, rather than one, the original
# aggregated result AND the percent of the map unit that shares that rating.  For example, for
# the drainage class/dominant condition example below, the rating would be "Moderately well
# drained" and the corresponding map unit percent would be 60:
#
# 6.  A horizon or layer where the attribute being aggregated is null will now never contribute
# to the final aggregated result.  There # was a case for the second version of the aggregation
# engine where this was not true.
#
# 7.  Column sdvattribute.fetchallcompsflag is no longer needed.  The new aggregation engine was
# updated to know that it needs to # include all components whenever no component percent cutoff
# is specified and the aggregation method is "Least Limiting" or "Most # Limiting" or "Minimum or Maximum".
#
# 8.  For aggregation methods "Least Limiting" and "Most Limiting", the rating will be set to "Unknown"
# if any component has a null # rating, and no component has a fully conclusive rating (0 or 1), depending
# on the type of rule (limitation or suitability) and the # corresponding aggregation method.
#

# 2015-12-17 Depth to Water Table: [Minimum or Maximum / Lower] is not swapping out NULL values for 201.
# The other aggregation methods appear to be working properly. So the minimum is returning mostly NULL
# values for the map layer when it should return 201's.

# 2015-12-17 For Most Limiting, I'm getting some questionable results. For example 'Somewhat limited'
# may get changed to 'Not rated'

# Looking at option to map fuzzy rating for all interps. This would require redirection to the
# Aggregate2_NCCPI amd CreateNumericLayer functions. Have this working, but needs more testing.
#
# 2015-12-23  Need to look more closely at my Tiebreak implementation for Interps. 'Dwellings with
# Basements (DCD, Higher) appears to be switched. Look at Delaware 'PsA' mapunit with Pepperbox-Rosedale components
# at 45% each.
#
# 2016-03-23 Fixed bad bug, skipping last mapunit in NCCPI and one other function
#
# 2016-04-19 bNulls parameter. Need to look at inclusion/exclusion of NULL rating values for Text or Choice.
# WSS seems to include NULL values for ratings such as Hydrologic Group and Flooding
#
# Interpretation columns
# interphr is the High fuzzy value, interphrc is the High rating class
# interplr is the Low fuzzy value, interplrc is the Low rating class
# Very Limited = 1.0; Somewhat limited = 0.22
#
# NCCPI maps fuzzy values by default. It appears that 1.0 would be high productivity and
# 0.01 very low productivity. Null would be Not rated.
#
# 2017-03-03 AggregateHZ_DCP_WTA - Bug fix. Was only returning surface rating for DCP. Need to let folks know about this.
#
# 2017-07-24 Depth to Water Table, DCP bug involving nullreplacementvalue and tiebreak code.
#
# 2017-08-11 Mapping interpretations using Cointerp  very slow on CONUS gSSURGO
#
# 2017-08-14 Altered Unique values legend code to skip the map symbology section for very large layers
#
# 2018-06-30 Addressed issue with some Raster maps-classified had color ramp set backwards. Added new logic and layer files.


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
        PrintMsg("Unhandled error in attFld method", 2)
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

        return "???"

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
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale,  operator, json, math, random, time
import xml.etree.cElementTree as ET
#from datetime import datetime

# Create the environment
from arcpy import env

try:
    if __name__ == "__main__":
        inputLayer = arcpy.GetParameterAsText(0)      # Input mapunit polygon layer
        sdvFolder = arcpy.GetParameter(1)             # SDV Folder
        sdvAtt = arcpy.GetParameter(2)                # SDV Attribute
        aggMethod = arcpy.GetParameter(3)             # Aggregation method
        primCst = arcpy.GetParameter(4)               # Primary Constraint choice list
        secCst = arcpy.GetParameter(5)                # Secondary Constraint choice list
        ranges = arcpy.GetParameterAsText(6)          # string containing list of depth ranges
        NA = arcpy.GetParameter(7)                    # bottom horizon depth             CHANGE THIS
        begMo = arcpy.GetParameter(8)                 # beginning month
        endMo = arcpy.GetParameter(9)                 # ending month
        tieBreaker = arcpy.GetParameter(10)           # tie-breaker setting
        #bZero = arcpy.GetParameter(11)                # treat null values as zero
        #cutOff = arcpy.GetParameter(12)               # minimum component percent cutoff (integer)
        #bFuzzy = arcpy.GetParameter(13)               # Map fuzzy values for interps
        #bNulls = arcpy.GetParameter(14)               # Include NULL values in rating summary or weighting (default=True)
        #sRV = arcpy.GetParameter(15)                  # flag to switch from standard RV attributes to low or high


        cutOff = None
        bFuzzy = False
        bNulls = True
        sRV = "Representative"

        import gSSURGO_CreateSoilMap
        
        rangeList = [int(v) for v in ranges.split(",")] # first item is lowest value, last item is highest value
        rangeList.sort(reverse=True)
        #PrintMsg(" \n" + str(rangeList), 1)

        for i in range(len(rangeList) - 1):
            top = rangeList[i + 1]
            bot = rangeList[i]

            msg = "Creating map number " + str(i + 1) + ":  " + sdvAtt + " " + str(top) + " to " + str(bot) + "cm"
            PrintMsg(" \n" + msg, 0)
            arcpy.SetProgressorLabel(msg)

            # Trying here to enter default values for most parameters and to modify CreateSoilMap.CreateSoilMap to use default aggregation method (aggMethod) when it is passed an empty string
            bSoilMap = gSSURGO_CreateSoilMap.CreateSoilMap(inputLayer, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV) # external script
            #arcpy.SetProgressorPosition()
            
            if bSoilMap == 2:
                badList.append(sdvAtt)

            elif bSoilMap == 0:
                #PrintMsg("\tbSoilMap returned 0", 0)
                badList.append(sdvAtt)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    PrintMsg(" \nFinal error gSSURGO_CreateSoilMap", 0)
    errorMsg()

