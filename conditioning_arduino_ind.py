# -*- coding: utf-8 -*-
"""
Created on Sun Dec 11 16:02:44 2022

@author: Nate
"""
import datetime
import serial
import cv2
import time
import pandas as pd
import numpy as np
import threading
import sys
import os
import subprocess
import signal
import atexit
import random 
import configparser
import warnings

"""Real config parsing"""

config = configparser.ConfigParser()
config.read('times.config')

cfg_lever_side = config['shared params']['lever side']
cfg_lever_duration = int(config['shared params']['lever out duration'])
exp_path = config['shared params']['exportpath']

params = config['conditioning params']
nop = int(params['number of pairings'])
a_iti = int(params['average iti'])
s_iti = int(params['std iti'])
min_iti = int(params['min iti'])
max_iti = int(params['max iti'])

device_pairs = config['shared params']['device pairs'].split(',')
device_pairs = [int(i) for i in device_pairs]

pair_ind = int(sys.argv[2]) * 2
print(f'\n\nThis is device pair {pair_ind}\n\n')
camera_choice = device_pairs[pair_ind]
arduino_choice = device_pairs[pair_ind + 1]

conditioning_day = True #Need to make this a sys.argv or have seperate pre/conditioning files
verbose = False #Will spit out sampling rate info onto shell


#Setting camera exposure stuff so that we don't accidentally drop frames
exp_settings = 'v4l2-ctl -d /dev/video{} --set-ctrl=exposure_absolute=300 --set-ctrl=exposure_auto=1'.format(camera_choice) #We turn off auto-exposure and peg the exposure time to 300

camset = subprocess.Popen(exp_settings.split()) #This runs the exposure setting command in terminal



"""Test config parameters

#config = configparser.ConfigParser()
#config.read('times.config')
conditioning_day = True

cfg_lever_side = 'right'
cfg_lever_duration = 5
exp_path = r'D:\hztest'

#params = config['conditioning params']
nop = 2
a_iti = 10
s_iti = 1
min_iti = 9
max_iti = 11


#device_pairs = config['shared params']['device pairs'].split(',')
#device_pairs = [int(i) for i in device_pairs]

#pair_ind = int(sys.argv[2]) * 2
#print(pair_ind)
#camera_choice = device_pairs[pair_ind]
arduino_choice = 0


end test params """


#%% Main function

