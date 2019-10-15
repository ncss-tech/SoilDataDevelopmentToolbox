# gSSURGO_ExportRasters.py
#
# Steve Peaslee, National Soil Survey Center
# 2018-11-30
#
# Purpose: Convert gSSURGO soil maps into a single raster with bands.
# Order of input soil maps should match order of bands.
#

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
        PrintMsg("Unhandled error in errorMsg method", 2)
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
def UpdateMetadata(theGDB, target, sdvLayer, description, iRaster, depthList):
    #
    # Used for non-ISO metadata
    #
    # Process:
    #     1. Read gSSURGO_MapunitRaster.xml
    #     2. Replace 'XX" keywords with updated information
    #     3. Write new file xxImport.xml
    #     4. Import xxImport.xml to raster
    #
    # Problem with ImportMetadata_conversion command. Started failing with an error.
    # Possible Windows 10 or ArcGIS 10.5 problem?? Later had to switch back because the
    # alternative ImportMetadata_conversion started for failing with the FY2018 rasters without any error.
    #
    # Search for keywords:  xxSTATExx, xxSURVEYSxx, xxTODAYxx, xxFYxx
    #
    try:
        PrintMsg("\tUpdating raster metadata...")
        arcpy.SetProgressor("default", "Updating raster metadata")

        # Reformat depthList
        sDepths = ""
        
        for i in range(len(depthList)):
            sDepths = sDepths + "\r\n\nBand " + str(i + 1) + ": " + depthList[i]
            

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        mdTranslator = os.path.join(installPath, prod)  # This file is not being used

        # Define input and output XML files
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info
        xmlPath = os.path.dirname(sys.argv[0])
        mdExport = os.path.join(xmlPath, "gSSURGO_PropertyRaster.xml") # original template metadata in script directory
        #PrintMsg(" \nParsing gSSURGO template metadata file: " + mdExport, 1)

        #PrintMsg(" \nUsing SurveyInfo: " + str(surveyInfo), 1)

        # Cleanup output XML files from previous runs
        if os.path.isfile(mdImport):
            os.remove(mdImport)

        # Get replacement value for the search words
        #
        stDict = StateNames()
        st = os.path.basename(theGDB)[8:-4]

        if st in stDict:
            # Get state name from the geodatabase
            mdState = stDict[st]

        else:
            # Leave state name blank. In the future it would be nice to include a tile name when appropriate
            mdState = ""

        # Update metadata file for the geodatabase
        #
        # Query the output SACATALOG table to get list of surveys that were exported to the gSSURGO
        #
        saTbl = os.path.join(theGDB, "sacatalog")
        expList = list()

        with arcpy.da.SearchCursor(saTbl, ("AREASYMBOL", "SAVEREST")) as srcCursor:
            for rec in srcCursor:
                expList.append(rec[0] + " (" + str(rec[1]).split()[0] + ")")
                
        surveyInfo = ", ".join(expList)
        
        #PrintMsg(" \nUsing this string as a substitute for xxSTATExx: '" + mdState + "'", 1)
        
        # Set date strings for metadata, based upon today's date
        #
        d = datetime.date.today()
        today = str(d.isoformat().replace("-",""))
        #PrintMsg(" \nToday replacement string: " + today, 1)

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        #PrintMsg(" \nFY replacement string: " + str(fy), 1)

        # Process gSSURGO_MapunitRaster.xml from script directory
        tree = ET.parse(mdExport)
        root = tree.getroot()

        # new citeInfo has title.text, edition.text, serinfo/issue.text
        citeInfo = root.findall('idinfo/citation/citeinfo/')

        if not citeInfo is None:
            # Process citation elements
            # title, edition, issue
            #
            for child in citeInfo:
                PrintMsg("\t\t" + str(child.tag), 0)
                
                if child.tag == "title":
                    if child.text.find('xxTITLExx') >= 0:
                        # Insert layer name here

                        if mdState != "":
                            newTitle = sdvLayer + " - " + mdState
                            #PrintMsg("\t\tUpdating title to: " + newTitle, 1)
                            #child.text = child.text.replace('xxSTATExx', mdState)
                            child.text = newTitle

                        else:
                            child.text = sdvLayer

                    else:
                        child.text = "Map Unit Raster " + str(iRaster) + "m"

                elif child.tag == "edition":
                    if child.text == 'xxFYxx':
                        #PrintMsg("\t\tReplacing xxFYxx", 1)
                        child.text = fy

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            #PrintMsg("\t\tReplacing xxFYxx", 1)
                            subchild.text = fy

        # Update place keywords
        ePlace = root.find('idinfo/keywords/place')

        if not ePlace is None:
            PrintMsg("\t\tplace keywords", 0)

            for child in ePlace.iter('placekey'):
                if child.text == "xxSTATExx":
                    #PrintMsg("\t\tReplacing xxSTATExx", 1)
                    child.text = mdState

                elif child.text == "xxSURVEYSxx":
                    #PrintMsg("\t\tReplacing xxSURVEYSxx", 1)
                    child.text = surveyInfo

        # Update credits
        eIdInfo = root.find('idinfo')
        if not eIdInfo is None:
            PrintMsg("\t\tcredits", 0)

            for child in eIdInfo.iter('datacred'):
                sCreds = child.text

                if sCreds.find("xxSTATExx") >= 0:
                    #PrintMsg("\t\tcredits " + mdState, 0)
                    child.text = child.text.replace("xxSTATExx", mdState)
                    #PrintMsg("\t\tReplacing xxSTATExx", 1)

                if sCreds.find("xxFYxx") >= 0:
                    #PrintMsg("\t\tcredits " + fy, 0)
                    child.text = child.text.replace("xxFYxx", fy)
                    #PrintMsg("\t\tReplacing xxFYxx", 1)

                if sCreds.find("xxTODAYxx") >= 0:
                    #PrintMsg("\t\tcredits " + today, 0)
                    child.text = child.text.replace("xxTODAYxx", today)
                    #PrintMsg("\t\tReplacing xxTODAYxx", 1)


        idAbstract = root.find('idinfo/descript/abstract')
        
        if not idAbstract is None:
            PrintMsg("\t\tabstract", 0)
            
            ip = idAbstract.text

            if ip.find("xxABSTRACTxx") >= 0:
                description = description + "\n" + sDepths
                idAbstract.text = ip.replace("xxABSTRACTxx", description)
                #PrintMsg("\t\tReplacing xxABSTRACTxx", 1)

        idPurpose = root.find('idinfo/descript/purpose')
        
        if not idPurpose is None:
            PrintMsg("\t\tpurpose", 0)
            
            ip = idPurpose.text

            if ip.find("xxFYxx") >= 0:
                idPurpose.text = ip.replace("xxFYxx", fy)
                #PrintMsg("\t\tReplacing xxFYxx", 1)
                

        #PrintMsg(" \nSaving template metadata to " + mdImport, 1)

        #  create new xml file which will be imported, thereby updating the table's metadata
        tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")

        # import updated metadata to the geodatabase table
        # Using three different methods with the same XML file works for ArcGIS 10.1
        #
        #PrintMsg(" \nImporting metadata " + mdImport + " to " + target, 1)
        arcpy.MetadataImporter_conversion(mdImport, target)  # This works. Raster now has metadata with 'XX keywords'. Is this step neccessary to update the source information?

        #PrintMsg(" \nUpdating metadata for " + target + " using file " + mdImport, 1)
        arcpy.ImportMetadata_conversion(mdImport, "FROM_FGDC", target, "DISABLED")  # Tool Validate problem here
        #arcpy.MetadataImporter_conversion(target, mdImport) # Try this alternate tool with Windows 10.

        # delete the temporary xml metadata file
        if os.path.isfile(mdImport):
            os.remove(mdImport)
            #pass

        # delete metadata tool logs
        logFolder = os.path.dirname(env.scratchFolder)
        logFile = os.path.basename(mdImport).split(".")[0] + "*"

        currentWS = env.workspace
        env.workspace = logFolder
        logList = arcpy.ListFiles(logFile)

        for lg in logList:
            arcpy.Delete_management(lg)

        env.workspace = currentWS

        return True

    except:
        errorMsg()
        False

