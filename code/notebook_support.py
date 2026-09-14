"""Load notebook modules and prepare their project-relative inputs."""
from __future__ import annotations

import importlib.abc
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


def notebook_source(path: Path, fullname: str) -> str:
    document = json.loads(path.read_text(encoding='utf-8'))
    return '\n\n'.join(
        ''.join(cell['source']).split('\n', 1)[1] for cell in document['cells']
        if cell['cell_type'] == 'code'
        and cell.get('metadata', {}).get('plot_module') == fullname
    )


class NotebookLoader(importlib.abc.SourceLoader):
    def __init__(self, path: Path, virtual_path: Path):
        self.path = path
        self.virtual_path = virtual_path

    def get_filename(self, fullname: str) -> str:
        return str(self.virtual_path)

    def get_data(self, path: str) -> bytes:
        return Path(path).read_bytes()

    def get_code(self, fullname: str):
        return compile(notebook_source(self.path, fullname), str(self.path), 'exec')


class NotebookFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        for directory in sys.path:
            candidate = Path(directory or os.curdir) / 'figures.ipynb'
            if candidate.is_file():
                document = json.loads(candidate.read_text(encoding='utf-8'))
                virtual = document.get('metadata', {}).get('plot_modules', {}).get(fullname)
                if virtual is not None:
                    filename = inside(candidate.parent, virtual)
                    loader = NotebookLoader(candidate, filename)
                    return importlib.util.spec_from_file_location(fullname, filename, loader=loader)
        return None


def install() -> None:
    if not any(isinstance(finder, NotebookFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, NotebookFinder())


def inside(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f'Invalid relative path: {relative}')
    return path


def prepare_runtime(project: Path) -> Path:
    workspace = project / 'environment/.runtime'
    workspace.mkdir(parents=True, exist_ok=True)
    entries = json.loads((project / 'environment/layout.json').read_text(encoding='utf-8'))
    for entry in entries:
        source = inside(project, entry['source'])
        target = inside(workspace, entry['runtime'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return workspace


def execute_module_cell(line: str, source: str) -> None:
    fullname = line.strip()
    module = sys.modules.get(fullname)
    if module is None:
        parent_name, _, attribute = fullname.rpartition('.')
        parent = importlib.import_module(parent_name) if parent_name else None
        spec = importlib.util.find_spec(fullname)
        if spec is None or not isinstance(spec.loader, NotebookLoader):
            raise ImportError(f'Notebook module not found: {fullname}')
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        if parent is not None:
            setattr(parent, attribute, module)
    exec(compile(source, module.__file__, 'exec'), module.__dict__)


def run_figure_module(fullname: str, workspace: Path, arguments=()) -> None:
    module = importlib.import_module(fullname)
    figures = workspace / 'outputs/figures'
    figures.mkdir(parents=True, exist_ok=True)
    previous = {str(f): f.stat().st_mtime_ns for f in figures.glob('*.png')}
    previous_argv, previous_cwd = sys.argv, Path.cwd()
    try:
        os.chdir(workspace)
        sys.argv = [module.__file__, *arguments]
        status = module.main()
        if status not in (None, 0):
            raise RuntimeError(f'{fullname} returned {status}')
        display_figures(workspace, previous)
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def display_figures(workspace: Path, previous: dict) -> None:
    if 'ipykernel' not in sys.modules:
        return
    from IPython.display import Image, display
    for file in sorted((workspace / 'outputs/figures').glob('*.png')):
        if previous.get(str(file)) != file.stat().st_mtime_ns:
            display(Image(filename=str(file)))

