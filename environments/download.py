import argparse
import concurrent.futures
import hashlib
import hmac
import secrets
import stat
import io
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import threading
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parent
PROGRESS = False
PROGRESS_LOCK = threading.Lock()
CURRENT_ASSET = None
STAGING_DIRS = set()
STAGING_LOCK = threading.Lock()
STAGING_JOURNAL = None
STAGING_TAG = None
CANCELLED = False
STAGING_SECRET = None
STAGING_ALLOWED = set()

def staging_secret(directory):
    file = directory / '.staging-key'
    lock = None
    for attempt in range(100):
        try:
            lock = acquire_lock(directory / '.staging-key.lock')
            break
        except RuntimeError:
            if attempt == 99:
                raise
            time.sleep(0.01)
    name = None
    try:
        for pending in directory.glob('.staging-key-*.tmp'):
            if re.fullmatch(r'\.staging-key-[a-z0-9_]{8}\.tmp', pending.name) and not pending.is_dir():
                pending.unlink(missing_ok=True)
        try:
            fd = os.open(file, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        except FileNotFoundError:
            key = b''
        else:
            with os.fdopen(fd, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError('Invalid staging key')
                key = stream.read(33)
            if len(key) == 32:
                return key
            if key or any(directory.glob('*.staging.json*')):
                raise ValueError('Invalid staging key; preserve recovery journals before replacing it')
        key = secrets.token_bytes(32)
        fd, name = tempfile.mkstemp(prefix='.staging-key-', suffix='.tmp', dir=directory)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(key)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, file)
        return key
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)
        release_lock(lock)


def staging_payload(paths):
    return json.dumps({'tag': STAGING_TAG, 'paths': sorted(paths)}, sort_keys=True, separators=(',', ':')).encode()


def validate_staging_path(directory):
    path = Path(directory)
    if not path.is_absolute() or path.name != STAGING_TAG or path.is_symlink() or path.resolve() != path:
        raise ValueError('Invalid staging directory')
    return path


def recover_staging():
    if not STAGING_JOURNAL.exists() and not STAGING_JOURNAL.is_symlink():
        return
    try:
        fd = os.open(STAGING_JOURNAL, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'r', encoding='utf-8') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Invalid staging journal')
            value = json.load(stream)
        if isinstance(value, list):
            paths = value
            if any(not isinstance(p, str) or str(validate_staging_path(p).parent) not in STAGING_ALLOWED for p in paths):
                raise ValueError('Untrusted legacy staging directory')
        elif isinstance(value, dict) and value.get('version') == 2 and isinstance(value.get('paths'), list):
            paths = value['paths']
            if any(not isinstance(p, str) for p in paths):
                raise ValueError('Invalid staging journal paths')
            signature = hmac.new(STAGING_SECRET, staging_payload(paths), hashlib.sha256).hexdigest()
            if not isinstance(value.get('signature'), str) or not hmac.compare_digest(signature, value['signature']):
                raise ValueError('Invalid staging journal signature')
        else:
            raise ValueError('Invalid staging journal')
        for directory in paths:
            validate_staging_path(directory)
        STAGING_DIRS.update(paths)
    except Exception:
        if STAGING_JOURNAL.exists() or STAGING_JOURNAL.is_symlink():
            os.replace(STAGING_JOURNAL, STAGING_JOURNAL.with_name(STAGING_JOURNAL.name + '.invalid-' + secrets.token_hex(6)))
        raise


def save_staging():
    paths = sorted(STAGING_DIRS)
    value = {'version': 2, 'paths': paths, 'signature': hmac.new(STAGING_SECRET, staging_payload(paths), hashlib.sha256).hexdigest()}
    fd, name = tempfile.mkstemp(prefix=STAGING_JOURNAL.name + '.', suffix='.tmp', dir=STAGING_JOURNAL.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, STAGING_JOURNAL)
    finally:
        Path(name).unlink(missing_ok=True)


