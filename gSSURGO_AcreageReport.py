# gSSURGO_AcreageReport.py
#
# Calculate acres for a soil propery layer.
#
# Fixed acre conversion error 6-07-2016
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
def GetUser():

    try:
        # Get computer login and try to format
        #
        envUser = arcpy.GetSystemEnvironment("USERNAME")

        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = env.User.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser

        return userName

    except:
        errorMsg()

        return ""

## ===================================================================================
def GetSDVAtts(gdb, resultField):
    # return dictionary containing sdvattribute information
    try:
        # Open sdvattribute table and query for [resultcolumnname] = resultField
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]

        # resultField will probably have an '_DCP', '_DCD', '_WTA' or '_PP' appended
        resultField = resultField.split("_")[0]
        sql1 = "upper(resultcolumnname) = '" + resultField[:-4] + "'"

        try:
            # Assuming that last 4 characters in the field name have been altered to reflect aggregation method
            with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
                rec = cur.next()  # just reading first record
                i = 0
                for val in rec:
                    dSDV[flds[i].lower()] = val
                    # PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                    i += 1

        except:
            # Assuming that the cursor failed because the field name has not been altered (no aggregation neccessary)
            # Try again using the original field name
            sql1 = "upper(resultcolumnname) = '" + resultField + "'"

            with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
                rec = cur.next()  # just reading first record
                i = 0
                for val in rec:
                    dSDV[flds[i].lower()] = val
                    # PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                    i += 1


        # Revise some attributes to accomodate fuzzy number mapping code
        #
        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        if dSDV["attributetype"].lower() == "interpretation" and dSDV["nasisrulename"][0:5] == "NCCPI":
            dSDV["attributecolumnname"] = "INTERPHR"

            #if bFuzzy == True:
            #PrintMsg(" \nSwitching to fuzzy number mapping...", 1)
            aggMethod = "Weighted Average"
            dSDV["effectivelogicaldatatype"] = 'float'
            dSDV["attributelogicaldatatype"] = 'float'
            dSDV["maplegendkey"] = 3
            dSDV["maplegendclasses"] = 5
            dSDV["attributeprecision"] = 2

        # Temporary workaround for sql whereclause. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = "UPPER(" + sqlParts[0] + ") = " + sqlParts[1].upper()

        if dSDV["attributetype"].lower() == "interpretation" and dSDV["notratedphrase"] is None:
            # Add 'Not rated' to choice list
            dSDV["notratedphrase"] = "Not rated" # should not have to do this, but this is not always set in Rule Manager

        if dSDV["secondaryconcolname"] is not None and dSDV["secondaryconcolname"].lower() == "yldunits":
            # then this would be units for legend (component crop yield)
            #PrintMsg(" \nSetting units of measure to: " + secCst, 1)
            dSDV["attributeuomabbrev"] = secCst

        return dSDV

    except:
        errorMsg()
        return dSDV

## ===================================================================================
def GetRatingDomain(gdb):
    # return list of domain values for rating
    # modify this function to use uppercase string version of values

    try:
        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        mdcols = os.path.join(gdb, "mdstatdomdet")
        #domainName = dSDV["tiebreakdomainname"]
        domainValues = list()

        if dSDV["tiebreakdomainname"] is not None:
            wc = "domainname = '" + dSDV["tiebreakdomainname"] + "'"

            sc = (None, "ORDER BY choicesequence ASC")

            with arcpy.da.SearchCursor(mdcols, ["choice", "choicesequence"], where_clause=wc, sql_clause=sc) as cur:
                for rec in cur:
                    domainValues.append(rec[0])

        return domainValues

    except:
        errorMsg()
        return []

## ===================================================================================
def CalculateAcres(sdvLayer):
    #
    # Read raster or featureclass table and calculate area in acres for each rating category
    #
    try:

        dAcres = dict()

        if sdvLayer.isRasterLayer:
            PrintMsg(" \nCreating acreage summary report for raster layer '" + layerName + "'", 0)
            # input is a raster
            cellSizeX = desc.meanCellWidth
            cellSizeY = desc.meanCellHeight
            cellSize = cellSizeX * cellSizeY

            for fld in layerFields:
                if fld.baseName.upper() == "COUNT":
                    countField = fld.name

            # number of acres per cell
            cellAcres = convAcres * cellSize
            #PrintMsg(" \nRaster cellsize = " + str(cellSize) + " " + units, 1)
            #PrintMsg(" \nRaster cellsize = " + str(cellAcres) + " acres", 1)

            fields = [countField, layerRatingField]

            with arcpy.da.SearchCursor(layerName, fields) as cur:
                for rec in cur:
                    # Accumulate acres for each rating value
                    try:
                        dAcres[rec[1]] += (float(rec[0]) * cellAcres)

                    except:
                        dAcres[rec[1]] = (rec[0] * cellAcres)

        elif sdvLayer.isFeatureLayer and desc.shapetype.lower() == "polygon":
            # input is a polygon featurelayer
            PrintMsg(" \nCreating acreage summary report for feature layer '" + layerName + "' \n ", 0)
            fields = ["SHAPE@AREA", layerRatingField]

            with arcpy.da.SearchCursor(layerName, fields) as cur:
                for rec in cur:
                    try:
                        dAcres[rec[1]] += (rec[0] * convAcres)

                    except:
                        dAcres[rec[1]] = (rec[0] * convAcres)

        return dAcres

    except MyError, e:
        PrintMsg(str(e), 2)
        return dAcres

    except:
        errorMsg()
        return dAcres