## ===================================================================================
def ResampleMapunitRaster(inputRaster, inRes, iFactor, outRes, outputRaster):
    # 
    #
    try:
        # Resample a high resolution gSSURGO mapunit raster to a lower resolution
        # Use Block Statistics Majority Aggregation and then Resample
        PrintMsg(" \nTurn Pyramids off and then build those and attributes at the end", 0)
        env.snapRaster = inputRaster
        env.pyramid = "NONE"
        nbr = NbrAnnulus(1, iFactor, "MAP")
        PrintMsg(" \n1. Running block statistics...", 0)
        blockRas =  BlockStatistics(inputRaster, nbr, "MAJORITY", "DATA")

        PrintMsg(" \n2. Filling NoData pixels...", 0)
        filledRas = Con(IsNull(blockRas), inputRaster, blockRas)  # Try filling the NoData holes in the aggregate raster using data from the 30m input raster

        if arcpy.Exists(filledRas):
            #arcpy.Delete_management(blockRas)
            
            PrintMsg(" \n3. Resampling to " + outputRaster, 0)
            arcpy.Resample_management(filledRas, outputRaster, outRes, "NEAREST")

            if arcpy.Exists(outputRaster):
                #arcpy.Delete_management(filledRas)

                arcpy.SetProgressor("default", "Calculating raster statistics...")
                PrintMsg("\tCalculating raster statistics...", 0)
                env.pyramid = "PYRAMIDS -1 NEAREST"
                arcpy.env.rasterStatistics = 'STATISTICS 100 100'
                arcpy.CalculateStatistics_management (outputRaster, 1, 1, "", "OVERWRITE" )
                
                arcpy.SetProgressor("default", "Building pyramids...")
                PrintMsg("\tBuilding pyramids...", 0)
                arcpy.BuildPyramids_management(outputRaster, "-1", "NONE", "NEAREST", "DEFAULT", "", "SKIP_EXISTING")
                
                PrintMsg("\tBuilding raster attribute table and updating MUKEY values", )
                arcpy.SetProgressor("default", "Building raster attrribute table...")
                arcpy.BuildRasterAttributeTable_management(outputRaster)

                # Add MUKEY values to final mapunit raster
                #
                arcpy.SetProgressor("default", "Adding MUKEY attribute to raster...")
                arcpy.AddField_management(outputRaster, "MUKEY", "TEXT", "#", "#", "30")
                
                with arcpy.da.UpdateCursor(outputRaster, ["VALUE", "MUKEY"]) as cur:
                    for rec in cur:
                        rec[1] = rec[0]
                        cur.updateRow(rec)

                # Add attribute index (MUKEY) for raster
                arcpy.AddIndex_management(outputRaster, ["mukey"], "Indx_" + os.path.basename(outputRaster))

        if arcpy.Exists(outputRaster):
            PrintMsg(" \nCompleted raster processing", 0)

        else:
            PrintMsg
            
        # Get description from last soil map layer
        #description = dMetadata[sdvLayer]

        #bMetadata = UpdateMetadata(gdb, newRaster, sdvLayer, description, iRaster, depthList)
        
            
        return True

    except MyError, e:
        PrintMsg(str(e) + " \n", 2)
        return False

    except:
        errorMsg()
        return False

# ====================================================================================
## ====================================== Main Body ==================================
# Import modules
import sys, string, os, locale, traceback, arcpy
from arcpy import env
from arcpy.sa import *
import xml.etree.cElementTree as ET

try:


    if __name__ == "__main__":
        
        inputRaster = arcpy.GetParameterAsText(0)    # gSSURGO FGDB raster that will be resampled to a lower resolution
        inRes = arcpy.GetParameter(1)
        iFactor = arcpy.GetParameter(2)
        outRes = arcpy.GetParameter(3)
        outputRaster = arcpy.GetParameterAsText(4)
        
        ResampleMapunitRaster(inputRaster, inRes, iFactor, outRes, outputRaster)


except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

