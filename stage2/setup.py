from pathlib import Path
import re
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

HERE = Path(__file__).resolve().parent


def bundle_runtime(destination):
    root = HERE.parent
    entry = root / 'harness/src/protocol-state.mjs'
    destination = Path(destination) / 'trinity_stage2/_runtime'
    if not entry.is_file():
        bundled = HERE / 'trinity_stage2/_runtime'
        if not bundled.is_dir():
            raise RuntimeError('Missing canonical Harness source for Stage 2 verification')
        shutil.copytree(bundled, destination, dirs_exist_ok=True)
        return
    seen = set()
    def copy(file):
        file = file.resolve()
        relative = file.relative_to(root.resolve())
        if file in seen:
            return
        seen.add(file)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
        for dependency in re.findall(r'''(?:from\s*|import\s*)['"](\.[^'"]+)['"]''', file.read_text()):
            copy(file.parent / dependency)
    copy(entry)


class Build(build_py):
    def run(self):
        super().run()
        bundle_runtime(self.build_lib)


class Source(sdist):
    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        bundle_runtime(base_dir)


setup(cmdclass={'build_py': Build, 'sdist': Source})
