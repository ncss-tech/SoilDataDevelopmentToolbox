# Create_SQLiteDB.py

# using a template gSSURGO database to create an SQLite database
#
# ArcGIS 10.5 - 10.6
#
# Steve Peaslee, National Soil Survey Center, Lincoln, Nebraska
#
# To do:
#
#    1. Compare the performace and behavior of sqlite3-CREATE TABLE vs. arcpy.CreateTable_management
#    2. Question. Can I add addional columns to a table created using sqlite3??
#    3. Do I need to add indexes on mukey to the rating tables?

# 2019-03-25 Problem with Geopackage. For some reason my tables aren't
# being recognized by ArcGIS anymore (used to work I think).


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
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

## ===============================================================================================================
def GetTableKeys(templateDB):
    #
    # Retrieve physical and alias names from mdstatidxdet table and assigns them to a blank dictionary.
    # tabphyname, idxphyname, idxcolsequence, colphyname
    # indxphyname prefixes: PK_, DI_

    try:
        tableKeys = dict()  # key = table name, values are a list containing [primaryKey, foreignKey]

        # Open mdstattabs table containing information for other SSURGO tables
        theMDTable = "mdstatidxdet"
        env.workspace = templateDB

        # Get primary and foreign keys for each table using mdstatidxdet table.
        #
        if arcpy.Exists(os.path.join(templateDB, theMDTable)):

            fldNames = ["tabphyname", "idxphyname", "colphyname"]
            wc = "idxphyname NOT LIKE 'UC_%'"
            #wc = ""

            with arcpy.da.SearchCursor(os.path.join(templateDB, theMDTable), fldNames, wc) as rows:

                for row in rows:
                    # read each table record and assign 'tabphyname' and 'tablabel' to 2 variables
                    tblName, indexName, columnName = row
                    #PrintMsg(str(row), 1)

                    if indexName[0:3] == "PK_":
                        # primary key
                        if tblName in tableKeys:
                            tableKeys[tblName][0] = columnName

                        else:
                            tableKeys[tblName] = [columnName, None]

                    elif indexName[0:3] == "DI_":
                        # foreign key
                        if tblName in tableKeys:
                            tableKeys[tblName][1] = columnName

                        else:
                            tableKeys[tblName] = [None, columnName]

            del theMDTable

            return tableKeys

        else:
            # The mdstattabs table was not found
            raise MyError, "Missing mdstattabs table"
            return dict()

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()


