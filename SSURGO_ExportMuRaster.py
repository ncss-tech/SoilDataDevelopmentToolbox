# SSURGO_ExportMuRaster.py
#
# Convert MUPOLYGON featureclass to raster for the specified SSURGO geodatabase.
# By default any small NoData areas (< 5000 sq meters) will be filled using
# the Majority value.
#
# Input mupolygon featureclass must have a projected coordinate system or it will skip.
# Input databases and featureclasses must use naming convention established by the
# 'SDM Export By State' tool.
#
# For geographic regions that have USGS NLCD available, the tool wil automatically
# align the coordinate system and raster grid to match.
#
# 10-31-2013 Added gap fill method
#
# 11-05-2014
# 11-22-2013
# 12-10-2013  Problem with using non-unique cellvalues for raster. Going back to
#             creating an integer version of MUKEY in the mapunit polygon layer.
# 12-13-2013 Occasionally see error messages related to temporary GRIDs (g_g*) created
#            under "C:\Users\steve.peaslee\AppData\Local\Temp\a subfolder". These
#            are probably caused by orphaned INFO tables.
# 01-08-2014 Added basic raster metadata (still need process steps)
# 01-12-2014 Restricted conversion to use only input MUPOLYGON featureclass having
#            a projected coordinate system with linear units=Meter
# 01-31-2014 Added progressor bar to 'Saving MUKEY values..'. Seems to be a hangup at this
#            point when processing CONUS geodatabase
# 02-14-2014 Changed FeatureToLayer (CELL_CENTER) to PolygonToRaster (MAXIMUM_COMBINED_AREA)
#            and removed the Gap Fill option.
# 2014-09-27 Added ISO metadata import
#
# 2014-10-18 Noticed that failure to create raster seemed to be related to long
# file names or non-alphanumeric characters such as a dash in the name.
#
# 2014-10-29 Removed ORDER BY MUKEY sql clause because some computers were failing on that line.
#            Don't understand why.
#
# 2014-10-31 Added error message if the MUKEY column is not populated in the MUPOLYGON featureclass
#
# 2014-11-04 Problems occur when the user's gp environment points to Default.gdb for the scratchWorkpace.
#            Added a fatal error message when that occurs.
#
# 2015-01-15 Hopefully fixed some of the issues that caused the raster conversion to crash at the end.
#            Cleaned up some of the current workspace settings and moved the renaming of the final raster.
#
# 2015-02-26 Adding option for tiling raster conversion by areasymbol and then mosaicing. Slower and takes
#            more disk space, but gets the job done when otherwise PolygonToRaster fails on big datasets.

# 2015-02-27 Make bTiling variable an integer (0, 2, 5) that can be used to slice the areasymbol value. This will
#            give the user an option to tile by state (2) or by survey area (5)
# 2015-03-10 Moved sequence of CheckInExtension. It was at the beginning which seems wrong.
#
# 2015-03-11 Switched tiled raster format from geodatabase raster to TIFF. This should allow the entire
#            temporary folder to be deleted instead of deleting rasters one-at-a-time (slow).
# 2015-03-11 Added attribute index (mukey) to raster attribute table
# 2015-03-13 Modified output raster name by incorporating the geodatabase name (after '_' and before ".gdb")
#
# 2015-09-16 Temporarily renamed output raster using a shorter string
#
# 2015-09-16 Trying several things to address 9999 failure on CONUS. Created a couple of ArcInfo workspace in temp
# 2015-09-16 Compacting geodatabase before PolygonToRaster conversion
#
# 2015-09-18 Still having problems with CONUS raster even with ArcGIS 10.3. Even the tiled method failed once
#            on AR105. Actually may have been the next survey, but random order so don't know which one for sure.
#            Trying to reorder mosaic to match the spatial order of the polygon layers. Need to figure out if
#            the 99999 error in PolygonToRaster is occurring with the same soil survey or same count or any
#            other pattern.
#
# 2015-09-18 Need to remember to turn off all layers in ArcMap. Redraw is triggered after each tile.
#
# 2015-10-01 Found problem apparently caused by 10.3. SnapRaster functionality was failing with tiles because of
#            MakeFeatureLayer where_clause. Perhaps due to cursor lock persistence? Rewrote entire function to
#            use SAPOLYGON featureclass to define extents for tiles. This seems to be working better anyway.
#
# 2015-10-02 Need to look at some method for sorting the extents of each tile and sort them in a geographic fashion.
#            A similar method was used in the Create gSSURGO database tools for the Append process.
#
# 2015-10-23 Jennifer and I finally figured out what was causing her PolygonToRaster 9999 errors.
#           It was dashes in the output GDB path. Will add a check for bad characters in path.
#
# 2015-10-26 Changed up SnapToNLCD function to incorporate SnapRaster input as long as the coordinate
#           system matches and the extent coordinates are integer (no floating point!).
#
# 2015-10-27 Looking at possible issue with batchmode processing of rasters. Jennifer had several
#           errors when trying to run all states at once.
#
# 2015-11-03 Fixed failure when indexing non-geodatabase rasters such as .IMG.
#
# 2018-07-12 Removed possibly unneccessary ArcINFO workspace creation because it requires an Advanced license - Olga

# 2018-09-11 Removed 'ImportMetadata_conversion' because I suddenly started getting that Tool validation error. Possibly due
#            to a Windows or IE update?


## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
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
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + "\n" + str(sys.exc_type)+ ": " + str(sys.exc_value)
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in errorMsg method", 2)
        pass

## ===================================================================================
def SetScratch():
    # try to set scratchWorkspace and scratchGDB if null
    #        SYSTEMDRIVE
    #        APPDATA C:\Users\adolfo.diaz\AppData\Roaming
    #        USERPROFILE C:\Users\adolfo.diaz
    try:
        #envVariables = os.environ

        #for var, val in envVariables.items():
        #    PrintMsg("\t" + str(var) + ": " + str(val), 1)

        if env.scratchWorkspace is None:
            #PrintMsg("\tWarning. Scratchworkspace has not been set for the geoprocessing environment", 1)
            env.scratchWorkspace = env.scratchFolder
            #PrintMsg("\nThe scratch geodatabase has been set to: " + str(env.scratchGDB), 1)

        elif str(env.scratchWorkspace).lower().endswith("default.gdb"):
            #PrintMsg("\tChanging scratch geodatabase from Default.gdb", 1)
            env.scratchWorkspace = env.scratchFolder
            #PrintMsg("\tTo: " + str(env.scratchGDB), 1)

        #else:
        #    PrintMsg(" \nOriginal Scratch Geodatabase is OK: " + env.scratchGDB, 1)

        if env.scratchGDB:
            return True
        
        else:
            return False

    
    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return False

    except:
        errorMsg()
        return False

        
