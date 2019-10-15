# AlexArcPy GitHub Gist
# Read file geodatabase domains with OGR without using arcpy and find what fields have assigned domains 


## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        excInfo = sys.exc_info()
        tb = excInfo[2]
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
                arcpy.AddError(" \n" + string)

    except:
        pass

## ===================================================================================
def UpdateMetadata(mdExport):
    #
    # Used for featureclass and geodatabase metadata. Does not do individual tables
    # Reads and edits the original metadata object and then exports the edited version
    # back to the featureclass or database.
    #
    try:

        # Parse exported XML metadata file
        #
        # Convert XML to tree format
        tree = ET.parse(mdExport)
        root = tree.getroot()

        mdState = "KY"
        lastDate = "2019-04-28"
        surveyInfo = "NE109"
        fy = "FY2019"

        # new citeInfo has title.text, edition.text, serinfo/issue.text
        citeInfo = root.findall('idinfo/citation/citeinfo/')

        if not citeInfo is None:
            # Process citation elements
            # title
            #
            # PrintMsg("citeInfo with " + str(len(citeInfo)) + " elements : " + str(citeInfo), 1)
            for child in citeInfo:
                PrintMsg("\t\t" + str(child.tag), 0)
                if child.tag == "title":
                    if child.text.find('xxSTATExx') >= 0:
                        child.text = child.text.replace('xxSTATExx', mdState)

                    elif mdState != "":
                        child.text = child.text + " - " + mdState

                elif child.tag == "edition":
                    if child.text == 'xxFYxx':
                        child.text = fy

                elif child.tag == "serinfo":
                    for subchild in child.iter('issue'):
                        if subchild.text == "xxFYxx":
                            subchild.text = fy

        # Update place keywords
        PrintMsg("\t\tplace keywords", 0)
        ePlace = root.find('idinfo/keywords/place')

        for child in ePlace.iter('placekey'):
            if child.text == "xxSTATExx":
                child.text = mdState

            elif child.text == "xxSURVEYSxx":
                child.text = surveyInfo

        # Update credits
        eIdInfo = root.find('idinfo')
        PrintMsg("\t\tcredits", 0)

        for child in eIdInfo.iter('datacred'):
            sCreds = child.text

            if sCreds.find("xxSTATExx") >= 0:
                PrintMsg("\t\tcredits " + mdState, 0)
                child.text = child.text.replace("xxSTATExx", mdState)

            if sCreds.find("xxFYxx") >= 0:
                PrintMsg("\t\tcredits " + fy, 0)
                child.text = child.text.replace("xxFYxx", fy)

            if sCreds.find("xxTODAYxx") >= 0:
                PrintMsg("\t\tcredits " + today, 0)
                child.text = child.text.replace("xxTODAYxx", lastDate)

        idPurpose = root.find('idinfo/descript/purpose')
        if not idPurpose is None:
            ip = idPurpose.text
            PrintMsg("\tip: " + ip, 1)
            if ip.find("xxFYxx") >= 0:
                PrintMsg("\t\tip", 1)
                idPurpose.text = ip.replace("xxFYxx", fy)

        procDates = root.find('dataqual/lineage')
        if not procDates is None:
            PrintMsg(" \nUpdating process step dates", 1)
            for child in procDates.iter('procdate'):

                sDate = child.text
                PrintMsg("\tFound process date: " + sDate, 1)
                if sDate.find('xxTODAYxx'):
                    PrintMsg("\tReplacing process date: " + sDate + " with " + lastDate, 1)
                    child.text = lastDate

        else:
            PrintMsg("\nNo find process date", 1)


        #  create new xml file which will be imported, thereby updating the table's metadata
        #tree.write(mdImport, encoding="utf-8", xml_declaration=None, default_namespace=None, method="xml")



        return True

    except:
        errorMsg()
        False

