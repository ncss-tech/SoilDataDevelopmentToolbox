# Metadata_Testing.py
# Return FGDB metadata for a selected object (workspace, raster, featureclass, table)
# This version of the script has been modified to handle gSSURGO.

# TODO for gSSURGO:
#     1. Still needs to remove geoprocessing steps (compress, etc). Question, will these only exist in the 'Workspace' object?
#     2. For the raster, will need to read the xml file from the tool folder, edit and then write
#        to the description. Looks like the template Esri/CreaDate needs to be xxTODAYxx.
#     3. Pull survey Info from geodatabase


# Issues:  funny apostrophes, removing gp history, removing FGDC metadata, sort and reverse order of node removal
# Get rid of left and right quotes using  string.replace(chr(8216), "'").replace(chr(8217), "'")


# UUID types being returned by validation code
# workspace:    {C673FE0F-7280-404F-8532-20755DD8FC06}
# featureclass  {70737809-852C-4A03-9E22-2CECEA5B9BFA}
# FGDB raster:  {5ED667A3-9CA9-44A2-8029-D95BF23704B9}
# FGDB table:   {CD06BC3B-789D-4C51-AAFA-A467912B8965}

# Python minidom help: https://docs.python.org/2/library/xml.dom.html

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        #excInfo = sys.exc_info()
        #tb = excInfo[2]
        #e = sys.exc_info()[1]
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_traceback is not None:
            arcpy.AddError("Error: " + str(exc_type) + ". " + str(exc_value) +  " on line number " + str(exc_traceback.tb_lineno) )

        else:
             arcpy.AddError("Error: " + str(exc_type) + ". " + str(exc_value) )
                            
        #arcpy.AddError("Error 2." + str(exc_value))
        #arcpy.AddError("Error line number" + str(exc_traceback.tb_lineno))
                            
        #if hasattr(sys, 'exc_traceback'):
        #    (filename, line_number, function_name, text) = traceback.extract_tb(sys.exc_traceback)[-1]

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
def UpdateMetadata(midXML):
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

    # TO DO: Create function to generated list of concatenated areasymbols: saverest for xxSURVEYSxx replacement
    # TO DO: Pass in name of state
    try:

        d = datetime.date.today()
        today = str(d.isoformat().replace("-",""))

        # Set fiscal year according to the current month. If run during January thru September,
        # set it to the current calendar year. Otherwise set it to the next calendar year.
        #
        if d.month > 9:
            fy = "FY" + str(d.year + 1)

        else:
            fy = "FY" + str(d.year)

        mdState = "Kansas"
        surveyInfo = "KS183 (2018-09-12), KS147 (2018-09-12), KS163 (2018-09-12), KS141 (2018-09-12)"
       

        # Begin parsing input xml file

        doc = minidom.parseString(midXML)  # this works with an XML string from the database
        doc_root = doc.documentElement
        nodeList = doc.childNodes

        #if len(nodeList) == 1:
        #    PrintMsg(" \ndoc has 1 node named: " + nodeList[0].nodeName, 0)

        #else:
        #    PrintMsg(" \ndoc has " + str(len(nodeList)) + " nodes", 0)

        for node_0 in doc_root.childNodes:

            if node_0.nodeName in ["idinfo", "dataidinfo", "distinfo", "dataIdInfo", "dqinfo"]:
                # These nodes may contain metadata entries that require search-and-replace for 'xx' keywords
                #
                for node_1 in node_0.childNodes:
                    #indx += 1
                    #PrintMsg("\t*" + node_1.parentNode.localName + ": " + node_1.localName, 0)
                    #PrintMsg("\t*" + node_1.parentNode.nodeName + ": " + node_1.nodeName, 0)
                    
                    # S&R xxSTATExx, xxYEARxx, xxSSAxx and xxTODAYxx
                    #if node_1.nodeName in ["citation", "keywords", "descript", "timeperd", "datacred", "placeKeys", "searchKeys"]:
                    if 1 == 1:
                        for node_2 in node_1.childNodes:
                            if node_2.nodeType == node_2.TEXT_NODE:
                                # this node has text that can be searched
                                nodeText = node_2.nodeValue
                                
                                if not nodeText is None:
                                    nodeText = nodeText.replace("xxSTATExx", mdState).replace("xxTODAYxx", today).replace("xxFYxx", fy).replace("xxSURVEYSxx", surveyInfo)
                                    #PrintMsg(node_2.parentNode.nodeName + " node text: ", 0)
                                    #PrintMsg(nodeText, 1)
                                    node_2.replaceWholeText(nodeText)

                            else:
                                for node_3 in node_2.childNodes:
                                    if node_3.nodeType == node_3.TEXT_NODE:
                                        nodeText = node_3.nodeValue
                                        
                                        if not nodeText is None:
                                            nodeText = nodeText.replace("xxSTATExx", mdState).replace("xxTODAYxx", today).replace("xxFYxx", fy).replace("xxSURVEYSxx", surveyInfo)
                                            #PrintMsg(node_3.parentNode.nodeName + " node text: ", 0)
                                            #PrintMsg(nodeText, 1)
                                            node_3.replaceWholeText(nodeText)

                                    else:
                                        for node_4 in node_3.childNodes:
                                            if node_4.nodeType == node_4.TEXT_NODE:

                                                nodeText = node_4.nodeValue
                                                
                                                if not nodeText is None:
                                                    nodeText = nodeText.replace("xxSTATExx", mdState).replace("xxTODAYxx", today).replace("xxFYxx", fy).replace("xxSURVEYSxx", surveyInfo)
                                                    #PrintMsg(node_4.parentNode.nodeName + " node text: ", 0)
                                                    #PrintMsg(nodeText, 1)
                                                    node_4.replaceWholeText(nodeText)

                                            else:
                                                for node_5 in node_4.childNodes:
                                                    if node_5.nodeType == node_5.TEXT_NODE:

                                                        nodeText = node_5.nodeValue
                                                        
                                                        if not nodeText is None:
                                                            nodeText = nodeText.replace("xxSTATExx", mdState).replace("xxTODAYxx", today).replace("xxFYxx", fy).replace("xxSURVEYSxx", surveyInfo)
                                                            #PrintMsg(node_5.parentNode.nodeName + " node text: ", 0)
                                                            #PrintMsg(nodeText, 1)
                                                            node_5.replaceWholeText(nodeText)
                                                        
            elif node_0.nodeName == "Binary":
                # This node can contain a thumbnail xor an old copy of FGDC metadata
                #
                #PrintMsg("Handling " + node_0.nodeName, 1)
                rmNodes = list()  # keep a list of any node indexes that need to be removed
                indx = -1
                
                for node_1 in node_0.childNodes:
                    indx += 1
                    #PrintMsg("\t*" + node_0.nodeName + ": " + node_0.nodeName, 0)
                    
                    if node_1.nodeName == "Enclosure":
                        #PrintMsg("Found Enclosure node at index " + str(indx), 0)
                        rmNodes.append(indx)

                    #else:
                    #    PrintMsg("Instead found " + node_1.nodeName, 0)

                if len(rmNodes) > 0:
                    #PrintMsg(" \nrmNodes list: " + str(rmNodes), 1)
                    
                    for indx in sorted(rmNodes):
                        #PrintMsg("\t\tRemoving node " + str(indx), 1)
                        node_0.removeChild(node_0.childNodes[indx])

                                        
                
            elif node_0.nodeName == "Esri":
                # Geoprocessing history may be found here
                #
                #PrintMsg("Handling " + node_0.nodeName, 1)
                rmNodes = list()  # keep a list of any node indexes that need to be removed
                indx = -1
                
                for node_1 in node_0.childNodes:
                    indx += 1
                    #PrintMsg("\t*" + node_0.nodeName + ": " + node_1.nodeName, 0)
                    
                    if node_1.nodeName == "DataProperties":
                        #PrintMsg("\t\tFound DataProperties node at index " + str(indx), 0)
                        rmNodes.append(indx)

                    #else:
                    #    PrintMsg("Instead found " + node_1.nodeName, 0)                        

                if len(rmNodes) > 0:
                    #PrintMsg(" \nrmNodes list: " + str(rmNodes), 1)
                    
                    for indx in sorted(rmNodes):
                        #PrintMsg("\t\tRemoving DataPropertiesnode " + str(indx), 1)
                        node_0.removeChild(node_0.childNodes[indx])

            else:
                # dataqual  spdoinfo  eainfo  distinfo  metainfo  dataIdInfo  
                #PrintMsg("----", 0)
                #PrintMsg("Dropped down to node " + node_0.nodeName, 1)
                
                #for node_1 in node_0.childNodes:
                #    PrintMsg("\t*" + node_0.nodeName + ": " + node_1.nodeName, 0)
                pass

        docTxt = doc.toxml()
            
        return docTxt

    except MyError as err:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(err), 2)
        return ""

    except:
        errorMsg()
        return ""



