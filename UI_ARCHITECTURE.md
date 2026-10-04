# UI and logic separation

Run the application with the existing command:

```powershell
python Main.py
```

## Modules

| Module | Responsibility |
|---|---|
| `Main.py` | Imports and composes `CrawlerUI` and `CrawlerController`, then starts the application |
| `crawler_ui.py` | Tkinter widgets, button callbacks, camera image display, Q-value rendering and dialogs |
| `crawler_controller.py` | Run/Test modes, training transitions, acknowledgement polling, timeout handling, save/load and scheduling |
| `read_maker.py` | OpenCV capture, ArUco IDs 1/2 and displacement measurement; no Tkinter dependency |
| `env.py` | Robot angle/state model and legal actions; no Canvas dependency |
| `agen.py` | Q-learning |
| `servo.py` | MQTT commands and acknowledgements |

The controller receives the UI through its constructor. The UI binds button callbacks to controller methods. The controller passes plain snapshots and RGB frames to the UI; the UI does not access the learner or MQTT client. Preview updates do not consume before/after reward samples.

The tracker exposes `update_frame(measure=False)` for preview, `get_start_world()` for the before-action sample, `update_frame()` for the after-action sample, `get_distance()` and `close()`. It no longer creates a window or schedules Tk callbacks. `ArucoTrackerApp` remains an import alias for `ArucoTracker`, but callers must use the new tracker API rather than pass a Tk root.

`env.CrawlingRobot()` no longer requires a Canvas. The legacy simulation in `crawlerMain.py` uses the separate `crawlerEnv.py` and is unchanged. Older standalone scripts using the old tracker UI interface need adaptation to the new constructor and preview scheduling.

## Checks

```powershell
python -m unittest discover -s tests -p test_ui_refactor.py -v
```

Tests cover injected camera/MQTT clients, acknowledgement waiting, marker ID reward mapping, greedy evaluation, timeout, save/load/reset, callback binding and rendering through a hidden real Tk window. They do not move physical robots or connect to a broker. Camera tests generate marker images in memory; no external image files are required.

Backups of replaced files are in `backups/ui_refactor_*/`. Hardware validation remains necessary: preview, detected IDs, Run/Test, both robot acknowledgements and window shutdown.

## Connection status

The UI displays broker connectivity and per-robot observed MQTT replies, their
age and last payload. Waiting and timeout are tracked independently for each
robot. Replies older than 30 seconds are marked stale, rather than declaring
the robot offline. Retained messages do not confirm live presence or complete
a new command. Without firmware heartbeat or last-will presence messages,
robots that have not published a reply remain unknown, even if powered on.
The status panel never sends movement commands to probe connectivity.