## ===================================================================================
def UpdateMetadata_ISO(outputWS, target, surveyInfo, description):
    # Adapted from MapunitRaster metadata function
    #
    # old function args: outputWS, target, surveyInfo, description
    #
    # Update and import the ISO 19139 metadata for the Map Unit Raster layer
    # Since the raster layer is created from scratch rather than from an
    # XML Workspace Document, the metadata must be imported from an XML metadata
    # file named 'gSSURGO_MapunitRaster.xml
    # Search nodevalues and replace keywords: xxSTATExx, xxSURVEYSxx, xxTODAYxx, xxFYxx
    #
    # Note: for existing featureclasses, this function would have to be modified to first
    # export their metadata to a temporary xml file, updated and saved to a new, temporary
    # xml file and then imported back to the featureclass.
    #
    try:
        #import xml.etree.cElementTree as ET
        PrintMsg("\t" + os.path.basename(target), 0)

        # Identify the raster template metadata file stored with the Python scripts
        #xmlPath = os.path.dirname(sys.argv[0])

        inputXML = os.path.join(env.scratchFolder, "xxOldMetadata.xml")       # original metadata from target
        midXML = os.path.join(env.scratchFolder, "xxMidMetadata.xml")         # intermediate xml
        outputXML = os.path.join(env.scratchFolder, "xxUpdatedMetadata.xml")  # updated metadata xml
        #inputXML = os.path.join(env.scratchFolder, "in_" + os.path.basename(target).replace(".", "") + ".xml")
        #outputXML = os.path.join(env.scratchFolder, "out_" + os.path.basename(target).replace(".", "") + ".xml")

        # Export original metadata from target
        #
        # Set ISO metadata translator file
        # C:\Program Files (x86)\ArcGIS\Desktop10.1\Metadata\Translator\ARCGIS2ISO19139.xml
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        #prod = r"Metadata/Translator/ARCGIS2ISO19139.xml"
        #prod = r"Metadata/Translator/ESRI_ISO2ISO19139.xml"
        prod = r"Metadata/Translator/ISO19139_2ESRI_ISO.xml"
        mdTranslator = os.path.join(installPath, prod)

        # Cleanup XML files from previous runs
        if os.path.isfile(inputXML):
            os.remove(inputXML)

        if os.path.isfile(midXML):
            os.remove(midXML)

        if os.path.isfile(outputXML):
            os.remove(outputXML)

        # initial metadata export is not ISO
        arcpy.ExportMetadata_conversion (target, mdTranslator, inputXML)

        # second export creates ISO metatadata
        prod = r"Metadata/Translator/ESRI_ISO2ISO19139.xml"
        mdTranslator = os.path.join(installPath, prod)
        #arcpy.ExportMetadata_conversion (target, mdTranslator, midXML)
        arcpy.ESRITranslator_conversion(inputXML, mdTranslator, midXML)


        # Try to get the statename by parsing the gSSURGO geodatabase name.
        # If the standard naming convention was not followed, the results
        # will be unpredictable
        #
        stDict = StateNames()
        st = os.path.basename(outputWS)[8:-4]

        if st in stDict:
            mdState = stDict[st]

        else:
            mdState = description

        #mdTitle = "Map Unit Raster " + str(iRaster) + "m - " + mdState

        # Set date strings for metadata, based upon today's date
        #
        d = datetime.date.today()
        today = str(d.isoformat().replace("-",""))

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        # Begin parsing input xml file
        doc = minidom.parse(midXML)

        # TITLE
        nodeValue = 'title'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if not node.firstChild is None:
                            if node.firstChild.nodeValue.find("xxSTATExx") >= 0:
                                PrintMsg("\t\tFound " + nodeValue + ": " + node.firstChild.nodeValue, 1)
                                #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                                title = node.firstChild.nodeValue.replace("xxSTATExx", mdState)
                                node.firstChild.nodeValue = title
                                PrintMsg("\t\t" + node.firstChild.nodeValue)

        # KEYWORDS
        nodeValue = 'keyword'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxSTATExx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = mdState
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

                        elif node.firstChild.nodeValue.find("xxSURVEYSxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = surveyInfo
                            PrintMsg("\t\t" + node.firstChild.nodeValue)


        # DATETIME
        nodeValue = 'dateTime'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "DateTime":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound datetime.DateTime: " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today + "T00:00:00"
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # DATESTAMP
        nodeValue = 'dateStamp'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "Date":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # DATE
        nodeValue = 'date'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "Date":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = today
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # CREDITS
        nodeValue = 'credit'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\tCredit: " + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxTODAYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            newCredit = node.firstChild.nodeValue
                            newCredit = newCredit.replace("xxTODAYxx", today).replace("xxFYxx", fy)
                            node.firstChild.nodeValue = newCredit
                            PrintMsg("\t\t" + node.firstChild.nodeValue)
                            #PrintMsg("\tEdited: " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 0)

        # FISCAL YEAR
        nodeValue = 'edition'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxFYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = fy
                            PrintMsg("\t\t" + node.firstChild.nodeValue)

        # ISSUE IDENTIFICATION
        nodeValue = 'issueIdentification'

        for elem in doc.getElementsByTagName(nodeValue):
            for node in elem.childNodes:
                #PrintMsg("\t\t" + str(node.ELEMENT_NODE) + " : " + str(node.localName), 1)

                if node.nodeType == node.ELEMENT_NODE:
                    if node.localName == "CharacterString":
                        if node.firstChild.nodeValue.find("xxFYxx") >= 0:
                            PrintMsg("\t\tFound " + str(nodeValue) + ": " + str(node.firstChild.nodeValue), 1)  # state value
                            #PrintMsg("\tFound " + nodeValue + " node: " + node.localName)
                            node.firstChild.nodeValue = fy
                            PrintMsg("\t\t" + node.firstChild.nodeValue)


        # Begin writing new metadata to a temporary xml file which can be imported back to ArcGIS
        newdoc = doc.toxml("utf-8")
        # PrintMsg(" \n" + newdoc + " \n ", 1)

        fh = open(outputXML, "w")
        fh.write(newdoc)
        fh.close()

        # import updated metadata to the geodatabase table
        #PrintMsg("\tSkipping metatdata import \n ", 1)
        #arcpy.ImportMetadata_conversion(outputXML, "FROM_ISO_19139", outputRaster, "DISABLED")
        arcpy.MetadataImporter_conversion (outputXML, target)

        # delete the temporary xml metadata files
        #os.remove(outputXML)
        #os.remove(inputXML)
        #if os.path.isfile(midXML):
        #    os.remove(midXML)


    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)

    except:
        errorMsg()


