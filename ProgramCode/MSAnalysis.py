# Second version of an opensource Peak Analysing program
import struct
import datetime
import itertools
import matplotlib.pyplot #  May need to install this library if not present. sudo apt-get install python3-matplotlib
import csv
import os
import bisect

# Tidying for version 0.2: DONE
def OpenFSA(filename):
    """
    Opens the .fsa file and checks it is in a valid ABIF format.
    Returns the binary file object if successful.
    """
    # Open the binary file (relying on builtin error handling to raise an exception that can be handled in calling function)
    binaryfile = open(filename, "rb")
    # Check file is valid ABIF
    signaturebinary = binaryfile.read(6)
    binaryfile.seek(0) # Reset read position
    signatureparsed = struct.unpack('>4sH', signaturebinary[:6])
    if signatureparsed[0].decode() != "ABIF":
        binaryfile.close()
        raise Exception("Error: File does not use ABI formatting.")
    # Check version of ABIF file
    if signatureparsed[1] > 199:
        binaryfile.close()
        raise Exception("Error: Incompatible ABIF file version.")
    return(binaryfile)

### Example use:
# file = OpenFSA('file.fsa')
# Optional use of error handling, or rely upon raised error messages.

# Tidying for version 0.2: DONE (None planned)
def ReturnElement(directoryparsed, fileobject):
    """
    Takes the binary data the ABI formatted file and converts it back to the correct format type.
    """
    ElementType = directoryparsed[2]
    ElementSize = directoryparsed[5] # Size in bytes
    ElementOffset = directoryparsed[6]
    # Get the element in binary form
    if ElementSize < 5:
        # Elements of 4 bytes of less is stored within the Offset value itself
        ElementBinary = ElementOffset
    else:
        # Larger elements are stored at the offset location
        fileobject.seek(ElementOffset)
        ElementBinary = fileobject.read(ElementSize)
    # Convert any data which has been retrieved as a number not binary.
    if isinstance(ElementBinary, int):
        try:
            ElementBinary=(ElementBinary).to_bytes(ElementSize, byteorder='big')
        except:
            # To fix instances when an empty byte is present due to importing whole Offset region
            ElementBinary=(ElementBinary).to_bytes(4, byteorder='big')
            ElementBinary=ElementBinary[:ElementSize]
    # Look up type and convert the binary element into the required format
    if ElementType == 1: # Byte
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>b',ElementBinary)))
    elif ElementType == 2: # String
        Element = ElementBinary.decode()
    elif ElementType == 3: # Word
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>H',ElementBinary)))
    elif ElementType == 4: # Short - Tested
        #Element = struct.unpack('>'+str(int(ElementSize/2))+'h',ElementBinary)
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>h',ElementBinary)))
    elif ElementType == 5: # Long
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>i',ElementBinary)))
    elif ElementType == 7: # Float
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>f',ElementBinary)))        
    elif ElementType == 8: # Double
        Element = tuple(itertools.chain.from_iterable(struct.iter_unpack('>d',ElementBinary)))
    elif ElementType == 10: # Date - Tested
        Element = datetime.date(*struct.unpack('>h2B',ElementBinary))
    elif ElementType == 11: # Time - Tested
        Element = datetime.time(*struct.unpack('>4B',ElementBinary))
    elif ElementType == 13: # Bool
        Element = bool(ElementBinary)
    elif ElementType == 18: # pString - Tested
        Element = ElementBinary[1:].decode()
    elif ElementType == 19: # cString
        Element = ElementBinary[:-1].decode()
    else:
        # print('Warning: No type handler for type: '+str(ElementType))
        Element=ElementBinary
    # Return single value if tuple of 1:
    if isinstance(Element, tuple):
        if len(Element) == 1:
            Element = Element[0]
    return Element

### Suggested improvements
# Where to start!
# Maybe bypass the length function of the tuple check with large elementsize values
# Must be a better approach then long elif statements.
# List of types is not complete (missing Thumb, User and the Legacy formats)
# Using struct.iter_unpack (Py3.4 and newer) may not be as quick (but is easier to write)

