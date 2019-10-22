
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

# ***********************************************************************
def RemoveHistory(myWorkspace, gp_history_xslt, output_dir):
##Removes GP History for feature dataset stored feature classes, and feature classes in the File Geodatabase.
    try:
        arcpy.env.workspace = myWorkspace
        
        for fds in arcpy.ListDatasets('','feature') + ['']:
            for fc in arcpy.ListFeatureClasses('','',fds):
                data_path = os.path.join(myWorkspace, fds, fc)
                if isNotSpatialView(myWorkspace, fc):
                    if removeAll(data_path, fc, gp_history_xslt, output_dir):
                        pass

                    else:
                        raise MyError, "Failed to remove geoprocessing history for " + fc

        # finally, remove geodatabase history..
        datapath = myWorkspace

        if removeAll(data_path, "geodatabase", gp_history_xslt, output_dir):
            pass

        else:
            raise MyError, "Failed to remove geoprocessing history for " + myWorkspace

        
    except:
        errorMsg()

# ***********************************************************************
def isNotSpatialView(myWorkspace, fc):
    ##Determines if the item is a spatial view and if so returns True to listFcsInGDB()
    try:
        if db_type <> "":
            desc = arcpy.Describe(fc)
            fcName = desc.name
            #Connect to the GDB
            egdb_conn = arcpy.ArcSDESQLExecute(myWorkspace)
            
            #Execute SQL against the view table for the specified RDBMS
            if db_type == "SQL":
                db, schema, tableName = fcName.split(".")
                sql = r"IF EXISTS(select * FROM sys.views where name = '{0}') SELECT 1 ELSE SELECT 0".format(tableName)
            elif db_type == "Oracle":
                schema, tableName = fcName.split(".")
                sql = r"SELECT count(*) from dual where exists (select * from user_views where view_name = '{0}')".format(tableName)
                egdb_return = egdb_conn.execute(sql)
                if egdb_return == 0:
                    return True
                else:
                    return False
            else:
                return True
        else:
            return True

    except:
        errorMsg()
        return False
    
# ***********************************************************************
def removeAll(data_path, feature, gp_history_xslt, output_dir):
    ##Remove all GP History metadata from a feature class.

    try:
        arcpy.ClearWorkspaceCache_management()
        name_xml = os.path.join(output_dir, str(feature)) + ".xml"
        
        if arcpy.Exists(name_xml):
            arcpy.Delete_management(name_xml)

        arcpy.XSLTransform_conversion(data_path, gp_history_xslt, name_xml)

        arcpy.MetadataImporter_conversion(name_xml, data_path)
        PrintMsg(" \n\tCleared history for " + feature, 0)

        if arcpy.Exists(name_xml):
            arcpy.Delete_management(name_xml)
            
        return True

    except:
        errorMsg()
        return False
               
# ***********************************************************************
def makeDirectory(output_dir):
    ##Creates directory to store the xml tables of converted metadata. If the
    ##directory already exists, the files will be created there.

    try:
        if not arcpy.Exists(output_dir):
            os.mkdir(output_dir)

        return True

    except:
        errorMsg()
        return False

# ***********************************************************************
# main

try:
    import arcpy
    import os, sys, string, locale, traceback
    from arcpy import env

    myWorkspace = arcpy.GetParameterAsText(0)

    ''' Update the following five variables before running the script.'''
    #version = "10.6"
    #dInstall = arcpy.GetInstallInfo()
    #arcgisPath = dInstall["InstallDir"]
    #gp_history_xslt = r"C:\Program Files (x86)\ArcGIS\Desktop10.7\Metadata\Stylesheets\gpTools\remove geoprocessing history.xslt".format(version)
    gp_history_xslt = os.path.join(os.path.dirname(sys.argv[0]), "remove geoprocessing history.xslt")
    #gp_history_xslt = os.path.join(arcgisPath, r"Metadata\Stylesheets\gpTools\remove geoprocessing history.xslt") # missing at 10.7.1

    output_dir = env.scratchFolder
    db_type = "" #Set this to either "SQL" or "Oracle" if your db has spatial views. If not you may set it to "".


    if makeDirectory(output_dir):
        RemoveHistory(myWorkspace, gp_history_xslt, output_dir)

    PrintMsg(" \nClear geoprocessing finished for " + os.path.basename(myWorkspace), 0)

except:
    errorMsg()
    
