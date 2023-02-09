import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QRadioButton,
    QPushButton,
    QCheckBox,
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
import pyqtgraph as pg
import numpy as np
from scipy import signal
from scipy.signal import butter, cheby1, lfilter
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
## Version: 0.1.0
## Email: jkamo_84@hotmail.com
## Status: development
##################################################


class SignalCommunicate(QObject):
    request_filter_update = pyqtSignal(np.ndarray, np.ndarray)
    request_ADSR_update = pyqtSignal(np.ndarray, np.ndarray)
    request_signal_update = pyqtSignal(np.ndarray, np.ndarray)


class Synthesizer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.started = False
        self.wave = "sinusoidal"
        self.fs = 44100
        self.LFO = np.ones(self.fs)
        self.t = np.linspace(0, 1, self.fs)
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
        # self.graphWidget2.setXRange(1, 5)
        self.graphWidget2.setYRange(-1, 1)

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
        b, a = cheby1(
            order, 12, normal_cutoff, btype="low", analog=True
        )  # generacion de numerador y denominador del modelo matematico del filtro
        w, h = signal.freqs(b, a)
        self.data_filter = self.graphWidget3.plot(w * 22050, 20 * np.log10(abs(h)))
        self.graphWidget3.setLogMode(True, False)
        self.graphWidget3.setXRange(1, 5)
        self.graphWidget3.setYRange(-50, 10)
        self.filter_state1 = np.zeros(4)
        self.filter_state2 = np.zeros(8)

        self.signal_comm = SignalCommunicate()
        self.signal_comm.request_signal_update.connect(self.update_signal_graph)
        self.signal_comm.request_ADSR_update.connect(self.update_ADSR_graph)
        self.signal_comm.request_filter_update.connect(self.update_filter_graph)

        # inicializar ventana de GUI
        self.setGeometry(50, 50, 1100, 600)
        self.setWindowTitle("Synthesizer")
        self.show()

        self.init_synth()

    def update_signal_graph(self, x, y):
        self.signal_line.setData(x, y)

    def update_ADSR_graph(self, x, y):
        self.data_line.setData(x, y)

    def update_filter_graph(self, x, y):
        self.data_filter.setData(x, y)

    def set_delay(self):
        self.delay = self.mySlider8.value()

    def set_order(self):
        self.forder = self.mySlider7.value()
        self.set_filter()

    def set_filter(self):
        normal_cutoff = self.mySlider6.value()
        nyq = 0.5 * self.fs  # máxima frecuencia
        normal_cutoff = normal_cutoff / nyq  # calculo real de frecuencia de corte
        if self.ftype in ["bandpass", "bandstop"]:
            b, a = butter(
                self.forder,
                [
                    (normal_cutoff - self.mySliderQ.value() * 0.5 / nyq),
                    (normal_cutoff + self.mySliderQ.value() * 0.5 / nyq),
                ],
                btype=self.ftype,
                analog=True,
            )  # generacion de numerador y denominador del modelo matematico del filtro
        else:
            b, a = butter(
                self.forder, normal_cutoff, btype=self.ftype, analog=True
            )  # generacion de numerador y denominador del modelo matematico del filtro
            b, a = cheby1(self.forder, 12, normal_cutoff, btype=self.ftype, analog=True)
        w, h = signal.freqs(b, a)
        y = 20 * np.log10(abs(h))
        self.signal_comm.request_filter_update.emit(w * 22050, y)

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
            r, self.filter_state2 = lfilter(b, a, sig, axis=0, zi=self.filter_state2)
        else:
            b, a = butter(
                self.forder, normal_cutoff, btype=self.ftype, analog=False
            )  # generacion de numerador y denominador del modelo matematico del filtro
            b, a = cheby1(self.forder, 6, normal_cutoff, btype=self.ftype, analog=False)
            r, self.filter_state1 = lfilter(b, a, sig, axis=0, zi=self.filter_state1)
            if self.ftype == "low":
                r *= 2

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

        # actualizacion de graficas
        if not self.started:
            self.data_line = self.graphWidget1.plot(self.t, adsr)
            self.signal_line = self.graphWidget2.plot(
                np.linspace(0, 2048 / self.fs, 2048), np.zeros(2048)
            )
            self.started = True
        else:
            self.signal_comm.request_ADSR_update.emit(self.t, adsr)

        return 0.707 * adsr

    def change_knob(self, value):
        # sliders que controlan valores de la senal envolvente
        knob = self.sender()
        units = "" if knob.name == "Sustain" else "ms"
        v = str(value / 44.1)[:3]
        v = str(value * 2 / 44.1)[:3] if knob.name == "Release" else v
        message = knob.name + ": " + v + units
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

    def get_waveform(self, frequency, t):
        if self.wave == "sinusoidal":
            armed_signal = np.sin(frequency * t * 2 * np.pi)
        elif self.wave == "triangle":
            armed_signal = 0.707 * signal.sawtooth(frequency * t * 2 * np.pi, 0.5)
        elif self.wave == "sawtooth":
            armed_signal = 0.5 * signal.sawtooth(frequency * t * 2 * np.pi, 1)
        elif self.wave == "square":
            armed_signal = 0.5 * signal.square(frequency * t * 2 * np.pi)
        elif self.wave == "noise":
            armed_signal = 0.707 * (np.random.rand(2048) * 2) - 1
        return armed_signal

    def waveform(self, frequency, played_chunk, release_chunk, chunk, feedback=3):
        # se controla la forma de onda segun radiobutton seleccionado, se utilizan funciones ya existentes de numpy y scipy
        t = np.linspace(
            (played_chunk * chunk) / self.fs,
            ((played_chunk + 1) * chunk) / self.fs,
            chunk,
            endpoint=False,
        )
        armed_signal = self.get_waveform(frequency, t)

        if self.lfo.isChecked():
            LFO = (self.mySlider5.value() / 200) * (
                np.sin(self.mySlider4.value() * t * 2 * np.pi)
                + (self.mySlider5.value() / 100)
            )
            armed_signal *= LFO

        envelope = self.calculate_ASDR(
            self.a_knob, self.d_knob, self.s_knob, self.r_knob
        )
        if played_chunk < 1 + (self.a_knob + self.d_knob) // chunk:
            armed_signal *= envelope[
                (played_chunk * chunk) : ((played_chunk + 1) * chunk)
            ]
        else:
            if release_chunk > 0:
                release = (
                    0.707 * np.logspace(synth.s_knob / 11025, 0, synth.r_knob * 2) / 10
                )
                release = np.concatenate((release, np.zeros(synth.fs)))
                armed_signal *= release[
                    release_chunk * chunk : (release_chunk + 1) * chunk
                ]
            else:
                armed_signal *= (
                    0.707 * np.ones(chunk) * 10 ** (self.s_knob / 11025) / 10
                )

        if self.lowpass_check.isChecked() and frequency != 15:
            armed_signal = self.apply_filter(armed_signal, self.mySlider6.value())

        # se aplican efectos segun esten activados por los checkbox

        if self.delay_box.isChecked() and feedback > 0:
            delay_chunks = self.mySlider8.value() // chunk + 1
            if played_chunk >= delay_chunks:
                delayed_signal = self.waveform(
                    frequency,
                    played_chunk - delay_chunks,
                    release_chunk - delay_chunks,
                    chunk,
                    feedback - 1,
                )
                armed_signal = armed_signal + delayed_signal * 0.5

        self.signal_comm.request_signal_update.emit(
            np.linspace(0, chunk / synth.fs, chunk), armed_signal
        )

        return armed_signal

    def init_synth(self):
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

    chunk = 2048
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=synth.fs,
        output=True,
        frames_per_buffer=chunk,
    )

    # teclas, notas y banderas de estado parametrizadas
    keys = ["z", "s", "x", "d", "c", "v", "g", "b", "h", "n", "j", "m"]
    flags = [False for _ in range(14)]
    notes = [246, 261, 277, 293, 311, 329, 349, 369, 392, 415, 440, 466]
    octave = 1
    played_chunk = 0

    # listener de presion de botones del teclado
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
                    flags = [False for _ in range(14)]
                    flags[i] = True
                    played_chunk = 0
                    release_chunk = 0
                signal = synth.waveform(
                    notes[i] * octave, played_chunk, release_chunk, chunk
                )
                data = signal.astype(np.float32)
                stream.write(data, chunk)
                played_chunk += 1
            elif flags[i] and not keyboard.is_pressed(j):
                signal = synth.waveform(
                    notes[i] * octave, played_chunk, release_chunk, chunk
                )

                data = signal.astype(np.float32)
                stream.write(data, chunk)
                release_chunk += 1
                played_chunk += 1
                if release_chunk > 17:
                    flags[i] = False
            else:
                print(".")

    stream.close()
    p.terminate()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    synth = Synthesizer()
    sys.exit(app.exec_())
