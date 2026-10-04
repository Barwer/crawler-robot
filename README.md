# Collaborative Crawler Robot

Python application for two ESP8266 crawler robots, with shared Q-learning,
MQTT command acknowledgements and ArUco camera tracking (IDs 1 and 2).

## Setup and run

Use Python 3.10 or later with Tkinter installed. Tested environment: Python 3.10 on Windows.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe Main.py
```

Start an MQTT broker first. The current broker is configured in `servo.py`
as `192.168.137.1:1883`; camera index 0 and marker IDs are in `read_maker.py`.
Robot firmware topics must match `servo.py`. The UI defaults to one robot;
choose `Robots: 2` while paused for collaborative mode. Run/Test requires
acknowledgements from all selected robots. In single mode choose Robot 1 or
Robot 2 using the single-robot selector. Robot 1 uses `servo/angles`,
`servo/crawler1_status` and marker ID 1. Robot 2 uses `servo2/angles`,
`servo2/crawler2_status` and marker ID 2. Dual mode controls both.
A camera is required for live tracking. Timeouts include the last payload
received from each selected robot; send/receive logs appear in the terminal.

## Generate markers and run checks

```powershell
.\venv\Scripts\python.exe gen_aruco.py
.\venv\Scripts\python.exe -m unittest discover -s tests -p test_ui_refactor.py -v
```

Marker images are generated locally in `aruco_markers/`. Tests generate their
own marker fixtures and do not require physical robots or a broker. Tkinter
rendering checks need a desktop session.

See `UI_ARCHITECTURE.md` for module responsibilities. Only current application
code, tests, dependency versions and documentation are tracked. Virtual
environments, generated images, experiment outputs, reports, backups and
legacy scripts stay local. New top-level source files must be added to the
allowlist in `.gitignore` before staging.

## Original project background and attribution

The following describes the original simulation; its scripts and GIF are not
part of this current code-only repository. Licensing and attribution notices
in the source files are retained.

# Crawler, Q-learning
 
Visual and interactive extension of Q-learning Crawler, based on the lectures and code from [Introduction to Artificial Intelligence, UC Berkeley](http://inst.eecs.berkeley.edu/~cs188/).

The game environment is a simplified kinematic model and the size of the action space is (13*9=) 117.
The project is small and self-contained, aiming to help gain an instinctual understanding of random walk, exploitation and exploration, the convergence of Q-value.

Alternative approach to the Crawler problem: model-based learning and MDP. The transitions are deterministic and the reward for every transition is known. In Q learning, when epsilon = 1 (meaning random exploration and no exploitation), it is equivalent to value iteration of MDP but in a random order and a less sample-efficient way.

The convergence and optimality of both Q-learning (fully explored) and value-iteration policies depend on the value of the discount factor. Increasing the discount factor from 0.8 (as demonstrated below) to 0.95, results a better policy with bigger crawling velocity (simply because the velocity is calculated without discount) but much longer convergence time.

![](stable.gif)

To train the Crawler: python crawlerMain.py.
Prerequisites: Python 3.6 (tested on Mac OS X).
