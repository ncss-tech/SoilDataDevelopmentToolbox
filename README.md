# SoilDataDevelopmentToolbox


Soil Data Development Toolbox
<ul>
  <li>Download SSURGO Toolset</li>
    <ul><li>Download SSURGO by AreaSymbol ~ Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. User can a wildcard to query the database by Areasymbol or by age.</li></ul>
    <ul><li>Download SSURGO by Map ~ Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. A soil survey boundary layer is used to define spatially which surveys will be downloaded.</li>
    <ul><li>Download SSURGO by Survey Name ~ Use Soil Data Access and Web Soil Survey download page to get SSURGO datasets. User enters a wildcard to query the database by Areaname.</li>
    <ul><li>Process WSS Downloads ~ Unzips WSS cache files to a new location and renames them to soil_[areasymbol].
    <li>gSSURGO Database Toolset</li>
   <ul> <li>Clip Soils by Polygon ~ Designed to facilitate clipping of large polygon layers</li></li>
    <ul><li>Create gSSURGO DB - Custom Tiled ~ Driver for SSURGO Export to GDB. Uses MO and SSA layers to automatically export SSURGO by MO.</li>
    <ul><li>Create gSSUROG DB - State Tiled ~ Driver script for creating gSSURGO by state tile using overlap tables (no clipping to state boundary)</li>
    <ul><li>Create gSSURGO DB by Map ~ Tool used to append spatial and tabular data from multiple soil surveys into a single file geodatabase. Based upon map layer selection.</li>
    <ul><li>Create gSSURGO Raster ~ Tool used to export the MUPOLYGON featureclass in the selected geodatabase to a raster layer.</li>
    <ul><li>Create gSSURGO Raster - Batch ~ Batch-mode process for creating MapunitRaster layers for multiple gSSURGO databases.</li>
    <ul><li>Create gSSURGO Valu Table ~ Test version of a script designed to create the valu table using a gSSURGO database. </li>
    <ul><li>Create gSSURGO Valu TAble - Batch ~ Batch-mode process for creating gSSURGO Valu tables for multiple gSSURGO databases.</li>
  <li>gSSURGO Mapping Toolset</li>
   <ul><li> Add National Map Unit Symbol ~ Add NationalMusym to an input featureclass with MUKEY as the join</li></li>
    <ul><li>Create Soil Map ~ Soil Data Viewer type mapping tool for gSSURGO</li>
   <ul><li> Create Soil Maps - Batch ~ Soil Data Viewer type mapping tool for gSSURGO.</li>
   <ul><li> Identify Dominant Components ~ Creates a new table containing map unit key (mukey) and component key (cokey) along with representative component percent (comppct_r) for the component with the highest comppct_r. Ties are handled by assigning the sorting cokey in descending order and taking the first one.</li>
    <ul><li>List Available Soil Maps ~ List SDV Folder and Attribute heirarchy</li>
    <ul><li>Map Interprtation Reasons ~ Method for creating map layers based upon interpretation reasons.</li>
    <ul><li>Merge Rating Tables ~ Allows user the merge ratings from individual soil map layers into a single table.</li>
    <ul><li>Update Layer File Symbology ~ Updates layer file (.lyr) symbology for selected soil map layers, incorporating any changes that the user has made to the original symbology.</li>
  <li>gSSURGO Reporting Toolset</li>
    <ul><li>Interp Rating Reasons ~ Creates a report based upon the rating reasons map layers created by the 'Map Interpretation Reasons' tool.</li></li>
   <ul><li>Pre-Summary ~ Creates simple report for gSSURGO Map layer. Information from the different related tables (mapunit, component, horizon) will be incorporated.</li>
  <ul> <li> Rating Acres ~ Creates simple acreage report for gSSURGO Map layer. Map layer must be based upon a text or integer field. Floating point values cannot be categorized.</li>
 <li> SSURGO Data Management Toolset</li>
    <ul><li>Merge Soil Shapefiles ~ Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile.</li>
   <ul><li> Merge Soil Shapefiles by DB ~ Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile, matching the contents of a Template database.</li>
    <ul><li>Merge Soil Shapefiles by Map ~ Tool used to append soil polygon shapefiles from multiple soil surveys into a single shapefile, matching the selection in a survey boundary map layer.</li>
    <ul><li>Merge Template Databases ~ Tool used to append data from a list of selected soil surveys into a single, custom Access database using the text files.</li>
   <ul><li> Merge Template Databases by Map ~ Tool used to append data from multiple soil surveys into a single, custom Access database for the selected surveys in a map layer.</li>
   <ul> <li>Project SSURGO Datasets ~ Projects a selected set of SSURGO downloads (WGS 1984 shapefiles) to a new folder with a projected coordinate system.</li>
</ul>
