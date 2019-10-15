# gSSURGO_CreateSoilMapLite.py
#
# SQLite version. Testing issues involved in moving from FGDB to SQLite database.
#
# Creates a single Soil Data Viewer-type maps using gSSURGO-Lite and the sdv* attribute tables
# Uses mdstatrship* tables and sdvattribute table to populate menu
#
# 2019-03-25 Need to add index on 'mukey', at least for larger datasets. This does help with joins and views, right?
#
# 2019-03-25 Replaced functions used to create the 'sdv_data' table to sqlite3. CreateOutputTable function.

# 2019-03-15 Generated output mapunit-rating table using sqlite3. As of 03-25, these tables are not recognized by ArcGIS.
#
# 2019-02-20 Created soil map layer as an SQLite View. This seems to work even though the tables are not recognized.
#
# SQLite:  dbDesc.workspaceFactoryProgID:  u'esriDataSourcesGDB.SqlWorkspaceFactory.1'
# import sqlite3
# import arcpy
# SQLITE_FILE = r"c:\temp\example.gpkg"
# conn = sqlite3.connect(SQLITE_FILE)
# conn.execute("VACUUM")
# conn.close()
#
# --Load the ST_Geometry library on Windows.
# SELECT load_extension(
# 'c:\Program Files (x86)\ArcGIS\Desktop10.3\DatabaseSupport\SQLite\Windows32\stgeometry_sqlite.dll',
# 'SDE_SQL_funcs_init'
#);
#
# cur = conn.execute("SELECT * FROM main.legend")
# print str(cur.fetchone())
#
# da cursors also work with SQLite tables, but conn.exectute might work better for management SQL.
# Only one SQL statement at a time is allowed, unless you use: executescript()
#
# Unable to obtain IMetadata from: C:\Geodata\ArcGIS_Home\scratch\SQLite_Test1.sqlite\sdv_ClLiMatSrc_DCD
#
# THINGS TO DO:
#
# Test the input MUPOLYGON featurelayer to see how many polygons are selected when compared
# to the total in the source featureclass. If there is a significant difference, consider
# applying a query filter using areasymbol to limit the size of the master query table.
#
# 0. Need to look at WTA for Depth to Any Restrictive Layer. Customer reported problem. The
#    201 values are being used in the weighting.
#
# 1.  Aggregation method "Weighted Average" can now be used for non-class soil interpretations.
#
# 2.   "Minimum or Maximum" and its use is now restricted to numeric attributes or attributes
#   with a corresponding domain that is logically ordered.
#
# 3.  Aggregation method "Absence/Presence" was replaced with a more generalized version
# thereof, which is referred to as "Percent Present".  Up to now, aggregation method
# "Absence/Presence" was supported for one and only one attribute, component.hydricrating.
# Percent Present is a powerful new aggregation method that opens up a lot of new possibilities,
# e.g. "bedrock within two feel of the surface".
#
# 4.  The merged aggregation engine now supports two different kinds of horizon aggregation,
# "weighted average" and "weighted sum".  For the vast majority of horizon level attributes,
# "weighted average" is used.  At the current time, the only case where "weighted sum" is used is
# for Available Water Capacity, where the water holding capacity needs to be summed rather than
# averaged.

# 5.  The aggregation process now always returns two values, rather than one, the original
# aggregated result AND the percent of the map unit that shares that rating.  For example, for
# the drainage class/dominant condition example below, the rating would be "Moderately well
# drained" and the corresponding map unit percent would be 60:
#
# 6.  A horizon or layer where the attribute being aggregated is null will now never contribute
# to the final aggregated result.  There # was a case for the second version of the aggregation
# engine where this was not true.
#
# 7.  Column sdvattribute.fetchallcompsflag is no longer needed.  The new aggregation engine was
# updated to know that it needs to # include all components whenever no component percent cutoff
# is specified and the aggregation method is "Least Limiting" or "Most # Limiting" or "Minimum or Maximum".
#
# 8.  For aggregation methods "Least Limiting" and "Most Limiting", the rating will be set to "Unknown"
# if any component has a null # rating, and no component has a fully conclusive rating (0 or 1), depending
# on the type of rule (limitation or suitability) and the # corresponding aggregation method.
#

# 2015-12-17 Depth to Water Table: [Minimum or Maximum / Lower] is not swapping out NULL values for 201.
# The other aggregation methods appear to be working properly. So the minimum is returning mostly NULL
# values for the map layer when it should return 201's.

# 2015-12-17 For Most Limiting, I'm getting some questionable results. For example 'Somewhat limited'
# may get changed to 'Not rated'

# Looking at option to map fuzzy rating for all interps. This would require redirection to the
# Aggregate2_NCCPI amd CreateNumericLayer functions. Have this working, but needs more testing.
#
# 2015-12-23  Need to look more closely at my Tiebreak implementation for Interps. 'Dwellings with
# Basements (DCD, Higher) appears to be switched. Look at Delaware 'PsA' mapunit with Pepperbox-Rosedale components
# at 45% each.
#
# 2016-03-23 Fixed bad bug, skipping last mapunit in NCCPI and one other function
#
# 2016-04-19 bNulls parameter. Need to look at inclusion/exclusion of NULL rating values for Text or Choice.
# WSS seems to include NULL values for ratings such as Hydrologic Group and Flooding
#
# Interpretation columns
# interphr is the High fuzzy value, interphrc is the High rating class
# interplr is the Low fuzzy value, interplrc is the Low rating class
# Very Limited = 1.0; Somewhat limited = 0.22
#
# NCCPI maps fuzzy values by default. It appears that 1.0 would be high productivity and
# 0.01 very low productivity. Null would be Not rated.
#
# 2017-03-03 AggregateHZ_DCP_WTA - Bug fix. Was only returning surface rating for DCP. Need to let folks know about this.
#
# 2017-07-24 Depth to Water Table, DCP bug involving nullreplacementvalue and tiebreak code.
#
# 2017-08-11 Mapping interpretations using Cointerp  very slow on CONUS gSSURGO
#
# 2017-08-14 Altered Unique values legend code to skip the map symbology section for very large layers
#
# 2018-06-30 Addressed issue with some Raster maps-classified had color ramp set backwards. Added new logic and layer files.
#
# 2019-02-23 Begin alterations for SQLite
#
# Line 9604: turned off metadata
#
# 2019-03-26 sdv_data table and sdv_ rating tables are invisible to ArcGIS. Need to find a way to
# register those to the geopackage.


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

        return "???"

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
def get_random_color(pastel_factor=0.5):
    # Part of generate_random_color
    try:
        newColor = [int(255 *(x+pastel_factor)/(1.0+pastel_factor)) for x in [random.uniform(0,1.0) for i in [1,2,3]]]

        return newColor

    except:
        errorMsg()
        return [0,0,0]

## ===================================================================================
def color_distance(c1,c2):
    # Part of generate_random_color
    return sum([abs(x[0]-x[1]) for x in zip(c1,c2)])

## ===================================================================================
def generate_new_color(existing_colors, pastel_factor=0.5):
    # Part of generate_random_color
    try:
        #PrintMsg(" \nExisting colors: " + str(existing_colors) + "; PF: " + str(pastel_factor), 1)

        max_distance = None
        best_color = None

        for i in range(0,100):
            color = get_random_color(pastel_factor)


            if not color in existing_colors:
                color.append(255) # add transparency level
                return color

            best_distance = min([color_distance(color,c) for c in existing_colors])

            if not max_distance or best_distance > max_distance:
                max_distance = best_distance
                best_color = color
                best_color.append(255)

            return best_color

    except:
        errorMsg()
        return None

## ===================================================================================
def rand_rgb_colors(num):
    # Generate a random list of rgb values
    # 2nd argument in generate_new_colors is the pastel factor. 0 to 1. Higher value -> more pastel.

    try:
        colors = []
        # PrintMsg(" \nGenerating " + str(num - 1) + " new colors", 1)

        for i in range(0, num):
            newColor = generate_new_color(colors, 0.1)
            colors.append(newColor)

        # PrintMsg(" \nColors: " + str(colors), 1)

        return colors

    except:
        errorMsg()
        return []

## ===================================================================================
def polylinear_gradient(colors, n):
  ''' returns a list of colors forming linear gradients between
      all sequential pairs of colors. "n" specifies the total
      number of desired output colors '''
  # The number of colors per individual linear gradient
  n_out = int(float(n) / (len(colors) - 1))
  # returns dictionary defined by color_dict()
  gradient_dict = linear_gradient(colors[0], colors[1], n_out)

  if len(colors) > 1:
    for col in range(1, len(colors) - 1):
      next = linear_gradient(colors[col], colors[col+1], n_out)
      for k in ("hex", "r", "g", "b"):
        # Exclude first point to avoid duplicates
        gradient_dict[k] += next[k][1:]

  return gradient_dict

## ===================================================================================
def fact(n):
  ''' Memoized factorial function '''
  try:
    return fact_cache[n]

  except(KeyError):
    if n == 1 or n == 0:
      result = 1
    else:
      result = n*fact(n-1)

    fact_cache[n] = result
    return result

## ===================================================================================
def bernstein(t,n,i):
  ''' Bernstein coefficient '''
  binom = fact(n)/float(fact(i)*fact(n - i))
  return binom*((1-t)**(n-i))*(t**i)

## ===================================================================================
def bezier_gradient(colors, n_out=100):
  ''' Returns a "bezier gradient" dictionary
      using a given list of colors as control
      points. Dictionary also contains control
      colors/points. '''
  # RGB vectors for each color, use as control points
  RGB_list = [hex_to_RGB(color) for color in colors]
  n = len(RGB_list) - 1

  def bezier_interp(t):
    ''' Define an interpolation function
        for this specific curve'''
    # List of all summands
    summands = [
      map(lambda x: int(bernstein(t,n,i)*x), c)
      for i, c in enumerate(RGB_list)
    ]
    # Output color
    out = [0,0,0]
    # Add components of each summand together
    for vector in summands:
      for c in range(3):
        out[c] += vector[c]

    return out

  gradient = [
    bezier_interp(float(t)/(n_out-1))
    for t in range(n_out)
  ]
  # Return all points requested for gradient
  return {
    "gradient": color_dict(gradient),
    "control": color_dict(RGB_list)
  }

## ===================================================================================
def BadTable(tbl):
    # Make sure the table has data
    #
    # If has contains one or more records, return False (not a bad table)
    # If the table is empty, return True (bad table)

    try:
        if not arcpy.Exists(tbl):
            return True

        recCnt = int(arcpy.GetCount_management(tbl).getOutput(0))

        if recCnt > 0:
            return False

        else:
            return True

    except:
        errorMsg()
        return True

## ===================================================================================
def SortData(muVals, a, b, sortA, sortB):
    # Input muVals is a list of lists to be sorted. Each list must have contain at least two items.
    # Input 'a' is the first item index in the sort order (integer)
    # Item 'b' is the second item index in the sort order (integer)
    # Item sortA is a bookean for reverse sort
    # Item sortB is a boolean for reverse sort
    # Perform a 2-level sort by then by item i, then by item j.
    # Return a single list

    try:
        #PrintMsg(" \nmuVals: " + str(muVals), 1)

        if len(muVals) > 0:
            muVal = sorted(sorted(muVals, key = lambda x : x[b], reverse=sortB), key = lambda x : x[a], reverse=sortA)[0]

        else:
            muVal = muVals[0]

        #PrintMsg(str(muVal) + " <- " + str(muVals), 1)

        return muVal

    except:
        errorMsg()
        return (None, None)

## ===================================================================================
def ColorRamp(dLabels, lowerColor, upperColor):
    # For Progressive color ramps, there are no colors defined for each legend item.
    # Create a dictionary of colors based upon the upper and lower colors.
    # Key value is 'part' which is the number of colors used to define the color ramp.
    #
    # count is always equal to three and part is always zero-based
    #
    # upper and lower Color are dictionaries (keys: 0, 1, 2) with RGB tuples as values
    # Will only handle base RGB color
    # dColors = ColorRamp(dLegend["count"], len(dLabels), dLegend["LowerColor"], dLegend["UpperColor"])

    try:
        import BezierColorRamp

        labelCnt = len(dLabels)
        #PrintMsg(" \nCreating color ramp based upon " + str(labelCnt) + " legend items", 1)

        dColorID = dict()
        dRGB = dict()

        # Use dColorID to identify the Lower and Upper Colors
        dColorID[(255,0,0)] = "Red"
        dColorID[(255,255,0)] = "Yellow"
        dColorID[(0,255,0)] ="Green"  # not being used in slope color ramp
        dColorID[(0,255,255)] = "Cyan"
        dColorID[(0,0,255)] = "Blue"
        dColorID[(255,0,255)] = "Magenta"   # not being used in slope color ramp

        dRGB["red"] = (255, 0, 0)
        dRGB["yellow"] = (255, 255, 0)
        dRGB["green"] = (0, 255, 0)
        dRGB["cyan"] = (0, 255, 255)
        dRGB["blue"] = (0, 0, 255)
        dRGB["magenta"] = (255, 0, 255)


        #PrintMsg(" \nLowerColor: " + str(lowerColor), 1)
        #PrintMsg("UpperColor: " + str(upperColor) + " \n ", 1)

        dBaseColors = dict()  # basic RGB color ramp as defined by lower and upper colors
        colorList = list()
        dColors = dict()

        j = -1
        lastclr = (-1,-1,-1)

        for i in range(len(lowerColor)):

            clr = lowerColor[i]
            if clr != lastclr:
                j += 1
                dBaseColors[j] = clr
                #PrintMsg("\t" + str(j) + ". " + dColorID[clr], 1)
                colorList.append(dColorID[clr])
                lastclr = clr

            clr = upperColor[i]
            if clr != lastclr:
                j += 1
                dBaseColors[j] = clr
                #PrintMsg("\t" + str(j) + ". " + dColorID[clr], 1)
                colorList.append(dColorID[clr])
                lastclr = clr

        newColors = BezierColorRamp.Process(labelCnt, colorList)

        for i in range(len(newColors)):
            dColors[i + 1] = {"red" : newColors[i][0], "green": newColors[i][1], "blue" : newColors[i][2]}

        #PrintMsg(" \ndColors: " + str(dColors), 1)

        return dColors

    except:
        errorMsg()
        return {}

