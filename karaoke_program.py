from tkinter import *
import tkinter.ttk as ttk
import pyaudio
import numpy as np
import wave
import os
from datetime import datetime
from audioop import mul, add, bias
from threading import Thread

INPUT_INDEX = 0  # change this to microphone
OUTPUT_INDEX = 0  # change this to main speaker
OUTPUT_FILENAME = 'output/%s.wav' % (
    datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
os.makedirs('output', exist_ok=True)  # 부른 노래를 wav파일로 저장하는 경로 지정


# input/ouput list
InputDeviceValue = {}
OutputDeviceValue = {}

CHUNK = 512  # 한번에 받을수 있는 스트리밍의 양 적을수록 딜레이가 적고 많아질수록 딜레이가 많아진다
RATE = 48000
SAMPLE_WIDTH = 2
DELAY_INTERVAL = 15  # 클수로 에코의 딜레이가 길어진다
DELAY_VOLUME_DECAY = 0.6  # 딜레이시켰을때 나오는 음이 얼마나 작아질 것인가
DELAY_N = 10  # 딜레이 반복되는 횟수

# delay sound
original_frames = []
index = 0


# find input/output device index & append list
p = pyaudio.PyAudio()
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')
for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        InputDeviceValue.update(
            {p.get_device_info_by_host_api_device_index(0, i).get('name'):
             p.get_device_info_by_host_api_device_index(0, i).get('index')})

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
        OutputDeviceValue.update(
            {p.get_device_info_by_host_api_device_index(0, i).get('name'):
             p.get_device_info_by_host_api_device_index(0, i).get('index')})


root = Tk()
root.title("Singing Room")
root.geometry("800x500+300+100")  # 가로 세로 x좌표 y좌표 설정


# Input Output Device List
InputDeviceCombobox = ttk.Combobox(
    root, height=5, values=list(InputDeviceValue.keys()), state="readonly")


OutputDeviceCombobox = ttk.Combobox(
    root, height=5, values=list(OutputDeviceValue.keys()), state="readonly")


def add_delay(input):
    global original_frames, index

    original_frames.append(input)
    output = input

    if len(original_frames) > DELAY_INTERVAL:
        for n_repeat in range(DELAY_N):
            delay = original_frames[max(index - n_repeat * DELAY_INTERVAL, 0)]

            delay = mul(delay, SAMPLE_WIDTH,
                        DELAY_VOLUME_DECAY ** (n_repeat + 1))
            output = add(output, delay, SAMPLE_WIDTH)

        index += 1

    return output


def start_stream():
    global INPUT_INDEX, OUTPUT_INDEX
    # open devices
    INPUT_INDEX = int(InputDeviceValue[InputDeviceCombobox.get()])
    OUTPUT_INDEX = int(OutputDeviceValue[OutputDeviceCombobox.get()])

    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        frames_per_buffer=CHUNK,
        input=True,
        output=True,
        input_device_index=INPUT_INDEX,
        output_device_index=OUTPUT_INDEX
    )

    frames = []

    # start stream
    while stream.is_active():
        try:
            input = stream.read(CHUNK, exception_on_overflow=False)
            input = add_delay(input)

            stream.write(input)
            frames.append(input)

            if stop == 1:
                break  # Break while loop when stop = 1

        except KeyboardInterrupt:
            break
        except Exception as e:
            print('[!] Unknown error!', e)
            exit()

    # write audio as a file
    total_frames = b''.join(frames)

    with wave.open(OUTPUT_FILENAME, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
        f.setframerate(RATE)
        f.writeframes(total_frames)

    stream.stop_stream()
    stream.close()
    p.terminate()


def start_thread():
    # Assign global variable and initialize value
    global stop
    stop = 0

    # Create and launch a thread
    t = Thread(target=start_stream)
    t.start()


def opencmd():
    if InputDeviceCombobox.get() != "default" and OutputDeviceCombobox.get() != "default":
        root.after(1000, start_stream)

    else:
        print("select device")


def closecmd():
    global stop
    stop = 1
    root.quit()


openbtn = Button(root, text="Run", command=start_thread)
closebtn = Button(root, text="Close", command=closecmd)

InputDeviceCombobox.pack()
OutputDeviceCombobox.pack()
openbtn.pack()
closebtn.pack()
InputDeviceCombobox.set("default")
OutputDeviceCombobox.set("default")


root.mainloop()
