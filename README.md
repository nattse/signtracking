# Overview
Behavioral tasks such as sign tracking and reversal learning are complex both in the information they provide and in the methodology/protocols they can require. As such, we wanted to gain better control over data collection (e.g. sampling frequency, video quality and framerate) while at the same time making the application of protocols more human-readable. In order to accomplish these tasks, we have created our own operant conditioning chambers. Protocol instructions and instrument readings are routed through an Arduino to a single laptop that time-syncs the data with high-resolution video capture. 

This specific code repository is for a sign tracking task.

## First time setup
These instructions assume you have downloaded this repository, the necessary packages, and the Arduino IDE. 
Connect the Arduino and use the IDE to upload *arduino_independence.ino* to the Arduino. At this point also note the port the Arduino is on (e.g. COM**1**). Plug in the USB camera next and use `v4l2-ctl --list-devices` to get the device number (e.g. /dev/video**2**). Then for **device pairs** in *times.config*, enter the camera device number and Arduino port number seperated by a comma. Repeat for every camera/Arduino pair you connect to the computer (e.g. 2,1,4,3 > video2, COM1, video4, COM3).

## Before each run
All experiment conditions are set beforehand in the *times.config* file. Importantly, ITI (inter-trial interval) settings in this file are used to generate a list of wait times. These wait times are used in two .py scripts, one of which is a training protocol (*preconditioning_arduino_ind.py*) and the other a testing protocol (*conditioning_arduino_ind.py*). 

Once video recording has begun, the procedure for either protocols is as follows:

### preconditioning.py
- Wait ITI[n] seconds
- Dispense food
- n += 1

### conditioning.py
- Wait ITI[n] seconds
- Present a lever (**lever side** in *times.config*)
- Wait a few seconds (**lever out duration** in *times.config*)
- Retract lever
- Dispense food
- n += 1

## Running the experiment
Run `python3 preconditioning_arduino_ind.py filename pair_index` replacing **filename** with whatever you want the resulting .csv and video files to be titled. If you have connected only one camera/Arduino pair, **pair_index** should always be 0. However, if you have multiple camera/Arduino pairs in **device pairs** in *times.config*, use **pair_index** to specify which device pair you are using. For example, given `device pairs = 2,1,4,3`, **pair_index** = 0 will specify video2/COM1, while **pair_index** = 1 will specify video4/COM3.

## Data output

 - filename.csv: Summary file, gives times when nose enters or exits food magazine and times when lever is pressed and released (mm:ss:ms)
 - filename_present_times.csv : Protocol file, tells you when the lever was extended (seconds)
 - filename_raw_decoded.csv/filename_raw_encoded.csv: Extra raw data including a readout of how many Arduino loops are completed per 1 second
 
## Common problems

**Video length does not match the actual run time:** Check the video framerate first - are levers in the video extended for the right amount of time? If video time seems faster than IRL time, you may be capturing less frames than expected. This may happen if you fail to peg down camera exposure settings - in low light, cameras using auto-exposure will increase exposure time to get better images, and as a result the number of frames captured will drop. Run `v4l2-ctl -d /dev/videoX --set-ctrl=exposure_absolute=300 --set-ctrl=exposure_auto=1`, replacing **X** with your camera device ID to check that your camera allows exposure to be manually set. 

If framerate seems fine, open the video and move to the very end. Play the video and see if the video stops where the video player says it should. If the video keeps playing past the supposed end point, there may be an encoding error (in these cases we also tend to see the correct video length displayed under the video file's properties, but incorrect length everywhere else). Try copying the files using ffmpeg: `ffmpeg -i input.mp4 -c copy output.mp4` - the copy file should hopefully have the correct length
 
# Operant Conditioning Chamber Wiring Diagram

Levers: **Med Associates ENV-312-3 Retractable Mouse Lever**

Food Dispenser: **Med Associates ENV-203 Pellet Dispenser**

Relays: **[HiLetgo 5V One Channel Relay Module With optocoupler Support High or Low Level Trigger](https://www.amazon.com/HiLetgo-Channel-optocoupler-Support-Trigger/dp/B00LW15A4W)**

IR Emitter and Receiver: **[Chanzon 5mm IR Infrared LED Diode Emitter + Receiver](https://www.amazon.com/Emitter-Receiver-VS1838B-Infrared-Raspberry/dp/B07TLBJR5J?th=1)**

![operant_chamber_wiring](https://user-images.githubusercontent.com/118491380/227418044-cb065a87-e8b8-4a8a-904e-f67036c5ebf5.png)

![chamber_image](https://user-images.githubusercontent.com/118491380/227365957-fa8b2439-1884-4f26-b954-e5c664bc3012.jpg)
