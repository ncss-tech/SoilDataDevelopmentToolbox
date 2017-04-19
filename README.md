# SoilDataDevelopmentToolbox
This is an ArcToolbox designed to process and manage FY2017 SSURGO downloads from Web Soil Survey and use them to create gSSURGO databases. Also includes gSSURGO Mapping toolset for creating Soil Data Viewer-style maps and the gSSURGO Reporting toolset. Version date 2017-01-11.

<ul>
<li><a href="https://www.nrcs.usda.gov/wps/PA_NRCSConsumption/download?cid=nrcseprd362254&ext=zip"> Soil Data Management Toolbox</a></li>
<li><a href="https://www.nrcs.usda.gov/wps/PA_NRCSConsumption/download?cid=nrcseprd362255&ext=pdf"> Development User Guide 3.0</a></li>
<li><a href="https://www.nrcs.usda.gov/wps/PA_NRCSConsumption/download?cid=nrcseprd427806&ext=pdf"> gSSURGO Tools Quick Start Guide</a></li>
</ul>

# Download SSURGO Toolset
<ul>
<li>Download SSURGO by Areasymbol - Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. User can a wildcard to query the database by Areasymbol or by age. </li> 
<li>Download SSURGO by Map - Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. A soil survey boundary layer is used to define spatially which surveys will be downloaded.</li>
<li>Download SSURGO by Survey Name - Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. User enters a wildcard to query the database by Areaname. </li>
<li>Process WSS Downloads - Unzips WSS cache files to a new location and renames them to soil_[areasymbol].  </li>
</ul>

# gSSURGO Database Toolset
<ul>
<li>Check gSSURGO - Given a list of file geodatabases, compare the schemas to make sure they are all the same. </li>
<li>Check gSSURGO Attribute Data - Looks for discrepancies in component percent, horizon depths, etc and reports.</li>
<li>Check gSSURGO Inventory - Get size of folders and file count. Useful for recording size of gsSSURGO databases or SSURGO downloads. </li>
<li>Create gSSURGO DB= Custom Tiled - Driver for SSURGO Export to GDB. Uses MO and SSA layers to automatically export SSURGO by MO. </li>
<li>Create gSSSURGO DB - State Tiled -Driver script for creating gSSURGO by state tile using overlap tables (no clipping to state boundary) </li>
<li>Create gSSURGO DB by Map - Tool used to append spatial and tabular data from multiple soil surveys into a single file geodatabase. Based upon map layer selection.</li>
<li>Create gSSURGO Raster - Tool used to export the MUPOLYGON featureclass in the selected geodatabase to a raster layer.</li>
<li>Create gSSURGO Raster - Batch - Batch-mode process for creating MapunitRaster layers for multiple gSSURGO databases. </li>
<li>Create gSSURGO Valu Table - Test version of a script designed to create the valu table using a gSSURGO database. </li>
<li>Create gSSURGO Valu Table - Batch - Batch-mode process for creating gSSURGO Valu tables for multiple gSSURGO databases. </li>
</ul>

# gSSURGO Mapping Toolset
<ul>
<li>Identify Dominant Components - Creates a new table containing map unit key (mukey) and component key (cokey) along with representative component percent (comppct_r) for the component with the highest comppct_r. Ties are handled by assigning the sorting cokey in descending order and taking the first one. </li>
<li>List Map Categories - List SDV Folder and Attribute heirarchy</li>
<li>Map Interpretation Reasons - Method for creating map layers based upon interpretation reasons. </li>
<li>Map Soil Properties and Interpretations - Soil Data Viewer type mapping tool for gSSURGO </li>
<li>Merge Rating Tables - Updates layer file (.lyr) symbology for selected soil map layers, incorporating any changes that the user has made to the original symbology. </li>
<li>Soil Map Descriptions - Lists soil properties and interpretations available in this geodatabase.  </li>
<li>Update Layer File Symbology - Updates layer file (.lyr) symbology for selected soil map layers, incorporating any changes that the user has made to the original symbology.  </li>
</ul>

# gSSURGO Reporting Toolset
<ul>
<li>Interp Rating Reasons - Creates a report based upon the rating reasons map layers created by the 'Map Interpretation Reasons' tool. </li>
<li>Pre-Summary - Creates simple report for gSSURGO Map layer. Information from the different related tables (mapunit, component, horizon) will be incorporated.</li>
<li>Rating Acres - Creates simple acreage report for gSSURGO Map layer. Map layer must be based upon a text or integer field. Floating point values cannot be categorized.</li>
</ul>

# SSURGO Data Management Tools
<ul>
<li>Merge Soil Shapefiles - Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile.</li>
<li>Merge Soil Shapefiles by DB - Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile, matching the contents of a Template database.</li>
<li>Merge Soil Shapefiles by DB - Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile, matching the selection in a survey boundary map layer.</li>
<li>Merge Template Databases - Tool used to append data from a list of selected soil surveys into a single, custom Access database using the text files.</li>
<li>Merge Template Databases by Map - Tool used to append data from multiple soil surveys into a single, custom Access database for the selected surveys in a map layer. </li>
<li>Project SSURGO Datasets - Projects a selected set of SSURGO downloads (WGS 1984 shapefiles) to a new folder with a projected coordinate system.</li>
</ul>

<ul>
<li><a href="https://www.nrcs.usda.gov/wps/portal/nrcs/detail/soils/survey/geo/?cid=nrcs142p2_053628"> Description of Gridded SSURGO Database</a></li>
<li><a href="https://www.nrcs.usda.gov/wps/PA_NRCSConsumption/download?cid=nrcs142p2_051847&ext=pdf"> gSSURGO User Guide</a></li>
<li><a href="https://youtu.be/iJyv71M85WE"> Webinar - gSSURGO for Disaster Recovery Planning</a></li>
</ul>