from __future__ import print_function
import json
import xml.etree.ElementTree as ET
import ogr

gdb_path = r'C:\GIS\data\Adv.gdb'
ds = ogr.Open(gdb_path)
res = ds.ExecuteSQL('select * from GDB_Items')
res.CommitTransaction()

for i in xrange(0, res.GetFeatureCount()):
    item = json.loads(
        res.GetNextFeature().ExportToJson())['properties']['Definition']
    if item:
        xml = ET.fromstring(item)
        if xml.tag == 'DEFeatureClassInfo' and xml.find('Name').text == 'Fc1':
            field_infos = xml.find('GPFieldInfoExs')

            for field in field_infos.getchildren():
                domain = field.find('DomainName').text if field.find('DomainName') is not None else ''
                print(field.find('Name').text, '<-', domain)
                
# OBJECTID <- 
# SHAPE <- 
# Field5 <- Domain1
# Field6 <- 
# SHAPE_Length <- 
# SHAPE_Area <-   

from arcpy import env
import os, sys
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import ogr

gdb_path = r"C:\Geodata\ArcGIS_Home\gSSURGO_KS.gdb"
env.workspace = gdb_path
tblName = "GDB_Items"
fieldNames = [fld.name for fld in arcpy.Describe(tblName).fields]
print("FieldNames for " + tblName + ": " + ", ".join(fieldNames) )

ds = ogr.Open(gdb_path)
result = ds.ExecuteSQL('select * from GDB_Items')
result.CommitTransaction()
cnt = result.GetFeatureCount()
print("Record count for " + tblName + ": " + str(cnt))
xmlFile = r"c:\temp\xxTest.xml"

if arcpy.Exists(xmlFile):
    arcpy.Delete_management(xmlFile)

fh = open(xmlFile, "a")

# Usually first item is 'Workspace'

for i in range(0, cnt):
    item = result.GetNextFeature()
    if item:
        nm = item.GetField('Name')
        tp = str(item.GetField("Type"))
        
        #if tp.startswith('{C673FE0F-7280-404F-8532-20755DD8FC06}') or tp.startswith('{CD06BC3B-789D-4C51-AAFA-A467912B8965}'):
        if tp.startswith('{C673FE0F-7280-404F-8532-20755DD8FC06}'):
            desc = item.GetField("Documentation")
            xml = ET.fromstring(desc)
            #fh.write(str(xml))
            print(nm)
            for

