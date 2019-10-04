# SSURGO_SimplyByMap.py
#
# Batchmode process for automatically removing excess vertices by survey area.
#
# 2018-08-24 Do I need to add indexes for areasymbol and mukey?
#
## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        sysExc = sys.exc_info()
        tb = sysExc[2]
        tbInfo = traceback.format_tb(tb)

        if len(tbInfo) == 0:
            # No error found
            return

        tbMsg = tbInfo[0]
        theMsg = tbMsg + " \n" + str(sys.exc_type)+ ": " + str(sys.exc_value) + " \n"
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error", 2)
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
        return ""


## ===================================================================================
def FindNewPolygons1(outputFC, soilLabels):
    # Also need to look for polygons that were eliminated. Use label points layer for this.

    try:
        
        polyFreq = dict()
        dupList = list()
        wc = "mukey != ''"
        joinedPoints = os.path.join(env.scratchGDB, "JoinedPoints")
        PrintMsg(" \nLooking for eliminated polygons using original label points", 1)
        
        if arcpy.Exists(outputFC):
            arcpy.SpatialJoin_analysis(soilLabels, outputFC, joinedPoints, "JOIN_ONE_TO_MANY", "KEEP_ALL")
                
            return True
        
        else:
            # PrintMsg("\tUsing existing report table", 0)
            raise MyError, "Missing output featureclass: " + outputFC

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False
   
## ===================================================================================
def FindNewPolygons2(outputFC, idField):
    # Find extra polygons with a duplicate ORIG_FID but is not missing MUKEY value
    #
    # Also need to look for extra polygons with missing MUKEY value
    #
    # Also need to look for polygons that were eliminated. Use another function?

    try:
        
        polyFreq = dict()
        dupList = list()
        extraList = list()

        PrintMsg(" \nLooking for eliminated polygons 2", 1)
        
        if arcpy.Exists(outputFC):
            with arcpy.da.SearchCursor(outputFC, [idField, "mukey"]) as cur:
                for rec in cur:
                    polyID, mukey = rec
                    
                    
                    # new polygon created by snapping.
                    # No corresponding label point, thus no mukey value.
                    if mukey is None:
                        try:
                            polyFreq[polyID] += 1
                            
                            if not polyID in dupList:
                                dupList.append(polyID)

                        except:
                            polyFreq[polyID] = 1
                    
            if len(dupList) > 0:
                PrintMsg(" \nDuplicate polygon id's: " + str(dupList), 1)
                
            return True
        
        else:
            # PrintMsg("\tUsing existing report table", 0)
            raise MyError, "Missing output featureclass: " + outputFC

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False
   
## ===================================================================================
def MakeReportTable(outputGDB, processReport):
    # Create new table to store simplification process statistics
    #

    try:
        reportTbl = os.path.join(outputGDB, processReport)
        
        if not arcpy.Exists(reportTbl):
            PrintMsg(" \nCreating new report table", 0)
            arcpy.CreateTable_management(os.path.dirname(reportTbl), os.path.basename(reportTbl))

            # AREASYMBOL, DATE, POLY_CNT1, POLY_CNT2, VERT_CNT1, VERT_CNT2, SETTINGS, COMPLETED
            arcpy.AddField_management(reportTbl, "AREASYMBOL", "TEXT", "", "", 20)
            arcpy.AddField_management(reportTbl, "LAYER_NAME", "TEXT", "", "", 30)
            arcpy.AddField_management(reportTbl, "RUN_DATE", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "POLY_CNT1", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "POLY_CNT2", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "POLY_DIFF", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "POLY_ELIM", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "NO_ATTS", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "VERT_CNT1", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "VERT_CNT2", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "VERT_DIFF", "LONG", "", "", "")
            arcpy.AddField_management(reportTbl, "VERT_PCT", "FLOAT", "", "", "")
            arcpy.AddField_management(reportTbl, "SETTINGS", "TEXT", "", "", 50)
            arcpy.AddField_management(reportTbl, "CS_NAME", "TEXT", "", "", 75)
            #arcpy.AddField_management(reportTbl, "POLY_LIST", "TEXT", "", "", 1024)
            
            return True
        
        else:
            # PrintMsg("\tUsing existing report table", 0)
            return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

   
## ===================================================================================
def AppendSurveyAreas(outputFDS, fcName, method, sortedList):
    # Optional. When an output featureclass name is specified by the user, append all
    # simplified survey area featureclasses to a single featureclass.

    try:
        if len(sortedList) == 0:
            raise MyError, "outputList is empty"

        outputList = [("Soils" + dMethods[method] + "_" + areasym) for areasym in sortedList]
        templateFC = os.path.join(outputFDS, outputList[0])

        
        PrintMsg(" \nAppending all simplified featureclasses to: " + fcName, 0)
        env.workspace = outputFDS
        #templateFC = os.path.join(outputFDS, fcName)

        if not arcpy.Exists(os.path.join(outputFDS, templateFC)):
            raise MyError, "Failed to find template featureclass for Append (" + templateFC + ")"

        #else:
        #    PrintMsg(" \n" + ", ".join(outputList), 1)

        #PrintMsg("Beginning Append to " + fcName + " with " + firstFC + " out of " + str(outputList), 1)
        arcpy.CreateFeatureclass_management(outputFDS, fcName, "POLYGON", templateFC, "DISABLED", "DISABLED", templateFC)
        
        arcpy.Append_management(outputList, fcName)
        arcpy.MakeFeatureLayer_management(templateFC, fcName)
        arcpy.SetParameter(6, os.path.join(outputFDS, fcName))
        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False
   
