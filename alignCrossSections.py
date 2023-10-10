"""
﻿Cross-section aligner v1.0.0
Copyright(C) 2023 R. van Eenige, Leiden University Medical Center
and individual contributors.

Reference:
If you choose to use this code please cite: van der Vaart JI, van Eenige R, Rensen PCN, Kooijman S. Atherosclerosis: an overview of mouse models and a detailed methodology to quantify lesions in the aortic root. (2023)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import cv2 #install with "pip3 install opencv-python"
import numpy as np #install with "pip3 install numpy"
import os
import itertools
import time
import sys
from datetime import datetime
import getopt
import pkg_resources

def print_help():
    help_text = """
Usage:
alignCrossSections.py -r <reference directory> -t <target directory> -x <threshold reference images> -y <threshold target images> [-s <treshold change steps>] [-m <treshold max change>] [-b <scale factor boundaries>] [-o <output-directory>] [-l <logfile-directory>] [-p] [-h]

Options:
  -h, --help                            Show this help message and exit
  -r, --reference-directory=DIR         Set the directory for reference images (required)
  -t, --target-directory=DIR            Set the directory for target images (required)
  -x, --threshold-reference-images=THRESHOLD
                                        Set the threshold for reference images (required, 0-255)
  -y, --threshold-target-images=THRESHOLD
                                        Set the threshold for target images (required, 0-255)
  -s, --treshold-change-steps=STEPS     Set the threshold change steps (optional, default: 2)
  -m, --treshold-max-change=MAX         Set the threshold max change (optional, default: 20)
  -b, --scale-factor-boundaries=MIN,MAX Set the scale factor boundaries (optional, default: 0.95,1.05)
  -o, --output-directory=OUTPUT_DIR     Set the output directory (optional, default: ./Alignments/'target-directory-basename'_Alignments/)
  -l, --logfile-directory=LOGFILE_DIR   Set the logfile path (optional, default: ./)
  -p, --suppress-overlap-images         Supress the creation of overlap images

