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
def StateNames():
    # Create dictionary object containing list of state abbreviations and their names that
    # will be used to name the file geodatabase.
    # For some areas such as Puerto Rico, U.S. Virgin Islands, Pacific Islands Area the
    # abbrevation is

    # NEED TO UPDATE THIS FUNCTION TO USE THE LAOVERLAP TABLE AREANAME. AREASYMBOL IS STATE ABBREV

    try:
        stDict = dict()
        stDict["AL"] = "Alabama"
        stDict["AK"] = "Alaska"
        stDict["AS"] = "American Samoa"
        stDict["AZ"] = "Arizona"
        stDict["AR"] = "Arkansas"
        stDict["CA"] = "California"
        stDict["CO"] = "Colorado"
        stDict["CT"] = "Connecticut"
        stDict["DC"] = "District of Columbia"
        stDict["DE"] = "Delaware"
        stDict["FL"] = "Florida"
        stDict["GA"] = "Georgia"
        stDict["HI"] = "Hawaii"
        stDict["ID"] = "Idaho"
        stDict["IL"] = "Illinois"
        stDict["IN"] = "Indiana"
        stDict["IA"] = "Iowa"
        stDict["KS"] = "Kansas"
        stDict["KY"] = "Kentucky"
        stDict["LA"] = "Louisiana"
        stDict["ME"] = "Maine"
        stDict["MD"] = "Maryland"
        stDict["MA"] = "Massachusetts"
        stDict["MI"] = "Michigan"
        stDict["MN"] = "Minnesota"
        stDict["MS"] = "Mississippi"
        stDict["MO"] = "Missouri"
        stDict["MT"] = "Montana"
        stDict["NE"] = "Nebraska"
        stDict["NV"] = "Nevada"
        stDict["NH"] = "New Hampshire"
        stDict["NJ"] = "New Jersey"
        stDict["NM"] = "New Mexico"
        stDict["NY"] = "New York"
        stDict["NC"] = "North Carolina"
        stDict["ND"] = "North Dakota"
        stDict["OH"] = "Ohio"
        stDict["OK"] = "Oklahoma"
        stDict["OR"] = "Oregon"
        stDict["PA"] = "Pennsylvania"
        stDict["PRUSVI"] = "Puerto Rico and U.S. Virgin Islands"
        stDict["RI"] = "Rhode Island"
        stDict["Sc"] = "South Carolina"
        stDict["SD"] ="South Dakota"
        stDict["TN"] = "Tennessee"
        stDict["TX"] = "Texas"
        stDict["UT"] = "Utah"
        stDict["VT"] = "Vermont"
        stDict["VA"] = "Virginia"
        stDict["WA"] = "Washington"
        stDict["WV"] = "West Virginia"
        stDict["WI"] = "Wisconsin"
        stDict["WY"] = "Wyoming"
        return stDict

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return stDict

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
def CreateRasterLayers(sdvLayers, inputRaster):
    # Merge rating tables from for the selected soilmap layers to create a single, mapunit-level table
    #
    try:
        # Get number of SDV layers selected for export
        # If we want to add the option for composite bands...
        #    arcpy.CompositeBands_management("band1.tif;band2.tif;band3.tif", "compbands.tif")


        env.overwriteOutput = True # Overwrite existing output tables

        env.pyramid = "NONE"    

        # Tool validation code is supposed to prevent duplicate output tables

        # Get arcpy mapping objects
        thisMXD = arcpy.mapping.MapDocument("CURRENT")
        mLayers = arcpy.mapping.ListLayers(thisMXD)
        dMetadata = dict()  # Save original soil map description so that it can passed on to the raster layer
        depthList = list()
        newMetadata = ""

        for mLayer in mLayers:
            
            mdItems = mLayer.description.split("\n")

            for md in mdItems:
                if md.startswith("Top horizon"):
                    depthList.append(md)

                else:
                    newMetadata = newMetadata + md + "\n"

            dMetadata[mLayer.name] = newMetadata
            

        # Probably should make sure all of these input layers have the same featureclass
        #
        # first get path where input SDV shapefiles are located (using last one in list)
        # hopefully each layer is based upon the same set of polygons
        #
        # First check each input table to make sure there are no duplicate rating fields
        # Begin by getting adding fields from the input shapefile (lastShp). This is necessary
        # to avoid duplication such as MUNAME which may often exist in a county shapefile.

        chkFields = list()  # list of rating fields from SDV soil map layers (basenames). Use this to count dups.
        #dFields = dict()
        dLayerFields = dict()
        maxRecords = 0  # use this to determine which table has the most records and put it first
        maxTable = ""

        

        # Iterate through each of the layers and get its rating field
        for sdvLayer in sdvLayers:

            if sdvLayer.startswith("'") and sdvLayer.endswith("'"):
                sdvLayer = sdvLayers[i][1:-1]  # this is dropping first and last char in name for RUSLE2 maps..

            #else:
            #    PrintMsg(" \nTitle: " + str(sdvLayer), 1)

            desc = arcpy.Describe(sdvLayer)
            dataType = desc.dataType

            if dataType == "FeatureLayer":
                gdb = os.path.dirname(desc.featureclass.catalogPath)

            elif dataType == "RasterLayer":
                gdb = os.path.dirname(desc.catalogPath)

            else:
                raise MyError, "Soil map datatype (" + dataType + ") not valid"

            allFields = desc.fields
            ratingField = allFields[-1]  # rating field should be the last one in the table
            fName = ratingField.name.encode('ascii')       # fully qualified name
            bName = ratingField.baseName.encode('ascii')   # physical name
            tblName = fName.upper().split(".")[0]
            nameParts = tblName.split("_")
            thePrefix = ("_").join(nameParts[1:-1])    # use this string for the output raster name

            clipLen = (-1 * (len(bName))) - 1
            sdvTblName = fName[0:clipLen]
            sdvTbl = os.path.join(gdb, sdvTblName)
            fldType = ratingField.type
            fldLen = ratingField.length
            #fldAlias = bName + ", " + sdvTblName
            #mukeyField = [fld.name for fld in desc.fields if fld.basename.upper() == "MUKEY"][0]
            
            # ('SDV_AWS025', 'AWS025', 'SDV_AWS025.AWS025', u'Single', 4, 'AWS025, SDV_AWS025', u'MUPOLYGON.MUKEY')
            dLayerFields[sdvLayer] = (sdvTblName, fName, bName, fldType, fldLen)
            chkFields.append(bName)


        # Create raster layer for each soil map
        indx = 0
        dRasters = dict()
        rasterList = list()
        
        for sdvLayer in sdvLayers:
            #PrintMsg("\t" + str(dLayerFields[sdvLayer]), 1)
            
            sdvTblName, fName, bName, fldType, fldLen= dLayerFields[sdvLayer]
            description = dMetadata[sdvLayer]

            tmpRaster = "Temp_Raster"
            
            if arcpy.Exists(tmpRaster):
                # clean up any previous runs
                arcpy.Delete_management(tmpRaster)

            # Get FGDB raster from inputLayer
            rDesc = arcpy.Describe(inputRaster)
            iRaster = rDesc.meanCellHeight
            
            if rDesc.dataType == "RasterLayer":
                inputDataset = arcpy.Describe(inputRaster).catalogPath
                arcpy.MakeRasterLayer_management(inputDataset, tmpRaster)
                gdb = os.path.dirname(inputDataset)

            elif rDesc.dataType == "RasterDataset":
                arcpy.MakeRasterLayer_management(inputRaster, tmpRaster)
                gdb = os.path.dirname(inputRaster)
                
            if not arcpy.Exists(tmpRaster):
                raise MyError, "Missing raster map layer"

            arcpy.AddJoin_management (tmpRaster, "MUKEY", os.path.join(gdb, sdvTblName), "MUKEY", "KEEP_ALL")

            # Create raster using Lookup_sa
            # Select non-Null values when fldType in ('Single', 'Double')
            wc = fName + " IS NOT NULL"
            arcpy.SelectLayerByAttribute_management(tmpRaster, "NEW_SELECTION", wc)

            PrintMsg(" \n\tConverting '" + sdvLayer + "' to raster", 0)

            
            dRasters[indx] = Lookup(tmpRaster, fName)
            indx += 1
            
            #newRaster = os.path.join(gdb, sdvTblName.replace("SDV", "Ras"))
            #newRaster = os.path.join(env.scratchFolder, "SoilRas_" + sdvTblName + "_" + bName + ".tif")
            #outRas.save(newRaster)

            
            #bMetadata = UpdateMetadata(gdb, newRaster, sdvLayer, description, iRaster)


            if arcpy.Exists(tmpRaster):
                # clean up any previous runs
                arcpy.Delete_management(tmpRaster)
                del tmpRaster


        # Create multiband raster
        for i in range(len(dRasters)):
        #for raster in sorted(dRasters):
            rasterList.append(dRasters[i])

        newRaster = os.path.join(gdb, "Ras_" + thePrefix)
        env.pyramid = "PYRAMIDS -1 NEAREST LZ77 # NO_SKIP"
        
        PrintMsg(" \n\tCreating new " + str(len(rasterList)) + " band raster: " + os.path.basename(newRaster) + " \n", 0)

        arcpy.CompositeBands_management(rasterList, newRaster)

        # Get description from last soil map layer
        description = dMetadata[sdvLayer]

        bMetadata = UpdateMetadata(gdb, newRaster, sdvLayer, description, iRaster, depthList)
        
            
        return True

    except MyError, e:
        PrintMsg(str(e) + " \n", 2)
        try:
            del thisMXD
        except:
            pass
        return False

    except:
        errorMsg()
        try:
            del thisMXD
        except:
            pass
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
        # Create a single table that contains
        #sdvLayers = arcpy.GetParameterAsText(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        sdvLayers = arcpy.GetParameter(0)           # 10.1 List of string values representing temporary SDV layers from ArcMap TOC
        inputRaster = arcpy.GetParameterAsText(1)    # gSSURGO raster that will be used to create individual rasters based upon selected attributes

        bRasters = CreateRasterLayers(sdvLayers, inputRaster)


except arcpy.ExecuteError:
    #arcpy.AddError(arcpy.GetMessages(2))
    errorMsg()

except MyError, e:
    # Example: raise MyError("this is an error message")
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()

