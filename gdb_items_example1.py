# AlexArcPy GitHub GIST
# Read file geodatabase domains with OGR without using arcpy and find what fields have assigned domains 

from __future__ import print_function
import json
import xml.etree.ElementTree as ET
import ogr

gdb_path = r'C:\GIS\data\Adv.gdb'
ds = ogr.Open(gdb_path)
res = ds.ExecuteSQL('select * from GDB_Items')
res.CommitTransaction()

for i in xrange(0, res.GetFeatureCount()):
    item = json.loads(
        res.GetNextFeature().ExportToJson())['properties']['Definition']
    if item:
        xml = ET.fromstring(item)
        if xml.tag == 'GPCodedValueDomain2':
            print(xml.find('DomainName').text)
            print(xml.find('Description').text)
            print(xml.find('FieldType').text)

            for table in xml.iter('CodedValues'):
                for child in table:
                    print(child.find('Code').text, child.find('Name').text)
            print()

        if xml.tag == 'GPRangeDomain2':
            print(xml.find('DomainName').text)
            print(xml.find('Description').text)
            print(xml.find('FieldType').text)
            print(xml.find('MinValue').text)
            print(xml.find('MaxValue').text)

# Domain1
# Desc1
# esriFieldTypeString
# a aa
# b bb

# Domain2
# Desc2
# esriFieldTypeInteger
# 1 aa
# 2 bb
# 3 cc

# Domain3
# Desc3
# esriFieldTypeInteger
# 0
# 100
            
