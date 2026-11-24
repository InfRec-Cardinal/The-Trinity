# BuildArena 1.0

`BuildArena-1.0/` is the single source tree used by the official task scripts and Trinity's Harness. `configurations.json` defines the nine official tasks; `linux/` is an optional adapter, not another copy of the environment. The Web catalog and offline Harness contract validation do not need Besiege, a display server, or mods.

## Optional native simulation

Install a licensed copy of Besiege, the required DLC, and the Lua Scripting mod separately. Neither the game nor any Workshop files are included or downloaded by Trinity. The official macOS GUI workflow uses `BuildArena-1.0/run_sim_h0.py`, Accessibility and Screen Recording permissions, and `BESIEGE_SAVED_MACHINES` set to the game's save directory. Calibrate the GUI for your display.

The Linux x86-64 Harness supports **transport_soft**. Install the task Python dependencies (Python 3.12, see `../../requirements/buildarena-1.0.txt`), system `Xvfb`, VirtualGL (`vglrun` with working EGL), and `xclip` on PATH. The external mod installation must also have a compatible **observer bridge**, not just the stock Workshop mod: the launcher expects `Main.dll` and `Observer.dll` declared in its `Mod.xml`. While running, the bridge must write fresh `Observer/state.json` (`wall`, `machine`, `scene`, `simulating`, `time_scale`) and `Observer/lua-snapshot.json` (`state` and Lua log `text`). The bridge is not supplied here. Without it, use the contract check rather than native scoring.

From the release root, set these variables in **both the launcher and Harness shells**; substitute your own absolute paths. Select the Python interpreter containing the task dependencies for `BUILDARENA_PYTHON`.

```sh
export BESIEGE_GAME_ROOT='/path/to/Besiege'
export BESIEGE_MOD_ROOT='/path/to/LuaScripting'
export BUILDARENA_PYTHON='/path/to/task-python'
launcher=environments/unseen/tasks/07-buildarena/linux/launch.py
python3 "$launcher" --check
python3 "$launcher" --out ../besiege-session
```

`--check` checks prerequisite files and system tools only. It does not run Steam, open the game, or verify live observer data. The launcher uses a dedicated display `:97` and refuses to reuse an occupied one. In the running game load **BARREN EXPANSE** before starting the Harness in the second shell. Configure the model credentials there for a real episode. The default save directory is `$BESIEGE_GAME_ROOT/Besiege_Data/SavedMachines`; export `BESIEGE_SAVED_MACHINES` in both shells if overriding it. For a contract-only run (no external game or model calls):

```sh
node iter4-harness/run.mjs --task buildarena_1_0 --cases transport_soft --episodes 1 --validate-only --out ../buildarena-contract
```