# Tidying for version 0.2: DONE (None planned)
def ExtractFSA(fileobject, ExtractTags = ('DATA','DyeN')):
    """
    Parses the ABI formatted file and creates a dictionary structure of the requested data.
    Use: ExtractFSA(<FileObject>,(Tuple of Fieldnames to extract))
    """
    ####### Extract Header
    fileobject.seek(0)
    headerbinary = fileobject.read(128)
    headerparsed = struct.unpack('>4sH4sI2H3I', headerbinary[:30])
    # First 6 bytes of header used to verify file compatibility
    # Next 28 bytes contains file structure information (only 2 fields needed)
    numelements = headerparsed[6] # Number of entries in directory
    dataoffset = headerparsed[8] # Directory location
    # Last 47 bytes are unused
    ###### Scan through directory
    FSAinformation={}
    currententry = 0
    while currententry < numelements:
        fileobject.seek(dataoffset+(currententry*28)) # Each entry 28bytes
        directorybinary = fileobject.read(28)
        directoryparsed = struct.unpack('>4sI2H4I', directorybinary)
        #print(directoryparsed) # Uncomment to see directory structure
        # If the tag is something we are interesed in:
        if directoryparsed[0].decode() in ExtractTags:
            #print(directoryparsed[0].decode()+str(directoryparsed[1]))
            FSAinformation[directoryparsed[0].decode()+str(directoryparsed[1])] = ReturnElement(directoryparsed,fileobject)
        currententry = currententry +1
    return(FSAinformation)

### Use
# DictionaryOutput = ExtractFSA(FileObject, TagNameTuple)

### Example code
# File = OpenFSA('Test.fsa')
# Data = ExtractFSA(File, ('DATA','DyeN','PSZE','RUND','RUNT'))
# print(Data)

# Tidying for version 0.2: DONE (None planned)
def PeakGraph(fileobject):
    """ Creates a matplotlib graph of data channals 1 to 4, and if present 105. """
    # Extract the required data
    GraphData = ExtractFSA(fileobject, ('DATA','DyeN','SMPL','TUBE'))
    # Setup plots
    matplotlib.pyplot.plot(GraphData['DATA1'],'r', label=GraphData['DyeN1'])
    matplotlib.pyplot.plot(GraphData['DATA2'],'g', label=GraphData['DyeN2'])
    matplotlib.pyplot.plot(GraphData['DATA3'],'b', label=GraphData['DyeN3'])
    matplotlib.pyplot.plot(GraphData['DATA4'],'y', label=GraphData['DyeN4'])
    if GraphData['DATA105']:
        # In case ladder not included (as data 105 is optional in specification)
        matplotlib.pyplot.plot(GraphData['DATA105'],'k--', label=GraphData['DyeN5'])
    matplotlib.pyplot.legend()
    try:
        Well = GraphData['TUBE1']
    except:
        Well = 'Unknown'
    try:
        Sample = GraphData['SMPL1']
    except:
        Sample = 'Unknown sample'
    matplotlib.pyplot.title(Sample+": Well "+Well)
    matplotlib.pyplot.show()

###
# Very basic function to plot all the data tracks, useful for problem solving (if not that useful for actual work).

### Use
# PeakGraph(FileObject)

### Example code
# File = OpenFSA('Test.fsa')
# PeakGraph(File)

########## Analysis of Data

# Tidying for version 0.2: DONE
def DetectPeaksIncHeight(fileobject, PeakThreshold = 50, DataTag=0):
    """
    Iterates through the data within a file object producing a dictionary of information on the peaks.
    Dictionary includes Start, End, Max locations and the maximum height.
    """
    PeakData = ExtractFSA(fileobject, ('DATA'))
    # Remove Datasets which are not true raw data as per specifications
    del PeakData['DATA5']
    del PeakData['DATA6']
    del PeakData['DATA7']
    del PeakData['DATA8']
    # Optionally process single dataset argument
    if DataTag:
        SinglePeakData={}
        SinglePeakData[DataTag] = PeakData[DataTag]
        PeakData = SinglePeakData
    # For each Data set detect peaks:
    PeakInformation = {}
    for DataSet in PeakData:
        position = 0
        # Are we starting in a peak?
        if PeakData[DataSet][0] < PeakThreshold:
            inpeak = 0
        else:
            inpeak = 1
            maxposition = position # Starting point for current max
        # Look for peak starts,end and peaks points.
        PeakStart=[]
        PeakEnd=[]
        PeakMaxArray=[]
        PeakMaxHeightArray=[]
        while position < len(PeakData[DataSet]):
            currentheight = PeakData[DataSet][position]
            if inpeak:
                # Iterating through peak in the DATA channel.
                # Detect max and height
                if PeakData[DataSet][position] > PeakData[DataSet][maxposition]:
                    maxposition = position
                # Detect peak end
                if currentheight < PeakThreshold:
                    #print('Peak End '+str(position))
                    PeakEnd.append(position)
                    PeakMaxArray.append(maxposition)
                    PeakMaxHeightArray.append(PeakData[DataSet][maxposition])
                    inpeak = 0
            else:
                if currentheight >= PeakThreshold:
                    #print('Peak Start '+str(position))
                    PeakStart.append(position)
                    inpeak = 1
                    maxposition = position # Starting point for current max
            position = position +1
        # Store array of positions into dictionary ready for reset
        PeakInformation[DataSet+'_START'] = PeakStart
        PeakInformation[DataSet+'_END'] = PeakEnd
        PeakInformation[DataSet+'_MAX'] = PeakMaxArray
        PeakInformation[DataSet+'_HEIGHT'] = PeakMaxHeightArray
    return(PeakInformation)