## ===================================================================================
def FindTextNodes(pNode, nodeList2):
    # Walk down through all nodes, finding text nodes

    try:
        for subNode in nodeList2:
            if subNode.nodeType == subNode.ELEMENT_NODE:
                
                # recursive call to drop down to next level
                PrintMsg(" \nElement node: " + subNode.tagName + " with " + str(len(nodeList2)) + " children", 0)
                bNodes = FindTextNodes(subNode, subNode.childNodes)

            elif subNode.nodeType == subNode.TEXT_NODE:
                PrintMsg("-->Text node "+ str(pNode.localName) + ": " + str(subNode.nodeValue), 0)
                bNodes = FindTextNodes(subNode, subNode.childNodes)

            else:
                PrintMsg("-->Dropped through to " + pNode.localName + " of type " + str(subNode.nodeType), 0)

            return True
    
    except MyError as err:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(err), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
        
#from __future__ import print_function

import arcpy 
from arcpy import env
import os, sys, locale, traceback
from osgeo import ogr
from xml.dom import minidom

try:
    gdb_path = arcpy.GetParameterAsText(0)        # input file geodatabase
    objectNames = arcpy.GetParameter(1)      # input geodatabase, featureclass, raster or table
    outputFolder = arcpy.GetParameterAsText(2)    # folder where output xml file will be stored
    
    env.workspace = gdb_path
    tblName = "GDB_Items"

    #PrintMsg("\nFieldNames for " + tblName + ": " + ", ".join(fieldNames), 1)

    # Open file geodatabase and retrieve metadata for specified object

    # Print list of ogr drivers:
    cnt = ogr.GetDriverCount()
    driverList = list()
    
    for i in range(cnt):
        driver = ogr.GetDriver(i)
        driverName = driver.GetName()

        if not driverName in driverList:
            driverList.append(driverName)

    driverList.sort()
    PrintMsg(", ".join(driverList), 0)

    ds = ogr.Open(gdb_path)
    
    if ds is None:
        raise MyError("Failed to open " + gdb_path + " in write mode")

    for objectName in objectNames:
        fieldNames = [fld.name for fld in arcpy.Describe(tblName).fields]
        PrintMsg(" \nProcessing " + objectName + " in " +  gdb_path, 0)
        
        result = ds.ExecuteSQL("SELECT * FROM GDB_Items WHERE name = '" + objectName + "'")
        result.CommitTransaction()

        # Get record count in selection
        cnt = result.GetFeatureCount()
        #print("Record count for " + tblName + ": " + str(cnt))

        if cnt != 1:
            if cnt == 0:
                raise MyError("Nothing selected")

            else:
                raise MyError(str(cnt) + " records selected, should only be one")

        # Name of output xml file will be objectname + .xml
        outputXML = os.path.join(outputFolder, objectName + ".xml")
        
        if arcpy.Exists(outputXML):
            arcpy.Delete_management(outputXML)

        item = result.GetNextFeature()
            
        if item:
            nm = item.GetField('Name')
            tp = str(item.GetField("Type"))
            doc = item.GetField("Documentation").replace(chr(8216), "'").replace(chr(8217), "'") # this is a string object
            newdoc = UpdateMetadata(doc)
            item.SetField("Documentation", newdoc)
            #updateSQL = "UPDATE GDB_Items SET documentation = " + newdoc + " FROM GDB_Items ON name = '" + objectName + "'"

            if not doc == "":
                # Write xml to file
                fh1 = open(outputXML, 'w')
                fh1.write(str(newdoc))
                fh1.close()
                del fh1
                del item
                PrintMsg("--Exported ArcGIS metadata for " + nm + " to: " + outputXML + " \n", 0)

                # Try something dangerous. Use da cursor to write xml to Documentation column.
                # Total fail: data access cursor fails
                wc = "name = '" + nm +  "'"
                #PrintMsg(" \nQuerying " + tblName + " for " + wc, 0)
                
                #with arcpy.da.SearchCursor(os.path.join(gdb_path, tblName), ["name", "documentation"], where_clause=wc ) as cur:
                #    for rec in cur:
                #        name = rec[0]
                #        PrintMsg(" \nDocumentation value for name = " + name , 0)
                        #cur.updateRow([newdoc])
                    
            else:
                PrintMsg("--Unable to export ArcGIS metadata for " + nm, 1)
                
        result.ResetReading()
        ds.ReleaseResultSet(result)
        del result

    

except MyError as err:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(err), 2)
        
except:
    errorMsg()
    
