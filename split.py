import sys, os, arcpy
from arcpy import env
env.overwriteOutput = True

#================== Define/Paramaterize these ======================

#gSSURGO db - SAPOLYGON and MUPOLYGON
ssa = r'F:\gSSURGO_FY18\gSSURGO_IA.gdb\SAPOLYGON'
stateSoils = os.path.dirname(arcpy.Describe(ssa).catalogPath) + os.sep + "MUPOLYGON"

#quads to dice things up with
quads = r'D:\Chad\GIS\NATIONAL\V\24kgridshp\t24kgrid.shp'

#destination directory
dest = 'D:\Chad\GIS\PROJECT_18\IA_LINES'

#==================================================================


areaL = []
with arcpy.da.SearchCursor(ssa, "areasymbol") as rows:
    for row in rows:
        val = str(row[0])#.encode('utf-8')
        if not val in areaL:
            areaL.append(val)

areaL.sort()

for area in areaL:

    # just investigating, let's not do a whole state yet
    if area == 'IA197':

        #test if output geodatabase for the survey area exists.
        #if it does we'll assume the required data is present (soil lines, border, lines by quad)
        if not arcpy.Exists(os.path.join(dest, area) + '.gdb'):
            print(os.path.join(dest, area) + '.gdb' + ' does not exist')
            arcpy.management.CreateFileGDB(dest, area)

            #where clause for subsetting MUPOLYGON layer
            wc = "AREASYMBOL = '{area}'".format(area=area)

            #preform the SSA subset from MUPOLYGON
            #if not arcpy.Exists(dest + os.sep + area + ".gdb", "AAAoriginal_" + area):
            arcpy.conversion.FeatureClassToFeatureClass(stateSoils, dest + os.sep + area + ".gdb", "AAAoriginal_" + area, wc)

            #dissolve the subsetted SSA to get the boundary only.  This ensurse it will fit back together (topologically)
            arcpy.management.Dissolve(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area,
                                      dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_border")

            # convert the border to a line that will be used to erase the perimeter of the state from soil polygons
            arcpy.management.FeatureToLine(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_border",
                                           dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_border_line",
                                           attributes="NO_ATTRIBUTES")

            # convert all MUPOLYGONS to lines
            arcpy.management.FeatureToLine(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area,
                                           dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_lines",
                                           attributes="NO_ATTRIBUTES")

            #create several feature layers used in selections
            arcpy.management.MakeFeatureLayer(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_lines", "areaLines")
            arcpy.management.MakeFeatureLayer(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_border_line", "borderLines")
            arcpy.management.MakeFeatureLayer(quads, "quads")

            #select where the SSA border line overlaps with polygons to delete them (soil poly borders)
            arcpy.management.SelectLayerByLocation("areaLines", "SHARE_A_LINE_SEGMENT_WITH", "borderLines")

            # delete the overlapping line features
            arcpy.management.DeleteFeatures("areaLines")

            #select quads that intersect the soil polys (soil lines)
            arcpy.management.SelectLayerByLocation("quads", "INTERSECT", "areaLines")

            #split the lines by the quads -  result are the soil polys (lines) chuncked up by quad
            arcpy.analysis.Split(dest + os.sep + area + ".gdb" + os.sep + "AAAoriginal_" + area + "_lines", "quads",
                                 "NAME", dest + os.sep + area + ".gdb" )

            #delete the 'layers'
            arcpy.management.Delete("areaLines")
            arcpy.management.Delete("quads")

        #iterate thru features and run the simplify process
        arcpy.env.workspace = dest + os.sep + area + ".gdb"
        features = arcpy.ListFeatureClasses()
        features.sort()
        for feature in features:
            if not feature.startswith("AAAoriginal_"):
                arcpy.cartography.SimplifyLine(feature, dest + os.sep + area + ".gdb" + os.sep + feature.replace(" ", "_") + "_pr5",
                                               'POINT_REMOVE',5, collapsed_point_option='NO_KEEP')


#need to add functionality to
#1. merge lines back together
#2. convert merged lines back to polygons
#3. zonal statistics - MAJORITY to get musym back into polys