result.ResetReading()
fh.close()


gdbFields = """		
Workspace
chaashto
chconsistence
chdesgnsuffix
chfrags
chorizon
chpores
chstruct
chstructgrp
chtext
chtexture
chtexturegrp
chtexturemod
chunified
cocanopycover
cocropyld
codiagfeatures
coecoclass
coeplants
coerosionacc
coforprod
coforprodo
cogeomordesc
cohydriccriteria
cointerp
comonth
component
copm
copmgrp
copwindbreak
corestrictions
cosoilmoist
cosoiltemp
cosurffrags
cosurfmorphgc
cosurfmorphhpp
cosurfmorphmr
cosurfmorphss
cotaxfmmin
cotaxmoistcl
cotext
cotreestomng
cotxfmother
distinterpmd
distlegendmd
distmd
featdesc
laoverlap
legend
legendtext
mapunit
month
muaggatt
muaoverlap
mucropyld
mutext
sacatalog
sainterp
sdvalgorithm
sdvattribute
sdvfolder
sdvfolderattribute
mdstatdomdet
mdstatdommas
mdstatidxdet
mdstatidxmas
mdstatrshipdet
mdstatrshipmas
mdstattabcols
mdstattabs
MUPOLYGON
FEATLINE
FEATPOINT
MULINE
SAPOLYGON
MUPOINT
zSdvattribute_Sdvfolderattribute
zSdvfolder_Sdvfolderattribute
zChaashto_Chorizon
zChconsistence_Chorizon
zChdesgnsuffix_Chorizon
zChfrags_Chorizon
zChpores_Chorizon
zChstructgrp_Chorizon
zChtext_Chorizon
zChtexturegrp_Chorizon
zChunified_Chorizon
zChstruct_Chstructgrp
zChtexturemod_Chtexture
zChtexture_Chtexturegrp
zCoforprodo_Coforprod
zCosurfmorphgc_Cogeomordesc
zCosurfmorphhpp_Cogeomordesc
zCosurfmorphmr_Cogeomordesc
zCosurfmorphss_Cogeomordesc
zCosoilmoist_Comonth
zCosoiltemp_Comonth
zChorizon_Component
zCocanopycover_Component
zCocropyld_Component
zCodiagfeatures_Component
zCoecoclass_Component
zCoeplants_Component
zCoerosionacc_Component
zCoforprod_Component
zCogeomordesc_Component
zCohydriccriteria_Component
zCointerp_Component
zComonth_Component
zCopmgrp_Component
zCopwindbreak_Component
zCorestrictions_Component
zCosurffrags_Component
zCotaxfmmin_Component
zCotaxmoistcl_Component
zCotext_Component
zCotreestomng_Component
zCotxfmother_Component
zCopm_Copmgrp
zDistinterpmd_Distmd
zDistlegendmd_Distmd
zMuaoverlap_Laoverlap
zLaoverlap_Legend
zLegendtext_Legend
zMapunit_Legend
zComponent_Mapunit
zMuaggatt_Mapunit
zMuaoverlap_Mapunit
zMucropyld_Mapunit
zMutext_Mapunit
zMdstatdomdet_Mdstatdommas
zMdstattabcols_Mdstatdommas
zMdstatidxdet_Mdstatidxmas
zMdstatrshipdet_Mdstatrshipmas
zMdstatidxmas_Mdstattabs
zMdstatrshipmas_Mdstattabs
zMdstattabcols_Mdstattabs
zSainterp_Sacatalog
zSdvfolderattribute_Sdvattribute
zSdvfolderattribute_Sdvfolder
zMUPOLYGON_Mapunit
zMUPOLYGON_Muaggatt
zSAPOLYGON_Legend
zMULINE_Mapunit
zMUPOINT_Mapunit
zFEATLINE_Featdesc
zFEATPOINT_Featdesc
MapunitRaster_10m
Valu1
Co_VALU
SDV_Data
SDV_NCCPI_WTA