## ===================================================================================
def GetMapLegend(dAtts, bFuzzy):
    # Get map legend values and order from maplegendxml column in sdvattribute table
    # Return dLegend dictionary containing contents of XML.

    # Problem with Farmland Classification. It is defined as a choice, but

    try:
        #bVerbose = True  # This function seems to work well, but prints a lot of messages.
        global dLegend
        dLegend = dict()
        dLabels = dict()

        #if bFuzzy and not dAtts["attributename"].startswith("National Commodity Crop Productivity Index"):
        #    # Skip map legend because the fuzzy values will not match the XML legend.
        #    return dict()

        arcpy.SetProgressorLabel("Getting map legend information")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        xmlString = dAtts["maplegendxml"]

        #if bVerbose:
        #    PrintMsg(" \nxmlString: " + xmlString + " \n ", 1)

        # Convert XML to tree format
        tree = ET.fromstring(xmlString)

        # Iterate through XML tree, finding required elements...
        i = 0
        dColors = dict()
        legendList = list()
        legendKey = ""
        legendType = ""
        legendName = ""

        # Notes: dictionary items will vary according to legend type
        # Looks like order should be dictionary key for at least the labels section
        #
        for rec in tree.iter():

            if rec.tag == "Map_Legend":
                dLegend["maplegendkey"] = rec.attrib["maplegendkey"]

            if rec.tag == "ColorRampType":
                dLegend["type"] = rec.attrib["type"]
                dLegend["name"] = rec.attrib["name"]

                if rec.attrib["name"] == "Progressive":
                    dLegend["count"] = int(rec.attrib["count"])

            if "name" in dLegend and dLegend["name"] == "Progressive":

                if rec.tag == "LowerColor":
                    # 'part' is zero-based and related to count
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Lower Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)

                if rec.tag == "UpperColor":
                    part = int(rec.attrib["part"])
                    red = int(rec.attrib["red"])
                    green = int(rec.attrib["green"])
                    blue = int(rec.attrib["blue"])
                    #PrintMsg("Upper Color part #" + str(part) + ": " + str(red) + ", " + str(green) + ", " + str(blue), 1)

                    if rec.tag in dLegend:
                        dLegend[rec.tag][part] = (red, green, blue)

                    else:
                        dLegend[rec.tag] = dict()
                        dLegend[rec.tag][part] = (red, green, blue)


            if rec.tag == "Labels":
                order = int(rec.attrib["order"])

                if dSDV["attributelogicaldatatype"].lower() == "integer":
                    # get dictionary values and convert values to integer
                    try:
                        val = int(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = int(rec.attrib["upper_value"])
                        lowerVal = int(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                elif dSDV["attributelogicaldatatype"].lower() == "float" and not bFuzzy:
                    # get dictionary values and convert values to float
                    try:
                        val = float(rec.attrib["value"])
                        label = rec.attrib["label"]
                        rec.attrib["value"] = val
                        dLabels[order] = rec.attrib

                    except:
                        upperVal = float(rec.attrib["upper_value"])
                        lowerVal = float(rec.attrib["lower_value"])
                        rec.attrib["upper_value"] = upperVal
                        rec.attrib["lower_value"] = lowerVal
                        dLabels[order] = rec.attrib

                else:
                    dLabels[order] = rec.attrib   # for each label, save dictionary of values

            if rec.tag == "Color":
                # Save RGB Colors for each legend item

                # get dictionary values and convert values to integer
                red = int(rec.attrib["red"])
                green = int(rec.attrib["green"])
                blue = int(rec.attrib["blue"])
                dColors[order] = rec.attrib

            if rec.tag == "Legend_Elements":
                try:
                    dLegend["classes"] = rec.attrib["classes"]   # save number of classes (also is a dSDV value)

                except:
                    pass

        # Add the labels dictionary to the legend dictionary
        dLegend["labels"] = dLabels
        dLegend["colors"] = dColors

        # Test iteration methods on dLegend
        #PrintMsg(" \n" + dAtts["attributename"] + " Legend Key: " + dLegend["maplegendkey"] + ", Type: " + dLegend["type"] + ", Name: " + dLegend["name"] , 1)

        if bVerbose:
            PrintMsg(" \n" + dAtts["attributename"] + "; MapLegendKey: " + dLegend["maplegendkey"] + ",; Type: " + dLegend["type"] , 1)

            for order, vals in dLabels.items():
                PrintMsg("\tNew " + str(order) + ": ", 1)

                for key, val in vals.items():
                    PrintMsg("\t\t" + key + ": " + str(val), 1)

                try:
                    r = int(dColors[order]["red"])
                    g = int(dColors[order]["green"])
                    b = int(dColors[order]["blue"])
                    rgb = (r,g,b)
                    #PrintMsg("\t\tRGB: " + str(rgb), 1)

                except:
                    pass

        if bVerbose:
            PrintMsg(" \ndLegend: " + str(dLegend), 1)

        return dLegend

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def CreateJSONLegend(dLegend, outputTbl, outputValues, ratingField, sdvAtt, bFuzzy):
    # This does not work for classes that have a lower_value and upper_value
    #
    try:
        # Input dictionary 'dLegend' contains two other dictionaries:
        #   dLabels[order]
        #    dump sorted dictionary contents into output table

        arcpy.SetProgressorLabel("Creating JSON map legend")
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

            if ratingField.startswith("interp"):
                # Here are examples of the rating classes for the new Forestry Interps. Use these to test and create new
                # dLegend[name], dSDV[maplegendkey], dLegend[type] and dLegend[labels]

                # [[Slight, Moderate, Severe, Not rated], [Low, Medium, High, Not rated], [Well suited, Moderately suited, Poorly suited, Not suited, Not rated]]
                PrintMsg(" \nThis is an unpublished interpretation layer. Need to create custom legend", 1)

            else:
                PrintMsg(" \nRating field: " + ratingField, 1)
                PrintMsg(str(dLegend), 1)

        # New code to handle unpublished interps that have no xmlmaplegend information
        #
        if ratingField.startswith("interp") and dSDV["attributetype"] == "Interpretation":
            # see if the outputValues match any of the new Forestry Interps
            # For other unpublished interps that have a different set of rating classes,
            # the following dInterps dictionary will have to be modified.
            #
            # I still need to populate the map legend colors. Perhaps use the length of the selected dInterps list?
            #
            bTested = TestLegends(outputValues)

            if bTested == False:
                PrintMsg(" \nFailed to find matching legend for unpublished interp", 1)

        if dLegend is None or len(dLegend) == 0:
            raise MyError, "xxx No Legend"

        if bVerbose:
            PrintMsg(" \ndLegend name: " + dLegend["name"] + ", type: " + str(dLegend["type"]), 1)
            PrintMsg("Effectivelogicaldatatype: " + dSDV["effectivelogicaldatatype"].lower(), 1)
            PrintMsg("Maplegendkey: " + str(dSDV["maplegendkey"]), 1)
            PrintMsg("dLegend labels: " + str(dLegend["labels"]), 1)
            PrintMsg("Output Values: " + str(outputValues), 1)
            PrintMsg(" \nNumber of outputValues: " + str(len(outputValues)) + " and number of dLegend labels: " + str(len(dLegend["labels"])), 1)

        bBadLegend = False

        if len(dLegend["labels"]) > 0 and dSDV["effectivelogicaldatatype"].lower() == "choice":
            # To address problem with Farmland Class where map legend values do not match actual data values, let's
            # try comparing the two.
            legendLabels = list()
            missingValues = list()
            badLabels = list()

            for labelIndx, labelItem in dLegend["labels"].items():
                legendLabels.append(labelItem["value"])

            for outputValue in outputValues:
                if not outputValue in legendLabels:
                    #PrintMsg("\tMissing data value (" + outputValue + ") in maplegendxml", 1)
                    bBadLegend = True
                    missingValues.append(outputValue)

            for legendLabel in legendLabels:
                if not legendLabel in outputValues:
                    #PrintMsg("\tLegend label not present in data (" + legendLabel + ")", 1)
                    bBadLegend = True
                    badLabels.append(legendLabel)

        legendList = list()  # Causing 'No data available for' error

        # Let's try checking the map information. If Random colors and nothing is set for map legend info,
        # bailout and let the next function handle this layer


    
        
        if dLegend["name"] == "Random" and len(dLegend["colors"]) == 0 and len(dLegend["labels"]) == 0:
            # If Random colors and nothing is set for map legend info,
            # bailout and let the next function handle this layer
            #PrintMsg(" \n\tNo map legend information available", 1)
            return dict()

        if dLegend["name"] == "Progressive":
            #PrintMsg(" \nLegend name: " + dLegend["name"] + " for " + sdvAtt, 1)

            if dSDV["maplegendkey"] in [3] and dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string', 'vtext', 'narrative text']:
                # This would be for text values using Progressive color ramp
                #
                legendList = list()

                numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                if len(numItems) == 0:
                    raise MyError, "dLegend has no color information"

                for item in numItems:
                    #PrintMsg("\t" + str(item), 1)

                    try:
                        # PrintMsg("Getting legend info for legend item #" + str(item), 1)
                        rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                        rgb = [int(c) for c in rgb]
                        rating = dLegend["labels"][item]["value"]
                        legendLabel = dLegend["labels"][item]["label"]
                        legendList.append([rating, legendLabel, rgb])
                        PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                    except:
                        errorMsg()

            elif dSDV["maplegendkey"] in [3, 7] and dSDV["effectivelogicaldatatype"].lower() in ["float", "integer", "choice"]:  #
                #PrintMsg(" \nCheck Maplegendkey for 7: " + str(dSDV["maplegendkey"]), 1)

                if "labels" in dLegend and len(dLegend["labels"]) > 0:
                    # Progressive color ramp for numeric values

                    # Get the upper and lower colors
                    upperColor = dLegend["UpperColor"]
                    lowerColor = dLegend["LowerColor"]

                    if outputValues and dSDV["effectivelogicaldatatype"].lower() == "choice":
                        # Create uppercase version of outputValues
                        dUpper = dict()
                        for val in outputValues:
                            dUpper[str(val).upper()] = val

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)

                    # For NCCPI with maplegendkey = 3 and type = 1, labels is an ordered list of label numbers
                    labels = sorted(dLegend["labels"])  # returns a sorted list of legend items

                    valueList = list()

                    if dLegend["type"] != "1":   # Not NCCPI

                        for item in labels:
                            try:
                                #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                                rating = dLegend["labels"][item]["value"]
                                legendLabel = dLegend["labels"][item]["label"]

                                if not rating in outputValues and rating.upper() in dUpper:
                                    # if the legend contains a value that has a case mismatch, update the
                                    # legend to match what is in outputValues
                                    #PrintMsg(" \nUpdating legend value for " + rating, 1)
                                    rating = dUpper[rating.upper()]
                                    legendLabel = rating
                                    dLegend["labels"][item]["label"] = rating
                                    dLegend["labels"][item]["value"] = rating

                                legendList.append([rating, legendLabel])
                                #PrintMsg("Getting legend value for legend item #" + str(item) + ": " + str(rating), 1)

                                if not rating in valueList:
                                    valueList.append(rating)

                            except:
                                errorMsg()

                    elif dLegend["type"] == "1": # This is NCCPI v3 or NirrCapClass?? Looks like this would overwrite the NCCPI legend labels??


                        for item in labels:
                            try:
                                rating = dLegend["labels"][item]["value"]
                                legendLabel = dLegend["labels"][item]["label"]

                                if not rating in outputValues and rating.upper() in dUpper:
                                    # if the legend contains a value that has a case mismatch, update the
                                    # legend to match what is in outputValues
                                    #PrintMsg(" \nUpdating legend value for " + rating, 1)
                                    rating = dUpper[rating.upper()]
                                    legendLabel = rating
                                    dLegend["labels"][item]["label"] = rating
                                    dLegend["labels"][item]["value"] = rating

                                legendList.append([rating, legendLabel])
                                #PrintMsg("Getting legend value for legend item #" + str(item) + ": " + str(rating), 1)

                                if not rating in valueList:
                                    valueList.append(rating)

                            except:
                                errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No value data for " + sdvAtt

                    else:
                        dColors = ColorRamp(dLegend["labels"], lowerColor, upperColor)

                    # Open legendList back up and add rgb colors
                    #PrintMsg(" \ndColors" + str(dColors) + " \n ", 1)

                    for cnt, clr in dColors.items():
                        rgb = [clr["red"], clr["green"], clr["blue"], 255]
                        rbg = [int(c) for c in rgb]
                        item = legendList[cnt - 1]
                        #item = legendList[cnt - 1]
                        item.append(rgb)
                        #PrintMsg(str(cnt) + ". '" + str(item) + "'", 0)
                        legendList[cnt - 1] = item
                        #PrintMsg(str(cnt) + ". '" + str(item) + "'", 1)


            elif dSDV["maplegendkey"] in [6]:
                #
                if "labels" in dLegend:
                    # This legend defines a number of labels with upper and lower values, along
                    # with an UpperColor and a LowerColor ramp.
                    # examples: component slope_r, depth to restrictive layer
                    # Use the ColorRamp function to create the correct number of progressive colors
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    #PrintMsg(" \ndLegend: " + str(dLegend), 1)
                    numItems = len(dLegend["labels"]) # returns a sorted list of legend item numbers. Fails for NCCPI v2

                    # 'LowerColor': {0: (255, 0, 0), 1: (255, 255, 0), 2: (0, 255, 255)}
                    lowerColor = dLegend["LowerColor"]
                    upperColor = dLegend["UpperColor"]

                    valueList = list()
                    dLegend["colors"] = ColorRamp(dLegend["labels"], lowerColor, upperColor)
                    #PrintMsg(" \ndLegend colors: " + str(dLegend["colors"]), 1)

                    if dLegend is None or len(dLegend["colors"]) == 0:
                        raise MyError, "xxx No Legend"

                    for item in range(1, numItems + 1):
                        try:
                            #PrintMsg("Getting legend info for legend item #"  + str(item) + ": " + str(dLegend["colors"][item]), 1)
                            #rgb = dLegend["colors"][item]
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rgb = [int(c) for c in rgb]
                            maxRating = dLegend["labels"][item]['upper_value']
                            minRating = dLegend["labels"][item]['lower_value']
                            valueList.append(dLegend["labels"][item]['upper_value'])
                            valueList.append(dLegend["labels"][item]['lower_value'])

                            #rating = dLegend["labels"][item]["value"]
                            if item == 1 and dSDV["attributeuomabbrev"] is not None:
                                legendLabel = dLegend["labels"][item]["label"] + " " + str(dSDV["attributeuomabbrev"])

                            else:
                                legendLabel = dLegend["labels"][item]["label"]

                            legendList.append([minRating, maxRating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(minRating) + "',  '" + str(maxRating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No data"

                    minValue = min(valueList)

                else:
                    # no "labels" in dLegend
                    # NCCPI version 2
                    # Legend Name:Progressive Type 1 MapLegendKey 6, float
                    #
                    PrintMsg(" \nThis section is designed to handle NCCPI version 2.0. No labels for the map legend", 1)
                    legendList = []



            else:
                # Maplegendkey test
                # Logic not defined for this type of map legend
                #
                raise MyError, "Problem creating legendList for: " + dLegend["name"] + "; maplegendkey " +  str(dSDV["maplegendkey"])  # Added the 3 to test for NCCPI. That did not help.


        elif dLegend["name"] == "Defined":
            #PrintMsg(" \nLegend name: " + dLegend["name"] + " for " + sdvAtt, 1)

            if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:  # works for Hydric (Defined, integer with maplegendkey=1)

                if dSDV["maplegendkey"] == 1:
                    # Hydric,
                    #PrintMsg(" \ndLegend for Defined, " + dSDV["effectivelogicaldatatype"].lower() + ", maplegendkey=" + str(dSDV["maplegendkey"]) + ": \n" + str(dLegend), 1)
                    # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers
                    valueList = list()

                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rgb = [int(c) for c in rgb]
                            maxRating = dLegend["labels"][item]['upper_value']
                            minRating = dLegend["labels"][item]['lower_value']
                            valueList.append(dLegend["labels"][item]['upper_value'])
                            valueList.append(dLegend["labels"][item]['lower_value'])

                            #rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]
                            legendList.append([minRating, maxRating, legendLabel, rgb])

                            #PrintMsg(str(item) + ". '" + str(minRating) + "',  '" + str(maxRating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()

                    if len(valueList) == 0:
                        raise MyError, "No data"
                    minValue = min(valueList)

                else:
                    # integer values
                    #
                    #PrintMsg(" \ndLegend for Defined, " + dSDV["effectivelogicaldatatype"].lower() + ", maplegendkey=" + str(dSDV["maplegendkey"]) + ": \n" + str(dLegend), 1)

                    # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                    # 4. Assemble all required legend information into a single, ordered list
                    legendList = list()
                    #PrintMsg(" \ndRatings: " + str(dRatings), 1)
                    numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]
                            legendList.append([rating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()


            elif dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string', 'vtext']:
                # This would include some of the interps
                #Defined, 2, choice
                # PrintMsg(" \n \ndLegend['colors']: " + str(dLegend["colors"]) + " \n ", 1)
                # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

                # 4. Assemble all required legend information into a single, ordered list
                #PrintMsg(" \nbBadLegend: " + str(bBadLegend) + " \n ", 1)

                legendList = list()
                numItems = sorted(dLegend["colors"])  # returns a sorted list of legend item numbers

                if bBadLegend:
                    # Problem with maplegend not matching data. Try replacing original labels and values.

                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]

                            # missingValues contains data values not in legend
                            # badLabels contains legend values not in data

                            if rating in outputValues:
                                # This one is good
                                legendList.append([rating, legendLabel, rgb])
                                #PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                            else:
                                # This is a badLabel. Replace it with one of the missingValues.
                                if len(missingValues) > 0:
                                    rating = missingValues.pop(0)
                                    legendLabel = rating
                                    legendList.append([rating, legendLabel, rgb])

                        except:
                            errorMsg()

                    #if len(missingValues) > 0:
                    #    PrintMsg("\tFailed to add these data values to the map legend: " + "; ".join(missingValues), 1)

                else:
                    # Maplegendxml is OK. Use legend as is.
                    for item in numItems:
                        try:
                            #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                            rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                            rating = dLegend["labels"][item]["value"]
                            legendLabel = dLegend["labels"][item]["label"]
                            legendList.append([rating, legendLabel, rgb])
                            #PrintMsg(str(item) + ". '" + str(rating) + "',  '" + str(legendLabel) + "'", 1)

                        except:
                            errorMsg()


            else:
                raise MyError, "Problem creating legendList 3 for those parameters"

        elif dLegend["name"] == "Random":
            # This is where I would need to determine whether labels exist. If they do
            # I need to assign random color to each legend item
            #
            #
            # This one has no colors predefined
            # Defined, 2, choice
            #PrintMsg(" \ndLegend name is 'Random'", 1)

            # {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '50', 'green': '204', 'red': '50'}, 3: {'blue': '154', 'green': '250', 'red': '0'}, 4: {'blue': '0', 'green': '255', 'red': '127'}, 5: {'blue': '0', 'green': '255', 'red': '255'}, 6: {'blue': '0', 'green': '215', 'red': '255'}, 7: {'blue': '42', 'green': '42', 'red': '165'}, 8: {'blue': '113', 'green': '189', 'red': '183'}, 9: {'blue': '185', 'green': '218', 'red': '255'}, 10: {'blue': '170', 'green': '178', 'red': '32'}, 11: {'blue': '139', 'green': '139', 'red': '0'}, 12: {'blue': '255', 'green': '255', 'red': '0'}, 13: {'blue': '180', 'green': '130', 'red': '70'}, 14: {'blue': '255', 'green': '191', 'red': '0'}}

            if len(dLegend["labels"]) > 0 and len(dLegend["colors"]) == 0:
                # Same as dLegend["type"] == "0": ????
                # 4. Assemble all required legend information into a single, ordered list
                # Capability Subclass dLegend:
                # dLegend: {'colors': {}, 'labels': {1: {'order': '1', 'value': 'e', 'label': 'Erosion'}, 2: {'order': '2', 'value': 's', 'label': 'Soil limitation within the rooting zone'}, 3: {'order': '3', 'value': 'w', 'label': 'Excess water'}, 4: {'order': '4', 'value': 'c', 'label': 'Climate condition'}}, 'type': '0', 'name': 'Random', 'maplegendkey': '8'}
                #
                legendList = list()
                labels = dLegend["labels"]  # returns a dictionary of label information
                numItems = len(labels) + 1
                rgbColors = rand_rgb_colors(numItems)
                #numItems += 1

                for i in range(1, numItems):
                    try:
                        #PrintMsg("Getting legend info for legend item #" + str(item), 1)
                        #
                        # Either this next line needs to get a random color or I need to generate a list of random colors for n-labels
                        #rgb = [dLegend["colors"][item]["red"], dLegend["colors"][item]["green"], dLegend["colors"][item]["blue"], 255]
                        rgb = rgbColors[i]
                        rating = dLegend["labels"][i]["value"]
                        legendLabel = dLegend["labels"][i]["label"]
                        legendList.append([rating, legendLabel, rgb])
                        #PrintMsg(str(i) + ". '" + str(rating) + "',  '" + str(legendLabel) + "',   rgb: " + str(rgb), 1)

                    except:
                        errorMsg()

        else:
            # Logic not defined for this type of map legend
            raise MyError, "Problem creating legendList2 for those parameters"

        # Not sure what is going on here, but legendList is not right at all for ConsTreeShrub
        #

        # 5. Create layer definition using JSON string

        # Let's try maplegendkey as the driver...
        #PrintMsg(" \n\nUsing maplegendkey to control flow for symbology", 1)
        
        if dSDV["maplegendkey"] in [1,2,4,5,6,7,8] and len(legendList) == 0:
            PrintMsg("\tNo data available for " + sdvAtt + " \n ", 1)
            #raise MyError, "\tNo data available for " + sdvAtt + " \n "
            raise MyError, "xxx legendList is empty"

        if dSDV["maplegendkey"] in [1]:
            # Integer: only Hydric
            # Can I get Salinity Risk into DefinedBreaksJSON?
            #
            #PrintMsg(" \nGetting Defined Class Breaks as JSON", 1)
            # Missing minValue at this point
            dLayerDef = DefinedBreaksJSON(legendList, minValue, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [2]:
            # Choice, Integer: Farmland class, TFactor, Corrosion Steel
            #PrintMsg(" \nProblem 1 getting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)
            #PrintMsg(" \nProblem 2 getting Unique Values legend as JSON", 1)

        elif dSDV["maplegendkey"] in [3]:
            # Float, Integer: numeric soil properties
            #PrintMsg(" \nGetting numeric Class Breaks legend as JSON", 1)
            dLayerDef = ClassBreaksJSON(os.path.basename(outputTbl), outputValues, ratingField, bFuzzy)

        elif dSDV["maplegendkey"] in [4]:
            # VText, String: Unique Values
            #PrintMsg(" \nGetting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [5]:
            # String: Interp rating classes
            #PrintMsg(" \nGetting Unique Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [6]:
            # Float, Integer: pH, Slope, Depth To...
            #PrintMsg(" \nGetting Defined Class Breaks as JSON", 1)
            # Missing minValue at this point
            #

            #
            if "labels" in dLegend:
                dLayerDef = DefinedBreaksJSON(legendList, minValue, os.path.basename(outputTbl), ratingField)

            else:
                dLayerDef = ClassBreaksJSON(os.path.basename(outputTbl), outputValues, ratingField, bFuzzy)

        elif dSDV["maplegendkey"] in [7]:
            # Choice: Capability Class, WEI, Drainage class
            #PrintMsg(" \nGetting Unique 'Choice' Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        elif dSDV["maplegendkey"] in [8]:
            # Random: AASHTO, HSG, NonIrr Subclass
            #PrintMsg(" \nGetting Unique 'Choice' Values legend as JSON", 1)
            dLayerDef = UniqueValuesJSON(legendList, os.path.basename(outputTbl), ratingField)

        else:
            PrintMsg(" \nCreating dLayerDefinition for " + dLegend["name"] + ", " + str(dSDV["maplegendkey"]) + ", " + dSDV["effectivelogicaldatatype"].lower(), 1)

        return dLayerDef

    except MyError, e:
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def TestLegends(outputValues):
    # Use to match unpublished interp output values with one of the existing map legend type
    # so that symbology can be defined for the new map layer

    try:

        dTests = dict()
        dTests["limitation1"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Very limited', 'label': 'Very limited'}, 2: {'order': '2', 'value': 'Somewhat limited', 'label': 'Somewhat limited'}, 3: {'order': '3', 'value': 'Not limited', 'label': 'Not limited'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["limitation2"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '170', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}, 4: {'blue': '115', 'green': '178', 'red': '115'}}, 'labels': {1: {'order': '1', 'value': 'Very Severe', 'label': 'Very Severe'}, 2: {'order': '2', 'value': 'Severe', 'label': 'Severe'}, 3: {'order': '3', 'value': 'Moderate', 'label': 'Moderate'}, 4: {'order': '4', 'value': 'Slight', 'label': 'Slight'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["suitability3"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '255'}}, 'labels': {1: {'order': '1', 'value': 'Poorly suited', 'label': 'Poorly suited'}, 2: {'order': '2', 'value': 'Moderately suited', 'label': 'Moderately suited'}, 3: {'order': '3', 'value': 'Well suited', 'label': 'Well suited'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["suitability4"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Unsuited', 'label': 'Unsuited'}, 2: {'order': '2', 'value': 'Poorly suited', 'label': 'Poorly suited'}, 3: {'order': '3', 'value': 'Moderately suited', 'label': 'Moderately suited'}, 4: {'order': '4', 'value': 'Well suited', 'label': 'Well suited'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["susceptibility"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Highly susceptible', 'label': 'Highly susceptible'}, 2: {'order': '2', 'value': 'Moderately susceptible', 'label': 'Moderately susceptible'}, 3: {'order': '3', 'value': 'Slightly susceptible', 'label': 'Slightly susceptible'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["penetration"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '85', 'red': '255'}, 3: {'blue': '0', 'green': '170', 'red': '255'}, 4: {'blue': '0', 'green': '255', 'red': '255'}, 5: {'blue': '0', 'green': '255', 'red': '169'}, 6: {'blue': '0', 'green': '255', 'red': '84'}, 7: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Unsuited', 'label': 'Unsuited'}, 2: {'order': '2', 'value': 'Very low penetration', 'label': 'Very low penetration'}, 3: {'order': '3', 'value': 'Low penetration', 'label': 'Low penetration'}, 4: {'order': '4', 'value': 'Moderate penetration', 'label': 'Moderate penetration'}, 5: {'order': '5', 'value': 'High penetration', 'label': 'High penetration'}, 6: {'order': '6', 'value': 'Very high penetration', 'label': 'Very high penetration'}, 7: {'order': '7', 'value': 'Very high penetration', 'label': 'Very high penetration'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["excellent"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '170', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '169'}, 4: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Poor', 'label': 'Poor'}, 2: {'order': '2', 'value': 'Fair', 'label': 'Fair'}, 3: {'order': '3', 'value': 'Good', 'label': 'Good'}, 4: {'order': '4', 'value': 'Excellent', 'label': 'Excellent'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["risk1"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'Severe', 'label': 'Severe'}, 2: {'order': '2', 'value': 'Moderate', 'label': 'Moderate'}, 3: {'order': '3', 'value': 'Slight', 'label': 'Slight'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}
        dTests["risk2"] = {'colors': {1: {'blue': '0', 'green': '0', 'red': '255'}, 2: {'blue': '0', 'green': '255', 'red': '255'}, 3: {'blue': '0', 'green': '255', 'red': '0'}}, 'labels': {1: {'order': '1', 'value': 'High', 'label': 'High'}, 2: {'order': '2', 'value': 'Medium', 'label': 'Medium'}, 3: {'order': '3', 'value': 'Low', 'label': 'Low'}}, 'type': '2', 'name': 'Defined', 'maplegendkey': '5'}

        for legendType, dTest in dTests.items():
            # get labels
            dLabels = dTest["labels"]
            legendValues = list()

            for order, vals in dLabels.items():
                val = vals["value"]
                legendValues.append(val)

            bMatched = True

            for val in outputValues:
                if not val in legendValues and not val.upper() == "NOT RATED" and not val is None:
                    bMatched = False

            if bMatched == True:
                #PrintMsg(" \nFound matching legend for unpublished interp: " + legendType, 1)
                dLegend["colors"] = dTest["colors"]
                dLegend["labels"] = dTest["labels"]
                dLegend["name"] = "Defined"
                dLegend["type"] = '2'
                dLegend["maplegendkey"] = '5'
                dSDV["maplegendkey"] = 5

                #PrintMsg(" \n" + str(dLegend), 1)
                break

            #else:
            #    PrintMsg(" \nNOT a matching legend for unpublished interp: " + legendType, 1)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()


## ===================================================================================
def ClassBreaksJSON(outputTbl, outputValues, ratingField, bFuzzy):
    # returns JSON string for classified break values template.
    # Use this for numeric data with Progressive legend name and maplegendkey = 3
    # I believe the color ramps are always for 5 classes: red, orange, light green, light blue, dark blue.
    # Red         255,0,0
    # Orange      255,200,0
    # Light Green 182,255,143
    # Light Blue  51,194,255
    # Blue        0,0,255
    #
    # Interesting note; ArcMap legend created with this code DOES display the field Name in the TOC. This is not
    # true for Unique Values legends. The qualified field name is a property of ["drawingInfo"]["renderer"]["field"]
    #
    # Need to handle better no data or outputValues only has one value.


    # need to set:
    # d.minValue as a number
    # d.classBreakInfos which is a list containing at least two slightly different dictionaries.
    # The last one contains an additional classMinValue item
    #
    # d.classBreakInfos[0]:
    #    classMaxValue: 1000
    #    symbol: {u'color': [236, 252, 204, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 10 to 1000
    #    label: 10.0 - 1000.000000

    # d.classBreakInfos[n - 1]:  # where n = number of breaks
    #    classMaxValue: 10000
    #    classMinValue: 8000
    #    symbol: {u'color': [255, 255, 0, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 1000 to 5000
    #    label: 8000.000001 - 10000.000000
    #
    # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges

    # RGB colors:
    # 255, 0, 0 = red
    # 255, 255, 0 = yellow
    # 0, 255, 0 = green
    # 0, 255, 255 = cyan
    # 0, 0, 255 = blue

    try:
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        drawOutlines = False

        # Set outline symbology
        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        # define legend colors
        #

        # Try getting the matching interphr for the first ratingclass label in the maplegendxml
        # PrintMsg(" \nTrying to get legend xml information: " + str(dLegend), 1)
        interphr = 1.0    # default value
        firstClass = ""  # default value for first rating class value in map legend
        lastClass = ""

        #if bFuzzy:
        if bFuzzy and len(dLegend["labels"]) > 0:
            firstClass = dLegend['labels'][1]['value']  # first legend value, usually the 'poor' one
            #PrintMsg(" \n" + str(dLegend['labels']), 1)
            lastClass = dLegend['labels'][len(dLegend['labels'])]['value']
            # New code using rulekey and distinterpmd table
            distinterpTbl = os.path.join(gdb, "distinterpmd")
            ruleKey = GetRuleKey(distinterpTbl, dSDV["nasisrulename"])

            # sqlClause = ('TOP 1', None)  # OOPS. 'TOP' is only supported with SQL Server, MS Access databases
            whereClause = "rulekey IN " + ruleKey + " AND interphrc = '" + firstClass + "'"
            cointerpTbl = os.path.join(gdb, "cointerp")

            PrintMsg(" \nWhy am I getting fuzzy values from " + cointerpTbl + " in this manner. Do I need to add TOP 1 and ORDER BY back in for SQLite???????", 1)

            with arcpy.da.SearchCursor(cointerpTbl, ["interphr"], where_clause=whereClause) as cur:
                for rec in cur:
                    interphr = rec[0]
                    break

                #PrintMsg(" \nInterp rating poor: " + str(interphr), 1)

            # check interphr (fuzzy value) for the 'poorest' rating. Default to a value of 1.0

        if interphr == 0:
            # Use standard legend order
            dColors = dict()
            dColors[0] = [255,0,0,255]
            dColors[1] = [255,255,0,255]
            dColors[2] = [0,255,0,255]
            dColors[3] = [0,255,255,255]
            dColors[4] = [0,0,255,255]

        elif interphr == 1 and len(dLegend["labels"]) > 0:
            #PrintMsg("\tSwitching color order for Suitability", 1)
            #PrintMsg(str(dLegend), 1)

            # Soil interpretation that displays limitations. Use red for zero.
            lastClass = dLegend['labels'][1]['value']
            firstClass = dLegend['labels'][len(dLegend['labels'])]['value']
            dColors = dict()
            dColors[4] = [255,0,0,255]
            dColors[3] = [255,255,0,255]
            dColors[2] = [0,255,0,255]
            dColors[1] = [0,255,255,255]
            dColors[0] = [0,0,255,255]

        else:
            # Standard legend
            dColors = dict()
            dColors[0] = [255,0,0,255]
            dColors[1] = [255,255,0,255]
            dColors[2] = [0,255,0,255]
            dColors[3] = [0,255,255,255]
            dColors[4] = [0,0,255,255]

        dOutline = dict()
        dOutline["type"] = "esriSLS"
        dOutline["style"] = "esriSLSSolid"
        dOutline["color"] = outLineColor
        dOutline["width"] = 0.4

        #
        if len(set(outputValues)) == 1:
            classNum = 1

        else:
            classNum = 5

        #PrintMsg(" \noutputValues: " + str(outputValues), 1)
        p = dSDV["attributeprecision"]
        #PrintMsg(" \nattributeprecision: " + str(p) + ";   and units of measure: " + str(dSDV["attributeuomabbrev"]), 1)
       # PrintMsg(" \noutputValues: " + str(outputValues), 1)

        if p is None:
            maxValue = max(outputValues)
            minValue = min(outputValues)
            low = min(outputValues)
            step = int(round(((maxValue - minValue) / float(min(  len(outputValues), classNum) )), 1))
            #PrintMsg(" \nminValue: " + str(minValue) + " maxValue: " + str(maxValue), 1)

        else:
            maxValue = round(max(outputValues), p)
            minValue = round(min(outputValues), p)
            low = round(min(outputValues), p)
            step = round(((maxValue - minValue) / float(classNum)), p)

        legendList = list()
        #

        for i in range(0, classNum, 1):
            # rating, label, rgb
            if p is None:
                high = low + step

            else:
                high = round((low + step), p)

            if i == 0:
                if str(dSDV["attributeuomabbrev"]).lower() == "none":
                    if firstClass != "":
                        label = "<= " + str(high) + "  (" + firstClass + ")"

                    else:
                        label = "<= " + str(high)

                else:
                    label = "<= " + str(high) + " " + str(dSDV["attributeuomabbrev"])

            else:
                if i == (classNum - 1) and firstClass != "":
                    label = "> " + str(low) + " and <= " + str(high) + "  (" + lastClass + ")"

                else:
                    label = "> " + str(low) + " and <= " + str(high)

            rec = [low, high, label, dColors[i]]
            legendList.append(rec)
            #PrintMsg("\t" + str(i) + ". " + str(rec), 1)  # this looks good for NCCPI
            low = round(low + step, 2)

        #PrintMsg(" \nUsing new function for Defined Breaks", 1)
        r = dict() # renderer
        r["type"] = "classBreaks"
        r["classificationMethod"] =  "esriClassifyManual"
        #r["field"]  = outputTbl + "." + ratingField # Needs fully qualified name with aggregation method as well.
        r["field"]  = ratingField # Needs fully qualified name with aggregation method as well.
        r["minValue"] = minValue

        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()

        #PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        #PrintMsg(" \n\t\tLegend maximum value: " + str(maxValue), 1)
        lastMax = minValue

        # Somehow I need to read through the legendList and determine whether it is ascending or descending order
        if cntLegend > 1:
            firstRating = legendList[0][0]
            lastRating = legendList[(cntLegend - 1)][0]

            if firstRating > lastRating:
                PrintMsg(" \nReverse legendlist", 1)
                legendList.reverse()

        # Create standard numeric legend in Ascending Order
        #
        #PrintMsg(" \n I seem to have a couple of extra items in dLegend: type=1 and name=Progressive. Where did these come from?? \n ", 1)
        if cntLegend > 0:
            dLeg = dict()

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                low, high, label, rgb = legendList[cnt]
                #if bVerbose:
                #    PrintMsg(" \n\t\tAdding legend item: " + str(label) + ", " + str(rgb), 1)
                #dLegend = dict()
                dSymbol = dict()
                legendItems = dict()
                legendItems["classMinValue"] = low
                legendItems["classMaxValue"] = high
                legendItems["label"] = label
                legendItems["description"] = ""
                legendItems["outline"] = dOutline
                dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                legendItems["symbol"] = dSymbol

                if bVerbose:
                    PrintMsg(" \nlegendItem: " + str(legendItems), 1)
                classBreakInfos.append(legendItems)


        r["classBreakInfos"] = classBreakInfos
        dLayerDef = dict()
        dRenderer = dict()
        dRenderer["renderer"] = r
        dLayerDef["drawingInfo"] = dRenderer

        #PrintMsg(" \n2. dLayerDef: \n" + str(dLayerDef), 0)  # For NCCPI this is WRONG
        test = dLayerDef['drawingInfo']['renderer']['classBreakInfos']
        #PrintMsg(" \nclassBreakInfos in ClassBreaksJSON: " + str(test), 1)

        return dLayerDef

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def UniqueValuesJSON(legendList, outputTbl, ratingField):
    # returns JSON string for unique values template. Use this for text, choice, vtext.
    #
    # Done: I need to get rid of the non-Renderer parts of the JSON so that it matches the ClassBreaksJSON function.
    # Need to implement this in the gSSURGO Mapping tools
    #
    # Example of legendList:
    # legendList: [[u'High', u'High', [0,0,255,255], [u'Moderate', u'Moderate', [0,255,0, 255], [u'Low', u'Low', [255,0,0,255]]
    #
    # Problem with legendList. FarmlandClass is not complete set of existing values. Why?

    try:
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Quick and dirty fix to see if using rating field basename instead of qualified name will fix broken symbology
        if bVerbose:
            PrintMsg(" \nUniqueValuesJSON ratingField: " + ratingField, 1)


        drawOutlines = False

        ltGray = [175, 175, 175, 255]
        dkGray = [110, 110, 110, 255]
        noColor = [0, 0, 0, 0]

        if drawOutlines == False:
            outLineColor = noColor

        else:
            outLineColor = ltGray

        d = dict()
        r = dict()
        v = dict()

        # Add each legend item to the list that will go in the uniqueValueInfos item
        cnt = 0
        legendItems = list()
        uniqueValueInfos = list()

        if len(legendList) == 0:
            raise MyError, "No data in legendList"

        for legendItem in legendList:
            #dSymbol = dict()
            rating, label, rgb = legendItem
            

            # calculate rgb colors
            #PrintMsg(" \nRGB: " + str(rgb), 1)
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : {"color": outLineColor, "width": 0.4, "style": "esriSLSSolid", "type": "esriSLS"}}
            legendItems = dict()
            legendItems["value"] = rating
            legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
            legendItems["label"] = label
            
            if bVerbose:
                PrintMsg("\tAdding legend label: " + label, 1)

            legendItems["symbol"] = symbol
            uniqueValueInfos.append(legendItems)


        # Add NULL values or empty strings as gray fill, no outline
        #
        # It looks like each value (<Null>, '', ' ') need to be added individually to the class values:
        # [u'<Null>', u'', u' ', u'High', u'Low', u'Moderate']
        #
        # Label values would then be repeated:
        # [u'Not rated or not available', u'Not rated or not available', u'Not rated or not available', u'High', u'Low', u'Moderate']
        #
        # Interps may have both 'Not rated' and <Null> values and perhaps variations on case to deal with.
        #
        if dSDV["attributetype"] == "Interpretation":
            legendItems = dict()
            legendItems["value"] = "Not rated"  # Interpretation returned 'Not rated'
            legendItems["description"] = ""     # This isn't really used unless I want to pull in a description of this individual rating
            legendItems["label"] = "Not rated"

            outLineColor = dkGray
            symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : dkGray, "outline" : {"color": noColor, "width": 0.0, "style": "esriSLSSolid", "type": "esriSLS"}}
            legendItems["symbol"] = symbol
            uniqueValueInfos.append(legendItems)

        # Add gray fill for NULL values
        legendItems = dict()
        legendItems["value"] = "<Null>"  # Null value
        legendItems["description"] = ""  # This isn't really used unless I want to pull in a description of this individual rating
        legendItems["label"] = "Null"
        outLineColor = ltGray
        symbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : ltGray, "outline" : {"color": noColor, "width": 0.0, "style": "esriSLSSolid", "type": "esriSLS"}}
        legendItems["symbol"] = symbol
        uniqueValueInfos.append(legendItems)

        v["uniqueValueInfos"] = uniqueValueInfos
        v["type"] = "uniqueValue"
        #v["field1"] = outputTbl + "." + ratingField
        v["field1"] = ratingField
        v["field2"] = "" # not being used
        v["field3"] = "" # not being used
        v["fielddelimiter"] = ";" # not being used
        r["renderer"] = v
        d["drawingInfo"] = r

        if bVerbose:
            PrintMsg(" \nUnique Values dictionary: " + str(d), 1)

        return d

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def DefinedBreaksJSON(legendList, minValue, outputTbl, ratingField):
    # returns JSON string for defined break values template. Use this for Hydric, pH.
    #
    # Slope uses a color ramp, with 6 classes.It has a maplegendkey=6
    # Red         255,0,0
    # Orange      255,166,0
    # Yellowish   231,255,74
    # Cyan        112,255,210
    # Blue        59,157,255
    # Dark Blue   8,8,255

    # Min and max values are set for each class
    # need to set:
    # d.minValue as a number
    # d.classBreakInfos which is a list containing at least two slightly different dictionaries.
    # The last one contains an additional classMinValue item
    #
    # d.classBreakInfos[0]:
    #    classMaxValue: 1000
    #    symbol: {u'color': [236, 252, 204, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 10 to 1000
    #    label: 10.0 - 1000.000000

    # d.classBreakInfos[n - 1]:  # where n = number of breaks
    #    classMaxValue: 10000
    #    classMinValue: 8000
    #    symbol: {u'color': [255, 255, 0, 255], u'style': u'esriSFSSolid', u'type': u'esriSFS', u'outline': {u'color': [110, 110, 110, 255], u'width': 0.4, u'style': u'esriSLSSolid', u'type': u'esriSLS'}}
    #    description: 1000 to 5000
    #    label: 8000.000001 - 10000.000000
    #
    # defaultSymbol is used to draw any polygon whose value is not within one of the defined ranges

    # RGB colors:
    # 255, 0, 0 = red
    # 255, 255, 0 = yellow
    # 0, 255, 0 = green
    # 0, 255, 255 = cyan
    # 0, 0, 255 = blue

    try:
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \n \n \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg("\tlegendList and minValue: " + str(legendList) + ";  " + str(minValue), 1)

        drawOutlines = False

        # Set outline symbology
        if drawOutlines == False:
            outLineColor = [0, 0, 0, 0]

        else:
            outLineColor = [110, 110, 110, 255]

        #PrintMsg(" \nUsing new function for Defined Breaks", 1)

        #PrintMsg(" \nUsing new function for Defined Breaks " + dSDV["attributelogicaldatatype"].lower(), 1)

        #if dSDV["attributelogicaldatatype"].lower() in ["text", "choice"]:
        r = dict() # renderer
        r["type"] = "classBreaks"
        r["classificationMethod"] =  "esriClassifyManual"
        r["field"]  = ratingField # Needs fully qualified name with aggregation method as well.
        r["minValue"] = minValue
        #r["defaultLabel"] = "Not rated or not available"  # Doesn't work for numeric data having classified breaks
        ds = {"type":"esriSFS", "style":"esriSFSSolid","color":[110,110,110,255], "outline": {"type":"esriSLS","style": "esriSLSSolid","color":outLineColor,"width": 0.5}}
        #r["defaultSymbol"] = ds


        # Add new rating field (fully qualified name) to list of layer fields

        cnt = 0
        cntLegend = (len(legendList))
        classBreakInfos = list()

        #PrintMsg(" \n\t\tLegend minimum value: " + str(minValue), 1)
        #PrintMsg(" \n\t\tLegend maximum value: " + str(maxValue), 1)
        lastMax = minValue

        # Somehow I need to read through the legendList and determine whether it is ascending or descending order
        if cntLegend > 1:

            #for legendInfo in legendList:
            firstRating = legendList[0][0]
            lastRating = legendList[(cntLegend - 1)][0]

        if firstRating > lastRating:
            legendList.reverse()

        # Create standard numeric legend in Ascending Order
        #
        if cntLegend > 1:
            #PrintMsg(" \nChecking legendList: \n" + str(legendList), 1)

            #for legendInfo in legendList:
            for cnt in range(0, (cntLegend)):

                minRating, maxRating, label, rgb = legendList[cnt]
                rgb = [int(c) for c in rgb]

                if not minRating is None:

                    #ratingValue = float(rating)
                    #PrintMsg(" \n\t\tAdding legend values: " + str(lastMax) + "-> " + str(rating) + ", " + str(label), 1)

                    # calculate rgb colors
                    #rgb = list(int(hexCode.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
                    #rgb.append(255)  # set transparency ?
                    dLegend = dict()
                    dSymbol = dict()
                    dLegend["classMinValue"] = minRating
                    dLegend["classMaxValue"] = maxRating
                    dLegend["label"] = label
                    dLegend["description"] = ""
                    dOutline = dict()
                    dOutline["type"] = "esriSLS"
                    dOutline["style"] = "esriSLSSolid"
                    dOutline["color"] = outLineColor
                    dOutline["width"] = 0.4
                    dSymbol = {"type" : "esriSFS", "style" : "esriSFSSolid", "color" : rgb, "outline" : dOutline}
                    dLegend["symbol"] = dSymbol
                    dLegend["outline"] = dOutline
                    classBreakInfos.append(dLegend)  # This appears to be working properly
                    #PrintMsg(" \n\t" + str(cnt) + ". Adding dLegend: " + str(dSymbol), 1)

                    #lastMax = ratingValue

                    cnt += 1  # why is cnt being incremented here????

        r["classBreakInfos"] = classBreakInfos
        dLayerDef = dict()
        dRenderer = dict()
        dRenderer["renderer"] = r
        dLayerDef["drawingInfo"] = dRenderer

        # Note to self. Hydric is running this DefinedBreaksJSON
        #PrintMsg(" \nDefinedBreaksJSON - dClassBreakInfos: \n" + str(classBreakInfos), 1)
        #PrintMsg("\tlegendList and minValue: " + str(legendList) + ";  " + str(minValue), 1)

        return dLayerDef

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return dict()

    except:
        errorMsg()
        return dict()

## ===================================================================================
def CreateMapLayer(fcName, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, creditsString, dLayerDefinition, bFuzzy):
    # Setup new map layer with appropriate symbology and add it to the table of contents.
    #
    # Quite a few global variables being called here.
    #
    # With ArcGIS 10.1, there seem to be major problems when the layer is a featurelayer
    # and the valueField is from a joined table. Any of the methods that try to
    # update the legend values will fail and possibly crash ArcMap.
    #
    # A new test using MakeQueryTable seems to work, but still flaky.
    #
    # Need to figure out why the symbols for Progressive allow the outlines to
    # be turned off, but 'Defined' do not.
    #
    #
    try:
        # bVerbose = True
        msg = "Preparing soil map layer for display..."
        arcpy.SetProgressorLabel(msg)
        PrintMsg("\t" + msg, 0)

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        hasJoin = False

        # Create initial map layer using MakeQueryTable. Need to add code to make
        # sure that a join doesn't already exist, thus changing field names
        #tableList = [inputLayer, outputTbl]

        # Create fieldInfo string
        dupFields = list()
        keyField = os.path.basename(fc) + ".OBJECTID"
        #fieldInfo = list()
        sFields = ""
        #PrintMsg(" \noutputLayer: " + outputLayer, 1)
        qLayer = "View_" + arcpy.ValidateTableName(outputLayer, gdb)

        # Use SQLite query to create a table view and then add that to ArcMap

        # Begin by writing SQL for table view
        sQuery = "CREATE VIEW " + qLayer + " AS SELECT \n"

        # first get list of fields from mupolygon layer

        for fld in muDesc.fields:
            dupFields.append(fld.baseName.lower())
            sQuery += "M." + fld.baseName.lower() + ", "


        # then get non-duplicate fields from output table
        fldCnt = len(tblDesc.fields)
        lastFld = tblDesc.fields[-1]
        
        for fld in tblDesc.fields:
            if not fld.baseName in dupFields:
                dupFields.append(fld.baseName.lower())

                if lastFld.baseName.lower() == fld.baseName.lower():
                    # This is the last field, no comma needed in query
                    sQuery += "R." + fld.baseName.lower() + " \n"
                    ratingField = fld.baseName.lower()

                else:
                    sQuery += "R." + fld.baseName.lower() + ", "

        #sQuery += "FROM MUPOLYGON M \n"  # this is a problem. Need to substitute the featureclass behind inputLayer
        sQuery += "FROM " + fcName + " M \n"  # this is a problem. Need to substitute the featureclass behind inputLayer
        sQuery += "LEFT OUTER JOIN " + os.path.basename(outputTbl) + " R ON M.mukey = R.mukey \n"
        sQuery += "ORDER BY M.objectid ASC"

        # Create connection to database
        queryDropView = "DROP VIEW IF EXISTS " + qLayer + ";"
        #PrintMsg(" \nDrop table query: \n" + queryDropView, 1)

        liteCur.execute(queryDropView)
        dbConn.commit()

        if bVerbose:
            PrintMsg(" \nCreate View query: \n" + sQuery, 1)

        liteCur.execute(sQuery)
        dbConn.commit()

        arcpy.MakeFeatureLayer_management(os.path.join(gdb, qLayer), outputLayer)

        # identify layer file in script directory to use as basis for symbology
        #
        if bFuzzy:
            sdvLyr = "sdv_InterpFuzzyNumbers.lyr"

        else:
            if dLegend["name"] == "Random":
                sdvLyr = "sdv_PolygonUnique.lyr"

            elif dSDV["maplegendkey"] == 2 and dSDV["attributelogicaldatatype"].lower() == "integer":
                sdvLyr = "sdv_" + str(dSDV["maplegendkey"]) + "_" + str(dLegend["type"]) + "_" + dLegend["name"] + "Integer" + ".lyr"

            else:
                sdvLyr = "sdv_" + str(dSDV["maplegendkey"]) + "_" + str(dLegend["type"]) + "_" + dLegend["name"] + ".lyr"

        sdvLyrFile = os.path.join(os.path.dirname(sys.argv[0]), sdvLyr)
        #

        if bVerbose:
            PrintMsg(" \nCreating symLayer using SDV symbology from '" + sdvLyrFile + "'", 1)

        if arcpy.Exists(outputLayer):
            outputFields = [fld.name for fld in arcpy.Describe(outputLayer).fields]

            if arcpy.Exists(outputLayerFile):
                arcpy.Delete_management(outputLayerFile)

            if bVerbose:
                PrintMsg(" \nSaving " + outputLayer + " to " + outputLayerFile, 1)

            arcpy.SaveToLayerFile_management(outputLayer, outputLayerFile, "ABSOLUTE")

            try:
                arcpy.Delete_management(outputLayer)

            except:
                PrintMsg(" \nFailed to remove " + outputLayer, 1)

            if bVerbose:
                PrintMsg(" \nSaved map to layerfile: " + outputLayerFile, 0)

        else:
            raise MyError, "\tFailed to create temporary layer: " + outputLayer + " from " + inputLayer

        if dLegend["name"] == "Random" and len(dLegend["labels"]) == 0:
            #
            # New code for unique values, random color featurelayer. This skips most of the CreateMapLayer function
            # which uses JSON to build map symbology.
            #
            # I may want to incorporate layer.getSelectionSet() in order to determine if there is a selected set
            # Tip. Apply a selection set using .setSelectionSet(selSet)

            #PrintMsg(" \n\tUpdating new layer symbology using " + sdvLyr, 1)
            start = time.time()
            symLayer = arcpy.mapping.Layer(sdvLyrFile)
            finalMapLayer = arcpy.mapping.Layer(outputLayerFile)  # recreate the outputlayer
            arcpy.mapping.UpdateLayer(df, finalMapLayer, symLayer, True)

            
            #finalMapLayer.symbology.valueField = os.path.basename(outputTbl) + "." + outputFields[-1]
            #PrintMsg(" \nValue Field: " + outputFields[-1], 1)
            finalMapLayer.symbology.valueField = outputFields[-1]

            if finalMapLayer.symbologyType.upper() == 'UNIQUE_VALUES':

                if bVerbose:
                    PrintMsg(" \noutputFields: " + ", ".join(outputFields), 1)
                    
                #finalMapLayer.symbology.valueField = os.path.basename(outputTbl) + "." + outputFields[-1]
                finalMapLayer.symbology.valueField = outputFields[-1]
                outputNum = len(outputValues)
                maxValues = 10000

                if outputNum < maxValues:
                    # If the number of unique values is less than maxValues, go ahead and create the map legend,
                    # otherwise skip it or we'll be here all day..
                    #
                    finalMapLayer.symbology.addAllValues()
                    arcpy.RefreshActiveView()
                    arcpy.RefreshTOC()
                    #theMsg = " \nUpdated symbology for " + Number_Format(outputNum, 0, True) + " unique values in " + elapsedTime(start)
                    #PrintMsg(theMsg, 0)
                    #end = time.time()
                    #lps = len(outputValues) / (end - start)
                    #PrintMsg(" \nProcessed " + Number_Format(lps, 0, True) + " labels per second", 1)

                else:
                    PrintMsg(" \nSkipping random color symbology. " + Number_Format(outputNum, 0, True) + " is too many unique values)", 0)

        else:
            # Handle all the non-Random legends

            # This next section is where classBV is getting populated for pH for Polygon
            #
            if dSDV["maplegendkey"] in [1, 3, 6]:
                # For maplegendkeys 3, 6, this legend will use Graduated Colors
                #
                # Need to move maplegendkey 1 to Defined colors for class breaks

                #PrintMsg(" \nIs this where Salinity Risk is going?", 1)
                #PrintMsg("dLegend: " + str(dLegend), 1)
                #PrintMsg("dLabels: " + str(dLabels), 1)


                classBV = list()
                classBL = list()

                if len(dLabels) > 0:
                    #PrintMsg(" \nGot labels....", 1)
                    if bVerbose:
                        for key, val in dLabels.items():
                            PrintMsg("\t3 dLabels[" + str(key) + "] = " + str(val), 1)

                    if float(dLabels[1]["upper_value"]) > float(dLabels[len(dLabels)]["upper_value"]):
                        # Need to swap because legend is high-to-low
                        classBV.append(float(dLabels[len(dLabels)]["lower_value"]))
                        #PrintMsg("\tLow value: " + dLabels[len(dLabels)]["lower_value"], 1)

                        for i in range(len(dLabels), 0, -1):
                            classBV.append(float(dLabels[i]["upper_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("\tLegend Text: " + dLabels[i]["label"], 1)
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                    else:
                        # Legend is already low-to-high

                        for i in range(1, len(dLabels) + 1):
                            classBV.append(float(dLabels[i]["lower_value"]))       # class break
                            classBL.append(dLabels[i]["label"])                    # label
                            #PrintMsg("Class: " + str(dLabels[i]["lower_value"]), 1)

                        classBV.append(float(dLabels[len(dLabels)]["upper_value"]))
                        #PrintMsg("\tLast value: " + dLabels[len(dLabels)]["upper_value"], 1)

                    # Report class breaks and class break labels
                    if bVerbose:
                        PrintMsg(" \nClass Break Values for 1, 3, 6: " + str(classBV), 1)
                        PrintMsg(" \nClass Break Labels for 1, 3, 6: " + str(classBL), 1)

            elif dSDV["maplegendkey"] in [2]:
                # I believe this is Unique Values renderer
                #
                # iterate through dLabels using the key 'order' to determine sequence within the map legend
                #
                labelText = list()
                dOrder = dict()    # test. create dictionary with key = uppercase(value) and contains a tuple (order, labeltext)
                classBV = list()
                classBL = list()

                if dSDV["effectivelogicaldatatype"].lower() == "integer":

                    for val in outputValues:
                        classBV.append(val)
                        classBL.append(str(val))

                else:
                    for i in range(1, len(dLabels) + 1):
                        label = dLabels[i]["label"]

                        if dSDV["effectivelogicaldatatype"].lower() == "float":
                            # Float
                            value = float(dLabels[i]["value"])    # Trying to get TFactor working

                        else:
                            # String or Choice
                            value = dLabels[i]["value"]    # Trying to get TFactor working

                        if value.upper() in domainValuesUp and not value in domainValues:
                            # Compare legend values to domainValues
                            #PrintMsg("\tFixing label value: " + str(value), 1)
                            value = dValues[value.upper()][1]

                        #elif not value.upper() in domainValuesUp and not value in domainValues:
                            # Compare legend values to domainValues
                            #PrintMsg("\tExtra label value?: " + str(value), 1)
                            #value = dValues[value.upper()]

                        labelText.append(label)
                        dOrder[str(value).upper()] = (i, value, label)
                        classBV.append(value) # 10-02 Added this because of TFactor failure
                        classBL.append(label) # 10-02 Added this because of TFactor failure

            elif dSDV["maplegendkey"] in [5, 7, 8]:
                # iterate through dLabels using the key 'order' to determine sequence within the map legend
                # Added method to handle Not rated for interps
                # Need to add method to handle NULL in interps
                #
                # Includes Soil Taxonomy  4, 0, Random
                #
                #labelText = list()
                dOrder = dict()    # test. create dictionary with key = uppercase(value) and contains a tuple (order, labeltext)
                classBV = list()
                classBL = list()

                for i in range(1, len(dLabels) + 1):
                    # Make sure label value is in domainValues
                    label = dLabels[i]["label"]
                    value = dLabels[i]["value"]

                    if value.upper() in domainValuesUp and not value in domainValues:
                        # Compare legend values to domainValues
                        #PrintMsg("\tFixing label value: " + str(value), 1)
                        value = dValues[value.upper()][1]
                        label = str(value)
                        domainValues.append(value)

                    elif not value.upper() in domainValuesUp and not value in domainValues and value.upper() in dValues:
                        # Compare legend values to domainValues
                        #PrintMsg("\tExtra label value?: " + str(value), 1)
                        value = dValues[value.upper()][1]
                        label = str(value)
                        domainValues.append(value)

                    if not value in classBV:
                        dOrder[value.upper()] = (i, value, label)
                        classBV.append(value)
                        classBL.append(str(value))
                        #labelText.append(str(value))
                        #PrintMsg("\tAdded class break and label values to legend: " + str(value), 1)

                # Compare outputValues to classBV. In conservation tree/shrub, there can be values that
                # were not included in the map legend.
                order = 0

                for value in outputValues:
                    if not value in classBV:
                        #PrintMsg("\tAdding missing Value '" + str(value) + " to map legend", 1)
                        classBV.append(value)
                        classBL.append(value)
                        order += 1
                        dOrder[str(value).upper()] = (order, value, value)  # Added str function on value to fix bNulls error

                if "Not Rated" in outputValues:
                    #PrintMsg(" \nFound the 'Not Rated' value in outputValues", 1)
                    dOrder["NOT RATED"] = (order + 1, "Not Rated", "Not Rated")

                elif "Not rated" in outputValues:
                    #PrintMsg(" \nFound the 'Not rated' value in outputValues", 1)
                    dOrder["NOT RATED"] = (order + 1, "Not rated", "Not rated")

            if bVerbose:
                PrintMsg(" \nfinalMapLayer created using " + outputLayerFile, 1)

            finalMapLayer = arcpy.mapping.Layer(outputLayerFile)  # recreate the outputlayer


            # Test JSON formatting method
            #
            #PrintMsg(" \nUpdating layer symbology using JSON method", 1)
            #PrintMsg(" \nJSON layer update: " + str(dLayerDefinition) + " \n ", 1)
            finalMapLayer.updateLayerFromJSON(dLayerDefinition)

        # Add layer file path to layer description property
        envUser = arcpy.GetSystemEnvironment("USERNAME")
        if "." in envUser:
            user = envUser.split(".")
            userName = " ".join(user).title()

        elif " " in envUser:
            user = envUser.split(" ")
            userName = " ".join(user).title()

        else:
            userName = envUser


        finalMapLayer.description = dSDV["attributedescription"] + "\r\n\r\n" + parameterString
        finalMapLayer.credits = creditsString
        finalMapLayer.visible = False
        arcpy.mapping.AddLayer(df, finalMapLayer, "TOP")
        arcpy.RefreshTOC()
        arcpy.SaveToLayerFile_management(finalMapLayer.name, outputLayerFile, "RELATIVE", "10.3")

        if __name__ == "__main__":
            PrintMsg("\tSaved map to layer file: " + outputLayerFile + " \n ", 0)

        else:
            PrintMsg("\tSaved map to layer file: " + outputLayerFile, 0)

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        try:
            if hasJoin:
            #    PrintMsg("\tRemoving join", 1)
                arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))

        except:
            pass

        return False

    except:
        errorMsg()
        if hasJoin:
            arcpy.RemoveJoin_management(inputLayer, os.path.basename(outputTbl))
        return False

## ===================================================================================
def ValidateName(inputName):
    # Remove characters from file name or table name that might cause problems
    try:
        #PrintMsg(" \nValidating input table name: " + inputName, 1)
        f = os.path.basename(inputName)
        db = os.path.dirname(inputName)
        validName = ""
        validChars = "_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        lastChar = "."
        charList = list()

        for s in f:
            if s in validChars:
                if  not (s == "_" and lastChar == "_"):
                    charList.append(s)

                elif lastChar != "_":
                    lastChar = s

        validName = "".join(charList)

        return os.path.join(db, validName)

    except MyError, e:
        PrintMsg(str(e), 2)
        try:
            arcpy.RemoveJoin_management(inputLayer, outputTbl)
            return ""
        except:
            return ""

    except:
        errorMsg()
        try:
            arcpy.RemoveJoin_management(inputLayer, outputTbl)
            return ""

        except:
            return ""

## ===================================================================================
def ReadTable(tbl, flds, wc, level, sql):
    # Read target table using specified fields and optional sql
    # Other parameters will need to be passed or other functions created
    # to handle aggregation methods and tie-handling
    # ReadTable(dSDV["attributetablename"].lower(), flds, primSQL, level, sql)
    try:
        #bVerbose = True

        arcpy.SetProgressorLabel("Reading input data (" + tbl.lower() +")")
        start = time.time()

        # Create dictionary to store data for this table
        dTbl = dict()
        # Open table with cursor
        iCnt = 0

        # ReadTable Diagnostics
        if bVerbose:
            PrintMsg(" \nReading Table: " + tbl + ", Fields: " + str(flds), 1)
            PrintMsg("WhereClause: " + str(wc) + ", SqlClause: " + str(sql) + " \n ", 1)

        with arcpy.da.SearchCursor(tbl, flds, where_clause=wc, sql_clause=sql) as cur:
            for rec in cur:

                val = list(rec[1:])

                try:
                    dTbl[rec[0]].append(val)

                except:
                    dTbl[rec[0]] = [val]

                iCnt += 1

        if bVerbose:
            theMsg = " \nProcessed " + Number_Format(iCnt, 0, True) + " " +tbl + " records in " + elapsedTime(start)
            PrintMsg(theMsg, 0)

        return dTbl

    except:
        errorMsg()
        return dict()

## ===================================================================================
def ListMonths():
    # return list of months
    try:
        moList = ['NULL', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        return moList

    except:
        errorMsg()
        return []

## ===================================================================================
def GetAreasymbols(gdb):
    # return a dictionary for areasymbol. Key = lkey and Value = areasymbol
    #
    try:
        dAreasymbols = dict()

        inputTbl = os.path.join(gdb, "LEGEND")

        # Get list of areasymbols from input feature layer
        #
        # I should probably compare the count of the featureclass vs the count of the featurelayer. If they are the
        # same, then just use the legend and skip this next part. I'm assuming that if the input featureclass name
        # is NOT "MUPOLYGON" then this is a subset and will automatically get the list from the input layer.
        #
        #
        if fcCnt != polyCnt or os.path.basename(fc) != "MUPOLYGON" and dataType != "rasterlayer":
            areasymbolList = list()  # new code
            #PrintMsg(" \nGetting list of areasymbols from the input soils layer", 1)
            #sqlClause = ("DISTINCT", "ORDER BY areasymbol")
            sqlClause = ("DISTINCT", None)

            with arcpy.da.SearchCursor(inputTbl, ["areasymbol"], sql_clause=sqlClause) as cur:  # new code
                for rec in cur:  # new code
                    areasymbolList.append(rec[0].encode('ascii')) # new code

            areasymbolList.sort()
            #PrintMsg(" \nFinished getting list of areasymbols (" + Number_Format(len(areasymbolList), 0, True) + ") for the input soils layer", 1)

            # Now get associated mapunit-legend keys for use in other queries
            #
            if len(areasymbolList) == 1:
                whereClause = "areasymbol = '" + areasymbolList[0] + "'"

            else:
                whereClause = "areasymbol IN " + str(tuple(areasymbolList))

            with arcpy.da.SearchCursor(inputTbl, ["lkey", "areasymbol"], where_clause=whereClause) as cur:
                for rec in cur:
                    if rec[1] in areasymbolList:  # new code
                        dAreasymbols[rec[0]] = rec[1]

        else:
            # For raster layers, get areasymbol from legend table. Not ideal, but alternatives could be much slower.
            #PrintMsg(" \nGetting list of areasymbols from the input database", 1)

            with arcpy.da.SearchCursor(inputTbl, ["lkey", "areasymbol"]) as cur:
                for rec in cur:
                    dAreasymbols[rec[0]] = rec[1]

        return dAreasymbols

    except:
        errorMsg()
        return dAreasymbols

## ===================================================================================
def GetSDVAtts(gdb, sdvAtt, aggMethod, tieBreaker, bFuzzy, sRV):
    # Create a dictionary containing SDV attributes for the selected attribute fields
    #
    try:
        # Open sdvattribute table and query for [attributename] = sdvAtt
        dSDV = dict()  # dictionary that will store all sdvattribute data using column name as key
        sdvattTable = os.path.join(gdb, "sdvattribute")
        flds = [fld.name for fld in arcpy.ListFields(sdvattTable)]
        sql1 = "attributename = '" + sdvAtt + "'"

        if bVerbose:
            PrintMsg(" \nReading sdvattribute table into dSDV dictionary", 1)

        with arcpy.da.SearchCursor(sdvattTable, "*", where_clause=sql1) as cur:
            rec = cur.next()  # just reading first record
            i = 0
            for val in rec:
                dSDV[flds[i].lower()] = val
                #PrintMsg(str(i) + ". " + flds[i] + ": " + str(val), 0)
                i += 1

        # Revise some attributes to accomodate fuzzy number mapping code
        #
        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number

        if dSDV["interpnullsaszeroflag"]:
            bZero = True

        if dSDV["attributetype"].lower() == "interpretation" and (dSDV["effectivelogicaldatatype"].lower() == "float" or bFuzzy == True):
            #PrintMsg(" \nOver-riding attributecolumnname for " + sdvAtt, 1)
            dSDV["attributecolumnname"] = "INTERPHR"

            # WHAT HAPPENS IF I SKIP THIS NEXT SECTION. DOES IT BREAK EVERYTHING ELSE WHEN THE USER SETS bFuzzy TO True?
            # Test is ND035, Salinity Risk%
            # Answer: It breaks my map legend.

            if dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() in ["string", "narrative text"] and dSDV["effectivelogicaldatatype"].lower() == "float":
                #PrintMsg("\tIdentified " + sdvAtt + " as being an interp with a numeric rating", 1)
                pass

            else:
            #if dSDV["nasisrulename"][0:5] != "NCCPI":
                # This comes into play when user selects option to create soil map using interp fuzzy values instead of rating classes.
                dSDV["effectivelogicaldatatype"] = 'float'
                dSDV["attributelogicaldatatype"] = 'float'
                dSDV["maplegendkey"] = 3
                dSDV["maplegendclasses"] = 5
                dSDV["attributeprecision"] = 2

        # Workaround for sql whereclause stored in sdvattribute table. File geodatabase is case sensitive.
        if dSDV["sqlwhereclause"] is not None:
            sqlParts = dSDV["sqlwhereclause"].split("=")
            dSDV["sqlwhereclause"] = "UPPER(" + sqlParts[0] + ") = " + sqlParts[1].upper()

        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False and dSDV["notratedphrase"] is None:
            # Add 'Not rated' to choice list
            dSDV["notratedphrase"] = "Not rated" # should not have to do this, but this is not always set in Rule Manager

        if dSDV["secondaryconcolname"] is not None and dSDV["secondaryconcolname"].lower() == "yldunits":
            # then this would be units for map legend (component crop yield)
            PrintMsg(" \nSetting units of measure to: " + secCst, 1)
            dSDV["attributeuomabbrev"] = secCst

        if dSDV["attributecolumnname"].endswith("_r") and sRV in ["Low", "High"]:
            # This functionality is not available with SDV or WSS. Does not work with interps.
            #
            if sRV == "Low":
                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_l")

            elif sRV == "High":
                dSDV["attributecolumnname"] = dSDV["attributecolumnname"].replace("_r", "_h")

            #PrintMsg(" \nUsing attribute column " + dSDV["attributecolumnname"], 1)

        # Working with sdvattribute tiebreak attributes:
        # tiebreakruleoptionflag (0=cannot change, 1=can change)
        # tiebreaklowlabel - if null, defaults to 'Lower'
        # tiebreaklowlabel - if null, defaults to 'Higher'
        # tiebreakrule -1=use lower  1=use higher
        if dSDV["tiebreaklowlabel"] is None:
            dSDV["tiebreaklowlabel"] = "Lower"

        if dSDV["tiebreakhighlabel"] is None:
            dSDV["tiebreakhighlabel"] = "Higher"

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            #PrintMsg(" \nUpdating dAgg", 1)
            dAgg["Minimum or Maximum"] = "Max"

        else:
            dAgg["Minimum or Maximum"] = "Min"
            #PrintMsg(" \nUpdating dAgg", 1)

        if aggMethod == "":
            aggMethod = dSDV["algorithmname"]

        if dAgg[aggMethod] != "":
            dSDV["resultcolumnname"] = dSDV["resultcolumnname"] + "_" + dAgg[aggMethod].lower()

        #PrintMsg(" \nSetting resultcolumn name to: '" + dSDV["resultcolumnname"] + "'", 1)

        return dSDV

    except:
        errorMsg()
        return dSDV

## ===================================================================================
def GetRuleKey(distinterpTbl, nasisrulename):

    # distinterpmd: rulekey, rulekey
    # cointerp: mrulekey, mrulename, ruledepth=0
    # Need to determine if there is always 1:1 for rulekey and rulename

    try:
        #bVerbose = True
        whereClause = "rulename = '" + nasisrulename + "'"
        ruleKeys = list()

        with arcpy.da.SearchCursor(distinterpTbl, ["rulekey"], where_clause=whereClause) as mCur:
            for rec in mCur:
                ruleKey = rec[0].encode('ascii')

                if not ruleKey in ruleKeys:
                    ruleKeys.append(ruleKey)

        if len(ruleKeys) == 1:
            keyString = "('" + ruleKeys[0] + "')"

        else:
            keyString = "('" + "','".join(ruleKeys) + "')"

        #if len(ruleKeys) > 1:
        #    PrintMsg("\tFound " + str(len(ruleKeys)) + " rulekey values for " + nasisrulename + ": " + str(ruleKeys), 1)

        #elif len(ruleKeys) == 0:
        #    return None

        if bVerbose:
            PrintMsg("\tSQL for " + nasisrulename + ": " + keyString, 1)

        return keyString

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()
        return None

## ===============================================================================================================
def GetTableKeys(gdb):
    #
    # Retrieve physical and alias names from mdstatidxdet table and assigns them to a blank dictionary.
    # tabphyname, idxphyname, idxcolsequence, colphyname
    # indxphyname prefixes: PK_, DI_

    try:
        tableKeys = dict()  # key = table name, values are a list containing [primaryKey, foreignKey]

        # Open mdstattabs table containing information for other SSURGO tables
        theMDTable = "mdstatidxdet"
        env.workspace = gdb

        # Get primary and foreign keys for each table using mdstatidxdet table.
        #
        if arcpy.Exists(os.path.join(gdb, theMDTable)):

            fldNames = ["tabphyname", "idxphyname", "colphyname"]
            wc = "idxphyname NOT LIKE 'UC_%'"
            #wc = ""

            with arcpy.da.SearchCursor(os.path.join(gdb, theMDTable), fldNames, wc) as rows:

                for row in rows:
                    # read each table record and assign 'tabphyname' and 'tablabel' to 2 variables
                    tblName, indexName, columnName = row
                    #PrintMsg(str(row), 1)

                    if indexName[0:3] == "PK_":
                        # primary key
                        if tblName in tableKeys:
                            tableKeys[tblName.lower()][0] = columnName

                        else:
                            tableKeys[tblName.lower()] = [columnName, None]

                    elif indexName[0:3] == "DI_" and columnName.lower().endswith("key"):
                        # foreign key
                        if tblName in tableKeys:
                            tableKeys[tblName.lower()][1] = columnName

                        else:
                            tableKeys[tblName.lower()] = [None, columnName]

            del theMDTable

            # For some reason muaggatt is a little different. I need a foreign key to use in my queries.
            # Try manual intervention
            tableKeys["muaggatt"][1] = "mukey"

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
def GetRatingDomain(gdb):
    # return list of tiebreak domain values for rating
    # modify this function to use uppercase string version of values
    #
    # The tiebreak domain name is not always used, even when there is a set
    # of domain names for the attribute (eg Conservation Tree and Shrub Group)

    try:

        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        mdcols = os.path.join(gdb, "mdstatdomdet")
        domainName = dSDV["tiebreakdomainname"]
        #PrintMsg(" \nUsing domain name: " + str(domainName), 1)
        domainValues = list()

        if dSDV["tiebreakdomainname"] is not None:
            wc = "domainname = '" + dSDV["tiebreakdomainname"] + "'"

            sc = (None, "ORDER BY choicesequence ASC")

            with arcpy.da.SearchCursor(mdcols, ["choice", "choicesequence"], where_clause=wc, sql_clause=sc) as cur:
                for rec in cur:
                    val = rec[0]

                    if not val in domainValues:
                        domainValues.append(val)

        return domainValues

    except:
        errorMsg()
        return []

## ===================================================================================
def GetValuesFromLegend(dLegend):
    # return list of legend values from dLegend (XML source)
    # modify this function to use uppercase string version of values

    try:
        legendValues = list()

        if len(dLegend) > 0:
            pass
            #dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext Now a global


        else:

            PrintMsg(" \nChanging legend name to 'Progressive'", 1)
            PrintMsg(" \ndLegend: " + str(dLegend["name"]), 1)
            legendValues = list()
            #dLegend["name"] = "Progressive"  # bFuzzy
            dLegend["type"] = "1"

        labelCnt = len(dLabels)     # get count for number of legend labels in dictionary

        #if not dLegend["name"] in ["Progressive", "Defined"]:
        # Note: excluding defined caused error for Interp DCD (Haul Roads and Log Landings)

        if not dLegend["name"] in ["Progressive", "Defined"]:
            # example AASHTO Group Classification
            legendValues = list()      # create empty list for label values

            for order in range(1, (labelCnt + 1)):
                #legendValues.append(dLabels[order]["value"].title())
                legendValues.append(dLabels[order]["value"])

                if bVerbose:
                    PrintMsg("\tAdded legend value #" + str(order) + " ('" + dLabels[order]["value"] + "') from XML string", 1)

        elif dLegend["name"] == "Defined":
            #if dSDV["attributelogicaldatatype"].lower() in ["string", "choice]:
            # Non-numeric values
            for order in range(1, (labelCnt + 1)):
                try:
                    # Hydric Rating by Map Unit
                    legendValues.append(dLabels[order]["upper_value"])
                    legendValues.append(dLabels[order]["lower_value"])

                except:
                    # Other Defined such as 'Basements With Dwellings', 'Land Capability Class'
                    legendValues.append(dLabels[order]["value"])

        return legendValues

    except:
        errorMsg()
        return []

## ===================================================================================
def GetMapunitSymbols(gdb):
    # Populate dictionary using mukey and musym
    # This function is for development purposes only and will probably not be
    # used in the final version.

    dSymbols = dict()
    env.workspace = gdb

    try:

        with arcpy.da.SearchCursor("mapunit", ["mukey", "musym"]) as mCur:
            for rec in mCur:
                dSymbols[rec[0]] = rec[1]

        return dSymbols

    except MyError, e:
        PrintMsg(str(e), 2)
        return dSymbols

    except:
        errorMsg()
        return dSymbols

## ===================================================================================
def CreateInitialTable(gdb, allFields, dFieldInfo, finalQuery, dbConn, liteCur):
    # Create the empty output table that will contain key fields from all levels plus
    # the input rating field
    #
    # Problem with Geopackage database. This table and the output table are not being
    # registered and thus are not seen by ArcGIS.
    
    try:
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        #
        initialTbl = "sdv_data"
        #PrintMsg(" \nDatabase on disk is " + gdb, 1)
        
        # Get distinct list of file geodatabase data types in gSSURGO
        # fldType = "TEXT"

        # FGDB datatypes: Date, String, SmallInteger, Integer, Single, Double
        fldTypes = dict()
        fldTypes['TEXT'] = "TEXT"
        fldTypes["SHORT"] = "INTEGER"
        fldTypes["FLOAT"] = "REAL"
        fldTypes["OID"] = "INTEGER PRIMARY KEY"

        allFields.insert(0, "OBJECTID")
        iFlds = len(allFields)
        newField = dSDV["attributecolumnname"].lower()
        i = 0

        # Add required fields to initial table
        i = 0
        queryFields = list()
        queryCreateTable = ""
        allFields = [fld for fld in allFields if fld != "lkey"]

        # New code. Try creating sdv_data table using IN_MEMORY workspace in ArcGIS.
        # Then copy the table to the geopackage database.

        memTbl = arcpy.CreateTable_management("IN_MEMORY", "mem_ratings")
        
        for fld in allFields:
            i += 1

            if not fld.lower() in queryFields:
                
                if fld == newField:
                    #PrintMsg("\tAdding last field " + fld + " to initialTbl as a " + dFieldInfo[fld][0], 1)
                    fldType, fldLen = dFieldInfo[fld.lower()]
                    
                    if fldType == "OID":
                        # Have to have OBJECTID field or the insert seems to fail
                        #fldSQL = fld + " " + fldTypes[fldType]
                        pass

                    else:
                        queryFields.append(fld.lower())

                    if fldType == "TEXT":
                        #fldSQL = fld + " " + fldTypes[fldType] + "(" + str(fldLen) + ")"
                        arcpy.AddField_management(memTbl, fld, fldType, "", "", fldLen)

                    else:
                        #fldSQL = fld + " " + fldTypes[fldType]
                        arcpy.AddField_management(memTbl, fld, fldType)

                else:
                    #PrintMsg("\tAdding field " + fld + " to initialTbl", 1)
                    fldType, fldLen = dFieldInfo[fld.lower()]

                    if fldType == "TEXT":
                        #fldSQL = fld + " " + fldTypes[fldType] + "(" + str(fldLen) + "),"
                        queryFields.append(fld.lower())
                        arcpy.AddField_management(memTbl, fld, fldType, "", "", fldLen)
                        
                    else:
                        fldSQL = fld + " " + fldTypes[fldType] + ","
                        
                        if fldType != "OID":
                            arcpy.AddField_management(memTbl, fld, fldType)
                            queryFields.append(fld.lower())

                #queryCreateTable += " \n" + fldSQL

        #queryCreateTable += " \n);"

        # Copy in_memory table to SQLite database
        arcpy.Copy_management(memTbl, os.path.join(gdb, initialTbl))
        del memTbl

        # Populate the empty sdv_data table in the input sqlite database
        queryInsert = "INSERT INTO " + initialTbl + " (" + ", ".join(queryFields) + ") \n" + finalQuery
        liteCur.execute(queryInsert)
        dbConn.commit()


        return initialTbl

    except MyError, e:
        PrintMsg(str(e), 2)
        return None

    except:
        errorMsg()

        return None

## ===================================================================================
def CreateOutputTable(initialTbl, outputTbl, dFieldInfo):
    # Create the initial output table that will contain key fields from all levels plus the input rating field
    #
    try:
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Validate output table name
        outputTbl = ValidateName(outputTbl)
        #outputTbl = os.path.join(os.path.dirname(outputTbl), "main." + os.path.basename(outputTbl))

        if outputTbl == "":
            return ""

        # Delete table from prior runs
        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

            if bVerbose:
                PrintMsg("\tDeleting existing copy of " + outputTbl, 1)

        # Update name for initialTbl
        #initialTbl = os.path.join(os.path.dirname(initialTbl), os.path.basename(initialTbl))
        
        if not arcpy.Exists(initialTbl):
            PrintMsg(" \nCannot find table " + initialTbl, 1)
            raise MyError, ""
            

        # Create the final output table

        # FGDB datatypes: Date, String, SmallInteger, Integer, Single, Double
        fldTypes = dict()
        fldTypes['TEXT'] = "TEXT"
        fldTypes["SHORT"] = "INTEGER"
        fldTypes["FLOAT"] = "REAL"
        fldTypes["OID"] = "INTEGER PRIMARY KEY"


        queryDropTable = "DROP TABLE IF EXISTS " + os.path.basename(outputTbl) + ";"
        liteCur.execute(queryDropTable)
        dbConn.commit()

        memTbl = "output_ratings"
        memTbl = arcpy.CreateTable_management("IN_MEMORY", "mem_ratings")

        # Drop cokey and chkey if present
        allFields = [fld.name.lower() for fld in arcpy.Describe(initialTbl).fields]

        x = allFields.pop(-1)

        newField = dSDV["resultcolumnname"].lower()
        allFields.append(newField)
        queryFields = list()
        i = 0

        for fld in allFields:
            i += 1

            if not fld.lower() in queryFields:
                
                if fld == newField:
                    #PrintMsg("\tAdding last field " + fld + " to initialTbl as a " + dFieldInfo[fld][0], 1)
                    fldType, fldLen = dFieldInfo[fld.lower()]
                    
                    if fldType == "OID":
                        # Have to have OBJECTID field or the insert seems to fail
                        #fldSQL = fld + " " + fldTypes[fldType]
                        pass

                    else:
                        queryFields.append(fld.lower())

                    if fldType == "TEXT":
                        #fldSQL = fld + " " + fldTypes[fldType] + "(" + str(fldLen) + ")"
                        arcpy.AddField_management(memTbl, fld, fldType, "", "", fldLen)

                    else:
                        #fldSQL = fld + " " + fldTypes[fldType]
                        arcpy.AddField_management(memTbl, fld, fldType)

                else:
                    #PrintMsg("\tAdding field " + fld + " to initialTbl", 1)
                    fldType, fldLen = dFieldInfo[fld.lower()]

                    if fldType == "TEXT":
                        #fldSQL = fld + " " + fldTypes[fldType] + "(" + str(fldLen) + "),"
                        queryFields.append(fld.lower())
                        arcpy.AddField_management(memTbl, fld, fldType, "", "", fldLen)
                        
                    else:
                        #fldSQL = fld + " " + fldTypes[fldType] + ","
                        
                        if fldType != "OID":
                            arcpy.AddField_management(memTbl, fld, fldType)
                            queryFields.append(fld.lower())
            

        # Copy in_memory table to SQLite database
        arcpy.Copy_management(memTbl, os.path.join(gdb, outputTbl))
        del memTbl

        #PrintMsg(" \noutputTable query: " + queryCreateTable, 1)

        if arcpy.Exists(outputTbl):
            # Need to be careful here. Sometimes the tables I create using sqlite3 are not recognized by arcpy.
            return outputTbl

        else:
            raise MyError, "Failed to create output table"

    except MyError, e:
        PrintMsg(str(e), 2)
        return ""

    except:
        errorMsg()
        return ""

## ===================================================================================
def CreateSoilMoistureTable(tblList, sdvTbl, dComponent, dMonth, dTbl, initialTbl, begMo, endMo):
    # Create level 4 table (mapunit, component, cmonth, cosoilmoist)
    #
    # Problem 2017-07-24 Steve Campbell found Yolo County mapunits where dominant component,
    # Depth to Water Table map is reporting 201cm for 459272 where the correct result should be 91cm.
    # My guess is that because there are some months in cosoilmoist table that are Null, this function
    # is using that value instead of the other months that are 91cm. Try removing NULLs in query that
    # creates the sdv_data table.
    #
    try:
        arcpy.SetProgressorLabel("Saving all relevant data to a single query table")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg

        #
        # Read mapunit table and then populate the initial output table
        allFields.remove("lkey")

        with arcpy.da.SearchCursor("mapunit", dFields["mapunit"], sql_clause=dSQL["mapunit"]) as mCur:
            with arcpy.da.InsertCursor(initialTbl, allFields) as ocur:
                for rec in mCur:
                    mukey, musym, muname, lkey = rec

                    try:
                        newrec = list()
                        corecs = dComponent[mukey]

                        for corec in corecs:

                            try:
                                newrec = list()
                                morecs = dMonth[corec[0]]

                                for morec in morecs:
                                    try:
                                        sdvrecs = dTbl[morec[0]]

                                        for sdvrec in sdvrecs:
                                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                            newrec.extend(corec)
                                            newrec.extend(morec)
                                            newrec.extend(sdvrec)
                                            #PrintMsg("\t1. " + str(newrec), 1)
                                            ocur.insertRow(newrec)

                                    except:
                                        newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                        newrec.extend(corec)
                                        newrec.extend(morec)
                                        newrec.extend(dMissing[sdvTbl])
                                        #PrintMsg("\t2. " + str(newrec), 1)
                                        ocur.insertRow(newrec)

                            except:
                                # No comonth records
                                newrec = [dAreasymbols[lkey], mukey, musym, muname]
                                newrec.extend(corec)
                                newrec.extend(dMissing["comonth"])
                                newrec.extend(dMissing[sdvTbl])
                                #PrintMsg("\t3. " + str(newrec), 1)
                                ocur.insertRow(newrec)

                    except:
                        # No component records or comonth records
                        try:
                            newrec = [dAreasymbols[lkey], mukey, musym, muname]
                            newrec.extend(dMissing["component"])
                            newrec.extend(dMissing["comonth"])
                            newrec.extend(dMissing[sdvTbl])
                            #PrintMsg("\t4. " + str(newrec), 1)
                            ocur.insertRow(newrec)

                        except:
                            pass

        return True

    except MyError, e:
        PrintMsg(str(e), 2)
        return False

    except:
        errorMsg()
        return False

## ===================================================================================
def Aggregate1(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    # Aggregate map unit level table
    # Added Areasymbol to output
    try:
        arcpy.SetProgressorLabel("Assembling map unit level data")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Read mapunit table and populate final output table
        # Create final output table with mukey and sdvFld
        #
        # Is this using muaggatt table???
        # Having problem with sqlite database.
        # Soil Health - Available Water Capacity
        # Underlying DBMS error[UNIQUE constraint failed: sdv_awcSurf_dcp_0to50.mukey]
        # Not sure why that the 'Soil Health - Available Water Capacity' is coming here. This is a
        # horizon-level attribute. Please note that the dqmodeoptionflag=1 and the depthqualifiermode='Surface Layer'
        #
        #
        outputTbl = os.path.join(gdb, tblName)
        inFlds = ["mukey", "areasymbol", dSDV["attributecolumnname"].lower()]
        outFlds = ["mukey", "areasymbol", dSDV["resultcolumnname"].lower()]
        outputValues = list()
        #PrintMsg(" \nWriting mapunit rating information to " + tblName + ", using " + ", ".join(outFlds), 1)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        fldPrecision = max(0, dSDV["attributeprecision"])

        if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
            # populate sdv_initial table and create list of min-max values
            iMax = -999999999
            iMin = 999999999

            with arcpy.da.SearchCursor(initialTbl, inFlds) as cur:
                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, val = rec

                        if not val is None:
                            val = round(val, fldPrecision)

                        iMax = max(val, iMax)

                        if not val is None:
                            iMin = min(val, iMin)

                        rec = [mukey, areasym, val]
                        ocur.insertRow(rec)

            # add max and min values to list
            outputValues = [iMin, iMax]

            if iMin == None and iMax == -999999999:
                # No data
                #raise MyError, "No data for " + sdvAtt
                raise MyError, ""


        else:
            # populate sdv_initial table and create a list of unique values
            with arcpy.da.SearchCursor(initialTbl, inFlds) as cur:
                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, val = rec

                        if not val is None and not val in outputValues:
                            outputValues.append(val)

                        ocur.insertRow(rec)

        if len(outputValues) < 20 and bVerbose:
            PrintMsg(" \nInitial output values: " + str(outputValues), 1)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    # Aggregate mapunit-component data to the map unit level using dominant component
    # Added areasymbol to output
    try:
        #bVerbose = True
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        outputValues = list()

        inFlds = ["mukey", "areasymbol", "cokey", "comppct_r", dSDV["attributecolumnname"].lower()]
        outFlds = ["mukey", "areasymbol", "comppct_r", dSDV["resultcolumnname"].lower()]

        #PrintMsg(" \ntieBreaker in AggregateCo_DCD is: " + tieBreaker, 1)
        #PrintMsg(str(dSDV["tiebreaklowlabel"]) + "; " + str(dSDV["tiebreakhighlabel"]), 1)


        if tieBreaker == dSDV["tiebreaklowlabel"]:
            sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + " ASC ")
            #PrintMsg(" \nAscending sort on " + dSDV["attributecolumnname"], 1)

        else:
            sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + " DESC ")
            #PrintMsg(" \nDescending sort on " + dSDV["attributecolumnname"], 1)


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            raise MyError, "No output table"
            return outputTbl, outputValues

        lastMukey = "xxxx"

        # Reading numeric data from initial table
        #
        if dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
            #PrintMsg(" \nEffectiveLogicalDataType: " + dSDV["effectivelogicaldatatype"].lower(), 1)
            # populate sdv_initial table and create list of min-max values
            iMax = -999999999.0
            iMin = 999999999.0
            fldPrecision = max(0, dSDV["attributeprecision"])

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause) as cur:

                with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                    for rec in cur:
                        mukey, areasym, cokey, comppct, rating = rec

                        #if mukey != lastMukey and lastMukey != "xxxx":  # This was dropping first map unit!!!
                        if mukey != lastMukey:

                            if not rating is None:
                                #
                                newrec = mukey, areasym, comppct, round(rating, fldPrecision)

                            else:
                                newrec = mukey, areasym, comppct, None

                            ocur.insertRow(newrec)

                            if not rating is None:
                                iMax = max(rating, iMax)
                                iMin = min(rating, iMin)

                        lastMukey = mukey

            # add max and min values to list
            outputValues = [iMin, iMax]

        else:
            # For text, vtext or choice data types
            #
            #PrintMsg(" \ndValues: " + str(dValues), 1)
            #PrintMsg(" \noutputValues: " + str(outputValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause) as cur:

                if len(dValues) > 0:
                    # Text, has domain values or values in the maplegendxml
                    #
                    with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                        for rec in cur:

                            mukey, areasym, cokey, comppct, rating = rec

                            if mukey != lastMukey:

                                #if not rating is None:
                                if str(rating).upper() in dValues:
                                    if dValues[rating.upper()][1] != rating: # we have a case problem in the maplegendxml
                                        # switch the dValue to lowercase to match the data
                                        dValues[str(rating).upper()][1] = rating

                                    newrec = [mukey, areasym, comppct, rating]

                                elif not rating is None:

                                    dValues[str(rating).upper()] = [None, rating]
                                    newrec = [mukey, areasym, comppct, rating]

                                else:
                                    newrec = [mukey, areasym, None, None]

                                if not rating in outputValues and not rating is None:
                                    outputValues.append(rating)

                                ocur.insertRow(newrec)
                                #PrintMsg(str(rec), 1)

                            lastMukey = mukey

                else:
                    # Text, without domain values
                    #
                    with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                        for rec in cur:
                            mukey, areasym, cokey, comppct, rating = rec

                            if mukey != lastMukey:
                                if not rating is None:
                                    newVal = rating.strip()

                                else:
                                    newVal = None

                                ocur.insertRow([mukey, areasym, comppct, newVal])


                                if not newVal is None and not newVal in outputValues:
                                    outputValues.append(newVal)

                            #else:
                            #    PrintMsg("\tSkipping " + str(rec), 1)

                            lastMukey = mukey


        #if None in outputValues:
        #    outputValues.remove(None)

        if outputValues[0] == -999999999.0 or outputValues[1] == 999999999.0:
            # Sometimes no data can skip through the max min test
            outputValues = [0.0, 0.0]
            raise MyError, "No data for " + sdvAtt

        #if (bZero and outputValues ==  [0.0, 0.0]):
        #    PrintMsg(" \nNo data for " + sdvAtt, 1)

        # Trying to handle NCCPI for dominant component
        if dSDV["attributetype"].lower() == "interpretation" and (dSDV["nasisrulename"][0:5] == "NCCPI"):
            outputValues = [0.0, 1.0]

        if dSDV["effectivelogicaldatatype"].lower() in ("float", "integer"):
            outputValues.sort()
            return outputTbl, outputValues

        else:
            return outputTbl, sorted(outputValues, key=lambda s: s.lower())

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Limiting(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Select either the "Least Limiting" or "Most Limiting" rating from all components
    # Component aggregation to the maximum or minimum value for the mapunit.

    # Based upon AggregateCo_DCD function, but sorted on rating or domain value instead of comppct
    #
    # domain: soil_erodibility_factor (text)  range = .02 .. .64
    # Added Areasymbol to output

    # Note! I have some dead code for 'no domain values'. Need to delete if those sections are never used.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg(" \nEffective Logical data type: " + dSDV["effectivelogicaldatatype"], 1)
            PrintMsg(" \nAttribute type: " + dSDV["attributetype"] + "; bFuzzy " + str(bFuzzy), 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "areasymbol", "cokey", "comppct_r", dSDV["attributecolumnname"].lower()]
        outFlds = ["mukey", "areasymbol", "comppct_r", dSDV["resultcolumnname"].lower()]

        # ignore any null values
        whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        #
        sqlClause =  (None, " ORDER BY mukey ASC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        if not dSDV["notratedphrase"] is None:
            # This should be for most interpretations
            notRatedIndex = domainValues.index(dSDV["notratedphrase"])

        else:
            # set notRatedIndex for properties that are not interpretations
            notRatedIndex = -1

        # 1. For ratings that have domain values, read data from initial table
        #
        if len(domainValues) > 0:
            #PrintMsg(" \ndValues: " + str(dValues), 1)

            # Save the rating for each component along with a list of components for each mapunit
            #
            try:
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    # inFlds: 0 mukey, 1 cokey, 2 comppct, 3 rating

                    for rec in cur:
                        #PrintMsg(str(rec), 1)
                        mukey, areasym, cokey, comppct, rating = rec
                        dAreasym[mukey] = areasym

                        # Save the associated domain index for this rating
                        dComp[cokey] = dValues[str(rating).upper()][0]

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit using mukey as key
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        #PrintMsg("Component '" + rec[1] + "' at " + str(rec[2]) + "% has a rating of: " + str(rec[3]), 1)

            except:
                errorMsg()

        else:
            # 2. No Domain Values, read data from initial table. Use alpha sort for tiebreaker
            #
            raise MyError, "No Domain values"


        # Write aggregated data to output table

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if dSDV["algorithmname"] == "Least Limiting":
                #
                # Need to take a closer look at how 'Not rated' components are handled in 'Least Limiting'
                #
                if domainValues:

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        muVals = list()    # may not need this for DCD
                        #maxIndx = 0        # Initialize index as zero ('Not rated')
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            indexes.append(ratingIndx)
                            #PrintMsg("\t\t" + mukey + ": " + cokey + " - " + str(ratingIndx) + ",  " + domainValues[ratingIndx], 1)

                            if ratingIndx in dRating:
                                 dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        # Use the highest index value to assign the map unit rating
                        indexes = sorted(set(indexes), reverse=True)
                        maxIndx = indexes[0]  # get the lowest index value

                        if maxIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            maxIndx = indexes[1]

                        pct = dRating[maxIndx]
                        rating = domainValues[maxIndx]
                        areasym = dAreasym[mukey]
                        newrec = [mukey, areasym, pct, rating]
                        ocur.insertRow(newrec)
                        #PrintMsg("\tMapunit rating: " + str(indexes) + "; " + str(maxIndx) + "; " + rating + " \n ", 1)

                        if not rating is None and not rating in outputValues:
                            outputValues.append(rating)

                else:
                    # Least Limiting, no domain values
                    #
                    raise MyError, "No domain values"


            elif dSDV["algorithmname"]== "Most Limiting":
                #
                # with domain values...
                #
                # Need to take a closer look at how 'Not rated' components are handled in 'Most Limiting'
                #
                if len(domainValues) > 0:
                    #
                    # Most Limiting, has domain values
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes))
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)

                        if not domainValues[minIndx] is None and not domainValues[minIndx] in outputValues:
                            outputValues.append(domainValues[minIndx])

                else:
                    #
                    # Most Limiting, no domain values
                    raise MyError, "No domain values"

                    #PrintMsg(" \nTesting " + aggMethod + ", no domain values!!!", 1)
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            ratingIndx = dComp[cokey]  # component rating

                            if ratingIndx != 0:
                                if ratingIndx in dRating:
                                    dRating[ratingIndx] = dRating[ratingIndx] + compPct

                                else:
                                    dRating[ratingIndx] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)
                            #PrintMsg("\t" + mukey + ": " + ",  " + str(muVals), 1)

                        if not newrec[2] is None and not newrec[2] in outputValues:
                            outputValues.append(newrec[2])

                # End of Lower

        outputValues.sort()

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_MaxMin(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    #
    # Looks at all components and returns the lowest or highest rating value. This
    # may be based upon the actual value or the index (for those properties with domains).
    #
    # "Minimum or Maximum" method of aggregation uses the tiebreak setting
    # and returns the highest or lowest rating accordingly.

    # "Least Limiting", "Most Limiting"
    # Component aggregation to the maximum or minimum value for the mapunit.
    #
    # dSDV["tiebreakrule"]: -1, 1 originally in sdvattribute table
    #
    # If tieBreak value == "lower" return the minimum value for the mapunit
    # Else return "Higher" value for the mapunit
    #
    # Based upon AggregateCo_DCD function, but sorted on rating or domain value instead of comppct
    #
    # domain: soil_erodibility_factor (text)  range = .02 .. .64
    # Added Areasymbol to output

    try:
        #bVerbose = True

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
            PrintMsg(" \nEffective Logical data type: " + dSDV["effectivelogicaldatatype"], 1)
            PrintMsg(" \nAttribute type: " + dSDV["attributetype"] + "; bFuzzy " + str(bFuzzy), 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "areasymbol", "cokey", "comppct_r", dSDV["attributecolumnname"].lower()]
        outFlds = ["mukey", "areasymbol", "comppct_r", dSDV["resultcolumnname"].lower()]

        # ignore any null values
        whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attributecolumn when it will be replaced by Domain values later?
        #
        if tieBreaker == dSDV["tiebreaklowlabel"]:
            sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + " ASC ")

        else:
            sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + " DESC ")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        if not dSDV["notratedphrase"] is None:
            # This should work for most interpretations
            if dSDV["notratedphrase"] in domainValues:
                notRatedIndex = domainValues.index(dSDV["notratedphrase"])

            else:
                notRatedIndex = -1

        else:
            # set notRatedIndex for properties that are not interpretations
            notRatedIndex = -1

        #
        # Begin component level processing. Branch according to whether values are members of a domain.
        #
        if len(domainValues) > 0:
            # Save the rating for each component along with a list of components for each mapunit
            #
            # PrintMsg(" \ndomainValues for " + sdvAtt + ": " + str(domainValues), 1)

            try:
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    # inFlds: 0 mukey, 1 cokey, 2 comppct, 3 rating

                    for rec in cur:
                        #PrintMsg(str(rec), 1)
                        mukey, areasym, cokey, comppct, rating = rec
                        dAreasym[mukey] = areasym

                        # Save the associated domain index for this rating
                        dComp[cokey] = dValues[str(rating).upper()][0]

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit using mukey as key
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        #PrintMsg("Component '" + rec[1] + "' at " + str(rec[2]) + "% has a rating of: " + str(rec[3]), 1)

            except:
                errorMsg()

        else:
            # 2. No Domain Values, read data from initial table. Use alpha sort for tiebreaker.
            #
            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    mukey, areasym, cokey, comppct, rating = rec
                    dAreasym[mukey] = areasym
                    # Assume that this is the first rating for the component
                    dComp[cokey] = rating

                    # save component percent for each component
                    dCompPct[cokey] = comppct

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        # End of component level processing
        #


        #
        # Begin process of writing mapunit-aggregated data to output table
        # Branch according to aggregation method and tiebreak settings and whether ratings are members of a domain
        #
        if bVerbose:
            PrintMsg(" \nTieBreaker: " + str(tieBreaker), 1)
            #PrintMsg("Tiebreak high label: " + str(dSDV["tiebreakhighlabel"]), 1)
            #PrintMsg("Tiebreak low label: " + str(dSDV["tiebreaklowlabel"]), 1)
            PrintMsg("Tiebreak Rule: " + str(dSDV["tiebreakrule"]), 1)
            PrintMsg("domainValues: " + str(domainValues), 1)
            PrintMsg("notRatedIndex: " + str(notRatedIndex), 1)

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            #
            # Begin Minimum or Maximum
            #
            if aggMethod == "Minimum or Maximum" and tieBreaker == dSDV["tiebreaklowlabel"]:
                #
                # MIN
                #
                if len(domainValues) > 0:
                    #
                    # MIN
                    # Has Domain
                    #
                    #PrintMsg(" \nThis option has domain values for MinMax!", 1) example WEI MaxMin

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes), reverse=False)
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)
                        #PrintMsg("\tPessimistic 3 Mapunit rating: " + str(indexes) + ", " + str(minIndx) + ", " + str(domainValues[minIndx]) + " \n ", 1)

                        if not domainValues[minIndx] is None and not domainValues[minIndx] in outputValues:
                            outputValues.append(domainValues[minIndx])

                else:
                    #
                    # MIN
                    # No domain
                    #
                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            rating = dComp[cokey]  # component rating

                            #if rating != 0:
                            if rating in dRating:
                                dRating[rating] = dRating[rating] + compPct

                            else:
                                dRating[rating] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals, 1, 0, False, True)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)

                            #if mukey == '2774629':
                            #    #PrintMsg("\t" + mukey + ": " + str(muVal) + " <- " + str(muVals), 1)
                            #    PrintMsg("\tThis mapunit " + mukey + " is rated: " + str(muVal[1]) + " <- " + str(muVals), 1)

                        if not muVal[1] is None and not muVal[1] in outputValues:
                            outputValues.append(muVal[1])

                # End of Lower

            elif aggMethod == "Minimum or Maximum" and tieBreaker == dSDV["tiebreakhighlabel"]:
                #
                # MAX
                #
                if len(domainValues) > 0:
                    #
                    # MAX
                    # Has Domain
                    #
                    #PrintMsg(" \nThis option has domain values for MinMax!", 1)

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()   # save sum of comppct for each rating within a mapunit
                        minIndx = 9999999  # save the lowest index value for each mapunit
                        indexes = list()

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # get comppct_r for this component
                            ratingIndx = dComp[cokey]  # get rating index for this component
                            indexes.append(ratingIndx)

                            # save the sum of comppct_r for each rating index in the dRating dictionary
                            if ratingIndx in dRating:
                                dRating[ratingIndx] = dRating[ratingIndx] + compPct

                            else:
                                dRating[ratingIndx] = compPct

                        indexes = sorted(set(indexes), reverse=True)
                        minIndx = indexes[0]  # get the lowest index value

                        if minIndx == notRatedIndex and len(indexes) > 1:
                            # if the lowest index is for 'Not rated', try to get the next higher index
                            minIndx = indexes[1]

                        newrec = [mukey, dAreasym[mukey], dRating[minIndx], domainValues[minIndx]]
                        #PrintMsg("\t" + mukey + ": " + " - " + str(minIndx) + ",  " + domainValues[minIndx], 1)
                        ocur.insertRow(newrec)
                        #PrintMsg("\tOptimistic 3 Mapunit rating: " + str(indexes) + ", " + str(minIndx) + ", " + str(domainValues[minIndx]) + " \n ", 1)

                        if not not domainValues[minIndx] is None and not domainValues[minIndx] in outputValues:
                            outputValues.append(domainValues[minIndx])

                else:
                    #raise MyError, "Should not be in this section of code"

                    #PrintMsg(" \nTesting " + aggMethod + " - " + tieBreaker + ", no domain values", 1)
                    #
                    # MAX
                    # No Domain

                    for mukey, cokeys in dMapunit.items():
                        dRating = dict()  # save sum of comppct for each rating within a mapunit
                        muVals = list()   # list of rating values for each mapunit

                        for cokey in cokeys:
                            compPct = dCompPct[cokey]  # component percent
                            rating = dComp[cokey]  # component rating

                            #if rating != 0:
                            if rating in dRating:
                                dRating[rating] = dRating[rating] + compPct

                            else:
                                dRating[rating] = compPct

                        for rating, compPct in dRating.items():
                            muVals.append([compPct, rating])

                        if len(muVals) > 0:
                            muVal = SortData(muVals, 1, 0, True, True)

                            newrec = [mukey, dAreasym[mukey], muVal[0], muVal[1]]
                            ocur.insertRow(newrec)
                            # muVal[0] is comppct, muVal[1] is rating
                            # PrintMsg("\tThis mapunit " + mukey + " is rated: " + str(muVal[1]) + " <- " + str(muVals), 1)

                        if not muVal[1] is None and not muVal[1] in outputValues:
                            outputValues.append(muVal[1])

                # End of Higher


        outputValues.sort()

        if bVerbose:
            PrintMsg(" \noutputValues: " + str(outputValues), 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCD(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    #
    # Component aggregation to the dominant condition for the mapunit.
    #
    # Need to remove references to domain values for rating
    #
    # Need to figure out how to handle tiebreaker code for Random values (no index for ratings)
    # Added areasymbol to output
    try:
        #bVerbose = True
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        # Keep any null values as part of the aggregation
        if bNulls:
            # Default setting
            whereClause = "comppct_r >=  " + str(cutOff)

        else:
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        if bVerbose:
            PrintMsg(" \nwhereClause: " + whereClause, 1)

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        #PrintMsg(" \nMap legend key: " + str(dSDV["maplegendkey"]), 1)
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        dAreasym = dict()

        # 1 Read initial table (ratings have domain values and can be ranked)
        #

        #PrintMsg(" \nAdding NONE to domainValues in AggregateCo_DCD", 1)

        if len(dValues) and not dSDV["tiebreakdomainname"] is None:
            if bNulls and not "NONE" in dValues:
                # Add Null value to domain
                dValues["NONE"] = [[len(dValues), None]]
                domainValues.append("NONE")

                if bVerbose:
                    PrintMsg(" \nDomain Values: " + str(domainValues), 1)
                    PrintMsg("dValues: " + str(dValues), 1)
                    PrintMsg("data type: " + dSDV["effectivelogicaldatatype"].lower(), 1 )

            # PrintMsg("dValues: " + str(dValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                # Use tiebreak rules and rating index values

                for rec in cur:
                    # read raw data from initial table
                    mukey, cokey, comppct, rating, areasym = rec
                    dRating = dict()

                    # get index for this rating
                    ratingIndx = dValues[str(rating).upper()][0]

                    if mukey == '397784':
                        PrintMsg("\t" + str(rec), 1)

                    dComp[cokey] = ratingIndx
                    dCompPct[cokey] = comppct
                    dAreasym[mukey] = areasym

                    # summarize the comppct for this rating and map unit combination
                    try:
                        dRating[ratingIndx] += comppct
                        #comppct = dRating[ratingIndx]

                    except:
                        dRating[ratingIndx] = comppct

                    # Not sure what I am doing here???
                    try:
                        #dMapunit[mukey][ratingIndx] = dRating[ratingIndx]
                        dMapunit[mukey].append(cokey)

                    except:
                        #dMapunit[mukey].append(ratingIndx)
                        dMapunit[mukey] = [cokey]

        else:
            # No domain values
            # 2 Read initial table (no domain values, must use alpha sort for tiebreaker)
            # Issue noted by ?? that without tiebreaking method, inconsistent results may occur
            #
            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                #
                # numeric values
                if dSDV["effectivelogicaldatatype"].lower() in ['integer', 'float']:
                    fldPrecision = max(0, dSDV["attributeprecision"])

                    for rec in cur:
                        mukey, cokey, comppct, rating, areasym = rec
                        # Assume that this is the rating for the component
                        # PrintMsg("\t" + str(rec[1]) + ": " + str(rec[3]), 1)
                        dComp[cokey] = rating
                        dAreasym[mukey] = areasym

                        # save component percent for each component
                        dCompPct[cokey] = comppct

                        # save list of components for each mapunit
                        # key value is mukey; dictionary value is a list of cokeys
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                else:
                    #
                    # choice, text, vtext values
                    for rec in cur:
                        # Assume that this is the rating for the component
                        #PrintMsg("\t" + str(rec[1]) + ": " + str(rec[3]), 1)
                        mukey, cokey, comppct, rating, areasym = rec
                        if not rating is None:
                            dComp[cokey] = rating.strip()

                        else:
                            dComp[cokey] = None

                        # save component percent for each component
                        dCompPct[cokey] = comppct
                        dAreasym[mukey] = areasym

                        # save list of components for each mapunit
                        # key value is mukey; dictionary value is a list of cokeys
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

        # Aggregate component-level data to the map unit
        #
        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if tieBreaker == dSDV["tiebreaklowlabel"]:
                #
                # No domain values, Lower
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    areasym = dAreasym[mukey]

                    for cokey in cokeys:
                        compPct = dCompPct[cokey]
                        rating = dComp[cokey]

                        if rating in dRating:
                            sumPct = dRating[rating] + compPct
                            dRating[rating] = sumPct  # this part could be compacted

                        else:
                            dRating[rating] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    muVal = SortData(muVals, 0, 1, True, False)  # switched from True, False

                    newrec = [mukey, muVal[0], muVal[1], areasym]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])

            elif tieBreaker == dSDV["tiebreakhighlabel"]:
                #
                # No domain values, Higher
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    areasym = dAreasym[mukey]

                    for cokey in cokeys:
                        compPct = dCompPct[cokey]
                        rating = dComp[cokey]

                        if rating in dRating:
                            sumPct = dRating[rating] + compPct
                            dRating[rating] = sumPct  # this part could be compacted

                        else:
                            dRating[rating] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    muVal = SortData(muVals, 0, 1, True, True)  # switched from True, True
                    newrec = [mukey, muVal[0], muVal[1], areasym]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])

            else:
                # fails on T Factor, etc. tiebreakruleoptionflag=1, tiebreakrule=-1, no tie labels.
                # tiebreakrule: 1 (select higher value); -1 (select the lower value)
                #
                # tiebreakruleoptionflag controls whether user can change the tiebreakrule option
                #
                PrintMsg(" \ntieBreaker value is: " + str(tieBreaker), 1)
                raise MyError, "Failed to aggregate map unit data"

        outputValues.sort()

        #if (bZero and outputValues ==  [0.0, 0.0]):
            #PrintMsg(" \nNo data for " + sdvAtt, 1)

        # Problem with integer or float data below

        if dSDV["effectivelogicaldatatype"].lower() in ['integer', 'float']:

            for rating in outputValues:
                #PrintMsg(" \ndValues for " + rating.upper() + ": " + str(dValues[rating.upper()][1]), 1)

                if rating in dValues:
                    # rating is in dValues but case is wrong
                    # fix dValues value
                    #PrintMsg("\tChanging dValue rating to: " + rating, 1)
                    dValues[rating][1] = rating

        else:
            for rating in outputValues:
                #PrintMsg(" \ndValues for " + rating.upper() + ": " + str(dValues[rating.upper()][1]), 1)

                if rating.upper() in dValues and dValues[rating.upper()][1] != rating:
                    # rating is in dValues but case is wrong
                    # fix dValues value
                    #PrintMsg("\tChanging dValue rating to: " + rating, 1)
                    dValues[rating.upper()][1] = rating


        #PrintMsg(" \ndValues (after) in AggregateCo_DCD: " + str(dValues), 1)

        if dSDV["effectivelogicaldatatype"].lower() in ["float", "integer"]:
            return outputTbl, outputValues

        else:
            return outputTbl, sorted(outputValues, key=lambda s: s.lower())

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP_DTWT(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Depth to Water Table, dominant component
    #
    # Aggregate mapunit-component data to the map unit level using dominant component
    # and the tie breaker setting to select the lowest or highest monthly rating.
    # Use this for comonth table. domainValues
    #
    # PROBLEMS with picking the correct depth for each component. Use tiebreaker to pick
    # highest or lowest month and then aggregate to DCP?
    # Added areasymbol to output
    #
    # Currently 2019-03-21 I'm only returning data where there is a water table for the
    # dominant component. The rest of the polygons are not displayed or symbolized.
    #

    try:

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Get null replacement value from dSDV
        nullValue = dSDV["nullratingreplacementvalue"]
        PrintMsg(" \nNULL replacement value: " + str(nullValue), 1)
        
        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        inFlds = ["mukey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dAreasym = dict()
        dataCnt = int(arcpy.GetCount_management(initialTbl).getOutput(0))

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # "mukey", "comppct_r", attribcolumn
            for rec in cur:
                arcpy.SetProgressorPosition()
                mukey, compPct, rating, areasym = rec
                dAreasym[mukey] = areasym

                try:
                    dMapunit[mukey].append([compPct, rating])

                except:
                    dMapunit[mukey] = [[compPct, rating]]

        del initialTbl  # Trying to save some memory 2016-06-23

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            #PrintMsg(" \nWriting to output table " + outputTbl + "...", 1)
            #PrintMsg("\t" + ", ".join(outFlds), 0)

            
            #arcpy.SetProgressor("step", "Writing to output table (" + os.path.basename(outputTbl) + ")", 0, len(dMapunit), 1 )

            for mukey, coVals in dMapunit.items():
                arcpy.SetProgressorPosition()
                # Grab the first pair of values (pct, depth) from the sorted list.
                # This is the dominant component rating using tie breaker setting
                dcpRating = SortData(coVals, 0, 1, True, False)  # For depth to water table, we want the lower value (closer to surface)
                
                if dcpRating[1] is None:
                    # Replace null value with 201
                    dcpRating[1] = nullValue
                    
                rec =[mukey, dcpRating[0], dcpRating[1], dAreasym[mukey]]
                ocur.insertRow(rec)
                #PrintMsg("\t" + str(rec), 1)

                if  not rec[2] is None and not rec[2] in outputValues:
                    outputValues.append(rec[2])

        #arcpy.ResetProgressor()
        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCD_DTWT(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Not being used???
    #
    # Aggregate mapunit-component-comonth data to the map unit level using dominant condition
    # and the tie breaker setting to select the lowest or highest monthly rating.
    # Use this for comonth table. domainValues
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # mukey,cokey , comppct_r, attribcolumn
            for rec in cur:
                mukey, cokey, compPct, rating, areasym = rec

                if rating is None:
                    rating = nullRating

                dAreasym[mukey] = areasym

                # Save list of cokeys for each mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            for cokey, coVals in dComponent.items():
                # Find high or low value for each component
                dCoRating[cokey] = max(coVals[1])

        else:
            for cokey, coVals in dComponent.items():
                # Find high or low value for each component
                dCoRating[cokey] = min(coVals[1])


        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                rating = dCoRating[cokey]
                compPct = dComponent[cokey][0]

                try:
                    dMuRatings[rating] += compPct

                except:
                    dMuRatings[rating] = compPct

            for rating, compPct in dMuRatings.items():
                # Find rating with highest sum of comppct
                if compPct > domPct:
                    domPct = compPct
                    dFinalRatings[mukey] = [compPct, rating]
                    #PrintMsg("\t" + mukey + ", " + str(compPct) + "%" + ", " + str(rating) + "cm", 1)

            del dMuRatings

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey, vals in dFinalRatings.items():
                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not rec[2] is None and not rec[2] in outputValues:
                    outputValues.append(rec[2])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_MaxMin(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Aggregate mapunit-component data to the map unit level using Minimum or Maximum
    # based upon the TieBreak rule.
    # Use this for comonth table. Example Depth to Water Table.
    #
    # It appears that WSS includes 0 percent components in the MinMax. This function
    # is currently set to duplicate this behavior
    # Added areasymbol to output
    #
    # Seems to be a problem with TitleCase Values in maplegendxml vs. SentenceCase in the original data. Domain values are SentenceCase.
    #

    try:
        #
        #bVerbose = True

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try later to substitute dSDV["nullratingreplacementvalue"]
        #whereClause = "comppct_r >=  " + str(cutOff) + " and not " + dSDV["attributecolumnname"].lower() + " is null"
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # mukey,cokey , comppct_r, attribcolumn
            for rec in cur:

                mukey, cokey, compPct, rating, areasym = rec
                dAreasym[mukey] = areasym
                #PrintMsg("\t" + str(rec), 1)


                # Save list of cokeys for each mapunit-mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # This is working correctly for DTWT
            # Backwards for Ponding

            # Identify highest value for each component
            for cokey, coVals in dComponent.items():
                # Find high value for each component
                #PrintMsg("Higher values for " + cokey + ": " + str(coVals) + " = " + str(max(coVals[1])), 1)
                dCoRating[cokey] = max(coVals[1])

        else:
            # This is working correctly for DTWT
            # Backwards for Ponding

            # Identify lowest value for each component
            for cokey, coVals in dComponent.items():
                # Find low rating value for each component
                #PrintMsg("Lower values for " + cokey + ": " + str(coVals) + " = " + str(min(coVals[1])), 1)
                dCoRating[cokey] = min(coVals[1])


        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                try:
                    rating = dCoRating[cokey]
                    compPct = dComponent[cokey][0]

                    try:
                        dMuRatings[rating] += compPct

                    except:
                        dMuRatings[rating] = compPct

                except:
                    pass

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # This is working correctly for DTWT
                # Backwards for Ponding
                highRating = 0

                for rating, compPct in dMuRatings.items():
                    # Find the highest
                    if rating > highRating:
                        highRating = rating
                        dFinalRatings[mukey] = [compPct, rating]
            else:
                # This is working correctly for DTWT
                # Backwards for Ponding
                lowRating = nullRating

                for rating, compPct in dMuRatings.items():

                    if rating < lowRating and rating is not None:
                        lowRating = rating
                        dFinalRatings[mukey] = [compPct, rating]

            del dMuRatings

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dMapunit):

                try:
                    vals = dFinalRatings[mukey]

                except:
                    sumPct = 0
                    for cokey in dMapunit[mukey]:
                        try:
                            sumPct += dComponent[cokey][0]

                        except:
                            pass

                    vals = [sumPct, nullRating]

                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not rec[2] is None and not rec[2] in outputValues:
                    outputValues.append(rec[2])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_Mo_DCD(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Aggregate mapunit-component data to the map unit level using the dominant condition
    # based upon the TieBreak rule.
    # Use this for comonth table. Example Depth to Water Table.
    #
    # It appears that WSS includes 0 percent components in the MinMax. This function
    # is currently set to duplicate this behavior
    #
    # Currently there is a problem with the comppct. It ends up being 12X.

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try to substitute dSDV["nullratingreplacementvalue"]
        #whereClause = "comppct_r >=  " + str(cutOff) + " and not " + dSDV["attributecolumnname"].lower() + " is null"
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # mukey,cokey , comppct_r, attribcolumn
            for rec in cur:
                #mukey = rec[0]; cokey = rec[1]; compPct = rec[2]; rating = rec[3]
                mukey, cokey, compPct, rating, areasym = rec
                if rating is None:
                    rating = 201

                # Save list of cokeys for each mapunit-mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]
                    dAreasym[mukey] = areasym
                    PrintMsg(" \nCheck dAreasymbols setting", 1)

                try:
                    # if the rating value meets the tiebreak rule, save the rating value along with comppct for each component
                    #if not rating is None:
                    if tieBreaker == dSDV["tiebreakhighlabel"]:
                        if rating > dComponent[cokey][1]:
                            dComponent[cokey][1] = rating

                    elif rating < dComponent[cokey][1]:
                        dComponent[cokey][1] = rating

                except:
                    #  Save rating value along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, rating]

        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            dMuRatings = dict()
            dMuRatings[mukey] = [None, None]  # create a dictionary of values for just this map unit
            domPct = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                if cokey in dComponent:

                    compPct, rating = dComponent[cokey]

                    if compPct > domPct:
                        domPct = compPct
                        dMuRatings[mukey] = [compPct, rating]
                        #PrintMsg("\t" + mukey + ":" + cokey  + ", " + str(compPct) + "%, " + str(rating), 1)

            dFinalRatings[mukey] = dMuRatings[mukey]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dFinalRatings):
                compPct, rating = dFinalRatings[mukey]
                rec = mukey, compPct, rating, dAreasym[mukey]
                ocur.insertRow(rec)

                if not rating is None and not rating in outputValues:
                    outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_DCP_Domain(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Use this function for Flooding or Ponding Frequency which involves the comonth table
    #
    # Need to modify this so that comppct_r is summed using just one value per component, not 12X.
    #
    # We have a case problem with Flooding Frequency Class: 'Very frequent'
    #
    # My tests on ND035 appear to return results based upon dominant condition, not dominant component!
    #

    try:
        # bVerbose = True
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dCase = dict()
        dAreasym = dict()

        # Read initial table for non-numeric data types
        # 02-03-2016 Try adding 'choice' to this method to see if it handles Cons. Tree/Shrub better
        # than the next method. Nope, did not work. Still have case problems.
        #
        if dSDV["attributelogicaldatatype"].lower() == "string":
            PrintMsg(" \n*dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    rating = rec[3]

                    try:
                        # capture component ratings as index numbers instead.
                        dComp[rec[1]].append(dValues[rating.upper()][0])

                    except:
                        dComp[rec[1]] = [dValues[rating.upper()][0]]
                        dCompPct[rec[1]] = rec[2]
                        dCase[rating.upper()] = rating  # save original value using uppercase key


                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        elif dSDV["attributelogicaldatatype"].lower() in ["float", "integer", "choice"]:

            PrintMsg(" \n**dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    rating = rec[3]

                    try:
                        # capture component ratings as index numbers instead
                        if rating is None:
                            dComp[rec[1]].append(dValues["<Null>"][0])

                        else:
                            dComp[rec[1]].append(dValues[rating.upper()][0])

                    except:
                        #PrintMsg(" \ndomainValues is empty, but legendValues has " + str(legendValues), 1)
                        dCase[rating.upper()] = rating

                        if rating.upper() in dValues:
                            dComp[rec[1]] = [dValues[rating.upper()][0]]
                            dCompPct[rec[1]] = rec[2]

                            # compare actual rating value to domainValues to make sure case is correct
                            if not rating in domainValues: # this is a case problem
                                # replace the original dValue item
                                dValues[rating.upper()][1] = rating

                                # replace the value in domainValues list
                                for i in range(len(domainValues)):
                                    if domainValues[i].upper() == rating.upper():
                                        domainValues[i] = rating

                        else:
                            # dValues is keyed on uppercase string rating
                            #
                            if not rating in missingDomain:
                                # Try to add missing value to dDomainValues dict and domainValues list
                                dValues[rating.upper()] = [len(dValues), rating]
                                #domainValues.append(rating])
                                #domainValuesUp.append(rating.upper()
                                #missingDomain.append(rating)
                                PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        else:
            PrintMsg(" \nProblem with handling domain values of type '" + dSDV["attributelogicaldatatype"] + "'", 1)


        # Aggregate monthly index values to a single value for each component
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        #
        # Testing on 2017-11-07 shows that I'm ending up with lower ratings when tiebreak is set High
        #PrintMsg(" \nNot sure about this sorting code for tiebreaker", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # "Higher" (default for flooding and ponding frequency)
            #PrintMsg(" \nTiebreak High: " + dSDV["tiebreakhighlabel"], 1)
            for cokey, indexes in dComp.items():
                val = sorted(indexes, reverse=True)[0]  #original that does not work
                #val = sorted(indexes, reverse=False)[0]  #test 1
                dComp[cokey] = val
        else:
            #PrintMsg(" \nTiebreak low: " + dSDV["tiebreaklowlabel"], 1)
            for cokey, indexes in dComp.items():
                val = sorted(indexes)[0]
                dComp[cokey] = val

        # Save list of component data to each mapunit
        dRatings = dict()

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # Default for flooding and ponding frequency
                #
                #PrintMsg(" \ndomainValues: " + str(domainValues), 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        #PrintMsg("\tB ratingIndx: " + str(dComp[cokey]), 1)
                        compPct = dCompPct[cokey]
                        ratingIndx = dComp[cokey]
                        muVals.append([compPct, ratingIndx])

                        # I think this section of code is in effect doing a dominant condition
                        # Fixed 2017-11-07
                        #if ratingIndx in dRating:
                        #    sumPct = dRating[ratingIndx] + compPct
                        #    dRating[ratingIndx] = sumPct  # this part could be compacted

                        #else:
                        #    dRating[ratingIndx] = compPct

                        # End of bad code

                    #for rating, compPct in dRating.items():
                    #    muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], x[1]))[0]  # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=True)[0]

                    muVal = SortData(muVals, 0, 1, True, True)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if  not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])

            else:
                # Lower
                PrintMsg(" \nFinal lower tiebreaker", 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            muVals.append([compPct, ratingIndx])

                        except:
                            pass

                    muVal = SortData(muVals, 0, 1, True, False)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])


        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_Mo_DCD_Domain(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Flooding or ponding frequency, dominant condition
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition.
    # Use domain values to determine sort order for tiebreaker
    #
    # Need to modify this function to correctly sum the comppct_r for the final output table.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        #bVerbose = False

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        if bNulls:
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            whereClause = "comppct_r >=  " + str(cutOff)

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dAreasym = dict()
        #dCase = dict()

        # Read initial table for non-numeric soil properties. Capture domain values and all component ratings.
        #
        if not dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:  # Changed here 2016-04-28
            #
            # No domain values for non-interp string ratings
            # !!! Probably never using this section of code.
            #
            if bVerbose:
                PrintMsg((40 * '*'), 1)
                PrintMsg(" \n*dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg("domainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)
                PrintMsg((40 * '*'), 1)



            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                if bVerbose:
                    PrintMsg(" \nReading initial data...", 1)

                for rec in cur:
                    # "mukey", "cokey", "comppct_r", RATING
                    mukey, cokey, compPct, rating, areasym = rec
                    dAreasym[mukey] = areasym
                    dComp[cokey] = rating
                    dCompPct[cokey] = compPct
                    #dCase[str(rating).upper()] = rating  # save original value using uppercase key

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        elif dSDV["attributelogicaldatatype"].lower() in ["string", "float", "integer", "choice"]:
            # Interp or numeric soil properties
            # Flooding and Ponding would fall in this section

            if len(domainValues) > 1 and not "None" in domainValues:
                PrintMsg(" \n******************* Immedidately adding 'None' to dValues ****************" , 1)
                dValues["<Null>"] = [len(dValues), None]
                #domainValues.append("None")

            if bVerbose:
                PrintMsg(" \n**domainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues) + " \n ", 1)
                PrintMsg(" \n**dValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)


            if  dSDV["tiebreakdomainname"] is None:
                # There are no domain values. We must make sure that the legend values are the same as
                # the output values.
                #
                PrintMsg(" \nNo domain name for this property", 1)

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    if bVerbose:
                        PrintMsg(" \nReading initial data...", 1)

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "mukey", "cokey", "comppct_r", RATING
                        #PrintMsg("\t" + str(rec), 1)
                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:

                            if not rating is None:
                                dCase[str(rating).upper()] = rating

                                if str(rating).upper() in dValues:
                                    #if mukey == '2780145':
                                    #    PrintMsg("\t*Target mapunit rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)

                                    dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                    #dComp[cokey] = rating
                                    dValues[str(rating).upper()][1] = rating
                                    dCompPct[cokey] = compPct

                                    # compare actual rating value to domainValues to make sure case is correct
                                    #
                                    # This does not make sense. domainValues must be coming from maplegendxml.
                                    #
                                    if not rating in domainValues: # this is a case problem
                                        # replace the original dValue item
                                        dValues[str(rating).upper()][1] = rating

                                        # replace the value in domainValues list
                                        for i in range(len(domainValues)):
                                            if str(domainValues[i]).upper() == str(rating).upper():
                                                domainValues[i] = rating


                                else:
                                    # dValues is keyed on uppercase string rating or is Null
                                    #
                                    # Conservation Tree Shrub has some values not found in the domain.
                                    # How can this be? Need to check with George?
                                    #
                                    #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                    if not str(rating) in missingDomain:
                                        #if mukey == '2780145':
                                        #    PrintMsg("\t**Target mapunit rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)

                                        # Try to add missing value to dDomainValues dict and domainValues list
                                        dComp[cokey] = len(dValues)
                                        dValues[str(rating).upper()] = [len(dValues), rating]
                                        domainValues.append(rating)
                                        #domainValuesUp.append(str(rating).upper())
                                        missingDomain.append(str(rating))
                                        dCompPct[cokey] = compPct

                                        #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)

                            else:
                                # Rating is Null
                                dComp[cokey] = dValues["<Null>"][0]
                                #dComp[cokey] = rating
                                #dValues[str(rating).upper()][1] = rating
                                dCompPct[cokey] = compPct

                                #if mukey == '2780145':
                                #    PrintMsg("\t***Target mapunit rating '" + rating + "' assigning index '" + str(dValues["<Null>"][0]) + "' to dComp", 1)




            else:
                # New code
                #PrintMsg(" \nDomain name for this property: '" + dSDV["tiebreakdomainname"] + "'", 1)

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:
                    if bVerbose:
                        PrintMsg(" \nReading initial data from " + initialTbl + "...", 1)

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "mukey", "cokey", "comppct_r", RATING

                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            #dCase[str(rating).upper()] = rating

                            if not rating is None:

                                if str(rating).upper() in dValues:
                                    #PrintMsg("\tNew rating '" + rating + "' assigning index'" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                    dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                    dCompPct[cokey] = compPct

                                    #if mukey == '2780145':
                                    #    PrintMsg("\t****Target mapunit rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                    #    PrintMsg("\tCokey for target mapunit: " + cokey, 1)

                                    # compare actual rating value to domainValues to make sure case is correct
                                    if not rating in domainValues: # this is a case problem
                                        # replace the original dValue item
                                        dValues[str(rating).upper()][1] = rating

                                        # replace the value in domainValues list
                                        for i in range(len(domainValues)):
                                            if str(domainValues[i]).upper() == str(rating).upper():
                                                domainValues[i] = rating


                                else:
                                    # dValues is keyed on uppercase string rating or is Null
                                    #
                                    # Conservation Tree Shrub has some values not found in the domain.
                                    # How can this be? Need to check with George?
                                    #
                                    #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                    if not str(rating) in missingDomain:
                                        # Try to add missing value to dDomainValues dict and domainValues list
                                        dComp[cokey] = len(dValues)
                                        dValues[str(rating).upper()] = [len(dValues), rating]
                                        domainValues.append(rating)
                                        #domainValuesUp.append(str(rating).upper())
                                        missingDomain.append(str(rating))
                                        dCompPct[cokey] = compPct

                                        #if mukey == '2780145':
                                        #    PrintMsg("\t*****Target mapunit rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)


                            else:
                                dComp[cokey] = dValues["<Null>"][0]  #
                                dCompPct[cokey] = compPct

                                #if mukey == '2780145':
                                #    PrintMsg("\t******Target mapunit rating " + str(rating) + " assigning index '" + str(dValues["<Null>"][0]) + "' to dComp", 1)


        else:
            raise MyError, "Problem with handling domain values of type '" + dSDV["attributelogicaldatatype"]

        # Aggregate monthly index values to a single value for each component??? Would it not be better to
        # create a new function for comonth-DCD? Then I could simplify this function.
        #
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        #if not dSDV["attributelogicaldatatype"].lower() in ["string", "vText"]:

        if bVerbose:
            PrintMsg(" \nAggregating to a single value per component which would generally only apply to comonth properties?", 1)


        # Save list of component rating data to each mapunit, sort and write out
        # a single map unit rating
        #
        dRatings = dict()

        if bVerbose:
            PrintMsg(" \nWriting map unit rating data to final output table", 1)
            PrintMsg(" \nUsing tiebreaker '" + tieBreaker + "' (where choices are " + dSDV["tiebreaklowlabel"] + " or " + dSDV["tiebreakhighlabel"] + ")", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for mukey, cokeys in dMapunit.items():
                    # Since this is comonth data, each cokey could be listed 12X.
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + " cokeys: " + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #This is the final aggregation from component to map unit rating
                    muVal = SortData(muVals, 0, 1, True, True)
                    comppct = muVal[0] / 12
                    newrec = [mukey, comppct, domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])

        else:
            # tieBreaker Lower
            # Overhauling this tiebreaker lower, need to do the rest once it is working properly
            #
            #PrintMsg(" \nActually in Lower tiebreaker code", 1)
            #PrintMsg("dMapunit has " + str(len(dMapunit)) + " records", 1 )

            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                # Process all mapunits
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + ":" + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            comppct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            #PrintMsg("\t" + cokey + " index: " + str(ratingIndx), 1)

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + comppct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = comppct

                        except:
                            errorMsg()

                    for ratingIndx, comppct in dRating.items():
                        muVals.append([comppct, ratingIndx])  # This muVal is not being populated

                    #PrintMsg("\t" + str(dRating), 1)

                    if len(muVals) > 0:
                        muVal = SortData(muVals, 0, 1, True, False)
                        #PrintMsg("\tMukey: " + mukey + ", " + str(muVal), 1)
                        comppct = muVal[0] / 12
                        ratingIndx = muVal[1]
                        #compPct, ratingIndx = muVal
                        rating = domainValues[ratingIndx]

                    else:
                        rating = None
                        comppct = None

                    #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                    #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                    newrec = [mukey, comppct, rating, dAreasym[mukey]]

                    ocur.insertRow(newrec)

                    if not rating is None and not rating in outputValues:
                        outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_Mo_WTA(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Aggregate monthly depth to water table to the map unit level using a special type
    # of Weighted average.
    #
    # Web Soil Survey takes only the Lowest or Highest of the monthly values from
    # each component and calculates the weighted average of those.
    #

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try to substitute dSDV["nullratingreplacementvalue"]
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        #PrintMsg(" \nSQL: " + whereClause, 1)
        #PrintMsg("Fields: " + str(inFlds), 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # mukey,cokey , comppct_r, attribcolumn
            for rec in cur:

                mukey, cokey, compPct, rating, areasym = rec
                dAreasym[mukey] = areasym

                # Save list of cokeys for each mapunit
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    if not rating is None:
                        dComponent[cokey] = [compPct, [rating]]

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # This is working correctly for DepthToWaterTable

            # Identify highest value for each component
            for cokey, coVals in dComponent.items():
                # Find highest monthly value for each component
                #PrintMsg("Higher values for cokey " + cokey + ": " + str(coVals[1]) + " = " + str(max(coVals[1])), 1)
                dCoRating[cokey] = max(coVals[1])

        else:
            # This is working correctly for DepthToWaterTable

            # Identify lowest monthly value for each component
            for cokey, coVals in dComponent.items():
                # Find low rating value for each component
                #PrintMsg("Lower values for cokey " + cokey + ": " + str(coVals[1]) + " = " + str(min(coVals[1])), 1)
                dCoRating[cokey] = min(coVals[1])

        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            #dMuRatings = dict()  # create a dictionary of values for just this map unit
            muPct = 0
            muRating = None

            for cokey in cokeys:
                # look at values for each component within the map unit
                try:
                    rating = dCoRating[cokey]
                    compPct = dComponent[cokey][0]
                    muPct += compPct

                    if not rating is None:
                      # accumulate product of depth and component percent
                      try:
                          muRating += (compPct * rating)

                      except:
                          muRating = compPct * rating

                except:
                    pass

            # Calculate weighted mapunit value from sum of products
            if not muRating is None:
                muRating = muRating / float(muPct)

            dFinalRatings[mukey] = [muPct, muRating]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey in sorted(dMapunit):
                compPct, rating = dFinalRatings[mukey]
                rec = mukey, compPct, rating, dAreasym[mukey]
                ocur.insertRow(rec)

                if not rating is None and not rating in outputValues:
                    outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_WTA_DTWT(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    #
    # In the process of converting DCD to WTA

    try:
        #
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #PrintMsg(" \nTesting nullRating variable: " + str(nullRating), 1)

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff)  # Leave in NULLs and try to substitute 200
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        dMapunit = dict()
        dComponent = dict()
        dCoRating = dict()
        dAreasym = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

            # mukey,cokey , comppct_r, attribcolumn
            for rec in cur:
                #mukey = rec[0]
                #cokey = rec[1]
                #compPct = rec[2]
                #rating = rec[3]
                mukey, cokey, compPct, rating, areasym = rec

                dAreasym[mukey] = areasym

                if rating is None:
                    rating = nullRating

                # Save list of cokeys for each mukey
                try:
                    if not cokey in dMapunit[mukey]:
                        dMapunit[mukey].append(cokey)

                except:
                    dMapunit[mukey] = [cokey]

                try:
                    # Save list of rating values along with comppct for each component
                    dComponent[cokey][1].append(rating)

                except:
                    #  Save list of rating values along with comppct for each component
                    dComponent[cokey] = [compPct, [rating]]


        if tieBreaker == dSDV["tiebreakhighlabel"]:
            for cokey, coVals in dComponent.items():
                # Find high value for each component
                dCoRating[cokey] = max(coVals[1])

        else:
            for cokey, coVals in dComponent.items():
                # Find low value for each component
                dCoRating[cokey] = min(coVals[1])

        dFinalRatings = dict()  # final dominant condition. mukey is key

        for mukey, cokeys in dMapunit.items():
            # accumulate ratings for each mapunit by sum of comppct
            sumPct = 0
            muProd = 0

            for cokey in cokeys:
                # look at values for each component within the map unit
                rating = dCoRating[cokey]
                compPct = dComponent[cokey][0]

                #if rating != nullRating:
                if not rating is None:
                    # Don't include the 201 (originally null) depths in the WTA calculation
                    sumPct += compPct            # sum comppct for the mapunit
                    muProd += (rating * compPct)   # calculate product of component percent and component rating

            if sumPct > 0:
                dFinalRatings[mukey] = [sumPct, round(float(muProd) / sumPct)]

            else:
                # now replace the nulls with 201
                dFinalRatings[mukey] = [100, nullRating]

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
            # Write final ratings to output table
            for mukey, vals in dFinalRatings.items():
                rec = mukey, vals[0], vals[1], dAreasym[mukey]
                ocur.insertRow(rec)

                if not vals[1] is None and not vals[1] in outputValues:
                    outputValues.append(vals[1])

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues


## ===================================================================================
def AggregateCo_DCD_Domain(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Flooding or ponding frequency, dominant condition
    #
    # Aggregate mapunit-component data to the map unit level using dominant condition.
    # Use domain values to determine sort order for tiebreaker
    #
    # Problem with domain values for some indexes which are numeric. Need to accomodate for
    # domain key values which cannot be 'uppercased'.
    #
    # Some domain values are not found in the data and vise versa.
    #
    # Bad problem 2016-06-08.
    # Noticed that my final rating table may contain multiple ratings (tiebreak) for a map unit. This creates
    # a funky join that may display a different map color than the Identify value shows for the polygon. NIRRCAPCLASS.
    # Added areasymbol to output
    #
    # Conservation Tree and Shrub group are located in the component table
    # This has domain values and component values which are all lowercase
    # The maplegendxml is all uppercase
    #
    # I think I need to loop through each output value from the table, find the UPPER match and
    # then alter the legend value and label to match the output value.
    #
    # Nov 2017 problem noticed with Irrigated Capability Class where null values are not used
    # as the dominant condition. Fixed.
    #

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        # Default setting is to include Null values as part of the aggregation process
        if bNulls:
            #PrintMsg(" \nIncluding components with null rating values...", 1)
            whereClause = "comppct_r >=  " + str(cutOff)

        else:
            #PrintMsg(" \nSkipping components with null rating values...", 1)
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dAreasym = dict()
        dCase = dict()

        # PrintMsg(" \ntiebreakdomainname: " + str(dSDV["tiebreakdomainname"]), 1)

        # Read initial table for non-numeric data types. Capture domain values and all component ratings.
        #
        if bVerbose:
            PrintMsg(" \nReading initial data from " + initialTbl + "...", 1)
            PrintMsg(whereClause, 1)

        if not dSDV["attributetype"].lower() == "interpretation" and dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:  # Changed here 2016-04-28
            # No domain values for non-interp string ratings
            # Probably not using this section of code.
            #
            if bVerbose:
                PrintMsg(" \ndValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    # "mukey", "cokey", "comppct_r", RATING
                    mukey, cokey, compPct, rating, areasym = rec
                    dAreasym[mukey] = areasym
                    dComp[cokey] = rating
                    dCompPct[cokey] = compPct
                    dCase[str(rating).upper()] = rating  # save original value using uppercase key

                    # save list of components for each mapunit
                    try:
                        dMapunit[mukey].append(cokey)

                    except:
                        dMapunit[mukey] = [cokey]

        elif dSDV["attributelogicaldatatype"].lower() in ["string", "float", "integer", "choice"]:
            #
            # if dSDV["tiebreakdomainname"] is not None:  # this is a test to see if there are true domain values
            # Use this to compare dValues to output values
            #

            if len(domainValues) > 1 and not None in domainValues:

                if tieBreaker == dSDV["tiebreakhighlabel"]:
                    # Put the null value at the beginning of the domain
                    dValues["<None>"] = [0, None]
                    #domainValues.insert(0, None)

                else:
                    # Put the null value at the end of the domain
                    dValues["<None>"] = [len(dValues), None]
                    #domainValues.append(None)

            # PrintMsg(" \ntiebreakdomainname: " + str(dSDV["tiebreakdomainname"]), 1)

            if bVerbose:
                # ********************** GPR Problem here
                #
                PrintMsg(" \ndValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(dValues), 1)
                PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues) + " \n ", 1)
                PrintMsg("tiebreakdomainname: " + str(dSDV["tiebreakdomainname"]), 1)

            if  dSDV["tiebreakdomainname"] is None:
                # There are no domain values.
                # We must make sure that the legend values are the same as the output values.
                #
                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym

                        #if bVerbose and mukey == '397784':
                        #    PrintMsg("\tRECORD:  " + str(rec), 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating


                            # I have a Problem here with domain values and 'None' vs None with GPR
                            # Perhaps I could add a '<Null>' value to the domain at the beginning or end?
                            #
                            if str(rating).upper() in dValues or rating is None:
                                #PrintMsg("\tNew rating '" + rating + "' assigning index '" + str(dValues[str(rating).upper()][0]) + "' to dComp", 1)
                                if not rating is None:
                                    # Don't confuse 'None' with None
                                    # Get the index from dValues for this component rating and save it to dComp by cokey
                                    dComp[cokey] = dValues[str(rating).upper()][0]  #

                                    #dValues[str(rating).upper()][1] = rating  # not sure why this line is needed

                                else:
                                    # Get the index from dValues for <Null> and save it to dComp by cokey
                                    dComp[cokey] = dValues["<Null>"][0]

                                    # dValues[str(rating).upper()][1] = rating  # not sure why this line is needed

                                #dComp[cokey] = rating

                                dCompPct[cokey] = compPct

                                #if mukey in ('2780146', '294959'):
                                #    PrintMsg("\tRating for " + mukey + " (" + str(rating) + ") assigned to index '" + str(dComp[cokey]) + "' in dComp", 1)


                                # compare actual rating value to domainValues to make sure case is correct
                                #
                                # This does not make sense. domainValues must be coming from maplegendxml.
                                #
                                if not rating in domainValues: # this is a case problem or perhaps
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct
                                    #PrintMsg("\t****Adding value '" + str(rating) + "' to domainValues", 1)


            else:
                # New code for property or interps with domain values

                with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                    for rec in cur:
                        mukey, cokey, compPct, rating, areasym = rec
                        dAreasym[mukey] = areasym
                        # "mukey", "cokey", "comppct_r", RATING

                        #if bVerbose and mukey == '397784':
                        #    PrintMsg("\tRECORD:  " + str(rec), 1)


                        # save list of components for each mapunit
                        try:
                            dMapunit[mukey].append(cokey)

                        except:
                            dMapunit[mukey] = [cokey]

                        # this is a new component record. create a new dictionary item.
                        #
                        if not cokey in dComp:
                            dCase[str(rating).upper()] = rating

                            if str(rating).upper() in dValues:

                                dComp[cokey] = dValues[str(rating).upper()][0]  # think this is bad
                                dCompPct[cokey] = compPct

                                # compare actual rating value to domainValues to make sure case is correct
                                if not rating in domainValues: # this is a case problem
                                    # replace the original dValue item
                                    dValues[str(rating).upper()][1] = rating

                                    # replace the value in domainValues list
                                    for i in range(len(domainValues)):
                                        if str(domainValues[i]).upper() == str(rating).upper():
                                            domainValues[i] = rating


                            else:
                                # dValues is keyed on uppercase string rating or is Null
                                #
                                # Conservation Tree Shrub has some values not found in the domain.
                                # How can this be? Need to check with George?
                                #
                                #PrintMsg("\tdValue not found for: " + str(rec), 1)
                                if not str(rating) in missingDomain:
                                    # Try to add missing value to dDomainValues dict and domainValues list
                                    dComp[cokey] = len(dValues)
                                    dValues[str(rating).upper()] = [len(dValues), rating]
                                    domainValues.append(rating)
                                    domainValuesUp.append(str(rating).upper())
                                    missingDomain.append(str(rating))
                                    dCompPct[cokey] = compPct
                                    #PrintMsg("\tAdding value '" + str(rating) + "' to domainValues", 1)



        else:
            raise MyError, "Problem with handling domain values of type '" + dSDV["attributelogicaldatatype"]

        # Aggregate monthly index values to a single value for each component??? Would it not be better to
        # create a new function for comonth-DCD? Then I could simplify this function.
        #
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component

        # Save list of component rating data to each mapunit, sort and write out
        # a single map unit rating
        #
        dRatings = dict()

        if bVerbose:
            PrintMsg(" \nWriting map unit rating data to final output table", 1)
            PrintMsg(" \nUsing tiebreaker '" + tieBreaker + "' (where choices are " + dSDV["tiebreaklowlabel"] + " or " + dSDV["tiebreakhighlabel"] + ")", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    #for rating, compPct in dRating.items():
                    #    muVals.append([compPct, rating])

                    for ratingIndx, compPct in dRating.items():
                        muVals.append([compPct, ratingIndx])  # This muVal is not being populated

                    #This is the final aggregation from component to map unit rating

                    #muVal = SortData(muVals, 0, 1, True, True)
                    #newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    #ocur.insertRow(newrec)

                    #if not newrec[2] is None and not newrec[2] in outputValues:
                    #    outputValues.append(newrec[2])

                    #PrintMsg("\t" + str(dRating), 1)
                    if len(muVals) > 0:
                        muVal = SortData(muVals, 0, 1, True, True)
                        compPct, ratingIndx = muVal
                        rating = domainValues[ratingIndx]

                        #if bVerbose and mukey == '397784':
                        #    PrintMsg("\tmuVal for mukey: " + mukey + ", " + str(muVal), 1)
                        #    PrintMsg("\tRating: " + str(rating), 1)

                    else:
                        rating = None
                        compPct = None

                    #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                    #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                    newrec = [mukey, compPct, rating, dAreasym[mukey]]

                    ocur.insertRow(newrec)

                    if not rating is None and not rating in outputValues:
                        outputValues.append(rating)

        else:
            # tieBreaker Lower
            # Overhauling this tiebreaker lower, need to do the rest once it is working properly
            #
            #PrintMsg(" \nActually in Lower tiebreaker code", 1)
            #PrintMsg("dMapunit has " + str(len(dMapunit)) + " records", 1 )

            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                # Process all mapunits
                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD
                    #PrintMsg("\t" + mukey + ":" + str(cokeys), 1)

                    for cokey in cokeys:
                        try:
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]
                            #PrintMsg("\t" + cokey + " index: " + str(ratingIndx), 1)

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            errorMsg()

                    for ratingIndx, compPct in dRating.items():
                        muVals.append([compPct, ratingIndx])  # This muVal is not being populated

                    #PrintMsg("\t" + str(dRating), 1)
                    if len(muVals) > 0:
                        muVal = SortData(muVals, 0, 1, True, False)
                        #PrintMsg("\tmuVal for mukey: " + mukey + ", " + str(muVal), 1)
                        compPct, ratingIndx = muVal
                        rating = domainValues[ratingIndx]

                    else:
                        rating = None
                        compPct = None

                    #PrintMsg(" \n" + tieBreaker + ". Checking index values for mukey " + mukey + ": " + str(muVal[0]) + ", " + str(domainValues[muVal[1]]), 1)
                    #PrintMsg("\tGetting mukey " + mukey + " rating: " + str(rating), 1)
                    newrec = [mukey, compPct, rating, dAreasym[mukey]]

                    ocur.insertRow(newrec)

                    if not rating is None and not rating in outputValues:
                        outputValues.append(rating)

        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_DCP_Domain(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    # Not being use.
    #
    # I may not use this function. Trying to handle ratings with domain values using the
    # standard AggregateCo_DCP function
    #
    # Flooding or ponding frequency, dominant component with domain values
    #
    # Use domain values to determine sort order for tiebreaker
    #
    # Problem with domain values for some indexes which are numeric. Need to accomodate for
    # domain key values which cannot be 'uppercased'.
    # Added areasymbol to output

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]
        whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        # initialTbl must be in a file geodatabase to support ORDER_BY
        # Do I really need to sort by attribucolumn when it will be replaced by Domain values later?
        sqlClause =  (None, " ORDER BY mukey ASC, comppct_r DESC")


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastCokey = "xxxx"
        dComp = dict()
        dCompPct = dict()
        dMapunit = dict()
        missingDomain = list()
        dCase = dict()
        dAreasym = dict()

        # Read initial table for non-numeric data types
        # 02-03-2016 Try adding 'choice' to this method to see if it handles Cons. Tree/Shrub better
        # than the next method. Nope, did not work. Still have case problems.
        #
        if dSDV["attributelogicaldatatype"].lower() == "string":
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"].lower() + "-type values : " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead.
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                        dCompPct[rec[1]] = rec[2]
                        dCase[str(rec[3]).upper()] = rec[3]  # save original value using uppercase key


                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        elif dSDV["attributelogicaldatatype"].lower() in ["float", "integer", "choice"]:
            # PrintMsg(" \ndomainValues for " + dSDV["attributelogicaldatatype"] + " values: " + str(domainValues), 1)

            with arcpy.da.SearchCursor(initialTbl, inFlds, sql_clause=sqlClause, where_clause=whereClause) as cur:

                for rec in cur:
                    dAreasym[rec[0]] = rec[4]
                    try:
                        # capture component ratings as index numbers instead
                        dComp[rec[1]].append(dValues[str(rec[3]).upper()][0])

                    except:
                        #PrintMsg(" \ndomainValues is empty, but legendValues has " + str(legendValues), 1)
                        dCase[str(rec[3]).upper()] = rec[3]

                        if str(rec[3]).upper() in dValues:
                            dComp[rec[1]] = [dValues[str(rec[3]).upper()][0]]
                            dCompPct[rec[1]] = rec[2]

                            # compare actual rating value to domainValues to make sure case is correct
                            if not rec[3] in domainValues: # this is a case problem
                                # replace the original dValue item
                                dValues[str(rec[3]).upper()][1] = rec[3]
                                # replace the value in domainValues list
                                for i in range(len(domainValues)):
                                    if domainValues[i].upper() == rec[3].upper():
                                        domainValues[i] = rec[3]

                        else:
                            # dValues is keyed on uppercase string rating
                            #
                            if not str(rec[3]) in missingDomain:
                                # Try to add missing value to dDomainValues dict and domainValues list
                                dValues[str(rec[3]).upper()] = [len(dValues), rec[3]]
                                domainValues.append(rec[3])
                                domainValuesUp.append(rec[3].upper())
                                missingDomain.append(str(rec[3]))
                                #PrintMsg("\tAdding value '" + str(rec[3]) + "' to domainValues", 1)

                        # save list of components for each mapunit
                        try:
                            dMapunit[rec[0]].append(rec[1])

                        except:
                            dMapunit[rec[0]] = [rec[1]]

        else:
            PrintMsg(" \nProblem with handling domain values of type '" + dSDV["attributelogicaldatatype"] + "'", 1)

        # Aggregate monthly index values to a single value for each component
        # Sort depending upon tiebreak setting
        # Update dictionary with a single index value for each component
        PrintMsg(" \nNot sure about this sorting code for tiebreaker", 1)

        if tieBreaker == dSDV["tiebreakhighlabel"]:
            # "Higher" (default for flooding and ponding frequency)
            for cokey, indexes in dComp.items():
                val = sorted(indexes, reverse=True)[0]
                dComp[cokey] = val
        else:
            for cokey, indexes in dComp.items():
                val = sorted(indexes)[0]
                dComp[cokey] = val

        # Save list of component data to each mapunit
        dRatings = dict()

        with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # Default for flooding and ponding frequency
                #
                #PrintMsg(" \ndomainValues: " + str(domainValues), 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()   # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        #PrintMsg("\tB ratingIndx: " + str(dComp[cokey]), 1)
                        compPct = dCompPct[cokey]
                        ratingIndx = dComp[cokey]

                        if ratingIndx in dRating:
                            sumPct = dRating[ratingIndx] + compPct
                            dRating[ratingIndx] = sumPct  # this part could be compacted

                        else:
                            dRating[ratingIndx] = compPct

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], x[1]))[0]  # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=True)[0]
                    muVal = SortData(muVals, 0, 1, True, True)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])

            else:
                # Lower
                PrintMsg(" \nFinal lower tiebreaker", 1)

                for mukey, cokeys in dMapunit.items():
                    dRating = dict()  # save sum of comppct for each rating within a mapunit
                    muVals = list()   # may not need this for DCD

                    for cokey in cokeys:
                        try:
                            #PrintMsg("\tA ratingIndx: " + str(dComp[cokey]), 1)
                            compPct = dCompPct[cokey]
                            ratingIndx = dComp[cokey]

                            if ratingIndx in dRating:
                                sumPct = dRating[ratingIndx] + compPct
                                dRating[ratingIndx] = sumPct  # this part could be compacted

                            else:
                                dRating[ratingIndx] = compPct

                        except:
                            pass

                    for rating, compPct in dRating.items():
                        muVals.append([compPct, rating])

                    #newVals = sorted(muVals, key = lambda x : (-x[0], -x[1]))[0] # Works for maplegendkey=2
                    #newVals = sorted(sorted(muVals, key = lambda x : x[0], reverse=True), key = lambda x : x[1], reverse=False)[0]
                    muVal = SortData(muVals, 0, 1, True, False)
                    newrec = [mukey, muVal[0], domainValues[muVal[1]], dAreasym[mukey]]
                    ocur.insertRow(newrec)

                    if not newrec[2] is None and not newrec[2] in outputValues:
                        outputValues.append(newrec[2])


        outputValues.sort()
        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_WTA(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    # Aggregate mapunit-component data to the map unit level using a weighted average
    #
    # Possible problem with Depth to Restriction and the null replacement values of 201. nullRating
    # Should be calculating 'BrD' mapunit using [ (66/(66 + 15) X 38cm) + (15/(66 + 15) X 0cm) ]

    # Another question. For depth to any restriction, there could be multiple restrictions per
    # component. Do I need to sort on depth according to tieBreaker setting?
    
    try:
        #bVerbose = True

        # TEST CODE FOR nullRating handling
        if bVerbose:
            PrintMsg(" \nnullRating: " + str(nullRating), 1)

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with mukey, comppct_r and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        # sort order of value is important
        if tieBreaker == "Lower":
            sOrder = " DESC"

        else:
            sOrder = " ASC"

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + sOrder)

        if bZero == False and nullRating is None:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # ignore values = null replacement value. Trying to fix Depth to Restriction WTA problem.
            #
            if not nullRating is None:
                #whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL AND " + dSDV["attributecolumnname"].lower() + " <> " + str(nullRating)
                #whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " <> " + str(nullRating)
                whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

            else:
                # retrieve null values and convert to zeros during the iteration process
                whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        if bVerbose:
            PrintMsg(" \nSQL: " + whereClause, 1)
            PrintMsg("Input table (" + initialTbl + ") has " + str(int(arcpy.GetCount_management(initialTbl).getOutput(0))) + " records", 1)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        #prec = dSDV["attributeprecision"]
        outputValues = [999999999, -999999999]
        recCnt = 0
        areasym = ""
        dPct = dict()  # sum of comppct_r for each map unit
        dMapunit = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    recCnt += 1
                    mukey, cokey, comppct, val, areasym = rec
                    #PrintMsg(str(recCnt) + ". " + str(rec), 1)

                    # Capture component list for each mapunit
                    try:
                        if not cokey in dMapunit[mukey]:
                            dMapunit[mukey].append(cokey)
                            
                            if not val == nullRating:
                                dPct[mukey] += comppct

                    except:
                        dMapunit[mukey] = [cokey]

                        if not val == nullRating:
                            dPct[mukey] = comppct

                    if val is None and bZero:
                        # convert null values to zero
                        val = 0.0

                    if val == nullRating:
                        # 
                        val = None
                        
                        

                    #if bVerbose and mukey in ['374414', '374451']:
                    #    PrintMsg("\t\tMukey " + mukey + ":" + cokey + ";  " + str(comppct) + "%;  " + str(val), 1)

                    if mukey != lastMukey and lastMukey != "xxxx":
                        # I'm losing an output value when there is only one rated component and bZeros == True
                        # This is because only the non-Null ratings are being processed for things like Range Production (Normal Year) in Batch Mode.
                        #
                        try:
                            sumPct = dPct[lastMukey]

                        except:
                            dPct[lastMukey] = 0
                            sumPct = 0
                        
                        if (sumPct > 0 and sumProd is not None):
                            # write out record for previous mapunit

                            meanVal = round(float(sumProd) / sumPct, fldPrecision)
                            newrec = [lastMukey, sumPct, meanVal, areasym]
                            ocur.insertRow(newrec)

                            #if bVerbose and lastMukey in ['374414', '374451']:
                            #    PrintMsg("\tTest mapunit1 " + lastMukey + ": " + str(meanVal) + ";  " + str(sumPct) + "%", 1)

                            # reset variables for the next mapunit record
                            sumPct = 0
                            sumProd = None

                            # save max-min values
                            if not meanVal is None:
                                outputValues[0] = min(meanVal, outputValues[0])
                                outputValues[1] = max(meanVal, outputValues[1])

                        else:
                        #    Tried to bring back null rating replacement value (201), but that didn't work because those
                        #    are being excluded from the entire process by the sql_clause.
                        #
                            newrec = [lastMukey, sumPct, nullRating, areasym]
                            #if bVerbose and lastMukey in ['374414', '374451']:
                            #    PrintMsg("\tTest mapunit2 " + lastMukey + ": " + str(nullRating) + ";  " + str(sumPct) + "%", 1)
                                
                            ocur.insertRow(newrec)
                            # reset variables for the next mapunit record
                            sumPct = 0
                            sumProd = None
                            dPct[lastMukey] = 0

                    # accumulate data for this mapunit
                    #PrintMsg("\tFollowup summary", 1)
                    #sumPct += comppct

                    if val is not None:
                        prod = comppct * float(val)
                        try:
                            sumProd += prod

                        except:
                            sumProd = prod

                    # set new mapunit flag
                    lastMukey = mukey

                # Add final record
                try:
                    sumPct = dPct[lastMukey]

                except:
                    dPct[lastMukey] = 0
                
                if areasym != "" and sumPct != 0:  # 
                    if sumProd is None:
                        meanVal = nullRating

                    else:
                        meanVal = round(float(sumProd) / sumPct, fldPrecision)
                        
                    newrec = [lastMukey, sumPct, meanVal, areasym]  # if there is no data, this will error
                    ocur.insertRow(newrec)

                    if dSDV["resultcolumnname"].lower().startswith("NCCPI"):
                        # For NCCPI, hardcode the range of values from 0.0 to 1.0 for a consistent map legend
                        outputValues = [0.0, 1.0]

                    elif not meanVal is None:
                        outputValues[0] = min(meanVal, outputValues[0])
                        outputValues[1] = max(meanVal, outputValues[1])

        outputValues.sort()
        del sumPct
        del sumProd
        del meanVal

        if outputValues[0] == -999999999 or outputValues[1] == 999999999:
            # Sometimes no data can skip through the max min test
            outputValues = [0.0, 0.0]

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_WTA_Old(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, bZero):
    # Aggregate mapunit-component data to the map unit level using a weighted average
    #
    # Possible problem with Depth to Restriction and the null replacement values of 201. nullRating
    # Should be calculating 'BrD' mapunit using [ (66/(66 + 15) X 38cm) + (15/(66 + 15) X 0cm) ]

    # Another question. For depth to any restriction, there could be multiple restrictions per
    # component. Do I need to sort on depth according to tieBreaker setting?
    
    try:
        #bVerbose = True

        # TEST CODE FOR nullRating handling
        if bVerbose:
            PrintMsg(" \nnullRating: " + str(nullRating), 1)

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with mukey, comppct_r and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]


        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, " + dSDV["attributecolumnname"].lower() + " DESC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # ignore values = null replacement value. Trying to fix Depth to Restriction WTA problem.
            #
            if not nullRating is None:
                whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " != " + str(nullRating)

            else:
                # retrieve null values and convert to zeros during the iteration process
                whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        if bVerbose:
            PrintMsg(" \nSQL: " + whereClause, 1)
            PrintMsg("Input table has " + str(int(arcpy.GetCount_management(initialTbl).getOutput(0))), 1)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues = list()

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        #prec = dSDV["attributeprecision"]
        outputValues = [999999999, -999999999]
        recCnt = 0
        areasym = ""
        dPct = dict()  # sum of comppct_r for each map unit
        #dMapunit = dict()

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    recCnt += 1
                    mukey, cokey, comppct, val, areasym = rec
                    #PrintMsg(str(recCnt) + ". " + str(rec), 1)

                    if val is None and bZero:
                        # convert null values to zero
                        val = 0.0

                    #if mukey != lastMukey and lastMukey != "xxxx":
                    if mukey != lastMukey:
                        # I'm losing an output value when there is only one rated component and bZeros == True
                        # This is because only the non-Null ratings are being processed for things like Range Production (Normal Year) in Batch Mode.
                        #
                        cokeyList = [cokey] # first component
                        dPct[mukey] = comppct
                        
                        if (sumPct > 0 and sumProd is not None):
                            # write out record for previous mapunit

                            meanVal = round(float(sumProd) / sumPct, fldPrecision)
                            newrec = [lastMukey, sumPct, meanVal, areasym]
                            ocur.insertRow(newrec)

                            # reset variables for the next mapunit record
                            sumPct = 0
                            sumProd = None

                            # save max-min values
                            if not meanVal is None:
                                outputValues[0] = min(meanVal, outputValues[0])
                                outputValues[1] = max(meanVal, outputValues[1])

                    if not cokey in cokeyList:  # other components
                        cokeyList.append(cokey)
                        dPct[mukey] += comppct
                        
    

                    # accumulate data for this mapunit
                    #PrintMsg("\tFollowup summary", 1)
                    sumPct += comppct

                    if val is not None:
                        prod = comppct * float(val)
                        try:
                            sumProd += prod

                        except:
                            sumProd = prod

                    # set new mapunit flag
                    lastMukey = mukey

                # Add final record
                if areasym != "":  # not sure why this is needed
                    meanVal = round(float(sumProd) / sumPct, fldPrecision)
                    newrec = [lastMukey, sumPct, meanVal, areasym]  # if there is no data, this will error
                    ocur.insertRow(newrec)

                    if dSDV["resultcolumnname"].lower().startswith("NCCPI"):
                        # For NCCPI, hardcode the range of values from 0.0 to 1.0 for a consistent map legend
                        outputValues = [0.0, 1.0]

                    elif not meanVal is None:
                        outputValues[0] = min(meanVal, outputValues[0])
                        outputValues[1] = max(meanVal, outputValues[1])

        outputValues.sort()
        del sumPct
        del sumProd
        del meanVal

        if outputValues[0] == -999999999 or outputValues[1] == 999999999:
            # Sometimes no data can skip through the max min test
            outputValues = [0.0, 0.0]

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateCo_PP_SUM(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker):
    #
    # Aggregate data to the map unit level using a sum (Hydric)
    # This is Percent Present
    # Soil Data Viewer reports zero for non-Hydric map units. This function is
    # currently not creating a record for those because they are not included in the
    # sdv_initial table.
    #
    # Will try removing sql whereclause from cursor and apply it to each record instead.
    #
    # Added Areasymbol to output

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with mukey, comppct_r and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["mukey", "areasymbol", "comppct_r", dSDV["attributecolumnname"].lower(), "areasymbol"]  # not sure why I have areasymbol on the end..
        outFlds = ["mukey", "areasymbol", dSDV["resultcolumnname"].lower(), "areasymbol"]

        inFlds = ["mukey", "areasymbol", "comppct_r", dSDV["attributecolumnname"].lower()]  # not sure why I have areasymbol on the end..
        outFlds = ["mukey", "areasymbol", dSDV["resultcolumnname"].lower()]

        sqlClause =  (None, "ORDER BY mukey ASC")

        # For Percent Present, do not apply the whereclause to the cursor. Wait
        # and use it against each record so that all map units are rated or set to zero.
        #whereClause = dSDV["sqlwhereclause"]
        whereClause = ""

        
        hydric = dSDV["sqlwhereclause"].split("=")[1].encode('ascii').strip().replace("'","")

        #PrintMsg(" \n" + sdvFld + " = " + hydric, 1)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        # Create outputTbl based upon initialTbl schema
        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        lastMukey = "xxxx"
        dRating = dict()
        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        iMax = -999999999
        iMin = 999999999

        if bVerbose:
            PrintMsg(" \nReading " + initialTbl + " and writing to " + outputTbl, 1)

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                for rec in cur:
                    mukey, areasym, comppct, val= rec

                    if comppct is None:
                        comppct = 0

                    if mukey != lastMukey and lastMukey != "xxxx":
                        #if sumPct > 0:
                        # write out record for previous mapunit
                        newrec = [lastMukey, areasym, sumPct]
                        ocur.insertRow(newrec)
                        iMax = max(sumPct, iMax)

                        if not sumPct is None:
                            iMin = min(sumPct, iMin)

                        # reset variables for the next mapunit record
                        sumPct = 0

                    # set new mapunit flag
                    lastMukey = mukey

                    # accumulate data for this mapunit
                    if str(val).upper() == "YES":
                        # using the sqlwhereclause on each record so that
                        # the 'NULL' hydric map units are assigned zero instead of NULL.
                        sumPct += comppct

                # Add final record
                newrec = [lastMukey, areasym, sumPct]
                ocur.insertRow(newrec)

        return outputTbl, [iMin, iMax]

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_WTA_SUM(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    # Aggregate mapunit-component-horizon data to the map unit level using a weighted average
    #
    # This version uses SUM for horizon data as in AWS
    # Added areasymbol to output
    #
    try:
        import decimal

        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        # Create final output table with mukey, comppct_r and sdvFld
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        #attribcolumn = dSDV["attributecolumnname"].lower()
        #resultcolumn = dSDV["resultcolumnname"].lower()
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl, outputValues

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0
        #prec = dSDV["attributeprecision"]
        roundOff = 2

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        try:
                            hzT = min(hzdepb, bot) - max(hzdept, top)   # Getting a None error here.usable thickness from this horizon

                        except:
                            hzT = 0

                        if hzT > 0:
                            aws = float(hzT) * val
                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, aws, areasym]

                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dAWS, areasym = dComp[cokey]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dAWS, areasym]

                        #arcpy.SetProgressorPosition()

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, dRec in dComp.items():
                        # get component level data  CHK
                        mukey, comppct, hzT, val, areasym = dRec

                        # get sum of component percent for the mapunit  CHK
                        try:
                            sumCompPct = float(dPct[mukey])

                        except:
                            # set the component percent to zero if it is not found in the
                            # dictionary. This is probably a 'Miscellaneous area' not included in the  CHK
                            # data or it has no horizon information.
                            sumCompPct = 0

                        #PrintMsg(areasym + ", " + mukey + ", " + cokey + ", " + str(comppct) + ", " + str(sumCompPct) + ", " + str(hzT) + ", " + str(val), 1)  # These look good


                        # calculate component percentage adjustment

                        if sumCompPct > 0:
                            # If there is no data for any of the component horizons, could end up with 0 for
                            # sum of comppct_r
                            adjCompPct = float(comppct) / sumCompPct   # WSS method

                            # adjust the rating value down by the component percentage and by the sum of the
                            # usable horizon thickness for this component
                            aws = adjCompPct * val
                            hzT = hzT * adjCompPct    # Adjust component share of horizon thickness by comppct

                            # Update component values in component dictionary
                            dComp[cokey] = mukey, comppct, hzT, aws, areasym

                            # Populate dMu dictionary
                            if mukey in dMu:
                                val1, val3, areasym = dMu[mukey]
                                comppct = comppct + val1
                                aws = aws + val3

                            dMu[mukey] = [comppct, aws, areasym]

                # Write out map unit aggregated AWS
                #
                murec = list()
                outputValues= [999999999, -999999999]

                for mukey, val in dMu.items():
                    compPct, aws, areasym = val
                    aws = round(aws, fldPrecision) # Test temporary removal of rounding
                    #aws = decimal.Decimal(str(aws)).quantize(decimal.Decimal("0.01"), decimal.ROUND_HALF_UP)
                    murec = [mukey, comppct, aws, areasym]
                    ocur.insertRow(murec)

                    # save max-min values
                    if not aws is None:
                        outputValues[0] = min(aws, outputValues[0])
                        outputValues[1] = max(aws, outputValues[1])

        outputValues.sort()

        #if (bZero and outputValues ==  [0.0, 0.0]):
            #PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_WTA_WTA(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    # Aggregate mapunit-component-horizon data to the map unit level using a weighted average
    #
    # This version uses weighted average for horizon data as in AWC and most others
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        initFlds = arcpy.Describe(initialTbl).fields
        initFldNames = [initFld.name for initFld in initFlds]
        #PrintMsg(" \ninitialTbl fields: " + ", ".join(initFldNames), 1)
        
        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        try:
                            hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        except:
                            hzT = 0

                        if hzT > 0:
                            aws = float(hzT) * val * comppct

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, aws, areasym]
                                try:
                                    dPct[mukey] = dPct[mukey] + comppct

                                except:
                                    dPct[mukey] = comppct

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dAWS, areasym = dComp[cokey]
                                dAWS = dAWS + aws
                                dHzT = dHzT + hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dAWS, areasym]

                        #else:
                        #    PrintMsg("\tFound horizon for mapunit (" + mukey + ":" + cokey + " with hzthickness of " + str(hzT), 1)

                    #else:
                    #    PrintMsg("\tFound horizon with no data for mapunit (" + mukey + ":" + cokey + " with hzthickness of " + str(hzT), 1)

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)
                    #arcpy.SetProgressor("step", "Saving map unit and component AWS data...",  0, iComp, 1)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, hzT, cval, areasym = vals

                        # get sum of comppct for mapunit
                        sumPct = dPct[mukey]

                        # calculate component weighted values
                        # get weighted layer thickness
                        divisor = sumPct * hzT

                        if divisor > 0:
                            newval = float(cval) / divisor

                        else:
                            newval = 0.0

                        if mukey in dMu:
                            pct, mval, areasym = dMu[mukey]
                            newval = newval + mval

                        dMu[mukey] = [sumPct, newval, areasym]

                # Write out map unit aggregated AWS
                #
                murec = list()
                outputValues= [999999999, -999999999]

                for mukey, vals in dMu.items():
                    sumPct, val, areasym = vals
                    aws = round(val, fldPrecision)
                    murec = [mukey, sumPct, aws, areasym]
                    ocur.insertRow(murec)
                    # save max-min values
                    if not aws is None:
                        outputValues[0] = min(aws, outputValues[0])
                        outputValues[1] = max(aws, outputValues[1])

        outputValues.sort()

        #if (bZero and outputValues ==  [0.0, 0.0]):
        #    PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_DCP_WTA(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    #
    # Dominant component for mapunit-component-horizon data to the map unit level
    #
    # This version uses weighted average for horizon data
    # Added areasymbol to output
    #
    # Problem: Need to fix tiebreaker logic

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")

        # Create final output table with mukey, comppct_r and sdvFld
        #bVerbose = True

        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])
        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")
        whereClause = "comppct_r >=  " + str(cutOff)
        # whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"


        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)
        outputValues= [999999999, -999999999]

        if outputTbl == "":
            raise MyError,""

        dPct = dict()  # sum of comppct_r for each map unit
        dHorizon = dict()
        dComp = dict() # component level information
        dMu = dict()
        dCompList = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:
                #arcpy.SetProgressor("step", "Reading initial query table ...",  0, iCnt, 1)

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range

                    if not cokey in dHorizon:
                        if not mukey in dPct:
                            # Problem:
                            # This if statement above is only getting the first component and ignoring any ties based upon component percent
                            #
                            dCompList[mukey] = [cokey]  # initialize list of components for this mapunit

                            dPct[mukey] = comppct  # cursor is sorted on comppct_r descending, so this should be dominant component percent.

                            if val is not None and hzdept is not None and hzdepb is not None:
                                # Normal component with horizon data
                                hzT = min(hzdepb, bot) - max(hzdept, top)
                                aws = float(hzT) * val
                                dHorizon[cokey] = [mukey, comppct, hzT, aws, areasym]

                        elif comppct >= dPct[mukey]:
                            # This should be a mapunit that has more than one dominant component
                            dCompList[mukey].append(cokey)

                            if val is not None and hzdept is not None and hzdepb is not None:
                                # Normal component with horizon data
                                hzT = min(hzdepb, bot) - max(hzdept, top)
                                aws = float(hzT) * val
                                dHorizon[cokey] = [mukey, comppct, hzT, aws, areasym]

                            else:
                                # Component with no data for this horizon
                                dHorizon[cokey] = [mukey, comppct, None, None, areasym]


                    else:
                        try:
                            # For dominant component:
                            # accumulate total thickness and total rating value by adding to existing component values  CHK

                            mukey, comppct, dHzT, dAWS, areasym = dHorizon[cokey]

                            if val is not None and hzdept is not None and hzdepb is not None:
                                hzT = min(hzdepb, bot) - max(hzdept, top)
                                aws = float(hzT) * val
                                dAWS = max(0, dAWS) + aws
                                dHzT = max(0, dHzT) + hzT
                                dHorizon[cokey] = [mukey, comppct, dHzT, dAWS, areasym]

                        except KeyError:
                            # Hopefully this is a component other than dominant
                            pass

                        except:
                            errorMsg()


                # get the total number of major components from the dictionary count
                iComp = len(dHorizon)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:

                    for cokey, vals in dHorizon.items():

                        # get component level data
                        mukey, pct, hzT, cval, areasym = vals

                        # calculate mean value for entire depth range
                        if not cval is None and hzT > 0:
                            newval = float(cval) / hzT

                        else:
                            newval = None

                        if cokey in dComp:
                            pct, mval, areasym = dComp[cokey]
                            newval = newval + mval

                        dComp[cokey] = [pct, newval, areasym]

                # Test iteration through dCompList?? and replace dMu
                if tieBreaker == dSDV["tiebreakhighlabel"]:
                    bRev = True

                else:
                    bRev = False

                for mukey, cokeys in dCompList.items():
                    if len(cokeys) > 0:
                        # find component with value according to tiebreaker rule
                        # assign that set of values to dMu
                        valList = list()

                        for cokey in cokeys:
                            try:
                                pct, newval, areasym = dComp[cokey]

                                if not newval is None:
                                    valList.append(newval)

                            except:
                                #PrintMsg("\tNo data for cokey: " + cokey, 1)
                                pass

                        if len(valList):
                            valList.sort(reverse=bRev)
                            val = valList[0]

                            if not val is None:
                                val = round(val, fldPrecision)

                            outputValues[0] = min(valList[0], outputValues[0])
                            outputValues[1] = max(valList[0], outputValues[1])

                        else:
                            val = None


                        murec =  mukey, pct, val, areasym
                        #dMu[mukey] = newrec
                        ocur.insertRow(murec)
                        #PrintMsg("\tMapunit: " + mukey + "; " + str(pct) + "%; " + str(val), 1)


        outputValues.sort()

        #if (bZero and outputValues ==  [0.0, 0.0]):
        #    PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, outputValues

    except:
        errorMsg()
        return outputTbl, outputValues