def cleanup_staging(retain_journal=False):
    paths = [validate_staging_path(directory) for directory in STAGING_DIRS]
    for path in sorted(paths, key=lambda p: len(p.parts), reverse=True):
        if path.exists():
            shutil.rmtree(path)
    if retain_journal:
        return
    STAGING_DIRS.clear()
    if STAGING_JOURNAL is not None:
        STAGING_JOURNAL.unlink(missing_ok=True)
        STAGING_JOURNAL.with_suffix('.tmp').unlink(missing_ok=True)
        for pending in STAGING_JOURNAL.parent.glob(STAGING_JOURNAL.name + '.*.tmp'):
            if pending.is_file() and not pending.is_symlink():
                pending.unlink()


def staging_directory(parent):
    if CANCELLED:
        raise InterruptedError('Download interrupted')
    if STAGING_JOURNAL is None:
        return parent
    parent = parent.resolve()
    if str(parent) not in STAGING_ALLOWED and not any(Path(p) == parent or Path(p) in parent.parents for p in STAGING_DIRS):
        raise ValueError('Unmanaged staging parent')
    directory = validate_staging_path(str(parent / STAGING_TAG))
    with STAGING_LOCK:
        STAGING_DIRS.add(str(directory))
        save_staging()
        directory.mkdir(parents=True, exist_ok=True)
        if CANCELLED:
            shutil.rmtree(directory, ignore_errors=True)
            raise InterruptedError('Download interrupted')
    return directory


def staging_parents(asset, root, cache):
    parents = {str(cache)}
    parents.update(str(inside(root, f['path']).parent) for f in asset.get('files', []))
    if asset.get('kind') == 'video':
        parents.add(str(inside(root, asset['path']).parent))
    if asset.get('kind') == 'frames':
        manifest = read(inside(root, asset['manifest']))
        target = inside(root, asset['target'])
        parents.update(str(inside(target, i)) for i in manifest['videos'])
    return parents


def cleanup_legacy_partials(asset, root, cache, key):
    targets = [inside(root, f['path']) for f in asset.get('files', [])]
    if asset.get('kind') in ('zip', 'glove'):
        targets.append(cache / ('glove.6B.zip' if asset['kind'] == 'glove' else key + '.zip'))
    for target in targets:
        if target.parent.is_dir():
            pattern = re.compile(re.escape(target.name) + r'\.[a-z0-9_]{8}\.partial')
            for pending in target.parent.iterdir():
                if pattern.fullmatch(pending.name) and pending.is_file() and not pending.is_symlink():
                    pending.unlink()

def interrupted(signum, frame):
    global CANCELLED
    CANCELLED = True
    try:
        cleanup_staging(retain_journal=True)
    finally:
        os._exit(128 + signum)


def progress(**values):
    if PROGRESS:
        with PROGRESS_LOCK:
            print(json.dumps({"type": "progress", "asset": CURRENT_ASSET, **values}), flush=True)

def copy_progress(src, dst, name, total):
    count = 0
    updated = 0
    while True:
        block = src.read(4 << 20)
        if not block:
            break
        dst.write(block)
        count += len(block)
        now = time.monotonic()
        if now - updated >= 1:
            progress(file=name, bytes=count, total=total)
            updated = now
    progress(file=name, bytes=count, total=total)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def inside(root, relative):
    target = (root / relative).resolve()
    if target == root.resolve() or root.resolve() not in target.parents:
        raise ValueError('Invalid destination: ' + relative)
    return target


def valid(path, spec):
    return path.is_file() and ('bytes' not in spec or path.stat().st_size == spec['bytes']) and ('sha256' not in spec or sha(path) == spec['sha256'])


def fetch(spec, target):
    if valid(target, spec):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        fd, name = tempfile.mkstemp(prefix=target.name + '.', suffix='.partial', dir=staging_directory(target.parent))
        pending = Path(name)
        try:
            request = urllib.request.Request(spec['url'], headers={'User-Agent': 'Trinity-Assets/1'})
            with os.fdopen(fd, 'wb') as output, urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 200:
                    raise RuntimeError('Unexpected HTTP status: ' + str(response.status))
                copy_progress(response, output, target.name, spec.get('bytes'))
            if not valid(pending, spec):
                raise RuntimeError('Size or SHA256 mismatch: ' + spec['url'])
            os.replace(pending, target)
            return target
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
        finally:
            pending.unlink(missing_ok=True)