## ===================================================================================
def CreateOutputTable(dAcres, domainValues):
    # Create the initial output table that will contain key fields from all levels plus the input rating field
    #
    # Do I need to add the option for AREASYMBOL subtotals? This would be difficult for rasters which
    # do not normally carry that attribute.

    try:

        # Validate output table name
        env.workspace = gdb
        outputTbl = os.path.join("IN_MEMORY", "SummaryTable")
        #outputTbl = os.path.join(env.scratchGDB, "SummaryTable")

        # Delete table from prior runs
        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        # Create the final output table using initialTbl as a template
        arcpy.CreateTable_management(os.path.dirname(outputTbl), os.path.basename(outputTbl))

        arcpy.AddField_management(outputTbl, resultField, fieldType, "", "", fieldLength, layerName)
        arcpy.AddField_management(outputTbl, "ACRES", "DOUBLE" )


        if len(domainValues) > 0 and ("Not rated" in dAcres or "Not Rated" in dAcres):
            PrintMsg(" \nDomain values includes 'Not rated'", 1)

        with arcpy.da.InsertCursor(outputTbl, [resultField, "ACRES"]) as cur:
            if len(domainValues) > 0:
                #PrintMsg(" \nCreating graph using domain values", 1)
                for rating in domainValues:
                    if rating is None:
                        cur.insertRow(["Not rated", round(dAcres[rating], 0)])
                        PrintMsg("Not rated: " + str(round(dAcres[rating])), 1)

                    else:
                        try:
                            cur.insertRow([rating, round(dAcres[rating], 0)])

                        except:
                            pass

            else:
                #PrintMsg(" \nCreating graph using table values", 1)
                iterValues = sorted(dAcres)

                for rating in iterValues:
                    if rating is None:
                        cur.insertRow(["Not rated", round(dAcres[rating], 0)])
                        domainValues.append("Not rated")

                    else:
                        cur.insertRow([rating, round(dAcres[rating], 0)])
                        domainValues.append(rating)


        if arcpy.Exists(outputTbl):
            #
            # Convert in-memory table to a table in the geodatabase
            #PrintMsg(" \nMaking copy of table to " + xTable)
            #arcpy.TableToTable_conversion(outputTbl, gdb, "xGraphTable")
            return outputTbl, domainValues

        else:
            raise MyError, "Failed to create output table"

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, domainValues

    except:
        errorMsg()
        return outputTbl, domainValues

## ===================================================================================
def CreateGraph(outputTbl, domainValues, valWidth, sAcres, outputFile):
    # Use in-memory summary table to create graph
    #
    # Graph is based upon domain values. Some attributes such as the integer Percent Hydric,
    # have no domain values. I would still like to graph these. Should I use unique values
    # natural breaks or class breaks??

    try:

        # New bar graph object
        graph = arcpy.Graph()
        graph.addSeriesBarVertical(outputTbl, "ACRES", "OBJECTID", resultField)

        # Get the total length of the legend value string and use to set graph width
        numChars = 0
        for val in domainValues:
            numChars += len(str(val))

        graphWidth = (numChars + valWidth) * 8.0
        graphHeight = 500.0

        graph.graphPropsGeneral.title = layerName  # This works but is lowercased
        graph.graphPropsGeneral.footer = "Input layer: " + os.path.join(os.path.basename(gdb), os.path.basename(fc))        # This works but is lowercased
        subTitle = "Total Acres: " + sAcres
        #PrintMsg(" \nTotal Acres used in graph subtitle = " + sAcres, 1)
        graph.graphPropsGeneral.subtitle = subTitle #
        #graph.graphAxis[0] = "Axis 0 ACRES"  # this is being ignored
        #graph.graphAxis[2] = "Axis 2 " + layerName  # this is being ignored
        outputGraph = "SDVGraph"
        graphTemplate = os.path.join(os.path.dirname(sys.argv[0]), "BarGraph_Classic.grf")

        # Create graph with the selected properties
        arcpy.MakeGraph_management(graphTemplate, graph, outputGraph)
        # Export the graph to the specified graphic file (emf)
        arcpy.SaveGraph_management (outputGraph, outputFile, "IGNORE_ASPECT_RATIO", graphWidth, graphHeight)  # graph width works

        if not arcpy.Exists(outputFile):
            # Display output graphic file for diagnostic purposes only
            #PrintMsg(" \nCreated output graphic file (" + outputFile + ")", 0)
            raise MyError, "Failed to create output graphic file"
            #os.startfile(outputFile)

        # return graph width and height in pixels. These will be used later to set the graph size in pageunits inches.
        return graphWidth, graphHeight

    except MyError, e:
        PrintMsg(str(e), 2)
        return 0, 0

    except:
        errorMsg()
        return 0, 0

