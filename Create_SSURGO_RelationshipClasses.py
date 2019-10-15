# Create_SSURGO_RelationshipClasses.py
#
# Steve Peaslee August 02, 2011
#
# Creates hard-coded table relationshipclasses in a geodatabase. If SSURGO featureclasses
# are present, featureclass to table relationshipclasses will also be built. All
# tables must be registered and have OBJECTID fields. Geodatabase must have been created
# using ArcGIS 9.2 or ArcGIS 9.3. Saving back to a 9.2 version from ArcGIS 10 also seems to
# work. Not so for saving back as 9.3 version (bug?)
#
# Also sets table and field aliases using the metadata tables in the output geodatabase.
#
# Tried to fix problem where empty MUPOINT featureclass is identified as Polygon



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
    # Check table or featureclass to see if specified field exists
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
                env.workspace = fds
                fcList = arcpy.ListFeatureClasses("*")
                env.workspace = wksp

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
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "SIMPLE", "> Mapunit Polygon Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Mapunit Line":
                    
                    if bOverwrite or not arcpy.Exists("zMapunit_MULINE") and arcpy.Exists("MULINE"):
                        PrintMsg("    --> zMapunit_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "SIMPLE", "> Mapunit Line Layer", "< + Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Mapunit Point":
                    if bOverwrite or not arcpy.Exists("zMapunit_MUPOINT") and arcpy.Exists("MUPOINT"):
                        PrintMsg("    --> zMapunit_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("mapunit", fc, "zMapunit_" + fc, "SIMPLE", "> MapUnit Point Layer", "< Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "MUKEY", "","")

                elif dataType == "Special Feature Point":
                    if bOverwrite or not arcpy.Exists("zFeatdesc_FEATPOINT") and arcpy.Exists("FEATPOINT"):
                        PrintMsg("    --> zFeatdesc_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("featdesc", fc, "zFeatdesc_" + fc, "SIMPLE", "> SF Point", "< Featdesc Table", "NONE", "ONE_TO_MANY", "NONE", "featkey", "FEATKEY", "","")

                elif dataType == "Special Feature Line":
                    if bOverwrite or not arcpy.Exists("zFeatdesc_FEATLINE") and arcpy.Exists("FEATLINE"):
                        PrintMsg("    --> zFeatdesc_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("featdesc", fc, "zFeatdesc_" + fc, "SIMPLE", "> SF Line Layer", "< Featdesc Table", "NONE", "ONE_TO_MANY", "NONE", "featkey", "FEATKEY", "","")

                elif dataType == "Survey Boundary":
                    if bOverwrite or not arcpy.Exists("zLegend_SAPOLYGON"):
                        PrintMsg("    --> zLegend_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("legend", fc, "zLegend_" + fc, "SIMPLE", "> Survey Boundary Layer", "< Legend Table", "NONE", "ONE_TO_MANY", "NONE", "lkey", "LKEY", "","")

                    if bOverwrite or not arcpy.Exists("zSacatalog_SAPOLYGON"):
                        PrintMsg("    --> zSacatalog_" + fc, 1)
                        arcpy.CreateRelationshipClass_management("sacatalog", fc, "zSacatalog_" + fc, "SIMPLE", "> Survey Boundary Layer", "< Survey Area Catalog Table", "NONE", "ONE_TO_MANY", "NONE", "areasymbol", "AREASYMBOL", "","")

                else:
                    PrintMsg("Unknown SSURGO datatype for featureclass (" + fc + ")", 1)

        else:
            PrintMsg("No featureclasses found in " + arcpy.Workspace + ", \nunable to create relationshipclasses", 2)
            #return False

    except:
        errorMsg()

    try:
        PrintMsg(" \nCreating relationships between SSURGO tables...", 0)

        if bOverwrite or not arcpy.Exists("zChorizon_Chaashto"):
            PrintMsg("    --> zChorizon_Chaashto", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chaashto", "zChorizon_Chaashto", "SIMPLE", "> Horizon AASHTO Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chconsistence"):
            PrintMsg("    --> zChorizon_Chconsistence", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chconsistence", "zChorizon_Chconsistence", "SIMPLE", "> Horizon Consistence Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chdesgnsuffix"):
            PrintMsg("    --> zChorizon_Chdesgnsuffix", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chdesgnsuffix", "zChorizon_Chdesgnsuffix", "SIMPLE", "> Horizon Designation Suffix Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chfrags"):
            PrintMsg("    --> zChorizon_Chfrags", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chfrags", "zChorizon_Chfrags", "SIMPLE", "> Horizon Fragments Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chpores"):
            PrintMsg("    --> zChorizon_Chpores", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chpores", "zChorizon_Chpores", "SIMPLE", "> Horizon Pores Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chstructgrp"):
            PrintMsg("    --> zChorizon_Chstructgrp", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chstructgrp", "zChorizon_Chstructgrp", "SIMPLE", "> Horizon Structure Group Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chtext"):
            PrintMsg("    --> zChorizon_Chtext", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chtext", "zChorizon_Chtext", "SIMPLE", "> Horizon Text Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chtexturegrp"):
            PrintMsg("    --> zChorizon_Chtexturegrp", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chtexturegrp", "zChorizon_Chtexturegrp", "SIMPLE", "> Horizon Texture Group Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChorizon_Chunified"):
            PrintMsg("    --> zChorizon_Chunified", 1)
            arcpy.CreateRelationshipClass_management("chorizon", "chunified", "zChorizon_Chunified", "SIMPLE", "> Horizon Unified Table", "<  Horizon Table", "NONE", "ONE_TO_MANY", "NONE", "chkey", "chkey", "","")

        if bOverwrite or not arcpy.Exists("zChstructgrp_Chstruct"):
            PrintMsg("    --> zChstructgrp_Chstruct", 1)
            arcpy.CreateRelationshipClass_management("chstructgrp", "chstruct", "zChstructgrp_Chstruct", "SIMPLE", "> Horizon Structure Table", "<  Horizon Structure Group Table", "NONE", "ONE_TO_MANY", "NONE", "chstructgrpkey", "chstructgrpkey", "","")

        if bOverwrite or not arcpy.Exists("zChtexture_Chtexturemod"):
            PrintMsg("    --> zChtexture_Chtexturemod", 1)
            arcpy.CreateRelationshipClass_management("chtexture", "chtexturemod", "zChtexture_Chtexturemod", "SIMPLE", "> Horizon Texture Modifier Table", "<  Horizon Texture Table", "NONE", "ONE_TO_MANY", "NONE", "chtkey", "chtkey", "","")

        if bOverwrite or not arcpy.Exists("zChtexturegrp_Chtexture"):
            PrintMsg("    --> zChtexturegrp_Chtexture", 1)
            arcpy.CreateRelationshipClass_management("chtexturegrp", "chtexture", "zChtexturegrp_Chtexture", "SIMPLE", "> Horizon Texture Table", "<  Horizon Texture Group Table", "NONE", "ONE_TO_MANY", "NONE", "chtgkey", "chtgkey", "","")

        if bOverwrite or not arcpy.Exists("zCoforprod_Coforprodo"):
            PrintMsg("    --> zCoforprod_Coforprodo", 1)
            arcpy.CreateRelationshipClass_management("coforprod", "coforprodo", "zCoforprod_Coforprodo", "SIMPLE", "> Component Forest Productivity - Other Table", "<  Component Forest Productivity Table", "NONE", "ONE_TO_MANY", "NONE", "cofprodkey", "cofprodkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphgc"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphgc", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphgc", "zCogeomordesc_Cosurfmorphgc", "SIMPLE", "> Component Three Dimensional Surface Morphometry Table", "<  Component Geomorphic Description Table", "NONE", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphhpp"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphhpp", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphhpp", "zCogeomordesc_Cosurfmorphhpp", "SIMPLE", "> Component Two Dimensional Surface Morphometry Table", "<  Component Geomorphic Description Table", "NONE", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphmr"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphmr", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphmr", "zCogeomordesc_Cosurfmorphmr", "SIMPLE", "> Component Microrelief Surface Morphometry Table", "<  Component Geomorphic Description Table", "NONE", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zCogeomordesc_Cosurfmorphss"):
            PrintMsg("    --> zCogeomordesc_Cosurfmorphss", 1)
            arcpy.CreateRelationshipClass_management("cogeomordesc", "cosurfmorphss", "zCogeomordesc_Cosurfmorphss", "SIMPLE", "> Component Slope Shape Surface Morphometry Table", "<  Component Geomorphic Description Table", "NONE", "ONE_TO_MANY", "NONE", "cogeomdkey", "cogeomdkey", "","")

        if bOverwrite or not arcpy.Exists("zComonth_Cosoilmoist"):
            PrintMsg("    --> zComonth_Cosoilmoist", 1)
            arcpy.CreateRelationshipClass_management("comonth", "cosoilmoist", "zComonth_Cosoilmoist", "SIMPLE", "> Component Soil Moisture Table", "<  Component Month Table", "NONE", "ONE_TO_MANY", "NONE", "comonthkey", "comonthkey", "","")

        if bOverwrite or not arcpy.Exists("zComonth_Cosoiltemp"):
            PrintMsg("    --> zComonth_Cosoiltemp", 1)
            arcpy.CreateRelationshipClass_management("comonth", "cosoiltemp", "zComonth_Cosoiltemp", "SIMPLE", "> Component Soil Temperature Table", "<  Component Month Table", "NONE", "ONE_TO_MANY", "NONE", "comonthkey", "comonthkey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Chorizon"):
            PrintMsg("    --> zComponent_Chorizon", 1)
            arcpy.CreateRelationshipClass_management("component", "chorizon", "zComponent_Chorizon", "SIMPLE", "> Horizon Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cocanopycover"):
            PrintMsg("    --> zComponent_Cocanopycover", 1)
            arcpy.CreateRelationshipClass_management("component", "cocanopycover", "zComponent_Cocanopycover", "SIMPLE", "> Component Canopy Cover Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cocropyld"):
            PrintMsg("    --> zComponent_Cocropyld", 1)
            arcpy.CreateRelationshipClass_management("component", "cocropyld", "zComponent_Cocropyld", "SIMPLE", "> Component Crop Yield Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Codiagfeatures"):
            PrintMsg("    --> zComponent_Codiagfeatures", 1)
            arcpy.CreateRelationshipClass_management("component", "codiagfeatures", "zComponent_Codiagfeatures", "SIMPLE", "> Component Diagnostic Features Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coecoclass"):
            PrintMsg("    --> zComponent_Coecoclass", 1)
            arcpy.CreateRelationshipClass_management("component", "coecoclass", "zComponent_Coecoclass", "SIMPLE", "> Component Ecological Classification Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coeplants"):
            PrintMsg("    --> zComponent_Coeplants", 1)
            arcpy.CreateRelationshipClass_management("component", "coeplants", "zComponent_Coeplants", "SIMPLE", "> Component Existing Plants Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coerosionacc"):
            PrintMsg("    --> zComponent_Coerosionacc", 1)
            arcpy.CreateRelationshipClass_management("component", "coerosionacc", "zComponent_Coerosionacc", "SIMPLE", "> Component Erosion Accelerated Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Coforprod"):
            PrintMsg("    --> zComponent_Coforprod", 1)
            arcpy.CreateRelationshipClass_management("component", "coforprod", "zComponent_Coforprod", "SIMPLE", "> Component Forest Productivity Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cogeomordesc"):
            PrintMsg("    --> zComponent_Cogeomordesc", 1)
            arcpy.CreateRelationshipClass_management("component", "cogeomordesc", "zComponent_Cogeomordesc", "SIMPLE", "> Component Geomorphic Description Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cohydriccriteria"):
            PrintMsg("    --> zComponent_Cohydriccriteria", 1)
            arcpy.CreateRelationshipClass_management("component", "cohydriccriteria", "zComponent_Cohydriccriteria", "SIMPLE", "> Component Hydric Criteria Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cointerp"):
            PrintMsg("    --> zComponent_Cointerp", 1)
            arcpy.CreateRelationshipClass_management("component", "cointerp", "zComponent_Cointerp", "SIMPLE", "> Component Interpretation Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Comonth"):
            PrintMsg("    --> zComponent_Comonth", 1)
            arcpy.CreateRelationshipClass_management("component", "comonth", "zComponent_Comonth", "SIMPLE", "> Component Month Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Copmgrp"):
            PrintMsg("    --> zComponent_Copmgrp", 1)
            arcpy.CreateRelationshipClass_management("component", "copmgrp", "zComponent_Copmgrp", "SIMPLE", "> Component Parent Material Group Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Copwindbreak"):
            PrintMsg("    --> zComponent_Copwindbreak", 1)
            arcpy.CreateRelationshipClass_management("component", "copwindbreak", "zComponent_Copwindbreak", "SIMPLE", "> Component Potential Windbreak Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Corestrictions"):
            PrintMsg("    --> zComponent_Corestrictions", 1)
            arcpy.CreateRelationshipClass_management("component", "corestrictions", "zComponent_Corestrictions", "SIMPLE", "> Component Restrictions Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cosurffrags"):
            PrintMsg("    --> zComponent_Cosurffrags", 1)
            arcpy.CreateRelationshipClass_management("component", "cosurffrags", "zComponent_Cosurffrags", "SIMPLE", "> Component Surface Fragments Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotaxfmmin"):
            PrintMsg("    --> zComponent_Cotaxfmmin", 1)
            arcpy.CreateRelationshipClass_management("component", "cotaxfmmin", "zComponent_Cotaxfmmin", "SIMPLE", "> Component Taxonomic Family Mineralogy Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotaxmoistcl"):
            PrintMsg("    --> zComponent_Cotaxmoistcl", 1)
            arcpy.CreateRelationshipClass_management("component", "cotaxmoistcl", "zComponent_Cotaxmoistcl", "SIMPLE", "> Component Taxonomic Moisture Class Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotext"):
            PrintMsg("    --> zComponent_Cotext", 1)
            arcpy.CreateRelationshipClass_management("component", "cotext", "zComponent_Cotext", "SIMPLE", "> Component Text Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotreestomng"):
            PrintMsg("    --> zComponent_Cotreestomng", 1)
            arcpy.CreateRelationshipClass_management("component", "cotreestomng", "zComponent_Cotreestomng", "SIMPLE", "> Component Trees To Manage Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zComponent_Cotxfmother"):
            PrintMsg("    --> zComponent_Cotxfmother", 1)
            arcpy.CreateRelationshipClass_management("component", "cotxfmother", "zComponent_Cotxfmother", "SIMPLE", "> Component Taxonomic Family Other Criteria Table", "<  Component Table", "NONE", "ONE_TO_MANY", "NONE", "cokey", "cokey", "","")

        if bOverwrite or not arcpy.Exists("zCopmgrp_Copm"):
            PrintMsg("    --> zCopmgrp_Copm", 1)
            arcpy.CreateRelationshipClass_management("copmgrp", "copm", "zCopmgrp_Copm", "SIMPLE", "> Component Parent Material Table", "<  Component Parent Material Group Table", "NONE", "ONE_TO_MANY", "NONE", "copmgrpkey", "copmgrpkey", "","")

        if bOverwrite or not arcpy.Exists("zDistmd_Distinterpmd"):
            PrintMsg("    --> zDistmd_Distinterpmd", 1)
            arcpy.CreateRelationshipClass_management("distmd", "distinterpmd", "zDistmd_Distinterpmd", "SIMPLE", "> Distribution Interp Metadata Table", "<  Distribution Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "distmdkey", "distmdkey", "","")

        if bOverwrite or not arcpy.Exists("zDistmd_Distlegendmd"):
            PrintMsg("    --> zDistmd_Distlegendmd", 1)
            arcpy.CreateRelationshipClass_management("distmd", "distlegendmd", "zDistmd_Distlegendmd", "SIMPLE", "> Distribution Legend Metadata Table", "<  Distribution Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "distmdkey", "distmdkey", "","")

        if bOverwrite or not arcpy.Exists("zLaoverlap_Muaoverlap"):
            PrintMsg("    --> zLaoverlap_Muaoverlap", 1)
            arcpy.CreateRelationshipClass_management("laoverlap", "muaoverlap", "zLaoverlap_Muaoverlap", "SIMPLE", "> Mapunit Area Overlap Table", "<  Legend Area Overlap Table", "NONE", "ONE_TO_MANY", "NONE", "lareaovkey", "lareaovkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Laoverlap"):
            PrintMsg("    --> zLegend_Laoverlap", 1)
            arcpy.CreateRelationshipClass_management("legend", "laoverlap", "zLegend_Laoverlap", "SIMPLE", "> Legend Area Overlap Table", "<  Legend Table", "NONE", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Legendtext"):
            PrintMsg("    --> zLegend_Legendtext", 1)
            arcpy.CreateRelationshipClass_management("legend", "legendtext", "zLegend_Legendtext", "SIMPLE", "> Legend Text Table", "<  Legend Table", "NONE", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zLegend_Mapunit"):
            PrintMsg("    --> zLegend_Mapunit", 1)
            arcpy.CreateRelationshipClass_management("legend", "mapunit", "zLegend_Mapunit", "SIMPLE", "> Mapunit Table", "<  Legend Table", "NONE", "ONE_TO_MANY", "NONE", "lkey", "lkey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Component"):
            PrintMsg("    --> zMapunit_Component", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "component", "zMapunit_Component", "SIMPLE", "> Component Table", "<  Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Muaggatt"):
            PrintMsg("    --> zMapunit_Muaggatt", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "muaggatt", "zMapunit_Muaggatt", "SIMPLE", "> Mapunit Aggregated Attribute Table", "<  Mapunit Table", "NONE", "ONE_TO_ONE", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Muaoverlap"):
            PrintMsg("    --> zMapunit_Muaoverlap", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "muaoverlap", "zMapunit_Muaoverlap", "SIMPLE", "> Mapunit Area Overlap Table", "<  Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Mucropyld"):
            PrintMsg("    --> zMapunit_Mucropyld", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "mucropyld", "zMapunit_Mucropyld", "SIMPLE", "> Mapunit Crop Yield Table", "<  Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

        if bOverwrite or not arcpy.Exists("zMapunit_Mutext"):
            PrintMsg("    --> zMapunit_Mutext", 1)
            arcpy.CreateRelationshipClass_management("mapunit", "mutext", "zMapunit_Mutext", "SIMPLE", "> Mapunit Text Table", "<  Mapunit Table", "NONE", "ONE_TO_MANY", "NONE", "mukey", "mukey", "","")

            #PrintMsg("    --> zMdstatdommas_Mdstatdomdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatdommas", "mdstatdomdet", "zMdstatdommas_Mdstatdomdet", "SIMPLE", "> Domain Detail Static Metadata Table", "<  Domain Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "domainname", "domainname", "","")
            #PrintMsg("    --> zMdstatdommas_Mdstattabcols", 1)
            #arcpy.CreateRelationshipClass_management("mdstatdommas", "mdstattabcols", "zMdstatdommas_Mdstattabcols", "SIMPLE", "> Table Column Static Metadata Table", "<  Domain Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "domainname", "domainname", "","")
            #PrintMsg("    --> zMdstatidxmas_Mdstatidxdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatidxmas", "mdstatidxdet", "zMdstatidxmas_Mdstatidxdet", "SIMPLE", "> Index Detail Static Metadata Table", "<  Index Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "idxphyname", "idxphyname", "","")
            #PrintMsg("    --> zMdstatrshipmas_Mdstatrshipdet", 1)
            #arcpy.CreateRelationshipClass_management("mdstatrshipmas", "mdstatrshipdet", "zMdstatrshipmas_Mdstatrshipdet", "SIMPLE", "> Relationship Detail Static Metadata Table", "<  Relationship Master Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "ltabphyname", "ltabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstatidxmas", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstatidxmas", "zMdstattabs_Mdstatidxmas", "SIMPLE", "> Index Master Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "tabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstatrshipmas", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstatrshipmas", "zMdstattabs_Mdstatrshipmas", "SIMPLE", "> Relationship Master Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "ltabphyname", "","")
            #PrintMsg("    --> zMdstattabs_Mdstattabcols", 1)
            #arcpy.CreateRelationshipClass_management("mdstattabs", "mdstattabcols", "zMdstattabs_Mdstattabcols", "SIMPLE", "> Table Column Static Metadata Table", "<  Table Static Metadata Table", "NONE", "ONE_TO_MANY", "NONE", "tabphyname", "tabphyname", "","")

        if bOverwrite or not arcpy.Exists("zSacatalog_Sainterp"):
            PrintMsg("    --> zSacatalog_Sainterp", 1)
            arcpy.CreateRelationshipClass_management("sacatalog", "sainterp", "zSacatalog_Sainterp", "SIMPLE", "> Survey Area Interpretation Table", "<  Survey Area Catalog Table", "NONE", "ONE_TO_MANY", "NONE", "sacatalogkey", "sacatalogkey", "","")

            #PrintMsg("    --> zSdvattribute_Sdvfolderattribute", 1)
            #arcpy.CreateRelationshipClass_management("sdvattribute", "sdvfolderattribute", "zSdvattribute_Sdvfolderattribute", "SIMPLE", "> SDV Folder Attribute Table", "<  SDV Attribute Table", "NONE", "ONE_TO_MANY", "NONE", "attributekey", "attributekey", "","")
            #PrintMsg("    --> zSdvfolder_Sdvfolderattribute", 1)
            #arcpy.CreateRelationshipClass_management("sdvfolder", "sdvfolderattribute", "zSdvfolder_Sdvfolderattribute", "SIMPLE", "> SDV Folder Attribute Table", "<  SDV Folder Table", "NONE", "ONE_TO_MANY", "NONE", "folderkey", "folderkey", "","")

        return True



    except:
        errorMsg()
        return False


## ===============================================================================================================
def CreateTableRelationships(wksp):
    # Create relationship classes between standalone attribute tables.
    # Relate parameters are pulled from the mdstatrhipdet and mdstatrshipmas tables,
    # thus it is required that the tables must have been copied from the template database.

    try:

        PrintMsg(" \nCreating Relationships between tables:",1)
        env.workspace = wksp
        
        if arcpy.Exists(os.path.join(wksp, "mdstatrshipdet")) and arcpy.Exists(os.path.join(wksp, "mdstatrshipmas")):

            # Create new Table View to contain results of join between relationship metadata tables

            tbl1 = os.path.join(wksp, "mdstatrshipmas")
            tbl2 = os.path.join("mdstatrshipdet")
            tblList = [tbl1, tbl2]
            queryTableName = "TblRelationships"

            sql = "mdstatrshipdet.ltabphyname = mdstatrshipmas.ltabphyname AND mdstatrshipdet.rtabphyname = mdstatrshipmas.rtabphyname AND mdstatrshipdet.relationshipname = mdstatrshipmas.relationshipname"

            fldList = [["mdstatrshipmas.ltabphyname","LTABPHYNAME"],["mdstatrshipmas.rtabphyname", "RTABPHYNAME"],["mdstatrshipdet.relationshipname", "RELATIONSHIPNAME"], ["mdstatrshipdet.ltabcolphyname", "LTABCOLPHYNAME"],["mdstatrshipdet.rtabcolphyname",  "RTABCOLPHYNAME"]]

            arcpy.MakeQueryTable_management (tblList, queryTableName, "ADD_VIRTUAL_KEY_FIELD", "", fldList, sql)

            if not arcpy.Exists(queryTableName):
                raise MyError, "Failed to create metadata table required for creation of relationshipclasses"

            tblCnt = int(arcpy.GetCount_management(queryTableName).getOutput(0))
            PrintMsg(" \nQuery table has " + str(tblCnt) + " records", 1)
            #arcpy.CopyRows_management(queryTableName, os.path.join(env.scratchGDB, "MdTable"))

            #fields = arcpy.Describe(queryTableName).fields
            #for fld in fields:
            #    PrintMsg("\tQuery Table: " + fld.name, 1)


            # Fields in RelshpInfo table view
            # OBJECTID, LTABPHYNAME, RTABPHYNAME, RELATIONSHIPNAME, LTABCOLPHYNAME, RTABCOLPHYNAME
            # Open table view and step through each record to retrieve relationshipclass parameters             
            with arcpy.da.SearchCursor(queryTableName, ["mdstatrshipmas_ltabphyname", "mdstatrshipmas_rtabphyname", "mdstatrshipdet_ltabcolphyname", "mdstatrshipdet_rtabcolphyname"]) as theCursor:

                for rec in theCursor:
                    # Get relationshipclass parameters from current table row
                    # Syntax for CreateRelationshipClass_management (origin_table, destination_table, 
                    # out_relationship_class, relationship_type, forward_label, backward_label, 
                    # message_direction, cardinality, attributed, origin_primary_key, 
                    # origin_foreign_key, destination_primary_key, destination_foreign_key)
                    #
                    #PrintMsg("\t" + str(rec), 1)
                    #originTable, destinationTable, originPKey, originFKey = rec
                    destinationTable, originTable, originFKey, originPKey = rec
                    
                    originTablePath = os.path.join(wksp, originTable)
                    destinationTablePath = os.path.join(wksp, destinationTable)

                    # Use table aliases for relationship labels
                    relName = "z" + originTable.title() + "_" + destinationTable.title()

                    if bOverwrite and arcpy.Exists(relName):
                        arcpy.Delete_management(relName)

                    # create Forward Label i.e. "> Horizon AASHTO Table"
                    fwdLabel = "< " + destinationTable.title() + " Table"

                    # create Backward Label i.e. "< Horizon Table"
                    backLabel = ">  " + originTable.title() + " Table"

                    if arcpy.Exists(originTablePath) and arcpy.Exists(destinationTablePath):
                        PrintMsg("\tCreating relationship for " + originTable + " to " + destinationTable, 1)
                        
                        #if FindField(originTablePath, originPKey) and FindField(wksp + os.sep + destinationTablePath, originFKey):
                        arcpy.CreateRelationshipClass_management(originTablePath, destinationTablePath, relName, "SIMPLE", fwdLabel, backLabel, "NONE", "ONE_TO_MANY", "NONE", originPKey, originFKey, "","")


        else:
            raise MyError, "Missing one or more of the metadata tables"


        # Establish Relationship between tables and Spatial layers

        # The following lines are for formatting only
        #formatTab1 = 15 - len(soilsFC)
        #formatTabLength1 = " " * formatTab1 + "--> "

        PrintMsg(" \nCreating Relationships between Featureclasses and Tables:", 1)

        # Relationship between MUPOLYGON --> Mapunit Table            
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MUPOLYGON"), os.path.join(wksp, "zSpatial_MUPOLYGON_Mapunit"), "SIMPLE", "< MUPOLYGON", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Mapunit", 1)

        # Relationship between MUPOLYGON --> Mapunit Aggregate Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "muaggatt"), os.path.join(wksp, "MUPOLYGON"), os.path.join(wksp, "zSpatial_MUPOLYGON_Muaggatt"), "SIMPLE", "< MUPOLYGON", "> Mapunit Aggregate Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "muaggatt" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Muaggatt", 1)

        # Relationship between SAPOLYGON --> Legend Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "legend"), os.path.join(wksp, "SAPOLYGON"), os.path.join(wksp, "zSpatial_SAPOLYGON_Legend"), "SIMPLE", "< SAPOLYGON", "> Legend Table", "NONE","ONE_TO_MANY", "NONE","LKEY","lkey", "","")
        #AddMsgAndPrint("\t" + ssaFC + formatTabLength1 + "legend" + "             --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SAPOLYGON_Legend", 1)

        # Relationship between MULINE --> Mapunit Table
        if arcpy.Exists("MULINE"):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MULINE"), os.path.join(wksp, "zSpatial_MULINE_Mapunit"), "SIMPLE", "< MULINE", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
            #AddMsgAndPrint("\t" + soilsmuLineFC + "         --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_MULINE_Mapunit", 1)

        # Relationship between MUPOINT --> Mapunit Table
        if arcpy.Exists("MUPOINT"):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MUPOINT"), os.path.join(wksp, "zSpatial_MUPOINT_Mapunit"), "SIMPLE", "< MUPOINT", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
            #AddMsgAndPrint("\t" + soilsmuPointFC + "        --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_MUPOINT_Mapunit", 1)

        # Relationship between FEATLINE --> Featdesc Table
        if arcpy.Exists("FEATLINE"):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "featdesc"), os.path.join(wksp, "FEATLINE"), os.path.join(wksp, "zSpatial_FEATLINE_Featdesc"), "SIMPLE", "< FEATLINE", "> Featdesc Table", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
            #AddMsgAndPrint("\t" + specLineFC + "       --> featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_SPECLINE_Featdesc", 1)

        # Relationship between FEATPOINT --> Featdesc Table
        if arcpy.Exists("FEATPOINT"):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "featdesc"), os.path.join(wksp, "FEATPOINT"), os.path.join(wksp, "zSpatial_FEATPOINT_Featdesc"), "SIMPLE", "< FEATPOINT", "> Featdesc Table", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
            #AddMsgAndPrint("\t" + specPointFC + formatTabLength1 + "featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SPECPOINT_Featdesc", 1)

        PrintMsg("\nSuccessfully Created featureclass and table relationships", 1)
        return True


    except:
        errorMsg()
        return False


## ===============================================================================================================
def CreateTableRelationships2(wksp):
    # Create relationship classes between standalone attribute tables.
    # Relate parameters are pulled from the mdstatrhipdet and mdstatrshipmas tables,
    # thus it is required that the tables must have been copied from the template database.
    #
    # Seem to be having problems with component to chorizon relationships. Try reversing tables.

    try:

        PrintMsg(" \nCreating Relationships between tables:",1)
        env.workspace = wksp
        
        if arcpy.Exists(os.path.join(wksp, "mdstatrshipdet")) and arcpy.Exists(os.path.join(wksp, "mdstatrshipmas")):

            # Create new Table View to contain results of join between relationship metadata tables

            tbl1 = os.path.join(wksp, "mdstatrshipmas")
            tbl2 = os.path.join("mdstatrshipdet")
            tblList = [tbl1, tbl2]
            queryTableName = "TblRelationships"

            sql = "mdstatrshipdet.ltabphyname = mdstatrshipmas.ltabphyname AND mdstatrshipdet.rtabphyname = mdstatrshipmas.rtabphyname AND mdstatrshipdet.relationshipname = mdstatrshipmas.relationshipname"

            fldList = [["mdstatrshipmas.ltabphyname","LTABPHYNAME"],["mdstatrshipmas.rtabphyname", "RTABPHYNAME"],["mdstatrshipdet.relationshipname", "RELATIONSHIPNAME"], ["mdstatrshipdet.ltabcolphyname", "LTABCOLPHYNAME"],["mdstatrshipdet.rtabcolphyname",  "RTABCOLPHYNAME"]]

            arcpy.MakeQueryTable_management (tblList, queryTableName, "ADD_VIRTUAL_KEY_FIELD", "", fldList, sql)

            if not arcpy.Exists(queryTableName):
                raise MyError, "Failed to create metadata table required for creation of relationshipclasses"

            tblCnt = int(arcpy.GetCount_management(queryTableName).getOutput(0))
            PrintMsg(" \nQuery table has " + str(tblCnt) + " records", 1)
            #arcpy.CopyRows_management(queryTableName, os.path.join(env.scratchGDB, "MdTable"))

            #fields = arcpy.Describe(queryTableName).fields
            #for fld in fields:
            #    PrintMsg("\tQuery Table: " + fld.name, 1)


            # Fields in RelshpInfo table view
            # OBJECTID, LTABPHYNAME, RTABPHYNAME, RELATIONSHIPNAME, LTABCOLPHYNAME, RTABCOLPHYNAME
            # Open table view and step through each record to retrieve relationshipclass parameters             
            with arcpy.da.SearchCursor(queryTableName, ["mdstatrshipmas_ltabphyname", "mdstatrshipmas_rtabphyname", "mdstatrshipdet_ltabcolphyname", "mdstatrshipdet_rtabcolphyname"]) as theCursor:

                for rec in theCursor:
                    # Get relationshipclass parameters from current table row
                    # Syntax for CreateRelationshipClass_management (origin_table, destination_table, 
                    # out_relationship_class, relationship_type, forward_label, backward_label, 
                    # message_direction, cardinality, attributed, origin_primary_key, 
                    # origin_foreign_key, destination_primary_key, destination_foreign_key)
                    #
                    #PrintMsg("\t" + str(rec), 1)
                    originTable, destinationTable, originPKey, originFKey = rec
                    #destinationTable, originTable, originFKey, originPKey = rec
                    
                    originTablePath = os.path.join(wksp, originTable)
                    destinationTablePath = os.path.join(wksp, destinationTable)

                    # Use table aliases for relationship labels
                    relName = "z" + originTable.title() + "_" + destinationTable.title()

                    if bOverwrite and arcpy.Exists(relName):
                        arcpy.Delete_management(relName)

                    # create Forward Label i.e. "> Horizon AASHTO Table"
                    fwdLabel = "< " + destinationTable.title() + " Table"

                    # create Backward Label i.e. "< Horizon Table"
                    backLabel = ">  " + originTable.title() + " Table"

                    if arcpy.Exists(originTablePath) and arcpy.Exists(destinationTablePath):
                        PrintMsg("\tCreating relationship for " + originTable + " to " + destinationTable, 1)
                        
                        #if FindField(originTablePath, originPKey) and FindField(wksp + os.sep + destinationTablePath, originFKey):
                        arcpy.CreateRelationshipClass_management(originTablePath, destinationTablePath, relName, "SIMPLE", fwdLabel, backLabel, "NONE", "ONE_TO_MANY", "NONE", originPKey, originFKey, "","")


        else:
            raise MyError, "Missing one or more of the metadata tables"


        # Establish Relationship between tables and Spatial layers

        # The following lines are for formatting only
        #formatTab1 = 15 - len(soilsFC)
        #formatTabLength1 = " " * formatTab1 + "--> "

        PrintMsg(" \nCreating Relationships between Featureclasses and Tables:", 1)

        # Relationship between MUPOLYGON --> Mapunit Table            
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MUPOLYGON"), os.path.join(wksp, "zSpatial_MUPOLYGON_Mapunit"), "SIMPLE", "< MUPOLYGON", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Mapunit", 1)

        # Relationship between MUPOLYGON --> Mapunit Aggregate Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "muaggatt"), os.path.join(wksp, "MUPOLYGON"), os.path.join(wksp, "zSpatial_MUPOLYGON_Muaggatt"), "SIMPLE", "< MUPOLYGON", "> Mapunit Aggregate Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
        #AddMsgAndPrint("\t" + soilsFC + formatTabLength1 + "muaggatt" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_MUPOLYGON_Muaggatt", 1)

        # Relationship between SAPOLYGON --> Legend Table
        arcpy.CreateRelationshipClass_management(os.path.join(wksp, "legend"), os.path.join(wksp, "SAPOLYGON"), os.path.join(wksp, "zSpatial_SAPOLYGON_Legend"), "SIMPLE", "< SAPOLYGON", "> Legend Table", "NONE","ONE_TO_MANY", "NONE","LKEY","lkey", "","")
        #AddMsgAndPrint("\t" + ssaFC + formatTabLength1 + "legend" + "             --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SAPOLYGON_Legend", 1)

        # Relationship between MULINE --> Mapunit Table
        if arcpy.Exists(os.path.join(wksp, "MULINE")):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MULINE"), os.path.join(wksp, "zSpatial_MULINE_Mapunit"), "SIMPLE", "< MULINE", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
            #AddMsgAndPrint("\t" + soilsmuLineFC + "         --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_MULINE_Mapunit", 1)

        # Relationship between MUPOINT --> Mapunit Table
        if arcpy.Exists(os.path.join(wksp, "MUPOINT")):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "mapunit"), os.path.join(wksp, "MUPOINT"), os.path.join(wksp, "zSpatial_MUPOINT_Mapunit"), "SIMPLE", "< MUPOINT", "> Mapunit Table", "NONE","ONE_TO_MANY", "NONE","MUKEY","mukey", "","")
            #AddMsgAndPrint("\t" + soilsmuPointFC + "        --> mapunit" + "            --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_MUPOINT_Mapunit", 1)

        # Relationship between FEATLINE --> Featdesc Table
        if arcpy.Exists(os.path.join(wksp, "FEATLINE")):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "featdesc"), os.path.join(wksp, "FEATLINE"), os.path.join(wksp, "zSpatial_FEATLINE_Featdesc"), "SIMPLE", "< FEATLINE", "> Featdesc Table", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
            #AddMsgAndPrint("\t" + specLineFC + "       --> featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "zSpatial_SPECLINE_Featdesc", 1)

        # Relationship between FEATPOINT --> Featdesc Table
        if arcpy.Exists(os.path.join(wksp, "FEATPOINT")):
            arcpy.CreateRelationshipClass_management(os.path.join(wksp, "featdesc"), os.path.join(wksp, "FEATPOINT"), os.path.join(wksp, "zSpatial_FEATPOINT_Featdesc"), "SIMPLE", "< FEATPOINT", "> Featdesc Table", "NONE","ONE_TO_MANY", "NONE","FEATKEY","featkey", "","")
            #AddMsgAndPrint("\t" + specPointFC + formatTabLength1 + "featdesc" + "           --> " + "ONE_TO_ONE" + "  --> " + "xSpatial_SPECPOINT_Featdesc", 1)

        PrintMsg("\nSuccessfully Created featureclass and table relationships", 1)
        return True


    except:
        errorMsg()
        return False

## ===============================================================================================================
    
## ===================================================================================
def GetFCType(fc):
    # Determine featureclass type  featuretype and table fields
    # Rename featureclasses from old shapefile-based name to new, shorter name
    # Returns new featureclass name using DSS convention for geodatabase
    #
    # The check for table fields is the absolute minimum

    featureType = ""

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
                featureType = ""

        # Survey Area Boundary
        if hasLkey:
            if featType == "Polygon":
                dataType = "Survey Boundary"

            else:
                PrintMsg(fcName + " is an unidentified " + featType + " featureclass with an LKEY field (GetFCName)", 2)
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
import sys, string, os, locale, arcpy, traceback, math, time
from arcpy import env

try:
    if __name__ == "__main__":
        # Create geoprocessor object
        #gp = arcgisscripting.create(9.3)
        #arcpy.OverwriteOutput = 1

        scriptname = sys.argv[0]
        wksp = arcpy.GetParameterAsText(0)   # input geodatabase containing SSURGO tables and featureclasses
        bOverwrite = arcpy.GetParameter(1)   # overwrite option independant of gp environment setting

        env.workspace = wksp

        bTableAliases = False # used to be a menu item for the 9.3 databases
        bFldAliases = False

        begin = time.time()
        # Create relationshipclasses

        if bOverwrite:
            env.overwriteOutput = True

        #bRL = CreateRL(wksp, bOverwrite)
        bRL = CreateTableRelationships2(wksp)

        theMsg = " \n" + os.path.basename(scriptname) + " finished in " + elapsedTime(begin)
        PrintMsg(theMsg, 1)

except:
    errorMsg()