## ===================================================================================
def GetMapunitAcres(inputLayer, wc):
    # inputLayer should be selected set for a single survey area or the temporary featureclass

    try:
        dMapunitAcres = dict()

        sr = CreateSpatialReference_management("Mercator_Auxiliary_Sphere")
        with arcpy.da.SearchCursor(inputLayer, ["mukey", "SHAPE@"], sr) as cur:
            for rec in cur:
                mukey, shape = rec
                area = shape.getArea("POLYGON", "ACRES")
                acres = round(area, 1)
                PrintMsg("\t" + mukey + ": " + str(acres), 1)                
                try:
                    dMapunitAcres[mukey] += acres

                except:
                    dMapunitAcres[mukey] = acres

            #PrintMsg(" \n" + str(dMapunitAcres), 1)

        
        

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def ProcessSurvey(outputGDB, outputFDS, surveyBoundaryLayer, soilLayer, areasym, method, simpleTol, sToday, csName, outputFCName):
    # Select soil polygons for the specified survey area and remove extra vertices from the soil lines
    
    """
    Process:

    1. Select geographic mupolygons by areasymbol

    2. Convert soil polygons to Coverage (POLYGON)

    3. Convert geographic mupolygons to point (labels inside)

    4. Select $LEFTPOLYGON = 1 or $RIGHTPOLYGON = 1 to pull out Survey BND

    5. Switch selection to pull out interior soil lines.

    6. Use Simplify_LINE on soil lines. Options POINT_REMOVE 1.0 meters. Would it help to use the BND as a barrier option?

    7. Merge the BND and simplified soil lines into a new line featureclass

    8. Use FeatureToPolygon to combine sTodaythe new lines and the label points to a polygon featureclass. 0.5 meter tolerance.

    9. Test the new polygon featureclass to make sure:
            a. Has the same number of polygons before and after
            b. Has no un-attributed polygons
            # AREASYMBOL, POLYCNT1, POLYCNT2, DATE, VERTEXCNT1, VERTEXCNT2, SETTINGS
    """
    
    try:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = mxd.activeDataFrame
        
        # Select soil polygons for the specified areasymbol
        #
        polyCnt1 = 0
        polyCnt2 = 0
        polyDiff = 0
        noAtt = 0
        vertexCnt1 = 0
        vertexCnt2 = 0
        vertDiff = 0

        settings = method + ", " + str(simpleTol)
        tmpFC = os.path.join(env.scratchGDB, "tmpSoils")
        wc = "areasymbol = '" + areasym + "'"
        arcpy.SelectLayerByAttribute_management(soilLayer, "NEW_SELECTION", wc)
        polyCnt1 = int(arcpy.GetCount_management(soilLayer).getOutput(0))  # original source polygon count

        if polyCnt1 == 0:
            raise MyError, "Failed to select soil polygons for areasymbol = '" + areasym + "'"
                 
        PrintMsg("\tBeginning with " + Number_Format(polyCnt1, 0, True) + " soil polygons", 0)

        # Add adjacent polygons from other survey areas
        #
        # Question, would it be easier to use a buffered clip rather than this existing two step method?
        tmpSA = "Single Survey"
        arcpy.MakeFeatureLayer_management(surveyBoundaryLayer, tmpSA, wc)

        # Try using the coverage polygon featureclass to get original statistics by polygon
        vertexCnt1 = 0  # vertex count original
        polyCnt1 = 0     # polygon count original
        dMapunitAcres = dict()

        #PrintMsg(" \n\tSaving area statistics from " + polyCov, 1)
        
        with arcpy.da.SearchCursor(soilLayer, ["OID@", "SHAPE@", "mukey"], where_clause=wc ) as cur:
            
            for rec in cur:
                oid, shape, mukey = rec

                #if areasymbol == areasym:
                mukey = mukey.encode('ascii')
                acres = shape.getArea("PRESERVE_SHAPE", "ACRES")
                
                try:
                    dMapunitAcres[mukey] += acres

                except:
                    dMapunitAcres[mukey] = acres
                    
                vertexCnt1 += shape.pointCount
                polyCnt1 += 1

        arcpy.SelectLayerByLocation_management(soilLayer, "WITHIN_A_DISTANCE", tmpSA, "5 Meters", "ADD_TO_SELECTION")
        #PrintMsg(" \n" + Number_Format(int(arcpy.GetCount_management(soilLayer).getOutput(0)), 0, True) + " polygons in big selection", 1)

   
        # Convert the selected soil polygons to an ArcINFO coverage (requires Desktop Advanced)
        #
        # Includes adjacent survey area polygons along boundary.
        # Trying to create a coincident boundary with this step

        # COV
        # outputCov = os.path.join(env.scratchFolder, "xx_soilcov")

        # NOTCOV
        outputCov = os.path.join(env.scratchGDB, "xx_soilcov")

        # COV
        # inFeatures = [[soilLayer, "POLYGON"]]


        # Output layers and featureclasses
        polyLayer = "AllPolygons"
        lineLayer = "AllLines_" + areasym
        
        lineCov = os.path.join(outputCov, "ARC")
        polyCov = os.path.join(outputCov, "POLYGON")
        allLinesFC = os.path.join(env.scratchGDB, lineLayer)

        
        #
        # Just in case, set the output coordinate system and datum transformation.
        # Begin with keeping the same input and output coordinate system so that the coverage matches the soils layer.
        env.outputCoordinateSystem = soilSR
        #PrintMsg(" \nStarting env spatialreference: " + str(env.outputCoordinateSystem.name), 1)

        
        covTol = "0.5  Meters"
        covTol = "0.1  Meters"
        # PrintMsg("\tCoverage created using " + covTol + " tolerance", 1)

        # COV
        # arcpy.FeatureclassToCoverage_conversion(inFeatures, outputCov, covTol, "DOUBLE") # coverage
        env.XYResolution = covTol
        # NOT COV
        arcpy.PolygonToLine_management(soilLayer, allLinesFC, "IDENTIFY_NEIGHBORS")  # With this new command, output will be 

        # See if setting the output coordinate system
        env.outputCoordinateSystem = fdsSR  # all geoprocessing layers should have the same coordinate system
        env.XYResolution = str(xyRes) + " " + fdsSRUnits
        env.XYTolerance = str(xyTol) + " " + fdsSRUnits             # This environment setting should match the FDS.
        
        
        # COV
        #if not arcpy.Exists(outputCov):
        #    raise MyError, "Failed to create output coverage"
        

        # COV
        # arcpy.MakeFeatureLayer_management(polyCov, polyLayer, wc)  # WARNING! Could I be losing snapped, unattributed polygons here?

        # NO COV
        arcpy.MakeFeatureLayer_management(soilLayer, polyLayer, wc)  # WARNING! Could I be losing snapped, unattributed polygons here?

        
        chkCnt = int(arcpy.GetCount_management(polyLayer).getOutput(0))

        if polyCnt1 != chkCnt:
            if polyCnt1 > chkCnt:
                PrintMsg("\tLost " + Number_Format((polyCnt1 - chkCnt), 0, True) + " polygons in first conversion step", 1)

            #else:
            #    PrintMsg("\tGained " + Number_Format((chkCnt - polyCnt1), 0, True) + " polygons in first conversion step", 1)
        
        # Can I select the arcs belonging to the target coverage instead of running the FeatureclassToCoverage twice?

        # 1. Begin by selecting all coverage polygons whose areasymbol is the current value.
        # 2. open a cursor and put all selected XX_SOILCOV-ID values in a list. Convert to a query string 
        # 3. Create a featurelayer for lineCov, no whereclause used
        # 4. Select featurelayer arcs where $LEFTPOLYGON IN wc AND $RIGHTPOLYGON IN wc (NEW_SELECTION returns all interior soil lines)
        # 5. Switch selection (returns all other arcs including survey boundary
        # 6. Select featurelayer arcs where $LEFTPOLYGON IN wc OR $RIGHTPOLYGON IN wc (SUBSET_SELECTION returns survey boundary)

        # Create list of coverage-ids belonging to the current survey area
        idList = list()
        dPolygonMukey = dict()  

        # COV
        # with arcpy.da.SearchCursor(polyLayer, ["XX_SOILCOV-ID", "MUKEY"], wc) as cur:
        # NO COV
        with arcpy.da.SearchCursor(polyLayer, ["OBJECTID", "MUKEY"], wc) as cur:
            for rec in cur:
                userid = rec[0]
                mukey = rec[1]
                idList.append(userid)
                dPolygonMukey[userid] = mukey 

        # Covert all coverage Arcs to scratchGDB featureclass.
        # 09-01-2018 This is failing when going from projected csr to geographic.
        #
        #
        #PrintMsg("\tSeparating soil line layer and survey boundary layer and simplifying", 1)
        #PrintMsg("\tEnvironment XY Tolerance set at " + covTol + " for new featureclasses", 1)

        # COV
        # arcpy.CopyFeatures_management(lineCov, allLinesFC)
        lineCnt = int(arcpy.GetCount_management(allLinesFC).getOutput(0))

        if lineCnt == 0:
            raise MyError, "Failed to convert coverage Arcs to featureclass"

        # Identify soil lines and soil survey boundary in line featureclass. Use F_ID as
        # a flag. Queries will also need F_LEFTPOLYGON and F_RIGHTPOLYGON fields
        # bnd line = -1
        # soil line = -2
        
        #PrintMsg("\tProcessing lines...", 1)
        arcpy.AddField_management(allLinesFC, "F_ID", "LONG", "", "", "")
        arcpy.AddField_management(allLinesFC, "MUKEY_L", "LONG", "", "", "")
        arcpy.AddField_management(allLinesFC, "MUKEY_R", "LONG", "", "", "")

        #PrintMsg(" \nList of coverage ids: " + str(dPolygonMukey.keys()), 1)

        # COV
        # with arcpy.da.UpdateCursor(allLinesFC, ["F_ID", "F_LEFTPOLYGON", "F_RIGHTPOLYGON", "MUKEY_L", "MUKEY_R"]) as cur:
        # NO COV
        with arcpy.da.UpdateCursor(allLinesFC, ["F_ID", "LEFT_FID", "RIGHT_FID", "MUKEY_L", "MUKEY_R"]) as cur:
            
            for rec in cur:
                fid, leftPoly, rightPoly, mukeyL, mukeyR = rec

                # Get left and right mukey values for this line
                try:
                    mukeyL = dPolygonMukey[leftPoly]

                except:
                    mukeyL = None

                try:
                    mukeyR = dPolygonMukey[rightPoly]

                except:
                    mukeyR = None

                bLeft = leftPoly in idList
                bRight = rightPoly in idList

                if not mukeyL is None and mukeyL == mukeyR:
                    # common-soil line
                    #PrintMsg("\tAllLines feature #" + str(fid) + " is a common-soil line", 1)
                    rec = [-3, leftPoly, rightPoly, mukeyL, mukeyR]

                elif (bLeft and not bRight) or (bRight and not bLeft):
                    # survey boundary
                    #PrintMsg("\t\tFound survey boundary for " + areasym, 1)
                    rec = [-2, leftPoly, rightPoly, mukeyL, mukeyR]
                    
                elif bLeft and bRight:
                    # could be soil line for target survey area
                    #PrintMsg("\t\tFound soil line for " + areasym, 1)
                    rec = [-1, leftPoly, rightPoly, mukeyL, mukeyR]

                else:
                    rec = [0, leftPoly, rightPoly, mukeyL, mukeyR]

                cur.updateRow(rec)
        
        # Select survey boundary in coverage and create a new featureclass.
        # Run Integrate on the survey boundary featureclass to try and cleanup gaps or overlaps.
        #
        # Originally I used FeatureToLine
        #PrintMsg("\tCreate map layer for survey boundary", 0)
        sqlBnd = "F_ID = -2"  # not sure that this where_clause is necessary
        bndLayer = "SurveyBnd_" + areasym.upper()
        arcpy.MakeFeatureLayer_management(allLinesFC, bndLayer, sqlBnd)

        bndCnt = int(arcpy.GetCount_management(bndLayer).getOutput(0))

        if bndCnt == 0:
            raise MyError, "Failed to identify boundary features in " + allLinesFC + " (F_ID = -2)"

        #PrintMsg("\tEnvironment XY Tolerance set at " + covTol + " for new survey boundary", 1)
        soilBnd = os.path.join(env.scratchGDB, bndLayer)
        arcpy.CopyFeatures_management(bndLayer, soilBnd)
        integrateTol = "1.0 Meters"
        # PrintMsg("\tRunning Integrate on survey boundary at a " + integrateTol + " tolerance", 1)
        arcpy.Integrate_management(soilBnd, integrateTol)   # HERE IS WHERE I AM COLLAPSING THE NW CORNER OF MN019!!!!!
        #PrintMsg("\tFinished processing lines...", 1)

        # Simplify just the soil lines
        PrintMsg("\tApplying " + method + " method with a tolerance of " + simpleTol.lower(), 0)
        simpleSoils = os.path.join(env.scratchGDB, "SimpleSoils_" + areasym)
        sqlSoilLines = "F_ID = -1"  # not sure that this where_clause is necessary
        soilLines = "SoilLines"
        arcpy.MakeFeatureLayer_management(allLinesFC, soilLines, sqlSoilLines)
        soilCnt = int(arcpy.GetCount_management(soilLines).getOutput(0))

        if soilCnt == 0:
            PrintMsg(" \n\tWarning. No soil lines found for survey area: " + areasym, 1)


        arcpy.SimplifyLine_cartography(soilLines, simpleSoils, method, simpleTol, "", "NO_KEEP", "") # last parameter is barrier
        soilCnt = int(arcpy.GetCount_management(simpleSoils).getOutput(0))

        if soilCnt == 0:
            PrintMsg(" \n\tEmpty output for SimplifyLine: " + areasym, 1)


        soilLabels = os.path.join(env.scratchGDB, "SoilLabels_" + areasym)
        arcpy.FeatureToPoint_management(polyLayer, soilLabels, "INSIDE")



        # Interesting finding. Using FeatureToPolygon with label points does not always match up correctly.
        # Intersect with FID_Only seems to match up correctly
        # Intersect with ALL attributes does not seem to match up correctly

    

        

        # Convert simplified soil lines, soil bnd and label points back into a featureclass in the outputFDS
        #
        #outputFCName = "Soils" + dMethods[method] + "_" + areasym
        outputFC = os.path.join(outputFDS, outputFCName)

        
        #env.XYTolerance = "0.5 Meters"  # Added this on my workstation version of the script on 2018-09-07. Losing polygons along the border with the original 0.001 tolerance from the FDS.
        envVal, envUnits = env.XYTolerance.split(" ")
        envVal = float(envVal) * 10.0
        #env.XYTolerance = str(envVal) + " " + envUnits
        env.XYTolerance = "0.5 Meters"
        
        PrintMsg("\tAssembling simplified featureclass: " + os.path.basename(outputFC) + " XYTolerance: " + str(env.XYTolerance), 0)

        theSoilLabels = "SoilLabels"

        arcpy.MakeFeatureLayer_management(soilLabels, theSoilLabels, wc)
        # Get label point count
        labelCnt = int(arcpy.GetCount_management(theSoilLabels).getOutput(0))

        # PrintMsg(" \n\t" + soilBnd + ":  " + Number_Format(bndCnt, 0, True) + " \n\t" + simpleSoils + ":  " + Number_Format(soilCnt, 0, True) + " \n\t" + soilLabels + ":  " + Number_Format(labelCnt, 0, True), 1)

        # With this next option, I will have to manually add the appropriate attribute columns and then one-by-one reattribute from
        # the label points
        arcpy.FeatureToPolygon_management([soilBnd, simpleSoils], outputFC, "", "NO_ATTRIBUTES")
        arcpy.AddSpatialIndex_management(outputFC)

        # Intersect label points with output polygons to get links between FIDs
        joinFC = os.path.join(env.scratchGDB, "LabelJoin_" + areasym)
        arcpy.Intersect_analysis([soilLabels, outputFC], joinFC, "ONLY_FID", "", "POINT")
        # Polygon ObjectID fieldname: os.path.basename(joinFC) + "_OBJECTID"
        # Intersect label point ObjectID should be the same as the original label point's

        # Create dictionary with polygon id as key and label point id as dictionary value
        dJoin = dict()
        pointFld = "FID_" + os.path.basename(soilLabels)
        polyFld = "FID_" + os.path.basename(outputFC)
        #PrintMsg("\tPolygon FID: " + polyFld, 1)
        
        with arcpy.da.SearchCursor(joinFC, [polyFld, pointFld]) as cur:
            for rec in cur:
                # dJoin[polygon id] = label point id
                dJoin[rec[0]] = rec[1]

        # Get dictionary with label point id as key and [areasymbol, spatialver, musym, mukey] as the value
        dPoints = dict()

        with arcpy.da.SearchCursor(soilLabels, ["OID@", "areasymbol", "spatialver", "musym", "mukey"]) as cur:
            for rec in cur:
                dPoints[rec[0]] = rec[1:]
                      
        

        # Add SSURGO attribute columns
        arcpy.SetProgressorLabel("Adding new polygon attribute fields")
        
        arcpy.AddField_management(outputFC, "AREASYMBOL", "TEXT", "", "", 20)
        arcpy.AddField_management(outputFC, "SPATIALVER", "DOUBLE", "", "", 20)
        arcpy.AddField_management(outputFC, "MUSYM", "TEXT", "", "", 6)
        arcpy.AddField_management(outputFC, "MUKEY", "TEXT", "", "", 30)
        #arcpy.AddField_management(outputFC, "XX_SOILCOV_ID", "LONG")

        #  Create FeatureLayer for new output soil polygon featureclass
        outputLayer = "Output Soils Layer"
        arcpy.MakeFeatureLayer_management(outputFC, outputLayer)

        # *****************************************************************
        # RE-ATTRIBUTE POLYGONS USING LABEL POINTS (OMG. SLOW METHOD)
        # *****************************************************************

        #arcpy.SetProgressor("step", "Updating polygon attributes...", 1, labelCnt, 1)

        with arcpy.da.UpdateCursor(outputFC, ["OID@", "areasymbol", "spatialver", "musym", "mukey"]) as cur:
            for rec in cur:
                # areasymbol, spatialver, musym, mukey = dPoints[label point id]
                try:
                    rec[1:] = dPoints[dJoin[rec[0]]]

                except:
                    rec[1:] = [None, None, None, None]
                    
                cur.updateRow(rec)
                


        # Using featurelayers...
        #arcpy.FeatureToPolygon_management([soilBnd, simpleSoils], outputFC, "", "ATTRIBUTES", theSoilLabels)
        # Add status field to outputFC. Use this field to flag polygons for elimination or reattribution.
        # 1 = eliminate; 2 = reattribute
        #PrintMsg(" \n\tAdding ELIM field to " + outputFC, 1)
        arcpy.AddField_management(outputFC, "ELIM", "SHORT", "", "", "")

        #arcpy.FeatureToPolygon_management([soilBnd, simpleSoils], outputFC, "1.0 Meters", "ATTRIBUTES", theSoilLabels)
        #arcpy.Delete_management(outputCov)
        arcpy.Delete_management(theSoilLabels)


        # *****************************************************************
        # IDENTIFY SMALL POLYGONS OR ANY THAT ARE MISSING SOIL ATTRIBUTES
        # *****************************************************************
        wcMissing = "mukey = ''"
        centroidList = list()
        elimList = list()
        missingCnt = 0
        # PrintMsg(" \n\tIdentifying '" + outputFCName + "' layer polygons less than 0.1 acres or larger areas missing soil attributes", 1)
        arcpy.SetProgressorLabel("Identifying unlabeled or very small polygons")



 
        with arcpy.da.UpdateCursor(outputFC, ["OID@", "SHAPE@", "mukey", "elim"]) as cur:                           # This one looks at all polygons
            for rec in cur:
                missingCnt += 1
                fid, shape, mukey, elim = rec
                acres = shape.getArea("PRESERVE_SHAPE", "ACRES")
                area = shape.area

                if acres < 0.10:
                    # small area, add it to the list for elimination
                    #PrintMsg("\tFeature " + str(fid) + " has a smaller area and will be eliminated", 1)
                    elimList.append(fid)
                    elim = 1

                elif mukey is None:
                    # larger area, add it to the list for re-attibution.
                    #PrintMsg("\tFeature " + str(fid) + " has a larger area and will be re-attributed", 1)
                    centroidPnt = shape.centroid
                    centroidList.append(arcpy.PointGeometry(centroidPnt))
                    elim = 2

                rec = fid, shape, mukey, elim
                cur.updateRow(rec)

        # *****************************************************************
        # ELIMINATE THE number 1's
        # *****************************************************************
        
        if len(elimList) > 0:
            #PrintMsg(" \nRunning eliminate on " + outputFC, 1)

            # Eliminate_management (in_features, out_feature_class, {selection}, {ex_where_clause}, {ex_features})
            elimLayer = "Elim_" + areasym
            elimFC = os.path.join(outputFDS, elimLayer)
            
            # PrintMsg("\telimFC = " + elimFC, 1)

        if bndCnt == 0:
            if arcpy.Exists(elimFC):
                # left over from previous run
                arcpy.Delete_management(elimFC)


            # Reselect small polygons using the ELIM 
            wcElim = "elim = 1"
            
            PrintMsg("\tTargeting " + Number_Format(len(elimList), 0, True) + " small polygons for elimination", 1)
            arcpy.SelectLayerByAttribute_management(outputLayer, "NEW_SELECTION", wcElim)
            arcpy.Eliminate_management(outputLayer, elimFC, "LENGTH")

            if arcpy.Exists(elimFC):
                env.workspace = outputGDB
                #PrintMsg("\nRenaming output featureclass...", 0)
                arcpy.Delete_management(outputFC)
                arcpy.Rename_management(elimFC, outputFC)

        # *****************************************************************
        # RE-ATTRIBUTE LARGER POLYGONS
        # *****************************************************************

        if len(centroidList) > 0:
            # Retrieve missing attributes from input soil polygon layer
            PrintMsg("\tUpdating " + Number_Format(len(centroidList), 0, True) + " polygons with missing attributes", 0)
            
            for centroidPnt in centroidList:

                # Use the centroid from the missing polygon to select the source polygon at the same location
                arcpy.SelectLayerByLocation_management(soilLayer, "INTERSECT", centroidPnt, "", "NEW_SELECTION")
                srcCnt = int(arcpy.GetCount_management(soilLayer).getOutput(0))
                
                if srcCnt == 0:
                    arcpy.SelectLayerByLocation_management(soilLayer, "INTERSECT", centroidPnt, "", "NEW_SELECTION")

                if srcCnt > 0:

                    # Use the centroid again to select the polygon missing data in the output featurelayer
                    arcpy.SelectLayerByLocation_management(outputLayer, "INTERSECT", centroidPnt, "", "NEW_SELECTION")
                    
                    
                    if int(arcpy.GetCount_management(outputLayer).getOutput(0)) > 0:
                        with arcpy.da.SearchCursor(soilLayer, ["areasymbol", "spatialver", "musym", "mukey"]) as srcCur:
                            # this cursor should only contain one record selected by the centroid location
                            
                            for rec in srcCur:
                                # Get the missing attributes from the source
                                areasym, spatialver, musym, mukey = rec  # 

                            # Now select the output featureclass polygon that is missing attributes and use the
                            # information above to populate it
                            # wcMissing = "elim = 1 AND mukey = ''"

                            outCur = arcpy.da.UpdateCursor(outputLayer, ["areasymbol", "spatialver", "musym", "mukey"])
                            
                            for rec in outCur:
                                # replace missing data in the output featureclass
                                newrec = [areasym, spatialver, musym, mukey]
                                #PrintMsg("\tUpdating polygon to " + str(newrec), 1)
                                outCur.updateRow(newrec)

                            del outCur

                    else:
                        PrintMsg("\tFailed to select polygon from output soilsLayer" , 1)
                        

                else:
                    PrintMsg(str(centroidPnt.centroid.X) + ", " + str(centroidPnt.centroid.Y), 1)

        arcpy.DeleteField_management(outputFC, "ELIM")
        
        # Get vertex count AFTER and report difference in polygon size
        #PrintMsg("\tGetting after vertex count", 0)
        vertexCnt2 = 0
        dMapunitAcres2 = dict()
        #chkPolyList = list()

        with arcpy.da.SearchCursor(outputFC, ["SHAPE@", "mukey", "OID@"]) as cur:
            for rec in cur:
                shape, mukey, objectID = rec
                
                #if not mukey is None:
                #    mukey = mukey.encode('ascii')
                acres = shape.getArea("PRESERVE_SHAPE", "ACRES")

                #PrintMsg("\t" + mukey + ": " + str(acres), 1)
                
                try:
                    dMapunitAcres2[mukey] += acres

                except:
                    dMapunitAcres2[mukey] = acres

                vertexCnt2 += rec[0].pointCount                        

        # Compare map unit acres before and after
        PrintMsg("\tChecking mapunit acres...", 0)
        
        for mukey, beforeAcres in dMapunitAcres.items():
            try:
                afterAcres = dMapunitAcres2[mukey]
                acresDiff = abs(beforeAcres - afterAcres)

                if acresDiff > 0.1:
                    PrintMsg("\t\tMapunit '" + mukey + "' has a " + Number_Format(acresDiff, 2, True) + " acre change (" + Number_Format(beforeAcres, 1, True) + " --> " + Number_Format(afterAcres, 1, True) + ")", 1)
                    
            except KeyError:
                PrintMsg("\t\tMissing mukey (" + mukey + ") in dMapunitAcres2 dictionary. BeforeAcres: " + Number_Format(beforeAcres, 1, True), 1)

        # Get polygon count AFTER all cleanup is finished
        polyCnt2 = int(arcpy.GetCount_management(outputFC).getOutput(0))
        polyDiff = abs(polyCnt2 - polyCnt1)

        if polyDiff > 0:
            PrintMsg("\tPolygon count change. Before: " + Number_Format(polyCnt1, 0, True) + ";  After: " + Number_Format(polyCnt2, 0, True), 1)

        
        # Write results to report table
        fieldNames = ["AREASYMBOL", "LAYER_NAME", "RUN_DATE", "POLY_CNT1", "POLY_CNT2", "POLY_DIFF", "POLY_ELIM", "NO_ATTS", "VERT_CNT1", "VERT_CNT2", "VERT_DIFF", "VERT_PCT", "SETTINGS", "CS_NAME"]
                
        vertexChng = vertexCnt1 - vertexCnt2
        vertPct = round((vertexChng * 100.0 / vertexCnt2), 1)

        rec = [areasym, outputFCName, sToday, polyCnt1, polyCnt2, polyDiff, len(elimList), noAtt, vertexCnt1, vertexCnt2, vertexChng, vertPct, settings, csName]

        #PrintMsg(" \n" + str(fieldNames), 1)

        with arcpy.da.InsertCursor(os.path.join(outputGDB, processReport), fieldNames) as cur:
            #PrintMsg( str(rec), 1)
            cur.insertRow(rec)


        if vertexChng > 0:
            PrintMsg("\tNumber of vertices reduced by " + str(vertPct) + "%: " + Number_Format(vertexChng, 0, True) + "  (" + Number_Format(vertexCnt1, 0, True) + " --> " + Number_Format(vertexCnt2, 0, True) + ")", 0)

        elif vertexChng == 0:
            PrintMsg("\tNo change in number of vertices:  " + Number_Format(vertexCnt1, 0, True) + " --> " + Number_Format(vertexCnt2, 0, True), 0)

        else:
            PrintMsg("\tNumber of vertices added: " + Number_Format(vertexChng, 0, True) + "  (" + Number_Format(vertexCnt1, 0, True) + " --> " + Number_Format(vertexCnt2, 0, True) + ")", 1)
        
        arcpy.SelectLayerByAttribute_management(soilLayer, "CLEAR_SELECTION")

        # Cleanup temporary layers
        layerList = [tmpFC, allLinesFC, bndLayer, simpleSoils, soilLabels, bndLayer, soilBnd, outputCov, joinFC]
        # layerList = [tmpFC, allLinesFC, bndLayer, bndLayer]
        layerList = []
        
        for layer in layerList:
            arcpy.Delete_management(layer)
            #PrintMsg("\t\tKeeping temporary layer: " + layer, 1)
            #pass

        del tmpFC, allLinesFC, simpleSoils, soilLabels, bndLayer, soilBnd, outputCov, joinFC
        
        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False
        