## ===================================================================================
def CreateTables(newDB, templateDB, databaseType):
    # Modified this function to use sqlite3 commands to CREATE TABLE
    #
    # ISO-8601 date/time string in the form YYYY-MM-DDTHH:MM:SS.SSSZ with T separator character
    # and Z suffix for coordinated universal time (UTC) encoded in either UTF-8 or UTF-16.
    # See TEXT. Stored as SQLite TEXT.
    #
    # Problem with Geopackage option using SQL and sqlite3 commands in Python. Tables aren't recognized by ArcGIS.

    #
    try:

        notes = """
>>> from arcpy import env
>>> db = r"G:\SpatialLite\Empty_CrTbl9.sqlite"
>>> import sqlite3
>>> conn = sqlite3.connect(db)
>>> conn.enable_load_extension(True)
>>> ex = "stgeometry_sqlite"
>>> conn.load_extension(ex)
        """

        addGeom = """
SELECT AddGeometryColumn(
 null,
'mupolygon',
'Shape',
4326,
'polygon',
'xy',
'null'
);
        """
        # Geopackage URL
        # http://www.geopackage.org/spec/

        # This method uses an empty geopackage that I downloaded
        # emptyDB = os.path.join(os.path.dirname(sys.argv[0]), "empty.gpkg")
        # shutil.copy2(emptyDB, newDB)

        # This method uses the ArcGIS CreateSQLiteDatabase method
        #if databaseType == "GEOPACKAGE_X":
        #    # Try using downloaded geopackage instead of 'CreateSQLiteDatabase' command
        #    emptyDB = os.path.join(os.path.dirname(sys.argv[0]), "empty.gpkg")
        #    PrintMsg(" \nUsing " + emptyDB + " to create database", 1)
        #    shutil.copy2(emptyDB, newDB)
        #
        #else:
        #    arcpy.CreateSQLiteDatabase_management(newDB, databaseType)

        # Try creating in-memory table as a template for sqlite database.
        # Will need to add something else for featureclasses.
        arcpy.CreateSQLiteDatabase_management(newDB, databaseType)

        # Create featureclasses
        tblList = ['mupolygon', 'sapolygon', 'featline', 'featpoint', 'muline', 'mupoint']

        for fcName in tblList:
            wc = ""
            arcpy.SetProgressorLabel("Creating featureclass " + fcName)
            template = os.path.join(templateDB, fcName)
            fms = arcpy.FieldMappings()
            fms.addTable(template)
            # Remove two unecessary shape fields
            fldIndx = fms.findFieldMapIndex("Shape_Area")

            if fldIndx >= 0:
                fms.removeFieldMap(fms.findFieldMapIndex("Shape_Area"))

            fldIndx = fms.findFieldMapIndex("Shape_Length")
            if fldIndx >= 0:
                fms.removeFieldMap(fms.findFieldMapIndex("Shape_Length"))
                
            mFC = arcpy.FeatureClassToFeatureClass_conversion(template, newDB, fcName.upper(), wc, fms)


        # Create tables
        tblList = ['month', 'mdstatdomdet', 'mdstatdommas', 'mdstatidxdet', 'mdstatidxmas', \
                   'mdstatrshipdet', 'mdstatrshipmas', 'mdstattabcols', 'mdstattabs', \
                   'distmd', 'legend', 'distinterpmd', 'distlegendmd', 'laoverlap', \
                   'legendtext', 'mapunit', 'component', 'muaggatt', 'muaoverlap', 'mucropyld', \
                   'mutext', 'chorizon', 'cocanopycover', 'cocropyld', 'codiagfeatures', \
                   'coecoclass', 'coeplants', 'coerosionacc', 'coforprod', 'cogeomordesc', \
                   'cohydriccriteria', 'cointerp', 'comonth', 'copmgrp', 'copwindbreak', \
                   'corestrictions', 'cosurffrags', 'cotaxfmmin', 'cotaxmoistcl', 'cotext', \
                   'cotreestomng', 'cotxfmother', 'chaashto', 'chconsistence', 'chdesgnsuffix', \
                   'chfrags', 'chpores', 'chstructgrp', 'chtext', 'chtexturegrp', 'chunified', \
                   'coforprodo', 'copm', 'cosoilmoist', 'cosoiltemp', 'cosurfmorphgc', 'cosurfmorphhpp', \
                   'cosurfmorphmr', 'cosurfmorphss', 'chstruct', 'chtexture', 'chtexturemod', \
                   'sacatalog', 'sainterp', 'sdvalgorithm', 'sdvattribute', 'sdvfolder', \
                   'sdvfolderattribute', 'featdesc']
        
        
        for tblName in tblList:
            arcpy.SetProgressorLabel("Creating table " + tblName)
            template = os.path.join(templateDB, tblName)
            mTbl = arcpy.CreateTable_management("IN_MEMORY", tblName, template)
            arcpy.Copy_management(mTbl, os.path.join(newDB, tblName))
                                  


        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateTables_SQL(newDB, templateDB, databaseType):
    # Modified this function to use sqlite3 commands to CREATE TABLE
    #
    # ISO-8601 date/time string in the form YYYY-MM-DDTHH:MM:SS.SSSZ with T separator character
    # and Z suffix for coordinated universal time (UTC) encoded in either UTF-8 or UTF-16.
    # See TEXT. Stored as SQLite TEXT.
    #
    # Problem with Geopackage option using SQL and sqlite3 commands in Python. Tables aren't recognized by ArcGIS.

    #
    try:

        notes = """
>>> from arcpy import env
>>> db = r"G:\SpatialLite\Empty_CrTbl9.sqlite"
>>> import sqlite3
>>> conn = sqlite3.connect(db)
>>> conn.enable_load_extension(True)
>>> ex = "stgeometry_sqlite"
>>> conn.load_extension(ex)
        """

        addGeom = """
SELECT AddGeometryColumn(
 null,
'mupolygon',
'Shape',
4326,
'polygon',
'xy',
'null'
);
        """
        # Geopackage URL
        # http://www.geopackage.org/spec/

        # This method uses an empty geopackage that I downloaded
        # emptyDB = os.path.join(os.path.dirname(sys.argv[0]), "empty.gpkg")
        # shutil.copy2(emptyDB, newDB)

        # This method uses the ArcGIS CreateSQLiteDatabase method
        #if databaseType == "GEOPACKAGE_X":
        #    # Try using downloaded geopackage instead of 'CreateSQLiteDatabase' command
        #    emptyDB = os.path.join(os.path.dirname(sys.argv[0]), "empty.gpkg")
        #    PrintMsg(" \nUsing " + emptyDB + " to create database", 1)
        #    shutil.copy2(emptyDB, newDB)
        #
        #else:
        #    arcpy.CreateSQLiteDatabase_management(newDB, databaseType)

        arcpy.CreateSQLiteDatabase_management(newDB, databaseType)
        
        tblList = ['mupolygon', 'sapolygon', 'featline', 'featpoint', 'muline', 'mupoint', \
                   'month', 'mdstatdomdet', 'mdstatdommas', 'mdstatidxdet', 'mdstatidxmas', \
                   'mdstatrshipdet', 'mdstatrshipmas', 'mdstattabcols', 'mdstattabs', \
                   'distmd', 'legend', 'distinterpmd', 'distlegendmd', 'laoverlap', \
                   'legendtext', 'mapunit', 'component', 'muaggatt', 'muaoverlap', 'mucropyld', \
                   'mutext', 'chorizon', 'cocanopycover', 'cocropyld', 'codiagfeatures', \
                   'coecoclass', 'coeplants', 'coerosionacc', 'coforprod', 'cogeomordesc', \
                   'cohydriccriteria', 'cointerp', 'comonth', 'copmgrp', 'copwindbreak', \
                   'corestrictions', 'cosurffrags', 'cotaxfmmin', 'cotaxmoistcl', 'cotext', \
                   'cotreestomng', 'cotxfmother', 'chaashto', 'chconsistence', 'chdesgnsuffix', \
                   'chfrags', 'chpores', 'chstructgrp', 'chtext', 'chtexturegrp', 'chunified', \
                   'coforprodo', 'copm', 'cosoilmoist', 'cosoiltemp', 'cosurfmorphgc', 'cosurfmorphhpp', \
                   'cosurfmorphmr', 'cosurfmorphss', 'chstruct', 'chtexture', 'chtexturemod', \
                   'sacatalog', 'sainterp', 'sdvalgorithm', 'sdvattribute', 'sdvfolder', \
                   'sdvfolderattribute', 'featdesc']
        
        tableKeys = GetTableKeys(templateDB)

        # Get distinct list of file geodatabase data types in gSSURGO
        fldTypes = list()
        fldType = "TEXT"

        # FGDB datatypes: Date, String, SmallInteger, Integer, Single, Double
        fldTypes = dict()
        fldTypes['Date'] = "TEXT"
        fldTypes["String"] = "TEXT"
        fldTypes["SmallInteger"] = "INTEGER"
        fldTypes["Integer"] = "INTEGER"
        fldTypes["Single"] = "REAL"
        fldTypes["Double"] = "REAL"
        fldTypes["Geometry"] = "Geometry"
        #fldTypes["OID"] = "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
        fldTypes["OID"] = "INTEGER PRIMARY KEY NOT NULL"

        PrintMsg(" \nFor OBJECTID, using fldType of '" +  fldTypes["OID"] + "'", 1)
        
        dFeatures = dict()
        dFeatures["Polygon"] = "Polygon"
        dFeatures["Polyline"] = "Linestring"
        dFeatures["Point"] = "Point"

        if len(tableKeys) == 0:
            raise MyError, "Failed to get schema from " + templateDB
        
        PrintMsg(" \nRunning queries creating " + str(len(tblList)) + " tables...", 1)
        conn = sqlite3.connect(newDB)
        c = conn.cursor()

        # I think I need this extension in order to use the AddGeometryColumn method
        # I'm not clear how this works with a geopackage though. Am I really getting
        # some type of ST_GEOMETRY in a geopackage database?
        #
        conn.enable_load_extension(True)
        ex = "stgeometry_sqlite"
        conn.load_extension(ex)
        
        for tblName in tblList:
            template = os.path.join(templateDB, tblName)
            
            arcpy.SetProgressorLabel("\tCreating table: " + tblName)
            tblDesc = arcpy.Describe(os.path.join(templateDB, tblName))
            fields = tblDesc.fields
            dType = tblDesc.dataType

            if tblName in tableKeys:
                keys = tableKeys[tblName]
                primaryKey = keys[0]
                foreignKey = keys[1]

            else:
                primaryKey = None
                foreignKey = None
                PrintMsg("\tKey fields not identified for " + tblName, 1)

            if dType == "FeatureClass":
                sql = "CREATE TABLE " + tblName.upper() + " \n("

            else:
                sql = "CREATE TABLE " + tblName + " \n("
                    
            sqlGeom = ""

            for fld in fields:
                fldName = fld.name.lower()
                fldType = fldTypes[fld.type]
                fldLen = fld.length
                    
                if fldName == "notnull":
                    fldName = "not_null"
                        
                if fld.type != "OID":

                    # Add ST_Geometry (Shape) field after table has been created

                    if fldType == "TEXT":
                        sql += fldName + " " + fldType + " (" + str(fldLen) + "), \n"

                    elif fldType == "Geometry":
                        featType = dFeatures[tblDesc.shapeType]
                        #PrintMsg("\tCreating geometry query for " + tblName + " of " + featType, 1)
                        sqlGeom = "SELECT AddGeometryColumn(null, '" + tblName + "', 'Shape', 4326, '" + featType + "', 'xy', 'null');"
                        
                    elif not fldName in ["shape_length", "shape_area"]:
                        sql += fldName + " " + fldType + ", \n"
    
                else:
                    # this should be OBJECTID coming from FGDB table
                    sql += "OBJECTID " + fldTypes["OID"] + ", \n"

                    
            sql = sql.encode('ascii')[:-3] + ");"
            PrintMsg(" \n" + sql, 1)
            c.execute(sql)
            #conn.commit()

            if sqlGeom != "":
                c.execute(sqlGeom)
                #conn.commit()
            
            
        #PrintMsg(" \nFGDB Types: " + ", ".join(fldTypes), 1)
        conn.commit()
        #c.close()
        conn.close()

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale, time, datetime, shutil, sqlite3

from arcpy import env

try:
    if __name__ == "__main__":

        newDB = arcpy.GetParameterAsText(0)        # New SQLite DB
        templateDB = arcpy.GetParameterAsText(1)     # template gSSURGO DB
        databaseType = arcpy.GetParameterAsText(2)   # ST_GEOMETRY, SPATIALITE, GEOPACKAGE_1.2

        if databaseType == "GEOPACKAGE_1.2":
            PrintMsg(" \nSupported datatypes for .gpkg (according to ESRI) are: SHORT INTEGER, LONG INTEGER, FLOAT, DOUBLE, TEXT, BLOB, DATETIME.", 1)
            
        bTables = CreateTables(newDB, templateDB, databaseType)

        PrintMsg(" \nFinished...", 1)
        

except MyError, e:
    PrintMsg(str(e), 2)

except:
    errorMsg()
                           
