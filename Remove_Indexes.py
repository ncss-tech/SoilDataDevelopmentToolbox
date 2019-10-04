
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
        #locale.setlocale(locale.LC_ALL, "")
        if bCommas:
            theNumber = locale.format("%.*f", (places, num), True)

        else:
            theNumber = locale.format("%.*f", (places, num), False)
        return theNumber

    except:
        errorMsg()
        return False

## ===================================================================================
# Main

try:
    # Remove all attribute indexes and relationshipclasses from a geodatabase
    # Might not work when a featuredataset is present
    import arcpy, os, sys

    db = arcpy.GetParameterAsText(0)  # input geodatabase

    from arcpy import env

    env.workspace = db

    PrintMsg(" \nRemoving indexes and relationshipclasses from " + os.path.basename(db), 0)

    # Process standalone tables first
    tblList = arcpy.ListTables()

    PrintMsg(" \nProcessing " + str(len(tblList)) + " tables", 0)
    tbl = ""
    arcpy.SetProgressor("step", "Removing indexes for " + tbl, 0, len(tblList), 1)
             
    for tbl in tblList:
        arcpy.SetProgressorLabel("Removing indexes for " + tbl)
        arcpy.SetProgressorPosition()
        
        indxList = arcpy.ListIndexes(tbl)
        for indx in indxList:
            # assuming only one field per index
            fldList = indx.fields
            if fldList[0].name != "OBJECTID":
                arcpy.RemoveIndex_management(tbl, indx.name)
                #print tbl + ", " + indx.name + ", " + fldList[0].name

            # remove relationshipclasses after indexes are gone
            rcs = arcpy.Describe(tbl).relationshipClassNames
            for rc in rcs:
                arcpy.Delete_management(rc)
                
            
    # Process featureclasses next
    fcList = arcpy.ListFeatureClasses()

    PrintMsg(" \nProcessing " + str(len(fcList)) + " featureclasses", 0)
    tbl = ""
    arcpy.SetProgressor("step", "Removing indexes for " + tbl, 0, len(fcList), 1)

    for tbl in fcList:
                                 
        arcpy.SetProgressorPosition()
        indxList = arcpy.ListIndexes(tbl)
        
        for indx in indxList:
            # assuming only one field per index
            fldList = indx.fields
            if not fldList[0].name in ("Shape", "OBJECTID"):
                #print tbl + ", " + indx.name + ", " + fldList[0].name
                if arcpy.Exists(indx.name):  # Having problems removing some indexes the first time through
                    arcpy.RemoveIndex_management(tbl, indx.name)

            # remove relationshipclasses after indexes are gone
            rcs = arcpy.Describe(tbl).relationshipClassNames
            for rc in rcs:
                arcpy.Delete_management(rc)

    PrintMsg(" \n", 0)
    
except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e) + " \n", 2)

except:
    errorMsg()
 
