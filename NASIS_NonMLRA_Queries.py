# NASIS_NonMLRA_Queries.py
#
# ArcGIS 10.1
#
# Steve Peaslee, August 02, 2011
#
# Generates (using Soil Data Access), a set of queries that can be used in
# NASIS to create a local database or selected set for non-MLRA soil survey areas.
# The number of survey areas in each query are limited to prevent failures in NASIS.

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def PrintMsg(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    #
    # Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line
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
        #PrintMsg("Unhandled exception in Number_Format function (" + str(num) + ")", 2)
        return "???"

## ===================================================================================
def StateNames():
    # Create dictionary object containing list of state abbreviations and their names that
    # will be used to name the file geodatabase.
    # For some areas such as Puerto Rico, U.S. Virgin Islands, Pacific Islands Area the
    # abbrevation is

    # NEED TO UPDATE THIS FUNCTION TO USE THE LAOVERLAP TABLE AREANAME. AREASYMBOL IS STATE ABBREV

    try:
        stDict = dict()
        stDict["Alabama"] = "AL"
        stDict["Alaska"] = "AK"
        stDict["American Samoa"] = "AS"
        stDict["Arizona"] =  "AZ"
        stDict["Arkansas"] = "AR"
        stDict["California"] = "CA"
        stDict["Colorado"] = "CO"
        stDict["Connecticut"] = "CT"
        stDict["District of Columbia"] = "DC"
        stDict["Delaware"] = "DE"
        stDict["Florida"] = "FL"
        stDict["Georgia"] = "GA"
        stDict["Territory of Guam"] = "GU"
        stDict["Guam"] = "GU"
        stDict["Hawaii"] = "HI"
        stDict["Idaho"] = "ID"
        stDict["Illinois"] = "IL"
        stDict["Indiana"] = "IN"
        stDict["Iowa"] = "IA"
        stDict["Kansas"] = "KS"
        stDict["Kentucky"] = "KY"
        stDict["Louisiana"] = "LA"
        stDict["Maine"] = "ME"
        stDict["Northern Mariana Islands"] = "MP"
        stDict["Marshall Islands"] = "MH"
        stDict["Maryland"] = "MD"
        stDict["Massachusetts"] = "MA"
        stDict["Michigan"] = "MI"
        stDict["Federated States of Micronesia"] ="FM"
        stDict["Minnesota"] = "MN"
        stDict["Mississippi"] = "MS"
        stDict["Missouri"] = "MO"
        stDict["Montana"] = "MT"
        stDict["Nebraska"] = "NE"
        stDict["Nevada"] = "NV"
        stDict["New Hampshire"] = "NH"
        stDict["New Jersey"] = "NJ"
        stDict["New Mexico"] = "NM"
        stDict["New York"] = "NY"
        stDict["North Carolina"] = "NC"
        stDict["North Dakota"] = "ND"
        stDict["Ohio"] = "OH"
        stDict["Oklahoma"] = "OK"
        stDict["Oregon"] = "OR"
        stDict["Palau"] = "PW"
        stDict["Pacific Basin"] = "PB"
        stDict["Pennsylvania"] = "PA"
        stDict["Puerto Rico and U.S. Virgin Islands"] = "PRUSVI"
        stDict["Rhode Island"] = "RI"
        stDict["South Carolina"] = "SC"
        stDict["South Dakota"] = "SD"
        stDict["Tennessee"] = "TN"
        stDict["Texas"] = "TX"
        stDict["Utah"] = "UT"
        stDict["Vermont"] = "VT"
        stDict["Virginia"] = "VA"
        stDict["Washington"] = "WA"
        stDict["West Virginia"] = "WV"
        stDict["Wisconsin"] = "WI"
        stDict["Wyoming"] = "WY"
        return stDict

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return None

## ===================================================================================
def StateAOI():
    # Create dictionary object containing list of state abbreviations and their geographic regions

    try:
        # "Lower 48 States":
        # "Alaska":
        # "Hawaii":
        # "American Samoa":
        # "Puerto Rico and U.S. Virgin Islands"
        # "Pacific Islands Area"
        #
        dAOI = dict()
        dAOI['Alabama'] = 'Lower 48 States'
        dAOI['Alaska'] = 'Alaska'
        dAOI['American Samoa'] = 'Hawaii'
        dAOI['Arizona'] = 'Lower 48 States'
        dAOI['Arkansas'] = 'Lower 48 States'
        dAOI['California'] = 'Lower 48 States'
        dAOI['Colorado'] = 'Lower 48 States'
        dAOI['Connecticut'] = 'Lower 48 States'
        dAOI['Delaware'] = 'Lower 48 States'
        dAOI['District of Columbia'] = 'Lower 48 States'
        dAOI['Florida'] = 'Lower 48 States'
        dAOI['Georgia'] = 'Lower 48 States'
        dAOI['Hawaii'] = 'Hawaii'
        dAOI['Idaho'] = 'Lower 48 States'
        dAOI['Illinois'] = 'Lower 48 States'
        dAOI['Indiana'] = 'Lower 48 States'
        dAOI['Iowa'] = 'Lower 48 States'
        dAOI['Kansas'] = 'Lower 48 States'
        dAOI['Kentucky'] = 'Lower 48 States'
        dAOI['Louisiana'] = 'Lower 48 States'
        dAOI['Maine'] = 'Lower 48 States'
        dAOI['Maryland'] = 'Lower 48 States'
        dAOI['Massachusetts'] = 'Lower 48 States'
        dAOI['Michigan'] = 'Lower 48 States'
        dAOI['Minnesota'] = 'Lower 48 States'
        dAOI['Mississippi'] = 'Lower 48 States'
        dAOI['Missouri'] = 'Lower 48 States'
        dAOI['Montana'] = 'Lower 48 States'
        dAOI['Nebraska'] = 'Lower 48 States'
        dAOI['Nevada'] = 'Lower 48 States'
        dAOI['New Hampshire'] = 'Lower 48 States'
        dAOI['New Jersey'] = 'Lower 48 States'
        dAOI['New Mexico'] = 'Lower 48 States'
        dAOI['New York'] = 'Lower 48 States'
        dAOI['North Carolina'] = 'Lower 48 States'
        dAOI['North Dakota'] = 'Lower 48 States'
        dAOI['Ohio'] = 'Lower 48 States'
        dAOI['Oklahoma'] = 'Lower 48 States'
        dAOI['Oregon'] = 'Lower 48 States'
        dAOI['Pacific Basin'] = 'Pacific Islands Area'
        dAOI['Pennsylvania'] = 'Lower 48 States'
        dAOI['Puerto Rico and U.S. Virgin Islands'] = 'Lower 48 States'
        dAOI['Rhode Island'] = 'Lower 48 States'
        dAOI['South Carolina'] = 'Lower 48 States'
        dAOI['South Dakota'] = 'Lower 48 States'
        dAOI['Tennessee'] = 'Lower 48 States'
        dAOI['Texas'] = 'Lower 48 States'
        dAOI['Utah'] = 'Lower 48 States'
        dAOI['Vermont'] = 'Lower 48 States'
        dAOI['Virginia'] = 'Lower 48 States'
        dAOI['Washington'] = 'Lower 48 States'
        dAOI['West Virginia'] = 'Lower 48 States'
        dAOI['Wisconsin'] = 'Lower 48 States'
        dAOI['Wyoming'] = 'Lower 48 States'
        dAOI['Northern Mariana Islands'] = 'Pacific Islands Area'
        dAOI['Federated States of Micronesia'] = 'Pacific Islands Area'
        dAOI['Guam'] = 'Pacific Islands Area'
        dAOI['Palau'] = 'Pacific Islands Area'
        dAOI['Marshall Islands'] = 'Pacific Islands Area'

        return dAOI

    except:
        PrintMsg("\tFailed to create list of state abbreviations (CreateStateList)", 2)
        return dAOI

## ===================================================================================
def GetAreasymbols(attName, theTile):
    # Pass a query (from GetSDMCount function) to Soil Data Access designed to get the count of the selected records
    import httplib, urllib2, json, socket

    try:

        # Now using this query to retrieve All surve areas including NOTCOM-only
        #sQuery = "SELECT legend.areasymbol FROM (legend INNER JOIN laoverlap ON legend.lkey = laoverlap.lkey) " + \
        #"INNER JOIN sastatusmap ON legend.areasymbol = sastatusmap.areasymbol " + \
        #"WHERE (((laoverlap.areatypename)='State or Territory') AND ((laoverlap.areaname) Like '" + theTile + "%') AND " + \
        #"((legend.areatypename)='Non-MLRA Soil Survey Area')) ;"

        sQuery = "SELECT legend.areasymbol FROM (legend INNER JOIN laoverlap ON legend.lkey = laoverlap.lkey) \
        INNER JOIN sastatusmap ON legend.areasymbol = sastatusmap.areasymbol \
        WHERE laoverlap.areatypename = 'State or Territory' AND laoverlap.areaname = '" + theTile + "' AND \
        legend.areatypename = 'Non-MLRA Soil Survey Area'"

        # Create empty value list to contain the count
        # Normally the list should only contain one item
        valList = list()

        # PrintMsg("\tQuery for " + theTile + ":  " + sQuery + " \n", 0)

	# NEW POST REST REQUEST BEGINS HERE
	#
        # Uses new HTTPS URL
        # Post Rest returns
        theURL = "https://sdmdataaccess.nrcs.usda.gov"
        url = theURL + "/Tabular/SDMTabularService/post.rest"

        # Create request using JSON, return data as JSON
        dRequest = dict()
        dRequest["format"] = "JSON"
        dRequest["query"] = sQuery
        jData = json.dumps(dRequest)

        # Send request to SDA Tabular service using urllib2 library
        req = urllib2.Request(url, jData)
        resp = urllib2.urlopen(req)
        jsonString = resp.read()

        # Convert the returned JSON string into a Python dictionary.
        data = json.loads(jsonString)
        del jsonString, resp, req

        # Find data section (key='Table')
        valList = list()

        if "Table" in data:
          dataList = data["Table"]  # Data as a list of lists. All values come back as string.

          # Iterate through dataList and reformat the data to create the menu choicelist

          for rec in dataList:
            val = rec[0]
            valList.append(val.encode('ascii'))

        else:
          # No data returned for this query
          raise MyError, "SDA query failed to return requested information: " + sQuery

        if len(valList) == 0:
            raise MyError, "SDA query failed: " + sQuery

        return valList

    except MyError, e:
        # Example: raise MyError, "This is an error message"
        PrintMsg(str(e), 2)
        return []

    except httplib.HTTPException, e:
        PrintMsg("HTTP Error: " + str(e), 2)
        return []

    except socket.error, e:
        raise MyError, "Soil Data Access problem: " + str(e)
        return []

    except:
        #PrintMsg(" \nSDA query failed: " + sQuery, 1)
        errorMsg()
        return []

## ===================================================================================
## ===================================================================================
## MAIN
## ===================================================================================

# Import system modules
import sys, string, os, arcpy, locale, traceback, time
from arcpy import env
import subprocess

# Create the Geoprocessor object
try:

    theTileValues = arcpy.GetParameter(0)           # list of state names
    maxAreas = arcpy.GetParameter(1)                # number of areasymbols for each query string
    bCombined = arcpy.GetParameter(2)               # merge queries so that they are no longer state specific, remove dups
    outputFile = arcpy.GetParameterAsText(3)        # optional output text file to write queries to. Popup.
    
    #import SSURGO_MergeSoilShapefilesbyAreasymbol_GDB
    #import SSURGO_Convert_to_Geodatabase

    # Get dictionary containing 'state abbreviations'
    stDict = StateNames()

    # Get dictionary containing the geographic region for each state
    dAOI = StateAOI()

    # Target attribute. Note that is this case it is lowercase. Thought it was uppercase for SAVEREST?
    # Used for XML parser
    attName = "areasymbol"

    if outputFile != "":
        fh = open(outputFile, "w")

    # Track success or failure for each exported geodatabase
    goodExports = list()
    badExports = list()
    masterList = list()

    # Need to look at option for maintaining a master list of areasymbols, for when multiple states
    # have been selected but you don't want duplicate survey areas downloaded.

    for theTile in theTileValues:
        stAbbrev = stDict[theTile]
        tileInfo = (stAbbrev, theTile)

        if not bCombined:
            PrintMsg(" \n***************************************************************", 0)
            PrintMsg("Generating queries for " + theTile, 0)
            PrintMsg("***************************************************************", 0)

        # Get list of AREASYMBOLs for this state tile from LAOVERLAP table in Soil Data Mart DB
        if theTile == "Puerto Rico and U.S. Virgin Islands":
            valList = GetAreasymbols(attName, "Puerto Rico")
            valList = valList + GetAreasymbols(attName, "Virgin Islands")

        else:
            valList = GetAreasymbols(attName, theTile)

        if len(valList) == 0:
            raise MyError, "Soil Data Access web service failed to retrieve list of areasymbols for " + theTile

        # If the state tile is "Pacific Basin", remove the Areasymbol for "American Samoa"
        # from the list. American Samoa will not be grouped with the rest of the PAC Basin
        if theTile == "Pacific Basin":
            rmVal = GetAreasymbols(attName, "American Samoa")[0]
          
            if rmVal in valList:
                valList.remove(rmVal)

        valList.sort()

        for val in valList:
            if not val in masterList:
                masterList.append(val)

        if not bCombined:                
            queryList = list()
            newList = list()
            
            for areasym in valList:
                if len(newList) < maxAreas:
                    newList.append(areasym)

                else:
                    queryList.append(newList)
                    newList = [areasym]
     
            if len(newList) > 0:
                queryList.append(newList)
                
            cnt = 0

            for query in queryList:
                cnt += 1
                
                if len(query) > 1:
                    sQuery = ", ".join(query)

                elif len(query) == 1:
                    sQuery = query[0]

                rec = sQuery + "     " + stAbbrev + "_QuerySSURGO_" + str(cnt)
                PrintMsg(rec, 0)
                
                if outputFile != "":
                    fh.write(rec + "\n")


        # end of tile for loop



    if bCombined:
        # Combine queries for multiple states. Remove duplicate survey areas.
        # This option is used when creating a multi-state or adhoc database.
        #
        PrintMsg(" \nGenerating queries for " + Number_Format(len(masterList), 0, True) + " survey areas: \n ", 0)
        masterList = list(set(masterList))
        masterList.sort()
        queryList = list()
        newList = list()
        
        for areasym in masterList:
            if len(newList) < maxAreas:
                newList.append(areasym)

            else:
                queryList.append(newList)
                newList = [areasym]
 
        if len(newList) > 0:
            queryList.append(newList)
            
        cnt = 0

        for query in queryList:
            cnt += 1
            
            if len(query) > 1:
                sQuery = ", ".join(query)

            elif len(query) == 1:
                sQuery = query[0]

            rec = sQuery + "     " + "QuerySSURGO_" + str(cnt)
            PrintMsg(rec, 0)
            
            if outputFile != "":
                fh.write(rec + "\n")

            
    else:
        PrintMsg(" \nGenerated  a series of queries for " + Number_Format(len(masterList), 0, True) + " survey areas: \n ", 0)
        
    if outputFile != "":
        fh.close()

        if arcpy.Exists(outputFile):
            PrintMsg(" \nOpening output query file " + outputFile, 0)
            #os.startfile(outputFile)
            subprocess.Popen(["notepad", outputFile])
            
    PrintMsg(" \nFinished state queries \n ", 0)
    
except MyError, err:
    PrintMsg(str(err), 2)

except:
    errorMsg()
