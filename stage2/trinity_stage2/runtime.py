from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def verification_runtime():
    source = Path(__file__).resolve().parents[2] / 'harness/src/protocol-state.mjs'
    if source.is_file():
        yield source
        return
    resource = files(__package__).joinpath('_runtime')
    if not resource.is_dir():
        raise RuntimeError('Stage 2 installation is missing its verification runtime; reinstall the complete wheel')
    with TemporaryDirectory(prefix='trinity-verifier-') as temporary:
        def copy(item, target):
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                for child in item.iterdir():
                    copy(child, target / child.name)
            else:
                target.write_bytes(item.read_bytes())
        copy(resource, Path(temporary))
        yield Path(temporary) / 'harness/src/protocol-state.mjs'
