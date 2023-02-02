import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QRadioButton,
    QPushButton,
    QCheckBox,
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from scipy import signal
from scipy.signal import butter, lfilter
import keyboard
import pyaudio
import time
from threading import Thread, Event, current_thread
from multiprocessing import Process

from gui import GUI

##################################################
## A real time-based synthetizer made with pyaudio and pyqt5
## functioning AM modulation, filters, delays and waveforms
##################################################
## Author: Juan Camilo Plazas
## Version: 0.0.2
## Email: jkamo_84@hotmail.com
## Status: development
##################################################


class Synthesizer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.started = False
        self.wave = "sinusoidal"
        self.fs = 44100
        self.LFO = np.ones(self.fs)
        self.t = np.linspace(0, 1, self.fs)
        self.noise = (np.random.rand(self.fs) * 2) - 1
        self.copy_noise = self.noise
        self.ftype = "low"
        self.forder = 4
        self.delay = True

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(p)

        self.a_knob = 11025
        self.d_knob = 11025
        self.s_knob = 5000
        self.r_knob = 11025

        self.t1 = None

        self.gui = GUI(self)
        # GUI

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
        self.graphWidget1.setGeometry(300, 20, 300, 150)

        self.graphWidget2 = pg.PlotWidget(self)
        self.graphWidget2.setGeometry(650, 20, 300, 150)

        self.graphWidget3 = pg.PlotWidget(self)
        self.graphWidget3.setGeometry(650, 190, 300, 150)

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

        self.lfo = QCheckBox("LFO", self)
        self.lfo.name = "lfo_box"
        self.lfo.toggled.connect(self.active_lfo)
        self.lfo.setStyleSheet("color: white;")
        self.lfo.setGeometry(40, 250, 100, 32)

        self.lowpass_check = QCheckBox("Filter", self)
        self.lowpass_check.name = "lowpass"
        self.lowpass_check.setStyleSheet("color: white;")
        self.lowpass_check.setGeometry(300, 190, 100, 32)

        self.delay_box = QCheckBox("Delay", self)
        self.delay_box.name = "delay_box"
        self.delay_box.toggled.connect(self.set_delay)
        self.delay_box.setStyleSheet("color: white;")
        self.delay_box.setGeometry(40, 430, 100, 32)

        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

        order = 12  # orden del filtro
        nyq = 0.5 * self.fs  # máxima frecuencia
        normal_cutoff = 100 / nyq  # calculo real de frecuencia de corte
        b, a = butter(
            order, normal_cutoff, btype="low", analog=False
        )  # generacion de numerador y denominador del modelo matematico del filtro
        w, h = signal.freqs(b, a)
        self.graphWidget3.setLogMode(True, False)
        self.graphWidget3.setXRange(1, 5)
        self.graphWidget3.setYRange(-100, 100)
        self.data_filter = self.graphWidget3.plot(w, 20 * np.log10(abs(h)))

        # inicializar ventana de GUI
        self.setGeometry(50, 50, 1100, 600)
        self.setWindowTitle("Synthesizer")
        self.show()
        self.init_synth()

    def set_delay(self):
        self.delay = self.mySlider8.value()
        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def set_order(self):
        self.forder = self.mySlider7.value()
        self.set_filter()

    def set_filter(self):
        normal_cutoff = self.mySlider6.value()
        if self.ftype in ["bandpass", "bandstop"]:
            b, a = butter(
                self.forder,
                [
                    (normal_cutoff - self.mySliderQ.value() * 0.5),
                    (normal_cutoff + self.mySliderQ.value() * 0.5),
                ],
                btype=self.ftype,
                analog=True,
            )  # generacion de numerador y denominador del modelo matematico del filtro
        else:
            b, a = butter(
                self.forder, normal_cutoff, btype=self.ftype, analog=True
            )  # generacion de numerador y denominador del modelo matematico del filtro
        w, h = signal.freqs(b, a)
        y = 20 * np.log10(abs(h))
        self.data_filter.setData(w, y)

    def apply_filter(self, sig, cutoff):
        nyq = 0.5 * self.fs  # máxima frecuencia
        normal_cutoff = cutoff / nyq  # calculo real de frecuencia de corte
        if self.ftype in ["bandpass", "bandstop"]:
            b, a = butter(
                self.forder,
                [
                    (cutoff - self.mySliderQ.value() * 0.5) / nyq,
                    (cutoff + self.mySliderQ.value() * 0.5) / nyq,
                ],
                btype=self.ftype,
                analog=False,
            )  # generacion de numerador y denominador del modelo matematico del filtro
        else:
            b, a = butter(
                self.forder, normal_cutoff, btype=self.ftype, analog=False
            )  # generacion de numerador y denominador del modelo matematico del filtro

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
        if radioButton.name != "slider_lfo":
            if radioButton.isChecked():
                self.LFO = (self.mySlider5.value() / 200) * (
                    np.sin(self.mySlider4.value() * self.t * 2 * np.pi)
                    + (self.mySlider5.value() / 100)
                )
            else:
                self.LFO = np.ones(self.fs)
        else:
            self.LFO = (self.mySlider5.value() / 200) * (
                np.sin(self.mySlider4.value() * self.t * 2 * np.pi)
                + (self.mySlider5.value() / 100)
            )

        message = "LFO: " + str(self.mySlider4.value()) + "Hz"
        self.myLabel4.setText(message)

        self.calculate_ASDR(self.a_knob, self.d_knob, self.s_knob, self.r_knob)

    def calculate_ASDR(self, a, d, s, r):
        # se genera la forma que va a afectar a la senal resultante por medio de su amplitud
        if a + d + r >= self.fs:
            raise Exception("sum", "have to complete 44100 samples")
        a = (np.logspace(1, 0, a) / 10) * -1 + 1.1
        d = np.logspace(1, s / 11025, d) / 10
        r = np.logspace(s / 11025, 0, r) / 10
        s = np.ones(self.fs - len(a) - len(d) - len(r)) * 10 ** (s / 11025) / 10

        adsr = np.concatenate((a, d, s, r)) * 1.1 - 0.1
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
        units = "" if knob.name == "Sustain" else "ms"
        message = knob.name + ": " + str(value / 44.1)[:3] + units
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
            delayed_signal = np.concatenate(
                (
                    np.zeros(self.mySlider8.value()),
                    armed_signal[: -self.mySlider8.value()],
                )
            )
            armed_signal = armed_signal + delayed_signal * 0.5

        armed_signal = armed_signal / np.max(np.abs(armed_signal))

        return armed_signal

    def init_synth(self):
        # self.pill2kill = Event()
        self.t1 = Thread(target=run_synth, args=(self,), daemon=True)
        self.t1.do_run = True
        self.t1.start()

    def closeEvent(self, event):
        if self.t1 is not None:
            self.t1.do_run = False
            time.sleep(1)
            self.t1.join()
        event.accept()