def atomic_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=staging_directory(target.parent), suffix='.partial')
    pending = Path(name)
    try:
        with os.fdopen(fd, 'wb') as out, source.open('rb') as src:
            shutil.copyfileobj(src, out, 4 << 20)
        os.replace(pending, target)
    finally:
        pending.unlink(missing_ok=True)


def files_ok(root, files):
    return all(valid(inside(root, f['path']), f) for f in files)


def frame_hashes(directory):
    return {f'frame-{i:02d}.jpg': sha(directory / f'frame-{i:02d}.jpg') for i in range(1, 65)}


class RemoteZip(io.RawIOBase):
    def __init__(self, spec):
        super().__init__()
        self.spec = spec
        self.position = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset + (self.position if whence == 1 else self.spec['bytes'] if whence == 2 else 0)
        if position < 0 or whence not in (0, 1, 2):
            raise ValueError('Invalid seek')
        self.position = position
        return position

    def read(self, size=-1):
        end = self.spec['bytes'] if size < 0 else min(self.spec['bytes'], self.position + size)
        if end <= self.position:
            return b''
        start = self.position
        for attempt in range(3):
            try:
                url = self.spec['url'] + f'?download=true&trinity_range={start}-{end - 1}'
                req = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end - 1}', 'User-Agent': 'Trinity-Assets/1'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end - 1}/{self.spec["bytes"]}':
                        raise RuntimeError('Server did not honor byte range')
                    data = response.read(end - start + 1)
                if len(data) != end - start:
                    raise RuntimeError('Incomplete range response')
                self.position = end
                return data
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)


def frames_ok(root, asset, video_id, meta, manifest):
    directory = inside(root, asset['target']) / video_id
    try:
        actual = frame_hashes(directory)
        if actual == manifest['frames'][video_id]:
            return True
        frozen = read(inside(root, asset['packageFrameManifest']))
        if actual == frozen[video_id]:
            return True
        receipt = read(directory / '.download-receipt.json')
        return receipt['videoSha256'] == meta['sha256'] and receipt['frameIndices'] == meta['frame_indices'] and receipt['files'] == actual
    except (OSError, KeyError, ValueError, TypeError):
        return False


def video_file(asset, meta, target):
    if valid(target, {'sha256': meta['sha256'], 'bytes': meta['size_bytes']}):
        return target
    archive_spec = next(a for a in asset['archives'] if a['path'] == 'videos/' + meta['zip'])
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        fd, name = tempfile.mkstemp(suffix='.mp4.partial', dir=staging_directory(target.parent))
        pending = Path(name)
        try:
            with os.fdopen(fd, 'wb') as out, RemoteZip(archive_spec) as remote, zipfile.ZipFile(remote) as archive, archive.open(meta['member']) as src:
                copy_progress(src, out, target.name, meta['size_bytes'])
            if not valid(pending, {'sha256': meta['sha256'], 'bytes': meta['size_bytes']}):
                raise RuntimeError('Video SHA256 mismatch: ' + meta['member'])
            os.replace(pending, target)
            return target
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
        finally:
            pending.unlink(missing_ok=True)


