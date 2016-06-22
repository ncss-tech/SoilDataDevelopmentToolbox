# SDV_AttributeReport.py
#
# Steve Peaslee, USDA-NRCS
# 2015-10-07
#
# Uses 'sdv' tables to generate an outline of the SDV interps and soil properties
# stored in the selected database.
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
import os, sys, traceback, arcpy
from arcpy import env

try:

    thePath = arcpy.GetParameterAsText(0) # input database
    bNational = arcpy.GetParameter(1)      # report only National Interps? boolean

    PrintMsg(" \nGenerating list of soil properties and interpretations available in " + os.path.basename(thePath), 0)

    # next find out if this is a workspace or a featuredataset
    desc = arcpy.Describe(thePath)
    theDataType = desc.dataType

    # get the workspace
    if theDataType.upper() != "WORKSPACE":
        # try going up one more level in the path to get the geodatabase
        thePath = os.path.dirname(thePath)

    # Define tables used to populate choice lists
    #if not self.params[0].hasBeenValidated:
    sdvFolder = os.path.join(thePath, "sdvfolder")
    sdvFolderAtt = os.path.join(thePath, "sdvfolderattribute")
    sdvAtt = os.path.join(thePath, "sdvattribute")
    legend = os.path.join(thePath, "legend")
    folderList = list()
    dFolder = dict()
    flds1 = ["foldername", "folderkey", "foldersequence"]
    sClause = [None, "ORDER BY FOLDERSEQUENCE"]
    stateList = list()

    if bNational:
        # only report national interps by identifying the sdvattributes that end in (ST)
        flds0 = ["areasymbol"]

        with arcpy.da.SearchCursor(legend, flds0) as lCur:
            for rec in lCur:
                st = rec[0][0:2]
                if not st in stateList:
                    stateList.append(st)
                    #PrintMsg("\tAdding '" + st + "' to state abbreviation list", 1)

    #PrintMsg(" \n\tReading SDVFOLDER table...", 1)

    with arcpy.da.SearchCursor(sdvFolder, flds1, sql_clause=sClause) as fCur:
        for rec in fCur:
            # populate list of sdvfolder names
            # save folder key for later use in query. ?Should I keep all folder keys?
            if not rec[0] in folderList:
                folderList.append(rec[0])  # folder name
                dFolder[rec[0]] = rec[1]   # save key value for each folder

    # Print attributes or interps for each folder
    for folderName in folderList:
        # Get attributekey from sdvfolderattribute table
        # folderkey, attributekey
        #folderName = self.params[1].value
        folderKey = dFolder[folderName]
        flds2 = ["attributekey"]
        sql1 = "folderkey = " + str(folderKey)
        attKeys = list()
        attList = list()

        #PrintMsg(" \n" + folderName, 0)

        with arcpy.da.SearchCursor(sdvFolderAtt, flds2, where_clause=sql1 ) as kCur:
            for rec in kCur:
                # populate list of sdvfolder names
                # save folder key for later use in query
                attKeys.append(str(rec[0]))

        if len(attKeys) > 0:
            flds3 = ["attributename", "attributelogicaldatatype", "algorithmname"]
            sql2 = "attributekey in (" + ",".join(attKeys) + ")"


            with arcpy.da.SearchCursor(sdvAtt, flds3, where_clause=sql2) as aCur:
                for rec in aCur:
                    # populate list of sdv attribute names
                    att = str(rec[0])
                    if not att in attList:

                        if bNational:
                            end = att[-4:]

                            if not ((end.startswith("(") and end.endswith(")")) and end[1:3] in stateList):
                                #PrintMsg("\t" + str(rec[0]), 0)
                                attList.append(att)           # accumulate sdv attribute names

                        else:
                            #PrintMsg("\t" + att, 0)
                            attList.append(str(rec[0]))           # accumulate sdv attribute names

            if len(attList) > 0:
                PrintMsg(" \n" + folderName, 0)
                attList.sort()
                for att in attList:
                    PrintMsg("\t" + att, 0)
                    pass


    PrintMsg(" \nProcess complete", 0)

except:
  errorMsg()
