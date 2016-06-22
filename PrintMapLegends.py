# PrintMapLegends.py
#
# Reads sdvattribute table and prints legend information for interpretations



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
def GetMapLegend(sdvrec, cnt):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    try:
        #arcpy.SetProgressorLabel("Getting map legend information")
        bVerbose = True

        attributekey, attributename, attributetablename, attributelogicaldatatype, attributetype, resultcolumnname, maplegendkey, maplegendxml, effectivelogicaldatatype = sdvrec

        # Convert XML to tree format
        tree = ET.fromstring(maplegendxml)

        # Iterate through XML tree, finding required elements...
        i = 0
        dLegend = dict()
        dLabels = dict()
        dColors = dict()
        #dLegendElements = dict()
        legendList = list()
        legendKey = ""
        legendType = ""
        legendName = ""
        valueList = list()

        # Notes: dictionary items will vary according to legend type
        # Looks like order should be dictionary key for at least the labels section

        for rec in tree.iter():

            if rec.tag == "Map_Legend":
                dLegend["maplegendkey"] = rec.attrib["maplegendkey"]

            if rec.tag == "ColorRampType":
                dLegend["type"] = rec.attrib["type"]
                dLegend["name"] = rec.attrib["name"]

            if rec.tag == "Labels":
                order = int(rec.attrib["order"])

                if attributelogicaldatatype.lower() == "integer":
                    # get dictionary values and convert values to integer
                    try:
                        val = int(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = int(rec.attrib["upper_value"])
                        lowerVal = int(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                elif attributelogicaldatatype.lower() == "float":
                    # get dictionary values and convert values to float
                    try:
                        val = float(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = float(rec.attrib["upper_value"])
                        lowerVal = float(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                else:
                    dLabels[order] = rec.attrib   # for each label, save dictionary of values

            if rec.tag == "Color":
                # Save RGB Colors for each legend item

                # get dictionary values and convert values to integer
                red = int(rec.attrib["red"])
                green = int(rec.attrib["green"])
                blue = int(rec.attrib["blue"])
                dColors[order] = rec.attrib

            if rec.tag == "Legend_Elements":
                try:
                    dLegend["classes"] = rec.attrib["classes"]   # save number of classes (also is a dSDV value)

                except:
                    pass


        # Add the labels dictionary to the legend dictionary
        dLegend["labels"] = dLabels
        dLegend["colors"] = dColors

        if bVerbose:

            for order, vals in dLabels.items():

                for key, val in vals.items():
                    #PrintMsg("\t" + key + ": " + str(val), 1)
                    if key == "value":
                        valueList.append(str(val))

                try:
                    r = int(dColors[order]["red"])
                    g = int(dColors[order]["green"])
                    b = int(dColors[order]["blue"])
                    rgb = (r,g,b)
                    #PrintMsg("\tRGB: " + str(rgb), 1)

                except:
                    pass

            #if len(valueList) > 0:
            PrintMsg(str(cnt) + "|" + attributetype + "|" + attributename + "|" + dLegend["maplegendkey"] + "|" + dLegend["type"] + "|" + dLegend["name"]  + "|" + ", ".join(valueList), 1)

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)

    except:
        errorMsg()

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time
import xml.etree.cElementTree as ET

# Create the environment
from arcpy import env

try:
    inputTbl = arcpy.GetParameterAsText(0)      # Input mapunit polygon layer

    fieldNames = ['attributekey', 'attributename', 'attributetablename', 'attributelogicaldatatype', 'attributetype', 'resultcolumnname', 'maplegendkey', 'maplegendxml', 'effectivelogicaldatatype']

    wc = "attributetype = 'Interpretation'"
    wc = None
    sql = (None, "ORDER BY maplegendkey ASC, attributename ASC")

    cnt = 0
    outputFields = ['row', 'attributetype', 'attributename', 'maplegendkey', 'legendtype', 'legendname', 'legendvalues']
    PrintMsg(" \n"+ "|".join(outputFields), 0)

    with arcpy.da.SearchCursor(inputTbl, fieldNames, where_clause=wc, sql_clause=sql) as cur:
        for rec in cur:
            cnt += 1
            #PrintMsg(" \n" + attributename, 0)
            GetMapLegend(rec, cnt)

    PrintMsg(" \n", 0)


except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()