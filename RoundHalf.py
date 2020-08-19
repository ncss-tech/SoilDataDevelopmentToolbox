# RoundHalf.py

## ===================================================================================
class MyError(Exception):
    pass

## ===================================================================================
def errorMsg():
    try:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        theMsg = tbinfo + "\n" + str(sys.exc_type)+ ": " + str(sys.exc_value)
        PrintMsg(theMsg, 2)

    except:
        PrintMsg("Unhandled error in unHandledException method", 2)
        pass

## ===================================================================================
def round_half_up(f1, d = 0):
    # trying to round to nearest even number
    m = 10.0**d
    #f2 = math.floor((float(f1) * m) + 0.5) / m
    f2 = float(Decimal(str(f1)).quantize(Decimal(str(1 / m)), ROUND_HALF_EVEN))
    
    return f2

## ===================================================================================
## ====================================== Main Body ==================================
# Import modules
import os, sys, locale
from decimal import *

try:
    if __name__ == "__main__":
        # get parameters
        f1 = arcpy.GetParameter(0)           # Input float
        d = arcpy.GetParameter(1)            # number of decimal places to preserve
        f2 = round_half_up(f1, d)

except MyError, e:
    # Example: raise MyError, "This is an error message"
    PrintMsg(str(e), 2)

except:
    errorMsg()