## ===================================================================================
def AggregateHz_MaxMin_WTA(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    # Aggregate mapunit-component-horizon data to the map unit level using weighted average
    # for horizon data, but the assigns either the minimum or maximum component rating to
    # the map unit, depending upon the Tiebreaker setting.
    # Added areasymbol to output
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range
                    if val is None and bZero:
                        val = 0

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        try:
                            hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        except:
                            hzT = 0

                        if hzT > 0:
                            rating = float(hzT) * val   # Not working for KFactor WTA
                            #rating = float(hzT) * float(val)   # Try floating the KFactor to see if that will work. Won't it still have to be rounded to standard KFactor index value?

                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                dComp[cokey] = [mukey, comppct, hzT, rating, areasym]

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, dHzT, dRating, areasym = dComp[cokey]
                                dRating += rating
                                dHzT += hzT
                                dComp[cokey] = [mukey, comppct, dHzT, dRating, areasym]

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, hzT, cval, areasym = vals
                        if not cval is None and hzT > 0:
                            rating = cval / hzT  # final horizon weighted average for this component

                        else:
                            rating = None

                        #PrintMsg("\t" + mukey + ", " + cokey + ", " + str(round(rating, 1)), 1)

                        try:
                            # append component weighted average rating to the mapunit dictionary
                            dMu[mukey].append([comppct, rating, areasym])

                        except:
                            # create a new mapunit record in the dictionary
                            dMu[mukey] = [[comppct, rating, areasym]]

                # Write out map unit aggregated rating
                #
                #murec = list()
                outputValues = [999999999, -999999999]

                if tieBreaker == dSDV["tiebreakhighlabel"]:
                    for mukey, muVals in dMu.items():
                        muVal = SortData(muVals, 1, 0, True, True)
                        pct, val, areasym = muVal
                        rating = round(val, fldPrecision)
                        murec = [mukey, pct, rating, areasym]
                        ocur.insertRow(murec)

                        if not rating is None:
                            # save overall max-min values
                            outputValues[0] = min(rating, outputValues[0])
                            outputValues[1] = max(rating, outputValues[1])

                else:
                    # Lower
                    for mukey, muVals in dMu.items():
                        muVal = SortData(muVals, 1, 0, False, True)
                        pct, val, areasym = muVal
                        rating = round(val, fldPrecision)
                        murec = [mukey, pct, rating, areasym]
                        ocur.insertRow(murec)

                        if not rating is None:
                            # save overall max-min values
                            outputValues[0] = min(rating, outputValues[0])
                            outputValues[1] = max(rating, outputValues[1])

        #if (bZero and outputValues ==  [0.0, 0.0]):
        #    PrintMsg(" \nNo data for " + sdvAtt, 1)

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def AggregateHz_MaxMin_DCD(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    # Aggregate mapunit-component-horizon data to the map unit level using the highest rating
    # from all horizons. Currently this would only apply to K Factor and dominant condition.

    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        try:
                            hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        except:
                            hzT = 0

                        if hzT > 0:
                            ratingIndx = domainValues.index(val)   # Change KFactor to an index based upon domain order

                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                # Create initial entry for this component using the first horiozon CHK
                                ratingList = [ratingIndx]
                                dComp[cokey] = [mukey, comppct, ratingList, areasym]

                            else:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, ratingList, areasym = dComp[cokey]
                                
                                if not ratingIndx in ratingList:
                                    ratingList.append(ratingIndx)
                                    dComp[cokey] = [mukey, comppct, ratingList, areasym]

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, ratingList, areasym = vals
                        
                        ratingIndx = max(ratingList)  # get highest K Factor from all horizons for this component
                        #PrintMsg("\t" + mukey + ", " + cokey + ", " + str(round(rating, 1)), 1)

                        try:
                            # append component weighted average rating to the mapunit dictionary
                            dMu[mukey].append([comppct, ratingIndx, areasym])

                        except:
                            # create a new mapunit record in the dictionary
                            dMu[mukey] = [[comppct, ratingIndx, areasym]]

                # Write out map unit aggregated rating
                #
                outputValues = [domainValues[0], domainValues[-1]]

                #if tieBreaker == dSDV["tiebreakhighlabel"]:
                oid = 0
                
                for mukey, muVals in dMu.items():
                    oid += 1
                    #muVal = SortData(muVals, 1, 0, True, True)
                    muVal = SortData(muVals, 0, 0, True, True)
                    pct, ratingIndx, areasym = muVal
                    rating = domainValues[ratingIndx]
                    murec = [mukey, pct, rating, areasym]

                    
                    #if mukey == "1427104":
                    #if mukey == "1380525":
                    #    PrintMsg(" \nOutput Table: " + outputTbl, 1)
                    #    PrintMsg("\t" + str(muVals), 1)
                    #    PrintMsg("\t" + str(muVal), 1)
                    #    PrintMsg("\t" + rating, 1)
                    #    PrintMsg("\t" + str(oid) + ", " + str(murec), 1)
                        
                    
                    ocur.insertRow(murec)

                    if not rating is None:
                    #    # save overall max-min values
                        outputValues[0] = min(rating, outputValues[0])
                        outputValues[1] = max(rating, outputValues[1])

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []


## ===================================================================================
def AggregateHz_MaxMin_DCP(gdb, sdvAtt, sdvFld, initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero):
    # Aggregate mapunit-component-horizon data to the map unit level using the highest rating
    # from all horizons. Currently this would only apply to K Factor and dominant component
    
    try:
        arcpy.SetProgressorLabel("Aggregating rating information to the map unit level")
        #
        if bVerbose:
            PrintMsg(" \nCurrent function : " + sys._getframe().f_code.co_name, 1)

        # Create final output table with mukey, comppct_r and sdvFld
        outputTbl = os.path.join(gdb, tblName)
        fldPrecision = max(0, dSDV["attributeprecision"])

        inFlds = ["mukey", "cokey", "comppct_r", "hzdept_r", "hzdepb_r", dSDV["attributecolumnname"].lower(), "areasymbol"]
        outFlds = ["mukey", "comppct_r", dSDV["resultcolumnname"].lower(), "areasymbol"]

        sqlClause =  (None, "ORDER BY mukey ASC, comppct_r DESC, hzdept_r ASC")

        if bZero == False:
            # ignore any null values
            whereClause = "comppct_r >=  " + str(cutOff) + " AND " + dSDV["attributecolumnname"].lower() + " IS NOT NULL"

        else:
            # retrieve null values and convert to zeros during the iteration process
            whereClause = "comppct_r >=  " + str(cutOff)

        if arcpy.Exists(outputTbl):
            arcpy.Delete_management(outputTbl)

        outputTbl = CreateOutputTable(initialTbl, outputTbl, dFieldInfo)

        if outputTbl == "":
            return outputTbl,[]

        dPct = dict()  # sum of comppct_r for each map unit
        dComp = dict() # component level information
        dMu = dict()

        # reset variables for cursor
        sumPct = 0
        sumProd = 0
        meanVal = 0

        with arcpy.da.SearchCursor(initialTbl, inFlds, where_clause=whereClause, sql_clause=sqlClause) as cur:
            with arcpy.da.InsertCursor(outputTbl, outFlds) as ocur:

                for rec in cur:
                    mukey, cokey, comppct, hzdept, hzdepb, val, areasym = rec
                    # top = hzdept
                    # bot = hzdepb
                    # td = top of range
                    # bd = bottom of range

                    if val is not None and hzdept is not None and hzdepb is not None:

                        # Calculate sum of horizon thickness and sum of component ratings for all horizons above bottom
                        try:
                            hzT = min(hzdepb, bot) - max(hzdept, top)   # usable thickness from this horizon

                        except:
                            hzT = 0

                        if hzT > 0:
                            ratingIndx = domainValues.index(val)   # Change KFactor to an index based upon domain order

                            #PrintMsg("\t" + str(aws), 1)

                            if not cokey in dComp:
                                if not mukey in dMu:
                                    dMu[mukey] = cokey

                                    # Create initial entry for this component using the first horiozon CHK
                                    ratingList = [ratingIndx]
                                    dComp[cokey] = [mukey, comppct, ratingList, areasym]

                            elif cokey == dMu[mukey]:
                                # accumulate total thickness and total rating value by adding to existing component values  CHK
                                mukey, comppct, ratingList, areasym = dComp[cokey]
                                
                                if not ratingIndx in ratingList:
                                    ratingList.append(ratingIndx)
                                    dComp[cokey] = [mukey, comppct, ratingList, areasym]

                # get the total number of major components from the dictionary count
                iComp = len(dComp)

                # Read through the component-level data and summarize to the mapunit level

                if iComp > 0:
                    #PrintMsg("\t" + str(top) + " - " + str(bot) + "cm (" + Number_Format(iComp, 0, True) + " components)"  , 0)

                    for cokey, vals in dComp.items():

                        # get component level data
                        mukey, comppct, ratingList, areasym = vals
                        
                        ratingIndx = max(ratingList)  # get highest K Factor from all horizons for this component
                        #PrintMsg("\t" + mukey + ", " + cokey + ", " + str(round(rating, 1)), 1)

                        try:
                            # append component weighted average rating to the mapunit dictionary
                            dMu[mukey].append([comppct, ratingIndx, areasym])

                        except:
                            # create a new mapunit record in the dictionary
                            dMu[mukey] = [[comppct, ratingIndx, areasym]]

                # Write out map unit aggregated rating
                #
                outputValues = [domainValues[0], domainValues[-1]]

                #if tieBreaker == dSDV["tiebreakhighlabel"]:
                oid = 0
                
                for mukey, muVals in dMu.items():
                    oid += 1
                    muVal = SortData(muVals, 1, 0, True, True)              
                    pct, ratingIndx, areasym = muVal
                    rating = domainValues[ratingIndx]
                    murec = [mukey, pct, rating, areasym]
                    #if mukey == "1427104":
                    #    PrintMsg(" \nOutput Table: " + outputTbl, 1)
                    #    PrintMsg("\t" + str(muVals), 1)
                    #    PrintMsg("\t" + str(muVal), 1)
                    #    PrintMsg("\t" + rating, 1)
                    #    PrintMsg("\t" + str(oid) + ", " + str(murec), 1)
                    ocur.insertRow(murec)

                    if not rating is None:
                    #    # save overall max-min values
                        outputValues[0] = min(rating, outputValues[0])
                        outputValues[1] = max(rating, outputValues[1])

        return outputTbl, outputValues

    except MyError, e:
        PrintMsg(str(e), 2)
        return outputTbl, []

    except:
        errorMsg()
        return outputTbl, []

## ===================================================================================
def CreateSoilMap(inputLayer, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV):
    #
    # function that can be called by other scripts
    #
    try:
         # not sure why this isn't being imported at the beginning
        global bVerbose

        bVerbose = False   # hard-coded boolean to print diagnostic messages
        #bVerbose = True

        # Value cache is a global variable used for fact function which is called by ColorRamp
        global fact_cache
        fact_cache = {}

        # Check the ArcGIS Desktop version number
        installInfo = arcpy.GetInstallInfo()
        version = installInfo["Version"][0:4]

        import datetime

        if not version[0:4] in ["10.3", "10.4", "10.5", "10.6"]:
            PrintMsg(" \nArcGIS Desktop version " + version + " does not support the map symbology functions in this tool", 1)

        # Get target gSSURGO database
        global fc, gdb, muDesc, dataType, dbConn, liteCur, tableKeys
        muDesc = arcpy.Describe(inputLayer)
        fc = muDesc.catalogPath                         # full path for input mapunit polygon layer
        fcName = os.path.basename(fc)                   # name of featureclass
        gdb = os.path.dirname(fc)                       # need to expand to handle featuredatasets
        dataType = muDesc.dataType.lower()

        # Set current workspace to the geodatabase
        env.workspace = gdb
        env.overwriteOutput = True
        dbConn = sqlite3.connect(gdb)
        liteCur = dbConn.cursor()

        # get scratchGDB
        scratchGDB = env.scratchGDB

        # Get dictionary of musym values (optional function for use during development)
        dSymbols = GetMapunitSymbols(gdb)

        # Create list of months for use in some queries
        moList = ListMonths()

        # Create dictionary of tables with primary and foreign keys
        tableKeys = GetTableKeys(gdb)

        # arcpy.mapping setup
        #
        # Get map document object
        global mxd, df
        mxd = arcpy.mapping.MapDocument("CURRENT")

        # Get active data frame object
        df = mxd.activeDataFrame

        # Dictionary for aggregation method abbreviations
        #
        #PrintMsg(" \naggMethod = " + str(aggMethod), 1)

        
        global dAgg
        dAgg = dict()
        dAgg["Dominant Component"] = "DCP"
        dAgg["Dominant Condition"] = "DCD"
        dAgg["No Aggregation Necessary"] = ""
        dAgg["Percent Present"] = "PP"
        dAgg["Weighted Average"] = "WTA"
        dAgg["Most Limiting"] = "ML"
        dAgg["Least Limiting"] = "LL"
        dAgg[""] = ""


        # Open sdvattribute table and query for [attributename] = sdvAtt
        # if aggMethod is not already set, get the default method from the sdvattribute table
        global dSDV

        dSDV = GetSDVAtts(gdb, sdvAtt, aggMethod, tieBreaker, bFuzzy, sRV)  # In batch mode, bFuzzy is set to False. This does not work for interps like NCCPI.

        tbl = dSDV["attributetablename"].lower()
        
        if aggMethod == "":
            aggMethod = dSDV["algorithmname"]

        if dSDV["attributetype"].lower() == "interpretation" and dSDV["effectivelogicaldatatype"] == "float":
            # For batch mode processing, override default bFuzzy setting to true. This applies to NCCPI interps.
            bFuzzy == True

        if tieBreaker == "":
            if dSDV["tiebreakrule"] == -1:
                tieBreaker = dSDV["tiebreaklowlabel"]

                if tieBreaker is None or tieBreaker == "":
                    tieBreaker = "Lower"

            else:
                tieBreaker = dSDV["tiebreakhighlabel"]

                if tieBreaker is None:
                    tieBreaker = "Higher"

        # Set null replacement values according to SDV rules
        global nullRating

        if not dSDV["nullratingreplacementvalue"] is None:
            if dSDV["attributelogicaldatatype"].lower() == "integer":
                nullRating = int(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() == "float":
                nullRating = float(dSDV["nullratingreplacementvalue"])

            elif dSDV["attributelogicaldatatype"].lower() in ["string", "choice"]:
                nullRating = dSDV["nullratingreplacementvalue"]

            else:
                nullRating = None

        else:
            nullRating = None

        if dSDV["interpnullsaszerooptionflag"]:
            bZero = True

        # Temporary workaround for NCCPI. Switch from rating class to fuzzy number
        if len(dSDV) == 0:
            raise MyError, "dSDV is not populated"

        # 'Big' 3 tables
        big3Tbls = ["mapunit", "component", "chorizon"]

        #  Create a dictionary to define minimum field list for the tables being used
        #
        global dFields
        dFields = dict()
        dFields["legend"] = ["lkey", "areasymbol"]
        dFields["mapunit"] = ["mukey", "musym", "muname", "lkey"] # confused about lkey. Do I need this here?
        #dFields["mapunit"] = ["mukey", "musym", "muname"]
        dFields["component"] = ["mukey", "cokey", "compname", "comppct_r"]
        dFields["chorizon"] = ["cokey", "chkey", "hzdept_r", "hzdepb_r"]
        dFields["comonth"] = ["cokey", "comonthkey"]
        #dFields["comonth"] = ["comonthKEY", "MONTH"]

        # Create dictionary containing substitute values for missing data
        global dMissing
        dMissing = dict()
        dMissing[tbl] = [nullRating]  
        dMissing["mapunit"] = [None] * len(dFields["mapunit"])
        dMissing["component"] = [None] * (len(dFields["component"]) - 1)  # adjusted number down because of mukey
        dMissing["chorizon"] = [None] * (len(dFields["chorizon"]) - 1)
        dMissing["comonth"] = [None] * (len(dFields["comonth"]) - 1)

        # Dictionary containing sql_clauses for the Big 3
        #
        global dSQL
        dSQL = dict()
        dSQL["mapunit"] = (None, "ORDER BY mukey ASC")
        dSQL["muaggatt"] = (None, "ORDER BY M.mukey ASC")
        dSQL["component"] = (None, "ORDER BY mukey ASC, comppct_r DESC")
        dSQL["comonth"] = (None, "ORDER BY mukey ASC, comppct_r DESC")
        dSQL["chorizon"] = (None, "ORDER BY cokey ASC, hzdept_r ASC")
        dSQL["chtexturegrp"] = (None, "ORDER BY mukey ASC, cokey ASC, hzdept_r ASC")
        dSQL["cointerp"] = (None, "ORDER BY cokey ASC, hzdept_r ASC")
        dSQL["cosoilmoist"] = (None, "ORDER BY mukey ASC, comppct_r DESC")
        dSQL["chaashto"] = (None, "ORDER BY mukey ASC, cokey ASC, hzdept_r ASC")
        dSQL["corestrictions"] = (None, "ORDER BY mukey ASC, comppct_r DESC")
        dSQL["copmgrp"] = (None, "ORDER BY mukey ASC, comppct_r DESC")
        dSQL["chunified"] = (None, "ORDER BY mukey ASC, cokey ASC, hzdept_r ASC")
        

        # Get information about the SDV output result field
        resultcolumn = dSDV["resultcolumnname"].lower()

        primaryconcolname = dSDV["primaryconcolname"]
        if primaryconcolname is not None:
            primaryconcolname = primaryconcolname.upper()

        secondaryconcolname = dSDV["secondaryconcolname"]
        if secondaryconcolname is not None:
            secondaryconcolname = secondaryconcolname.upper()

        # Create dictionary to contain key field definitions
        # AddField_management (in_table, field_name, field_type, {field_precision}, {field_scale}, {field_length}, {field_alias}, {field_is_nullable}, {field_is_required}, {field_domain})
        # TEXT, FLOAT, DOUBLE, SHORT, LONG, DATE, BLOB, RASTER, GUID
        # field_type, field_length (text only),

        global dTypeConversion # Use this only for 'CREATE TABLE' in sqlite3 command.
        dTypeConversion = dict()  # This is the sdvattribute.effectivelogicaldatatype to SQLite datatype conversion dictionary. Key is sdvattribute.effectivelogicaldatatype.
        dTypeConversion["Choice"] = "TEXT"
        dTypeConversion["Narrative Text"] = "TEXT"
        dTypeConversion["VText"] = "TEXT"
        dTypeConversion["String"] = "TEXT"
        dTypeConversion["string"] = "TEXT"
        dTypeConversion["Integer"] = "INTEGER"
        dTypeConversion["Float"] = "REAL"

        global dFieldInfo
        dFieldInfo = dict()

        # Convert original sdvattribute field settings to ArcGIS data types
        if dSDV["effectivelogicaldatatype"].lower() in ['choice', 'string']:
            #
            dFieldInfo[resultcolumn] = ["TEXT", 254]

        elif dSDV["effectivelogicaldatatype"].lower() == 'vtext':
            #
            dFieldInfo[resultcolumn] = ["TEXT", 1024]  # guess

        elif dSDV["effectivelogicaldatatype"].lower() == 'float':
            #dFieldInfo[resultcolumn] = ["DOUBLE", ""]
            dFieldInfo[resultcolumn] = ["FLOAT", ""]  # trying to match muaggatt table data type

        elif dSDV["effectivelogicaldatatype"].lower() == 'integer':
            dFieldInfo[resultcolumn] = ["SHORT", ""]

        elif dSDV["effectivelogicaldatatype"].lower() == 'narrative text':
            dFieldInfo[resultcolumn] = ["TEXT", 1024]  # need to find out where this new data type came from

        else:
            raise MyError, "Failed to set dFieldInfo for " + resultcolumn + ", " + dSDV["effectivelogicaldatatype"]

        dFieldInfo["areasymbol"] = ["TEXT", 20]
        dFieldInfo["lkey"] = ["TEXT", 30]
        dFieldInfo["mukey"] = ["TEXT", 30]
        dFieldInfo["musym"] = ["TEXT", 6]
        dFieldInfo["muname"] = ["TEXT", 175]
        dFieldInfo["cokey"] = ["TEXT", 30]
        dFieldInfo["compname"] = ["TEXT", 60]
        dFieldInfo["chkey"] = ["TEXT", 30]
        dFieldInfo["comppct_r"] = ["SHORT", ""]
        dFieldInfo["hzdept_r"] = ["SHORT", ""]
        dFieldInfo["hzdepb_r"] = ["SHORT", ""]
        dFieldInfo["interphr"] = ["FLOAT", ""]  # trying to match muaggatt data type
        dFieldInfo["objectid"] = ["OID", ""]

        # I don't remember why I did this
        if dSDV["attributetype"].lower() == "interpretation" and (bFuzzy == True or dSDV["effectivelogicaldatatype"].lower() == "float"):
            # For NCCPI?
            dFieldInfo["interphrc"] = ["FLOAT", ""]

        else:
            dFieldInfo["interphrc"] = ["TEXT", 254]

        dFieldInfo["month"] = ["TEXT", 10]
        dFieldInfo["monthseq"] = ["SHORT", ""]
        dFieldInfo["comonthkey"] = ["TEXT", 30]

        #PrintMsg(" \ndFieldInfo: " + str(dFieldInfo), 1)

        # Get possible result domain values from mdstattabcols and mdstatdomdet tables
        # There is a problem because the XML for the legend does not always match case
        # Create a dictionary as backup, but uppercase and use that to store the original values
        #
        # Assume that data types of string and vtext do not have domains

        #PrintMsg(" \nCreating global variables for domainValues and domainValuesUp", 1)
        global domainValues, domainValuesUp

        if not dSDV["attributelogicaldatatype"].lower() in ["string", "vtext"]:
            domainValues = GetRatingDomain(gdb)
            #PrintMsg( "\ndomainValues: " + str(domainValues), 1)
            domainValuesUp = [x.upper() for x in domainValues]    # Is this variable being used?

        else:
            domainValues = list()
            domainValuesUp = list()


        # Get map legend information from the maplegendxml string
        # For some interps, there are case mismatches with the actual rating values. This
        # problem originates in the Rule Manager. This affects dLegend, legendValues, domainValues, dValues and dLabels.
        # At some point I need to use outputValues to fix these.
        #
        global dLegend

        dLegend = GetMapLegend(dSDV, bFuzzy)    # dictionary containing all maplegendxml properties
        #PrintMsg(" \nChecking dLegend values to see if rgb is text:  " + str(dLegend), 1)

        global dLabels
        dLabels = dict()

        #PrintMsg(" \nAttributelogicaldatatype: " + dSDV["attributelogicaldatatype"].lower(), 1)

        if len(dLegend) > 0:
            if not dSDV["effectivelogicaldatatype"].lower() in ["integer", "float"]:
                #
                legendValues = GetValuesFromLegend(dLegend)
                dLabels = dLegend["labels"] # dictionary containing just the label properties such as value and labeltext

                if len(domainValues) == 0:
                    for i in range(1, (len(dLabels) + 1)):
                        domainValues.append(dLabels[i]["value"])

                    #PrintMsg(" \nAdding <Null> to domainValues in CreateSoilMap function", 1)

            else:
                #PrintMsg(" \n", 1)
                legendValues = GetValuesFromLegend(dLegend)

        else:
            # No map legend information in xml. Must be Progressive or using fuzzy values instead of original classes.
            #
            # This causes a problem for NCCPI.
            legendValues = list()  # empty list, no legend
            dLegend["type"] = "1"

        # If there are no domain values, try using the legend values instead.
        # May want to reconsider this move
        #
        if len(legendValues) > 0:
            if len(domainValues) == 0:
                PrintMsg(" \nUsing map legend values to populate domainValues", 1)
                domainValues = legendValues

        # Some problems with the 'Not rated' data value, legend value and sdvattribute setting ("notratedphrase")
        # No perfect solution.
        #
        # Start by cleaning up the not rated value as best possible
        if dSDV["attributetype"].lower() == "interpretation" and bFuzzy == False:
            if not dSDV["notratedphrase"] is None:
                # see if the lowercase value is equivalent to 'not rated'
                if dSDV["notratedphrase"].upper() == 'NOT RATED':
                    dSDV["notratedphrase"] = 'Not rated'

                else:
                    dSDV["notratedphrase"] == dSDV["notratedphrase"][0:1].upper() + dSDV["notratedphrase"][1:].lower()

            else:
                dSDV["notratedphrase"] = 'Not rated' # no way to know if this is correct until all of the data has been processed

            #
            # Next see if the not rated value exists in the domain from mdstatdomdet or map legend values
            bNotRated = False

            for d in domainValues:
                if not dSDV["notratedphrase"] is None and not d is None:
                    if d.upper() == dSDV["notratedphrase"].upper():
                        bNotRated = True

            if bNotRated == False:
                domainValues.insert(0, dSDV["notratedphrase"])

        if not None in domainValues and len(domainValues) > 0:
            # Insert None at beginning or end of domainValues
            #PrintMsg(" \nAdding <Null> to domainValues in CreateSoilMap function", 1)

            if tieBreaker == dSDV["tiebreakhighlabel"]:
                # Put the null value at the beginning of the domain
                #dValues["<None>"] = [0, None]
                domainValues.insert(0, None)

            else:
                # Put the null value at the end of the domain
                #dValues["<None>"] = [len(dValues), None]
                domainValues.append(None)

        if dSDV["ruledesign"] == 2:
            # Flip legend (including Not rated) for suitability interps
            domainValues.reverse()


        # Create a dictionary based upon domainValues or legendValues.
        # This dictionary will use an uppercase-string version of the original value as the key
        #
        global dValues
        dValues = dict()  # Try creating a new dictionary. Key is uppercase-string value. Value = [order, original value]

        # if still no domainValues...
        # Populate dValues dictionary using domainValues
        #
        if len(domainValues) > 0:
            #PrintMsg(" \ndomainValues looks like: " + str(domainValues), 1)

            for val in domainValues:
                if not val is None:
                    #PrintMsg("\tAdding value (" + val + ") with index of " + str(len(dValues)) + " to dValues dictionary", 1)
                    dValues[str(val).upper()] = [len(dValues), val]  # new 02/03

                else:
                    dValues["<Null>"] = [len(dValues), None]

        #PrintMsg(" \ndValues: " + str(dValues), 1)

        # For the attribute column in the sdv_data table we need to translate the sdvattribute value to an ArcGIS field data type
        # If I switch to sqlite3 CREATE TABLE this will need to be modified to use the dTypeConversion.
        #  'Choice' 'Float' 'Integer' 'string' 'String' 'VText'
        #PrintMsg(" \nAdding result column ( " + dSDV["resultcolumnname"].lower() + ") to dFieldInfo", 1)
        
        if dSDV["attributelogicaldatatype"].lower() in ['string', 'choice']:
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["TEXT", dSDV["attributefieldsize"]]

        elif dSDV["attributelogicaldatatype"].lower() == "vtext":
            # Not sure if 254 is adequate
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["TEXT", 254]

        elif dSDV["attributelogicaldatatype"].lower() == "integer":
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["SHORT", ""]

        elif dSDV["attributelogicaldatatype"].lower() == "float":
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["FLOAT", dSDV["attributeprecision"]]

        elif dSDV["attributelogicaldatatype"].lower() == "narrative text":
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["TEXT", 1024]
            
        else:
            raise MyError, "Failed to set dFieldInfo for " + dSDV["resultcolumnname"].lower()

        # Fix datatype for interps using fuzzy values
        if dSDV["effectivelogicaldatatype"].lower() == "float" and dSDV["attributetype"].lower() == "interpretation":
            dFieldInfo[dSDV["attributecolumnname"].lower()] = ["FLOAT", dSDV["attributeprecision"]]
            
        # Identify related tables using mdstatrshipdet and add to tblList
        #
        mdTable = os.path.join(gdb, "mdstatrshipdet")
        mdFlds = ["LTABPHYNAME", "RTABPHYNAME", "LTABCOLPHYNAME", "RTABCOLPHYNAME"]
        level = 0  # table depth
        tblList = list()

        # Make sure mdstatrshipdet table is populated.
        if int(arcpy.GetCount_management(mdTable).getOutput(0)) == 0:
            raise MyError, "Required table (" + mdTable + ") is not populated"

        if (sdvAtt in ["Surface Texture"] or sdvAtt.endswith("(Surface)")) and not (top == 0 and bot == 1):

            if __name__ == "__main__":
                #PrintMsg(" \nRenaming layer...", 1)

                if sdvAtt == "Surface Texture":
                    outputLayer = "Texture"

                elif sdvAtt.endswith("(Surface)"):
                    outputLayer = sdvAtt.replace("(Surface)", ", ")

            else:
                #PrintMsg(" \nKeeping this as a surface layer...", 1)
                outputLayer = sdvAtt
                top = 0
                bot = 1

        else:
            #PrintMsg(" \nKeeping this as the original layer...", 1)
            outputLayer = sdvAtt

        if dAgg[aggMethod] != "":
            outputLayer = outputLayer + " " + dAgg[aggMethod]


        if dSDV["horzlevelattribflag"] == 1:
            if (sdvAtt in ["Surface Texture"] or sdvAtt.endswith("(Surface)")) and not (top == 0 and bot == 1):
                outputLayer = outputLayer + " at " + str(top)  + "cm"

            else:
                outputLayer = outputLayer + ", " + str(top) + " to " + str(bot) + "cm"

            tf = "hzdept_r"
            bf = "hzdepb_r"
            rng = str(tuple(range(top, bot)))

            if (bot - top) == 1:
                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"
                #PrintMsg(" \nhzQuery: " + hzQuery, 1)

            else:
                #rng = str(tuple(range(top, (bot + 1))))
                #rng = str(tuple(range(top, bot)))
                #hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"
                hzQuery = "((" + tf + " BETWEEN " + str(top) + " AND " + str(bot - 1) + " OR " + bf + " BETWEEN " + str(top) + " AND " + str(bot) + ") OR (" + tf + " <= " + str(top) + " AND " + str(bf) + " >= " + str(bot) + "))"

        elif dSDV["cmonthlevelattribflag"] == 1:
            outputLayer = outputLayer + ", " + str(begMo) + " - " + str(endMo)


        elif secCst != "":
            #PrintMsg(" \nAdding primary and secondary constraint to layer name (" + primCst + " " + secCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst + ", " + secCst

        elif primCst != "":
            #PrintMsg(" \nAdding primaryconstraint to layer name (" + primCst + ")", 1)
            outputLayer = outputLayer + ", " + primCst

        # Remove any forward slashes from outputLayer name
        outputLayer = outputLayer.replace("/", "-")


        # Print status
        # Need to modify message when type is Interp and bFuzzy is True
        #
        if __name__ == "__main__":
            if aggMethod == "Minimum or Maximum":
                if tieBreaker == dSDV["tiebreakhighlabel"]:
                    PrintMsg(" \nCreating map of '" + outputLayer + "' using " + os.path.basename(gdb), 0)

                else:
                    PrintMsg(" \nCreating map of '" + outputLayer + "' using " + os.path.basename(gdb), 0)

            elif dSDV["attributetype"].lower() == "interpretation" and bFuzzy == True:
                PrintMsg(" \nCreating map for '" + outputLayer + "' using " + os.path.basename(gdb), 0)

            else:
                PrintMsg(" \nCreating map of '" + outputLayer + "' using " + os.path.basename(gdb), 0)

        # Check to see if the layer already exists and delete if necessary
        layers = arcpy.mapping.ListLayers(mxd, outputLayer, df)

        if len(layers) == 1:
            arcpy.mapping.RemoveLayer(df, layers[0])

        # Create list of tables in the ArcMap TOC. Later check to see if a table
        # involved in queries needs to be removed from the TOC.
        
        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)
        mainTables = ['mapunit', 'component', 'chorizon']

        for tv in tableViews:
            if tv.datasetName.lower() in mainTables:
                # Remove this table view from ArcMap that might cause a conflict with queries
                arcpy.mapping.RemoveTableView(df, tv)

        tableViews = arcpy.mapping.ListTableViews(mxd, "*", df)   # any other table views...
        rtabphyname = "XXXXX"
        mdSQL = "RTABPHYNAME = '" + tbl + "'"  # initial whereclause for mdstatrshipdet

        # Setup initial queries
        while rtabphyname != "mapunit":
            level += 1

            with arcpy.da.SearchCursor(mdTable, mdFlds, where_clause=mdSQL) as cur:
                # This should only select one record

                for rec in cur:
                    ltabphyname = rec[0].lower()
                    rtabphyname = rec[1].lower()
                    ltabcolphyname = rec[2].lower()
                    rtabcolphyname = rec[3].lower()
                    mdSQL = "rtabphyname = '" + ltabphyname.lower() + "'"

                    if bVerbose:
                        PrintMsg("\tGetting level " + str(level) + " information for " + rtabphyname.lower(), 1)

                    if not rtabphyname in tblList:
                        tblList.append(rtabphyname) # save list of tables involved

                    for tv in tableViews:
                        if tv.datasetName.lower() == rtabphyname.lower():
                            # Remove this table view from ArcMap that might cause a conflict with queries
                            arcpy.mapping.RemoveTableView(df, tv)

                    if rtabphyname.lower() == tbl:
                        #
                        # This is the table that contains the rating values
                        #
                        # check for primary and secondary restraints
                        # and use a query to apply them if found.

                        # Begin setting up SQL statement for initial filter
                        # This may be changed further down
                        #
                        primSQL = None

                        if dSDV["attributelogicaldatatype"].lower() in ['integer', 'float']:
                            #
                            if not dSDV["sqlwhereclause"] is None:
                                primSQL = dSDV["sqlwhereclause"]

                            else:
                                primSQL = None

                        if not primaryconcolname is None:
                            # has primary constraint, get primary constraint value
                            if primSQL is None:
                                primSQL = primaryconcolname + " = '" + primCst + "'"

                            else:
                                primSQL = primSQL + " and " + primaryconcolname + " = '" + primCst + "'"

                            if not secondaryconcolname is None:
                                # has primary constraint, get primary constraint value
                                secSQL = secondaryconcolname + " = '" + secCst + "'"
                                primSQL = primSQL + " and " + secSQL


                        #PrintMsg(" \nprimSQL at the very top: " + str(primSQL), 0)

                        # Only one of these tables will be processed in this next section
                        #
                        if tbl == "cointerp":

                            # New code using rulekey and distinterpmd table
                            distinterpTbl = os.path.join(gdb, "distinterpmd")
                            ruleKey = GetRuleKey(distinterpTbl, dSDV["nasisrulename"])

                            if ruleKey == None:
                                raise MyError, "Interp query failed to return key values for " + dSDV["nasisrulename"]

                            # Time for CONUS using different indexes and queries
                            # ruledepth and mrulename 9:53 min
                            # rulekey 4:09 min
                            # ruledepth and mrulekey: 4:03 min
                            #
                            interpSQL = "rulekey IN " + ruleKey                                        # 4:03

                            if primSQL is None:
                                primSQL = interpSQL

                            else:
                                primSQL = interpSQL + " AND " + primSQL

                            dSDV["sqlwhereclause"] = primSQL

                            #PrintMsg(" \nCheck cointerp sql section primSQL: " + primSQL, 1)

                            # Try populating the cokeyList variable here and use it later in ReadTable
                            cokeyList = list()

                        elif tbl == "chorizon":
                            if primSQL is None:
                                primSQL = hzQuery

                            else:
                                primSQL = primSQL + " and " + hzQuery

                        elif tbl == "chunified":
                            if not primSQL is None:
                                primSQL = primSQL + " and rvindicator = 'Yes'"

                            else:
                                primSQL = "rvindicator = 'Yes'"

                        elif tbl == "comonth":
                            if primSQL is None:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = "(monthseq = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = "(monthseq IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            else:
                                if begMo == endMo:
                                    # query for single month
                                    primSQL = primSQL + " AND (monthseq = " + str(moList.index(begMo)) + ")"

                                else:
                                    primSQL = primSQL + " AND (monthseq IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            #PrintMsg(" \nInitial value for primSQL: " + primSQL, 1)

                        elif tbl == "cosoilmoist":
                            # Having problems with NULL values for some months. Need to retain NULL values with query,
                            # but then substitute 201cm in ReadTable
                            #
                            primSQL = dSDV["sqlwhereclause"]
                            #PrintMsg(" \nprimSQL with cosoilmoist: " + primSQL, 1)


                        elif tbl == "mapunit":
                            primSQL = ""
                            
                            
                        if primSQL is None:
                            primSQL = ""

                        if bVerbose:
                            PrintMsg("\tRating table (" + rtabphyname.lower() + ") SQL: " + primSQL, 1)

                        # Create list of necessary fields

                        # Get field list for mapunit or component or chorizon
                        if rtabphyname in big3Tbls:
                            flds = dFields[rtabphyname]
                            if not dSDV["attributecolumnname"].lower() in flds:
                                flds.append(dSDV["attributecolumnname"].lower())

                            dFields[rtabphyname] = flds
                            dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)

                        else:
                            # Not one of the big 3 tables, just use foreign key and sdvattribute column
                            flds = [rtabcolphyname, dSDV["attributecolumnname"].lower()]
                            dFields[rtabphyname] = flds

                            if not rtabphyname in dMissing:
                                dMissing[rtabphyname] = [None] * (len(dFields[rtabphyname]) - 1)
                                #PrintMsg("\nSetting missing fields for " + rtabphyname + " to " + str(dMissing[rtabphyname]), 1)

                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # For tables other than the primary ones.
                            sql = (None, None)

                        if rtabphyname == "mapunit" and aggMethod != "No Aggregation Necessary":
                            # No aggregation necessary?
                            #PrintMsg(" \nProperty includes mapunit", 1)
                            
                            #dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)
                            orderBy = dSQL[tbl][1]

                            #if len(dMapunit) == 0:
                            #    raise MyError, "No mapunit test data for " + sdvAtt

                        elif rtabphyname == "component":
                            #PrintMsg(" \nProperty includes component", 1)
                            orderBy = dSQL[tbl][1]
                            
                            if dSDV["sqlwhereclause"] is not None:
                                if cutOff == 0:
                                    # Having problems with CONUS database. Including comppct_r in the
                                    # where_clause is returning zero records. Found while testing Hydric map. Is a Bug?
                                    # Work around is to put comppct_r part of query last in the string

                                    primSQL =  dSDV["sqlwhereclause"] + " AND compname <> 'NOTCOM'"

                                else:
                                    primSQL = dSDV["sqlwhereclause"] + ' AND "comppct_r" >= ' + str(cutOff)  + " AND compname <> 'NOTCOM'"

                            else:
                                primSQL = "comppct_r >= " + str(cutOff)  + " AND compname <> 'NOTCOM'"


                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            #dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            #if len(dComponent) == 0:
                            #    raise MyError, "No component data for " + sdvAtt  

                        elif rtabphyname == "chorizon":
                            #PrintMsg(" \nProperty includes chorizon", 1)
                            #PrintMsg(" \nchorizon hzQuery: " + hzQuery, 1)
                            
                            if dSDV["sqlwhereclause"] is not None:
                                primSQL = dSDV["sqlwhereclause"] + " AND " + hzQuery
                                

                            else:
                                primSQL = hzQuery
                                
                                
                            #dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)
                            orderBy = dSQL[tbl][1]

                            #if len(dHorizon) == 0:
                            #    raise MyError, "No horizon data for " + sdvAtt

                        else:
                            # This should be one of the other lower level tables containing the requested data
                            #
                            cokeyList = list()  # Try using this to pare down the cointerp table record count
                            orderBy = dSQL[tbl][1]

                        # Save query for use in testQuery
                        attSQL = str(primSQL)
                        dSDV["sqlwhereclause"] = primSQL

                    else:
                        # Bottom section
                        #
                        # This is one of the intermediate tables
                        # Create list of necessary fields
                        # Get field list for mapunit or component or chorizon
                        #       
                        flds = dFields[rtabphyname]
                        
                        try:
                            sql = dSQL[rtabphyname]

                        except:
                            # This needs to be fixed. I have a whereclause in the try and an sqlclause in the except.
                            sql = (None, None)

                        #PrintMsg(" \nResetting primSQL to empty string", 1)
                        #primSQL = ""
                        #PrintMsg(" \n\tReading intermediate table: " + rtabphyname + "   sql: " + str(sql), 1)

                        if rtabphyname == "mapunit":
                            primSQL = ""
                            #dMapunit = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "component":
                            primSQL = "comppct_r >= " + str(cutOff)

                            #PrintMsg(" \nPopulating dictionary from component table", 1)

                            #dComponent = ReadTable(rtabphyname, flds, primSQL, level, sql)

                        elif rtabphyname == "chorizon":
                            tf = "hzdept_r"
                            bf = "hzdepb_r"

                            if (bot - top) == 1:
                                hzQuery = "((" + tf + " = " + str(top) + " or " + bf + " = " + str(bot) + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            else:
                                rng = str(tuple(range(top, bot)))
                                hzQuery = "((" + tf + " in " + rng + " or " + bf + " in " + rng + ") or ( " + tf + " <= " + str(top) + " and " + bf + " >= " + str(bot) + " ) )"

                            #PrintMsg(" \nSetting primSQL for when rtabphyname = 'chorizon' to: " + hzQuery, 1)
                            #dHorizon = ReadTable(rtabphyname, flds, hzQuery, level, sql)

                        elif rtabphyname == "comonth":
                            #PrintMsg(" \nItermediate tables include comonth", 1)

                            # Need to look at the SQL for the other tables as well...
                            if begMo == endMo:
                                # query for single month
                                primSQL = "(monthseq = " + str(moList.index(begMo)) + ")"

                            else:
                                primSQL = "(monthseq IN " + str(tuple(range(moList.index(begMo), (moList.index(endMo) + 1 )))) + ")"

                            #PrintMsg(" \nIntermediate SQL: " + primSQL, 1)
                            #dMonth = ReadTable(rtabphyname, flds, primSQL, level, sql)

                            #if len(dMonth) == 0:
                            #    raise MyError, "No comonth data for " + sdvAtt + " \n "


                        else:
                            PrintMsg(" \n\tUnable to read data from: " + rtabphyname, 1)


            if level > 6:
                raise MyError, "Failed to get table relationships"


        # Create a list of all fields needed for the initial output table. This
        # one will include primary keys that won't be in the final output table.
        #
        if len(tblList) == 0:
            # No Aggregation Necessary, append field to mapunit list
            tblList = ["mapunit", "legend"]

            if dSDV["attributecolumnname"].lower() in dFields["mapunit"]:
                PrintMsg(" \nSkipping addition of field "  + dSDV["attributecolumnname"].lower(), 1)

            else:
                dFields["mapunit"].append(dSDV["attributecolumnname"].lower())

        tblList.reverse()  # Set order of the tables so that mapunit is on top
        tblList.insert(0, "legend")

        if bVerbose:
            PrintMsg(" \nUsing these tables: " + ", ".join(tblList), 1)

        # Create a list of all fields to be used
        global allFields
        allFields = ["areasymbol"]
        allFields.extend(dFields["mapunit"])  # always include the selected set of fields from mapunit table
        #PrintMsg(" \nallFields 1: " + ", ".join(allFields), 1)

        # Substitute resultcolumname for last field in allFields
        for eachTbl in tblList:
            tFields = dFields[eachTbl]
            for fld in tFields:
                if not fld.lower() in allFields:
                    #PrintMsg("\tAdding " + tbl + "." + fld.upper(), 1)
                    allFields.append(fld.lower())

        if not dSDV["attributecolumnname"].lower() in allFields:
            allFields.append(dSDV["attributecolumnname"].lower())

        # Create initial output table (one-to-many)
        # Now created with resultcolumnname
        #
        #PrintMsg(" \nUsing these tables: " + ", ".join(tblList), 1)
        #PrintMsg("Using these allFields: " + ", ".join(allFields), 1)
        tblKeys = GetTableKeys(gdb)
 
        selectKeys = list()

        dAlias = dict()
        dAlias["mapunit"] = "M"
        dAlias["legend"] = "L"
        dAlias["component"] = "CO"
        dAlias["comonth"] = "CM"
        dAlias["chorizon"] = "CZ"
        dAlias["muaggatt"] = "MGT"
        dAlias["cosoilmoist"] = "CSM"
        dAlias["chtexture"] = "CTX"
        dAlias["chtexturegrp"] = "CTG"
        dAlias["cointerp"] = "CTP"
        dAlias["coecoclass"] = "CE"
        dAlias["mutext"] = "MT"
        dAlias["mucropyld"] = "MC"
        dAlias["corestrictions"] = "CR"
        dAlias["copmgrp"] = "CPM"
        dAlias["chaashto"] = "CT"
        dAlias["coforprod"] = "CF"
        dAlias["cosoilmoist"] = "CSM"
        dAlias["chunified"] = "CU"
        
        dPK = dict()  # table aliases used to build queries
        dPK["musym"] = dAlias["mapunit"]
        dPK["muname"] = dAlias["mapunit"]

        #PrintMsg(" \nValue for 'tbl': " + tbl + " \n ", 1)
            
        joinStatements = list()

        #PrintMsg(" \nAssembling information for initial query", 1)

        for i in range(len(tblList) - 1):
            # PrintMsg("\tProcessing " + tblList[i], 0)
            # PrintMsg("\t" + eachTbl + ": " + str(primaryKey) + ",  " + str(foreignKey), 1)
            
            try:
                tbl_1 = str(tblList[i])
                alias_1 = str(dAlias[tbl_1])
                pKey = str(tblKeys[tbl_1][0])
                dPK[pKey] = alias_1 # save alias for parent key of each table in the list
                tbl_2 = str(tblList[(1 + i)])
                alias_2 = str(dAlias[tbl_2])
                fKey = str(tblKeys[tbl_2][1])
                sqlClause = str(dSDV["sqlwhereclause"])
                #PrintMsg("\t1. " + tbl_1 + ", " + alias_1 + ", " + pKey + ", " + sqlClause, 1)
                #PrintMsg("\t2. " + tbl_2 + ", " + alias_2 + ", " + fKey, 1)
                
                if tbl_2 == tbl:
                    # this is the attribute table with the rating value
                    if not sqlClause in ["None", ""] :
                        sql = "LEFT OUTER JOIN " + tbl_2 + " " + alias_2 + " ON " + alias_1 + "." + pKey + " = " + alias_2 + "." + fKey + " \n"
                        sql += "WHERE " + sqlClause + " \n"
                        joinStatements.append(sql)

                    else:
                        sql = "LEFT OUTER JOIN " + tbl_2 + " " + alias_2 + " ON " + alias_1 + "." + pKey + " = " + alias_2 + "." + fKey + " \n"
                        joinStatements.append(sql)
                        
                else:
                    # this is one of the upper level support tables
                    if tbl_1 == "legend":
                        sql = "INNER JOIN " + tbl_2 + " " + alias_2 + " ON " + alias_1 + "." + pKey + " = " + alias_2 + "." + fKey + " \n"
                        joinStatements.append(sql)

                    else:
                        sql = "LEFT OUTER JOIN " + tbl_2 + " " + alias_2 + " ON " + alias_1 + "." + pKey + " = " + alias_2 + "." + fKey + " \n"
                        joinStatements.append(sql)
                    
            except:
                errorMsg()
                break

        selectFields = list()
        
        for eachFld in allFields:
            if eachFld in dPK:
                #PrintMsg(" \n" + dPK[eachFld] + "." + eachFld + ", ", 1)
                if not eachFld == "lkey":
                    selectFields.append(dPK[eachFld] + "." + eachFld )

            else:
                #PrintMsg(" \n" + eachFld + ", ", 1)
                selectFields.append(eachFld)


        # Assemble the final query for SQLite.
        # Question, do I need to apply the sqlClause here, or in the aggregation steps?
        # Leaving it out at this point will leave all data in the 'sdv_data' table.
        #
        sql_1 = ", ".join(selectFields[0:(len(selectFields) -1)])
        sql_2 = ", " + selectFields[-1]

        finalQuery = "SELECT " + sql_1 + sql_2
        finalQuery += " \nFROM legend " + dAlias["legend"]
        finalQuery += " \n" + "".join(joinStatements) + ";"
        #PrintMsg(" \n" + finalQuery + " \n ", 0)

        initialTbl = CreateInitialTable(gdb, allFields, dFieldInfo, finalQuery, dbConn, liteCur)

        if initialTbl is None:
            raise MyError, "Failed to create initial query table"


        if int(arcpy.GetCount_management(initialTbl).getOutput(0)) == 0:
            #
            raise MyError, "Failed to populate " + initialTbl + " table"

        #PrintMsg(" \nGot data for " + initialTbl, 1)

        # Create dictionary for areasymbol (not being used)
        #fcCnt = GetLayerCount(dbConn, liteCur, fc)


        # **************************************************************************
        # Look at attribflags and apply the appropriate aggregation function

        if not arcpy.Exists(initialTbl):
            # Output table was not created. Exit program.
            raise MyError, "xxx Failed to create " + initialTbl + " table"

        #PrintMsg(" \ninitialTbl has " + arcpy.GetCount_management(initialTbl).getOutput(0) + " records", 1)

        # Proceed with aggregation if the intermediate table has data.
        # Add result column to fields list
        # PrintMsg(" \nPreparing data aggregation", 1)
        
        iFlds = len(allFields)
        newField = dSDV["resultcolumnname"].lower()

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)
        allFields[len(allFields) - 1] = newField
        rmFields = ["musym", "compname", "lkey"]

        for fld in rmFields:
            if fld in allFields:
                allFields.remove(fld)

        if newField == "muname":
            allFields.remove("muname")

        #PrintMsg(" \nallFields: " + ", ".join(allFields), 1)

        # Create name for final output table that will be saved to the input gSSURGO database
        #
        global tblName

        if dAgg[aggMethod] == "":
            # No aggregation method necessary
            tblName = "sdv_" + dSDV["resultcolumnname"].title()

        else:
            if secCst != "":
                # Problem with primary and secondary constraint values. These can produce
                # illegal table names
                #
                #tblName = "sdv_" + dSDV["resultcolumnname"] + "_" + dAgg[aggMethod] + "_" + primCst.replace(" ", "_") + "_" + secCst.replace(" ", "_")
                tblName = "sdv_" + dSDV["resultcolumnname"].title() + "_" + primCst.replace(" ", "_") + "_" + secCst.replace(" ", "_")

            elif primCst != "":
                #tblName = "sdv_" + dSDV["resultcolumnname"] + "_" + dAgg[aggMethod] + "_" + primCst.replace(" ", "_")
                tblName = "sdv_" + dSDV["resultcolumnname"].title() + "_" + primCst.replace(" ", "_")

            elif dSDV["horzlevelattribflag"]:
                #tblName = "sdv_" + dSDV["resultcolumnname"] + "_" + dAgg[aggMethod] + "_" + str(top) + "to" + str(bot)
                tblName = "sdv_" + dSDV["resultcolumnname"].title() + "_" + str(top) + "to" + str(bot)

            else:
                #tblName = "sdv_" + dSDV["resultcolumnname"]+ "_" + dAgg[aggMethod]
                tblName = "sdv_" + dSDV["resultcolumnname"].title()

        tblName = arcpy.ValidateTableName(tblName, gdb)

        # Cleanup any duplicate underscores in the table name
        newName = ""
        lastChar = "_"

        for c in tblName:
            if c == lastChar and c == "_":
                # Don't use this character because it is another underscore
                lastChar = c

            else:
                newName += c
                lastChar = c

        if newName[-1] == "_":
            newName = newName[:-1]

        tblName = newName

        # **************************************************************************
        #
        # Aggregation Logic to determine which functions will be used to process the
        # intermediate table and produce the final output table.
        #
        # This is where the outputTbl is populated and outputValues is set
        #
        # PROPERTY
        if dSDV["attributetype"] == "Property":
            # These are all Soil Properties

            # HORIZON
            if dSDV["horzlevelattribflag"] == 1:
                # These are all Horizon Level Soil Properties

                if sdvAtt.startswith("K Factor"):
                    # Need to figure out aggregation method for horizon level  max-min
                    if aggMethod == "Dominant Condition":
                        outputTbl, outputValues = AggregateHz_MaxMin_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(),  initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                    elif aggMethod == "Dominant Component":
                        outputTbl, outputValues = AggregateHz_MaxMin_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(),  initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                elif aggMethod == "Weighted Average":
                    # component aggregation is weighted average

                    if dSDV["attributelogicaldatatype"].lower() in ["integer", "float"]:
                        # Just making sure that these are numeric values, not indexes
                        if dSDV["horzaggmeth"] == "Weighted Average":
                            # Use weighted average for horizon data (works for AWC)
                            outputTbl, outputValues = AggregateHz_WTA_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                        elif dSDV["horzaggmeth"] == "Weighted Sum":
                            # Calculate sum for horizon data (egs. AWS)
                            outputTbl, outputValues = AggregateHz_WTA_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                    else:
                        raise MyError, "12. Weighted Average not appropriate for " + dataType

                elif aggMethod == "Dominant Component":
                    # Need to find or build this function

                    if dSDV["depthqualifiermode"].lower() == 'surface layer':
                    #if sdvAtt.startswith("Surface") or sdvAtt.endswith("(Surface)"):
                        #
                        outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif dSDV["effectivelogicaldatatype"].lower() == "choice":
                        # Indexed value such as kFactor, cannot use weighted average
                        # for horizon properties.
                        outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt,dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif dSDV["horzaggmeth"] == "Weighted Average":
                        #PrintMsg(" \nHorizon aggregation method = WTA and attributelogical datatype = " + dSDV["attributelogicaldatatype"].lower(), 1)
                        outputTbl, outputValues = AggregateHz_DCP_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                    else:
                        raise MyError, "9. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

                elif aggMethod == "Dominant Condition":

                    if dSDV["depthqualifiermode"].lower() == 'surface layer':
                        if dSDV["effectivelogicaldatatype"].lower() == "choice":
                            if bVerbose:
                                PrintMsg(" \nDominant condition for surface-level attribute", 1)
                            outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                        else:
                            outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif dSDV["effectivelogicaldatatype"].lower() in ("float", "integer"):
                        # Dominant condition for a horizon level numeric value is probably not a good idea
                        outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif dSDV["effectivelogicaldatatype"].lower() == "choice" and dSDV["tiebreakdomainname"] is not None:
                        # KFactor (Indexed values)
                        #if bVerbose:
                        #PrintMsg(" \nDominant condition for choice type", 1)
                        outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                    else:
                        raise MyError, "No aggregation calculation selected for DCD"

                elif aggMethod == "Minimum or Maximum":
                    # Need to figure out aggregation method for horizon level  max-min
                    if dSDV["effectivelogicaldatatype"].lower() == "choice":
                        # PrintMsg("\tRunning AggregateCo_MaxMin for " + sdvAtt, 1)
                        outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].lower(),  initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    else:  # These should be numeric, probably need to test here.
                        outputTbl, outputValues = AggregateHz_MaxMin_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, top, bot, bZero)

                else:
                    raise MyError, "Horizon-level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

            # END OF HORIZON


            # COMPONENT
            elif dSDV["complevelattribflag"] == 1:

                #if dSDV["horzlevelattribflag"] == 0:
                # These are Component Level-Only Soil Properties

                if dSDV["cmonthlevelattribflag"] == 0:
                    #
                    #  These are Component Level Soil Properties

                    if aggMethod == "Dominant Component":
                        #PrintMsg(" \n1. domainValues: " + ", ".join(domainValues), 1)
                        outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif aggMethod == "Minimum or Maximum":
                        outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif aggMethod == "Dominant Condition":
                        if bVerbose:
                            PrintMsg(" \nDomain Values are now: " + str(domainValues), 1)

                        if len(domainValues) > 0 and dSDV["tiebreakdomainname"] is not None :  # Problem with NonIrr CapSubCls
                        #if len(domainValues) > 0: # Test failing on Parent Material
                            if bVerbose:
                                PrintMsg(" \n1. aggMethod = " + aggMethod + " and domainValues = " + str(domainValues), 1)

                            outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                            if bVerbose:
                                PrintMsg(" \nOuputValues: " + str(outputValues), 1)

                        else:
                            if bVerbose:
                                PrintMsg(" \n2. aggMethod = " + aggMethod + " and no domainValues", 1)

                            outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif aggMethod == "Minimum or Maximum":
                        #
                        outputTbl, outputValues = AggregateCo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif aggMethod == "Weighted Average" and dSDV["attributetype"].lower() == "property":
                        # Using NCCPI for any numeric component level value?
                        #
                        outputTbl, outputValues = AggregateCo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(),  initialTbl, bNulls, cutOff, tieBreaker, bZero)

                    elif aggMethod == "Percent Present":
                        # This is Hydric?
                        outputTbl, outputValues = AggregateCo_PP_SUM(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                    else:
                        # Don't know what kind of interp this is
                        raise MyError, "5. Component aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

                elif dSDV["cmonthlevelattribflag"] == 1:
                    #
                    # These are Component-Month Level Soil Properties
                    #
                    if dSDV["resultcolumnname"].startswith("Dep2WatTbl"):
                        #PrintMsg(" \nThis is Depth to Water Table (" + dSDV["resultcolumnname"] + ")", 1)

                        if aggMethod == "Dominant Component":
                            outputTbl, outputValues = AggregateCo_DCP_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                        elif aggMethod == "Dominant Condition":
                            outputTbl, outputValues = AggregateCo_Mo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)
                            #raise MyError, "EARLY OUT"

                        elif aggMethod == "Weighted Average":
                            outputTbl, outputValues = AggregateCo_WTA_DTWT(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                        else:
                            # Component-Month such as depth to water table - Minimum or Maximum
                            outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)
                            #raise MyError, "5. Component-comonth aggregation method has not yet been developed "

                    else:
                        # This will be flooding or ponding frequency. In theory these should be the same value
                        # for each month because these are normally annual ratings
                        #
                        # PrintMsg(" \nThis is Flooding or Ponding (" + dSDV["resultcolumnname"] + ")", 1 )
                        #
                        if aggMethod == "Dominant Component":
                            # Problem with this aggregation method (AggregateCo_DCP). The CompPct sum is 12X because of the months.
                            outputTbl, outputValues = AggregateCo_Mo_DCP_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                        elif aggMethod == "Dominant Condition":
                            # Problem with this aggregation method (AggregateCo_DCP_Domain). The CompPct sum is 12X because of the months.
                            outputTbl, outputValues = AggregateCo_Mo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker) # Orig
                            #PrintMsg(" \noutputValues: " + ", ".join(outputValues), 1)

                        elif aggMethod == "Minimum or Maximum":
                            outputTbl, outputValues = AggregateCo_Mo_MaxMin(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                        elif aggMethod == "Weighted Average":
                          outputTbl, outputValues = AggregateCo_Mo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                        else:
                            raise MyError, "Aggregation method: " + aggMethod + "; attibute " + dSDV["attributecolumnname"].lower()

                else:
                    raise MyError, "Attribute level flag problem"
                # END OF COMPONENT


            # MAPUNIT
            elif dSDV["mapunitlevelattribflag"] == 1:
                # This is a Map unit Level Soil Property
                #PrintMsg("Map unit level, no aggregation neccessary", 1)
                outputTbl, outputValues = Aggregate1(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

            # END OF MAPUNIT
            
            else:
                # Should never hit this
                raise MyError, "Unknown depth level '" + aggMethod + "' aggregation method for " + sdvAtt + " has not been developed"

        # INTERPRETATION
        elif dSDV["attributetype"].lower() == "interpretation":

            #PrintMsg(" \nInterpretation with aggMethod = '" + aggMethod + "'", 1)

            if len(domainValues) == 0 and "label" in dLegend:
                # create fake domain using map legend labels and hope they are correct
                labelValues = dLegend["labels"]

                for i in range(1, (len(labelValues) + 1)):
                    domainValues.append(labelValues[i])

            if not 'Not rated' in domainValues and len(domainValues) > 0:
                # These are all Soil Interpretations
                domainValues.insert(0, "Not rated")

            if dSDV["ruledesign"] == 1:
                #
                # This is a Soil Interpretation for Limitations or Risk

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                elif aggMethod == "Dominant Condition":
                    #PrintMsg(" \nInterpretation; aggMethod = " + aggMethod, 1)
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                elif aggMethod == "Weighted Average":
                    # This is an interp that has been set to use fuzzy values
                    outputTbl, outputValues = AggregateCo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)
                    outputValues = [0.0, 1.0]

                else:
                    # Don't know what kind of interp this is
                    #PrintMsg(" \nmapunitlevelattribflag: " + str(dSDV["mapunitlevelattribflag"]) + ", complevelattribflag: " + str(dSDV["complevelattribflag"]) + ", cmonthlevelattribflag: " + str(dSDV["cmonthlevelattribflag"]) + ", horzlevelattribflag: " + str(dSDV["horzlevelattribflag"]) + ", effectivelogicaldatatype: " + dSDV["effectivelogicaldatatype"], 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed ('" + dSDV["algorithmname"] + "', '" + dSDV["horzaggmeth"] + "')"

            elif dSDV["ruledesign"] == 2:
                # This is a Soil Interpretation for Suitability

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD_Domain(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)  # changed this for Sand Suitability

                elif bFuzzy or (aggMethod == "Weighted Average" and dSDV["effectivelogicaldatatype"].lower() == 'float'):
                    # This is NCCPI
                    #PrintMsg(" \nA Aggregate2_NCCPI", 1)
                    #outputTbl, outputValues = Aggregate2_NCCPI(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)
                    # PrintMsg(" \nNCCPI 3", 1)
                    outputTbl, outputValues = AggregateCo_WTA(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)
                    outputValues = [0.0, 1.0]

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                else:
                    # Don't know what kind of interp this is
                    # Friday problem here for NCCPI
                    #PrintMsg(" \n" + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    #PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Aggregation method has not yet been developed (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

            elif dSDV["ruledesign"] == 3:
                # This is a Soil Interpretation for Class. Only a very few interps in the nation use this.
                # Such as MO- Pasture hayland; MT-Conservation Tree Shrub Groups; CA- Revised Storie Index

                if aggMethod == "Dominant Component":
                    outputTbl, outputValues = AggregateCo_DCP(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                elif aggMethod == "Dominant Condition":
                    outputTbl, outputValues = AggregateCo_DCD(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker, bZero)

                elif aggMethod in ['Least Limiting', 'Most Limiting']:
                    #PrintMsg(" \nNot sure about aggregation method for ruledesign = 3", 1)
                    # Least Limiting or Most Limiting Interp
                    outputTbl, outputValues = AggregateCo_Limiting(gdb, sdvAtt, dSDV["attributecolumnname"].lower(), initialTbl, bNulls, cutOff, tieBreaker)

                else:
                    # Don't know what kind of interp this is
                    PrintMsg(" \nRuledesign 3: " + str(dSDV["mapunitlevelattribflag"]) + ", " + str(dSDV["complevelattribflag"]) + ", " + str(dSDV["cmonthlevelattribflag"]) + ", " + str(dSDV["horzlevelattribflag"]) + " -NA2", 1)
                    PrintMsg(aggMethod + "; " + dSDV["effectivelogicaldatatype"], 1)
                    raise MyError, "5. Interp aggregation method has not yet been developed ruledesign 3 (" + dSDV["algorithmname"] + ", " + dSDV["horzaggmeth"] + ")"

            elif dSDV["ruledesign"] is None:
                # This is a Soil Interpretation???
                raise MyError, "Soil Interp with no RuleDesign setting"

            else:
                raise MyError, "No aggregation calculation selected 10"

        # END OF INTERPRETATION
        
        else:
            raise MyError, "Invalid SDV AttributeType: " + str(dSDV["attributetype"])

        # quit if no data is available for selected property or interp
        if outputValues == [0.0, 0.0] or len(outputValues) == 0 or (len(outputValues) == 1 and (outputValues[0] == None or outputValues[0] == "")):

            PrintMsg("\tNo data available for '" + sdvAtt + "'", 1)
            return 2
            #raise MyError, "No data available for '" + sdvAtt + "'"
            #PrintMsg("No data available for '" + sdvAtt + "'", 1)

        elif BadTable(outputTbl):
            #PrintMsg("\tBadTable check, No data available for '" + sdvAtt + "'", 1)
            PrintMsg("\tNo data available for '" + sdvAtt + "'", 1)
            return 2

        #
        # End of Aggregation Logic and Data Processing
        # **************************************************************************
        # **************************************************************************
        #


        # **************************************************************************
        # **************************************************************************
        #
        # Symbology Code Begins Below
        #
        #
        #PrintMsg(" \nPreparing symbology for new map layer", 1)
        
        if bVerbose:
            PrintMsg(" \noutputValues: " + str(outputValues) + " \n ", 1)

            for param in sorted(dSDV):
                setting = dSDV[param]

                if not param in ["attributedescription", "maplegendxml"]:
                    PrintMsg("\t" + param + ":\t" + str(setting), 1)

            PrintMsg(" \n", 0)

        if outputValues != [-999999999, 999999999]:
            #raise MyError, "We have an outputValues problem"


            # Adding new code on 2017-07-27 to try and address case mismatches between data and map legend values
            # This affects dLegend, legendValues, domainValues, dValues and dLabels.

            if bVerbose:
                try:
                    # PrintMsg(" \nSTOPPED HERE", 1)
                    PrintMsg(" \n" + dSDV["attributename"] + "; MapLegendKey: " + dLegend["maplegendkey"] + "; Type: " + dLegend["type"] + " \n ", 1)

                except:
                    # Is dLegend populated??
                    PrintMsg("\nProblem at STOPPED HERE", 1)
                    #pass


            if dSDV["effectivelogicaldatatype"] != 'float' and "labels" in dLegend:
                # NCCPI v2 is failing here since it does not have dLegend["labels"]. Should I be skipping effectivelogicaldatatype == 'float'???
                arcpy.SetProgressorLabel("Getting map legend information")
                # Fix dLegend first
                dLabels = dLegend["labels"]   # NCCPI version 2 is failing here
                end = len(dLabels) + 1

                try:

                    for i in range(1, end):
                        labelInfo = dLabels[i]
                        order = labelInfo["order"]
                        value = labelInfo["value"]
                        label = labelInfo["label"]

                        if value.upper() in dValues:
                            # Compare value to outputValues
                            for dataValue in outputValues:
                                if dataValue.upper() == value.upper():
                                    value = dataValue
                                    labelInfo["value"] = value
                                    dLabels[i] = labelInfo

                    dLegend["labels"] = dLabels

                except:

                    # Fix domainValues
                    try:

                        for dv in domainValues:
                            for dataValue in outputValues:

                                if dataValue.upper() == dv.upper() and dataValue != dv:
                                    indx = domainValues.index(dv)
                                    junk = domainValues.pop(indx)
                                    domainValues.insert(indx, dataValue)

                    except:
                        pass

                    # Fix dValues
                    try:
                        for key, val in dValues.items():
                            seq, dv = val

                            for dataValue in outputValues:

                                if dataValue.upper() == key and dataValue != dv:
                                    indx = domainValues.index(dv)
                                    junk = domainValues.pop(indx)
                                    val =[seq, dataValue]
                                    dValues[key] = val

                    except:
                        pass

                #
                # End of case-mismatch code

            #PrintMsg(" \nLegend name in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)
            if bVerbose:
                PrintMsg("dLegend name: " + str(dLegend["name"]) + ";  type: " + str(dLegend["type"]), 1)

            #if dLegend["name"] != "Random" and muDesc.dataType.lower() == "featurelayer":  #original code
            if dLegend["name"] != "Random":  # trying to get raster to work for Hydric
                if bVerbose:
                    PrintMsg(" \nLegend name in CreateSoilMap: " + dLegend["name"] + " " +  muDesc.dataType.lower(), 1)
                    PrintMsg(" \nChecking dLegend contents: " + str(dLegend), 1)

                global dLayerDefinition  # ??? why global here???
                #PrintMsg(" \nNo labels in dLegend. Could we use ClassBreaksJSON here?", 1)
                dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"].lower(), sdvAtt, bFuzzy)

            elif dLegend["name"] == "Random" and dLegend["type"] == "0" and "labels" in dLegend:
                # Handle Capbility Subclass here
                if bVerbose:
                    PrintMsg(" \nOn the new Cability Subclass track", 1)

                dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"].lower(), sdvAtt, bFuzzy)

            elif dLegend["name"] == "Defined" and dLegend["type"] == 2:
                dLayerDefinition = CreateJSONLegend(dLegend, outputTbl, outputValues, dSDV["resultcolumnname"].lower(), sdvAtt, bFuzzy)

            else:
                # Create empty legend dictionary so that CreateMapLayer function will run for Random Color legend
                #PrintMsg(" \nLegend name in CreateSoilMap: " + dLegend["name"] + " color;  dataType: " +  muDesc.dataType.lower(), 1)
                PrintMsg("Created empty dLegend: " + str(dLegend), 1)

                dLayerDefinition = dict()  #
                # Another test:
                dInfo = dict()
                dInfo["renderer"] = dLegend
                dLayerDefinition["drawingInfo"] = dInfo

            # Create map layer with join using arcpy.mapping
            # sdvAtt, aggMethod, inputLayer
            if arcpy.Exists(outputTbl):
                global tblDesc
                tblDesc = arcpy.Describe(outputTbl)

                #PrintMsg(" \nCreating layer file for " + outputLayer + "....", 0)
                outputLayerFile = os.path.join(os.path.dirname(gdb), os.path.basename(outputLayer.replace(", ", "_").replace(" ", "_")) + ".lyr")

                # Save parameter settings for layer description
                if not dSDV["attributeuom"] is None:
                    parameterString = "Units of Measure: " +  dSDV["attributeuom"]
                    parameterString = parameterString + "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

                else:
                    parameterString = "\r\nAggregation Method: " + aggMethod + ";  Tiebreak rule: " + tieBreaker

                if primCst != "":
                    parameterString = parameterString + "\r\n" + dSDV["primaryconstraintlabel"] + ": " + primCst

                if secCst != "":
                    parameterString = parameterString + "; " + dSDV["secondaryconstraintlabel"] + ": " + secCst

                if dSDV["horzlevelattribflag"]:
                    parameterString = parameterString + "\r\nTop horizon depth: " + str(top)
                    parameterString = parameterString + ";  " + "Bottom horizon depth: " + str(bot)

                elif dSDV["cmonthlevelattribflag"]:
                    parameterString = parameterString + "\r\nMonths: " + begMo + " through " + endMo

                if cutOff is not None:
                    parameterString = parameterString + "\r\nComponent Percent Cutoff:  " + str(cutOff) + "%"

                if dSDV["effectivelogicaldatatype"].lower() in ["float", "integer"]:
                    parameterString = parameterString + "\r\nUsing " + sRV.lower() + " values (" + dSDV["attributecolumnname"] + ") from " + dSDV["attributetablename"].lower() + " table"

                # Finish adding system information to description
                #
                #
                envUser = arcpy.GetSystemEnvironment("USERNAME")
                if "." in envUser:
                    user = envUser.split(".")
                    userName = " ".join(user).title()

                elif " " in envUser:
                    user = envUser.split(" ")
                    userName = " ".join(user).title()

                else:
                    userName = envUser

                # Get today's date
                d = datetime.date.today()
                toDay = d.isoformat()
                #today = datetime.date.today().isoformat()

                parameterString = parameterString + "\r\nGeoDatabase: " + os.path.dirname(fc) + "\r\n" + muDesc.dataType.title() + ": " + \
                os.path.basename(fc) + "\r\nRating Table: " + os.path.basename(outputTbl) + \
                "\r\nLayer File: " + outputLayerFile

                creditsString = "\r\nCreated by " + userName + " on " + toDay + " using script " + os.path.basename(sys.argv[0])

                if arcpy.Exists(outputLayerFile):
                    arcpy.Delete_management(outputLayerFile)

                surveyInfo = ["This is dummy survey data"]

                if muDesc.dataType.lower() == "featurelayer":
                    #PrintMsg(" \ndLayerDefinition has " + str(len(dLayerDefinition)) + " items", 1)
                    #bMapLayer = CreateMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, creditsString, dLayerDefinition, bFuzzy)  # missing dLayerDefinition
                    bMapLayer = CreateMapLayer(fcName, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, creditsString, dLayerDefinition, bFuzzy)  # missing dLayerDefinition
                    #PrintMsg(" \nFinished '" + sdvAtt + "' (" + aggMethod.lower() + ") for " + os.path.basename(gdb) + " \n ", 0)

                elif muDesc.dataType.lower() == "rasterlayer":
                    if bVerbose:
                        PrintMsg(" \ndLayerDefinition: " + str(dLayerDefinition), 1)

                    bMapLayer = CreateRasterMapLayer(inputLayer, outputTbl, outputLayer, outputLayerFile, outputValues, parameterString, creditsString, dLayerDefinition)

                if bMapLayer == False:
                    PrintMsg("\tFailed to create soil map layer ", 0)
                    return 0

                del df, mxd
                arcpy.SetProgressorLabel("")
                return 1

            else:
                raise MyError, "Failed to create summary table and map layer \n "

        else:
            PrintMsg("\tNo data available for " + sdvAtt, 1)
            return 2

    except MyError, e:
        PrintMsg(str(e), 2)
        return 2

    except:
        PrintMsg("Error in CreateSoilMap", 0)
        errorMsg()
        return 0

    finally:
        try:
            del mxd, df

        except:
            pass

        try:
            dbConn.close()
            del dbConn

        except:
            pass

## ===================================================================================
def GetLayerCount(dbConn, liteCur, fc):

    try:
        queryCnt = "SELECT COUNT(*) FROM " + os.path.basename(fc)
        liteCur.execute(queryCnt)
        rec = liteCur.fetchone()
        PrintMsg(" \nGetLayerCount returned a feature count of " + Number_Format(rec[0], 0, True) + " for " + fc, 1)

        return int(rec[0])
    
    except MyError, e:
        PrintMsg(str(e), 2)
        return -1

    except:
        PrintMsg("Error in CreateSoilMap", 0)
        errorMsg()
        return 1
        

## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import arcpy, sys, string, os, traceback, locale,  operator, json, math, random, time
import xml.etree.cElementTree as ET
import sqlite3
#from datetime import datetime

# Create the environment
from arcpy import env

try:
    if __name__ == "__main__":
        inputLayer = arcpy.GetParameterAsText(0)      # Input mapunit polygon layer
        sdvFolder = arcpy.GetParameter(1)             # SDV Folder
        sdvAtt = arcpy.GetParameter(2)                # SDV Attribute
        aggMethod = arcpy.GetParameter(3)             # Aggregation method
        primCst = arcpy.GetParameter(4)               # Primary Constraint choice list
        secCst = arcpy.GetParameter(5)                # Secondary Constraint choice list
        top = arcpy.GetParameter(6)                   # top horizon depth
        bot = arcpy.GetParameter(7)                   # bottom horizon depth
        begMo = arcpy.GetParameter(8)                 # beginning month
        endMo = arcpy.GetParameter(9)                 # ending month
        tieBreaker = arcpy.GetParameter(10)           # tie-breaker setting
        bZero = arcpy.GetParameter(11)                # treat null values as zero
        cutOff = arcpy.GetParameter(12)               # minimum component percent cutoff (integer)
        bFuzzy = arcpy.GetParameter(13)               # Map fuzzy values for interps
        bNulls = arcpy.GetParameter(14)               # Include NULL values in rating summary or weighting (default=True)
        sRV = arcpy.GetParameter(15)                  # flag to switch from standard RV attributes to low or high

        #global bVerbose
        #bVerbose = False   # hard-coded boolean to print diagnostic messages

        bSoilMap = CreateSoilMap(inputLayer, sdvAtt, aggMethod, primCst, secCst, top, bot, begMo, endMo, tieBreaker, bZero, cutOff, bFuzzy, bNulls, sRV)
        PrintMsg("", 0)

except MyError, e:
    PrintMsg(str(e), 2)

except:
    PrintMsg(" \nFinal error gSSURGO_CreateSoilMap", 0)
    errorMsg()

