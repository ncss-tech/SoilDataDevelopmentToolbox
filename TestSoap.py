# Testing

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
import sys, string, os, arcpy, locale, traceback, httplib, urllib2

try:
    arg = arcpy.GetParameterAsText(0)  # HTTP, HTTPS


    sQuery = "SELECT top 1 areaname FROM SACATALOG WHERE AREASYMBOL = 'NE109'"
    sURL = 'sdmdataaccess.sc.egov.usda.gov'

    sXML = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <RunQuery xmlns="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
      <Query>""" + sQuery + """</Query>
    </RunQuery>
  </soap:Body>
</soap:Envelope>"""

    dHeaders = dict()
    dHeaders['SOAPAction'] = 'http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx/RunQuery'
    #dHeaders['Host'] = 'sdmdataaccess.sc.egov.usda.gov'
    dHeaders['Host'] = 'sdmdataaccess.nrcs.usda.gov'
    dHeaders['Content-Type'] = 'text/xml; charset=utf-8'

    if arg == "HTTP":
        conn = httplib.HTTPConnection(sURL, 80)

    elif arg == "HTTPS":
        conn = httplib.HTTPSConnection(sURL, 443)

    else:
        raise myError, "Problem with HTTP argument"

    tabURL = "/Tabular/SDMTabularService.asmx"
    #tabURL = "Tabular/SDMTabularService.asmx"
    #tabURL = "sdmdataaccess.sc.egov.usda.gov/tabular/SDMTabularService.asmx"

    req = conn.request("POST", tabURL, sXML, dHeaders)
    #req = conn.request("POST", "", sXML, dHeaders)
    resp = conn.getresponse()
    conn.close()
    rHeaders = resp.getheaders()

    status = resp.status
    msg = resp.reason

    PrintMsg(" \nStatus code: " + str(status) + " " + msg, 1)




except:
    errorMsg()
    #conn.close()