## ===================================================================================
def SnapToNLCD(inputFC, iRaster):
    # This function will set an output extent that matches the NLCD or a specified snapraster layer.
    # In effect this is like using NLCD as a snapraster as long as the projections are the same,
    # which is USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
    #
    # Returns empty string if linear units are not 'foot' or 'meter'

    try:
        theDesc = arcpy.Describe(inputFC)
        sr = theDesc.spatialReference
        inputSRName = sr.name
        theUnits = sr.linearUnitName
        pExtent = theDesc.extent

        PrintMsg(" \nCoordinate system: " + inputSRName + " (" + theUnits.lower() + ")", 0)

        if pExtent is None:
            raise MyError, "Failed to get extent from " + inputFC

        x1 = float(pExtent.XMin)
        y1 = float(pExtent.YMin)
        x2 = float(pExtent.XMax)
        y2 = float(pExtent.YMax)

        if 'foot' in theUnits.lower():
            theUnits = "feet"

        elif theUnits.lower() == "meter":
            theUnits = "meters"

        #if theSnapRaster == "":
        # Use fixed NLCD raster coordinates for different regions. These are all integer values.
        #
        # PrintMsg(" \nUsing NLCD snapraster: " + theSnapRaster, 1)
        # Hawaii_Albers_Equal_Area_Conic  -345945, 1753875
        # Western_Pacific_Albers_Equal_Area_Conic  -2390975, -703265 est.
        # NAD_1983_Alaska_Albers  -2232345, 344805
        # WGS_1984_Alaska_Albers  Upper Left Corner:  -366405.000000 meters(X),  2380125.000000 meters(Y)
        # WGS_1984_Alaska_Albers  Lower Right Corner: 517425.000000 meters(X),  2032455.000000 meters(Y)
        # Puerto Rico 3092415, -78975 (CONUS works for both)

        if theUnits != "meters":
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"

        elif inputSRName in ["Albers_Conical_Equal_Area", "USA_Contiguous_Albers_Equal_Area_Conic_USGS_version"]:
            # This used to be the Contiguous USGS version
            xNLCD = 532695
            yNLCD = 1550295

        elif inputSRName == "Hawaii_Albers_Equal_Area_Conic":
            xNLCD = -29805
            yNLCD = 839235

        elif inputSRName == "NAD_1983_Alaska_Albers":
            xNLCD = -368805
            yNLCD = 1362465

        elif inputSRName == "WGS_1984_Albers":
            # New WGS 1984 based coordinate system matching USGS 2001 NLCD for Alaska
            xNLCD = -366405
            yNLCD = 2032455

        elif inputSRName == "Western_Pacific_Albers_Equal_Area_Conic":
            # WGS 1984 Albers for PAC Basin area
            xNLCD = -2390975
            yNLCD = -703265

        else:
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"

        if 1 == 2:  # old code for using snap raster
            # Need to calculate a pair of Albers coordinates based upon the snapraster
            #PrintMsg(" \nUsing snapraster: " + theSnapRaster, 1)
            rDesc = arcpy.Describe(theSnapRaster)
            env.snapRaster = theSnapRaster

            # Compare input soil polygon featureclass with snapraster and see if they have the same coordinate system.
            if rDesc.spatialReference.name == theDesc.extent.spatialReference.name:
                # Same coordinate system, go ahead and
                xNLCD = rDesc.extent.XMin
                yNLCD = rDesc.extent.YMin
                if xNLCD != int(xNLCD) or yNLCD != int(yNLCD):
                    raise MyError, "SnapRaster has floating point extent coordinates"

            else:
                raise MyError, "Input featureclass and snapraster have different coordinate systems"


        pExtent = theDesc.extent  # Input featureclass extent
        x1 = float(pExtent.XMin)
        y1 = float(pExtent.YMin)
        x2 = float(pExtent.XMax)
        y2 = float(pExtent.YMax)

        # Round off coordinates to integer values based upon raster resolution
        # Use +- 5 meters to align with NLCD
        # Calculate snapgrid using 30 meter Kansas NLCD Lower Left coordinates = -532,695 X 1,550,295
        #
        #xNLCD = 532695
        #yNLCD = 1550295
        #iRaster = int(iRaster)

        # Calculate number of columns difference between KS NLCD and the input extent
        # Align with the proper coordinate pair

        iCol = int((x1 - xNLCD) / 30)
        iRow = int((y1 - yNLCD) / 30)

        x1 = (30 * iCol) + xNLCD - 60
        y1 = (30 * iRow) + yNLCD - 60

        numCols = int(round(abs(x2 - x1) / 30)) + 2
        numRows = int(round(abs(y2 - y1) / 30)) + 2

        x2 = numCols * 30 + x1
        y2 = numRows * 30 + y1

        theExtent = str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2)
        # Format coordinate pairs as string
        sX1 = Number_Format(x1, 0, True)
        sY1 = Number_Format(y1, 0, True)
        sX2 = Number_Format(x2, 0, True)
        sY2 = Number_Format(y2, 0, True)
        sLen = 11
        sX1 = ((sLen - len(sX1)) * " ") + sX1
        sY1 = " X " + ((sLen - len(sY1)) * " ") + sY1
        sX2 = ((sLen - len(sX2)) * " ") + sX2
        sY2 = " X " + ((sLen - len(sY2)) * " ") + sY2

        PrintMsg(" \nAligning output raster to match NLCD:", 0)
        PrintMsg("\tUR: " + sX2 + sY2 + " " + theUnits.lower(), 0)
        PrintMsg("\tLL: " + sX1 + sY1 + " " + theUnits.lower(), 0)
        PrintMsg(" \n\tNumber of rows =    \t" + str(numRows * 30 / iRaster), 0)
        PrintMsg("\tNumber of columns = \t" + str(numCols * 30 / iRaster), 0)

        return theExtent

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def SnapToNLCD_original(inputFC, iRaster):
    # This function will set an output extent that matches the NLCD raster dataset.
    # In effect this is like using NLCD as a snapraster as long as the projections are the same,
    # which is USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
    #
    # Returns empty string if linear units are not 'foot' or 'meter'

    try:
        theDesc = arcpy.Describe(inputFC)
        sr = theDesc.spatialReference
        inputSRName = sr.name
        theUnits = sr.linearUnitName
        pExtent = theDesc.extent

        PrintMsg(" \nCoordinate system: " + inputSRName + " (" + theUnits.lower() + ")", 0)

        if pExtent is None:
            raise MyError, "Failed to get extent from " + inputFC

        x1 = float(pExtent.XMin)
        y1 = float(pExtent.YMin)
        x2 = float(pExtent.XMax)
        y2 = float(pExtent.YMax)

        if 'foot' in theUnits.lower():
            theUnits = "feet"

        elif theUnits.lower() == "meter":
            theUnits = "meters"

        # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version (NAD83)
        xNLCD = 532695
        yNLCD = 1550295

        # Hawaii_Albers_Equal_Area_Conic  -345945, 1753875
        # Western_Pacific_Albers_Equal_Area_Conic  -2390975, -703265 est.
        # NAD_1983_Alaska_Albers  -2232345, 344805
        # WGS_1984_Alaska_Albers  Upper Left Corner:  -366405.000000 meters(X),  2380125.000000 meters(Y)
        # WGS_1984_Alaska_Albers  Lower Right Corner: 517425.000000 meters(X),  2032455.000000 meters(Y)
        # Puerto Rico 3092415, -78975 (CONUS works for both)

        if theUnits != "meters":
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"

        elif inputSRName == "USA_Contiguous_Albers_Equal_Area_Conic_USGS_version":
            xNLCD = 532695
            yNLCD = 1550295

        elif inputSRName == "Hawaii_Albers_Equal_Area_Conic":
            xNLCD = -29805
            yNLCD = 839235

        elif inputSRName == "NAD_1983_Alaska_Albers":
            xNLCD = -368805
            yNLCD = 1362465

        elif inputSRName == "WGS_1984_Albers":
            # New WGS 1984 based coordinate system matching USGS 2001 NLCD for Alaska
            xNLCD = -366405
            yNLCD = 2032455

        elif inputSRName == "Western_Pacific_Albers_Equal_Area_Conic":
            # WGS 1984 Albers for PAC Basin area
            xNLCD = -2390975
            yNLCD = -703265

        else:
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"

        pExtent = theDesc.extent
        x1 = float(pExtent.XMin)
        y1 = float(pExtent.YMin)
        x2 = float(pExtent.XMax)
        y2 = float(pExtent.YMax)

        # Round off coordinates to integer values based upon raster resolution
        # Use +- 5 meters to align with NLCD
        # Calculate snapgrid using 30 meter Kansas NLCD Lower Left coordinates = -532,695 X 1,550,295
        #
        xNLCD = 532695
        yNLCD = 1550295
        iRaster = int(iRaster)

        # Calculate number of columns difference between KS NLCD and the input extent
        # Align with NLCD CONUS
        # Finding that with tile method, I am losing pixels along the edge!!!
        # Do I need to move x1 and y1 southwest one pixel and then add two pixels to the column and row width?
        iCol = int((x1 - xNLCD) / 30)
        iRow = int((y1 - yNLCD) / 30)
        #x1 = (30 * iCol) + xNLCD - 30
        #y1 = (30 * iRow) + yNLCD - 30

        x1 = (30 * iCol) + xNLCD - 60
        y1 = (30 * iRow) + yNLCD - 60

        numCols = int(round(abs(x2 - x1) / 30)) + 2
        numRows = int(round(abs(y2 - y1) / 30)) + 2

        x2 = numCols * 30 + x1
        y2 = numRows * 30 + y1

        theExtent = str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2)
        # Format coordinate pairs as string
        sX1 = Number_Format(x1, 0, True)
        sY1 = Number_Format(y1, 0, True)
        sX2 = Number_Format(x2, 0, True)
        sY2 = Number_Format(y2, 0, True)
        sLen = 11
        sX1 = ((sLen - len(sX1)) * " ") + sX1
        sY1 = " X " + ((sLen - len(sY1)) * " ") + sY1
        sX2 = ((sLen - len(sX2)) * " ") + sX2
        sY2 = " X " + ((sLen - len(sY2)) * " ") + sY2

        PrintMsg(" \nAligning output raster to match NLCD:", 0)
        PrintMsg("\tUR: " + sX2 + sY2 + " " + theUnits.lower(), 0)
        PrintMsg("\tLL: " + sX1 + sY1 + " " + theUnits.lower(), 0)
        PrintMsg(" \n\tNumber of rows =    \t" + Number_Format(numRows * 30 / iRaster), 0)
        PrintMsg("\tNumber of columns = \t" + Number_Format(numCols * 30 / iRaster), 0)

        return theExtent

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def TiledExtents(inputSA, tileList, theDesc, iRaster, bTiled):

    # Returns empty string if linear units are not 'foot' or 'meter'

    try:
        dExtents = dict()

        if bTiled == "Large":
            with arcpy.da.SearchCursor(inputSA, ["SHAPE@", "AREASYMBOL"]) as cur:

                for rec in cur:
                    polygon, areaSym = rec
                    st = areaSym[0:2]
                    pExtent = polygon.extent
                    try:
                        # expand existing extent for this state
                        xMin, yMin, xMax, yMax = dExtents[st] # get previous extent
                        xMin = min(xMin, pExtent.XMin)
                        yMin = min(yMin, pExtent.YMin)
                        xMax = max(xMax, pExtent.XMax)
                        yMax = max(yMax, pExtent.YMax)
                        dExtents[st] = xMin, yMin, xMax, yMax # update extent to include this polygon

                    except:
                        # first polygon for this state
                        dExtents[st] = pExtent.XMin, pExtent.YMin, pExtent.XMax, pExtent.YMax


        elif bTiled == "Small":
            with arcpy.da.SearchCursor(inputSA, ["SHAPE@", "AREASYMBOL"]) as cur:

                for rec in cur:
                    polygon, areaSym = rec
                    pExtent = polygon.extent
                    try:
                        # expand existing extent for this state
                        xMin, yMin, xMax, yMax = dExtents[areaSym] # get previous extent
                        xMin2 = min(xMin, pExtent.XMin)
                        yMin2 = min(yMin, pExtent.YMin)
                        xMax2 = max(xMax, pExtent.XMax)
                        yMax2 = max(yMax, pExtent.YMax)
                        dExtents[areaSym] = xMin2, yMin2, xMax2, yMax2 # update extent to include this polygon

                    except:
                        # first polygon for this state
                        dExtents[areaSym] = pExtent.XMin, pExtent.YMin, pExtent.XMax, pExtent.YMax


        for tile in tileList:
            beginExtent = dExtents[tile]
            rasExtent = AdjustExtent(beginExtent, theDesc, iRaster)
            dExtents[tile] = rasExtent

        return dExtents

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return dExtents

    except:
        errorMsg()
        return dExtents

