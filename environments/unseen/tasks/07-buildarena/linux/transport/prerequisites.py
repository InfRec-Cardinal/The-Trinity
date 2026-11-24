"""External prerequisites for the optional Linux game adapter (no downloads)."""
import os
import platform
import shutil
from pathlib import Path
from xml.etree import ElementTree


def installation(game_root, mod_root):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise ValueError('The native adapter requires Linux x86-64')
    if not game_root or not mod_root:
        raise ValueError('Set BESIEGE_GAME_ROOT and BESIEGE_MOD_ROOT to your own installations')
    game = Path(game_root).expanduser().resolve() / 'Besiege.x86_64'
    if not game.is_file() or not os.access(game, os.X_OK) or not (game.parent / 'Besiege_Data').is_dir():
        raise ValueError(f'Missing executable game or Besiege_Data: {game.parent}')
    mod = Path(mod_root).expanduser().resolve()
    try:
        assemblies = {item.get('path') for item in ElementTree.parse(mod / 'Mod.xml').findall('./Assemblies/Assembly')}
    except (OSError, ElementTree.ParseError) as error:
        raise ValueError(f'Missing or invalid external mod manifest: {mod / "Mod.xml"}') from error
    for name in ('Main.dll', 'Observer.dll'):
        if name not in assemblies or not (mod / name).is_file():
            raise ValueError(f'External Lua mod and compatible observer required: {name} must exist and be declared in Mod.xml')
    tools = {tool: shutil.which(tool) for tool in ('Xvfb','vglrun','xclip')}
    missing = [name for name, path in tools.items() if not path]
    if missing:
        raise ValueError('Install the system tools and add to PATH: ' + ', '.join(missing))
    return game, mod, tools['Xvfb'], tools['vglrun']
