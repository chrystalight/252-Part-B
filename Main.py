import wave
import matplotlib.pyplot as plt
import scipy
from scipy.io.wavfile import read
import numpy as np
import sys

#NOTE: TO RUN THIS CODE, THE INPUT FILE MUST BE NAMED RECORDING.WAV AND MUST BE IN THE SAME FOLDER AS THIS FILE.  

def convertToMono(frameArray):
    #----------------INPUTS-----------
    #frameArray is a STEREO wav file in the form of a bit array
    #if this function is passed a MONO wav  it will not work
    #---------------------------------
    
    monoFrameArray = []
    
    #deletes every other set of two bits to halve the information in the channel
    for i in range(0,len(frameArray),4):
        monoFrameArray.append(frameArray[i])
        monoFrameArray.append(frameArray[i+1])
        
    #convert the array back to a bytes object for the Wave library
    monoFrameArray = bytes(monoFrameArray)
    return monoFrameArray

def downsample(frameArray):
    #----------------INPUTS-----------
    #frameArray is a MONO, 48khz wav file in the form of a bit array
    #if this function is passed a STEREO wav  it will not work    
    #---------------------------------

    downsampledFrameArray=[]
    
    #will samples to 16khz by dropping every 3rd frame (2 bytes)
    for i in range(0,len(frameArray),6):
        downsampledFrameArray.append(frameArray[i])
        downsampledFrameArray.append(frameArray[i+1])
    downsampledFrameArray = bytes(downsampledFrameArray)
    return downsampledFrameArray


def writeFile(frameArray, fileName):
    #----------------INPUTS-----------
    #frameArray is an array of bytes 
    #fileName is a string that ends in .wav 
    #---------------------------------

    with wave.open(fileName, "wb") as outputFile: 
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
    audio = input_data[1]
    plt.plot(audio)

    #label the axes
    plt.ylabel("Amplitude")
    plt.xlabel("Time")
    #set the title  
    plt.title(title)
    #save the plot
    plt.savefig(title+"png")
    plt.clf()


def processFile():
    #This function will process the input file into a 16khz mono wav file represented as a frame array


    with wave.open("Recording.wav", "rb") as inputFile:
        #opened wav file in such a way that it will automatically close when we are done with it (when the with block ends)
        #good for if we end the program early/terminate it (dont have to manually call close every time)
        frameRate = inputFile.getframerate()
        frameNumber = inputFile.getnframes()
        frameArray = inputFile.readframes(frameNumber)
        nChannels = inputFile.getnchannels()
        
    if nChannels>2:
        raise Exception("There are too many channels! Input either a Mono or a Stero wave file.")
    elif nChannels == 2:
        #we have to cut out half of the data (leave it only with one channel)
        frameArray = convertToMono(frameArray)
    
    if frameRate == 48_000:
        #we have to downsample to 16k
        frameArray = downsample(frameArray)
    elif frameRate != 16_000:
        raise Exception("Check your frame rate! Input either 48k or 16k")
    
    return frameArray

def chunkFile(length, gap):
    # ------------------- INPUTS -------------------
    # input chunk length and gap in frames (ms*16)
    # negative chunkGap will result in frames overlapping (except not really, it explodes the code later on)
    # ----------------------------------------------

    #use scipy to read the processed file (16khz mono) to an array of objects
    inputData = read("processed.wav")

    #object at index 0 of input data is an array
    #audio data is an array of values where each value represents the data in one frame of the wave file
    audioData = inputData[1]

    chunkLength = length
    chunkGap = gap

    #iterate through the audioData array and add lists to a new list, where each list is chunk_frames long
    chunkedFrameArray=[]

    #for every value between 0 and the end of the audio list, start a new chunk, but jump up by chunk length + chunk gap each time
    for i in range(0,len(audioData),chunkLength+chunkGap):

        #chunkHolder is a list that temporarily stores the chunk before we add it as an array to chunkedFrameArray, which is an array of arrays
        chunkHolder=[]
        for j in range(chunkLength):
            #starting at i (j=0) where i is the index of the first value of the active chunk, add each consecutive value till we hit chunk length
            chunkHolder.append(audioData[i+j])
        chunkedFrameArray.append(chunkHolder)
        
    return chunkedFrameArray