## ===================================================================================
def AdjustExtent(beginExtent, theDesc, iRaster):
    # This function is used to set an output extent for each tile that matches the NLCD raster dataset.
    # In effect this is like using NLCD as a snapraster as long as the projections are the same,
    # which is USA_Contiguous_Albers_Equal_Area_Conic_USGS_version
    #
    # Major problem. Extent from featurelayer is the same as the original featureclass.
    # Need to copy SAPOLYGON features to a temporary featureclass and get the extent from that instead.
    #
    # Returns empty string if linear units are not 'foot' or 'meter'

    try:
        #theDesc = arcpy.Describe(tmpSA)
        sr = theDesc.spatialReference
        inputSRName = sr.name
        theUnits = sr.linearUnitName

        x1 = float(beginExtent[0])
        y1 = float(beginExtent[1])
        x2 = float(beginExtent[2])
        y2 = float(beginExtent[3])

        if 'foot' in theUnits.lower():
            theUnits = "feet"

        elif theUnits.lower() == "meter":
            theUnits = "meters"

        # USA_Contiguous_Albers_Equal_Area_Conic_USGS_version (NAD83)
        xNLCD = 532695
        yNLCD = 1550295

        # Hawaii_Albers_Equal_Area_Conic  -345945, 1753875
        # Western_Pacific_Albers_Equal_Area_Conic  -2390975, -703265 est.
        # NAD_1983_Alaska_Albers  -2232345, 344805
        # WGS_1984_Alaska_Albers  Upper Left Corner:  -366405.000000 meters(X),  2380125.000000 meters(Y)
        # WGS_1984_Alaska_Albers  Lower Right Corner: 517425.000000 meters(X),  2032455.000000 meters(Y)
        # Puerto Rico 3092415, -78975 (CONUS works for both)

        if theUnits != "meters":
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"

        elif inputSRName == "USA_Contiguous_Albers_Equal_Area_Conic_USGS_version":
            xNLCD = 532695
            yNLCD = 1550295

        elif inputSRName == "Hawaii_Albers_Equal_Area_Conic":
            xNLCD = -29805
            yNLCD = 839235

        elif inputSRName == "NAD_1983_Alaska_Albers":
            xNLCD = -368805
            yNLCD = 1362465

        elif inputSRName == "WGS_1984_Albers":
            # New WGS 1984 based coordinate system matching USGS 2001 NLCD for Alaska
            xNLCD = -366405
            yNLCD = 2032455

        elif inputSRName == "Western_Pacific_Albers_Equal_Area_Conic":
            # WGS 1984 Albers for PAC Basin area
            xNLCD = -2390975
            yNLCD = -703265

        else:
            PrintMsg("Projected coordinate system is " + inputSRName + "; units = '" + theUnits + "'", 0)
            raise MyError, "Unable to align raster output with this coordinate system"


        # Round off coordinates to integer values based upon raster resolution
        # Use +- 5 meters to align with NLCD
        # Calculate snapgrid using 30 meter Kansas NLCD Lower Left coordinates = -532,695 X 1,550,295
        #
        xNLCD = 532695
        yNLCD = 1550295
        iRaster = int(iRaster)

        # Calculate number of columns difference between KS NLCD and the input extent
        # Align with NLCD CONUS
        # Finding that with tile method, I am losing pixels along the edge!!!
        # Do I need to move x1 and y1 southwest one pixel and then add two pixels to the column and row width?
        iCol = int((x1 - xNLCD) / 30)
        iRow = int((y1 - yNLCD) / 30)
        #x1 = (30 * iCol) + xNLCD - 30
        #y1 = (30 * iRow) + yNLCD - 30

        x1 = (30 * iCol) + xNLCD - 60
        y1 = (30 * iRow) + yNLCD - 60

        numCols = int(round(abs(x2 - x1) / 30)) + 2
        numRows = int(round(abs(y2 - y1) / 30)) + 2

        x2 = numCols * 30 + x1
        y2 = numRows * 30 + y1

        theExtent = str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2)
        # Format coordinate pairs as string
        sX1 = Number_Format(x1, 0, True)
        sY1 = Number_Format(y1, 0, True)
        sX2 = Number_Format(x2, 0, True)
        sY2 = Number_Format(y2, 0, True)
        sLen = 11
        sX1 = ((sLen - len(sX1)) * " ") + sX1
        sY1 = " X " + ((sLen - len(sY1)) * " ") + sY1
        sX2 = ((sLen - len(sX2)) * " ") + sX2
        sY2 = " X " + ((sLen - len(sY2)) * " ") + sY2

        #PrintMsg(" \nAdjustExtent is aligning output tile to match NLCD:", 0)
        #PrintMsg("\tUR: " + sX2 + sY2 + " " + theUnits.lower(), 0)
        #PrintMsg("\tLL: " + sX1 + sY1 + " " + theUnits.lower(), 0)
        #PrintMsg(" \n\tNumber of rows =    \t" + Number_Format(numRows * 30 / iRaster), 0)
        #PrintMsg("\tNumber of columns = \t" + Number_Format(numCols * 30 / iRaster), 0)

        return theExtent

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e) + " \n ", 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def WriteToLog(theMsg, theRptFile):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #print msg
    #
    try:
        fh = open(theRptFile, "a")
        theMsg = "\n" + theMsg
        fh.write(theMsg)
        fh.close()

    except:
        errorMsg()
        pass

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
        return False

