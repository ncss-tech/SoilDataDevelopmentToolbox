# MapRotateNorth.py
# Rotate map display frame north
# Steve Peaslee 2018-02-10

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
        PrintMsg("Unhandled error in unHandledException method", 2)
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
def OffsetAngle(a, b, c):
    # Given 3 points [x, y, z], calculate the angle formed
    # Create vectors from points
    # Each point is a list [x, y, z]
    #
    try:
        angle = 0
        
        ba = [ aa-bb for aa,bb in zip(a,b) ]
        bc = [ cc-bb for cc,bb in zip(c,b) ]

        # Normalize vector
        nba = math.sqrt ( sum ( (x**2.0 for x in ba) ) )
        ba = [ x/nba for x in ba ]

        nbc = math.sqrt ( sum ( (x**2.0 for x in bc) ) )
        bc = [ x/nbc for x in bc ]

        # Calculate scalar from normalized vectors
        scale = sum ( (aa*bb for aa,bb in zip(ba,bc)) )

        # calculate the angle in radian
        radians = math.acos(scale)

        # Get the sign
        if (c[0] - a[0]) == 0:
            s = 0

        else:
            s = ( c[0] - a[0] ) / abs(c[0] - a[0]) 

        angle = s * ( -1.0 * round(math.degrees(radians), 1) )

        return angle

        # A-----C
        # |    /
        # |   /
        # |  /
        # | /
        # |/
        # B

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return angle

    except:
        errorMsg()
        return angle
    
## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, os, math, traceback
from arcpy import env

try:
    mxd = arcpy.mapping.MapDocument("CURRENT")

except:
    PrintMsg(" \nUnable to get handle on current map", 2)

try:
    df = mxd.activeDataFrame
    dfSR = df.spatialReference
    rotation = df.rotation
    extent = df.extent # XMin...

    # Calculate center of display
    xCntr = ( extent.XMin + extent.XMax ) / 2.0
    yCntr = ( extent.YMin + extent.YMax ) / 2.0
    dfPoint1 = arcpy.Point(xCntr, yCntr)
    pointGeometry = arcpy.PointGeometry(dfPoint1, dfSR)

    # Create same point but as Geographic WGS1984
    # Designed to handle dataframe coordinate system datums: NAD1983 or WGS1984.
    # 
    outputSR = arcpy.SpatialReference(4326)        # GCS WGS 1984
    env.geographicTransformations = "WGS_1984_(ITRF00)_To_NAD_1983"
    pointGM = pointGeometry.projectAs(outputSR, "")
    pointGM1 = pointGM.firstPoint
    
    wgsX1 = pointGM1.X
    wgsY2 = pointGM1.Y + 1.0
    offsetPoint = arcpy.Point(wgsX1, wgsY2)


    # Project north offset back to dataframe coordinate system
    offsetGM = arcpy.PointGeometry(offsetPoint, outputSR)

    dfOffset = offsetGM.projectAs(dfSR, "")
    dfPoint2 = dfOffset.firstPoint
    A = [dfPoint2.X, dfPoint2.Y, 0.0]

    B = [xCntr, yCntr, 0.0]

    C = [xCntr, (yCntr + 1000.0), 0.0]

    angle = OffsetAngle(A, B, C)
    
    PrintMsg(" \nOffset Angle: " + str(angle) + " degrees \n ", 0)

    df.rotation = angle
    arcpy.RefreshActiveView()
    
    

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
