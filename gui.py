from typing import Callable

from PyQt5.QtWidgets import (
    QApplication,
    QGroupBox,
    QMainWindow,
    QSlider,
    QLabel,
    QRadioButton,
    QPushButton,
    QCheckBox,
    QVBoxLayout,
)
from PyQt5.QtCore import Qt


class GUI:
    def __init__(self, synth: object) -> None:
        self.synth = synth
        self.synth.myLabel1 = self.create_label("Attack: 0ms", pos=(40, 10))
        self.synth.myLabel2 = self.create_label("Decay: 0ms", pos=(40, 70))
        self.synth.myLabel3 = self.create_label("Sustain: 0", pos=(40, 130))
        self.synth.myLabelR = self.create_label("Release: 0ms", pos=(40, 190))
        self.synth.mySlider1 = self.create_slider(
            "Attack",
            geo=(30, 40, 200, 30),
            default=self.synth.a_knob,
            value_change=self.synth.change_knob,
        )
        self.synth.mySlider2 = self.create_slider(
            "Decay",
            geo=(30, 100, 200, 30),
            max=11025,
            default=self.synth.d_knob,
            value_change=self.synth.change_knob,
        )
        self.synth.mySlider3 = self.create_slider(
            "Sustain",
            geo=(30, 160, 200, 30),
            max=11025,
            default=self.synth.s_knob,
            value_change=self.synth.change_knob,
        )
        self.synth.mySliderR = self.create_slider(
            "Release",
            geo=(30, 220, 200, 30),
            max=11025,
            default=self.synth.r_knob,
            value_change=self.synth.change_knob,
        )
        self.synth.myLabel4 = self.create_label("LFO: 1Hz", pos=(40, 310))
        self.synth.mySlider4 = self.create_slider(
            "slider_lfo",
            geo=(30, 340, 200, 30),
            max=100,
            default=100,
            value_change=self.synth.active_lfo,
        )

        self.synth.myLabel5 = self.create_label("LFO offset", pos=(40, 370))
        self.synth.mySlider5 = self.create_slider(
            "slider_lfo",
            geo=(30, 400, 200, 30),
            max=100,
            default=100,
            value_change=self.synth.active_lfo,
        )

        self.synth.myLabel6 = self.create_label("Cutoff Frequency", pos=(300, 230))
        self.synth.mySlider6 = self.create_slider(
            "slider_filter",
            geo=(300, 260, 200, 30),
            min=100,
            max=8000,
            default=100,
            value_change=self.synth.set_filter,
        )

        self.synth.myLabelQ = self.create_label("Band Width", pos=(300, 290))
        self.synth.mySliderQ = self.create_slider(
            "slider_filter",
            geo=(300, 320, 200, 30),
            min=10,
            max=1000,
            default=10,
            value_change=self.synth.set_filter,
        )

        self.synth.myLabel7 = self.create_label("Filter Order", pos=(300, 350))
        self.synth.mySlider7 = self.create_slider(
            "order_filter",
            geo=(300, 380, 200, 30),
            max=16,
            default=4,
            value_change=self.synth.set_order,
        )

        self.synth.myLabel8 = self.create_label("Delay", pos=(40, 490))
        self.synth.mySlider8 = self.create_slider(
            "delay",
            geo=(40, 520, 200, 30),
            default=11025,
            value_change=self.synth.set_delay,
        )

    def create_slider(
        self,
        name,
        geo: tuple = (0, 0, 0, 0),
        min: int = 1,
        max: int = 22050,
        default: int = 1,
        value_change: Callable = lambda: None,
    ):
        slider = QSlider(Qt.Horizontal, self.synth)
        slider.setGeometry(*geo)
        slider.setMinimum(min)
        slider.name = name
        slider.setMaximum(max)
        slider.setValue(default)
        slider.valueChanged[int].connect(value_change)
        return slider

    def create_label(
        self, text: str, style: str = "color: white;", pos: tuple = (0, 0)
    ):
        label = QLabel(self.synth)
        label.setText(text)
        if style is not None:
            label.setStyleSheet(style)
        label.move(*pos)
        return label