###### Create calibrated scale using marker:

# Tidying for version 0.2: DONE (Little change needed, may modify output)
def CreateBasepairScale(fileobject, markerfileobject, PeakThreshold=50, MarkerChannel = 'DATA105'):
    """
    Creates a scale that can be used to align peak data to when reporting location.
    Current version returns the scale in a dictionary with other data, might be changed later.
    """
    MarkerPeaks = DetectPeaksIncHeight(fileobject, PeakThreshold, MarkerChannel)
    MarkerLocations = tuple(str.split(markerfileobject.read(),','))
    # Check we have enough peaks for the marker:
    # Make this toggleable and report setting used (ALSO add filter to remove very high peaks at start)
    while len(MarkerLocations) > len(MarkerPeaks[MarkerChannel+'_MAX']):
        PeakThreshold = PeakThreshold-10
        print('Insufficient peaks to map marker locations. Adjusting threshold to '+str(PeakThreshold)+".")
        MarkerPeaks = DetectPeaksIncHeight(fileobject, PeakThreshold, MarkerChannel)
        if PeakThreshold < 1:
            print('Unable to detect sufficient peaks.')
            break
    print('Number of markers: '+str(len(MarkerLocations))+". Number of peaks: "+str(len(MarkerPeaks['DATA105_MAX']))+".")
    # Create a scale using the markers and peaks above
    # Remove unused markers, starting at the start (Most of the additional peaks come from the start)
    ExcessPeaks=len(MarkerPeaks[MarkerChannel+'_MAX'])-len(MarkerLocations)
    while ExcessPeaks:
        del MarkerPeaks[MarkerChannel+'_MAX'][0]
        del MarkerPeaks[MarkerChannel+'_HEIGHT'][0]
        del MarkerPeaks[MarkerChannel+'_START'][0]
        del MarkerPeaks[MarkerChannel+'_END'][0]
        ExcessPeaks=len(MarkerPeaks[MarkerChannel+'_MAX'])-len(MarkerLocations)
    # Align peaks: ideally needs some kind of check scale is linear
    # Pad out scale until first marker:
    scaleposition = 0
    scale = []
    while scaleposition < MarkerPeaks[MarkerChannel+'_MAX'][0]:
        scale.append(0)
        scaleposition = scaleposition+1
    # Start scale
    prevarrayentry=0
    for nextpos in MarkerPeaks[MarkerChannel+'_MAX'][1:]:
        # Divide difference in marker location between number of points and add to scale
        prevpos = MarkerPeaks[MarkerChannel+'_MAX'][prevarrayentry]
        gappoints = nextpos-prevpos
        gapbases = int(MarkerLocations[prevarrayentry+1])-int(MarkerLocations[prevarrayentry])
        delta = gapbases/gappoints
        #print("Gap points: "+str(gappoints)+"Bases: "+str(gapbases))
        #scale.append(int(MarkerLocations[prevarrayentry]))
        currentvalue=int(MarkerLocations[prevarrayentry])
        while scaleposition < nextpos:
            scale.append(currentvalue)
            currentvalue=currentvalue+delta
            #scale.append(currentvalue)
            scaleposition=scaleposition+1
        prevarrayentry=prevarrayentry+1
    # Add final value here (noticed missed off scale from above)
    scale.append(int(MarkerLocations[prevarrayentry]))
    MarkerPeaks['SCALE'] = scale
    #print(scale)
    #print(str(len(scale)))
    return(MarkerPeaks) # Maybe return scale as a list instead of dictionary.

# Above: does re-run a function to generate information already generated. But needed incase threshold needs to change.
# May need alternative method of error handling than used.

### Use
# Calculates scale and adds to dictionary structure on Dye peak information

# Tidying for version 0.2: DONE
# Silly function to make it look nicer
def TablePadding(Size,String):
    """ Takes a string and coloumn width and returns a string of the correct size to line up table columns. """
    if isinstance(String,str):
        StringSize=len(String)
    else:
        StringSize=len(str(String))
    Spacing = Size-StringSize
    padding=""
    while Spacing > 0:
        padding=padding+" "
        Spacing=Spacing-1
    padding=padding+"| "
    return(padding)

