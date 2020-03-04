import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QSlider, QLabel, QRadioButton, QPushButton, QCheckBox
from PyQt5.QtCore import Qt
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import numpy as np
from scipy import signal
from scipy.signal import butter, lfilter, freqz
import keyboard
import pyaudio
import time
from threading import Thread, Event, currentThread

##################################################
## A real time-based synthetizer made with pyaudio and pyqt5
## functioning AM modulation, filters, delays and waveforms
##################################################
## Author: Juan Camilo Plazas
## Version: 0.0.1
## Email: jkamo_84@hotmail.com
## Status: development
##################################################

class Example(QMainWindow):

    def __init__(self):
        super().__init__()
        # variables iniciales de componentes
        self.started = False
        self.wave = 'sinusoidal'
        self.fs= 44100
        self.LFO = np.ones(44100)
        self.t = np.linspace(0,1,self.fs)
        self.noise = (np.random.rand(self.fs) * 2) - 1
        self.copy_noise = self.noise
        self.ftype = 'low'
        self.forder = 4
        self.delay = True

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(p)

        self.a_knob = 11025
        self.d_knob = 11025
        self.s_knob = 5000
        self.r_knob = 11025

        # inicializacion de objetos de la GUI
        self.myLabel1 = QLabel(self)
        self.myLabel1.setText('Attack: 0ms')
        self.myLabel1.setStyleSheet("color: white;")
        self.myLabel1.move(40, 10)

        self.mySlider1 = QSlider(Qt.Horizontal, self)
        self.mySlider1.setGeometry(30, 40, 200, 30)
        self.mySlider1.setMinimum(1)
        self.mySlider1.name = 'Attack'
        self.mySlider1.setMaximum(22050)
        self.mySlider1.setValue(self.a_knob)
        self.mySlider1.valueChanged[int].connect(self.change_knob)

        self.myLabel2 = QLabel(self)
        self.myLabel2.setText('Decay: 0ms')
        self.myLabel2.setStyleSheet("color: white;")
        self.myLabel2.move(40, 70)

        self.mySlider2 = QSlider(Qt.Horizontal, self)
        self.mySlider2.setGeometry(30, 100, 200, 30)
        self.mySlider2.setMinimum(1)
        self.mySlider2.name = 'Decay'
        self.mySlider2.setMaximum(11025)
        self.mySlider2.setValue(self.d_knob)
        self.mySlider2.valueChanged[int].connect(self.change_knob)

        self.myLabel3 = QLabel(self)
        self.myLabel3.setText('Sustain: 0ms')
        self.myLabel3.setStyleSheet("color: white;")
        self.myLabel3.move(40, 130)

        self.mySlider3 = QSlider(Qt.Horizontal, self)
        self.mySlider3.setGeometry(30, 160, 200, 30)
        self.mySlider3.setMinimum(1)
        self.mySlider3.name = 'Sustain'
        self.mySlider3.setMaximum(11025)
        self.mySlider3.setValue(self.s_knob)
        self.mySlider3.valueChanged[int].connect(self.change_knob)

        self.myLabelR = QLabel(self)
        self.myLabelR.setText('Release: 0ms')
        self.myLabelR.move(40, 190)

        self.mySliderR = QSlider(Qt.Horizontal, self)
        self.mySliderR.setGeometry(30, 220, 200, 30)
        self.mySliderR.setMinimum(1)
        self.mySliderR.name = 'Release'
        self.mySliderR.setMaximum(11025)
        self.mySliderR.setValue(self.r_knob)
        self.mySliderR.valueChanged[int].connect(self.change_knob)

        self.myLabel4 = QLabel(self)
        self.myLabel4.setText('LFO: 1Hz')
        self.myLabel4.setStyleSheet("color: white;")
        self.myLabel4.move(40, 310)

        self.mySlider4 = QSlider(Qt.Horizontal, self)
        self.mySlider4.setGeometry(30, 340, 200, 30)
        self.mySlider4.setMinimum(1)
        self.mySlider4.setMaximum(100)
        self.mySlider4.setValue(1)
        self.mySlider4.name = 'slider_lfo'
        self.mySlider4.valueChanged[int].connect(self.active_lfo)

        self.myLabel5 = QLabel(self)
        self.myLabel5.setText('LFO offset')
        self.myLabel5.setStyleSheet("color: white;")
        self.myLabel5.move(40, 370)

        self.mySlider5 = QSlider(Qt.Horizontal, self)
        self.mySlider5.setGeometry(30, 400, 200, 30)
        self.mySlider5.setMinimum(1)
        self.mySlider5.setMaximum(100)
        self.mySlider5.setValue(100)
        self.mySlider5.name = 'slider_lfo'
        self.mySlider5.valueChanged[int].connect(self.active_lfo)

        self.myLabel6 = QLabel(self)
        self.myLabel6.setText('Cutoff Frequency')
        self.myLabel6.setStyleSheet("color: white;")
        self.myLabel6.move(300, 230)

        self.mySlider6 = QSlider(Qt.Horizontal, self)
        self.mySlider6.setGeometry(300, 260, 200, 30)
        self.mySlider6.setMinimum(100)
        self.mySlider6.setMaximum(8000)
        self.mySlider6.setValue(100)
        self.mySlider6.name = 'slider_filter'
        self.mySlider6.valueChanged[int].connect(self.set_filter)

        self.myLabelQ = QLabel(self)
        self.myLabelQ.setText('Band Width')
        self.myLabelQ.move(300, 290)

        self.mySliderQ = QSlider(Qt.Horizontal, self)
        self.mySliderQ.setGeometry(300, 320, 200, 30)
        self.mySliderQ.setMinimum(10)
        self.mySliderQ.setMaximum(1000)
        self.mySliderQ.setValue(10)
        self.mySliderQ.name = 'slider_filter'
        self.mySliderQ.valueChanged[int].connect(self.set_filter)

        self.myLabel7 = QLabel(self)
        self.myLabel7.setText('Filter Order')
        self.myLabel7.setStyleSheet("color: white;")
        self.myLabel7.move(300, 350)

        self.mySlider7 = QSlider(Qt.Horizontal, self)
        self.mySlider7.setGeometry(300, 380, 200, 30)
        self.mySlider7.setMinimum(1)
        self.mySlider7.setMaximum(16)
        self.mySlider7.setValue(4)
        self.mySlider7.name = 'order_filter'
        self.mySlider7.valueChanged[int].connect(self.set_order)

        self.myLabel8 = QLabel(self)
        self.myLabel8.setText('Delay')
        self.myLabel8.setStyleSheet("color: white;")
        self.myLabel8.move(40, 490)

        self.mySlider8 = QSlider(Qt.Horizontal, self)
        self.mySlider8.setGeometry(40, 520, 200, 30)
        self.mySlider8.setMinimum(1)
        self.mySlider8.setMaximum(22050)
        self.mySlider8.setValue(11025)
        self.mySlider8.name = 'delay'
        self.mySlider8.valueChanged[int].connect(self.set_delay)

        radiobutton2 = QRadioButton("Highpass", self)
        radiobutton2.name = "highpass"
        radiobutton2.toggled.connect(self.onClickedF)
        radiobutton2.setStyleSheet("color: white;")
        radiobutton2.setGeometry(300, 420, 200, 32)

        radiobutton2 = QRadioButton("Lowpass", self)
        radiobutton2.name = "lowpass"
        radiobutton2.toggled.connect(self.onClickedF)
        radiobutton2.setStyleSheet("color: white;")
        radiobutton2.setGeometry(300, 460, 200, 32)

        radiobutton2 = QRadioButton("Bandpass", self)
        radiobutton2.name = "bandpass"
        radiobutton2.toggled.connect(self.onClickedF)
        radiobutton2.setStyleSheet("color: white;")
        radiobutton2.setGeometry(300, 500, 200, 32)
        
        radiobutton2 = QRadioButton("Bandstop", self)
        radiobutton2.name = "bandstop"
        radiobutton2.toggled.connect(self.onClickedF)
        radiobutton2.setStyleSheet("color: white;")
        radiobutton2.setGeometry(300, 540, 200, 32)

        self.graphWidget1 = pg.PlotWidget(self)
        self.graphWidget1.setGeometry(300,20,300,150)

        self.graphWidget2 = pg.PlotWidget(self)
        self.graphWidget2.setGeometry(650,20,300,150)

        self.graphWidget3 = pg.PlotWidget(self)
        self.graphWidget3.setGeometry(650,190,300,150)

        radiobutton = QRadioButton("Sine", self)
        radiobutton.setChecked(True)
        radiobutton.wave = "sinusoidal"
        radiobutton.toggled.connect(self.onClicked)
        radiobutton.setStyleSheet("color: white;")
        radiobutton.setGeometry(1000, 40, 200, 30)

        radiobutton = QRadioButton("Triangle", self)
        radiobutton.wave = "triangle"
        radiobutton.toggled.connect(self.onClicked)
        radiobutton.setStyleSheet("color: white;")
        radiobutton.setGeometry(1000, 100, 200, 31)

        radiobutton = QRadioButton("Sawtooth", self)
        radiobutton.wave = "sawtooth"
        radiobutton.toggled.connect(self.onClicked)
        radiobutton.setStyleSheet("color: white;")
        radiobutton.setGeometry(1000, 160, 200, 32)

        radiobutton = QRadioButton("Square", self)
        radiobutton.wave = "square"
        radiobutton.toggled.connect(self.onClicked)
        radiobutton.setStyleSheet("color: white;")
        radiobutton.setGeometry(1000, 220, 200, 32)

        radiobutton = QRadioButton("Noise", self)
        radiobutton.wave = "noise"
        radiobutton.toggled.connect(self.onClicked)
        radiobutton.setStyleSheet("color: white;")
        radiobutton.setGeometry(1000, 280, 200, 32)

        self.lfo = QCheckBox('LFO', self)
        self.lfo.name = 'lfo_box'
        self.lfo.toggled.connect(self.active_lfo)
        self.lfo.setStyleSheet("color: white;")
        self.lfo.setGeometry(40, 250, 100, 32)

        self.lowpass_check = QCheckBox('Filter', self)
        self.lowpass_check.name = 'lowpass'
        self.lowpass_check.setStyleSheet("color: white;")
        self.lowpass_check.setGeometry(300, 190, 100, 32)

        self.delay_box = QCheckBox('Delay', self)
        self.delay_box.name = 'delay_box'
        self.delay_box.toggled.connect(self.set_delay)
        self.delay_box.setStyleSheet("color: white;")
        self.delay_box.setGeometry(40, 430, 100, 32)

        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

        play_button = QPushButton('Play', self)
        play_button.name = 'play'
        play_button.clicked.connect(self.play_mode)
        play_button.setStyleSheet("color: white; border: 1px solid white; border-radius: 5px; background: black;")
        play_button.setGeometry(700, 380, 200, 32)

        play_button = QPushButton('Stop', self)
        play_button.name = 'stop'
        play_button.clicked.connect(self.play_mode)
        play_button.setStyleSheet("color: white; border: 1px solid white; border-radius: 5px; background: black;")
        play_button.setGeometry(700, 440, 200, 32)

        order = 12 #orden del filtro
        nyq = 0.5 * self.fs #máxima frecuencia
        normal_cutoff = 100 / nyq #calculo real de frecuencia de corte
        b, a = butter(order, normal_cutoff, btype='low', analog=False) #generacion de numerador y denominador del modelo matematico del filtro
        w, h = signal.freqs(b, a)
        self.graphWidget3.setLogMode(True, False)
        self.graphWidget3.setXRange(1,5)
        self.graphWidget3.setYRange(-100,100)
        self.data_filter = self.graphWidget3.plot(w, 20 * np.log10(abs(h)))

        # inicializar ventana de GUI
        self.setGeometry(50,50,1100,600)
        self.setWindowTitle("Synthesizer")
        self.show()

    def set_delay(self):
        self.delay = self.mySlider8.value()
        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def set_order(self):
        self.forder = self.mySlider7.value()
        self.set_filter()

    def set_filter(self):
        normal_cutoff = self.mySlider6.value()
        if self.ftype in ['bandpass','bandstop']:
            b, a = butter(self.forder, [(normal_cutoff - self.mySliderQ.value() * 0.5), (normal_cutoff + self.mySliderQ.value() * 0.5)], btype=self.ftype, analog=True) #generacion de numerador y denominador del modelo matematico del filtro
        else:    
            b, a = butter(self.forder, normal_cutoff, btype=self.ftype, analog=True) #generacion de numerador y denominador del modelo matematico del filtro
        w, h = signal.freqs(b, a)
        y = 20 * np.log10(abs(h))
        self.data_filter.setData(w, y)

    def apply_filter(self, sig, cutoff):
        nyq = 0.5 * self.fs #máxima frecuencia
        normal_cutoff = cutoff / nyq #calculo real de frecuencia de corte
        if self.ftype in ['bandpass','bandstop']:
            b, a = butter(self.forder, [(cutoff - self.mySliderQ.value() * 0.5) / nyq, (cutoff + self.mySliderQ.value() * 0.5) / nyq], btype=self.ftype, analog=False) #generacion de numerador y denominador del modelo matematico del filtro
        else:    
            b, a = butter(self.forder, normal_cutoff, btype=self.ftype, analog=False) #generacion de numerador y denominador del modelo matematico del filtro
        
        r = lfilter(b, a, sig)
        return r

    def onClickedF(self):
        # control de los radiobutton de tipo de filtro
        radioButton = self.sender()
        if radioButton.isChecked():
            self.ftype = radioButton.name

        self.set_filter()

    def onClicked(self):
        # control de radiobutton de tipo de onda
        radioButton = self.sender()
        if radioButton.isChecked():
            self.wave = radioButton.wave
            self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def active_lfo(self):
        # generacion de onda moduladora segun posicion de sliders
        radioButton = self.sender()
        if radioButton.name != 'slider_lfo':
            if radioButton.isChecked():
                self.LFO = (self.mySlider5.value() / 200) * (np.sin(self.mySlider4.value() * self.t * 2 * np.pi) + (self.mySlider5.value() / 100))
            else:
                self.LFO = np.ones(self.fs)
        else:
            self.LFO = (self.mySlider5.value() / 200) * (np.sin(self.mySlider4.value() * self.t * 2 * np.pi) + (self.mySlider5.value() / 100))

        message = 'LFO: ' + str(self.mySlider4.value()) + 'Hz'
        self.myLabel4.setText(message)

        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def calculate_ASDR(self, a, d, s, r):
        # se genera la forma que va a afectar a la senal resultante por medio de su amplitud
        if a + d + r >= 44100:
            raise Exception('sum','have to complete 44100 samples')
        a = (np.logspace(1, 0, a) / 10) * -1 + 1.1
        d = np.logspace(1, s / 11025, d) / 10
        r = np.logspace(s / 11025, 0, r) / 10
        s = np.ones(self.fs - len(a) - len(d) - len(r)) * 10**(s / 11025) / 10

        adsr = np.concatenate((a,d,s,r)) * 1.1 - 0.1
        signal = self.waveform(self.wave, 15, adsr)

        # actualizacion de graficas
        if not self.started:
            self.data_line = self.graphWidget1.plot(self.t, adsr)
            self.signal_line = self.graphWidget2.plot(self.t, signal)
            self.started = True
        else:
            self.signal_line.setData(self.t, signal)
            self.data_line.setData(self.t, adsr)

        return adsr

    def change_knob(self, value):
        # sliders que controlan valores de la senal envolvente
        knob = self.sender()
        message = knob.name + ': ' + str(value / 44.1)[:3] + 'ms'
        if knob.name == "Attack":
            self.a_knob = value
            self.mySlider2.setValue(self.d_knob)
            self.myLabel1.setText(message)
        elif knob.name == "Decay":
            self.d_knob = value
            self.mySlider3.setValue(self.s_knob)
            self.myLabel2.setText(message)
        elif knob.name == "Sustain":
            self.s_knob = value
            self.myLabel3.setText(message)
        elif knob.name == "Release":
            self.r_knob = value
            self.myLabelR.setText(message)

        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def waveform(self, form, frequency, adsr):
        # se controla la forma de onda segun radiobutton seleccionado, se utilizan funciones ya existentes de numpy y scipy
        if form == "sinusoidal":
            armed_signal = np.sin(frequency * self.t * 2 * np.pi)
        elif form == "triangle":
            armed_signal = signal.sawtooth(frequency * self.t * 2 * np.pi, 0.5)
        elif form == "sawtooth":
            armed_signal = signal.sawtooth(frequency * self.t * 2 * np.pi, 1)
        elif form == "square":
            armed_signal = signal.square(frequency * self.t * 2 * np.pi)
        elif form == "noise":
            armed_signal = self.noise
        
        # se aplican efectos segun esten activados por los checkbox
        if self.lowpass_check.isChecked() and frequency != 15:
            armed_signal = self.apply_filter(armed_signal, self.mySlider6.value())

        armed_signal = armed_signal * adsr
        if self.lfo.isChecked():
            armed_signal = armed_signal * self.LFO

        if self.delay_box.isChecked():
            delayed_signal =  np.concatenate( (np.zeros(self.mySlider8.value()), armed_signal[:-self.mySlider8.value()]) )
            armed_signal = armed_signal + delayed_signal * 0.5

        armed_signal = armed_signal / np.max(np.abs(armed_signal))

        return armed_signal

    def play_mode(self):
        button = self.sender()
        if button.name == 'play':
            self.pill2kill = Event()
            self.t1 = Thread(target=self.run_synth)
            self.t1.do_run = True
            self.t1.start()
        else:
            self.t1.do_run = False
            time.sleep(1)
            self.t1.join()

    def run_synth(self):
        t1 = currentThread()

        p = pyaudio.PyAudio()

        stream = p.open(format = pyaudio.paFloat32,
                        channels = 1,
                        rate = self.fs,
                        output = True)
        chunk = 1024
        
        #teclas, notas y banderas de estado parametrizadas
        keys = ['z','s','x','d','c','v','g','b','h','n','j','m']
        flags = [False,False,False,False,False,False,False,False,False,False,False,False,False,False]
        notes = [246,261,277,293,311,329,349,369,392,415,440,466]
        octave = 1
        
        # listener de presion de botones del teclado
        while t1.do_run:
            #time.sleep(0.002)
            if keyboard.is_pressed('q') and not flags[-1]:
                print("closed")
                break

            if keyboard.is_pressed('p') and not flags[-1]:
                octave *= 2
                flags[-1] = True
            elif flags[-1] and not keyboard.is_pressed('p'):
                flags[-1] = False

            if keyboard.is_pressed('o') and not flags[-2]:
                octave /= 2
                flags[-2] = True
            elif flags[-2] and not keyboard.is_pressed('o'):
                flags[-2] = False
            

            for i,j in enumerate(keys):
                if keyboard.is_pressed(j):
                    if not flags[i]: 
                        note = self.waveform(self.wave, notes[i] * octave, self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob))
                        data = note.astype(np.float32)
                        flags[i] = True
                    stream.write(data, chunk)
                    data = np.concatenate((data[chunk:],data[:chunk]))
                elif flags[i] and not keyboard.is_pressed(j):
                    flags[i] = False

        stream.close()
        p.terminate()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())