# gSSURGO_UpdateLayerFile.py
#
# Saves user changes to layer properties to the original layer file. Only works with last gSSURGO map layers
# created by 'Map Soil Properties and Interpretations.
#
# 2016-03-27

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
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time

# Create the environment
from arcpy import env

try:
    inputLayers = arcpy.GetParameter(0)      # Input mapunit polygon laye

    env.overwriteOutput = True

    folderList = list()

    for inputLayer in inputLayers:
        # Get target gSSURGO database
        muDesc = arcpy.Describe(inputLayer)
        catalogPath = muDesc.catalogPath                         # full path for input mapunit polygon layer
        gdb = os.path.dirname(catalogPath)                       # need to expand to handle featuredatasets
        folder = os.path.dirname(gdb)

        if not folder in folderList:
            folderList.append(folder)

        # Overwrite original
        outputLayerFile = os.path.join(os.path.dirname(gdb), os.path.basename(inputLayer.replace(", ", "_").replace(" ", "_")) + ".lyr")
        arcpy.SaveToLayerFile_management(inputLayer, outputLayerFile)
        PrintMsg(" \n\tUpdated layer file for '" + inputLayer + "'", 0)

    if len(folderList) == 0:
        raise MyError, "No layer files updated \n "

    elif len(folderList) == 1:
        PrintMsg(" \nLayer files are located under the '" + folderList[0] + "' folder \n ", 0)

    else:
        PrintMsg(" \nLayer files are located under the '" + "', '".join(folderList) + "' folders \n ")


except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
