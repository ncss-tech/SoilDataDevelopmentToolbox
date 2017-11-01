# BezierColorRamp.py
#
# Generate a color ramp given a list of colors to
# define the ramp and a number of output colors
# returns a list of lists of [R, G, B] integer values (0-255)

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
def hex_to_RGB(hex):
    ''' "#FFFFFF" -> [255,255,255] '''
    # Pass 16 to the integer function for change of base
    return [int(hex[i:i+2], 16) for i in range(1,6,2)]

## ===================================================================================
def RGB_to_hex(RGB):
    ''' [255,255,255] -> "#FFFFFF" '''
    # Components need to be integers for hex to make sense
    #PrintMsg(" \n" + str(RGB), 1)
    RGB = [int(x) for x in RGB]

    return "#"+"".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in RGB])

## ===================================================================================
def color_dict(gradient):
    # Takes in a list of RGB sub-lists and returns dictionary of
    # colors in RGB and hex form for use in a graphing function
    # defined later on
    return {"hex":[RGB_to_hex(RGB) for RGB in gradient],"r":[RGB[0] for RGB in gradient],"g":[RGB[1] for RGB in gradient],"b":[RGB[2] for RGB in gradient]}

## ===================================================================================
def linear_gradient(start_hex, finish_hex="#FFFFFF", n=10):
    # returns a gradient list of (n) colors between
    # two hex colors. start_hex and finish_hex
    # should be the full six-digit color string,
    # inlcuding the number sign ("#FFFFFF")

    try:
        # Starting and ending colors in RGB form
        s = hex_to_RGB(start_hex)
        f = hex_to_RGB(finish_hex)

        # Initilize a list of the output colors with the starting color
        RGB_list = [s]

        # Calcuate a color at each evenly spaced value of t from 1 to n
        for t in range(1, n):

            # Interpolate RGB vector for color at the current value of t
            curr_vector = [int(s[j] + (float(t)/(n-1))*(f[j]-s[j])) for j in range(3)]

            # Add it to our list of output colors
            RGB_list.append(curr_vector)

        return color_dict(RGB_list)

    except:
        errorMsg()
        return{}

## ===================================================================================
def rand_hex_color(num=1):
    # Generate random hex colors, default is one,
    #  returning a string. If num is greater than
    #  1, an array of strings is returned.
    try:
        colors = [RGB_to_hex([x*255 for x in random.rand(3)]) for i in range(num)]

        if num == 1:
            return colors[0]

        else:
            return colors

    except:
        errorMsg()

## ===================================================================================
def polylinear_gradient(colors, n):
    ''' returns a list of colors forming linear gradients between
      all sequential pairs of colors. "n" specifies the total
      number of desired output colors '''
    try:
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

    except:
        errorMsg()
        return {}

## ===================================================================================
def fact(n, fact_cache):
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

    except:
        errorMsg()

## ===================================================================================
def bernstein(t,n,i, fact_cache):
    ''' Bernstein coefficient '''
    try:
        binom = fact(n, fact_cache)/float(fact(i, fact_cache)*fact(n - i, fact_cache))

        return binom*((1-t)**(n-i))*(t**i)

    except:
        errorMsg()

## ===================================================================================
#def bezier_gradient(colors, n_out, fact_cache):
def bezier_gradient(RGB_list, n_out, fact_cache):
    ''' Returns a "bezier gradient" dictionary
      using a given list of colors as control
      points. Dictionary also contains control
      colors/points. '''

    try:
        # RGB vectors for each color, use as control points
        #RGB_list = [hex_to_RGB(color) for color in colors]
        n = len(RGB_list) - 1
        #PrintMsg(" \nRGB_list: " + str(RGB_list), 1)

        def bezier_interp(t, fact_cache):
            ''' Define an interpolation function
            for this specific curve'''
            # List of all summands

            summands = [ map(lambda x: int(bernstein(t,n,i, fact_cache)*x), c)
                for i, c in enumerate(RGB_list)]

            # Output color
            out = [0,0,0]
            # Add components of each summand together
            for vector in summands:
                for c in range(3):
                    out[c] += vector[c]

            return out

        gradient = [ bezier_interp(float(t)/(n_out-1), fact_cache)
            for t in range(n_out)]

        # Return all points requested for gradient
        return { "gradient": color_dict(gradient), "control": color_dict(RGB_list)}



    except:
        errorMsg()
        return []

## ===================================================================================
def Process(colorNum, colorList):
    # main function

    fact_cache = {}

    try:
        rgbList = list()
        dRGB = dict()
        dRGB["Red"] = [255, 0, 0]
        dRGB["Yellow"] = [255, 255, 0]
        dRGB["Green"] = [0, 255, 0]
        dRGB["Cyan"] = [0, 255, 255]
        dRGB["Blue"] = [0, 0, 255]
        dRGB["Magenta"] = [255, 0, 255]
        masterColors = list()

        processList = list()
        for color in colorList:
            processList.append(dRGB[color])

        #PrintMsg(" \nCreated processList: " + str(processList), 1)

        lastRGB = [-1, -1, -1]

        for i in range(len(processList)):
            try:

                rgb1 = processList[i]
                rgb2 = processList[i + 1]
                #PrintMsg(" \nRGB1-2: " + str(rgb1) + ", " + str(rgb2), 1)
                #hexList = [RGB_to_hex(rgb1), RGB_to_hex(rgb2)]
                RGB_list = [processList[i], processList[i + 1]]
                #dBesier = bezier_gradient(hexList, colorNum, fact_cache)
                dBesier = bezier_gradient(RGB_list, colorNum, fact_cache)

                red = dBesier["gradient"]["r"]
                green = dBesier["gradient"]["g"]
                blue = dBesier["gradient"]["b"]

                for i in range(len(red)):
                    thisRGB = [red[i], green[i], blue[i]]

                    if not thisRGB == lastRGB:
                        masterColors.append([red[i], green[i], blue[i]])

                    lastRGB = thisRGB

            except:
                pass

        skipNum = int(round((len(masterColors) - colorNum) / float(colorNum - 1.0), 0))
        legendColors = list()

        i = 0
        #j = 0
        #masterColors = list()

        while i < len(masterColors):

            legendColors.append(masterColors[i])
            i += (skipNum + 1)
            #j += 1

        #PrintMsg(" \n" + str(legendColors), 1)

        return legendColors


    except:
        errorMsg()
        return []

## ===================================================================================
# MAIN
import arcpy, sys, os, locale, traceback
from numpy import random as rnd

try:

    if __name__ == "__main__":

        colorNum = arcpy.GetParameter(0)   # numbers of colors in map legend
        colorList = arcpy.GetParameter(1) # list of strings representing color names [Red, Yellow, Green, Cyan, Blue]

        legendColors = Process(colorNum, colorListist)


except:
    errorMsg()