## ===================================================================================
# main
# Import system modules
import arcpy, sys, os, locale, string, traceback, datetime
from arcpy import env


try:

    arcpy.overwriteOutput = True

    # Script arguments...
    surveyBoundaryLayer = arcpy.GetParameterAsText(0)
    surveyList = arcpy.GetParameter(1)
    soilPolygons = arcpy.GetParameter(2)     # input soil polygon layer or featureclass
    outputFDS = arcpy.GetParameterAsText(3)
    fcName = arcpy.GetParameterAsText(4)     # optional output featureclass name
    method = arcpy.GetParameterAsText(5)
    simpleTol = arcpy.GetParameterAsText(6)
    bOverwrite = arcpy.GetParameter(7)
    bCleanUp = arcpy.GetParameter(8)

    # initialize error and progress trackers
    failedList = list()  # track list of failed downloads
    failedCnt = 0        # track consecutive failures
    skippedList = list() # track list of downloads that were skipped because a newer version already exists
    goodList = list()    # list of successful surveys
    fcName = os.path.basename(fcName)

    PrintMsg(" \n" + str(len(surveyList)) + " soil survey(s) selected for processing...", 0)

    # Get datestamp for report
    today = datetime.date.today()
    sToday = today.strftime('%Y%m%d')

    # Get geodatabase for featuredataset
    fdsDesc = arcpy.Describe(outputFDS)
    outputGDB = os.path.dirname(fdsDesc.catalogPath)
    

    fdsSR = fdsDesc.spatialReference
    fdsSRType = fdsSR.type

    if fdsSRType == "Geographic":
        fdsSRUnits = fdsSR.angularUnitName

    else:
        fdsSRUnits = fdsSR.linearUnitName

    xyTol = fdsSR.XYTolerance
    xyRes = fdsSR.XYResolution



    # PROBLEM HERE. CopyFeatures is not creating features when input and output csr are different
    #
    #env.outputCoordinateSystem = spatialRef  # all geoprocessing layers should have the same coordinate system
    #env.XYResolution = str(xyRes) + " " + srUnits
    #env.XYTolerance = str(xyTol) + " " + srUnits             # This environment setting should match the FDS.

    tm = "WGS_1984_(ITRF00)_To_NAD_1983"
    env.geographicTransformations = tm
    #PrintMsg(" \nOutput spatial reference: " + spatialRef.name + " : " + srType + " : " + srUnits, 1)
    #PrintMsg("Output XY resolution and tolerance: " + str(env.XYResolution) + ";  " + str(env.XYTolerance), 1)
    #raise MyError, "EARLY OUT"


    # Get coordinate system for output featuredataset
    #
    soilDesc = arcpy.Describe(soilPolygons)  # Only using this for datatype (featurelayer or featureclass)
    soilSR = soilDesc.spatialReference

    



    if bOverwrite:
        env.overwriteOutput = True
        
    outputList = list()

    # Get table for saving process statistics
    processReport = "SimplifyReport_" + sToday
    bReport = MakeReportTable(outputGDB, processReport)

    # Define abbreviation for simplification algorithms. The selected method will be
    # incorporated into the output featureclass name.
    dMethods = dict()
    dMethods["POINT_REMOVE"] = "PR"
    dMethods["BEND_SIMPLIFY"] = "BS"
    dMethods["WEIGHTED_AREA"] = "WA"
    

    if soilDesc.dataType.upper() == "FEATURECLASS":
        soilLayer = "soilLayer"
        arcpy.MakeFeatureLayer_management(soilPolygons, soilLayer)

    else:
        soilLayer = soilPolygons


    # Perform a spatial sort on the selected survey areas and use that
    # to resort surveyList the same way. List will consist of areasymbol values.

    sortedSSA = os.path.join(env.scratchGDB, "SortedSSA")
    ssaDesc = arcpy.Describe(surveyBoundaryLayer)
    shapeField = ssaDesc.featureclass.shapeFieldName
    arcpy.Sort_management(surveyBoundaryLayer, sortedSSA, shapeField, "LR")
    sortedList = list()

    with arcpy.da.SearchCursor(sortedSSA, ["areasymbol"]) as cur:
        for rec in cur:
            areasym = rec[0].encode('ascii')
            
            if areasym in surveyList:
                sortedList.append(areasym)


    # Get a list of other featuredatasets in the output geodatabase and make sure that
    # the outputFC does not exist in any of them. Only needed when there is more than one?
    env.workspace = outputGDB
    fdsList = arcpy.ListDatasets("*", "Feature")

    if len(fdsList) == 1:
        fdsList = list()

    
    rowCnt = 0
    arcpy.Delete_management(sortedSSA)

    processedList = list()
    
    for areasym in surveyList:  # Process in alphabetical order
        rowCnt += 1
        outputFCName = "Soils" + dMethods[method] + "_" + areasym

        #
        for fds in fdsList:
            #PrintMsg("\tFDS: " + fds, 1)
            testFC = os.path.join(os.path.join(outputGDB, fds), outputFCName)

            if arcpy.Exists(testFC):
                PrintMsg("\tDeleting " + testFC, 1)
                arcpy.Delete_management(testFC)

        if bOverwrite == False and arcpy.Exists(os.path.join(outputFDS, outputFCName)):
            # skip existing output
            pass
        
        else:
            # Create new simplified survey layer
            PrintMsg(" \n" + Number_Format(rowCnt, 0, True) + ". Processing soil survey: " + areasym, 0)
            arcpy.SetProgressorLabel(Number_Format(rowCnt, 0, True) + ". Processing soil survey: " + areasym)

            bDone = ProcessSurvey(outputGDB, outputFDS, surveyBoundaryLayer, soilLayer, areasym, method, simpleTol, sToday, fdsSR.name, outputFCName)

            if bDone == False:
                raise MyError, ""

            else:
                processedList.append(outputFCName)

    # Optional. If user specifies a single output featureclass, use append to create it.
    if len(processedList) > 0 and fcName != "":

        # Recreate outputList in spatially sorted order and use this for the Append command
        #outputList = [("Soils" + dMethods[method] + "_" + areasym) for areasym in sortedList]
        #PrintMsg(" \nOutput list: " + str(outputList), 1)
        bAppended = AppendSurveyAreas(outputFDS, fcName, method, sortedList)

        # If Append succeeds and user has set option to cleanup indivdual soil polygon layers, go ahead and remove them all.
        if bCleanUp and bAppended:
            #PrintMsg("\tDeleting individual soil survey layers...", 1)
            
            for outputFCName in processedList:
                #PrintMsg("\tDeleting " + fcName, 1)
                arcpy.Delete_management(outputFCName)
            
    arcpy.SetProgressorLabel("Processing complete...")

    
    PrintMsg(" \nOutput report: " + processReport + " \n ", 0)


except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
