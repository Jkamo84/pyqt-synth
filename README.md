# pyqt-synth

A real-time polyphonic synthesizer application built with Python and PyQt5.

![pyqt-synth Screenshot](https://via.placeholder.com/600x400.png?text=Add+a+screenshot+of+your+app+here!)
*A screenshot of the synthesizer interface would be great here!*

## Features

*   Real-time audio synthesis.
*   Interactive GUI built with PyQt5.
*   Multiple waveform oscillators (e.g., Sine, Square, Sawtooth).
*   ADSR (Attack, Decay, Sustain, Release) envelope controls.
*   (Add any other features your synthesizer has!)

## Prerequisites

*   Python 3.8+
*   `pip` and `venv`

## Quickstart

Follow these steps to get the synthesizer up and running.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/pyqt-synth.git
cd pyqt-synth
```

### 2. Create a Virtual Environment and Install Dependencies

It's recommended to use a virtual environment to manage project dependencies.

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt
```

### 3. Run the Synthesizer

Once the dependencies are installed, you can start the application.

```bash
python synthetizer.py
```

### Explanation of the `PyInstaller` command:

*   `pyinstaller`: The command to run the tool.
*   `--name "pyqt-synth"`: Sets the name of your executable file.
*   `--onefile`: Bundles all necessary files and libraries into a single `.exe` file for easy distribution.
*   `--windowed`: This is important for a GUI application. It prevents a console window from appearing in the background when you run the executable.
*   `synthetizer.py`: The entry point script for your application.

## Author

*   **Juan Camilo Plazas**

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
