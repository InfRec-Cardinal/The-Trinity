import fs from 'node:fs';
import {spawn, spawnSync} from 'node:child_process';

export function openFifoProcess({python, args, cwd, env, req, resp, timeoutMs = 60000}) {
  if (process.platform === 'win32') throw new Error('FIFO environments require a POSIX system');
  const timeout = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 60000;
  let child, reader, writer, closed = false, launchError = null, buffer = Buffer.alloc(0);
  const sleep = new Int32Array(new SharedArrayBuffer(4));
  const close = () => {
    if (closed) return;
    closed = true;
    for (const fd of [reader, writer]) if (fd !== undefined) { try { fs.closeSync(fd); } catch {} }
    if (child?.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
    for (const name of [req, resp]) { try { fs.unlinkSync(name); } catch {} }
  };
  const check = deadline => {
    if (closed) throw new Error('FIFO session is closed');
    if (launchError) throw launchError;
    if (!child?.pid || child.exitCode !== null || child.signalCode !== null) throw new Error('FIFO worker has ended');
    try {
      process.kill(child.pid, 0);
      if (process.platform === 'linux') {
        const stat = fs.readFileSync('/proc/' + child.pid + '/stat', 'utf8');
        if (/^[ZX]/.test(stat.slice(stat.lastIndexOf(')') + 2))) throw new Error('FIFO worker has ended');
      }
    } catch (error) { throw new Error('FIFO worker unavailable: ' + error.message); }
    if (Date.now() >= deadline) throw new Error('FIFO worker timed out');
  };
  const wait = deadline => { check(deadline); Atomics.wait(sleep, 0, 0, Math.min(10, Math.max(1, deadline - Date.now()))); };
  const read = deadline => {
    const chunk = Buffer.alloc(65536);
    for (;;) {
      if (closed) throw new Error('FIFO session is closed');
      if (Date.now() >= deadline) throw new Error('FIFO worker timed out');
      const at = buffer.indexOf(10);
      if (at >= 0) { const line = buffer.subarray(0, at).toString('utf8'); buffer = buffer.subarray(at + 1); return line; }
      let count = 0;
      try { count = fs.readSync(reader, chunk, 0, chunk.length, null); }
      catch (error) { if (!['EAGAIN', 'EINTR'].includes(error.code)) throw error; }
      if (count) {
        buffer = Buffer.concat([buffer, chunk.subarray(0, count)]);
        if (buffer.length > 64 * 1024 * 1024) throw new Error('FIFO response limit exceeded');
      } else wait(deadline);
    }
  };
  const write = (data, deadline) => {
    const bytes = Buffer.from(JSON.stringify(data) + '\n');
    let offset = 0;
    while (offset < bytes.length) {
      check(deadline);
      try { offset += fs.writeSync(writer, bytes, offset, bytes.length - offset); }
      catch (error) { if (!['EAGAIN', 'EINTR'].includes(error.code)) throw error; wait(deadline); }
    }
  };
  const guard = operation => { try { return operation(); } catch (error) { close(); throw Object.assign(error, {code: 'environment_error'}); } };
  return guard(() => {
    for (const name of [req, resp]) {
      try { fs.unlinkSync(name); } catch (error) { if (error.code !== 'ENOENT') throw error; }
      const result = spawnSync('mkfifo', [name], {timeout: 5000});
      if (result.status !== 0) throw new Error('Could not create FIFO');
    }
    child = spawn(python, args, {cwd, env, stdio: ['ignore', 'ignore', 'ignore']});
    child.on('error', error => { launchError = error; }); child.unref();
    reader = fs.openSync(resp, fs.constants.O_RDONLY | fs.constants.O_NONBLOCK);
    const deadline = Date.now() + timeout;
    for (;;) {
      check(deadline);
      try { writer = fs.openSync(req, fs.constants.O_WRONLY | fs.constants.O_NONBLOCK); break; }
      catch (error) { if (error.code !== 'ENXIO') throw error; wait(deadline); }
    }
    return {
      readLine: () => guard(() => read(Date.now() + timeout)),
      send: data => guard(() => { const end = Date.now() + timeout; write(data, end); return read(end); }),
      close
    };
  });
}
