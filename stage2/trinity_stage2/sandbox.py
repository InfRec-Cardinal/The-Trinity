from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile


def run_python_check(code: str, work_dir: Path, timeout: int = 120) -> dict:
    work = Path(work_dir).resolve(strict=True)
    if work == Path('/') or not work.is_dir():
        raise ValueError('A dedicated evidence directory is required')
    bwrap = shutil.which('bwrap')
    python = Path('/usr/bin/python3')
    if not bwrap or not python.is_file():
        raise RuntimeError('Rule checks require Linux bubblewrap and /usr/bin/python3; no unisolated fallback is permitted')
    args = [bwrap, '--die-with-parent', '--new-session', '--unshare-all', '--cap-drop', 'ALL', '--clearenv',
            '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib',
            '--symlink', 'usr/lib64', '/lib64', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
            '--ro-bind', str(work), '/work', '--chdir', '/work', '--setenv', 'WORK_DIR', '/work',
            '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/bin', '--', str(python), '-I', '-c',
            'import resource,sys\n'
            'resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))\n'
            'resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))\n'
            'resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))\n'
            'resource.setrlimit(resource.RLIMIT_NPROC,(16,16))\n'
            f'resource.setrlimit(resource.RLIMIT_CPU,({timeout},{timeout}))\n'
            'exec(compile(sys.stdin.read(),"<rule-check>","exec"))']
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True, env={'PATH': '/usr/bin:/bin'})
        try:
            proc.communicate(code.encode('utf-8'), timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise RuntimeError('Rule check exceeded its time limit') from None
        stdout.seek(0); stderr.seek(0)
        out = stdout.read().decode('utf-8', errors='replace')[-20000:]
        err = stderr.read().decode('utf-8', errors='replace')[-4000:]
        if proc.returncode != 0 and 'bwrap:' in err:
            raise RuntimeError('Rule check sandbox could not start: ' + err)
        return {'stdout': out, 'stderr': err, 'returncode': proc.returncode}
