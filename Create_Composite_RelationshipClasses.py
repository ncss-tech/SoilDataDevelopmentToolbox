# Create_Composite_RelationshipClasses.py
#
# Steve Peaslee August 02, 2011. Modified 2017-10-23 to create composite relationshipclasses.
#
# Hard-coded creation of table relationshipclasses in a geodatabase. Does NOT use
# mdstatrshipmas or mdstatrshipdet tables. If SSURGO featureclasses are present,
# featureclass to table relationshipclasses will also be built. All
# tables must be registered and have OBJECTID fields. Geodatabase must have been created
# Can also set table and field aliases using the metadata tables in the output geodatabase.
#
# Tried to fix problem where empty MUPOINT featureclass is identified as Polygon
#
# Problem: composite relationships only work when the foreign key is nullable. This field
# property can only be changed when the table is empty.
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
        PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return False

## ===================================================================================
def elapsedTime(start):
    # Calculate amount of time since "start" and return time string
    try:
        # Stop timer
        #
        end = time.time()

        # Calculate total elapsed seconds
        eTotal = end - start

        # day = 86400 seconds
        # hour = 3600 seconds
        # minute = 60 seconds

        eMsg = ""

        # calculate elapsed days
        eDay1 = eTotal / 86400
        eDay2 = math.modf(eDay1)
        eDay = int(eDay2[1])
        eDayR = eDay2[0]

        if eDay > 1:
          eMsg = eMsg + str(eDay) + " days "
        elif eDay == 1:
          eMsg = eMsg + str(eDay) + " day "

        # Calculated elapsed hours
        eHour1 = eDayR * 24
        eHour2 = math.modf(eHour1)
        eHour = int(eHour2[1])
        eHourR = eHour2[0]

        if eDay > 0 or eHour > 0:
            if eHour > 1:
                eMsg = eMsg + str(eHour) + " hours "
            else:
                eMsg = eMsg + str(eHour) + " hour "

        # Calculate elapsed minutes
        eMinute1 = eHourR * 60
        eMinute2 = math.modf(eMinute1)
        eMinute = int(eMinute2[1])
        eMinuteR = eMinute2[0]

        if eDay > 0 or eHour > 0 or eMinute > 0:
            if eMinute > 1:
                eMsg = eMsg + str(eMinute) + " minutes "
            else:
                eMsg = eMsg + str(eMinute) + " minute "

        # Calculate elapsed secons
        eSeconds = "%.1f" % (eMinuteR * 60)

        if eSeconds == "1.00":
            eMsg = eMsg + eSeconds + " second "
        else:
            eMsg = eMsg + eSeconds + " seconds "

        return eMsg

    except:
        errorMsg()
        return ""

