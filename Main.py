import wave
import matplotlib.pyplot as plt
import scipy
from scipy.io.wavfile import read
import numpy as np
import sys

#import matplotlib.pyplot as plt
#import scipy
#inputFile = wave.open("Recording.wav", "rb")

def convertToMono(frameArray):
    #assume it is stereo
    
    monoFrameArray = []
    #print("length of the input frame array is", len(frameArray))
    for i in range(0,len(frameArray),4):
        monoFrameArray.append(frameArray[i])
        monoFrameArray.append(frameArray[i+1])
    monoFrameArray = bytes(monoFrameArray)
    #print("lenght of monoframe array is", len(monoFrameArray))
    return monoFrameArray

def downsample(frameArray):
    #function assumes you're passing it a mono 48khz wav file
    #will downsize to 16khz by dropping every 3rd frame (2 bytes)
    downsampledFrameArray=[]
    for i in range(0,len(frameArray),6):
        downsampledFrameArray.append(frameArray[i])
        downsampledFrameArray.append(frameArray[i+1])
    downsampledFrameArray = bytes(downsampledFrameArray)
    return downsampledFrameArray


def writeFile(frameArray):
    with wave.open("output.wav", "wb") as outputFile: 
        outputFile.setnchannels(1)
        outputFile.setsampwidth(2)
        outputFile.setframerate(16_000)
        outputFile.writeframes(frameArray)

def plotWave(fileName, title):
    # ------------------- INPUTS -------------------
    #input file name as a string: "output.wav"
    #input title as a string: "title"
    # ----------------------------------------------
    input_data = read(fileName)
    print(input_data)
    audio = input_data[1]
    # plot the first 100000 samples
    # we should probably find a better way to pick this length
    plt.plot(audio[0:100000])
    # label the axes
    plt.ylabel("Amplitude")
    plt.xlabel("Time")
    # set the title  
    plt.title(title)
    # display the plot
    plt.show()

    
        
def readFile():
    with wave.open("Recording.wav", "rb") as inputFile:
        #opened wav file in such a way that it will automatically close when we are done with it (when the with block ends)
        #good for if we end the program early/terminate it (dont have to manually call close every time)
        frameRate = inputFile.getframerate()
        frameNumber = inputFile.getnframes()
        frameArray = inputFile.readframes(frameNumber)
        sampWidth = inputFile.getsampwidth()
        nChannels = inputFile.getnchannels()
        
    if nChannels>2:
        raise Exception("oops! error message: there are too many channels")
    elif nChannels == 2:
        #we have to cut out half of the data (leave it only with one channel)
        frameArray = convertToMono(frameArray)
    
    if frameRate == 48_000:
        frameArray = downsample(frameArray)
    elif frameRate != 16_000:
        raise Exception("error: your frame rate needs to be either 48k or 16k")
    
    return frameArray

def chunkFile(length, gap):
    # ------------------- INPUTS -------------------
    #input chunk length and gap in frames (ms*16)
    #a negative chunkGap will result in frames overlapping
    # ----------------------------------------------

    inputData = read("output.wav")
    audioData = inputData[1]
    #audio data is an array of values where each value represents the data in one frame of the wave file
    #we iterate through the values at a rate of 16khz

    chunkLength = length
    chunkGap = gap

    #iterate through the audioData array and add lists to a new list, where each list is chunk_frames long
    chunkedFrameArray=[]

    for i in range(0,len(audioData),chunkLength+chunkGap):
        chunkHolder=[]
        for j in range(chunkLength):
            chunkHolder.append(audioData[i+j])
        chunkedFrameArray.append(chunkHolder)

    #should be a variable called audio data or something
    #go through that list of numbers and split it up into chunks
    return chunkedFrameArray

def rms(filteredList):
    rms = np.sqrt(np.mean(filteredList**2))
    return rms

def filterChunkList(chunkArray):
    # ------------------- INPUTS -------------------
    #chunkArray --> list of sub lists which are each made up of ints, representing a complete wave file
    # ----------------------------------------------   
    minFrequency = 50
    maxFrequency = 6000
    frequencyInterval = 50 
    filteredChunkArray = []

    for i in range(0, len(chunkArray), 1):
        tempFilterHolder = []
        t = i*len(chunkArray[i])

        for j in range(minFrequency, maxFrequency, int(frequencyInterval/2)):
            #apply a bunch of different butterworth filters
            sos = scipy.signal.butter(4, (j-(frequencyInterval/2), j+(frequencyInterval/2)), btype='bandpass', analog=False, output='sos', fs=16_000) 
            filteredSignal =  scipy.signal.sosfilt(sos, chunkArray[i])

            #calculate the RMS of the butterworth filter
            filteredSignal_RMS = rms(filteredSignal)
            synthesizedFilter = []

            for k in range(i*len(chunkArray[i]),i*len(chunkArray[i])+ len(chunkArray)):\
                synthesizedFilter.append(filteredSignal_RMS*np.sin(2*np.pi*j*k))

            tempFilterHolder.append(synthesizedFilter)
        tempFilterHolderArray = np.array(tempFilterHolder)
        sumOfWaves = np.sum(tempFilterHolderArray, axis=0)
        filteredChunkArray.append(sumOfWaves)
    
    #now: filteredChunkArray holds lists of filtered signals
    return np.concatenate(filteredChunkArray, axis=0)

        
def main():
    plotWave("Recording.wav", "Initial wave form") #plots the file titles output.wav
    frameArray = readFile() #reads the file titled "Recording.wav" and processes it to 1 channel 16khz
    #print(frameArray)
    writeFile(frameArray) #writes the resultant wave form to a file titled "output.wav"
    plotWave("output.wav", "Decimated wave form") #plots the file titles output.wav
    chunked = chunkFile(160,0)
    #print(filterChunkList(chunked))
    finalArray = filterChunkList(chunked)
    #print(chunked)
    #fnext up: pass each value in chunk through a BUNCH of bandpass filters, ending up with a list of CHUNKS made up of a list of FILTERED CHUNKS which are themselves lists of int16s
    print("length of new array is", len(finalArray))
    #scipy.io.wavfile.write("finaloutput.wav",16_000, finalArray)
    writeFile(finalArray.astype(np.int16).tobytes())
    plotWave("output.wav", "Final final wave form") #plots the file titled output.wav


main()