## ===================================================================================
def ListEnv():
    # List geoprocessing environment settings
    try:
        environments = arcpy.ListEnvironments()

        # Sort the environment list, disregarding capitalization
        #
        environments.sort(key=string.lower)

        for environment in environments:
            # As the environment is passed as a variable, use Python's getattr
            #   to evaluate the environment's value
            #
            envSetting = getattr(arcpy.env, environment)

            # Format and print each environment and its current setting
            #
            #print "{0:<30}: {1}".format(environment, envSetting)
            PrintMsg("\t" + environment + ": " + str(envSetting), 0)

    except:
        errorMsg()

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
def CheckStatistics(outputRaster):
    # For no apparent reason, ArcGIS sometimes fails to build statistics. Might work one
    # time and then the next time it may fail without any error message.
    #
    try:
        #PrintMsg(" \n\tChecking raster statistics", 0)

        for propType in ['MINIMUM', 'MAXIMUM', 'MEAN', 'STD']:
            statVal = arcpy.GetRasterProperties_management (outputRaster, propType).getOutput(0)
            #PrintMsg("\t\t" + propType + ": " + statVal, 1)

        return True

    except:
        return False

## ===================================================================================
def UpdateMetadata(theGDB, target, surveyInfo, iRaster):
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

        # Set metadata translator file
        dInstall = arcpy.GetInstallInfo()
        installPath = dInstall["InstallDir"]
        prod = r"Metadata/Translator/ARCGIS2FGDC.xml"
        mdTranslator = os.path.join(installPath, prod)  # This file is not being used

        # Define input and output XML files
        mdImport = os.path.join(env.scratchFolder, "xxImport.xml")  # the metadata xml that will provide the updated info
        xmlPath = os.path.dirname(sys.argv[0])
        mdExport = os.path.join(xmlPath, "gSSURGO_MapunitRaster.xml") # original template metadata in script directory
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
                    if child.text.find('xxSTATExx') >= 0:
                        newTitle = "Map Unit Raster " + str(iRaster) + "m - " + mdState
                        #PrintMsg("\t\tUpdating title to: " + newTitle, 1)
                        #child.text = child.text.replace('xxSTATExx', mdState)
                        child.text = newTitle

                    elif mdState != "":
                        child.text = child.text + " " + str(iRaster) + "m - " + mdState

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
def CheckSpatialReference(inputFC):
    # Make sure that the coordinate system is projected and units are meters
    try:
        desc = arcpy.Describe(inputFC)
        inputSR = desc.spatialReference

        if inputSR.type.upper() == "PROJECTED":
            if inputSR.linearUnitName.upper() == "METER":
                env.outputCoordinateSystem = inputSR
                return True

            else:
                raise MyError, os.path.basename(theGDB) + ": Input soil polygon layer does not have a valid coordinate system for gSSURGO"

        else:
            raise MyError, os.path.basename(theGDB) + ": Input soil polygon layer must have a projected coordinate system"

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def ConvertToRaster(target, iRaster, bTiled):
    # main function used for raster conversion
    try:
        #
        # Only use large tiles for multi-state, CONUS or regions
        # Important to understand that All tiles are based on AREASYMBOL values in SAPOLYGON featureclass

        # Set geoprocessing environment
        #
        env.overwriteOutput = True
        arcpy.env.compression = "LZ77"
        env.tileSize = "128 128"
        desc = arcpy.Describe(target)

        if desc.dataType.lower() == "workspace":
            theGDB = target
            inputFC = os.path.join(theGDB, "MUPOLYGON")

        elif desc.dataType.lower() == "featureclass":
            inputFC = target
            theGDB = os.path.dirname(target)

        # Make sure that the env.scratchGDB set, and not to Default.gdb. This causes problems for
        # some unknown reason.

        if not SetScratch():
            raise MyError, "Unable to set scratch workspace"


        # Create an ArcInfo workspace under the scratchFolder. Trying to prevent
        # 99999 errors for PolygonToRaster on very large databases
        #
        #aiWorkspace = env.scratchFolder

        #if not arcpy.Exists(os.path.join(aiWorkspace, "info")):
            #PrintMsg(" \nCreating ArcInfo workspace (" + os.path.basename(aiWorkspace) + ") in: " + os.path.dirname(aiWorkspace), 1)
        #    arcpy.CreateArcInfoWorkspace_management(os.path.dirname(aiWorkspace), os.path.basename(aiWorkspace))

        # turn off automatic Pyramid creation and Statistics calculation
        env.rasterStatistics = "NONE"
        env.pyramid = "PYRAMIDS 0"

        # Need to check for dashes or spaces in folder names or leading numbers in database or raster names

        # create final raster in same workspace as input polygon featureclass
        rasterExt = ""

        if desc.dataType.lower() == "workspace":
            # input is a geodatabase, skip the extra bit in the tilename. Just convert the standard MUPOLYGON.
            outputRaster = os.path.join(theGDB, "MapunitRaster_" + str(iRaster) + "m")

        else:
            # Input is a featureclass
            if os.path.basename(inputFC).upper() == "MUPOLYGON":
                outputRaster = os.path.join(theGDB, "MapunitRaster_" + str(iRaster) + "m")

            else:
                tileName = inputFC[(inputFC.rfind("_") + 1):]
                outputRaster = os.path.join(theGDB, "MapunitRaster_" + tileName.lower() + "_" + str(iRaster) + "m")

        inputSA = os.path.join(theGDB, "SAPOLYGON")

        if not arcpy.Exists(inputFC):
            raise MyError, "Could not find input featureclass: " + inputFC

        # Check input layer's coordinate system to make sure horizontal units are meters
        # set the output coordinate system for the raster (neccessary for PolygonToRaster)
        if CheckSpatialReference(inputFC) == False:
            return False

        # Sometimes it helps to compact large databases before raster conversion
        #arcpy.SetProgressorLabel("Compacting database prior to rasterization...")
        #arcpy.Compact_management(theGDB)

        # For rasters named using an attribute value, some attribute characters can result in
        # 'illegal' names.
        outputRaster = outputRaster.replace("-", "")

        if arcpy.Exists(outputRaster):
            arcpy.Delete_management(outputRaster)
            time.sleep(1)

        if arcpy.Exists(outputRaster):
            err = "Output raster (" + os.path.basename(outputRaster) + ") already exists"
            raise MyError, err

        start = time.time()   # start clock to measure total processing time
        #begin = time.time()   # start clock to measure set up time
        time.sleep(2)

        PrintMsg(" \nBeginning raster conversion process", 0)

        # Create Lookup table for storing MUKEY values and their integer counterparts
        #
        if bTiled in ["Large", "Small"]:
            lu = os.path.join(theGDB, "Lookup")

        else:
            # bTiled = None
            lu = os.path.join(env.scratchGDB, "Lookup")

        if arcpy.Exists(lu):
            arcpy.Delete_management(lu)

        # The Lookup table contains both MUKEY and its integer counterpart (CELLVALUE).
        # Using the joined lookup table creates a raster with CellValues that are the
        # same as MUKEY (but integer). This will maintain correct MUKEY values
        # during a moscaic or clip.
        #
        arcpy.CreateTable_management(os.path.dirname(lu), os.path.basename(lu))
        arcpy.AddField_management(lu, "CELLVALUE", "LONG")
        arcpy.AddField_management(lu, "MUKEY", "TEXT", "#", "#", "30")

        # Create list of areasymbols present in the MUPOLYGON featureclass
        # Having problems processing CONUS list of MUKEYs. Python seems to be running out of memory,
        # but I don't see high usage in Windows Task Manager
        #
        # PrintMsg(" \nscratchFolder set to: " + env.scratchFolder, 1)

        if bTiled in ["Large", "Small"]:
            PrintMsg("\tCreating tile inventory...", 0)
            arcpy.SetProgressor("default", "Creating tile inventory...")
            tileList = list()

            # Try creating a temporary folder for holding temporary rasters
            # This may allow the entire folder to be deleted at once instead of one raster at-a-time
            tmpFolder = os.path.join(env.scratchFolder, "TmpRasters")

            if arcpy.Exists(tmpFolder):
                shutil.rmtree(tmpFolder)

            sqlClause = ("DISTINCT", None)

            #with arcpy.da.SearchCursor(inputSA, ["AREASYMBOL"], sql_clause=sqlClause) as cur:
            with arcpy.da.SearchCursor(inputFC, ["AREASYMBOL"], sql_clause=sqlClause) as cur:
                # Create a unique, UNSORTED list of AREASYMBOL values in the SAPOLYGON featureclass
                # The original order of polygons in the SAPOLYGON featureclass should be sorted spatially.
                # Not sure if this order will help mosaic, but worth trying.

                if bTiled == "Small":
                    # Use soil survey areas as tile
                    for rec in cur:
                        # get areasymbol for tile value

                        if not rec[0] in tileList and rec[0] is not None:
                            tileList.append(rec[0])

                elif bTiled == "Large":
                    for rec in cur:
                        # Large tiles (state), using first two characters of AREASYMBOL
                        st = rec[0][0:2]
                        if not st in tileList:
                            tileList.append(st)


            tileCnt = len(tileList)

            if tileCnt == 1:
                # Only one tile in list
                # Switch to the 'un-tiled' mode
                bTiled = "None"

            elif tileCnt == 0:
                raise MyError, "Error creating list of " + bTiles.lower() + " tiles"

        # Create list of MUKEY values from the MUPOLYGON featureclass
        #
        # Create a list of map unit keys present in the MUPOLYGON featureclass
        #
        PrintMsg("\tGetting list of mukeys from input soil polygon layer...", 0)
        arcpy.SetProgressor("default", "Getting inventory of map units...")
        tmpPolys = "SoilPolygons"
        sqlClause = ("DISTINCT", None)

        with arcpy.da.SearchCursor(inputFC, ["MUKEY"], "", "", "", sql_clause=sqlClause) as srcCursor:
            # Create a unique, sorted list of MUKEY values in the MUPOLYGON featureclass
            mukeyList = [row[0] for row in srcCursor]

        mukeyList.sort()

        if len(mukeyList) == 0:
            raise MyError, "Failed to get MUKEY values from " + inputFC

        muCnt = len(mukeyList)

        # Load MUKEY values into Lookup table
        #
        #PrintMsg("\tSaving " + Number_Format(muCnt, 0, True) + " MUKEY values for " + Number_Format(polyCnt, 0, True) + " polygons"  , 0)
        arcpy.SetProgressorLabel("Creating lookup table...")

        with arcpy.da.InsertCursor(lu, ("CELLVALUE", "MUKEY") ) as inCursor:
            for mukey in mukeyList:
                rec = mukey, str(mukey)
                inCursor.insertRow(rec)

        # Add MUKEY attribute index to Lookup table
        arcpy.AddIndex_management(lu, ["mukey"], "Indx_LU")

        #
        # End of Lookup table code

        # Match NLCD raster (snapraster)
        #if theSnapRaster != "":
            # Set snapraster environment if  one is specified
        #    arcpy.snapRaster = theSnapRaster

        # Set output extent
        fullExtent = SnapToNLCD(inputFC, iRaster)

        # Raster conversion process...
        #
        if bTiled in ["Large", "Small"]:
            # Tiled raster process...
            #
            PrintMsg(" \n\tCreating " + Number_Format(len(tileList), 0, True) + " raster tiles from " + os.path.join(os.path.basename(os.path.dirname(inputFC)), os.path.basename(inputFC)) + " featureclass", 0)
            PrintMsg(" \n\tOutput location for raster tiles: " + tmpFolder, 0)

            # Create output folder
            arcpy.CreateFolder_management(os.path.dirname(tmpFolder), os.path.basename(tmpFolder))
            rasterList = list()
            i = 0

            # Create dictionary of extents for each tile
            theDesc = arcpy.Describe(inputSA)

            arcpy.SetProgressor("default", "Getting extents for each tile...")
            #PrintMsg(" \nGetting extents for individual tiles...", 1)
            dExtents = TiledExtents(inputSA, tileList, theDesc, iRaster, bTiled)

            for tile in tileList:
                i += 1
                #tmpPolys = "poly_" + tile
                if bTiled == "Small":
                    wc = "AREASYMBOL = '" + tile + "'"

                elif bTiled == "Large":
                    wc = "AREASYMBOL LIKE '" + tile[0:2] + "%'"

                tileRaster = os.path.join(tmpFolder, tile.lower() + ".tif")
                rasterList.append(tileRaster)
                msg = "\t\tPerforming raster conversion for '" + tile + "'  (tile " + str(i) + " of " + str(tileCnt) + ")..."
                arcpy.SetProgressor("default", msg)
                PrintMsg(msg, 0)

                # Get 'snapped raster' extent from dictionary
                if tile in dExtents:
                    env.extent = dExtents[tile]

                else:
                    raise MyError, "Missing extents for tile " + str(tile) + " in dExtents"

                arcpy.MakeFeatureLayer_management(inputFC, tmpPolys, wc)
                arcpy.AddJoin_management (tmpPolys, "MUKEY", lu, "MUKEY", "KEEP_ALL")

                # Need to make sure that the join was successful
                time.sleep(1)
                rasterFields = arcpy.ListFields(tmpPolys)
                rasterFieldNames = list()

                for rFld in rasterFields:
                    rasterFieldNames.append(rFld.name.upper())

                if not "LOOKUP.CELLVALUE" in rasterFieldNames:
                    raise MyError, "Join failed for Lookup table (CELLVALUE)"

                if (os.path.basename(inputFC) + ".SPATIALVERSION") in rasterFieldNames:
                    priorityFld = os.path.basename(inputFC) + ".SPATIALVERSION"

                else:
                    priorityFld = os.path.basename(inputFC) + ".SPATIALVER"

                # Use a priority field for tiled rasters to try and prevent NoData around edge

                #ListEnv()
                arcpy.PolygonToRaster_conversion(tmpPolys, "Lookup.CELLVALUE", tileRaster, "MAXIMUM_COMBINED_AREA", priorityFld, iRaster)  # Getting some NoData pixels

            del tileRaster
            PrintMsg(" \n\tMosaicing tiles to a single raster...", 0)
            arcpy.SetProgressorLabel("Mosaicing tiles to a single raster...")
            env.extent = fullExtent
            arcpy.MosaicToNewRaster_management (rasterList, os.path.dirname(outputRaster), os.path.basename(outputRaster), "", "32_BIT_UNSIGNED", iRaster, 1, "MAXIMUM")
            del rasterList
            # Compact the scratch geodatabase after deleting all the rasters

        else:
            # Create a single raster, no tiles
            #
            PrintMsg(" \nConverting featureclass " + os.path.join(os.path.basename(os.path.dirname(inputFC)), os.path.basename(inputFC)) + " to raster (" + str(iRaster) + " meter)", 0)
            tmpPolys = "poly_tmp"
            arcpy.MakeFeatureLayer_management (inputFC, tmpPolys)
            arcpy.AddJoin_management (tmpPolys, "MUKEY", lu, "MUKEY", "KEEP_ALL")
            arcpy.SetProgressor("default", "Running PolygonToRaster conversion...")
            env.extent = fullExtent

            # Need to make sure that the join was successful
            time.sleep(1)
            rasterFields = arcpy.ListFields(tmpPolys)
            rasterFieldNames = list()

            for rFld in rasterFields:
                rasterFieldNames.append(rFld.name.upper())

            if not "LOOKUP.CELLVALUE" in rasterFieldNames:
                raise MyError, "Join failed for Lookup table (CELLVALUE)"

            if (os.path.basename(inputFC) + ".SPATIALVERSION") in rasterFieldNames:
                #raise MyError, "Join failed for Lookup table (SPATIALVERSION)"
                priorityFld = os.path.basename(inputFC) + ".SPATIALVERSION"

            else:
                priorityFld = os.path.basename(inputFC) + ".SPATIALVER"


            #ListEnv()
            arcpy.PolygonToRaster_conversion(tmpPolys, "Lookup.CELLVALUE", outputRaster, "MAXIMUM_COMBINED_AREA", priorityFld, iRaster) # No priority field for single raster

            # immediately delete temporary polygon layer to free up memory for the rest of the process
            time.sleep(1)
            arcpy.Delete_management(tmpPolys)

            # End of single raster process


        # Now finish up the single temporary raster
        #
        PrintMsg(" \nFinalizing raster conversion process:", 0)
        # Reset the stopwatch for the raster post-processing
        #begin = time.time()

        # Remove lookup table
        if arcpy.Exists(lu):
            arcpy.Delete_management(lu)

        # ****************************************************
        # Build pyramids and statistics
        # ****************************************************
        if arcpy.Exists(outputRaster):
            time.sleep(3)
            arcpy.SetProgressor("default", "Calculating raster statistics...")
            PrintMsg("\tCalculating raster statistics...", 0)
            env.pyramid = "PYRAMIDS -1 NEAREST"
            arcpy.env.rasterStatistics = 'STATISTICS 100 100'
            arcpy.CalculateStatistics_management (outputRaster, 1, 1, "", "OVERWRITE" )

            if CheckStatistics(outputRaster) == False:
                # For some reason the BuildPyramidsandStatistics command failed to build statistics for this raster.
                #
                # Try using CalculateStatistics while setting an AOI
                PrintMsg("\tInitial attempt to create statistics failed, trying another method...", 0)
                time.sleep(3)

                if arcpy.Exists(os.path.join(theGDB, "SAPOLYGON")):
                    # Try running CalculateStatistics with an AOI to limit the area that is processed
                    # if we have to use SAPOLYGON as an AOI, this will be REALLY slow
                    #arcpy.CalculateStatistics_management (outputRaster, 1, 1, "", "OVERWRITE", os.path.join(outputWS, "SAPOLYGON") )
                    arcpy.CalculateStatistics_management (outputRaster, 1, 1, "", "OVERWRITE" )

                if CheckStatistics(outputRaster) == False:
                    time.sleep(3)
                    PrintMsg("\tFailed in both attempts to create statistics for raster layer", 1)

            arcpy.SetProgressor("default", "Building pyramids...")
            PrintMsg("\tBuilding pyramids...", 0)
            arcpy.BuildPyramids_management(outputRaster, "-1", "NONE", "NEAREST", "DEFAULT", "", "SKIP_EXISTING")

            # ****************************************************
            # Add MUKEY to final raster
            # ****************************************************
            # Build attribute table for final output raster. Sometimes it fails to automatically build.
            PrintMsg("\tBuilding raster attribute table and updating MUKEY values", )
            arcpy.SetProgressor("default", "Building raster attrribute table...")
            arcpy.BuildRasterAttributeTable_management(outputRaster)

            # Add MUKEY values to final mapunit raster
            #
            arcpy.SetProgressor("default", "Adding MUKEY attribute to raster...")
            arcpy.AddField_management(outputRaster, "MUKEY", "TEXT", "#", "#", "30")
            with arcpy.da.UpdateCursor(outputRaster, ["VALUE", "MUKEY"]) as cur:
                for rec in cur:
                    rec[1] = rec[0]
                    cur.updateRow(rec)

            # Add attribute index (MUKEY) for raster
            if rasterExt == '':
                arcpy.AddIndex_management(outputRaster, ["mukey"], "Indx_RasterMukey")

        else:
            err = "Missing output raster (" + outputRaster + ")"
            raise MyError, err

        # Compare list of original mukeys with the list of raster mukeys
        # Report discrepancies. These are usually thin polygons along survey boundaries,
        # added to facilitate a line-join.
        #
        arcpy.SetProgressor("default", "Looking for missing map units...")
        rCnt = int(arcpy.GetRasterProperties_management (outputRaster, "UNIQUEVALUECOUNT").getOutput(0))

        if rCnt <> muCnt:
            missingList = list()
            rList = list()

            # Create list of raster mukeys...
            with arcpy.da.SearchCursor(outputRaster, ("MUKEY",)) as rcur:
                for rec in rcur:
                    mukey = rec[0]
                    rList.append(mukey)

            missingList = list(set(mukeyList) - set(rList))
            queryList = list()
            
            for mukey in missingList:
                queryList.append("'" + mukey + "'")

            if len(queryList) > 0:
                PrintMsg("\tDiscrepancy in mapunit count for new raster", 1)
                #PrintMsg("\t\tInput polygon mapunits: " + Number_Format(muCnt, 0, True), 0)
                #PrintMsg("\t\tOutput raster mapunits: " + Number_Format(rCnt, 0, True), 0)
                PrintMsg("The following MUKEY values were present in the original MUPOLYGON featureclass, ", 1)
                PrintMsg("but not in the raster", 1)
                PrintMsg("\t\tMUKEY IN (" + ", ".join(queryList) + ") \n ", 0)

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
        time.sleep(2)
        arcpy.SetProgressorLabel("Updating metadata...")

        arcpy.SetProgressorLabel("Compacting database...")
        bMetaData = UpdateMetadata(theGDB, outputRaster, surveyInfo, iRaster)

        arcpy.SetProgressorLabel("Compacting database...")
        PrintMsg("\tCompacting geodatabase...", 0)
        arcpy.Compact_management(theGDB)
        arcpy.RefreshCatalog(os.path.dirname(outputRaster))

        if bTiled in ["Small", "Large"]:

            if arcpy.Exists(tmpFolder):
                PrintMsg("\tCleaning up raster tiles...", 0)
                shutil.rmtree(tmpFolder)

        #theMsg = "\tPost-processing: " + elapsedTime(begin)
        #PrintMsg(theMsg, 1)

        # Get location such as name of state for use in layer title
        theDesc = arcpy.Describe(inputFC)

        theMsg = " \nProcessing time for " + outputRaster + ": " + elapsedTime(start) + " \n "
        PrintMsg(theMsg, 0)

        del outputRaster
        del inputFC

        #WriteToLog(theMsg, theRptFile)
        arcpy.CheckInExtension("Spatial")

        return True

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return False
        arcpy.CheckInExtension("Spatial")

    except MemoryError:
    	raise MyError, "Not enough memory to process. Try running again with the 'Use tiles' option"

    except:
        errorMsg()
        return False
        arcpy.CheckInExtension("Spatial")

## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, math, time, datetime, shutil
import xml.etree.cElementTree as ET
from arcpy import env

# Create the Geoprocessor object
try:
    if __name__ == "__main__":
        # get parameters
        theGDB = arcpy.GetParameterAsText(0)                   # required geodatabase containing MUPOLYGON featureclass
        #outputWS = arcpy.GetParameterAsText(1)                # optional output workspace. If not set, output raster will be created in the same workspace
        #theSnapRaster = arcpy.GetParameterAsText(1)           # optional snap raster. If not set, uses NLCD Albers USGS NAD83 for CONUS
        iRaster = arcpy.GetParameter(1)                       # output raster resolution
        bTiled = arcpy.GetParameter(2)                                         # boolean - split raster into survey-tiles and then mosaic
        env.overwriteOutput= True

        # Get Spatial Analyst extension
        if arcpy.CheckExtension("Spatial") == "Available":
            # try to find the name of the tile from the geodatabase name
            # set the name of the output raster using the tilename and cell resolution
            from arcpy.sa import *
            arcpy.CheckOutExtension("Spatial")

        else:
            raise MyError, "Required Spatial Analyst extension is not available"

        # Call function that does all of the work
        bRaster = ConvertToRaster(theGDB, iRaster, bTiled)
        arcpy.CheckInExtension("Spatial")

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
