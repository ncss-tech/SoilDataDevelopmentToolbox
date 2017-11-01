# CompareMapLegend_Domain.py
#
# Purpose is to compare the Values in maplegendxml with domain values and flag any discrepancies
# 2017-03-09
# Steve Peaslee


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
def GetRatingDomain(gdb):
    # return list of tiebreak domain values for rating
    # modify this function to use uppercase string version of values
    #
    # The tiebreak domain name is not always used, even when there is a set
    # of domain names for the attribute (eg Conservation Tree and Shrub Group)

    try:

        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        mdcols = os.path.join(gdb, "mdstatdomdet")
        domainName = dSDV["tiebreakdomainname"]
        #PrintMsg(" \ndomainName: " + str(domainName), 1)
        domainValues = list()

        if dSDV["tiebreakdomainname"] is not None:
            wc = "domainname = '" + dSDV["tiebreakdomainname"] + "'"

            sc = (None, "ORDER BY choicesequence ASC")

            with arcpy.da.SearchCursor(mdcols, ["choice", "choicesequence"], where_clause=wc, sql_clause=sc) as cur:
                for rec in cur:
                    domainValues.append(rec[0])

        elif bVerbose:
            PrintMsg(" \n" + sdvAtt + ": no domain choices found", 1)

        return domainValues

    except:
        errorMsg()
        return []

## ===================================================================================
def GetSDVAtts(gdb, sdvAtt, aggMethod):
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    try:
        # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        sql1 = "attributename = '" + sdvAtt + "'"

        if bVerbose:
            PrintMsg(" \nReading sdvattribute table into dSDV dictionary", 1)

        with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
            rec = cur.next()  # just reading first record
            i = 0
            for val in rec:
                dSDV[flds[i].lower()] = val
                # PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                i += 1


        return dSDV

    except:
        errorMsg()
        return dSDV

## ===================================================================================
def GetMapLegend(dSDV):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    try:
        #bVerbose = False  # This function seems to work well, but prints a lot of messages.

        arcpy.SetProgressorLabel("Getting map legend information")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        xmlString = dSDV["maplegendxml"]

        if bVerbose:
            PrintMsg(" \n" + xmlString + " \n ", 1)

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        # Iterate through XML tree, finding required elements...
        i = 0
        dLegend = dict()
        dLabels = dict()
        dColors = dict()
        valueList = list()

        #dLegendElements = dict()
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

                if dSDV["attributelogicaldatatype"].lower() == "integer":
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

                elif dSDV["attributelogicaldatatype"].lower() == "float" and not bFuzzy:
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

        # Test iteration methods on dLegend
        #PrintMsg(" \n" + dSDV["attributename"] + " Legend Key: " + dLegend["maplegendkey"] + ", Type: " + dLegend["type"] + ", Name: " + dLegend["name"] , 1)

        if bVerbose:
            PrintMsg(" \n" + dSDV["attributename"] + " Legend Key: " + dLegend["maplegendkey"] + ", Type: " + dLegend["type"] + ", Name: " + dLegend["name"] , 1)

            for order, vals in dLabels.items():
                PrintMsg("\tNew " + str(order) + ": ", 1)

                for key, val in vals.items():
                    PrintMsg("\t\t" + key + ": " + str(val), 1)

                try:
                    r = int(dColors[order]["red"])
                    g = int(dColors[order]["green"])
                    b = int(dColors[order]["blue"])
                    rgb = (r,g,b)
                    #PrintMsg("\t\tRGB: " + str(rgb), 1)

                except:
                    pass



        for i in sorted(dLegend["labels"]):
            valueList.append(dLegend["labels"][i]["value"])

        if bVerbose:
            PrintMsg(" \ndLegend values: " + str(valueList), 1)

        return valueList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except:
        errorMsg()
        return []

## ===================================================================================
def RunComparison(sdvAtt, legendValues, domainValues):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    try:
        bProblem = False
        uppercaseLegend = [val.upper() for val in legendValues]
        uppercaseDomain = [val.upper() for val in domainValues]

        for val in legendValues:
            if not val in domainValues:
                if val.upper() in uppercaseDomain:
                    # case problem in legend
                    PrintMsg("Legend case problem for " + sdvAtt + ": '" + str(val) + "'", 0)

                else:
                    PrintMsg("Missing domain value for " + sdvAtt + ": '" + str(val) + "'", 0)

                bProblem = True

        for val in domainValues:
            if not val in legendValues:
                #PrintMsg("\tMissing legend value for " + sdvAtt + ": '" + str(val) + "'", 1)
                if not val.upper() in uppercaseLegend:
                    PrintMsg("Missing legend value for " + sdvAtt + ": '" + str(val) + "'", 0)
                #else:
                #    PrintMsg("\tMissing legend value for " + sdvAtt + ": '" + str(val) + "'", 1)
                bProblem = True

        if bProblem:
            PrintMsg(" \n" + sdvAtt + " domain values: " + ", ".join(domainValues), 1)
            PrintMsg(sdvAtt + " legend values: " + ", ".join(legendValues) + " \n ", 1)


        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time, operator, json
import xml.etree.cElementTree as ET

try:
    gdb = arcpy.GetParameterAsText(0)

    #global variables
    bVerbose = False
    #bFuzzy = False
    tieBreaker = "Lower"
    # Dictionary for aggregation method abbreviations
    #
    #dAgg = dict()
    #dAgg["Dominant Component"] = "DCP"
    #dAgg["Dominant Condition"] = "DCD"
    #dAgg["No Aggregation Necessary"] = ""
    #dAgg["Percent Present"] = "PP"
    #dAgg["Weighted Average"] = "WTA"
    #dAgg["Most Limiting"] = "ML"
    #dAgg["Least Limiting"] = "LL"



    # Begin by opening SDVATTRIBUTE table and getting ATTRIBUTENAMES for
    # all properties that have a TIEBREAKDOMAINNAME set.

    sdvattTable = os.path.join(gdb, "sdvattribute")

    wc = '"tiebreakdomainname" IS NOT NULL'
    fldNames = ['attributename']
    attList = list()

    with arcpy.da.SearchCursor(sdvattTable, fldNames, where_clause=wc) as cur:
        for rec in cur:
            attList.append(rec[0])

    PrintMsg(" \n", 0)

    if len(attList) > 0:
        for sdvAtt in attList:
            # Get sdvattribute information for this property
            #PrintMsg(" \nChecking attribute: '" + sdvAtt + "'", 1)
            dSDV = GetSDVAtts(gdb, sdvAtt, "Dominant Component")

            # Get map legend for this property
            legendValues = GetMapLegend(dSDV)

            # Get domain values from metdata tables
            domainValues = GetRatingDomain(gdb)

            # Compare legend values with domain values

            bCompared = RunComparison(sdvAtt, legendValues, domainValues)








except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()

