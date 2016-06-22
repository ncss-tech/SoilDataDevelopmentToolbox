# gSSURGO_TabularInterpReport.py
#
# Converts the InterpQuery table into a report.
# That table is created by the 'Map Intepretation Reasons' tool.
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

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time

# Create the environment
from arcpy import env

try:
    layerName = arcpy.GetParameterAsText(0)      # Input Soil Map layer in ArcMap TOC

    env.overwriteOutput = True

    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = mxd.activeDataFrame
    sdvLayer = arcpy.mapping.ListLayers(mxd, layerName, df)[0]
    gdb = os.path.dirname(arcpy.Describe(sdvLayer).catalogPath)
    env.workspace = gdb
    inputTbl = os.path.join(gdb, "SDV_Data")  # table containing pre-aggregated data in gSSURGO database
    legendTbl = os.path.join(gdb, "legend")    # table containing legend.areaname

    # Cleanup query table from previous run
    sdvTableName = "SDV_Data"

    #if arcpy.Exists(sdvTbl):
    #    arcpy.Delete_management(sdvTbl, "FEATURELAYER")

    if arcpy.Exists(inputTbl):

        # Create relate between rating table and legend table to get areaname
        arcpy.CreateRelationshipClass_management(legendTbl, inputTbl, os.path.join(gdb, "xLegend_SDVData"), "SIMPLE", "SDV_Data", "Legend", None, "ONE_TO_ONE", None, "AREASYMBOL", "AREASYMBOL", "","")

        # Get SDV map layer information
        layerFields = arcpy.Describe(layerName).fields
        layerField = layerFields[-1]  # assume the last field is the rating
        #layerRatingField = "SDV_Data." + layerField.baseName.upper().encode('ascii')
        layerRatingField = layerField.baseName.upper().encode('ascii')

        fieldType = layerField.type.lower()

        # Get SDV Rating table information
        fmFields = list()
        ratingFields = arcpy.Describe(inputTbl).fields
        ratingField = ratingFields[-1]  # assume the last field is the rating
        ratingType = ratingFields[-1].type.lower()
        #ratingFieldName = "SDV_Data." + layerField.name.upper()
        ratingFieldName = ratingField.name.upper().encode('ascii')

        if ratingType != fieldType:
            PrintMsg(" \nSwitch in data type (" + fieldType + "-->" + ratingType + ")", 1)
            fieldType = ratingType

        for fld in ratingFields:
            fmFields.append(fld.name)

        # SDV_MapDescription.mxd; TEXT_BOX "Description Text Box"
        # ListLayoutElements (map_document, "TEXT_ELEMENT", "Description Text Box*")

        # Need to also add a comparison of field alias names for the rating table and the selected layer. Try
        # to make sure they are both based upon the same data (this is now being done in the validation code).
        #
        # Determine type of rating table and which report template will match attributes
        if "HZDEPT_R" in fmFields:
            # horizon level rating, use landscape format for all
            #
            mxdName = "SDV_MapDescription_Landscape.mxd"
            fm = {"AREASYMBOL":"AREASYMBOL", "MUKEY":"MUKEY", "MUSYM":"MUSYM", "MUNAME":"MUNAME", "COMPNAME":"COMPNAME", "COMPPCT_R":"COMPPCT_R", "HZDEPT_R":"HZDEPT_R", "HZDEPB_R":"HZDEPB_R", "RATING":ratingFieldName}

            if fieldType in ["string", "choice"]:
                templateName = "SDV_Report_Hz_String.rlf"

            elif fieldType in ["single", "double", "float"]:
                templateName = "SDV_Report_Hz_Float.rlf"

            elif fieldType == "smallinteger":
                templateName = "SDV_Report_Hz_Integer.rlf"

            else:
                raise MyError, "Invalid data type: " + fieldType

        elif "COMPNAME" in fmFields:
            # component level rating
            fm = {"AREASYMBOL":"AREASYMBOL", "MUKEY":"MUKEY", "MUSYM":"MUSYM", "MUNAME":"MUNAME", "COMPNAME":"COMPNAME", "COMPPCT_R":"COMPPCT_R", "RATING":ratingFieldName}

            if fieldType in ["string", "choice"]:
                mxdName = "SDV_MapDescription_Landscape.mxd"
                templateName = "SDV_Report_Co_String.rlf"

            elif fieldType in ["single", "double", "float"]:
                mxdName = "SDV_MapDescription_Portrait.mxd"
                templateName = "SDV_Report_Co_Float.rlf"

            elif fieldType == "smallinteger":
                mxdName = "SDV_MapDescription_Portrait.mxd"
                templateName = "SDV_Report_Co_Integer.rlf"

            else:
                raise MyError, "Invalid data type: " + fieldType

        else:
            # Map unit level rating
            mxdName = "SDV_MapDescription_Portrait.mxd"
            fm = {"AREASYMBOL":"AREASYMBOL", "MUKEY":"MUKEY", "MUSYM":"MUSYM", "MUNAME":"MUNAME", "RATING":ratingFieldName}

            if ratingFieldName == "MUNAME":
                PrintMsg(" \nCreating report for map unit name", 1)
                templateName = "SDV_Report_MuName.rlf"
                #fm = {"AREASYMBOL":"AREASYMBOL", "MUKEY":"MUKEY", "MUSYM":"MUSYM", "MUNAME":"MUNAME"}
                #fm = "AREANAME":"AREANAME"
                fm = None

            elif fieldType in ["string", "choice"]:
                templateName = "SDV_Report_Mu_String.rlf"

            elif fieldType in ["single", "double", "float", "smallinteger"]:
                templateName = "SDV_Report_Mu_Float.rlf"

            elif fieldType == "integer":
                templateName = "SDV_Report_Mu_Integer.rlf"

            else:
                raise MyError, "Invalid data type: " + fieldType

        # Get the path for the template MXD being used to create the cover page
        mxdFile = os.path.join(os.path.dirname(sys.argv[0]), mxdName)

        # Get SDV narrative and settings used from the soil map layer
        layerDesc = sdvLayer.description

        # Open mxd with text box and update with layer description
        textMXD = arcpy.mapping.MapDocument(mxdFile)
        textDF = textMXD.activeDataFrame
        textBox = arcpy.mapping.ListLayoutElements(textMXD, "TEXT_ELEMENT", "Description Text Box*")[0]
        textMXD.title = layerName
        textBox.text = layerDesc
        textPDF = os.path.join(env.scratchFolder, "description.pdf")
        arcpy.mapping.ExportToPDF(textMXD, textPDF)

        # Get report template file fullpath (.rlf) and import current SDV_Data table into it
        template = os.path.join(os.path.dirname(sys.argv[0]), templateName)
        reportPDF = os.path.join(os.path.dirname(gdb), layerName + ".pdf")

        if arcpy.Exists(reportPDF):
            arcpy.Delete_management(reportPDF, "FILE")

        # Set some of the parameters for the ExportReport command
        dataset = "USE_RLF"
        dataset = "ALL"
        title = layerName
        start = None
        range = None
        extent = None

        # Try adding tableView and then joining the legend table to that so
        # that I can get the survey area name. For some reason this
        # report is picking up the legend relationshipclass
        # when I manually run the report, but not from within this script.
        # Possible ArcMap 10.1 bug? There is no error message.
        tableViews = arcpy.mapping.ListTableViews(mxd, sdvTableName, df)

        for tbl in tableViews:
            if tbl.name == sdvTableName:
                arcpy.mapping.RemoveTableView(df, tbl)

        sdvTbl = arcpy.mapping.TableView(inputTbl)
        sdvTableName = sdvTbl.name

        PrintMsg(" \nInput rating table: " + inputTbl, 0)
        PrintMsg(" \nUsing report template: " + template, 0)
        #PrintMsg(" \nUsing field mapping: " + str(fm), 0)
        PrintMsg(" \nRating data type: " + fieldType, 0)

        arcpy.mapping.AddTableView(df, sdvTbl)

        arcpy.SetProgressorLabel("Running report for '" + title + "' ....")
        PrintMsg(" \nImporting table into report template...", 0)

        # Create PDF for tabular report
        arcpy.mapping.ExportReport(sdvTbl, template, reportPDF, dataset, report_title=title, field_map=fm)

        # Open the report PDF for editing
        pdfDoc = arcpy.mapping.PDFDocumentOpen(reportPDF)

        # Delete the opening page where I have the title and a page break. It would be better if I
        # simply remove the title object from each of the report template files.
        #
        pdfDoc.deletePages(1)

        # Insert the title page PDF with narrative that created using the MXD layout
        pdfDoc.insertPages(textPDF, 1)

        # Update some of the PDF settings and metadata properties
        keyWords = 'gSSURGO;soil map'
        userName = GetUser()
        pdfDoc.updateDocProperties(pdf_title=title, pdf_author=userName, pdf_subject="Soil Map", pdf_keywords=keyWords, pdf_layout="SINGLE_PAGE", pdf_open_view="USE_NONE")
        pdfDoc.saveAndClose()

        # Remove the 'SDV_Data' table view
        arcpy.mapping.RemoveTableView(df, sdvTbl)

        if arcpy.Exists(reportPDF):
            arcpy.SetProgressorLabel("Report complete")
            PrintMsg(" \nReport complete (" + reportPDF + ")\n ", 0)
            os.startfile(reportPDF)

    else:
        raise MyError, "Failed to identify target layer"


except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
