# gSSURGO_InterpReport.py
#
# Converts the InterpQuery table into a report
#
# InterpQuery is a table view created by 'Map Interpretation Reasons' tool.
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

## =============================================================================
def GetSDVAttributes(sdvAtt):
    # query sdvattribute table for settings
    try:
        dSDV = dict()

       # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        sql1 = "attributename = '" + sdvAtt + "'"

        with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
            rec = cur.next()  # just reading first record
            i = 0
            for val in rec:
                dSDV[flds[i]] = val
                #PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                i += 1

        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        if dSDV["nasisrulename"] is not None and dSDV["nasisrulename"][0:5] == "NCCPI":
            dSDV["attributecolumnname"] = "interphr"

        # Temporary workaround for sql whereclause. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = "UPPER(" + sqlParts[0] + ") = " + sqlParts[1].upper()

        return dSDV

    except MyError, e:
        # Example: raise MyError("this is an error message")
        PrintMsg(str(e) + " \n", 2)
        return None

    except:
        errorMsg()
        return None

## ===================================================================================
def MakeReport(tableView):
    # Take InterpQuery table and create a report

    try:

        # Get SDV Rating table information

        fmFields = list()
        tblDesc = arcpy.Describe(tableViewName)
        ratingFields = tblDesc.fields

        dSDV = GetSDVAttributes(tableViewName)

        ratingField = ratingFields[-1]  # assume the last field is the rating
        ratingType = ratingFields[-1].type.lower()
        ratingFieldName = ratingField.name.upper().encode('ascii')

        # Get the path for the template MXD being used to create the cover page
        mxdName = "SDV_MapDescription_Landscape.mxd"
        mxdFile = os.path.join(os.path.dirname(sys.argv[0]), mxdName)

        # Get SDV narrative and settings used from the soil map layer
        layerDesc = dSDV["attributedescription"]

        # Open mxd with text box and update with layer description
        textMXD = arcpy.mapping.MapDocument(mxdFile)
        textDF = textMXD.activeDataFrame
        textBox = arcpy.mapping.ListLayoutElements(textMXD, "TEXT_ELEMENT", "Description Text Box*")[0]
        textMXD.title = dSDV["attributename"]
        textBox.text = layerDesc
        textPDF = os.path.join(env.scratchFolder, "description.pdf")
        arcpy.mapping.ExportToPDF(textMXD, textPDF)

        # Get report template file fullpath (.rlf) and import current SDV_Data table into it
        templateName = "SDV_InterpReasons.rlf"
        template = os.path.join(os.path.dirname(sys.argv[0]), templateName)
        reportPDF = os.path.join(os.path.dirname(gdb), dSDV["attributename"] + "_Interp.pdf")

        if arcpy.Exists(reportPDF):
            arcpy.Delete_management(reportPDF, "FILE")

        # Set some of the parameters for the ExportReport command
        dso = "DEFINITION_QUERY"
        title = dSDV["attributename"] + " Rating Reasons"
        start = None
        range = None
        extent = None
        fm = {"LEGEND_AREASYMBOL":"LEGEND_AREASYMBOL","COMPONENT_MUKEY":"COMPONENT_MUKEY", "MAPUNIT_MUSYM":"MAPUNIT_MUSYM", "MAPUNIT_MUNAME":"MAPUNIT_MUNAME", "COMPONENT_COMPNAME":"COMPONENT_COMPNAME", "COMPONENT_COMPPCT_R":"COMPONENT_COMPPCT_R", "COMPONENT_LOCALPHASE":"COMPONENT_LOCALPHASE", "COINTERP_RULENAME":"COINTERP_RULENAME", "COINTERP_INTERPHR":"COINTERP_INTERPHR"}
        #report_definition_query
        rdq = "COINTERP_RULEDEPTH > 0 AND COINTERP_INTERPHR IS NOT NULL"

        PrintMsg(" \nUsing report template: " + template, 0)
        #PrintMsg(" \nUsing field mapping: " + str(fm), 0)
        #PrintMsg(" \nRating data type: " + ratingType, 0)

        arcpy.SetProgressorLabel("Running report for '" + title + "' ....")
        PrintMsg(" \nImporting table into report template...", 0)

        # Create PDF for tabular report
        arcpy.mapping.ExportReport(tableView, template, reportPDF, dataset_option=dso, report_definition_query=rdq, report_title=title, field_map=fm)

        # Open the report PDF for editing
        pdfDoc = arcpy.mapping.PDFDocumentOpen(reportPDF)

        # Insert the title page PDF with narrative that created using the MXD layout
        pdfDoc.insertPages(textPDF, 1)

        # Update some of the PDF settings and metadata properties
        keyWords = 'gSSURGO;soil interpretation'
        userName = GetUser()

        pdfDoc.updateDocProperties(pdf_title=title, pdf_author=userName, pdf_subject="Soil Map", pdf_keywords=keyWords, pdf_layout="SINGLE_PAGE", pdf_open_view="USE_NONE")
        pdfDoc.saveAndClose()

        # Remove the 'SDV_Data' table view
        #arcpy.mapping.RemoveTableView(df, tableView)

        if arcpy.Exists(reportPDF):
            arcpy.SetProgressorLabel("Report complete")
            PrintMsg(" \nReport complete (" + reportPDF + ")\n ", 0)
            os.startfile(reportPDF)

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
    tableViewName = arcpy.GetParameterAsText(0)      # input table view

    env.overwriteOutput = True

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame

    tableViews = arcpy.mapping.ListTableViews(mxd, tableViewName, df)

    for tableView in tableViews:
    #   name = sdv attributename
    #   datasetName = "InterpQuery"
    #   workspacePath = gSSURGO database path
        if tableView.datasetName == "InterpQuery":
            gdb = tableView.workspacePath
            bReport = MakeReport(tableView)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