# Tidying for version 0.2: DONE - Little to change
# A quickly put together function to run and display results from a .fsa file and marker.
def AnalyseFile(DataFile, MarkerFile):
    """ Quick test function using a single file, as an example in how to view information. """
    # Open files:
    Data = OpenFSA(DataFile)
    Marker = open(MarkerFile,'r') # Add error handling later
    #Calibrate and analyse
    Scale = CreateBasepairScale(Data,Marker) # Using default threshold and channel info
    DataPeaks = DetectPeaksIncHeight(Data,50)
    # Display the results for channels 1-4
    # Quick go at plotting some base points:
    Channels = ['DATA1','DATA2','DATA3','DATA4','DATA105']# Can add DATA105 for marker
    for entry in Channels:
        print('Peak information for: '+entry)
        print("Start   | End     | Height  | MaxPoint(relative) | MaxPoint(bases)")
        count=0
        for start in DataPeaks[entry+'_START']:
            end = DataPeaks[entry+'_END'][count]
            top = DataPeaks[entry+'_MAX'][count]
            height = DataPeaks[entry+'_HEIGHT'][count]
            try:
                base = Scale['SCALE'][int(top)]
            except:
                base = 0
            # Make it look the part
            pad1 = TablePadding(8,start)
            pad2 = TablePadding(8,end)
            pad3 = TablePadding(8,height)
            pad4 = TablePadding(19,top)
            print(str(start)+pad1+str(end)+pad2+str(height)+pad3+str(top)+pad4+str(base))
            count = count+1
    # Produce a graph
    PeakGraph(Data)
    # Make a quick and dirty graph to check calibration
    GraphData = ExtractFSA(Data, ('DATA'))
    matplotlib.pyplot.plot(Scale['SCALE'])
    matplotlib.pyplot.plot(GraphData['DATA105'])
    matplotlib.pyplot.show()

# Function to take a dataset and mask the regions we are not interested in.
def DataMaskingSimple(UnmaskedDict, SelectedRegionsDict, conversionscale=0):
    """ Simple function to crop data to region of interest (upto 3 regions per channel). """
    MaskedData = {}
    # Convert numbers in the selected regions dict from bases to relative positioning
    if conversionscale:
        SelectedRegionsDict = ConvertRegionsDict(SelectedRegionsDict,conversionscale)
    # for loop adding data to the new dictionary
    for key in SelectedRegionsDict:
        MaskedData[key]=[]
        Regions = len(SelectedRegionsDict[key])
        for peak in UnmaskedDict[key]:
            if peak>SelectedRegionsDict[key][0] and peak<SelectedRegionsDict[key][1]:
                MaskedData[key].append(peak)
            if Regions >= 4:
                if peak>SelectedRegionsDict[key][2] and peak<SelectedRegionsDict[key][3]:
                    MaskedData[key].append(peak)
            if Regions >= 6:
                if peak>SelectedRegionsDict[key][4] and peak<SelectedRegionsDict[key][5]:
                    MaskedData[key].append(peak)
    return MaskedData

def ConvertRegionsDict(SelectedRegionsDict,conversionscale):
    """ Takes a dictionary of values per key and converts the basepair locations to data channel locations. """
    #print(SelectedRegionsDict)
    RelativeSelectedRegionsDict={}
    for key in SelectedRegionsDict:
        positionlist=[]
        for entry in SelectedRegionsDict[key]:
            # Check for closest entry in scale
            relativepoistion = bisect.bisect(conversionscale,entry)
            # Create a list with the updated values
            positionlist.append(relativepoistion)
        RelativeSelectedRegionsDict[key]= positionlist
    #print(RelativeSelectedRegionsDict)
    return RelativeSelectedRegionsDict

#### Set of functions to export the peak locations to a CSV file
# NOT comprehensive, doesn't include height of peaks etc.

# Maybe overkill to have this as a seperate function
def ExportAddHeaderSimple(CSVObject, DataFileObject):
    """ Shared function to define and add header to the CSV file. """
    # Produce header:
    DyeNames = ExtractFSA(DataFileObject, ('DyeN')) # Get Dye names
    try:
        Header=['Sample',DyeNames['DyeN1'],DyeNames['DyeN2'],DyeNames['DyeN3'],DyeNames['DyeN4']]
    except:
        Header=['Sample','DATA1','DATA2','DATA3','DATA4']
    CSVObject.writerow(Header)