## ===================================================================================
def CreateReport(outputTbl, template, reportPDF):
    #
    #
    try:
        # Get report template file fullpath (.rlf) and import current SDV_Data table into it

        if arcpy.Exists(reportPDF):
            arcpy.Delete_management(reportPDF, "FILE")

        # Set some of the parameters for the ExportReport command
        dataset = "USE_RLF"
        dataset = "ALL"
        title = layerName
        start = None
        range = None
        extent = None

        # Remove table view for summary. It might be an old one
        sdvTableName = os.path.basename(outputTbl)
        tableViews = arcpy.mapping.ListTableViews(mxd, sdvTableName, df)

        for tbl in tableViews:
            if tbl.name == sdvTableName:
                arcpy.mapping.RemoveTableView(df, tbl)

        #PrintMsg(" \nCreating table view using '" + outputTbl + "'", 1)
        sdvTbl = arcpy.mapping.TableView(outputTbl)

        #PrintMsg(" \nInput summary table: " + outputTbl, 0)
        #PrintMsg(" \nUsing report template: " + template, 0)
        #PrintMsg(" \nRating data type: " + fieldType, 0)

        arcpy.mapping.AddTableView(df, sdvTbl)

        arcpy.SetProgressorLabel("Running report for '" + title + "' ....")
        PrintMsg(" \nImporting table into report template...", 0)

        fm = {"OBJECTID":"ObjectID", "RATING":resultField, "ACRES":"ACRES"}

        # Create PDF for tabular report
        arcpy.mapping.ExportReport(sdvTbl, template, reportPDF, field_map=fm)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time

# Create the environment
from arcpy import env

