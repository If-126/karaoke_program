import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QComboBox, QPushButton
import pyaudio
import numpy as np
import wave
import os
from datetime import datetime
from audioop import mul, add, bias
from threading import Thread

# set globals
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

    def initUI(self):
        global InputDeviceValue, OutputDeviceValue
        self.test1 = QLabel('Defalult', self)
        self.test1.move(50, 150)
        self.test2 = QLabel('Defalult', self)
        self.test2.move(50, 200)
        self.btn = QPushButton('start', self)
        self.btn.move(50, 350)

        inputCB = QComboBox(self)
        inputCB.addItem('Defalult')
        outputCB = QComboBox(self)
        outputCB.addItem('Defalult')
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                InputDeviceValue.update(
                    {p.get_device_info_by_host_api_device_index(0, i).get('name'):
                     p.get_device_info_by_host_api_device_index(0, i).get('index')})
                inputCB.addItem(p.get_device_info_by_host_api_device_index(
                    0, i).get('name'))

        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
                OutputDeviceValue.update(
                    {p.get_device_info_by_host_api_device_index(0, i).get('name'):
                     p.get_device_info_by_host_api_device_index(0, i).get('index')})
                outputCB.addItem(p.get_device_info_by_host_api_device_index(
                    0, i).get('name'))

        inputCB.move(50, 50)
        outputCB.move(50, 100)
        inputCB.activated[str].connect(self.onActivatedInput)
        outputCB.activated[str].connect(self.onActivatedOutput)
        self.btn.clicked.connect(self.onAirButton)
        self.setWindowTitle('Karaoke_Program')
        self.setGeometry(300, 300, 600, 600)  # x,y,width,height
        self.show()

    def onActivatedInput(self, text):  # select inputindex
        global INPUT_INDEX
        INPUT_INDEX = int(InputDeviceValue[text])

    def onActivatedOutput(self, text):  # select outputindex
        global OUTPUT_INDEX
        OUTPUT_INDEX = int(OutputDeviceValue[text])

    def onAirButton(self):
        global INPUT_INDEX, OUTPUT_INDEX
        self.test1.setText(str(INPUT_INDEX))
        self.test1.adjustSize()
        self.test2.setText(str(OUTPUT_INDEX))
        self.test2.adjustSize()
        self.start_stream()

    def add_delay(self, input):
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