def create_frames(asset, video_id, meta, directory, cache):
    import decord
    from PIL import Image
    with tempfile.TemporaryDirectory(prefix='video-', dir=staging_directory(cache)) as temp:
        video = video_file(asset, meta, Path(temp) / (video_id + '.mp4'))
        reader = decord.VideoReader(str(video), num_threads=1)
        indices = [int(i * (len(reader) / 65)) for i in range(1, 65)]
        if len(reader) != meta['decord_n_frames'] or indices != meta['frame_indices']:
            raise RuntimeError('Video frame count or sample indices mismatch: ' + video_id)
        staging = Path(temp) / 'frames'
        staging.mkdir()
        for number, index in enumerate(indices, 1):
            im = Image.fromarray(reader[index].asnumpy())
            w, h = im.size
            scale = min(1, 768 / max(w, h))
            if scale < 1:
                im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
            im.save(staging / f'frame-{number:02d}.jpg', format='JPEG', quality=90)
            progress(file=video_id, frames=number, totalFrames=64)
        receipt = {'videoSha256': meta['sha256'], 'frameIndices': indices, 'decoder': 'decord-' + decord.__version__, 'files': frame_hashes(staging)}
        (staging / '.download-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        (staging / '.video.sha256').write_text(meta['sha256'] + '\n', encoding='utf-8')
        directory.mkdir(parents=True, exist_ok=True)
        for f in staging.iterdir():
            atomic_copy(f, directory / f.name)
        del reader


def selected_files(asset, only):
    if not only:
        return asset.get('files', [])
    selected = [f for f in asset.get('files', []) if f['path'] in only or Path(f['path']).name in only]
    matched = {v for v in only if any(v in (f['path'], Path(f['path']).name) for f in selected)}
    if matched != set(only):
        raise ValueError('Unknown file selection: ' + ','.join(set(only) - matched))
    return selected


def perform(key, asset, root, cache, args):
    kind = asset['kind']
    if kind == 'manual':
        print(json.dumps({'asset': key, 'status': 'manual-install', 'url': asset['url'], 'externalRootVariable': asset['externalRootVariable']}))
        return False
    if kind == 'frames':
        manifest = read(inside(root, asset['manifest']))
        ids = args.video or sorted(manifest['videos'])
        if any(i not in manifest['videos'] for i in ids):
            raise ValueError('Unknown video ID')
        missing = [i for i in ids if not frames_ok(root, asset, i, manifest['videos'][i], manifest)]
        if not args.check:
            for i in missing:
                create_frames(asset, i, manifest['videos'][i], inside(root, asset['target']) / i, cache)
                if not frames_ok(root, asset, i, manifest['videos'][i], manifest):
                    raise RuntimeError('Frame validation failed: ' + i)
                print(json.dumps({'asset': key, 'video': i, 'status': 'ready'}), flush=True)
            missing = []
        return not missing
    if kind == 'video':
        spec = {'sha256': asset['video']['sha256'], 'bytes': asset['video']['size_bytes']}
        path = inside(root, asset['path'])
        if not args.check:
            video_file(asset, asset['video'], path)
        return valid(path, spec)
    files = selected_files(asset, args.file)
    if files_ok(root, files):
        return True
    if args.check:
        return False
    if kind == 'files':
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(lambda f: fetch(f, inside(root, f['path'])), files))
    elif kind == 'zip':
        archive = fetch(asset['archive'], cache / (key + '.zip'))
        with zipfile.ZipFile(archive) as z:
            for f in files:
                target = inside(root, f['path'])
                if valid(target, f):
                    continue
                if 'url' in f:
                    fetch(f, target)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(dir=staging_directory(target.parent), suffix='.partial')
                pending = Path(name)
                try:
                    with os.fdopen(fd, 'wb') as out, z.open(f['member']) as src:
                        shutil.copyfileobj(src, out, 4 << 20)
                    if not valid(pending, f):
                        raise RuntimeError('Archive member SHA256 mismatch: ' + f['path'])
                    os.replace(pending, target)
                finally:
                    pending.unlink(missing_ok=True)
    elif kind == 'glove':
        archive = fetch(asset['archive'], cache / 'glove.6B.zip')
        with tempfile.TemporaryDirectory(prefix='glove-', dir=staging_directory(cache)) as temp:
            subprocess.run([sys.executable, str(inside(root, 'train/tools/convert_glove.py')), str(archive), temp], check=True)
            for f in files:
                src = Path(temp) / Path(f['path']).name
                if not valid(src, f):
                    raise RuntimeError('Converted GloVe SHA256 mismatch: ' + f['path'])
                atomic_copy(src, inside(root, f['path']))
    else:
        raise ValueError('Unsupported asset kind: ' + kind)
    return files_ok(root, files)



def acquire_lock(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0), 0o600)
    handle = os.fdopen(fd, 'r+b')
    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
        handle.close()
        raise ValueError('Download lock must be a regular file')
    try:
        if os.name == 'nt':
            import msvcrt
            if handle.seek(0, 2) == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError as error:
        handle.close()
        raise RuntimeError('This resource is already being downloaded') from error

