import gzip
import json
import shutil
from gzip import GzipFile
from io import TextIOWrapper
from os import getpid
from pathlib import Path
from sys import stderr
from typing import Iterable, Union, Sequence


class TmpFile:
    """Gives a temp filename. Will rename the temp file to the correct name when no exception occurs."""

    def __init__(self, filename: Union[Path, str]) -> None:
        self.filename = Path(filename)
        self.temp_filename = self.filename.with_suffix(
            f'{self.filename.suffix}{getpid()}.tmp')

    def __enter__(self) -> Path:
        return self.temp_filename

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.temp_filename.replace(self.filename)
        else:
            self.temp_filename.unlink(missing_ok=True)
        return False  # Do not suppress exceptions


def split_chunks(seq: Sequence, size):
    return (seq[i:i + size] for i in range(0, len(seq), size))


def read_json_gz_file(file):
    with gzip.open(file, mode='rt', encoding='utf-8') as f:
        return json.load(f)


def write_json_gz_file(file: Path, contents):
    with TmpFile(file) as tmp, tmp.open(mode='wb') as fh,\
            GzipFile(file.name.removesuffix('.gz'), fileobj=fh, mode='wb') as fg,\
            TextIOWrapper(fg, encoding='utf-8') as ft:
        json.dump(contents, ft)


def one_way_sync(src: Path, dest: Path, files: Iterable[Path]):
    files = set(files)
    in_dest = set(f.relative_to(dest) for f in dest.iterdir() if f.is_file())
    for f in in_dest - files:
        (dest / f).unlink()
    for f in files - in_dest:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        if (src / f).is_file():
            shutil.copy(src / f, dest / f)
        else:
            print('File not found:', src / f, file=stderr)
    for f in files.union(in_dest):
        if (src / f).stat().st_mtime > (dest / f).stat().st_mtime:
            (dest / f).unlink()
            shutil.copy(src / f, dest / f)