def run_synth(synth):
    t1 = current_thread()

    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=synth.fs, output=True)
    chunk = 1024

    # teclas, notas y banderas de estado parametrizadas
    keys = ["z", "s", "x", "d", "c", "v", "g", "b", "h", "n", "j", "m"]
    flags = [False for _ in range(14)]
    notes = [246, 261, 277, 293, 311, 329, 349, 369, 392, 415, 440, 466]
    octave = 1
    zeros = np.sin(0 * synth.t * 2 * np.pi)
    fade_in = np.linspace(0, 1, num=chunk)
    fade_out = np.linspace(1, 0, num=chunk)

    # listener de presion de botones del teclado
    print("")
    while t1.do_run:
        # time.sleep(0.002)
        if keyboard.is_pressed("q") and not flags[-1]:
            print("closed")
            break

        if keyboard.is_pressed("p") and not flags[-1]:
            octave *= 2
            flags[-1] = True
        elif flags[-1] and not keyboard.is_pressed("p"):
            flags[-1] = False

        if keyboard.is_pressed("o") and not flags[-2]:
            octave /= 2
            flags[-2] = True
        elif flags[-2] and not keyboard.is_pressed("o"):
            flags[-2] = False

        for i, j in enumerate(keys):
            if keyboard.is_pressed(j):
                if not flags[i]:
                    note = synth.waveform(
                        synth.wave,
                        notes[i] * octave,
                        synth.calculate_ASDR(
                            synth.a_knob, synth.d_knob, synth.s_knob, synth.r_knob
                        ),
                    )
                    data = note.astype(np.float32)
                    data[:chunk] = data[:chunk] * fade_in
                    flags[i] = True
                stream.write(data, chunk)
                data = np.concatenate((data[chunk:], data[:chunk]))
            elif flags[i] and not keyboard.is_pressed(j):
                flags[i] = False
                data[:chunk] = data[:chunk] * fade_out
                stream.write(data, chunk)
            else:
                print("", end="")

    stream.close()
    p.terminate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    synth = Synthesizer()
    sys.exit(app.exec_())