## ===================================================================================
def FindField(theInput, chkField, bVerbose = False):
    # Check table or featureclass to see if specified field Exists
    # If fully qualified name is found, return that
    # Set workspace before calling FindField
    try:
        if arcpy.Exists(theInput):
            theDesc = arcpy.Describe(theInput)
            theFields = theDesc.Fields
            #theField = theFields.next()
            # Get the number of tokens in the fieldnames
            #theNameList = arcpy.ParseFieldName(theField.Name)
            #theCnt = len(theNameList.split(",")) - 1

            for theField in theFields:
                theNameList = arcpy.ParseFieldName(theField.Name)
                theCnt = len(theNameList.split(",")) - 1
                theFieldname = theNameList.split(",")[theCnt].strip()

                if theFieldname.upper() == chkField.upper():
                    return theField.Name

                #theField = theFields.next()

            if bVerbose:
                PrintMsg("Failed to find column " + chkField + " in " + theInput, 2)

            return ""

        else:
            PrintMsg("\tInput layer not found", 0)
            return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def CreateRL(wksp, bOverwrite):
    # Manually create relationshipclasses for the standard SSURGO tables and featureclasses
    #
    # Currently no check to make sure tables actually exist, they will just throw an error.
    #
    # Note!!! One thing that has gotten me into trouble a couple of times...
    #         If you have a table from one database loaded in your ArcMap project, and reference
    #         the same table from another database in your script, the script will grab the one
    #         from ArcMap, if no workspace or path is used to differentiate the two.
    #
    try:
        # Create featureclass relationshipclasses
        #

        fcList = arcpy.ListFeatureClasses("*")

        if len(fcList) == 0:
            # No featureclasses found in workspace, try looking in a feature dataset.
            fdList = arcpy.ListDatasets("*", "Feature")

            if len(fdList) > 0:
                # grab the first feature dataset. Will not look any farther.
                fds = fdList[0]
                arcpy.Workspace = fds
                fcList = arcpy.ListFeatureClasses("*")
                arcpy.Workspace = wksp

            else:
                PrintMsg("No featureclasses found in " + arcpy.Workspace + ", \nunable to create relationshipclasses", 2)
                return False

        if len(fcList) > 0:
            PrintMsg(" \nCreating relationships between featureclasses and tables...", 0)

            for fc in fcList:
                dataType = GetFCType(fc)

                # Check for existence of each featureclass
                #
                if dataType == "Mapunit Polygon":
                    if bOverwrite or not arcpy.Exists("zMapunit_MUPOLYGON"):
                        PrintMsg("    --> zMapunit_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "COMPOSITE", "> Mapunit Polygon Layer", "< Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Mapunit Line":
                    if bOverwrite or not arcpy.Exists("zMapunit_MULINE"):
                        PrintMsg("    --> zMapunit_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "COMPOSITE", "> Mapunit Line Layer", "< + Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Mapunit Point":
                    if bOverwrite or not arcpy.Exists("zMapunit_MUPOINT"):
                        PrintMsg("    --> zMapunit_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "COMPOSITE", "> MapUnit Point Layer", "< Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Special Feature Point":
                    if bOverwrite or not arcpy.Exists("zFeatdesc_FEATPOINT"):
                        PrintMsg("    --> zFeatdesc_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("featdesc", fc, "zFeatdesc_" + fc, "COMPOSITE", "> SF Point", "< Featdesc Table", "BOTH", "ONE_TO_MANY", "NONE", "featkey", "FEATKEY", "","")

                elif dataType == "Special Feature Line":
                    if bOverwrite or not arcpy.Exists("zFeatdesc_FEATLINE"):
                        PrintMsg("    --> zFeatdesc_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("featdesc", fc, "zFeatdesc_" + fc, "COMPOSITE", "> SF Line Layer", "< Featdesc Table", "BOTH", "ONE_TO_MANY", "NONE", "featkey", "FEATKEY", "","")

                elif dataType == "Survey Boundary":
                    if bOverwrite or not arcpy.Exists("zLegend_SAPOLYGON"):
                        PrintMsg("    --> zLegend_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("legend", fc, "zLegend_" + fc, "COMPOSITE", "> Survey Boundary Layer", "< Legend Table", "BOTH", "ONE_TO_MANY", "NONE", "lkey", "LKEY", "","")

                    if bOverwrite or not arcpy.Exists("zSacatalog_SAPOLYGON"):
                        PrintMsg("    --> zSacatalog_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("sacatalog", fc, "zSacatalog_" + fc, "SIMPLE", "> Survey Boundary Layer", "< Survey Area Catalog Table", "BOTH", "ONE_TO_MANY", "NONE", "areasymbol", "AREASYMBOL", "","")

                elif dataType == "Survey Status Map":
                    pass

                else:
                    PrintMsg("Unknown SSURGO datatype for featureclass (" + fc + ")", 1)

        else:
            PrintMsg("No featureclasses found in " + arcpy.Workspace + ", \nunable to create relationshipclasses", 2)
            #return False

    except:
        errorMsg()

    #PrintMsg(" \nSkipping relationships for tables ", 1)
    #return True

    try:
        PrintMsg(" \nCreating relationships between SSURGO tables...", 0)

        if bOverwrite or not arcpy.Exists("zChorizon_Chaashto"):
            PrintMsg("    --> zChorizon_Chaashto", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chaashto", "zChorizon_Chaashto", "COMPOSITE", "> Horizon AASHTO Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chconsistence"):
            PrintMsg("    --> zChorizon_Chconsistence", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chconsistence", "zChorizon_Chconsistence", "COMPOSITE", "> Horizon Consistence Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chdesgnsuffix"):
            PrintMsg("    --> zChorizon_Chdesgnsuffix", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chdesgnsuffix", "zChorizon_Chdesgnsuffix", "COMPOSITE", "> Horizon Designation Suffix Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chfrags"):
            PrintMsg("    --> zChorizon_Chfrags", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chfrags", "zChorizon_Chfrags", "COMPOSITE", "> Horizon Fragments Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chpores"):
            PrintMsg("    --> zChorizon_Chpores", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chpores", "zChorizon_Chpores", "COMPOSITE", "> Horizon Pores Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chstructgrp"):
            PrintMsg("    --> zChorizon_Chstructgrp", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chstructgrp", "zChorizon_Chstructgrp", "COMPOSITE", "> Horizon Structure Group Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chtext"):
            PrintMsg("    --> zChorizon_Chtext", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chtext", "zChorizon_Chtext", "COMPOSITE", "> Horizon Text Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chtexturegrp"):
            PrintMsg("    --> zChorizon_Chtexturegrp", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chtexturegrp", "zChorizon_Chtexturegrp", "COMPOSITE", "> Horizon Texture Group Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chunified"):
            PrintMsg("    --> zChorizon_Chunified", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chunified", "zChorizon_Chunified", "COMPOSITE", "> Horizon Unified Table", "<  Horizon Table", "BOTH", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChstructgrp_Chstruct"):
            PrintMsg("    --> zChstructgrp_Chstruct", 1)
            arcpy.CreateRelationshipClass_management("chstructgrp", "chstruct", "zChstructgrp_Chstruct", "COMPOSITE", "> Horizon Structure Table", "<  Horizon Structure Group Table", "BOTH", "ONE_TO_MANY", "NONE", "chstructgrpkey", "chstructgrpkey", "","")

        if bOverwrite or not arcpy.Exists("zChtexture_Chtexturemod"):
            PrintMsg("    --> zChtexture_Chtexturemod", 1)
            arcpy.CreateRelationshipClass_management("chtexture", "chtexturemod", "zChtexture_Chtexturemod", "COMPOSITE", "> Horizon Texture Modifier Table", "<  Horizon Texture Table", "BOTH", "ONE_TO_MANY", "NONE", "chtkey", "chtkey", "","")

        if bOverwrite or not arcpy.Exists("zChtexturegrp_Chtexture"):
            PrintMsg("    --> zChtexturegrp_Chtexture", 1)
            arcpy.CreateRelationshipClass_management("chtexturegrp", "chtexture", "zChtexturegrp_Chtexture", "COMPOSITE", "> Horizon Texture Table", "<  Horizon Texture Group Table", "BOTH", "ONE_TO_MANY", "NONE", "chtgkey", "chtgkey", "","")

        if bOverwrite or not arcpy.Exists("zCoforprod_Coforprodo"):
            PrintMsg("    --> zCoforprod_Coforprodo", 1)
            arcpy.CreateRelationshipClass_management("coforprod", "coforprodo", "zCoforprod_Coforprodo", "COMPOSITE", "> Component Forest Productivity - Other Table", "<  Component Forest Productivity Table", "BOTH", "ONE_TO_MANY", "NONE", "cofprodkey", "cofprodkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphgc"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphgc", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphgc", "zCogeomordesc_Cosurfmorphgc", "COMPOSITE", "> Component Three Dimensional Surface Morphometry Table", "<  Component Geomorphic Description Table", "BOTH", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphhpp"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphhpp", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphhpp", "zCogeomordesc_Cosurfmorphhpp", "COMPOSITE", "> Component Two Dimensional Surface Morphometry Table", "<  Component Geomorphic Description Table", "BOTH", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphmr"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphmr", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphmr", "zCogeomordesc_Cosurfmorphmr", "COMPOSITE", "> Component Microrelief Surface Morphometry Table", "<  Component Geomorphic Description Table", "BOTH", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphss"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphss", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphss", "zCogeomordesc_Cosurfmorphss", "COMPOSITE", "> Component Slope Shape Surface Morphometry Table", "<  Component Geomorphic Description Table", "BOTH", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zComonth_Cosoilmoist"):
            PrintMsg("    --> zComonth_Cosoilmoist", 1)
            arcpy.CreateRelationshipClass_management("comonth", "cosoilmoist", "zComonth_Cosoilmoist", "COMPOSITE", "> Component Soil Moisture Table", "<  Component Month Table", "BOTH", "ONE_TO_MANY", "NONE", "comonthkey", "comonthkey", "","")

        if bOverwrite or not arcpy.Exists("zComonth_Cosoiltemp"):
            PrintMsg("    --> zComonth_Cosoiltemp", 1)
            arcpy.CreateRelationshipClass_management("comonth", "cosoiltemp", "zComonth_Cosoiltemp", "COMPOSITE", "> Component Soil Temperature Table", "<  Component Month Table", "BOTH", "ONE_TO_MANY", "NONE", "comonthkey", "comonthkey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Chorizon"):
            PrintMsg("    --> zComponent_Chorizon", 1)
            arcpy.CreateRelationshipClass_management("component", "chorizon", "zComponent_Chorizon", "COMPOSITE", "> Horizon Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cocanopycover"):
            PrintMsg("    --> zComponent_Cocanopycover", 1)
            arcpy.CreateRelationshipClass_management("component", "cocanopycover", "zComponent_Cocanopycover", "COMPOSITE", "> Component Canopy Cover Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cocropyld"):
            PrintMsg("    --> zComponent_Cocropyld", 1)
            arcpy.CreateRelationshipClass_management("component", "cocropyld", "zComponent_Cocropyld", "COMPOSITE", "> Component Crop Yield Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Codiagfeatures"):
            PrintMsg("    --> zComponent_Codiagfeatures", 1)
            arcpy.CreateRelationshipClass_management("component", "codiagfeatures", "zComponent_Codiagfeatures", "COMPOSITE", "> Component Diagnostic Features Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coecoclass"):
            PrintMsg("    --> zComponent_Coecoclass", 1)
            arcpy.CreateRelationshipClass_management("component", "coecoclass", "zComponent_Coecoclass", "COMPOSITE", "> Component Ecological Classification Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coeplants"):
            PrintMsg("    --> zComponent_Coeplants", 1)
            arcpy.CreateRelationshipClass_management("component", "coeplants", "zComponent_Coeplants", "COMPOSITE", "> Component Existing Plants Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coerosionacc"):
            PrintMsg("    --> zComponent_Coerosionacc", 1)
            arcpy.CreateRelationshipClass_management("component", "coerosionacc", "zComponent_Coerosionacc", "COMPOSITE", "> Component Erosion Accelerated Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coforprod"):
            PrintMsg("    --> zComponent_Coforprod", 1)
            arcpy.CreateRelationshipClass_management("component", "coforprod", "zComponent_Coforprod", "COMPOSITE", "> Component Forest Productivity Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cogeomordesc"):
            PrintMsg("    --> zComponent_Cogeomordesc", 1)
            arcpy.CreateRelationshipClass_management("component", "cogeomordesc", "zComponent_Cogeomordesc", "COMPOSITE", "> Component Geomorphic Description Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cohydriccriteria"):
            PrintMsg("    --> zComponent_Cohydriccriteria", 1)
            arcpy.CreateRelationshipClass_management("component", "cohydriccriteria", "zComponent_Cohydriccriteria", "COMPOSITE", "> Component Hydric Criteria Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cointerp"):
            PrintMsg("    --> zComponent_Cointerp", 1)
            arcpy.CreateRelationshipClass_management("component", "cointerp", "zComponent_Cointerp", "COMPOSITE", "> Component Interpretation Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Comonth"):
            PrintMsg("    --> zComponent_Comonth", 1)
            arcpy.CreateRelationshipClass_management("component", "comonth", "zComponent_Comonth", "COMPOSITE", "> Component Month Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Copmgrp"):
            PrintMsg("    --> zComponent_Copmgrp", 1)
            arcpy.CreateRelationshipClass_management("component", "copmgrp", "zComponent_Copmgrp", "COMPOSITE", "> Component Parent Material Group Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Copwindbreak"):
            PrintMsg("    --> zComponent_Copwindbreak", 1)
            arcpy.CreateRelationshipClass_management("component", "copwindbreak", "zComponent_Copwindbreak", "COMPOSITE", "> Component Potential Windbreak Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Corestrictions"):
            PrintMsg("    --> zComponent_Corestrictions", 1)
            arcpy.CreateRelationshipClass_management("component", "corestrictions", "zComponent_Corestrictions", "COMPOSITE", "> Component Restrictions Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cosurffrags"):
            PrintMsg("    --> zComponent_Cosurffrags", 1)
            arcpy.CreateRelationshipClass_management("component", "cosurffrags", "zComponent_Cosurffrags", "COMPOSITE", "> Component Surface Fragments Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotaxfmmin"):
            PrintMsg("    --> zComponent_Cotaxfmmin", 1)
            arcpy.CreateRelationshipClass_management("component", "cotaxfmmin", "zComponent_Cotaxfmmin", "COMPOSITE", "> Component Taxonomic Family Mineralogy Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotaxmoistcl"):
            PrintMsg("    --> zComponent_Cotaxmoistcl", 1)
            arcpy.CreateRelationshipClass_management("component", "cotaxmoistcl", "zComponent_Cotaxmoistcl", "COMPOSITE", "> Component Taxonomic Moisture Class Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotext"):
            PrintMsg("    --> zComponent_Cotext", 1)
            arcpy.CreateRelationshipClass_management("component", "cotext", "zComponent_Cotext", "COMPOSITE", "> Component Text Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotreestomng"):
            PrintMsg("    --> zComponent_Cotreestomng", 1)
            arcpy.CreateRelationshipClass_management("component", "cotreestomng", "zComponent_Cotreestomng", "COMPOSITE", "> Component Trees To Manage Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotxfmother"):
            PrintMsg("    --> zComponent_Cotxfmother", 1)
            arcpy.CreateRelationshipClass_management("component", "cotxfmother", "zComponent_Cotxfmother", "COMPOSITE", "> Component Taxonomic Family Other Criteria Table", "<  Component Table", "BOTH", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zCopmgrp_Copm"):
            PrintMsg("    --> zCopmgrp_Copm", 1)
            arcpy.CreateRelationshipClass_management("copmgrp", "copm", "zCopmgrp_Copm", "COMPOSITE", "> Component Parent Material Table", "<  Component Parent Material Group Table", "BOTH", "ONE_TO_MANY", "NONE", "copmgrpkey", "copmgrpkey", "","")

        if bOverwrite or not arcpy.Exists("zDistmd_Distinterpmd"):
            PrintMsg("    --> zDistmd_Distinterpmd", 1)
            arcpy.CreateRelationshipClass_management("distmd", "distinterpmd", "zDistmd_Distinterpmd", "COMPOSITE", "> Distribution Interp Metadata Table", "<  Distribution Metadata Table", "BOTH", "ONE_TO_MANY", "NONE", "distmdkey", "distmdkey", "","")

        if bOverwrite or not arcpy.Exists("zDistmd_Distlegendmd"):
            PrintMsg("    --> zDistmd_Distlegendmd", 1)
            arcpy.CreateRelationshipClass_management("distmd", "distlegendmd", "zDistmd_Distlegendmd", "COMPOSITE", "> Distribution Legend Metadata Table", "<  Distribution Metadata Table", "BOTH", "ONE_TO_MANY", "NONE", "distmdkey", "distmdkey", "","")

        if bOverwrite or not arcpy.Exists("zLaoverlap_Muaoverlap"):
            PrintMsg("    --> zLaoverlap_Muaoverlap", 1)
            arcpy.CreateRelationshipClass_management("laoverlap", "muaoverlap", "zLaoverlap_Muaoverlap", "COMPOSITE", "> Mapunit Area Overlap Table", "<  Legend Area Overlap Table", "BOTH", "ONE_TO_MANY", "NONE", "lareaovkey", "lareaovkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Laoverlap"):
            PrintMsg("    --> zLegend_Laoverlap", 1)
            arcpy.CreateRelationshipClass_management("legend", "laoverlap", "zLegend_Laoverlap", "COMPOSITE", "> Legend Area Overlap Table", "<  Legend Table", "BOTH", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Legendtext"):
            PrintMsg("    --> zLegend_Legendtext", 1)
            arcpy.CreateRelationshipClass_management("legend", "legendtext", "zLegend_Legendtext", "COMPOSITE", "> Legend Text Table", "<  Legend Table", "BOTH", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Mapunit"):
            PrintMsg("    --> zLegend_Mapunit", 1)
            arcpy.CreateRelationshipClass_management("legend", "mapunit", "zLegend_Mapunit", "COMPOSITE", "> Mapunit Table", "<  Legend Table", "BOTH", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Component"):
            PrintMsg("    --> zMapunit_Component", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "component", "zMapunit_Component", "COMPOSITE", "> Component Table", "<  Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Muaggatt"):
            PrintMsg("    --> zMapunit_Muaggatt", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "muaggatt", "zMapunit_Muaggatt", "COMPOSITE", "> Mapunit Aggregated Attribute Table", "<  Mapunit Table", "BOTH", "ONE_TO_ONE", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Muaoverlap"):
            PrintMsg("    --> zMapunit_Muaoverlap", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "muaoverlap", "zMapunit_Muaoverlap", "SIMPLE", "> Mapunit Area Overlap Table", "<  Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Mucropyld"):
            PrintMsg("    --> zMapunit_Mucropyld", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "mucropyld", "zMapunit_Mucropyld", "COMPOSITE", "> Mapunit Crop Yield Table", "<  Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Mutext"):
            PrintMsg("    --> zMapunit_Mutext", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "mutext", "zMapunit_Mutext", "COMPOSITE", "> Mapunit Text Table", "<  Mapunit Table", "BOTH", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

            #PrintMsg("    --> zMdstatdommas_Mdstatdomdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatdommas", "mdstatdomdet", "xMdstatdommas_Mdstatdomdet", "COMPOSITE", "> Domain Detail Static Metadata Table", "<  Domain Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "domainname", "domainname", "","")
            #PrintMsg("    --> zMdstatdommas_Mdstattabcols", 1)
            #arcpy.CreateRelationshipClass_management("mdstatdommas", "mdstattabcols", "xMdstatdommas_Mdstattabcols", "COMPOSITE", "> Table Column Static Metadata Table", "<  Domain Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "domainname", "domainname", "","")
            #PrintMsg("    --> zMdstatidxmas_Mdstatidxdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatidxmas", "mdstatidxdet", "xMdstatidxmas_Mdstatidxdet", "COMPOSITE", "> Index Detail Static Metadata Table", "<  Index Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "idxphyname", "idxphyname", "","")
            #PrintMsg("    --> zMdstatrshipmas_Mdstatrshipdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatrshipmas", "mdstatrshipdet", "xMdstatrshipmas_Mdstatrshipdet", "COMPOSITE", "> Relationship Detail Static Metadata Table", "<  Relationship Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "ltabphyname", "ltabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstatidxmas", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstatidxmas", "xMdstattabs_Mdstatidxmas", "COMPOSITE", "> Index Master Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "tabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstatrshipmas", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstatrshipmas", "xMdstattabs_Mdstatrshipmas", "COMPOSITE", "> Relationship Master Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "ltabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstattabcols", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstattabcols", "xMdstattabs_Mdstattabcols", "COMPOSITE", "> Table Column Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "tabphyname", "","")

        if bOverwrite or not arcpy.Exists("zSacatalog_Sainterp"):
            PrintMsg("    --> zSacatalog_Sainterp", 1)
            arcpy.CreateRelationshipClass_management("sacatalog", "sainterp", "zSacatalog_Sainterp", "COMPOSITE", "> Survey Area Interpretation Table", "<  Survey Area Catalog Table", "BOTH", "ONE_TO_MANY", "NONE", "sacatalogkey", "sacatalogkey", "","")

            #PrintMsg("    --> zSdvattribute_Sdvfolderattribute", 1)
            #arcpy.CreateRelationshipClass_management("sdvattribute", "sdvfolderattribute", "xSdvattribute_Sdvfolderattribute", "COMPOSITE", "> SDV Folder Attribute Table", "<  SDV Attribute Table", "NONE", "ONE_TO_MANY", "NONE", "attributekey", "attributekey", "","")
            #PrintMsg("    --> zSdvfolder_Sdvfolderattribute", 1)
            #arcpy.CreateRelationshipClass_management("sdvfolder", "sdvfolderattribute", "xSdvfolder_Sdvfolderattribute", "COMPOSITE", "> SDV Folder Attribute Table", "<  SDV Folder Table", "NONE", "ONE_TO_MANY", "NONE", "folderkey", "folderkey", "","")

        return True



    except:
        errorMsg()
        return False

## ===================================================================================
def GetFieldAliases():
    # Dumped these aliases out of a SSURGO v2.0 Access template DB.

    try:
        dFieldAliases = dict()

        dFieldAliases["tabphyname.colphyname"] = "collabel"
        dFieldAliases["chaashto.aashtocl"] = "AASHTO"
        dFieldAliases["chaashto.rvindicator"] = "RV?"
        dFieldAliases["chaashto.chkey"] = "Chorizon Key"
        dFieldAliases["chaashto.chaashtokey"] = "Chorizon AASHTO Key"
        dFieldAliases["chconsistence.rupresblkmst"] = "Rupture Moist"
        dFieldAliases["chconsistence.rupresblkdry"] = "Rupture Dry"
        dFieldAliases["chconsistence.rupresblkcem"] = "Rupture Cement"
        dFieldAliases["chconsistence.rupresplate"] = "Rupture Plate"
        dFieldAliases["chconsistence.mannerfailure"] = "Manner of Failure"
        dFieldAliases["chconsistence.stickiness"] = "Stickiness"
        dFieldAliases["chconsistence.plasticity"] = "Plasticity"
        dFieldAliases["chconsistence.rvindicator"] = "RV?"
        dFieldAliases["chconsistence.chkey"] = "Chorizon Key"
        dFieldAliases["chconsistence.chconsistkey"] = "Chorizon Consistence Key"
        dFieldAliases["chdesgnsuffix.desgnsuffix"] = "Suffix"
        dFieldAliases["chdesgnsuffix.chkey"] = "Chorizon Key"
        dFieldAliases["chdesgnsuffix.chdesgnsfxkey"] = "Chorizon Designation Suffix Key"
        dFieldAliases["chfrags.fragvol_l"] = "Vol % - Low Value"
        dFieldAliases["chfrags.fragvol_r"] = "Vol % - Representative Value"
        dFieldAliases["chfrags.fragvol_h"] = "Vol % - High Value"
        dFieldAliases["chfrags.fragkind"] = "Kind"
        dFieldAliases["chfrags.fragsize_l"] = "Size - Low Value"
        dFieldAliases["chfrags.fragsize_r"] = "Size - Representative Value"
        dFieldAliases["chfrags.fragsize_h"] = "Size - High Value"
        dFieldAliases["chfrags.fragshp"] = "Shape"
        dFieldAliases["chfrags.fraground"] = "Roundness"
        dFieldAliases["chfrags.fraghard"] = "Hardness"
        dFieldAliases["chfrags.chkey"] = "Chorizon Key"
        dFieldAliases["chfrags.chfragskey"] = "Chorizon Fragments Key"
        dFieldAliases["chorizon.hzname"] = "Designation"
        dFieldAliases["chorizon.desgndisc"] = "Disc"
        dFieldAliases["chorizon.desgnmaster"] = "Master"
        dFieldAliases["chorizon.desgnmasterprime"] = "Prime"
        dFieldAliases["chorizon.desgnvert"] = "Sub"
        dFieldAliases["chorizon.hzdept_l"] = "Top Depth - Low Value"
        dFieldAliases["chorizon.hzdept_r"] = "Top Depth - Representative Value"
        dFieldAliases["chorizon.hzdept_h"] = "Top Depth - High Value"
        dFieldAliases["chorizon.hzdepb_l"] = "Bottom Depth - Low Value"
        dFieldAliases["chorizon.hzdepb_r"] = "Bottom Depth - Representative Value"
        dFieldAliases["chorizon.hzdepb_h"] = "Bottom Depth - High Value"
        dFieldAliases["chorizon.hzthk_l"] = "Thickness - Low Value"
        dFieldAliases["chorizon.hzthk_r"] = "Thickness - Representative Value"
        dFieldAliases["chorizon.hzthk_h"] = "Thickness - High Value"
        dFieldAliases["chorizon.fraggt10_l"] = "Rock Fragments >10 - Low Value"
        dFieldAliases["chorizon.fraggt10_r"] = "Rock Fragments >10 - Representative Value"
        dFieldAliases["chorizon.fraggt10_h"] = "Rock Fragments >10 - High Value"
        dFieldAliases["chorizon.frag3to10_l"] = "Rock Fragments 3-10 - Low Value"
        dFieldAliases["chorizon.frag3to10_r"] = "Rock Fragments 3-10 - Representative Value"
        dFieldAliases["chorizon.frag3to10_h"] = "Rock Fragments 3-10 - High Value"
        dFieldAliases["chorizon.sieveno4_l"] = "Sieve #4 - Low Value"
        dFieldAliases["chorizon.sieveno4_r"] = "Sieve #4 - Representative Value"
        dFieldAliases["chorizon.sieveno4_h"] = "Sieve #4 - High Value"
        dFieldAliases["chorizon.sieveno10_l"] = "Sieve #10 - Low Value"
        dFieldAliases["chorizon.sieveno10_r"] = "Sieve #10 - Representative Value"
        dFieldAliases["chorizon.sieveno10_h"] = "Sieve #10 - High Value"
        dFieldAliases["chorizon.sieveno40_l"] = "Sieve #40 - Low Value"
        dFieldAliases["chorizon.sieveno40_r"] = "Sieve #40 - Representative Value"
        dFieldAliases["chorizon.sieveno40_h"] = "Sieve #40 - High Value"
        dFieldAliases["chorizon.sieveno200_l"] = "Sieve #200 - Low Value"
        dFieldAliases["chorizon.sieveno200_r"] = "Sieve #200 - Representative Value"
        dFieldAliases["chorizon.sieveno200_h"] = "Sieve #200 - High Value"
        dFieldAliases["chorizon.sandtotal_l"] = "Total Sand - Low Value"
        dFieldAliases["chorizon.sandtotal_r"] = "Total Sand - Representative Value"
        dFieldAliases["chorizon.sandtotal_h"] = "Total Sand - High Value"
        dFieldAliases["chorizon.sandvc_l"] = "Very Course Sand - Low Value"
        dFieldAliases["chorizon.sandvc_r"] = "Very Course Sand - Representative Value"
        dFieldAliases["chorizon.sandvc_h"] = "Very Course Sand - High Value"
        dFieldAliases["chorizon.sandco_l"] = "Course Sand - Low Value"
        dFieldAliases["chorizon.sandco_r"] = "Course Sand - Representative Value"
        dFieldAliases["chorizon.sandco_h"] = "Course Sand - High Value"
        dFieldAliases["chorizon.sandmed_l"] = "Medium Sand - Low Value"
        dFieldAliases["chorizon.sandmed_r"] = "Medium Sand - Representative Value"
        dFieldAliases["chorizon.sandmed_h"] = "Medium Sand - High Value"
        dFieldAliases["chorizon.sandfine_l"] = "Fine Sand - Low Value"
        dFieldAliases["chorizon.sandfine_r"] = "Fine Sand - Representative Value"
        dFieldAliases["chorizon.sandfine_h"] = "Fine Sand - High Value"
        dFieldAliases["chorizon.sandvf_l"] = "Very Fine Sand - Low Value"
        dFieldAliases["chorizon.sandvf_r"] = "Very Fine Sand - Representative Value"
        dFieldAliases["chorizon.sandvf_h"] = "Very Fine Sand - High Value"
        dFieldAliases["chorizon.silttotal_l"] = "Total Silt - Low Value"
        dFieldAliases["chorizon.silttotal_r"] = "Total Silt - Representative Value"
        dFieldAliases["chorizon.silttotal_h"] = "Total Silt - High Value"
        dFieldAliases["chorizon.siltco_l"] = "Coarse Silt - Low Value"
        dFieldAliases["chorizon.siltco_r"] = "Coarse Silt - Representative Value"
        dFieldAliases["chorizon.siltco_h"] = "Coarse Silt - High Value"
        dFieldAliases["chorizon.siltfine_l"] = "Fine Silt - Low Value"
        dFieldAliases["chorizon.siltfine_r"] = "Fine Silt - Representative Value"
        dFieldAliases["chorizon.siltfine_h"] = "Fine Silt - High Value"
        dFieldAliases["chorizon.claytotal_l"] = "Total Clay - Low Value"
        dFieldAliases["chorizon.claytotal_r"] = "Total Clay - Representative Value"
        dFieldAliases["chorizon.claytotal_h"] = "Total Clay - High Value"
        dFieldAliases["chorizon.claysizedcarb_l"] = "CaCO3 Clay - Low Value"
        dFieldAliases["chorizon.claysizedcarb_r"] = "CaCO3 Clay - Representative Value"
        dFieldAliases["chorizon.claysizedcarb_h"] = "CaCO3 Clay - High Value"
        dFieldAliases["chorizon.om_l"] = "OM - Low Value"
        dFieldAliases["chorizon.om_r"] = "OM - Representative Value"
        dFieldAliases["chorizon.om_h"] = "OM - High Value"
        dFieldAliases["chorizon.dbtenthbar_l"] = "Db 0.1 bar H2O - Low Value"
        dFieldAliases["chorizon.dbtenthbar_r"] = "Db 0.1 bar H2O - Representative Value"
        dFieldAliases["chorizon.dbtenthbar_h"] = "Db 0.1 bar H2O - High Value"
        dFieldAliases["chorizon.dbthirdbar_l"] = "Db 0.33 bar H2O - Low Value"
        dFieldAliases["chorizon.dbthirdbar_r"] = "Db 0.33 bar H2O - Representative Value"
        dFieldAliases["chorizon.dbthirdbar_h"] = "Db 0.33 bar H2O - High Value"
        dFieldAliases["chorizon.dbfifteenbar_l"] = "Db 15 bar H2O - Low Value"
        dFieldAliases["chorizon.dbfifteenbar_r"] = "Db 15 bar H2O - Representative Value"
        dFieldAliases["chorizon.dbfifteenbar_h"] = "Db 15 bar H2O - High Value"
        dFieldAliases["chorizon.dbovendry_l"] = "Db oven dry - Low Value"
        dFieldAliases["chorizon.dbovendry_r"] = "Db oven dry - Representative Value"
        dFieldAliases["chorizon.dbovendry_h"] = "Db oven dry - High Value"
        dFieldAliases["chorizon.partdensity"] = "Dp"
        dFieldAliases["chorizon.ksat_l"] = "Ksat - Low Value"
        dFieldAliases["chorizon.ksat_r"] = "Ksat - Representative Value"
        dFieldAliases["chorizon.ksat_h"] = "Ksat - High Value"
        dFieldAliases["chorizon.awc_l"] = "AWC - Low Value"
        dFieldAliases["chorizon.awc_r"] = "AWC - Representative Value"
        dFieldAliases["chorizon.awc_h"] = "AWC - High Value"
        dFieldAliases["chorizon.wtenthbar_l"] = "0.1 bar H2O - Low Value"
        dFieldAliases["chorizon.wtenthbar_r"] = "0.1 bar H2O - Representative Value"
        dFieldAliases["chorizon.wtenthbar_h"] = "0.1 bar H2O - High Value"
        dFieldAliases["chorizon.wthirdbar_l"] = "0.33 bar H2O - Low Value"
        dFieldAliases["chorizon.wthirdbar_r"] = "0.33 bar H2O - Representative Value"
        dFieldAliases["chorizon.wthirdbar_h"] = "0.33 bar H2O - High Value"
        dFieldAliases["chorizon.wfifteenbar_l"] = "15 bar H2O - Low Value"
        dFieldAliases["chorizon.wfifteenbar_r"] = "15 bar H2O - Representative Value"
        dFieldAliases["chorizon.wfifteenbar_h"] = "15 bar H2O - High Value"
        dFieldAliases["chorizon.wsatiated_l"] = "Satiated H2O - Low Value"
        dFieldAliases["chorizon.wsatiated_r"] = "Satiated H2O - Representative Value"
        dFieldAliases["chorizon.wsatiated_h"] = "Satiated H2O - High Value"
        dFieldAliases["chorizon.lep_l"] = "LEP - Low Value"
        dFieldAliases["chorizon.lep_r"] = "LEP - Representative Value"
        dFieldAliases["chorizon.lep_h"] = "LEP - High Value"
        dFieldAliases["chorizon.ll_l"] = "LL - Low Value"
        dFieldAliases["chorizon.ll_r"] = "LL - Representative Value"
        dFieldAliases["chorizon.ll_h"] = "LL - High Value"
        dFieldAliases["chorizon.pi_l"] = "PI - Low Value"
        dFieldAliases["chorizon.pi_r"] = "PI - Representative Value"
        dFieldAliases["chorizon.pi_h"] = "PI - High Value"
        dFieldAliases["chorizon.aashind_l"] = "AASHTO Group Index - Low Value"
        dFieldAliases["chorizon.aashind_r"] = "AASHTO Group Index - Representative Value"
        dFieldAliases["chorizon.aashind_h"] = "AASHTO Group Index - High Value"
        dFieldAliases["chorizon.kwfact"] = "K-Factor Whole Soil"
        dFieldAliases["chorizon.kffact"] = "K-Factor Rock Free"
        dFieldAliases["chorizon.caco3_l"] = "CaCO3 - Low Value"
        dFieldAliases["chorizon.caco3_r"] = "CaCO3 - Representative Value"
        dFieldAliases["chorizon.caco3_h"] = "CaCO3 - High Value"
        dFieldAliases["chorizon.gypsum_l"] = "Gypsum - Low Value"
        dFieldAliases["chorizon.gypsum_r"] = "Gypsum - Representative Value"
        dFieldAliases["chorizon.gypsum_h"] = "Gypsum - High Value"
        dFieldAliases["chorizon.sar_l"] = "SAR - Low Value"
        dFieldAliases["chorizon.sar_r"] = "SAR - Representative Value"
        dFieldAliases["chorizon.sar_h"] = "SAR - High Value"
        dFieldAliases["chorizon.ec_l"] = "EC - Low Value"
        dFieldAliases["chorizon.ec_r"] = "EC - Representative Value"
        dFieldAliases["chorizon.ec_h"] = "EC - High Value"
        dFieldAliases["chorizon.cec7_l"] = "CEC-7 - Low Value"
        dFieldAliases["chorizon.cec7_r"] = "CEC-7 - Representative Value"
        dFieldAliases["chorizon.cec7_h"] = "CEC-7 - High Value"
        dFieldAliases["chorizon.ecec_l"] = "ECEC - Low Value"
        dFieldAliases["chorizon.ecec_r"] = "ECEC - Representative Value"
        dFieldAliases["chorizon.ecec_h"] = "ECEC - High Value"
        dFieldAliases["chorizon.sumbases_l"] = "Sum of Bases - Low Value"
        dFieldAliases["chorizon.sumbases_r"] = "Sum of Bases - Representative Value"
        dFieldAliases["chorizon.sumbases_h"] = "Sum of Bases - High Value"
        dFieldAliases["chorizon.ph1to1h2o_l"] = "pH H2O - Low Value"
        dFieldAliases["chorizon.ph1to1h2o_r"] = "pH H2O - Representative Value"
        dFieldAliases["chorizon.ph1to1h2o_h"] = "pH H2O - High Value"
        dFieldAliases["chorizon.ph01mcacl2_l"] = "pH CaCl2 - Low Value"
        dFieldAliases["chorizon.ph01mcacl2_r"] = "pH CaCl2 - Representative Value"
        dFieldAliases["chorizon.ph01mcacl2_h"] = "pH CaCl2 - High Value"
        dFieldAliases["chorizon.freeiron_l"] = "Free Iron - Low Value"
        dFieldAliases["chorizon.freeiron_r"] = "Free Iron - Representative Value"
        dFieldAliases["chorizon.freeiron_h"] = "Free Iron - High Value"
        dFieldAliases["chorizon.feoxalate_l"] = "Oxalate Fe - Low Value"
        dFieldAliases["chorizon.feoxalate_r"] = "Oxalate Fe - Representative Value"
        dFieldAliases["chorizon.feoxalate_h"] = "Oxalate Fe - High Value"
        dFieldAliases["chorizon.extracid_l"] = "Ext Acidity - Low Value"
        dFieldAliases["chorizon.extracid_r"] = "Ext Acidity - Representative Value"
        dFieldAliases["chorizon.extracid_h"] = "Ext Acidity - High Value"
        dFieldAliases["chorizon.extral_l"] = "Extract Al - Low Value"
        dFieldAliases["chorizon.extral_r"] = "Extract Al - Representative Value"
        dFieldAliases["chorizon.extral_h"] = "Extract Al - High Value"
        dFieldAliases["chorizon.aloxalate_l"] = "Oxalate Al - Low Value"
        dFieldAliases["chorizon.aloxalate_r"] = "Oxalate Al - Representative Value"
        dFieldAliases["chorizon.aloxalate_h"] = "Oxalate Al - High Value"
        dFieldAliases["chorizon.pbray1_l"] = "Bray 1 Phos - Low Value"
        dFieldAliases["chorizon.pbray1_r"] = "Bray 1 Phos - Representative Value"
        dFieldAliases["chorizon.pbray1_h"] = "Bray 1 Phos - High Value"
        dFieldAliases["chorizon.poxalate_l"] = "Oxalate Phos - Low Value"
        dFieldAliases["chorizon.poxalate_r"] = "Oxalate Phos - Representative Value"
        dFieldAliases["chorizon.poxalate_h"] = "Oxalate Phos - High Value"
        dFieldAliases["chorizon.ph2osoluble_l"] = "Water Soluble Phos - Low Value"
        dFieldAliases["chorizon.ph2osoluble_r"] = "Water Soluble Phos - Representative Value"
        dFieldAliases["chorizon.ph2osoluble_h"] = "Water Soluble Phos - High Value"
        dFieldAliases["chorizon.ptotal_l"] = "Total Phos - Low Value"
        dFieldAliases["chorizon.ptotal_r"] = "Total Phos - Representative Value"
        dFieldAliases["chorizon.ptotal_h"] = "Total Phos - High Value"
        dFieldAliases["chorizon.excavdifcl"] = "Excav Diff"
        dFieldAliases["chorizon.excavdifms"] = "Excav Diff Moisture"
        dFieldAliases["chorizon.cokey"] = "Component Key"
        dFieldAliases["chorizon.chkey"] = "Chorizon Key"
        dFieldAliases["chpores.poreqty_l"] = "Quantity - Low Value"
        dFieldAliases["chpores.poreqty_r"] = "Quantity - Representative Value"
        dFieldAliases["chpores.poreqty_h"] = "Quantity - High Value"
        dFieldAliases["chpores.poresize"] = "Size"
        dFieldAliases["chpores.porecont"] = "Continuity"
        dFieldAliases["chpores.poreshp"] = "Shape"
        dFieldAliases["chpores.rvindicator"] = "RV?"
        dFieldAliases["chpores.chkey"] = "Chorizon Key"
        dFieldAliases["chpores.chporeskey"] = "Chorizon Pores Key"
        dFieldAliases["chstruct.structgrade"] = "Grade"
        dFieldAliases["chstruct.structsize"] = "Size"
        dFieldAliases["chstruct.structtype"] = "Type"
        dFieldAliases["chstruct.structid"] = "Structure ID"
        dFieldAliases["chstruct.structpartsto"] = "Parts to Structure ID"
        dFieldAliases["chstruct.chstructgrpkey"] = "Chorizon Structure Group Key"
        dFieldAliases["chstruct.chstructkey"] = "Chorizon Structure Key"
        dFieldAliases["chstructgrp.structgrpname"] = "Structure"
        dFieldAliases["chstructgrp.rvindicator"] = "RV?"
        dFieldAliases["chstructgrp.chkey"] = "Chorizon Key"
        dFieldAliases["chstructgrp.chstructgrpkey"] = "Chorizon Structure Group Key"
        dFieldAliases["chtext.recdate"] = "Date"
        dFieldAliases["chtext.chorizontextkind"] = "Kind"
        dFieldAliases["chtext.textcat"] = "Category"
        dFieldAliases["chtext.textsubcat"] = "Subcategory"
        dFieldAliases["chtext.text"] = "Text"
        dFieldAliases["chtext.chkey"] = "Chorizon Key"
        dFieldAliases["chtext.chtextkey"] = "Chorizon Text Key"
        dFieldAliases["chtexture.texcl"] = "Texture"
        dFieldAliases["chtexture.lieutex"] = "In Lieu"
        dFieldAliases["chtexture.chtgkey"] = "Chorizon Texture Group Key"
        dFieldAliases["chtexture.chtkey"] = "Chorizon Texture Key"
        dFieldAliases["chtexturegrp.texture"] = "Tex Mod & Class"
        dFieldAliases["chtexturegrp.stratextsflag"] = "Stratified?"
        dFieldAliases["chtexturegrp.rvindicator"] = "RV?"
        dFieldAliases["chtexturegrp.texdesc"] = "Texture Description"
        dFieldAliases["chtexturegrp.chkey"] = "Chorizon Key"
        dFieldAliases["chtexturegrp.chtgkey"] = "Chorizon Texture Group Key"
        dFieldAliases["chtexturemod.texmod"] = "Modifier"
        dFieldAliases["chtexturemod.chtkey"] = "Chorizon Texture Key"
        dFieldAliases["chtexturemod.chtexmodkey"] = "Chorizon Texture Modifier Key"
        dFieldAliases["chunified.unifiedcl"] = "Unified"
        dFieldAliases["chunified.rvindicator"] = "RV?"
        dFieldAliases["chunified.chkey"] = "Chorizon Key"
        dFieldAliases["chunified.chunifiedkey"] = "Chorizon Unified Key"
        dFieldAliases["cocanopycover.plantcov"] = "Canopy Cover %"
        dFieldAliases["cocanopycover.plantsym"] = "Plant Symbol"
        dFieldAliases["cocanopycover.plantsciname"] = "Scientific Name"
        dFieldAliases["cocanopycover.plantcomname"] = "Common Name"
        dFieldAliases["cocanopycover.cokey"] = "Component Key"
        dFieldAliases["cocanopycover.cocanopycovkey"] = "Component Canopy Cover Key"
        dFieldAliases["cocropyld.cropname"] = "Crop Name"
        dFieldAliases["cocropyld.yldunits"] = "Units"
        dFieldAliases["cocropyld.nonirryield_l"] = "Nirr Yield - Low Value"
        dFieldAliases["cocropyld.nonirryield_r"] = "Nirr Yield - Representative Value"
        dFieldAliases["cocropyld.nonirryield_h"] = "Nirr Yield - High Value"
        dFieldAliases["cocropyld.irryield_l"] = "Irr Yield - Low Value"
        dFieldAliases["cocropyld.irryield_r"] = "Irr Yield - Representative Value"
        dFieldAliases["cocropyld.irryield_h"] = "Irr Yield - High Value"
        dFieldAliases["cocropyld.cropprodindex"] = "Prod Index"
        dFieldAliases["cocropyld.vasoiprdgrp"] = "VA Soil Prod Group"
        dFieldAliases["cocropyld.cokey"] = "Component Key"
        dFieldAliases["cocropyld.cocropyldkey"] = "Component Crop Yield Key"
        dFieldAliases["codiagfeatures.featkind"] = "Kind"
        dFieldAliases["codiagfeatures.featdept_l"] = "Top Depth - Low Value"
        dFieldAliases["codiagfeatures.featdept_r"] = "Top Depth - Representative Value"
        dFieldAliases["codiagfeatures.featdept_h"] = "Top Depth - High Value"
        dFieldAliases["codiagfeatures.featdepb_l"] = "Bottom Depth - Low Value"
        dFieldAliases["codiagfeatures.featdepb_r"] = "Bottom Depth - Representative Value"
        dFieldAliases["codiagfeatures.featdepb_h"] = "Bottom Depth - High Value"
        dFieldAliases["codiagfeatures.featthick_l"] = "Thickness - Low Value"
        dFieldAliases["codiagfeatures.featthick_r"] = "Thickness - Representative Value"
        dFieldAliases["codiagfeatures.featthick_h"] = "Thickness - High Value"
        dFieldAliases["codiagfeatures.cokey"] = "Component Key"
        dFieldAliases["codiagfeatures.codiagfeatkey"] = "Component Diagnostic Features Key"
        dFieldAliases["coecoclass.ecoclasstypename"] = "Ecological Classification Type Name"
        dFieldAliases["coecoclass.ecoclassref"] = "Ecological Classification Reference"
        dFieldAliases["coecoclass.ecoclassid"] = "Ecological Classification ID"
        dFieldAliases["coecoclass.ecoclassname"] = "Ecological Classification Name"
        dFieldAliases["coecoclass.cokey"] = "Component Key"
        dFieldAliases["coecoclass.coecoclasskey"] = "Component Ecological Classification Key"
        dFieldAliases["coeplants.plantsym"] = "Plant Symbol"
        dFieldAliases["coeplants.plantsciname"] = "Scientific Name"
        dFieldAliases["coeplants.plantcomname"] = "Common Name"
        dFieldAliases["coeplants.forestunprod"] = "Understory Prod %"
        dFieldAliases["coeplants.rangeprod"] = "Range Prod %"
        dFieldAliases["coeplants.cokey"] = "Component Key"
        dFieldAliases["coeplants.coeplantskey"] = "Component Existing Plants Key"
        dFieldAliases["coerosionacc.erokind"] = "Kind"
        dFieldAliases["coerosionacc.rvindicator"] = "RV?"
        dFieldAliases["coerosionacc.cokey"] = "Component Key"
        dFieldAliases["coerosionacc.coeroacckey"] = "Component Erosion Accelerated Key"
        dFieldAliases["coforprod.plantsym"] = "Plant Symbol"
        dFieldAliases["coforprod.plantsciname"] = "Scientific Name"
        dFieldAliases["coforprod.plantcomname"] = "Common Name"
        dFieldAliases["coforprod.siteindexbase"] = "Site Index Base"
        dFieldAliases["coforprod.siteindex_l"] = "Site Index - Low Value"
        dFieldAliases["coforprod.siteindex_r"] = "Site Index - Representative Value"
        dFieldAliases["coforprod.siteindex_h"] = "Site Index - High Value"
        dFieldAliases["coforprod.fprod_l"] = "Productivity ft3/ac/yr CMAI - Low Value"
        dFieldAliases["coforprod.fprod_r"] = "Productivity ft3/ac/yr CMAI - Representative Value"
        dFieldAliases["coforprod.fprod_h"] = "Productivity ft3/ac/yr CMAI - High Value"
        dFieldAliases["coforprod.cokey"] = "Component Key"
        dFieldAliases["coforprod.cofprodkey"] = "Component Forest Productivity Key"
        dFieldAliases["coforprodo.siteindexbase"] = "Site Index Base"
        dFieldAliases["coforprodo.siteindex_l"] = "Site Index - Low Value"
        dFieldAliases["coforprodo.siteindex_r"] = "Site Index - Representative Value"
        dFieldAliases["coforprodo.siteindex_h"] = "Site Index - High Value"
        dFieldAliases["coforprodo.fprod_l"] = "Productivity - Low Value"
        dFieldAliases["coforprodo.fprod_r"] = "Productivity - Representative Value"
        dFieldAliases["coforprodo.fprod_h"] = "Productivity - High Value"
        dFieldAliases["coforprodo.fprodunits"] = "Units"
        dFieldAliases["coforprodo.cofprodkey"] = "Component Forest Productivity Key"
        dFieldAliases["coforprodo.cofprodokey"] = "Component Forest Productivity Other Key"
        dFieldAliases["cogeomordesc.geomftname"] = "Feature Type"
        dFieldAliases["cogeomordesc.geomfname"] = "Feature Name"
        dFieldAliases["cogeomordesc.geomfmod"] = "Feature Modifier"
        dFieldAliases["cogeomordesc.geomfeatid"] = "Feature ID"
        dFieldAliases["cogeomordesc.Existsonfeat"] = "Exists On Feature ID"
        dFieldAliases["cogeomordesc.rvindicator"] = "RV?"
        dFieldAliases["cogeomordesc.cokey"] = "Component Key"
        dFieldAliases["cogeomordesc.cogeomdkey"] = "Component Geomorphic Description Key"
        dFieldAliases["cohydriccriteria.hydriccriterion"] = "Hydric Criterion"
        dFieldAliases["cohydriccriteria.cokey"] = "Component Key"
        dFieldAliases["cohydriccriteria.cohydcritkey"] = "Component Hydric Criteria Key"
        dFieldAliases["cointerp.cokey"] = "Component Key"
        dFieldAliases["cointerp.mrulekey"] = "Main Rule Key"
        dFieldAliases["cointerp.mrulename"] = "Main Rule Name"
        dFieldAliases["cointerp.seqnum"] = "Sequence Number"
        dFieldAliases["cointerp.rulekey"] = "Rule Key"
        dFieldAliases["cointerp.rulename"] = "Rule Name"
        dFieldAliases["cointerp.ruledepth"] = "Rule Depth"
        dFieldAliases["cointerp.interpll"] = "Interp Low Low"
        dFieldAliases["cointerp.interpllc"] = "Interp Low Low Class"
        dFieldAliases["cointerp.interplr"] = "Interp Low Representative Value"
        dFieldAliases["cointerp.interplrc"] = "Interp Low Representative Value Class"
        dFieldAliases["cointerp.interphr"] = "Interp High Representative Value"
        dFieldAliases["cointerp.interphrc"] = "Interp High Representative Value Class"
        dFieldAliases["cointerp.interphh"] = "Interp High High"
        dFieldAliases["cointerp.interphhc"] = "Interp High High Class"
        dFieldAliases["cointerp.nullpropdatabool"] = "Null Property Data Boolean"
        dFieldAliases["cointerp.defpropdatabool"] = "Default Property Data Boolean"
        dFieldAliases["cointerp.incpropdatabool"] = "Inconsistent Property Data Boolean"
        dFieldAliases["cointerp.cointerpkey"] = "Component Interpretation Key"
        dFieldAliases["comonth.monthseq"] = "Month Sequence"
        dFieldAliases["comonth.month"] = "Month"
        dFieldAliases["comonth.flodfreqcl"] = "Flooding Frequency"
        dFieldAliases["comonth.floddurcl"] = "Flooding Duration"
        dFieldAliases["comonth.pondfreqcl"] = "Ponding Frequency"
        dFieldAliases["comonth.ponddurcl"] = "Ponding Duration"
        dFieldAliases["comonth.ponddep_l"] = "Ponding Depth - Low Value"
        dFieldAliases["comonth.ponddep_r"] = "Ponding Depth - Representative Value"
        dFieldAliases["comonth.ponddep_h"] = "Ponding Depth - High Value"
        dFieldAliases["comonth.dlyavgprecip_l"] = "Daily Precip - Low Value"
        dFieldAliases["comonth.dlyavgprecip_r"] = "Daily Precip - Representative Value"
        dFieldAliases["comonth.dlyavgprecip_h"] = "Daily Precip - High Value"
        dFieldAliases["comonth.dlyavgpotet_l"] = "Daily ET - Low Value"
        dFieldAliases["comonth.dlyavgpotet_r"] = "Daily ET - Representative Value"
        dFieldAliases["comonth.dlyavgpotet_h"] = "Daily ET - High Value"
        dFieldAliases["comonth.cokey"] = "Component Key"
        dFieldAliases["comonth.comonthkey"] = "Component Month Key"
        dFieldAliases["component.comppct_l"] = "Comp % - Low Value"
        dFieldAliases["component.comppct_r"] = "Comp % - Representative Value"
        dFieldAliases["component.comppct_h"] = "Comp % - High Value"
        dFieldAliases["component.compname"] = "Component Name"
        dFieldAliases["component.compkind"] = "Component Kind"
        dFieldAliases["component.majcompflag"] = "Major Component"
        dFieldAliases["component.otherph"] = "SIR phase"
        dFieldAliases["component.localphase"] = "Local Phase"
        dFieldAliases["component.slope_l"] = "Slope Gradient - Low Value"
        dFieldAliases["component.slope_r"] = "Slope Gradient - Representative Value"
        dFieldAliases["component.slope_h"] = "Slope Gradient - High Value"
        dFieldAliases["component.slopelenusle_l"] = "Slope Length USLE - Low Value"
        dFieldAliases["component.slopelenusle_r"] = "Slope Length USLE - Representative Value"
        dFieldAliases["component.slopelenusle_h"] = "Slope Length USLE - High Value"
        dFieldAliases["component.runoff"] = "Runoff Class"
        dFieldAliases["component.tfact"] = "T Factor"
        dFieldAliases["component.wei"] = "WEI"
        dFieldAliases["component.weg"] = "WEG"
        dFieldAliases["component.erocl"] = "Erosion Class"
        dFieldAliases["component.earthcovkind1"] = "Cover Kind 1"
        dFieldAliases["component.earthcovkind2"] = "Cover Kind 2"
        dFieldAliases["component.hydricon"] = "Hydric Condition"
        dFieldAliases["component.hydricrating"] = "Hydric Rating"
        dFieldAliases["component.drainagecl"] = "Drainage Class"
        dFieldAliases["component.elev_l"] = "Elevation - Low Value"
        dFieldAliases["component.elev_r"] = "Elevation - Representative Value"
        dFieldAliases["component.elev_h"] = "Elevation - High Value"
        dFieldAliases["component.aspectccwise"] = "Aspect Counter Clockwise"
        dFieldAliases["component.aspectrep"] = "Aspect Representative"
        dFieldAliases["component.aspectcwise"] = "Aspect Clockwise"
        dFieldAliases["component.geomdesc"] = "Geomorphic Description"
        dFieldAliases["component.albedodry_l"] = "Albedo Dry - Low Value"
        dFieldAliases["component.albedodry_r"] = "Albedo Dry - Representative Value"
        dFieldAliases["component.albedodry_h"] = "Albedo Dry - High Value"
        dFieldAliases["component.airtempa_l"] = "MAAT - Low Value"
        dFieldAliases["component.airtempa_r"] = "MAAT - Representative Value"
        dFieldAliases["component.airtempa_h"] = "MAAT - High Value"
        dFieldAliases["component.map_l"] = "MAP - Low Value"
        dFieldAliases["component.map_r"] = "MAP - Representative Value"
        dFieldAliases["component.map_h"] = "MAP - High Value"
        dFieldAliases["component.reannualprecip_l"] = "REAP - Low Value"
        dFieldAliases["component.reannualprecip_r"] = "REAP - Representative Value"
        dFieldAliases["component.reannualprecip_h"] = "REAP - High Value"
        dFieldAliases["component.ffd_l"] = "Frost Free Days - Low Value"
        dFieldAliases["component.ffd_r"] = "Frost Free Days - Representative Value"
        dFieldAliases["component.ffd_h"] = "Frost Free Days - High Value"
        dFieldAliases["component.nirrcapcl"] = "Nirr Land Capability Class"
        dFieldAliases["component.nirrcapscl"] = "Nirr Land Capability Subclass"
        dFieldAliases["component.nirrcapunit"] = "Nirr Land Capability Unit"
        dFieldAliases["component.irrcapcl"] = "Irr Land Capability Class"
        dFieldAliases["component.irrcapscl"] = "Irr Land Capability Subclass"
        dFieldAliases["component.irrcapunit"] = "Irr Land Capability Unit"
        dFieldAliases["component.cropprodindex"] = "Crop Productivity Index"
        dFieldAliases["component.constreeshrubgrp"] = "Cons Tree Shrub Group"
        dFieldAliases["component.wndbrksuitgrp"] = "Windbreak Suitability (Obsolete)"
        dFieldAliases["component.rsprod_l"] = "Range Prod - Low Value"
        dFieldAliases["component.rsprod_r"] = "Range Prod - Representative Value"
        dFieldAliases["component.rsprod_h"] = "Range Prod - High Value"
        dFieldAliases["component.foragesuitgrpid"] = "Forage Suitability Group ID"
        dFieldAliases["component.wlgrain"] = "Grain Habitat"
        dFieldAliases["component.wlgrass"] = "Grass Habitat"
        dFieldAliases["component.wlherbaceous"] = "Herbaceous Habitat"
        dFieldAliases["component.wlshrub"] = "Shrub Habitat"
        dFieldAliases["component.wlconiferous"] = "Conifer Habitat"
        dFieldAliases["component.wlhardwood"] = "Hardwood Habitat"
        dFieldAliases["component.wlwetplant"] = "Wetland Habitat"
        dFieldAliases["component.wlshallowwat"] = "Water Habitat"
        dFieldAliases["component.wlrangeland"] = "Rangeland Wildlife"
        dFieldAliases["component.wlopenland"] = "Openland Wildlife"
        dFieldAliases["component.wlwoodland"] = "Woodland Wildlife"
        dFieldAliases["component.wlwetland"] = "Wetland Wildlife"
        dFieldAliases["component.soilslippot"] = "Soil Slip Potential"
        dFieldAliases["component.frostact"] = "Frost Action"
        dFieldAliases["component.initsub_l"] = "Init Subsidence - Low Value"
        dFieldAliases["component.initsub_r"] = "Init Subsidence - Representative Value"
        dFieldAliases["component.initsub_h"] = "Init Subsidence - High Value"
        dFieldAliases["component.totalsub_l"] = "Total Subsidence - Low Value"
        dFieldAliases["component.totalsub_r"] = "Total Subsidence - Representative Value"
        dFieldAliases["component.totalsub_h"] = "Total Subsidence - High Value"
        dFieldAliases["component.hydgrp"] = "Hydrologic Group"
        dFieldAliases["component.corcon"] = "Corrosion Concrete"
        dFieldAliases["component.corsteel"] = "Corrosion Steel"
        dFieldAliases["component.taxclname"] = "Taxonomic Class"
        dFieldAliases["component.taxorder"] = "Taxonomic Order"
        dFieldAliases["component.taxsuborder"] = "Taxonomic Suborder"
        dFieldAliases["component.taxgrtgroup"] = "Great Group"
        dFieldAliases["component.taxsubgrp"] = "Subgroup"
        dFieldAliases["component.taxpartsize"] = "Particle Size"
        dFieldAliases["component.taxpartsizemod"] = "Particle Size Mod"
        dFieldAliases["component.taxceactcl"] = "CEC Activity Class"
        dFieldAliases["component.taxreaction"] = "Reaction"
        dFieldAliases["component.taxtempcl"] = "Temperature Class"
        dFieldAliases["component.taxmoistscl"] = "Moist Subclass"
        dFieldAliases["component.taxtempregime"] = "Temperature Regime"
        dFieldAliases["component.soiltaxedition"] = "Keys to Taxonomy Edition Used"
        dFieldAliases["component.castorieindex"] = "CA Storie Index"
        dFieldAliases["component.flecolcomnum"] = "FL Ecol Comm #"
        dFieldAliases["component.flhe"] = "FL HE"
        dFieldAliases["component.flphe"] = "FL PHE"
        dFieldAliases["component.flsoilleachpot"] = "FL Leach Potential"
        dFieldAliases["component.flsoirunoffpot"] = "FL Runoff Potential"
        dFieldAliases["component.fltemik2use"] = "FL Temik"
        dFieldAliases["component.fltriumph2use"] = "FL Triumph"
        dFieldAliases["component.indraingrp"] = "IN Drainage Group"
        dFieldAliases["component.innitrateleachi"] = "IN NO3 Leach Index"
        dFieldAliases["component.misoimgmtgrp"] = "MI Soil Mgmt Group"
        dFieldAliases["component.vasoimgtgrp"] = "VA Soil Mgmt Group"
        dFieldAliases["component.mukey"] = "Mapunit Key"
        dFieldAliases["component.cokey"] = "Component Key"
        dFieldAliases["copm.pmorder"] = "Vertical Order"
        dFieldAliases["copm.pmmodifier"] = "Textural Modifier"
        dFieldAliases["copm.pmgenmod"] = "General Modifier"
        dFieldAliases["copm.pmkind"] = "Parent Material Kind"
        dFieldAliases["copm.pmorigin"] = "Parent Material Origin"
        dFieldAliases["copm.copmgrpkey"] = "Component Parent Material Group Key"
        dFieldAliases["copm.copmkey"] = "Component Parent Material Key"
        dFieldAliases["copmgrp.pmgroupname"] = "Group Name"
        dFieldAliases["copmgrp.rvindicator"] = "RV?"
        dFieldAliases["copmgrp.cokey"] = "Component Key"
        dFieldAliases["copmgrp.copmgrpkey"] = "Component Parent Material Group Key"
        dFieldAliases["copwindbreak.wndbrkht_l"] = "Height - Low Value"
        dFieldAliases["copwindbreak.wndbrkht_r"] = "Height - Representative Value"
        dFieldAliases["copwindbreak.wndbrkht_h"] = "Height - High Value"
        dFieldAliases["copwindbreak.plantsym"] = "Plant Symbol"
        dFieldAliases["copwindbreak.plantsciname"] = "Scientific Name"
        dFieldAliases["copwindbreak.plantcomname"] = "Common Name"
        dFieldAliases["copwindbreak.cokey"] = "Component Key"
        dFieldAliases["copwindbreak.copwindbreakkey"] = "Component Potential Windbreak Key"
        dFieldAliases["corestrictions.reskind"] = "Kind"
        dFieldAliases["corestrictions.reshard"] = "Hardness"
        dFieldAliases["corestrictions.resdept_l"] = "Top Depth - Low Value"
        dFieldAliases["corestrictions.resdept_r"] = "Top Depth - Representative Value"
        dFieldAliases["corestrictions.resdept_h"] = "Top Depth - High Value"
        dFieldAliases["corestrictions.resdepb_l"] = "Bottom Depth - Low Value"
        dFieldAliases["corestrictions.resdepb_r"] = "Bottom Depth - Representative Value"
        dFieldAliases["corestrictions.resdepb_h"] = "Bottom Depth - High Value"
        dFieldAliases["corestrictions.resthk_l"] = "Thickness - Low Value"
        dFieldAliases["corestrictions.resthk_r"] = "Thickness - Representative Value"
        dFieldAliases["corestrictions.resthk_h"] = "Thickness - High Value"
        dFieldAliases["corestrictions.cokey"] = "Component Key"
        dFieldAliases["corestrictions.corestrictkey"] = "Component Restrictions Key"
        dFieldAliases["cosoilmoist.soimoistdept_l"] = "Top Depth - Low Value"
        dFieldAliases["cosoilmoist.soimoistdept_r"] = "Top Depth - Representative Value"
        dFieldAliases["cosoilmoist.soimoistdept_h"] = "Top Depth - High Value"
        dFieldAliases["cosoilmoist.soimoistdepb_l"] = "Bottom Depth - Low Value"
        dFieldAliases["cosoilmoist.soimoistdepb_r"] = "Bottom Depth - Representative Value"
        dFieldAliases["cosoilmoist.soimoistdepb_h"] = "Bottom Depth - High Value"
        dFieldAliases["cosoilmoist.soimoiststat"] = "Moisture Status"
        dFieldAliases["cosoilmoist.comonthkey"] = "Component Month Key"
        dFieldAliases["cosoilmoist.cosoilmoistkey"] = "Component Soil Moisture Key"
        dFieldAliases["cosoiltemp.soitempmm"] = "Monthly Temp"
        dFieldAliases["cosoiltemp.soitempdept_l"] = "Top Depth - Low Value"
        dFieldAliases["cosoiltemp.soitempdept_r"] = "Top Depth - Representative Value"
        dFieldAliases["cosoiltemp.soitempdept_h"] = "Top Depth - High Value"
        dFieldAliases["cosoiltemp.soitempdepb_l"] = "Bottom Depth - Low Value"
        dFieldAliases["cosoiltemp.soitempdepb_r"] = "Bottom Depth - Representative Value"
        dFieldAliases["cosoiltemp.soitempdepb_h"] = "Bottom Depth - High Value"
        dFieldAliases["cosoiltemp.comonthkey"] = "Component Month Key"
        dFieldAliases["cosoiltemp.cosoiltempkey"] = "Component Soil Temperature Key"
        dFieldAliases["cosurffrags.sfragcov_l"] = "Cover % - Low Value"
        dFieldAliases["cosurffrags.sfragcov_r"] = "Cover % - Representative Value"
        dFieldAliases["cosurffrags.sfragcov_h"] = "Cover % - High Value"
        dFieldAliases["cosurffrags.distrocks_l"] = "Spacing - Low Value"
        dFieldAliases["cosurffrags.distrocks_r"] = "Spacing - Representative Value"
        dFieldAliases["cosurffrags.distrocks_h"] = "Spacing - High Value"
        dFieldAliases["cosurffrags.sfragkind"] = "Kind"
        dFieldAliases["cosurffrags.sfragsize_l"] = "Size - Low Value"
        dFieldAliases["cosurffrags.sfragsize_r"] = "Size - Representative Value"
        dFieldAliases["cosurffrags.sfragsize_h"] = "Size - High Value"
        dFieldAliases["cosurffrags.sfragshp"] = "Shape"
        dFieldAliases["cosurffrags.sfraground"] = "Roundness"
        dFieldAliases["cosurffrags.sfraghard"] = "Hardness"
        dFieldAliases["cosurffrags.cokey"] = "Component Key"
        dFieldAliases["cosurffrags.cosurffragskey"] = "Component Surface Fragments Key"
        dFieldAliases["cosurfmorphgc.geomposmntn"] = "Geomorphic Component - Mountains"
        dFieldAliases["cosurfmorphgc.geomposhill"] = "Geomorphic Component - Hills"
        dFieldAliases["cosurfmorphgc.geompostrce"] = "Geomorphic Component - Terraces"
        dFieldAliases["cosurfmorphgc.geomposflats"] = "Geomorphic Component - Flats"
        dFieldAliases["cosurfmorphgc.cogeomdkey"] = "Component Geomorphic Description Key"
        dFieldAliases["cosurfmorphgc.cosurfmorgckey"] = "Component Surface Morphometry - Geomorphic Component Key"
        dFieldAliases["cosurfmorphhpp.hillslopeprof"] = "Hillslope Profile"
        dFieldAliases["cosurfmorphhpp.cogeomdkey"] = "Component Geomorphic Description Key"
        dFieldAliases["cosurfmorphhpp.cosurfmorhppkey"] = "Component Surface Morphometry - Hillslope Profile Position"
        dFieldAliases["cosurfmorphmr.geomicrorelief"] = "Microrelief Kind"
        dFieldAliases["cosurfmorphmr.cogeomdkey"] = "Component Geomorphic Description Key"
        dFieldAliases["cosurfmorphmr.cosurfmormrkey"] = "Component Surface Morphometry - Micro Relief Key"
        dFieldAliases["cosurfmorphss.shapeacross"] = "Slope Shape Across"
        dFieldAliases["cosurfmorphss.shapedown"] = "Slope Shape Up/Down"
        dFieldAliases["cosurfmorphss.cogeomdkey"] = "Component Geomorphic Description Key"
        dFieldAliases["cosurfmorphss.cosurfmorsskey"] = "Component Surface Morphometry - Slope Shape Key"
        dFieldAliases["cotaxfmmin.taxminalogy"] = "Mineralogy"
        dFieldAliases["cotaxfmmin.cokey"] = "Component Key"
        dFieldAliases["cotaxfmmin.cotaxfmminkey"] = "Component Taxonomic Family Mineralogy Key"
        dFieldAliases["cotaxmoistcl.taxmoistcl"] = "Moisture Class"
        dFieldAliases["cotaxmoistcl.cokey"] = "Component Key"
        dFieldAliases["cotaxmoistcl.cotaxmckey"] = "Component Taxonomic Family Moisture Class Key"
        dFieldAliases["cotext.recdate"] = "Date"
        dFieldAliases["cotext.comptextkind"] = "Kind"
        dFieldAliases["cotext.textcat"] = "Category"
        dFieldAliases["cotext.textsubcat"] = "Subcategory"
        dFieldAliases["cotext.text"] = "Text"
        dFieldAliases["cotext.cokey"] = "Component Key"
        dFieldAliases["cotext.cotextkey"] = "Component Text Key"
        dFieldAliases["cotreestomng.plantsym"] = "Plant Symbol"
        dFieldAliases["cotreestomng.plantsciname"] = "Scientific Name"
        dFieldAliases["cotreestomng.plantcomname"] = "Common Name"
        dFieldAliases["cotreestomng.cokey"] = "Component Key"
        dFieldAliases["cotreestomng.cotreestomngkey"] = "Component Trees to Manage Key"
        dFieldAliases["cotxfmother.taxfamother"] = "Family Other"
        dFieldAliases["cotxfmother.cokey"] = "Component Key"
        dFieldAliases["cotxfmother.cotaxfokey"] = "Component Taxonomic Family Other Key"
        dFieldAliases["distinterpmd.rulename"] = "Rule Name"
        dFieldAliases["distinterpmd.ruledesign"] = "Rule Design"
        dFieldAliases["distinterpmd.ruledesc"] = "Description"
        dFieldAliases["distinterpmd.dataafuse"] = "Ready to use?"
        dFieldAliases["distinterpmd.mrecentrulecwlu"] = "Most Recent Rule Component When Last Updated"
        dFieldAliases["distinterpmd.rulekey"] = "Rule Key"
        dFieldAliases["distinterpmd.distmdkey"] = "Distribution Metadata Key"
        dFieldAliases["distinterpmd.distinterpmdkey"] = "Distribution Interpretation Metadata Key"
        dFieldAliases["distlegendmd.areatypename"] = "Area Type Name"
        dFieldAliases["distlegendmd.areasymbol"] = "Area Symbol"
        dFieldAliases["distlegendmd.areaname"] = "Area Name"
        dFieldAliases["distlegendmd.ssastatus"] = "Survey Status"
        dFieldAliases["distlegendmd.cordate"] = "Correlation Date"
        dFieldAliases["distlegendmd.exportcertstatus"] = "Export Certification Status"
        dFieldAliases["distlegendmd.exportcertdate"] = "Export Certification Date"
        dFieldAliases["distlegendmd.exportmetadata"] = "Export Metadata"
        dFieldAliases["distlegendmd.lkey"] = "Legend Key"
        dFieldAliases["distlegendmd.distmdkey"] = "Distribution Metadata Key"
        dFieldAliases["distlegendmd.distlegendmdkey"] = "Distribution Legend Metadata Key"
        dFieldAliases["distmd.distgendate"] = "Distribution Generation Date"
        dFieldAliases["distmd.diststatus"] = "Distribution Status"
        dFieldAliases["distmd.interpmaxreasons"] = "Interpretation Maximum Reasons"
        dFieldAliases["distmd.distmdkey"] = "Distribution Metadata Key"
        dFieldAliases["featdesc.areasymbol"] = "Area Symbol"
        dFieldAliases["featdesc.spatialversion"] = "Spatial Version"
        dFieldAliases["featdesc.featsym"] = "Feature Symbol"
        dFieldAliases["featdesc.featname"] = "Feature Name"
        dFieldAliases["featdesc.featdesc"] = "Feature Description"
        dFieldAliases["featdesc.featkey"] = "Feature Key"
        dFieldAliases["featline.areasymbol"] = "Area Symbol"
        dFieldAliases["featline.spatialversion"] = "Spatial Version"
        dFieldAliases["featline.featsym"] = "Feature Symbol"
        dFieldAliases["featline.featkey"] = "Feature Key"
        dFieldAliases["featpoint.areasymbol"] = "Area Symbol"
        dFieldAliases["featpoint.spatialversion"] = "Spatial Version"
        dFieldAliases["featpoint.featsym"] = "Feature Symbol"
        dFieldAliases["featpoint.featkey"] = "Feature Key"
        dFieldAliases["laoverlap.areatypename"] = "Area Type Name"
        dFieldAliases["laoverlap.areasymbol"] = "Area Symbol"
        dFieldAliases["laoverlap.areaname"] = "Area Name"
        dFieldAliases["laoverlap.areaovacres"] = "Overlap Acres"
        dFieldAliases["laoverlap.lkey"] = "Legend Key"
        dFieldAliases["laoverlap.lareaovkey"] = "Legend Area Overlap Key"
        dFieldAliases["legend.areatypename"] = "Area Type Name"
        dFieldAliases["legend.areasymbol"] = "Area Symbol"
        dFieldAliases["legend.areaname"] = "Area Name"
        dFieldAliases["legend.areaacres"] = "Area Acres"
        dFieldAliases["legend.mlraoffice"] = "MLRA Office"
        dFieldAliases["legend.legenddesc"] = "Legend Description"
        dFieldAliases["legend.ssastatus"] = "Survey Status"
        dFieldAliases["legend.mouagncyresp"] = "MOU Agency Responsible"
        dFieldAliases["legend.projectscale"] = "Project Scale"
        dFieldAliases["legend.cordate"] = "Correlation Date"
        dFieldAliases["legend.ssurgoarchived"] = "SSURGO Archived"
        dFieldAliases["legend.legendsuituse"] = "Geographic Applicability"
        dFieldAliases["legend.legendcertstat"] = "Legend Certification Status"
        dFieldAliases["legend.lkey"] = "Legend Key"
        dFieldAliases["legendtext.recdate"] = "Date"
        dFieldAliases["legendtext.legendtextkind"] = "Kind"
        dFieldAliases["legendtext.textcat"] = "Category"
        dFieldAliases["legendtext.textsubcat"] = "Subcategory"
        dFieldAliases["legendtext.text"] = "Text"
        dFieldAliases["legendtext.lkey"] = "Legend Key"
        dFieldAliases["legendtext.legtextkey"] = "Legend Text Key"
        dFieldAliases["mapunit.musym"] = "Mapunit Symbol"
        dFieldAliases["mapunit.muname"] = "Mapunit Name"
        dFieldAliases["mapunit.mukind"] = "Kind"
        dFieldAliases["mapunit.mustatus"] = "Status"
        dFieldAliases["mapunit.muacres"] = "Total Acres"
        dFieldAliases["mapunit.mapunitlfw_l"] = "Linear Feature Width - Low Value"
        dFieldAliases["mapunit.mapunitlfw_r"] = "Linear Feature Width - Representative Value"
        dFieldAliases["mapunit.mapunitlfw_h"] = "Linear Feature Width - High Value"
        dFieldAliases["mapunit.mapunitpfa_l"] = "Point Feature Area - Low Value"
        dFieldAliases["mapunit.mapunitpfa_r"] = "Point Feature Area - Representative Value"
        dFieldAliases["mapunit.mapunitpfa_h"] = "Point Feature Area - High Value"
        dFieldAliases["mapunit.farmlndcl"] = "Farm Class"
        dFieldAliases["mapunit.muhelcl"] = "HEL"
        dFieldAliases["mapunit.muwathelcl"] = "HEL Water"
        dFieldAliases["mapunit.muwndhelcl"] = "HEL Wind"
        dFieldAliases["mapunit.interpfocus"] = "Interpretive Focus"
        dFieldAliases["mapunit.invesintens"] = "Order of Mapping"
        dFieldAliases["mapunit.iacornsr"] = "IA CSR"
        dFieldAliases["mapunit.nhiforsoigrp"] = "NH Forest Soil Group"
        dFieldAliases["mapunit.nhspiagr"] = "NH SPI Agr"
        dFieldAliases["mapunit.vtsepticsyscl"] = "VT Septic System"
        dFieldAliases["mapunit.mucertstat"] = "Map Unit Certification Status"
        dFieldAliases["mapunit.lkey"] = "Legend Key"
        dFieldAliases["mapunit.mukey"] = "Mapunit Key"
        dFieldAliases["mdstatdomdet.domainname"] = "Domain Name"
        dFieldAliases["mdstatdomdet.choicesequence"] = "Choice Sequence"
        dFieldAliases["mdstatdomdet.choice"] = "Choice"
        dFieldAliases["mdstatdomdet.choicedesc"] = "Choice Description"
        dFieldAliases["mdstatdomdet.choiceobsolete"] = "Obsolete Choice?"
        dFieldAliases["mdstatdommas.domainname"] = "Domain Name"
        dFieldAliases["mdstatdommas.domainmaxlen"] = "Domain Maximum Length"
        dFieldAliases["mdstatidxdet.tabphyname"] = "Table Physical Name"
        dFieldAliases["mdstatidxdet.idxphyname"] = "Index Physical Name"
        dFieldAliases["mdstatidxdet.idxcolsequence"] = "Index Column Sequence"
        dFieldAliases["mdstatidxdet.colphyname"] = "Column Physical Name"
        dFieldAliases["mdstatidxmas.tabphyname"] = "Table Physical Name"
        dFieldAliases["mdstatidxmas.idxphyname"] = "Index Physical Name"
        dFieldAliases["mdstatidxmas.uniqueindex"] = "Unique Index?"
        dFieldAliases["mdstatrshipdet.ltabphyname"] = "Left Table Physical Name"
        dFieldAliases["mdstatrshipdet.rtabphyname"] = "Right Table Physical Name"
        dFieldAliases["mdstatrshipdet.relationshipname"] = "Relationship Name"
        dFieldAliases["mdstatrshipdet.ltabcolphyname"] = "Left Table Column Physical Name"
        dFieldAliases["mdstatrshipdet.rtabcolphyname"] = "Right Table Column Physical Name"
        dFieldAliases["mdstatrshipmas.ltabphyname"] = "Left Table Physical Name"
        dFieldAliases["mdstatrshipmas.rtabphyname"] = "Right Table Physical Name"
        dFieldAliases["mdstatrshipmas.relationshipname"] = "Relationship Name"
        dFieldAliases["mdstatrshipmas.cardinality"] = "Cardinality"
        dFieldAliases["mdstatrshipmas.mandatory"] = "Mandatory?"
        dFieldAliases["mdstattabcols.tabphyname"] = "Table Physical Name"
        dFieldAliases["mdstattabcols.colsequence"] = "Column Sequence"
        dFieldAliases["mdstattabcols.colphyname"] = "Column Physical Name"
        dFieldAliases["mdstattabcols.collogname"] = "Column Logical Name"
        dFieldAliases["mdstattabcols.collabel"] = "Column Label"
        dFieldAliases["mdstattabcols.logicaldatatype"] = "Logical Data Type"
        dFieldAliases["mdstattabcols.notnull"] = "Not Null?"
        dFieldAliases["mdstattabcols.fieldsize"] = "Field Size"
        dFieldAliases["mdstattabcols.precision"] = "Precision"
        dFieldAliases["mdstattabcols.minimum"] = "Minimum"
        dFieldAliases["mdstattabcols.maximum"] = "Maximum"
        dFieldAliases["mdstattabcols.uom"] = "Unit of Measure"
        dFieldAliases["mdstattabcols.domainname"] = "Domain Name"
        dFieldAliases["mdstattabcols.coldesc"] = "Column Description"
        dFieldAliases["mdstattabs.tabphyname"] = "Table Physical Name"
        dFieldAliases["mdstattabs.tablogname"] = "Table Logical Name"
        dFieldAliases["mdstattabs.tablabel"] = "Table Label"
        dFieldAliases["mdstattabs.tabdesc"] = "Table Description"
        dFieldAliases["mdstattabs.iefilename"] = "Import/Export File Name"
        dFieldAliases["month.monthseq"] = "Month Sequence"
        dFieldAliases["month.monthname"] = "Month Name"
        dFieldAliases["muaggatt.musym"] = "Mapunit Symbol"
        dFieldAliases["muaggatt.muname"] = "Mapunit Name"
        dFieldAliases["muaggatt.mustatus"] = "Status"
        dFieldAliases["muaggatt.slopegraddcp"] = "Slope Gradient - Dominant Component"
        dFieldAliases["muaggatt.slopegradwta"] = "Slope Gradient - Weighted Average"
        dFieldAliases["muaggatt.brockdepmin"] = "Bedrock Depth - Minimum"
        dFieldAliases["muaggatt.wtdepannmin"] = "Water Table Depth - Annual - Minimum"
        dFieldAliases["muaggatt.wtdepaprjunmin"] = "Water Table Depth - April - June - Minimum"
        dFieldAliases["muaggatt.flodfreqdcd"] = "Flooding Frequency - Dominant Condition"
        dFieldAliases["muaggatt.flodfreqmax"] = "Flooding Frequency - Maximum"
        dFieldAliases["muaggatt.pondfreqprs"] = "Ponding Frequency - Presence"
        dFieldAliases["muaggatt.aws025wta"] = "Available Water Storage 0-25 cm - Weighted Average"
        dFieldAliases["muaggatt.aws050wta"] = "Available Water Storage 0-50 cm - Weighted Average"
        dFieldAliases["muaggatt.aws0100wta"] = "Available Water Storage 0-100 cm - Weighted Average"
        dFieldAliases["muaggatt.aws0150wta"] = "Available Water Storage 0-150 cm - Weighted Average"
        dFieldAliases["muaggatt.drclassdcd"] = "Drainage Class - Dominant Condition"
        dFieldAliases["muaggatt.drclasswettest"] = "Drainage Class - Wettest"
        dFieldAliases["muaggatt.hydgrpdcd"] = "Hydrologic Group - Dominant Conditions"
        dFieldAliases["muaggatt.iccdcd"] = "Irrigated Capability Class - Dominant Condition"
        dFieldAliases["muaggatt.iccdcdpct"] = "Irrigated Capability Class  - Dominant Condition Aggregate Percent"
        dFieldAliases["muaggatt.niccdcd"] = "Non-Irrigated Capability Class - Dominant Condition"
        dFieldAliases["muaggatt.niccdcdpct"] = "Non-Irrigated Capability Class  - Dominant Condition Aggregate Percent"
        dFieldAliases["muaggatt.engdwobdcd"] = "ENG - Dwellings W/O Basements - Dominant Condition"
        dFieldAliases["muaggatt.engdwbdcd"] = "ENG - Dwellings with Basements - Dominant Condition"
        dFieldAliases["muaggatt.engdwbll"] = "ENG - Dwellings with Basements - Least Limiting"
        dFieldAliases["muaggatt.engdwbml"] = "ENG - Dwellings with Basements - Most Limiting"
        dFieldAliases["muaggatt.engstafdcd"] = "ENG - Septic Tank Absorption Fields - Dominant Condition"
        dFieldAliases["muaggatt.engstafll"] = "ENG - Septic Tank Absorption Fields - Least Limiting"
        dFieldAliases["muaggatt.engstafml"] = "ENG - Septic Tank Absorption Fields - Most Limiting"
        dFieldAliases["muaggatt.engsldcd"] = "ENG - Sewage Lagoons - Dominant Condition"
        dFieldAliases["muaggatt.engsldcp"] = "ENG - Sewage Lagoons - Dominant Component"
        dFieldAliases["muaggatt.englrsdcd"] = "ENG - Local Roads and Streets - Dominant Condition"
        dFieldAliases["muaggatt.engcmssdcd"] = "ENG - Construction Materials; Sand Source - Dominant Condition"
        dFieldAliases["muaggatt.engcmssmp"] = "ENG - Construction Materials; Sand Source - Most Probable"
        dFieldAliases["muaggatt.urbrecptdcd"] = "URB/REC - Paths and Trails - Dominant Condition"
        dFieldAliases["muaggatt.urbrecptwta"] = "URB/REC - Paths and Trails - Weighted Average"
        dFieldAliases["muaggatt.forpehrtdcp"] = "FOR - Potential Erosion Hazard (Road/Trail) - Dominant Component"
        dFieldAliases["muaggatt.hydclprs"] = "Hydric Classification - Presence"
        dFieldAliases["muaggatt.awmmfpwwta"] = "AWM - Manure and Food Processing Waste - Weighted Average"
        dFieldAliases["muaggatt.mukey"] = "Mapunit Key"
        dFieldAliases["muaoverlap.areaovacres"] = "Overlap Acres"
        dFieldAliases["muaoverlap.lareaovkey"] = "Legend Area Overlap Key"
        dFieldAliases["muaoverlap.mukey"] = "Mapunit Key"
        dFieldAliases["muaoverlap.muareaovkey"] = "Mapunit Area Overlap Key"
        dFieldAliases["mucropyld.cropname"] = "Crop Name"
        dFieldAliases["mucropyld.yldunits"] = "Units"
        dFieldAliases["mucropyld.nonirryield_l"] = "Nirr Yield - Low Value"
        dFieldAliases["mucropyld.nonirryield_r"] = "Nirr Yield - Representative Value"
        dFieldAliases["mucropyld.nonirryield_h"] = "Nirr Yield - High Value"
        dFieldAliases["mucropyld.irryield_l"] = "Irr Yield - Low Value"
        dFieldAliases["mucropyld.irryield_r"] = "Irr Yield - Representative Value"
        dFieldAliases["mucropyld.irryield_h"] = "Irr Yield - High Value"
        dFieldAliases["mucropyld.mukey"] = "Mapunit Key"
        dFieldAliases["mucropyld.mucrpyldkey"] = "Mapunit Crop Yield Key"
        dFieldAliases["muline.areasymbol"] = "Area Symbol"
        dFieldAliases["muline.spatialversion"] = "Spatial Version"
        dFieldAliases["muline.musym"] = "Mapunit Symbol"
        dFieldAliases["muline.mukey"] = "Mapunit Key"
        dFieldAliases["mupoint.areasymbol"] = "Area Symbol"
        dFieldAliases["mupoint.spatialversion"] = "Spatial Version"
        dFieldAliases["mupoint.musym"] = "Mapunit Symbol"
        dFieldAliases["mupoint.mukey"] = "Mapunit Key"
        dFieldAliases["mupolygon.areasymbol"] = "Area Symbol"
        dFieldAliases["mupolygon.spatialversion"] = "Spatial Version"
        dFieldAliases["mupolygon.musym"] = "Mapunit Symbol"
        dFieldAliases["mupolygon.mukey"] = "Mapunit Key"
        dFieldAliases["mutext.recdate"] = "Date"
        dFieldAliases["mutext.mapunittextkind"] = "Kind"
        dFieldAliases["mutext.textcat"] = "Category"
        dFieldAliases["mutext.textsubcat"] = "Subcategory"
        dFieldAliases["mutext.text"] = "Text"
        dFieldAliases["mutext.mukey"] = "Mapunit Key"
        dFieldAliases["mutext.mutextkey"] = "Mapunit Text Key"
        dFieldAliases["sacatalog.areasymbol"] = "Area Symbol"
        dFieldAliases["sacatalog.areaname"] = "Area Name"
        dFieldAliases["sacatalog.saversion"] = "Survey Area Version"
        dFieldAliases["sacatalog.saverest"] = "Survey Area Version Established"
        dFieldAliases["sacatalog.tabularversion"] = "Tabular Version"
        dFieldAliases["sacatalog.tabularverest"] = "Tabular Version Established"
        dFieldAliases["sacatalog.tabnasisexportdate"] = "Tabular NASIS Export Date"
        dFieldAliases["sacatalog.tabcertstatus"] = "Tabular Certification Status"
        dFieldAliases["sacatalog.tabcertstatusdesc"] = "Tabular Certification Status Description"
        dFieldAliases["sacatalog.fgdcmetadata"] = "FGDC Metadata"
        dFieldAliases["sacatalog.sacatalogkey"] = "Survey Area Catalog Key"
        dFieldAliases["sainterp.areasymbol"] = "Area Symbol"
        dFieldAliases["sainterp.interpname"] = "Interpretation Name"
        dFieldAliases["sainterp.interptype"] = "Interpretation Type"
        dFieldAliases["sainterp.interpdesc"] = "Interpretation Description"
        dFieldAliases["sainterp.interpdesigndate"] = "Interpretation Design Date"
        dFieldAliases["sainterp.interpgendate"] = "Interpretation Generation Date"
        dFieldAliases["sainterp.interpmaxreasons"] = "Interpretation Maximum Reasons"
        dFieldAliases["sainterp.sacatalogkey"] = "Survey Area Catalog Key"
        dFieldAliases["sainterp.sainterpkey"] = "Survey Area Interpretation Key"
        dFieldAliases["sapolygon.areasymbol"] = "Area Symbol"
        dFieldAliases["sapolygon.spatialversion"] = "Spatial Version"
        dFieldAliases["sapolygon.lkey"] = "Legend Key"
        dFieldAliases["sdvalgorithm.algorithmsequence"] = "Algorithm Sequence"
        dFieldAliases["sdvalgorithm.algorithmname"] = "Algorithm Name"
        dFieldAliases["sdvalgorithm.algorithminitials"] = "Algorithm Initials"
        dFieldAliases["sdvalgorithm.algorithmdescription"] = "Algorithm Description"
        dFieldAliases["sdvattribute.attributekey"] = "Attribute Key"
        dFieldAliases["sdvattribute.attributename"] = "Attribute Name"
        dFieldAliases["sdvattribute.attributetablename"] = "Attribute Table Name"
        dFieldAliases["sdvattribute.attributecolumnname"] = "Attribute Column Name"
        dFieldAliases["sdvattribute.attributelogicaldatatype"] = "Attribute Logical Data Type"
        dFieldAliases["sdvattribute.attributefieldsize"] = "Attribute Field Size"
        dFieldAliases["sdvattribute.attributeprecision"] = "Attribute Precision"
        dFieldAliases["sdvattribute.attributedescription"] = "Attribute Description"
        dFieldAliases["sdvattribute.attributeuom"] = "Attribute Units of Measure"
        dFieldAliases["sdvattribute.attributeuomabbrev"] = "Attribute Units of Measure Abbreviation"
        dFieldAliases["sdvattribute.attributetype"] = "Attribute Type"
        dFieldAliases["sdvattribute.nasisrulename"] = "NASIS Rule Name"
        dFieldAliases["sdvattribute.ruledesign"] = "Rule Design"
        dFieldAliases["sdvattribute.notratedphrase"] = "Not Rated Phrase"
        dFieldAliases["sdvattribute.mapunitlevelattribflag"] = "Map Unit Level Attribute Flag"
        dFieldAliases["sdvattribute.complevelattribflag"] = "Component Level Attribute Flag"
        dFieldAliases["sdvattribute.cmonthlevelattribflag"] = "Component Month Level Attribute Flag"
        dFieldAliases["sdvattribute.horzlevelattribflag"] = "Horizon Level Attribute Flag"
        dFieldAliases["sdvattribute.tiebreakdomainname"] = "Tie Break Domain Name"
        dFieldAliases["sdvattribute.tiebreakruleoptionflag"] = "Tie Break Rule Option Flag"
        dFieldAliases["sdvattribute.tiebreaklowlabel"] = "Tie Break Low Label"
        dFieldAliases["sdvattribute.tiebreakhighlabel"] = "Tie Break High Label"
        dFieldAliases["sdvattribute.tiebreakrule"] = "Tie Break Rule"
        dFieldAliases["sdvattribute.resultcolumnname"] = "Result Column Name"
        dFieldAliases["sdvattribute.sqlwhereclause"] = "SQL Where Clause"
        dFieldAliases["sdvattribute.primaryconcolname"] = "Primary Constraint Column Name"
        dFieldAliases["sdvattribute.pcclogicaldatatype"] = "Primary Constraint Column Logical Data Type"
        dFieldAliases["sdvattribute.primaryconstraintlabel"] = "Primary Constraint Label"
        dFieldAliases["sdvattribute.secondaryconcolname"] = "Secondary Constraint Column Name"
        dFieldAliases["sdvattribute.scclogicaldatatype"] = "Secondary Constraint Column Logical Data Type"
        dFieldAliases["sdvattribute.secondaryconstraintlabel"] = "Secondary Constraint Label"
        dFieldAliases["sdvattribute.dqmodeoptionflag"] = "Depth Qualifier Mode Option Flag"
        dFieldAliases["sdvattribute.depthqualifiermode"] = "Depth Qualifier Mode"
        dFieldAliases["sdvattribute.layerdepthtotop"] = "Layer Depth to Top"
        dFieldAliases["sdvattribute.layerdepthtobottom"] = "Layer Depth to Bottom"
        dFieldAliases["sdvattribute.layerdepthuom"] = "Layer Depth UOM"
        dFieldAliases["sdvattribute.monthrangeoptionflag"] = "Month Range Option Flag"
        dFieldAliases["sdvattribute.beginningmonth"] = "Beginning Month"
        dFieldAliases["sdvattribute.endingmonth"] = "Ending Month"
        dFieldAliases["sdvattribute.fetchallcompsflag"] = "Fetch All Components Flag"
        dFieldAliases["sdvattribute.interpnullsaszerooptionflag"] = "Interpret Nulls as Zero Option Flag"
        dFieldAliases["sdvattribute.interpnullsaszeroflag"] = "Interpret Nulls as Zero Flag"
        dFieldAliases["sdvattribute.nullratingreplacementvalue"] = "Null Rating Replacement Value"
        dFieldAliases["sdvattribute.basicmodeflag"] = "Basic Mode Flag"
        dFieldAliases["sdvattribute.maplegendkey"] = "Map Legend Key"
        dFieldAliases["sdvattribute.maplegendclasses"] = "Map Legend Classes"
        dFieldAliases["sdvattribute.maplegendxml"] = "Map Legend XML"
        dFieldAliases["sdvattribute.nasissiteid"] = "NASIS Site ID"
        dFieldAliases["sdvattribute.wlupdated"] = "Last Updated"
        dFieldAliases["sdvattribute.algorithmname"] = "Algorithm Name"
        dFieldAliases["sdvattribute.componentpercentcutoff"] = "Component Percent Cutoff"
        dFieldAliases["sdvattribute.readytodistribute"] = "Ready to Distribute"
        dFieldAliases["sdvfolder.foldersequence"] = "Folder Sequence"
        dFieldAliases["sdvfolder.foldername"] = "Folder Name"
        dFieldAliases["sdvfolder.folderdescription"] = "Folder Description"
        dFieldAliases["sdvfolder.folderkey"] = "Folder Key"
        dFieldAliases["sdvfolder.parentfolderkey"] = "Parent Folder Key"
        dFieldAliases["sdvfolder.wlupdated"] = "Last Updated"
        dFieldAliases["sdvfolderattribute.folderkey"] = "Folder Key"
        dFieldAliases["sdvfolderattribute.attributekey"] = "Attribute Key"

        return dFieldAliases

    except:
        errorMsg()

## ===================================================================================
def SetFieldAliases(theOWS):
    # Test: directly edit the GDB_FieldInfo table to set field aliases
    #
    # Check out the GDB_FieldInfo table
    #               ClassID - table number? relates to where to get the name?
    #               FieldName - original field name
    #               AliasName - new field alias
    #               ModelName - appears to be same as FieldName value
    #
    # The GDB_ObjectClasses table has table name and relates to GDB_FieldInfo table
    #               ID - relates to ClassID
    #               Name - Table name
    #               AliasName - Table alias

    # create query string depending upon output database type (PGDB delimiter = [ and FGDB = ")

    try:
        PrintMsg(" \nSetting aliases for columns in each table...", 0)
        arcpy.Workspace = theOWS
        Tbl_FieldInfo = os.path.join(theOWS, "GDB_FieldInfo")
        Tbl_OC = os.path.join(theOWS,"GDB_ObjectClasses")

        if not arcpy.Exists(Tbl_OC):
            PrintMsg("\nTable " + Tbl_OC + " not found",2)
            return False

        if not arcpy.Exists(Tbl_FieldInfo):
            PrintMsg("\nTable " + Tbl_FieldInfo + " not found",2)
            return False

        # Get dictionary containing field aliases (change this to use output database metadata tables)
        dFieldAliases = GetFieldAliases()

        # Get dictionary containing table names. Key is table ID in GDB_ObjectClasses table.
        dTableIDs = GetTableIDs(theOWS)

        #
        dTableNames = GetTableNames(theOWS)

        # Create sorted list of table names using dTableNames dictionary
        tblList = dTableNames.keys()
        tblList.sort()

        theCursor = arcpy.InsertCursor(Tbl_FieldInfo)
        theRec = theCursor.next()

        for theTable in tblList:
            #PrintMsg("Getting info from tblList", 0)
            #
            # Get validated table name
            # The problem for the "MONTH" table is that at this point, "theTable" is
            # already "MONTH_".
            theNewTable = arcpy.ValidateTableName(theTable, theOWS)

            if theTable in dTableNames:
                theID = dTableNames[theTable]
                #PrintMsg(theTable + ": getting field aliases", 0)
                # Create list of fields for this table
                PrintMsg("\t" + theTable , 1)
                theFields = arcpy.ListFields(theOWS + "\\" + theNewTable)
                #theField = theFields.next()

                #while theField:
                for theField in theFields:
                    theFieldName = theField.Name
                    skipList = ["OBJECTID","SHAPE","SHAPE_AREA","SHAPE_LENGTH"]

                    if not theFieldName.upper() in skipList:

                        theFKey = theNewTable.lower() + "." + theFieldName.lower()

                        if theFKey in dFieldAliases:
                            # get field alias
                            theFieldAlias = dFieldAliases[theFKey]

                            fieldQuery = "ClassID = " + str(theID) + " AND FieldName = '" + theFieldName + "'"
                            upCursor = arcpy.SearchCursor(Tbl_FieldInfo, fieldQuery)
                            upRec = upCursor.next()

                            if upRec is None:
                                del upCursor
                                del upRec
                                PrintMsg("\t\tSetting alias for " + theFieldName + " to '" + theFieldAlias + "'", 0)
                                inCursor = arcpy.InsertCursor(Tbl_FieldInfo)
                                inRec = inCursor.NewRow()
                                inRec.ClassID = theID
                                inRec.FieldName = theFieldName
                                inRec.AliasName = theFieldAlias
                                inRec.ModelName = theFieldName
                                inRec.IsRequired = 0
                                inRec.IsSubtypeFixed = 0
                                inRec.IsEditable = 1
                                inCursor.InsertRow(inRec)
                                del inCursor
                                del inRec

            else:
                PrintMsg("Missing table key for: " + theTable, 0)
                return False

        return True

    except:
        errorMsg()

        try:
            del theCursor
            del theRec

        except:
            pass

        return False

## ===================================================================================
def GetTableIDs(theOWS):
    # Create dictionary object containing table names keyed by ID. This will be used aid in
    # setting field aliases???. Workspace is the Output Geodatabase
    # The GDB_ObjectClasses table has table name and relates to GDB_FieldInfo table
    #               ID - relates to ClassID
    #               Name - Table name

    arcpy.workspace = theOWS
    theTable = "GDB_ObjectClasses"
    dTableIDs = dict()

    if not arcpy.Exists(theTable):
        PrintMsg("Missing metadata table: " + theTable + " (GetTableIDs)", 1)
        return dTableIDs

    try:
        # Initialize variables
        tableName = ""
        theFieldName = ""

        # Open mdstattabcols table in new workspace
        theCursor = arcpy.SearchCursor(theTable)
        theRec = theCursor.Next()

        while theRec:
            # Read GDB_ObjectClasses and use it to load dictionary
            theID = theRec.ID
            tableName = theRec.Name
            dTableIDs[theID] = tableName.lower()
            theRec = theCursor.Next()
            #PrintMsg("\tTable " + str(theID) + ": " + tableName.lower(), 0)

        del theCursor
        del theRec
        return dTableIDs

    except MyError():
        PrintMsg(err, 2)
        return dTableIDs

    except:
        errorMsg()
        return dTableIDs

## ===================================================================================
def GetTableNames(theOWS):
    # Create dictionary object containing table names keyed by ID. This will be used aid in
    # setting field aliases???. Workspace is the Output Geodatabase
    # The GDB_ObjectClasses table has table name and relates to GDB_FieldInfo table
    #               ID - relates to ClassID
    #               Name - Table name

    arcpy.workspace = theOWS
    theTable = "GDB_ObjectClasses"
    dTableNames = dict()

    if not arcpy.Exists(theTable):
        PrintMsg("Missing metadata table: " + theTable + " (GetTableNames)", 1)
        return dTableIDs

    try:
        # Initialize variables
        tableName = ""
        theFieldName = ""

        theCursor = arcpy.SearchCursor(theTable)
        theRec = theCursor.Next()

        while theRec:
            # Read GDB_ObjectClasses and use it to load dictionary
            theID = theRec.ID
            tableName = theRec.Name.lower()
            dTableNames[tableName] = theID
            theRec = theCursor.Next()
            #PrintMsg("\tSaved table ID for " + tableName + " (" + str(theID) + ")", 0)

        del theCursor
        del theRec
        return dTableNames

    except MyError():
        PrintMsg(err, 2)
        return dTableNames

    except:
        errorMsg()
        return dTableNames

## ===================================================================================
def GetTableAliases(theWorkspace):
    # Retrieve table aliases from MDSTATTABS table.
    # Use aliases in schema and relationshipclass labels. Stores physical names (key) and
    # aliases (value) in a Python dictionary.
    # Table Aliases are stored in the GDB_ObjectClasses table. Fieldnames are Name and AliasName.

    try:
        # Open mdstattabs table containing information for other SSURGO tables
        theMDTable = "mdstattabs"
        tblAliases = dict()

        if arcpy.Exists(theWorkspace + "\\" + theMDTable):
            theCursor = arcpy.SearchCursor(theWorkspace + "\\" + theMDTable)
            theRec = theCursor.Next()

            while theRec:
                # read each table record and load dictionary
                physicalName = theRec.tabphyname
                aliasName = theRec.tablabel

                if not tblAliases.has_key(physicalName):
                    tblAliases[physicalName] = aliasName

                theRec = theCursor.Next()

            del theCursor
            del theRec

            return tblAliases

        else:
            PrintMsg("\nUnable to get table aliases (missing mdstattabs table)", 2)
            return tblAliases

    except:
        errorMsg()
        return tblAliases

## ===================================================================================
def SetTableAliases(theWorkspace):
    # Implement table aliases (originating from "GetTableAliases function) by
    # editing the GDB_ObjectClasses table (not sure how good an idea this is!)

    try:
        PrintMsg("\nSetting featureclass and table aliases in new geodatabase", 0)
        tblAliases = GetTableAliases(theWorkspace)

        nameField = "Name"
        aliasField = "AliasName"

        if arcpy.Exists(os.path.join(theWorkspace, "GDB_ObjectClasses")):
            theCursor = arcpy.UpdateCursor(os.path.join(theWorkspace,"GDB_ObjectClasses"))
            rec = theCursor.Next()

            while rec:
                theTableName = rec.GetValue("Name")

                if arcpy.Exists(os.path.join(theWorkspace, theTableName)):

                    if theTableName.lower() in tblAliases:
                        theAlias = tblAliases[theTableName.lower()]
                        rec.AliasName = theAlias
                        PrintMsg("\t" + theTableName + " --> " + theAlias, 1)
                        theCursor.UpdateRow(rec)

                else:
                    PrintMsg("Missing table or fc: " + theTableName, 0)

                rec = theCursor.Next()

            del theCursor
            del rec
            return True

        else:
            PrintMsg(" \nGDB_ObjectClasses table not found, unable to access table aliases", 2)
            return False

        return True

    except:
        errorMsg()
        return False

## ===================================================================================
def CreateFieldAliases(InputDB):
    # Not being used any more. Using hardcoded aliases now.
    # Create dictionary object containing field aliases. With the TableToTable method
    # I need the aliases BEFORE copying Access Template tables to new geodatabase.

    arcpy.Workspace = InputDB
    theMDTable = "mdstattabcols"
    theFieldAliases = dict()

    if not arcpy.Exists(theMDTable):
        PrintMsg("Missing metadata table: " + theMDTable + " (CreateFieldAliases)", 1)
        return theFieldAliases

    try:
        # Initialize variables
        tableName = ""
        theFieldName = ""
        theFieldAlias = ""

        # Open mdstattabcols table in new workspace
        theCursor = arcpy.SearchCursor(theMDTable)
        theRec = theCursor.Next()

        while theRec:
            # Read mdstattabcols and use it to load dictionary
            tableName = theRec.tabphyname
            theFieldName = theRec.colphyname
            theFieldAlias = theRec.collabel
            theKey = arcpy.ValidateTableName(tableName, InputDB) + "." + theFieldName
            theFieldAliases[theKey] = theFieldAlias
            theRec = theCursor.Next()

        del theCursor
        del theRec
        return theFieldAliases

    except:
        errorMsg()
        return theFieldAliases

## ===================================================================================
def GetFCType(fc):
    # Determine featureclass type  featuretype and table fields
    # Rename featureclasses from old shapefile-based name to new, shorter name
    # Returns new featureclass name using DSS convention for geodatabase
    #
    # The check for table fields is the absolute minimum

    featType = ""

    # Look for minimum list of required fields
    #
    if FindField(fc, "MUSYM"):
        hasMusym = True

    else:
        hasMusym = False

    if FindField(fc, "LKEY"):
        hasLkey = True

    else:
        hasLkey = False

    if FindField(fc, "FEATSYM"):
        hasFeatsym = True

    else:
        hasFeatsym = False

    if FindField(fc, "SAPUBSTATUSCODE"):
        hasStatus = True

    else:
        hasStatus = False

    if FindField(fc, "AREASYMBOL"):
        hasAreasymbol = True

    else:
        hasAreasymbol = False

    try:
        fcName = os.path.basename(fc)
        theDescription = arcpy.Describe(fc)
        featType = theDescription.ShapeType

        # Mapunit Features
        if hasMusym:
            if featType == "Polygon" and fcName.upper() != "MUPOINT":
                dataType = "Mapunit Polygon"

            elif featType == "Polyline":
                dataType = "Mapunit Line"

            elif featType == "Point" or featType == "Multipoint" or fcName.upper() == "MUPOINT":
                dataType = "Mapunit Point"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an MUSYM field (GetFCName)", 2)
                dataType = ""

        # Survey Area Boundary
        if hasLkey:
            if featType == "Polygon":
                dataType = "Survey Boundary"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an LKEY field (GetFCName)", 2)
                dataType = ""

        # Survey Area Status Map
        if hasStatus and hasAreasymbol:
            if featType == "Polygon":
                dataType = "Survey Status Map"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an AREASYMBOL field (GetFCName)", 2)
                dataType = ""

        # Special Features
        if hasFeatsym:
            # Special Feature Line
            if featType == "Polyline":
                dataType = "Special Feature Line"

            # Special Feature Point
            elif featType == "Point" or featType == "Multipoint":
                dataType = "Special Feature Point"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an FEATSYM field (GetFCName)", 2)
                dataType = ""

        return dataType

    except:
        errorMsg()
        return ""

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import arcpy, sys, string, os, locale, arcgisscripting, traceback, math, time
from arcpy import env

try:
    # Create geoprocessor object
    #gp = arcgisscripting.create(9.3)
    #arcpy.OverwriteOutput = 1

    scriptname = sys.argv[0]
    wksp = arcpy.GetParameterAsText(0)   # input geodatabase containing SSURGO tables and featureclasses
    bOverwrite = arcpy.GetParameter(1)   # overwrite option independant of gp environment setting
    bFldAliases = arcpy.GetParameter(2)  # boolean: if SSURGO metatata tables are present, create field aliases
    bTblAliases = arcpy.GetParameter(3)  # boolean: if SSURGO metadata tables are present, create table aliases

    env.workspace = wksp
    env.overWriteOutput = True

    begin = time.time()
    # Create relationshipclasses
    bRL = CreateRL(wksp, bOverwrite)

    # Create table aliases
    #if bTblAliases:
    #    bSuccessful = SetTableAliases(wksp)

    # Create field aliases
    #if bFldAliases:
    #    bSuccesful = SetFieldAliases(wksp)

    theMsg = " \n" + os.path.basename(scriptname) + " finished in " + elapsedTime(begin)
    PrintMsg(theMsg, 1)

except:
    errorMsg()