try:
    layerName = arcpy.GetParameterAsText(0)      # Selected input Soil Map layer from ArcMap TOC

    env.overwriteOutput = True

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame
    sdvLayer = arcpy.mapping.ListLayers(mxd, layerName, df)[0]
    desc = arcpy.Describe(sdvLayer.name)
    fc = desc.catalogPath

    gdb = os.path.dirname(fc)  # need to modify this to handle feature datasets

    env.workspace = gdb
    layerFields = desc.fields
    layerField = layerFields[-1]  # assume the last field is the rating
    layerRatingField = layerField.name.upper()
    resultField = layerField.baseName.upper()
    fieldType = layerField.type.lower()
    fieldLength = layerField.length
    sr = desc.spatialReference
    units = sr.linearUnitName.lower()

    # Get information from sdvattribute table
    dSDV = GetSDVAtts(gdb, resultField)

    if len(dSDV) == 0:
        raise MyError, ""

    # Get domain tiebreak values for this attribute
    domainValues = GetRatingDomain(gdb)

    if len(domainValues) > 0:
        domainValuesUp = [x.upper() for x in domainValues]
        #PrintMsg(" \n" + ", ".join(domainValues), 1)

    # Create dictionary to store acreage by rating values


    if units == "meter":
        convAcres = 0.000247104393                     # meters

    elif units == "foot_us":
        convAcres = 0.000022956841138659               # US Survey foot

    elif units == "foot":
        convAcres = 0.00002295679522500955             # International Feet

    else:
        raise MyError, "Unable to handle unit conversion for area (" + units + ")"

    dAcres = CalculateAcres(sdvLayer)

    # Print area for each rating
    #
    # Need to output this to a table for use in creating a Graph
    #
    valWidth = 0  # save string length of acreage values for use in graph formatting
    totalAcres = 0
    totalArea = 0

    for rating in sorted(dAcres):
        #area = dAcres[rating]
        #acres = round(convAcres * area, 0)
        acres = round(dAcres[rating], 0)
        totalAcres += acres
        #totalArea += area
        #dAcres[rating] = acres
        valWidth += len(str(acres))
        PrintMsg("\tSubtotal for " + str(rating) + ": " + Number_Format(acres, 0, True) + " acres", 0)

    PrintMsg("\t" + ("-" * 40) + " \n\tTotal Acres: " + Number_Format(totalAcres, 0, True), 0)

    #totalAcres = int(round(convAcres * totalArea, 0))

    valWidth += (len(dAcres) * 2)  # add a little extra width for space

    # Create summary table
    outputTbl, domainValues = CreateOutputTable(dAcres, domainValues)

    #PrintMsg(" \nOutput table created", 1)

    # Get the path for the template MXD being used to create the cover page

    # Get SDV narrative and settings used from the soil map layer
    layerDesc = sdvLayer.description

    # Open portrait layout mxd with text box and update with layer description
    mxdName = "SDV_MapDescription_Portrait.mxd"
    mxdFile = os.path.join(os.path.dirname(sys.argv[0]), mxdName)
    textMXD = arcpy.mapping.MapDocument(mxdFile)
    textDF = textMXD.activeDataFrame
    textBox = arcpy.mapping.ListLayoutElements(textMXD, "TEXT_ELEMENT", "Description Text Box*")[0]
    textMXD.title = layerName
    textBox.text = layerDesc
    textPDF = os.path.join(os.path.dirname(gdb), layerName + "_AcreageSummary.pdf")
    #PrintMsg(" \nCreating text PDF", 1)
    arcpy.mapping.ExportToPDF(textMXD, textPDF)
    #PrintMsg(" \nText PDF created", 1)

    if len(domainValues) <= 12:
        # Small number of rating values, make a graph
        #
        outputGraphic = os.path.join(env.scratchFolder, "BarGraph.emf")  # output graphic file

        graphWidth, graphHeight = CreateGraph(outputTbl, domainValues, valWidth, Number_Format(totalAcres, 0, True), outputGraphic)

        #
        # PROBABLY NEED TO MOVE SOME OF THE CODE DIRECTLY BELOW INTO THE CreateGraph FUNCTION
        #
        if graphWidth == 0:
            raise MyError, ""

        # determine page size for graphic, trying to keep original aspect ratio
        pageWidth = 6.5
        dpiX = round((graphWidth / pageWidth), 0)
        aspectRatio = graphHeight / graphWidth
        pageHeight = round((pageWidth * aspectRatio), 1)

        # Lower left origin on page for graphic
        originX = 1.0
        originY = 9.0 - pageHeight

        mxdName = "SDV_Graph_Portrait.mxd"
        mxdFile = os.path.join(os.path.dirname(sys.argv[0]), mxdName)
        graphMXD = arcpy.mapping.MapDocument(mxdFile)
        graphDF = graphMXD.activeDataFrame
        graphElement = arcpy.mapping.ListLayoutElements(graphMXD, "PICTURE_ELEMENT", "GraphArea")[0]
        graphMXD.title = layerName
        graphElement.sourceImage = outputGraphic

        # The following 4 properties did not work. The graphic is no longer on the page. Page Units???
        graphElement.elementHeight = pageHeight
        graphElement.elementWidth = pageWidth
        graphElement.elementPositionX = originX
        graphElement.elementPositionY = originY
        graphPDF = os.path.join(env.scratchFolder, "graph.pdf")
        #PrintMsg(" \nCreating graph", 1)
        arcpy.mapping.ExportToPDF(graphMXD, graphPDF)
        #PrintMsg(" \nGraph created", 1)

    else:
        PrintMsg

    # Get report template file fullpath (.rlf) and import current SDV_Data table into it
    if fieldType == "smallinteger":
        templateName = "SDV_Report_AcreageInt.rlf"  # No AREASYMBOL in this report

    else:
        templateName = "SDV_Report_Acreage.rlf"  # No AREASYMBOL in this report

    template = os.path.join(os.path.dirname(sys.argv[0]), templateName)
    reportPDF = os.path.join(os.path.dirname(gdb), layerName + ".pdf")
    #PrintMsg(" \nCreating report", 1)
    bReport = CreateReport(outputTbl, template, reportPDF)
    #PrintMsg(" \nReport created", 1)

    # Open the report PDF for final editing

    # Need to open textPDF first (title, description)
    # If there is a graph, Append the Graph PDF
    # Append the other PDF files

    pdfDoc = arcpy.mapping.PDFDocumentOpen(textPDF)

    if len(domainValues) <= 12:
        # should be a graph
        pdfDoc.appendPages(graphPDF)

    pdfDoc.appendPages(reportPDF)

    # Update some of the PDF settings and metadata properties
    keyWords = 'gSSURGO;soil map'
    userName = GetUser()
    pdfDoc.updateDocProperties(pdf_title=layerName, pdf_author=userName, pdf_subject="Soil Map", pdf_keywords=keyWords, pdf_layout="SINGLE_PAGE", pdf_open_view="USE_NONE")
    pdfDoc.saveAndClose()

    if arcpy.Exists(textPDF):
        arcpy.SetProgressorLabel("Report complete")
        PrintMsg(" \nReport complete (" + textPDF + ")\n ", 0)
        os.startfile(textPDF)

    else:
        raise MyError, "Failed to create " + textPDF

    del mxd

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