def release_lock(handle):
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()

def main():
    global PROGRESS, CURRENT_ASSET, STAGING_JOURNAL, STAGING_TAG, STAGING_SECRET, STAGING_ALLOWED
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true')
    group.add_argument('--task', action='append')
    group.add_argument('--asset', action='append')
    group.add_argument('--list', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--progress', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--video', action='append')
    ap.add_argument('--file', action='append')
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--cache', type=Path)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    PROGRESS = args.progress
    catalog = read(ROOT / 'downloads.json')
    if args.list:
        print(json.dumps(catalog, ensure_ascii=False, indent=2))
        return 0
    if args.workers < 1 or args.workers > 16:
        ap.error('--workers must be between 1 and 16')
    if args.all:
        keys = [k for k in catalog['assets'] if k not in catalog['excludedByDefault']]
    elif args.task:
        unknown = set(args.task) - catalog['tasks'].keys()
        if unknown:
            ap.error('Unknown tasks: ' + ','.join(sorted(unknown)))
        keys = sorted({k for t in args.task for k in catalog['tasks'][t]})
    else:
        keys = list(dict.fromkeys(args.asset))
    if set(keys) - catalog['assets'].keys():
        ap.error('Unknown asset')
    if args.video and keys != ['videomme']:
        ap.error('--video requires --asset videomme')
    if args.file and (len(keys) != 1 or catalog['assets'][keys[0]]['kind'] != 'files'):
        ap.error('--file requires one files asset')
    if args.dry_run:
        print(json.dumps({k: catalog['assets'][k] for k in keys}, ensure_ascii=False, indent=2))
        return 0
    root = args.root.resolve()
    cache = (args.cache or root / '.downloads').resolve()
    if not args.check and any(catalog['assets'][k]['kind'] != 'manual' for k in keys):
        cache.mkdir(parents=True, exist_ok=True)
        (root / '.downloads').mkdir(parents=True, exist_ok=True)
        if (root / '.downloads').resolve() != root / '.downloads':
            raise ValueError('Managed download directory must not be a symlink')
        STAGING_SECRET = staging_secret(root / '.downloads')
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, interrupted)
    failures = []
    for key in keys:
        CURRENT_ASSET = key
        if PROGRESS:
            print(json.dumps({'type': 'asset-start', 'asset': key}), flush=True)
        lock = None
        cache_lock = None
        try:
            if not args.check and catalog['assets'][key]['kind'] != 'manual':
                lock = acquire_lock(root / '.downloads' / (key + '.download.lock'))
                if cache != root / '.downloads':
                    cache_lock = acquire_lock(cache / (key + '.download.lock'))
                STAGING_TAG = '.trinity-staging-' + hashlib.sha256((str(root) + ':' + key).encode()).hexdigest()[:24]
                STAGING_JOURNAL = root / '.downloads' / (key + '.staging.json')
                STAGING_ALLOWED = staging_parents(catalog['assets'][key], root, cache)
                recover_staging()
                cleanup_staging()
                cleanup_legacy_partials(catalog['assets'][key], root, cache, key)
            ok = perform(key, catalog['assets'][key], root, cache, args)
            print(json.dumps({'asset': key, 'status': 'ready' if ok else 'missing-or-invalid'}), flush=True)
            if not ok:
                failures.append(key)
        except Exception as error:
            failures.append(key)
            print(json.dumps({'asset': key, 'status': 'error', 'error': str(error)}), flush=True)
        finally:
            if lock is not None:
                try:
                    if STAGING_JOURNAL is not None:
                        cleanup_staging()
                finally:
                    STAGING_JOURNAL = None
                    STAGING_TAG = None
                    STAGING_ALLOWED = set()
                    STAGING_DIRS.clear()
                    if cache_lock is not None:
                        release_lock(cache_lock)
                    release_lock(lock)
    if not keys:
        print(json.dumps({'tasks': args.task, 'status': 'no-external-assets'}))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
