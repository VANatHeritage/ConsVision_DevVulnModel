# ----------------------------------------------------------------------------------------
# procNLCD.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-09-05
# Last Edit: 2019-09-06
# Creator:  Kirsten R. Hazler

# Summary:
# A library of functions for processing National Land Cover Database data 
# ----------------------------------------------------------------------------------------

import Helper

def MakeWeightKernel(out_File, nCells, gamma, scale = 100, rounding = 0, ysnInt = 1, centerVal = 0):
	'''Creates a weighted neighborhood kernel, in which the influence of cells in a circular neighborhood decays with (cell) distance. The output is a properly formatted text file that can be used in the ArcGIS Focal Statistics tool for the "Weight" neighborhood option. See: http://desktop.arcgis.com/en/arcmap/10.3/tools/spatial-analyst-toolbox/how-focal-statistics-works.htm. 
	
	This function is based on the "Development Pressure" variable, defined by equation 2 in a paper by Meentemeyer et al., 2012 (https://www.tandfonline.com/doi/abs/10.1080/00045608.2012.707591. However, it can be broadly applied to any situation in which a weighted neighborhood kernel is needed.
	
	The weight of a neighboring cell is calculated as: 
	w = scale/(distance^gamma)
	
	See also: 
	https://grasswiki.osgeo.org/wiki/Workshop_on_urban_growth_modeling_with_FUTURES#Development_pressure
	https://grass.osgeo.org/grass76/manuals/addons/r.futures.devpressure.html
	
	Parameters:
	- out_File: The output file. Should end in .txt.
	- nCells: The radius, in number of cells, for the kernel neighborhood.
	- gamma: The exponent in the equation above
	- scale: The scaling parameter in the equation above
	- rounding: The number of decimal places to maintain in rounding
	- ysnInt: Indicator of whether the output should be integerized (1) or not (0)
	- centerVal: Indicator of whether focal cell influences the output (1) or not (0)
	'''
	# Set up array and do all the calculations
	diam = 2*nCells + 1
	maxDist = nCells + 0.5
	dims = (diam,diam)
	s = numpy.zeros(dims)
	s += scale
	(ycoords, xcoords) = numpy.where(s)
	ycoords.shape = dims
	xcoords.shape = dims
	midY = ycoords.max()/2
	midX = xcoords.max()/2
	d = numpy.sqrt((xcoords - midX)**2 + (ycoords - midY)**2)
	weight = numpy.where(d> maxDist, 0, numpy.where(d==0, centerVal*scale, s/d**gamma))
	normWt = scale*weight/numpy.sum(weight)
	if ysnInt == 1:
		normWt = numpy.around(normWt)
	else:
		normWt = numpy.around(normWt, rounding)

	# Write to output file
	outfile = open(out_File, 'w')
	first_line = str(dims[1]) + ' ' + str(dims[0])
	outfile.write(first_line)
	for row in weight:
		outfile.write('\n')
		for column in row:
			outfile.write(str(column) + '    ')
	outfile.close()
	
	return (s, d, weight, normWt)

def FocalInfluence