def ExportAddRowSimple(CSVObject, DataFileObject, MarkerFileObject, SelectedRegionsDict=0):
    """ Shared function to add an entry to a CSV file """
    # Determine well name
    WellNames = ExtractFSA(DataFileObject, ('TUBE'))
    #Calibrate and analyse
    Scale = CreateBasepairScale(DataFileObject,MarkerFileObject) # Using default threshold and channel info
    DataPeaks = DetectPeaksIncHeight(DataFileObject,50)
    # Perform masking of data
    if SelectedRegionsDict:
        DataPeaksOLD=DataPeaks # This step probably isn't needed
        DataPeaks=DataMaskingSimple(DataPeaksOLD, SelectedRegionsDict,Scale['SCALE'])
    # Record the results for channels 1-4
    # Produce content:
    Sample = WellNames['TUBE1'] # Sample name
    Channels = ['DATA1','DATA2','DATA3','DATA4']
    PeakInfo={} # Make new dict of peaks
    for entry in Channels:
        count=0
        PeakInfo[entry]=[]
        PeakArray=[]
        for start in DataPeaks[entry+'_MAX']:
            top = DataPeaks[entry+'_MAX'][count]
            try:
                base = Scale['SCALE'][int(top)]
            except: # Not sure why I put this in a try function. Should always work.
                base = 0
            count = count+1
            # Add to array
            base = int(round(base,0)) # Round to closest int
            PeakArray.append(base)
            try:
                #PeakInfo[DyeNames['DyeN1']]=
                PeakInfo[entry]= PeakArray
            except:
                PeakInfo[entry]= PeakArray
    # Write out Sample name in Sample. entry contains current dye. base contains peak location.
    content = [Sample,PeakInfo['DATA1'],PeakInfo['DATA2'],PeakInfo['DATA3'],PeakInfo['DATA4']]
    CSVObject.writerow(content)
    
def SingleFileExportSimple(DataFile, MarkerFile='MarkersLIZ500.txt', CSVFile='MultiTest.csv', SelectedRegionsDict=0):
    """ Produces a CSV file with a single row with the peak locations for a single well. """
    # Open files:
    Data = OpenFSA(DataFile)
    CSVout = open(CSVFile,'w') # Needs error handling
    Marker = open(MarkerFile,'r') # Add error handling later
    # Produce header:
    writeout = csv.writer(CSVout)
    ExportAddHeaderSimple(writeout, Data) # In it's own function to increase sharing of code
    # Add content:
    ExportAddRowSimple(writeout, Data, Marker, SelectedRegionsDict)
    CSVout.close()
    print("Done")

# Function to iterate through a directory and produce a spreadsheet file.
def MultiFileExportSimple(directory=os.getcwd(), MarkerFile='MarkersLIZ500.txt', CSVFile='MultiTest.csv', SelectedRegionsDict=0):
    """ Produces a CSV file with a row for each FSA file within a directory """
    CSVout = open(CSVFile,'w') # Needs error handling
    # Add in large for loop to iterate through each file.
    counter = 0
    for root,dirs,files in os.walk(directory):
        for filename in files:
            if filename[-3:]=='fsa':
                #print(filename)
                DataFile=os.path.join(root,filename)
                print(DataFile)
                # Open files:
                Data = OpenFSA(DataFile)
                Marker = open(MarkerFile,'r')
                ### First loop only create the header and open the file:
                if counter==0:
                        # Produce header:
                        writeout = csv.writer(CSVout)
                        ExportAddHeaderSimple(writeout, Data) # In it's own function to increase sharing of code
                # Produce content
                ExportAddRowSimple(writeout, Data, Marker, SelectedRegionsDict)
                counter=counter+1
    CSVout.close()
    print('Done')

# Run analysis of data

print ('START OF EXPORT')

# Define area
area = {}
area['DATA1_MAX']=[129,197,213,245] # 6-FAM BTMS0125 and BTMS0045
area['DATA2_MAX']=[114,156] # VIC BT10
area['DATA3_MAX']=[210,240] # NED B96
area['DATA4_MAX']=[118,148] # PET B131
# Start export
#MultiFileExportSimple('/home/mydirectory', 'MarkersLIZ500.txt', 'Plate1Test.csv',area)

print ('END OF EXPORT')

AnalyseFile('SampleA2.fsa','MarkersLIZ500.txt')

# Find out the machine information:
Data = OpenFSA('SampleA2.fsa')
Machine = ExtractFSA(Data, ('MCHN','MODF','MODL','DyeN','RUND'))
print('Machine: '+str(Machine['MCHN1']))
print('Model: '+str(Machine['MODL1']))
print('Run date: '+str(Machine['RUND1']))