Reference:
If you choose to use this code please cite: van der Vaart JI, van Eenige R, Rensen PCN, Kooijman S. Atherosclerosis: an overview of mouse models and a detailed methodology to quantify lesions in the aortic root. (2023)
"""
    print(help_text)
    
def main(argv):
    referenceFilesDirectory = ""
    targetFilesDirectory = ""
    outputDirectory = ""
    logFileDirectory = ""
    tresholdReferenceImages = -1 # Value between 0 and 255
    tresholdTargetImages = -1 # Value between 0 and 255
    tresholdChangeSteps = 2 # A positive integer, thresholds will be changed with steps of given size
    tresholdMaxChange = 20 # A positive integer, can take any value but only makes sense between 0 and 255
    scaleFactorBoundaries = [0.95, 1.05] # Allowed scale factor range
    suppressOverlapImages = False
    
    try:
        opts, args = getopt.getopt(argv,"hr:t:x:y:s:m:b:o:l:p",["help", "reference-subfolder=","reference-directory=","target-subfolder=","target-directory=","threshold-reference-images=","threshold-target-images=", "treshold-change-steps=", "treshold-max-change=", "scale-factor-boundaries=", "output-directory", "--logfile-directory", "--suppress-overlap-images"])
    except getopt.GetoptError:
        print_help()
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit()
        elif opt in ("-r", "--reference-directory"):
            referenceFilesDirectory = os.path.normpath(arg)
        elif opt in ("-t", "--target-directory"):
            targetFilesDirectory = os.path.normpath(arg)
        elif opt in ("-x", "--threshold-reference-images"):
            tresholdReferenceImages = abs(int(arg))
        elif opt in ("-y", "--threshold-target-images"):
            tresholdTargetImages = abs(int(arg))
        elif opt in ("-s", "--treshold-change-steps"):
            tresholdChangeSteps = abs(int(arg))
        elif opt in ("-m", "--treshold-max-change"):
            tresholdMaxChange = abs(int(arg))
        elif opt in ("-b", "--scale-factor-boundaries"):
            scaleFactorBoundaries = list(map(float, arg.split(',')))
        elif opt in ("-o", "--output-directory"):
            outputDirectory = os.path.normpath(arg)
        elif opt in ("-l", "--logfile-directory"):
            logFileDirectory = os.path.normpath(arg)
        elif opt in ("-p", "--suppress-overlap-images"):
            suppressOverlapImages = True
    
    # Check if the reference and target folders exist
    if not referenceFilesDirectory or not os.path.exists(referenceFilesDirectory):
        print(f"Error: reference folder does not exist.")
        print_help()
        sys.exit()
    elif not targetFilesDirectory or not os.path.exists(targetFilesDirectory):
        print(f"Error: target folder does not exist.")
        print_help()
        sys.exit()
    
    # Check if the reference and target folders are difference
    if os.path.abspath(os.path.normpath(referenceFilesDirectory)) == os.path.abspath(os.path.normpath(targetFilesDirectory)):
        print(f"Error: reference and target folder should be different.")
        print_help()
        sys.exit()
    
    # Check if the thresholds are between 0 and 255
    if not 0 <= tresholdReferenceImages <= 255:
        print("Error: the reference threshold should be between 0 and 255.")
        print_help()
        sys.exit(1)
    elif not 0 <= tresholdTargetImages <= 255:       
        print("Error: the target threshold should be between 0 and 255.")
        print_help()
        sys.exit(1)
    
    # Check if scale factor boundaries are in the correct format
    if len(scaleFactorBoundaries) != 2:
        print("Error: please provide a lower and an upper boundary.")
        print_help()
        sys.exit(1)
    elif scaleFactorBoundaries[0] < 0:
        print("Error: the lower boundary should not be smaller than 0.")
        print_help()
        sys.exit(1)
    elif scaleFactorBoundaries[0] >= scaleFactorBoundaries[1]:
        print("Error: the upper boundary should be greater than the lower boundary.")
        print_help()
        sys.exit(1)

    # Check if the output directory exists. Create directory or fall back to default if needed.
    try:
        defaultOutputDirectory = os.path.normpath(os.getcwd() + "/Alignments/" + os.path.basename(targetFilesDirectory) + "_Alignments/")
        
        if not outputDirectory: # If outputDirectory is empty, i.e. a directory was not provided by the user
            outputDirectory = defaultOutputDirectory
            
        if not os.path.exists(outputDirectory):
            # Attempt to create the output directory
            os.makedirs(outputDirectory, exist_ok=True)   
            print(f"Output directory '{outputDirectory}' created.")
            
        if not suppressOverlapImages and not os.path.exists(os.path.normpath(outputDirectory + "/overlap/")):
            os.makedirs(os.path.normpath(outputDirectory + "/overlap/"), exist_ok=True)
        
        if not os.access(outputDirectory, os.W_OK):
            raise ValueError("Cannot write to output directory") 
    except Exception as e:
        if isinstance(e, ValueError):
            print(f"Failed to write to the output directory '{outputDirectory}', using default '{defaultOutputDirectory}'.")
            
        if outputDirectory: # If outputDirectory is not empty, i.e. a directory was provided by the user
            if not isinstance(e, ValueError):
                print(f"Failed to create output directory '{outputDirectory}', using default '{defaultOutputDirectory}'.")
        
            try:
                outputDirectory = defaultOutputDirectory
                os.makedirs(outputDirectory, exist_ok=True)
                
                if not suppressOverlapImages:
                    os.makedirs(os.path.normpath(outputDirectory + "/overlap/"), exist_ok=True)
            except Exception as e:
                print(f"Error creating output directory '{outputDirectory}'.")
                sys.exit(1)
        else:
            print(f"Error creating output directory '{outputDirectory}'.")
            sys.exit(1)
    
    # Check if output directory is empty or not
    try:
        if (suppressOverlapImages and len(os.listdir(outputDirectory)) > 1) or (not suppressOverlapImages and (len(os.listdir(outputDirectory)) > 1 or len(os.listdir(os.path.normpath(outputDirectory + "/overlap/"))) != 0)):
            if query_yes_no(f"Output folder '{outputDirectory}' is not empty. Some files may be overwritten. Proceed? [Y/n]") == False:
                print(f"Exiting.")
                sys.exit(0)
    except Exception as e:
        sys.exit(1)
    
    # Create log file directory, or fall back to default log file location if needed. Then check if the log file can be opened.
    try:
        logFileName = os.path.basename(targetFilesDirectory) + "_Log " + datetime.now().strftime("%Y_%m_%d %H_%M_%S") + ".txt"
        defaultLogFilePath = os.getcwd() + "/" + logFileName
        
        if logFileDirectory: # If logFileDirectory is not empty, i.e. a directory was provided by the user
            logFilePath = os.path.normpath(logFileDirectory + "/" + logFileName)
            
            # Check if the logfile directory exists
            if not os.path.exists(logFileDirectory):
                # Attempt to create the logfile directory
                os.makedirs(logFileDirectory, exist_ok=True)
        else:
            logFilePath = defaultLogFilePath

        # Open log file
        logFile = open(logFilePath, "w")
    except Exception as e:
        if logFileDirectory: # If not empty
            print(f"Failed to open log file '{logFilePath}', using default.")
            
            try:
                logFilePath = defaultLogFilePath
                logFile = open(logFilePath, "w")
            except Exception as e:
                print(f"Failed to open log file '{logFilePath}'.")
                sys.exit(1)
        else:
            print(f"Failed to open log file '{logFilePath}'.")
            sys.exit(1)
    
    # Get all reference images
    referenceFiles = [f for f in os.listdir(referenceFilesDirectory) if os.path.isfile(os.path.join(referenceFilesDirectory, f))]

    # Determine the min and max values of the threshold ranges
    tresholdMaxChangeReferenceImages = np.minimum(255 - tresholdReferenceImages, tresholdMaxChange)
    tresholdMaxDecreaseReferenceImages = np.minimum(tresholdReferenceImages, tresholdMaxChange)
    tresholdMaxChangeTargetImages = np.minimum(255 - tresholdTargetImages, tresholdMaxChange)
    tresholdMaxDecreaseTargetImages = np.minimum(tresholdTargetImages, tresholdMaxChange)

    # Create treshold ranges
    tresholdRangeReferenceImages = [*range(0, tresholdMaxChangeReferenceImages, tresholdChangeSteps), *range(-tresholdChangeSteps, -tresholdMaxDecreaseReferenceImages, -tresholdChangeSteps)]
    tresholdRangeTargetImages = [*range(0, tresholdMaxChangeTargetImages, tresholdChangeSteps), *range(-tresholdChangeSteps, -tresholdMaxDecreaseTargetImages, -tresholdChangeSteps)]
       
    # Get python version
    pythonVersion = sys.version.replace('\n', '; ')
    
    # Write details to log
    logFileMessage = f"""    {" ".join(sys.argv[:])}
    Working directory: {os.path.abspath(os.path.normpath(os.getcwd()))}
    Reference files directory: {os.path.abspath(referenceFilesDirectory)}
    Target files directory: {os.path.abspath(targetFilesDirectory)}
    Output directory: {os.path.abspath(outputDirectory)}
    Logfile location: {os.path.abspath(logFilePath)}
    Default treshold reference images: {tresholdReferenceImages}
    Default treshold target images: {tresholdTargetImages}
    Treshold range reference images: {', '.join(map(str, tresholdRangeReferenceImages))}
    Treshold range target images: {', '.join(map(str, tresholdRangeTargetImages))}
    Scale factor boundaries: {', '.join(map(str, scaleFactorBoundaries))}
    Python version: {pythonVersion}
    opencv-python version: {pkg_resources.get_distribution("opencv-python").version}
    NumPy version: {pkg_resources.get_distribution("NumPy").version}
    Start: {datetime.now().strftime('%Y_%m_%d %H_%M_%S')}\n"""
    
    logFile.write(logFileMessage)
    print(logFileMessage)
    
    # Initiate progress bar
    fileNumber = 0 # Used for progress reporting
    updateProgress(fileNumber / len(referenceFiles), "")
    
    for referenceFile in referenceFiles:
        fileNumber += 1

        if os.path.isfile(targetFilesDirectory + "/" + referenceFile): # Continue only if corresponding target file exists
            scaleFactor = -1 # Default

            try:
                # Try aligning each target image with the corresponding reference image
                # If alignment is not immediately successful (i.e. the resulting scale factor is outside the allowed range),
                # the thresholds will be altered until alignment is succesful or alignment cannot be established
                for i in tresholdRangeReferenceImages:
                    for j in tresholdRangeTargetImages:
                        if not (scaleFactorBoundaries[0] <= scaleFactor <= scaleFactorBoundaries[1]):
                            (scaleFactor, rotationAngle, transformedImage, alignedImageOverlapedWithRefImage) = alignImages(tresholdReferenceImages + i, tresholdTargetImages + j, (targetFilesDirectory + "/"), (referenceFilesDirectory+ "/"), referenceFile)
                            
                            if (scaleFactorBoundaries[0] <= scaleFactor <= scaleFactorBoundaries[1]):
                                logFile.write(f"{referenceFile}; Used treshold reference image: {(tresholdReferenceImages + i)}; Used treshold target image: {(tresholdTargetImages + j)}; Rotation angle: {rotationAngle}; Scale factor: {scaleFactor}\n")
                                break # Alignment successful
                    if (scaleFactorBoundaries[0] <= scaleFactor <= scaleFactorBoundaries[1]):
                        break # Alignment successful
                
                if not (scaleFactorBoundaries[0] <= scaleFactor <= scaleFactorBoundaries[1]):
                    # Alignment unsuccessful
                    logFile.write(referenceFile + " alignment unsuccesful" +"\n")
                else:
                    # Alignment successful
                    # Save the output
                    outputDirectory += "/"
                    cv2.imwrite(outputDirectory + referenceFile, transformedImage)
                    
                    if not suppressOverlapImages:
                        cv2.imwrite(outputDirectory + "overlap/" + referenceFile, alignedImageOverlapedWithRefImage)

                # Update progress bar
                updateProgress(fileNumber / len(referenceFiles), referenceFile)
            except KeyboardInterrupt:
                logFile.close()
                raise
            except Exception as e:
                logFile.write(f"Error aligning image {referenceFile}, error: {e}\n")

    sys.stdout.flush() # Clear progress bar
    logFile.write(f"    Finished: {datetime.now().strftime('%Y_%m_%d %H_%M_%S')}")
    logFile.close()

def updateProgress(progress, currentReferenceFileName):
    # Function adapted from: https://stackoverflow.com/questions/3160699/python-progress-bar/15860757
    barLength = 20
    status = ""

    if isinstance(progress, int):
        progress = float(progress)

    if not isinstance(progress, float):
        progress = 0
        status = "Error: progress var must be float\r\n"

    if progress < 0:
        progress = 0
        status = "Halt...\r\n"

    if progress >= 1:
        progress = 1
        status = "Done...\r\n"

    block = int(round(barLength*progress))
    referenceFileToReport = "..." + currentReferenceFileName[-15:] if len(currentReferenceFileName) > 15 else currentReferenceFileName[-15:]
    text = "\rPercent: [{0}] {1}% {2} {3} ".format( "#"*block + "-"*(barLength-block), round(progress*100, 3), referenceFileToReport, status)

    sys.stdout.write(text)
    sys.stdout.flush()

def query_yes_no(question):
    answers = {"yes": True, "y": True, "no": False, "n": False}
    
    while True:
        sys.stdout.write(question)
        answer = input().lower()
        
        if answer == "":
            return True
        elif answer in answers:
            return answers[answer]
        else:
            sys.stdout.write("Please type 'yes' or 'y', or 'no' or 'n'.\n")

def alignImages(tresholdReferenceImage, tresholdTargetImage, targetFilesDirectory, referenceFilesDirectory, referenceFile):
    # Open the image files
    targetImageColor = cv2.imread(targetFilesDirectory + referenceFile) # Image to be aligned
    referenceImageColor = cv2.imread(referenceFilesDirectory + referenceFile) # Reference image

    # Convert images to grayscale
    targetImageGrayscale = cv2.cvtColor(targetImageColor, cv2.COLOR_BGR2GRAY)
    referenceImageGrayscale = cv2.cvtColor(referenceImageColor, cv2.COLOR_BGR2GRAY)
    height, width = referenceImageGrayscale.shape

    # Convert images to black and white
    (thresh, targetImageGrayscale) = cv2.threshold(targetImageGrayscale, tresholdTargetImage, 255, cv2.THRESH_BINARY)
    (thresh, referenceImageGrayscale) = cv2.threshold(referenceImageGrayscale, tresholdReferenceImage, 255, cv2.THRESH_BINARY)

    # Create ORB detector
    orbDetector = cv2.ORB_create(5000)
    keyPoints1, descriptor1 = orbDetector.detectAndCompute(targetImageGrayscale, None)
    keyPoints2, descriptor2 = orbDetector.detectAndCompute(referenceImageGrayscale, None)

    # Match and sort features using Hamming distance
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck = True)
    matches = matcher.match(descriptor1, descriptor2)
    matches.sort(key = lambda x: x.distance)

    # Continue with the top 90% matches
    matches = matches[:int(len(matches)*0.9)]

    # Reshape keypoints
    src_pts = np.float32([keyPoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([keyPoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

    # Find homography
    transformationMatrix, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    # Compute a rigid transformation matrix (i.e. only scale, rotation and translation)
    transformationRigidMatrix, rigid_mask = cv2.estimateAffinePartial2D(src_pts, dst_pts)
    matchesMask = mask.ravel().tolist()

    # Calculate the rotation angle and scale factor
    rotationAngle = np.degrees(np.arctan2(-transformationRigidMatrix[0,1], transformationRigidMatrix[0,0]))
    scaleFactor = np.sign(transformationRigidMatrix[0,0]) * np.sqrt(np.square(transformationRigidMatrix[0,0]) + np.square(transformationRigidMatrix[0,1]))

    # Use the transformation matrix to warp the opened target image
    transformedImage = cv2.warpAffine(targetImageColor,
                       transformationRigidMatrix, (width, height))

    # In addition, overlap the aligned image with the opened reference image
    alignedImageOverlapedWithRefImage = cv2.addWeighted(referenceImageColor, 0.5, transformedImage, 0.7, 0)

    return (scaleFactor, rotationAngle, transformedImage, alignedImageOverlapedWithRefImage)

if __name__ == "__main__":
   main(sys.argv[1:])

