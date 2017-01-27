# GetRGB.py
#
# light blue for cold (low magnitude) all the way to yellow for hot (high magnitude).
#
# Three arguments:
# mag = arcpy.GetParameter(0)     # rating value within the range of cmin and cmax
# cmin = arcpy.GetParameter(1)    # minimum rating value
# cmax = arcpy.GetParameter(2)    # maximum rating value

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #print msg
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
        PrintMsg("Unhandled error in unHandledException method", 2)
        pass

## ===================================================================================
def GetFloatRgb(mag, cmin, cmax):
    # light blue for cold (low magnitude) all the way to yellow for hot (high magnitude).
    #
    # Return a tuple of floats between 0 and 1 for R, G, and B. """
    # Normalize to 0-1
    try: x = float(mag-cmin)/(cmax-cmin)
    except ZeroDivisionError: x = 0.5 # cmax == cmin
    blue  = min((max((4*(0.75-x), 0.)), 1.))
    red   = min((max((4*(x-0.25), 0.)), 1.))
    green = min((max((4*math.fabs(x-0.5)-1., 0.)), 1.))
    return red, green, blue

## ===================================================================================
def GetRGB(mag, cmin, cmax):
    # Convert floating point RGB to integer (0-255)
    #
    red, green, blue = GetFloatRgb(mag, cmin, cmax)
    return int(red*255), int(green*255), int(blue*255)

## ===================================================================================
def GetStrRGB(mag, cmin, cmax):
    # Convert integer RGB (R,G,B) to HEX
    return "#%02x%02x%02x".upper() % GetRGB(mag, cmin, cmax)
    #return hexCode.upper()

## ===================================================================================
## ===================================================================================
#
# light blue for cold (low magnitude) all the way to yellow for hot (high magnitude).
#
import sys, string, os, locale, arcpy, traceback, math

mag = arcpy.GetParameter(0)      # a single rating value within the range of cmin and cmax
#cmin = arcpy.GetParameter(1)    # minimum rating value
#cmax = arcpy.GetParameter(2)    # maximum rating value
#
# need to change this to input a limited list of integer values and output an ordered list of hexcodes.
# would be nice to allow type of color ramp to be another input parameter.

try:

    # Ignore magnitude and try running in a loop in the range of values defined by mag

    #for mag in range(cmin, cmax):
    cmin = min(range(mag + 1))
    cmax = max(range(mag + 1))



    #for mag in range(cmin, cmax):
    for i in range(cmin, cmax):

        rgbVal = GetRGB(i, cmin, cmax)

        #PrintMsg(" \nRGB Color " + str(mag) + " : " + str(rgb), 0)

        hexVal = GetStrRGB(i, cmin, cmax)

        PrintMsg(" \nColor " + str(i + 1) + " : " + hexVal + ", " + str(rgbVal), 1)

    PrintMsg(" \n", 0)

except:
    errorMsg()


