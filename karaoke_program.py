import sys
import pyaudio
import numpy as np
import wave
import os
import threading
from audioop import mul, add, bias
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QComboBox, QPushButton
from PyQt5.QtCore import QCoreApplication

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
p = pyaudio.PyAudio()


class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()
        self.echocontrol = 1

    def initUI(self):
        # select device index and list
        self.inputdeviceindex = QLabel('Defalult', self)
        self.outputdeviceindex = QLabel('Defalult', self)
        self.inputCB = QComboBox(self)
        self.outputCB = QComboBox(self)
        # control button
        self.startBtn = QPushButton('start', self)
        self.controlBtn = QPushButton('echo off', self)
        # UI layout
        self.startBtn.move(50, 350)
        self.controlBtn.move(200, 350)
        self.inputdeviceindex.move(50, 150)
        self.outputdeviceindex.move(50, 200)
        self.inputCB.move(50, 50)
        self.outputCB.move(50, 100)
        # widget activated
        self.findDevice()
        self.inputCB.activated[str].connect(self.onActivatedInput)
        self.outputCB.activated[str].connect(self.onActivatedOutput)
        self.startBtn.clicked.connect(self.onAirButton)
        self.controlBtn.clicked.connect(self.onoffEcho)
        self.setWindowTitle('Karaoke_Program')
        self.setGeometry(300, 300, 600, 600)
        self.show()

    def findDevice(self):  # add device list
        global InputDeviceValue, OutputDeviceValue
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        self.inputCB.addItem('Defalult')
        self.outputCB.addItem('Defalult')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                InputDeviceValue.update(
                    {p.get_device_info_by_host_api_device_index(0, i).get('name'):
                     p.get_device_info_by_host_api_device_index(0, i).get('index')})
                self.inputCB.addItem(
                    p.get_device_info_by_host_api_device_index(0, i).get('name'))

        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
                OutputDeviceValue.update(
                    {p.get_device_info_by_host_api_device_index(0, i).get('name'):
                     p.get_device_info_by_host_api_device_index(0, i).get('index')})
                self.outputCB.addItem(
                    p.get_device_info_by_host_api_device_index(0, i).get('name'))

    def onActivatedInput(self, text):  # select inputindex
        global INPUT_INDEX
        INPUT_INDEX = int(InputDeviceValue[text])

    def onActivatedOutput(self, text):  # select outputindex
        global OUTPUT_INDEX
        OUTPUT_INDEX = int(OutputDeviceValue[text])

    def onAirButton(self):  # start karaoke
        global INPUT_INDEX, OUTPUT_INDEX
        self.inputdeviceindex.setText(str(INPUT_INDEX))
        self.inputdeviceindex.adjustSize()
        self.outputdeviceindex.setText(str(OUTPUT_INDEX))
        self.outputdeviceindex.adjustSize()
        thread = threading.Thread(target=self.start_stream)
        thread.daemon = True
        thread.start()

    def onoffEcho(self):
        if self.echocontrol == 1:  # offecho
            self.controlBtn.setText('offecho')
            self.echocontrol = 0
        elif self.echocontrol == 0:
            self.controlBtn.setText('onecho')
            self.echocontrol = 1

    def add_delay(self, input):  # karaoke echo
        global original_frames, index

        original_frames.append(input)
        output = input

        if len(original_frames) > DELAY_INTERVAL:
            for n_repeat in range(DELAY_N):
                delay = original_frames[max(
                    index - n_repeat * DELAY_INTERVAL, 0)]

                delay = mul(delay, SAMPLE_WIDTH,
                            DELAY_VOLUME_DECAY ** (n_repeat + 1))
                output = add(output, delay, SAMPLE_WIDTH)

            index += 1

        return output

    def start_stream(self):
        # open devices
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
                if self.echocontrol == 1:
                    input = self.add_delay(input)

                stream.write(input)
                frames.append(input)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print('[!] Unknown error!', e)
                exit()

        # write audio as a file
        total_frames = b''.join(frames)

        with wave.open(OUTPUT_FILENAME, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            f.setframerate(RATE)
            f.writeframes(total_frames)

        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())
