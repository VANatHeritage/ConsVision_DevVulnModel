# ----------------------------------------------------------------------------------------
# procNLCD.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2019-09-05
# Last Edit: 2019-09-11
# Creator:  Kirsten R. Hazler

# Summary:
# A library of functions for processing National Land Cover Database data 
# ----------------------------------------------------------------------------------------

import Helper

def MakeWeightKernel(out_File, nCells, gamma, scale = 100, rounding = 3, ysnInt = 0, centerVal = 0, annDist = 10):
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
	- annDist: The inner radius of the annulus neighborhood. Cells within this radius are set to the centerVal. Cells at the edge of this radius get the maximum weight, and weight decays outwards from there.
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
	weight = numpy.where(d> maxDist, 0, numpy.where(d<=annDist, centerVal*scale, s/(d-annDist)**gamma))
	normWt = scale*weight/numpy.sum(weight)
	if ysnInt == 1:
		normWt = numpy.around(normWt)
	else:
		normWt = numpy.around(normWt, rounding)

	# Write to output file
	outfile = open(out_File, 'w')
	first_line = str(dims[1]) + ' ' + str(dims[0])
	outfile.write(first_line)
	for row in normWt:
		outfile.write('\n')
		for column in row:
			outfile.write(str(column) + '    ')
	outfile.close()
	
	return (s, d, weight, normWt)

def MakeKernelList(out_Dir):
	'''Creates a pre-defined list of parameter lists, to be input into the MultiWeightKernels function
	Parameters:
	- out_Dir: directory in which output text files will be saved.
	'''
	f1 = out_Dir + os.sep + 'k100_025_10.txt'
	f2 = out_Dir + os.sep + 'k100_050_10.txt'
	f3 = out_Dir + os.sep + 'k100_100_10.txt'
	f4 = out_Dir + os.sep + 'k100_150_10.txt'
	f5 = out_Dir + os.sep + 'k100_200_10.txt'
	
	p1 = [f1, 100, 0.25, 100, 3, 0, 0, 10]
	p2 = [f2, 100, 0.50, 100, 3, 0, 0, 10]
	p3 = [f3, 100, 1.00, 100, 3, 0, 0, 10]
	p4 = [f4, 100, 1.50, 100, 3, 0, 0, 10]
	p5 = [f5, 100, 2.00, 100, 3, 0, 0, 10]
	
	parmsList = [p1, p2, p3, p4, p5]
	return parmsList

def MultiWeightKernels(parmsList):
	'''Creates multiple weighted neighborhood kernels using the MakeWeightKernel function, using a list of parameter sets.
	Parameters:
	- parmsList: A list of parameter lists. Each parameter list must contain the set of parameters in order required by the MakeWeightKernel function
	''' 
	for p in parmsList:
		out_File = p[0]
		nCells = p[1]
		gamma = p[2]
		scale = p[3]
		rounding = p[4]
		ysnInt = p[5]
		centerVal = p[6]
		MakeWeightKernel(out_File, nCells, gamma, scale, rounding, ysnInt, centerVal)
	return
		