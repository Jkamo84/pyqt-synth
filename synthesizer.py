import sys
import time
from queue import Queue
from threading import Thread

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QErrorMessage,
    QMainWindow,
    QPushButton,
    QRadioButton,
)
from scipy import signal
from scipy.signal import butter, cheby1, lfilter

from gui import GUI
from real_time_audio import run_synth

##################################################
## A real time-based synthetizer made with pyaudio and pyqt5
## functioning AM modulation, filters, delays and waveforms
##################################################
## Author: Juan Camilo Plazas
## Version: 0.1.2
## Email: jkamo_84@hotmail.com
## Status: development
##################################################

VERSION = "0.1.2"
SAMPLE_RATE = 44100


class SignalCommunicate(QObject):
    request_filter_update = pyqtSignal(np.ndarray, np.ndarray)
    request_ADSR_update = pyqtSignal(np.ndarray, np.ndarray)
    request_signal_update = pyqtSignal(np.ndarray, np.ndarray)


class Synthesizer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.started = False
        self.wave = "sinusoidal"
        self.fs = SAMPLE_RATE
        self.t = np.linspace(0, 1, self.fs)  # Used for plotting ADSR envelope
        self.ftype = "low"  # Default filter type
        self.forder = 2

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(p)

        # --- ADSR Parameters ---
        self.a_knob = 11025
        self.d_knob = 11025
        self.s_knob = 5000
        self.r_knob = 11025
        self.adsr_envelope = np.zeros(self.fs)

        # --- Filter Parameters ---
        self.filter_state = np.zeros(self.forder)
        self.filter_b = np.array([1.0])
        self.filter_a = np.array([1.0])

        # --- Inter-thread communication ---
        self.waveform_queue = Queue()

        self.t1 = None

        self.gui = GUI(self)
        self._setup_ui()

        self.signal_comm = SignalCommunicate()
        self.signal_comm.request_signal_update.connect(self.update_signal_graph)
        self.signal_comm.request_ADSR_update.connect(self.update_ADSR_graph)
        self.signal_comm.request_filter_update.connect(self.update_filter_graph)

        # inicializar ventana de GUI
        self.setGeometry(50, 50, 1100, 600)
        self.setWindowTitle("Synthesizer")
        self.show()

        self.init_synth()

        # Timer to update the waveform graph without blocking the audio thread
        self.graph_update_timer = pg.QtCore.QTimer()
        self.graph_update_timer.timeout.connect(self.update_waveform_graph)
        self.graph_update_timer.start(33)  # Update roughly 30 times per second

    def _setup_ui(self):
        """Create and arrange all GUI widgets."""
        # Filter Type Radio Buttons
        filter_radios = {
            "Highpass": (400, 500),
            "Lowpass": (400, 540),
            "Bandpass": (300, 500),
            "Bandstop": (300, 540),
        }
        for name, pos in filter_radios.items():
            rb = QRadioButton(name, self)
            rb.name = name.lower()
            rb.toggled.connect(self.onClickedF)
            rb.setStyleSheet("color: white;")
            rb.setGeometry(pos[0], pos[1], 100, 32)

        # Plot Widgets
        self.graphWidget1 = pg.PlotWidget(self)  # ADSR
        self.graphWidget1.setGeometry(300, 20, 300, 150)

        self.graphWidget2 = pg.PlotWidget(self)  # Waveform
        self.graphWidget2.setGeometry(650, 20, 300, 150)
        self.graphWidget2.setYRange(-1, 1)

        self.graphWidget3 = pg.PlotWidget(self)  # Filter response
        self.graphWidget3.setGeometry(650, 190, 300, 150)

        # Waveform Type Radio Buttons
        wave_radios = {
            "Sine": ("sinusoidal", (1000, 40)),
            "Triangle": ("triangle", (1000, 100)),
            "Sawtooth": ("sawtooth", (1000, 160)),
            "Square": ("square", (1000, 220)),
            "Noise": ("noise", (1000, 280)),
        }
        self.wave_radio_buttons = []
        for name, (wave_type, pos) in wave_radios.items():
            rb = QRadioButton(name, self)
            rb.wave = wave_type
            rb.toggled.connect(self.onClicked)
            rb.setStyleSheet("color: white;")
            rb.setGeometry(pos[0], pos[1], 200, 30)
            self.wave_radio_buttons.append(rb)
        self.wave_radio_buttons[0].setChecked(True)

        # Checkboxes
        self.lfo = QCheckBox("LFO", self)
        self.lfo.toggled.connect(self.active_lfo)
        self.lfo.setStyleSheet("color: white;")
        self.lfo.setGeometry(40, 280, 100, 32)

        self.lowpass_check = QCheckBox("Filter", self)
        self.lowpass_check.setStyleSheet("color: white;")
        self.lowpass_check.setGeometry(300, 190, 100, 32)

        self.delay_box = QCheckBox("Delay", self)
        # self.delay_box.toggled.connect(self.set_delay) # This is not needed
        self.delay_box.setStyleSheet("color: white;")
        self.delay_box.setGeometry(40, 490, 100, 32)

        # Initial state setup
        self.update_adsr_envelope()
        self.set_filter(init=True)

    def set_filter(self, init=False):
        """Calculates and plots the filter frequency response."""
        if init:
            # Initial filter plot setup
            order = 2
            nyq = 0.5 * self.fs
            normal_cutoff = 100 / nyq
            b, a = cheby1(order, 12, normal_cutoff, btype="low", analog=True)
            w, h = signal.freqs(b, a)
            h *= 2
            self.data_filter = self.graphWidget3.plot(w * 22050, 20 * np.log10(abs(h)))
            self.graphWidget3.setLogMode(True, False)
            self.graphWidget3.setXRange(1, 5)
            self.graphWidget3.setYRange(-20, 10)
        else:
            # Update filter plot and coefficients
            b, a = self.calculate_filter_coeffs(analog=True)
            w, h = signal.freqs(b, a)
            if self.ftype not in ["bandpass", "bandstop"]:
                h *= 2
            y = 20 * np.log10(abs(h))
            self.signal_comm.request_filter_update.emit(w * 22050, y)

        # Cache digital filter coefficients for the audio thread
        self.filter_b, self.filter_a = self.calculate_filter_coeffs(analog=False)

    def update_signal_graph(self, x, y):
        self.signal_line.setData(x, y)

    def update_ADSR_graph(self, x, y):
        self.data_line.setData(x, y)

    def update_filter_graph(self, x, y):
        self.data_filter.setData(x, y)

    def set_order(self):
        self.forder = self.mySlider7.value()
        self.filter_state = np.zeros(self.forder)
        if self.ftype in ["bandpass", "bandstop"]:
            self.filter_state = np.zeros(self.forder * 2)
        self.set_filter()

    def calculate_filter_coeffs(self, analog=False):
        normal_cutoff = self.mySlider6.value()
        nyq = 0.5 * self.fs  # máxima frecuencia
        normal_cutoff = normal_cutoff / nyq  # calculo real de frecuencia de corte
        if self.ftype in ["bandpass", "bandstop"]:
            b, a = butter(
                self.forder,
                [  # This calculation for band edges might need review
                    (normal_cutoff - self.mySliderQ.value() * 0.5 / nyq),
                    (normal_cutoff + self.mySliderQ.value() * 0.5 / nyq),
                ],
                btype=self.ftype,
                analog=analog,
            )  # generacion de numerador y denominador del modelo matematico del filtro
        else:
            b, a = cheby1(
                self.forder, 12, normal_cutoff, btype=self.ftype, analog=analog
            )
        return b, a

    def apply_filter(self, sig):
        # Use cached filter coefficients
        try:
            r, self.filter_state = lfilter(
                self.filter_b, self.filter_a, sig, axis=0, zi=self.filter_state
            )
        except ValueError:
            # This can happen if filter state is not the correct size.
            # This is a failsafe to reset it and continue.
            print("Warning: Mismatch in filter state size. Resetting filter state.")
            # The expected size for zi is max(len(a), len(b)) - 1
            expected_len = max(len(self.filter_a), len(self.filter_b)) - 1
            self.filter_state = np.zeros(expected_len)
            # Retry lfilter with the corrected state
            r, self.filter_state = lfilter(
                self.filter_b, self.filter_a, sig, axis=0, zi=self.filter_state
            )
        if self.ftype not in ["bandpass", "bandstop"]:
            r *= 2
        return r

    def onClickedF(self):
        # control de los radiobutton de tipo de filtro
        radioButton = self.sender()
        if radioButton.isChecked():
            self.ftype = radioButton.name
        self.filter_state = np.zeros(self.forder)
        if radioButton.name in ["bandpass", "bandstop"]:
            self.filter_state = np.zeros(self.forder * 2)

        self.set_filter()

    def onClicked(self):
        # control de radiobutton de tipo de onda
        radioButton = self.sender()
        if radioButton.isChecked():
            self.wave = radioButton.wave

    def active_lfo(self):
        # generacion de onda moduladora segun posicion de sliders
        message = f"LFO: {self.mySlider4.value()}Hz"
        self.myLabel4.setText(message)

    def update_adsr_envelope(self):
        """Calculates the ADSR envelope and updates the plot and cached envelope."""
        a_len, d_len, s_val, r_len = self.a_knob, self.d_knob, self.s_knob, self.r_knob

        if a_len + d_len + r_len >= self.fs:
            # Handle case where ADSR times are too long for the buffer
            # For now, just return to avoid crashing. A real implementation might scale them.
            print("Warning: ADSR times exceed sample rate.")
            return

        a = (np.logspace(1, 0, a_len) / 10) * -1 + 1.1
        d = np.logspace(1, s_val / 11025, d_len) / 10
        r = np.logspace(s_val / 11025, 0, r_len) / 10
        s_len = self.fs - a_len - d_len - r_len
        s = np.ones(s_len) * 10 ** (s_val / 11025) / 10

        self.adsr_envelope = np.concatenate((a, d, s, r)) * 1.1 - 0.1
        self.adsr_envelope *= 0.707  # Apply gain

        # Update graphs
        if not self.started:
            self.data_line = self.graphWidget1.plot(self.t, self.adsr_envelope)
            self.signal_line = self.graphWidget2.plot(
                np.linspace(0, 2048 / self.fs, 2048), np.zeros(2048)
            )
            self.started = True
        else:
            self.signal_comm.request_ADSR_update.emit(self.t, self.adsr_envelope)

    def change_knob(self, value):
        # sliders que controlan valores de la senal envolvente
        knob = self.sender()
        units = "" if knob.name == "Sustain" else "ms"
        v = str(value / 44.1)[:3]
        v = str(value * 2 / 44.1)[:3] if knob.name == "Release" else v
        message = f"{knob.name}: {v}{units}"
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

        self.update_adsr_envelope()

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
            lfo_a = self.mySlider5A.value() / 200
            lfo_off = self.mySlider5.value() / 200
            LFO = lfo_a * (np.sin(self.mySlider4.value() * t * 2 * np.pi))
            armed_signal = armed_signal * (LFO + lfo_off)

        if played_chunk < 1 + (self.a_knob + self.d_knob) // chunk:
            armed_signal *= self.adsr_envelope[
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
            armed_signal = self.apply_filter(armed_signal)

        # se aplican efectos segun esten activados por los checkbox

        # NOTE: Recursive delay is very inefficient. A delay buffer (ring buffer)
        # would be a much better approach for performance.
        if self.delay_box.isChecked() and feedback > 0:
            delay_chunks = self.mySlider8.value() // chunk  # + 1
            if played_chunk >= delay_chunks:
                delayed_signal = self.waveform(
                    frequency,
                    played_chunk - delay_chunks,
                    release_chunk - delay_chunks,
                    chunk,
                    feedback - 1,
                )
                armed_signal = armed_signal + delayed_signal * 0.5

        # Only put the final signal in the queue for plotting (not the recursive delay calls)
        if feedback == 3:
            if not self.waveform_queue.full():
                self.waveform_queue.put(armed_signal)

        return armed_signal

    def update_waveform_graph(self):
        """Reads from the queue and updates the graph in the main GUI thread."""
        if not self.waveform_queue.empty():
            data = self.waveform_queue.get()
            self.update_signal_graph(
                np.linspace(0, len(data) / self.fs, len(data)), data
            )

    def set_counter(self):
        self.v_label.setText(VERSION)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    synth = Synthesizer()
    sys.exit(app.exec_())
