# SDA_FixSelfInsersections.py
#
# Purpose: Remove self-intersecting points from AOI polygons so that they will
# be valid for Soil Data Access (SQL Server)
#
# ArcGIS 10.3
#
# Steve Peaslee, USDA-NRCS, National Soil Survey Center
#
# Adapted from CommonPoints script.
#
class MyError(Exception):
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
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + " \n" + str(sys.exc_type)+ ": " + str(sys.exc_value)
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in errorMsg method", 2)
        pass

## ===================================================================================
def Number_Format(num, places=0, bCommas=True):
    # Format a number according to locality and given places
    import locale

    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8') #use locale.format for commafication

    except locale.Error:
        locale.setlocale(locale.LC_ALL, '') #set to default locale (works on windows)

    try:

        import locale


        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)

        return theNumber

    except:
        PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def RemoveIntersections(inLayer, outputFC):

    # Given a polygon layer, look for self-intersections and remove

    try:
        dDups = dict()

        iSelection = int(arcpy.GetCount_management(inLayer).getOutput(0))

        # define output featureclass
        #desc = arcpy.Describe(inLayer)
        #dt = desc.dataType.upper()
        #sr = desc.spatialReference
        #env.workspace = os.path.dirname(desc.catalogPath)

        # input layer needs to be a featurelayer. If it is a featureclass, do a switch.
        #if dt == "FEATURECLASS":
            # swap out the input featureclass for a new featurelayer based upon that featureclass
        #    inLayer = desc.name + " Layer"
        #    PrintMsg(" \nCreating new featurelayer named: " + inLayer, 0)
        #    inputFC = desc.catalogPath
        #    arcpy.MakeFeatureLayer_management(inputFC, inLayer)

        #elif dt == "FEATURELAYER":
        #    inputName = desc.Name
        #    inputFC = desc.FeatureClass.catalogPath


        # Process records using a series of search cursors while tracking progress
        arcpy.SetProgressorLabel("Reading polygon geometry...")
        arcpy.SetProgressor("step", "Reading polygon geometry...",  0, iSelection, 1)
        PrintMsg(" \nProcessing " + Number_Format(iSelection, 0, True) + " polygons in '" + inLayer + "'", 0)

        iCnt = 0

        flds = ["OID@","SHAPE@"]

        with arcpy.da.SearchCursor(inLayer, flds) as cursor:
            for row in cursor:
                arcpy.SetProgressorPosition()
                pntList = list()  # clear point list for the new polygon
                dupList = list()  # clear duplicate point list for the new polygon
                fid = row[0]

                for part in row[1]:
                    # look for duplicate points within each polygon part
                    #
                    bRing = True  # helps prevent from-node from being counted as a duplicate of to-node

                    for pnt in part:
                        if pnt:
                            if not bRing:
                                # add vertice or to-node coordinates to list
                                pntList.append((pnt.X,pnt.Y))

                            bRing = False

                        else:
                            # interior ring encountered
                            ring = pntList.pop()  # removes first node from list
                            bRing = True  # prevents island from-node from being identified as a duplicate of the to-node

                # get duplicate coordinate pairs within the list of vertices for the current attribute value
                dupList = [x for x, y in collections.Counter(pntList).items() if y > 1]

                if len(dupList) > 0:
                    dDups[fid] = dupList
                    iCnt += len(dupList)
                    PrintMsg(" \n\tFound common " + str(len(dupList)) + " self-intersecting points for polygon " + str(fid), 0)
                    arcpy.SetProgressorLabel("Reading polygon geometry ( flagged " + Number_Format(iCnt) + " locations )...")



        arcpy.ResetProgressor()  # completely finished reading all polygon geometry

        # if common-points were found, create a point shapefile containing the attribute value for each point
        #
        if len(dDups) > 0:
            PrintMsg(" \nTotal of " + Number_Format(iCnt, 0, True) + " 'common points' found in " + inLayer, 0)

            # create output points layer to store common-point locations
            pointsFC = os.path.join(env.scratchGDB, "QA_SelfIntersections")
            arcpy.CreateFeatureclass_management(os.path.dirname(pointsFC), os.path.basename(pointsFC), "POINT", "", "DISABLED", "DISABLED", sr)
            arcpy.AddField_management(pointsFC, "PolyID", "LONG")

            # Process records using cursor, track progress
            arcpy.SetProgressorLabel("Opening output featureclass...")
            arcpy.SetProgressor("step", "Writing point geometry..." , 0, iCnt, 1)

            # open new output points featureclass and add common point locations
            with arcpy.da.InsertCursor(pointsFC, ["SHAPE@XY", "PolyID"]) as cursor:
                # for each value that has a reported common-point, get the list of coordinates from
                # the dDups dictionary and write to the output Common_Points featureclass
                for val in dDups.keys():

                    for coords in dDups[val]:
                        cursor.insertRow([coords, val]) # write both geometry and the single attribute value to the output layer
                        arcpy.SetProgressorPosition()

            arcpy.ResetProgressor()
            arcpy.SetProgressorLabel("Process complete...")

            # Buffer points to create an Erase featureclass
            buffFC = os.path.join(env.scratchGDB, "QA_Buffer")
            arcpy.Buffer_analysis(pointsFC, buffFC, "0.25 Meters", "FULL", "ROUND", "ALL", "", "GEODESIC")

            # Erase the buffer points from the input AOI featureclass

            arcpy.Erase_analysis(inLayer, buffFC, outputFC, "0.10 Meters")

            return True

        else:
            PrintMsg(" \nNo common-point issues found with '" + inLayer + "' \n ", 0)
            return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## main
##

import os, sys, traceback, collections
import arcpy
from arcpy import env

try:

    # single polygon featurelayer as input parameter
    inLayer = arcpy.GetParameterAsText(0)



except MyError, e:
    # Example: raise MyError, "this is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