def rms(filteredList):
    #calculates RMS as laid out in project outline
    rms = np.sqrt(np.mean(filteredList**2))
    return rms

def filterChunkList(chunkArray):
    # ------------------- INPUTS -------------------
    #chunkArray --> list of sub lists which are each made up of ints, representing a complete wave file
    # ----------------------------------------------   

    #-------------SET FILTER PARAMETERS HERE!!----------------
    minFrequency = 50
    maxFrequency = 7000
    frequencyInterval = 150 
    filteredChunkArray = []
    chunkLength = 160*5
    samplingRate = 16_000
    #---------------------------------------------------------

    for i in range(0, len(chunkArray), 1):
        tempFilterHolder = []
        
        chunkLength = len(chunkArray[i])
        start_time = i*chunkLength
        end_time = start_time + chunkLength - 1
        timeInSamples = np.linspace(start_time, end_time, chunkLength)
        timeInSeconds = timeInSamples/samplingRate

        


        for j in range(minFrequency, maxFrequency, int(frequencyInterval)):
            #apply a bunch of different butterworth filters
            minBandpass = j-(frequencyInterval/2)
            maxBandpass = j+(frequencyInterval/2)
            if minBandpass < 1:
                minBandpass = 1
            sos = scipy.signal.butter(4, [minBandpass, maxBandpass] , btype='bandpass', analog=False, output='sos', fs=16_000) 
            filteredSignal =  scipy.signal.sosfilt(sos, chunkArray[i])

            #calculate the RMS of the butterworth filter
            filteredSignal_RMS = rms(filteredSignal)
            sinArray = np.sin(2*np.pi*j*timeInSeconds)
            synthesizedSignal = filteredSignal_RMS * sinArray

            tempFilterHolder.append(synthesizedSignal)
            
        tempFilterHolderArray = np.array(tempFilterHolder)
        sumOfWaves = np.sum(tempFilterHolderArray, axis=0)
        filteredChunkArray.append(sumOfWaves)
    
    #now: filteredChunkArray holds lists of filtered signals
    return np.concatenate(filteredChunkArray, axis=0)

        
def main():
    plotWave("Recording.wav", "Initial wave form") #plots the file titles output.wav
    frameArray = processFile() #reads the file titled "Recording.wav" and processes it to 1 channel 16khz
    writeFile(frameArray, "processed.wav") #writes the resultant wave form to a file titled "processed.wav"
    plotWave("processed.wav", "Decimated wave form") #plots the file titles processed.wav

    chunked = chunkFile(160,0)
    finalArray = filterChunkList(chunked)
    writeFile(finalArray.astype(np.int16).tobytes(), "output.wav")
    plotWave("output.wav", "10ms chunks, no gaps") #plots the file titled output.wav

    chunkedWithGaps = chunkFile(160, 160)
    chunkedWithGapsArray = filterChunkList(chunkedWithGaps)
    writeFile(chunkedWithGapsArray.astype(np.int16).tobytes(), "output with 10 ms gaps.wav")
    plotWave("output with 10 ms gaps.wav", "10ms chunks, 10ms gaps")

    # chunkedWithOverlaps = chunkFile(160, -160)
    # chunkedWithOverlapsArray = filterChunkList(chunkedWithOverlaps)
    # writeFile(chunkedWithOverlapsArray.astype(np.int16).tobytes(), "output with 10 ms overlap.wav")
    # plotWave("output with 30 ms overlap.wav", "10ms chunks, 10ms overlap")

    biggerChunks = chunkFile (320, 0)
    biggerChunksArray = filterChunkList(biggerChunks)
    writeFile(biggerChunksArray.astype(np.int16).tobytes(), "output with double chunk length.wav")
    plotWave("output with double chunk length.wav", "20ms chunks, no gaps")

main()
