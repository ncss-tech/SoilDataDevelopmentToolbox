## Read map legend info for all properties and interpretations in the sdvattribute table
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
        PrintMsg("Unhandled error", 2)
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
def GetMapLegend(xmlString, attributelogicaldatatype):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    try:
        #bVerbose = False  # This function seems to work well, but prints a lot of messages.
        dLegend = dict()
        dLabels = dict()
        arcpy.SetProgressorLabel("Getting map legend information")

        # xmlString = dAtts["maplegendxml"]

        #PrintMsg(" \n" + xmlString + " \n ", 1)

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        # Iterate through XML tree, finding required elements...
        i = 0
        dColors = dict()
        legendList = list()
        legendKey = ""
        legendType = ""
        legendName = ""

        # Notes: dictionary items will vary according to legend type
        # Looks like order should be dictionary key for at least the labels section
        #
        for rec in tree.iter():

            if rec.tag == "Map_Legend":
                dLegend["maplegendkey"] = rec.attrib["maplegendkey"]

            if rec.tag == "ColorRampType":
                dLegend["type"] = rec.attrib["type"]
                dLegend["name"] = rec.attrib["name"]

                if rec.attrib["name"] == "Progressive":
                    dLegend["count"] = int(rec.attrib["count"])

            if "name" in dLegend and dLegend["name"] == "Progressive":

                if rec.tag == "LowerColor":
                    # 'part' is zero-based and related to count
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Lower Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)

                if rec.tag == "UpperColor":
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Upper Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)


            if rec.tag == "Labels":
                order = int(rec.attrib["order"])

                if attributelogicaldatatype.lower() == "integer":
                    # get dictionary values and convert values to integer
                    try:
                        val = int(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        #rec.attrib["label"] = label
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = int(rec.attrib["upper_value"])
                        lowerVal = int(rec.attrib["lower_value"])
                        #label = rec.attrib["label"]
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                elif attributelogicaldatatype.lower() == "float":
                    # get dictionary values and convert values to float
                    try:
                        val = float(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        #rec.attrib["label"] = label
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = float(rec.attrib["upper_value"])
                        lowerVal = float(rec.attrib["lower_value"])
                        #label = rec.attrib["label"]
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

        return dLegend

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
import os, sys, traceback, locale, arcpy
import xml.etree.cElementTree as ET

try:
    if __name__ == "__main__":
        sdvTbl = arcpy.GetParameterAsText(0)
        sdvAtt = arcpy.GetParameterAsText(1)  # optional 'attributename' value

        # Set up
        #
        fieldNames = ["attributename", "maplegendkey", "maplegendclasses", "maplegendxml", "effectivelogicaldatatype", "attributelogicaldatatype", "maplegendxml"]

        if sdvAtt == "":
            whereClause = ""

        else:
            whereClause = "attributename = '" + str(sdvAtt) + "'"
            
        dMapLegendInfo = dict()
        dClassInfo = dict()
        dXML = dict()

        with arcpy.da.SearchCursor(sdvTbl, fieldNames, where_clause=whereClause) as cur:
            for rec in cur:
                # All values are returned as string
                attributename, maplegendkey, maplegendclasses, maplegendxml, effectivelogicaldatatype, attributelogicaldatatype, maplegendxml = rec
                #PrintMsg(" \n" + attributename, 0)
                dMapLegendInfo[attributename] = GetMapLegend(maplegendxml, attributelogicaldatatype)
                dClassInfo[attributename] = maplegendclasses
                dXML[attributename] = maplegendxml

        hdr = "attributename|maplegendname|maplegendtype|maplegendkey|maplegendclass|maplegendxml"
        PrintMsg(" \n" + hdr, 0)

        attributeList = sorted(dMapLegendInfo.keys())
        
        for attributename in attributeList:
            val = dMapLegendInfo[attributename]
            sName = val["name"]
            sType = val["type"]
            sMapLegendKey = val["maplegendkey"]
            maplegendclass = dClassInfo[attributename]
            maplegendxml = dXML[attributename].replace("\r", "")
            
            PrintMsg(attributename + "|" + sName + "|" + sType + "|" + sMapLegendKey + "|" + str(maplegendclass) + "|" + " ".join(maplegendxml.split("\n")), 1)

        PrintMsg(" \nFinished \n ", 0)

except:
    errorMsg()
    