def run_arduino_ind():
    
    #Supporting functions
    def wait_gather_data(duration):
        inner_time = time.time()
        while True:
            cycle_time = time.time()
            time_passed = cycle_time - inner_time
            if time_passed > duration:
                break
            incoming = ser.readline()
            if len(incoming) > 0:
                read_data.append(incoming)

    #Pass a dataset containing timestamps of a constant measurement (such as ir_data if you leave something in the food magazine)
    def find_interval(dataset):
        data = pd.DataFrame(dataset)
        interval = data - data.shift(1)
        interval = interval / 1000
        print(f'The average interval was {np.nanmean(interval.values)} seconds per measurement, \nwhile the highest was {np.nanmax(interval.values)}.')
        print(f'The data was recorded at an average of {1/np.nanmean(interval.values)} Hz \n\n')
        
    def find_loop_hz(loop_dataset):
        loop_df = pd.DataFrame(loop_dataset)
        loop_df = loop_df 
        print(f'From direct loop timing, the average interval was {1 / np.nanmean(loop_df.values)} seconds per measurement, \nwhile the highest was {1 / np.nanmin(loop_df.values)}.')
        print(f'The data was recorded at an average of {np.nanmean(loop_df.values)} Hz')

    def show_intervals():
        f, (ax1, ax2) = plt.subplots(2, 1)
        ax1.plot(loop_data)
        ax2.plot(interval)

    def make_visualizations():
        f, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

        ir_df = [i / 1000 for i in ir_data]
        ax1.eventplot(ir_df)
        
        lever_df = [i / 1000 for i in lever_data]
        ax2.eventplot(lever_df)    
        
    #Raw data stored here
    read_data = []
    
    #Using time.time to get the exact irl time point of each lever/food presentation relative
    #to experiment start, so you can easily match to data timestamps
    presentation_times = [] 
    
    #Global variables that are used to communicate with the video capture process
    global r_t_s
    r_t_s = False
    global program_done
    program_done = False
    
    
    #Randomly generating ITIs
    iti_times = []
    while len(iti_times) < nop: #This is how many ITI periods you will have and consequently how many lever/food presentations there will be
        iti = random.gauss(a_iti,s_iti) #We pick our ITIs randomly from a normal distribution, with an average and standard deviation of our choosing
        if (min_iti < iti < max_iti): #A hard cutoff for our ITIs
            iti_times.append(iti)
            
    if conditioning_day:
        total_time = sum(iti_times) + (cfg_lever_duration * nop)
    else:
        total_time = sum(iti_times)
    print(f'\n\nApproximate duration of experiment will be {total_time/60} minutes\n\n')
    
            
    #Startup routine - wait until arduino is ready to recieve transmissions
    ser = serial.Serial('/dev/ttyACM{}'.format(arduino_choice),9600,timeout=0.5)
    #ser = serial.Serial('COM5'.format(arduino_choice),9600,timeout=.5)
    while r_t_s == False:
        signal = ser.readline().decode().strip()
        
        if signal == 'ready':
            print('Sending start signal now')
            r_t_s = True
            break
        
    def serial_reader(): #Try offloading reading the serial data to another thread
        while True:
            signal = ser.readline().decode().strip()
            if len(signal) > 0:
                read_data.append(signal)
            if signal == 'end':
                break
    
    #y = threading.Thread(target=serial_reader, args=()).start()
    
    #Get starting time and tell arduino to begin its data collection
    start_time = time.time()
    inner_time = start_time
    ser.write(b'g')
    
    #Loop through each ITI
    for iti in iti_times:
        wait_gather_data(iti)
        presentation_times.append(time.time() - start_time)
        
        if conditioning_day:
            if cfg_lever_side == 'right':
                ser.write(b'r')
            elif cfg_lever_side == 'left':
                ser.write(b'l')
            wait_gather_data(cfg_lever_duration)
            ser.write(b'k')
        ser.write(b'd')
        
    #Tell everyone to stop recording
    ser.write(b's')
    program_done = True
    stop_time = time.time()
    time.sleep(1) #Need to ensure arduino's confirm END signal can get into the serial buffer
    #y.join()
    #Make sure to completely finish reading the serial buffer
    while ser.in_waiting:
        read_data.append(ser.readline())
    
    whole_run_duration = datetime.timedelta(seconds=(stop_time - start_time))
    print(f'Whole operation took {whole_run_duration} \n')
    
    ser.close()
    
    #%%% Data processing
    
    presentation_times = pd.DataFrame(presentation_times)
    filename = os.path.join(exp_path,(f'{sys.argv[1]}_present_times.csv'))
    presentation_times.to_csv(filename)
    
    raw_data_exp_encoded = pd.DataFrame(read_data)
    filename = os.path.join(exp_path,(f'{sys.argv[1]}_raw_encoded.csv'))
    raw_data_exp_encoded.to_csv(filename)

    raw_data_exp_decoded = pd.DataFrame([i.decode().strip() for i in read_data])
    filename = os.path.join(exp_path,(f'{sys.argv[1]}_raw_decoded.csv'))
    raw_data_exp_decoded.to_csv(filename)


    #Collapse data by data type
    ir_data = []
    lever_data = []
    loop_data = [] #Number of full loops per 1 second intervals
    
    for a in read_data[1:-1]:
        raw_data = a.decode().strip()
        category, timestamp = raw_data.split()
        if 'nose' in category:
            ir_data.append((category,timestamp))
        elif 'lever' in category:
            lever_data.append((category,timestamp))
        elif category == 'loop':
            loop_data.append(int(timestamp))
            
    #make sure every start has a stop
    def check_alternating(dataset,name_set):
        for i in range(len(dataset)-1):
            if (dataset[i][0] == dataset[i+1][0]):
                warnings.warn(f'Unmatched on/off pairing in {name_set} data\n')
    
    check_alternating(ir_data,'ir beam break')
    check_alternating(lever_data,'lever press')
            
    ir_df = pd.DataFrame(ir_data, columns = ['nose state', 'nose time (s)'])
    lever_df = pd.DataFrame(lever_data, columns = ['lever state', 'lever time (s)'])
    
    filename = os.path.join(exp_path,(f'{sys.argv[1]}.csv'))
    export_df = pd.concat([ir_df,lever_df],axis=1)
    export_df.to_csv(filename)
    
    
    #obsolete tests
    if verbose == 'no':     
        try:
            print('ir_data: \n')
            find_interval(ir_data)
        except ValueError:
            if not len(ir_data):
                print('Recorded no IR beam breaks\n\n')
            
        try:
            print('lever_data: \n')
            find_interval(lever_data)
        except ValueError:
            if not len(lever_data):
                print('Recorded no lever presses\n\n')
                
    try:
        find_loop_hz(loop_data)
    except:
        pass
        
    #Checking the integrity of the data transfer is essential
    try:
        if not (read_data[0].decode().strip() == 'start'):
            warnings.warn("First value read was not START - data may be missing head")
    except:
        pass
    
    try:
        if not (read_data[-1].decode().strip() == 'end'):
            warnings.warn("Last value read was not END - data may be missing tail")
    except:
        pass

    
    
    
    


#%% Running with gstreamer

x = threading.Thread(target=run_arduino_ind, args=()).start() #Runs the arduino protocol


r_t_s = False
program_done = False

#GStreamer code - waits for the Arduino and then immediately starts video capture outside of python (to cut down on the amount of processing we have to do on frames)
while r_t_s == False:
    pass
gstr_arg = 'gst-launch-1.0 v4l2src device=/dev/video{} num-buffers=-1 do-timestamp=true ! image/jpeg,width=3840,height=2160,framerate=30/1 ! queue ! avimux ! filesink location=/media/leelab/Elements/{}.avi -e'.format(camera_choice,sys.argv[1])
print(gstr_arg)
print('\n')
gstr_cmd = gstr_arg.split()
video_capture = subprocess.Popen(gstr_cmd)
vid_id = video_capture.pid

while program_done == False:
    pass

os.kill(vid_id,signal.SIGINT)
