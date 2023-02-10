import keyboard
import pyaudio
from threading import current_thread

import numpy as np
import time


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
                synth.set_counter()
                # data = np.zeros(chunk).astype(np.float32)
                # stream.write(np.zeros(chunk), chunk)
                # time.sleep(0.00001)

    stream.close()
    p.terminate()
