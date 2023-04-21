import os
import mmap
import struct
import chess
import chess.polyglot
from typing import Union

from utils import polyglot_move, original_move


ENTRY = struct.Struct(">QHHI")


class PolyglotBook:
    def __init__(self, file: str = None):
        self.book = {}
        self.unpacked = {}
        self.mmap = None
        if file: self.read(file)

    def __len__(self) -> int:
        return self.mmap.size() // ENTRY.size

    def __getitem__(self, index: int):
        if index < 0: index = len(self) + index
        try: key, raw_move, weight, learn = ENTRY.unpack_from(self.mmap, index * ENTRY.size)
        except struct.error as e:
            raise IndexError() from e
        # There is no need to get the original move as raw_move will just do fine
        return key, raw_move, weight, learn

    def add_entry(self, board: chess.Board, move: chess.Move, weight: int, learn: int = 0):
        key = chess.polyglot.zobrist_hash(board)
        convmove = polyglot_move(board, move)
        entry = struct.pack('>QHHI', key, convmove, weight, learn)
        unpacked_entry = [original_move(convmove), weight, learn]
        if key in self.book and entry not in self.book[key]: self.book[key].append(entry)
        else: self.book[key] = [entry];
        if key in self.unpacked and unpacked_entry not in self.unpacked[key]: self.unpacked[key].append(unpacked_entry)
        else: self.unpacked[key] = [unpacked_entry]

    def get_entries(self, key: int):
        return None if key not in self.book else self.book[key]

    def write(self, file: str):
        # Should be noted that this function is destructive and closes the memory mapped file
        try: self.mmap.close()
        except:
            try: del self.mmap
            except Exception: raise IOError('mmap failed to close the file.')
        try: os.remove(file)
        except FileNotFoundError: pass
        with open(file, "wb") as wrbook:
            for key in sorted(self.book):
                entries = self.book[key]
                for entry in entries: wrbook.write(entry)

    def read(self, file: str):
        fd = os.open(file, os.O_BINARY | os.O_RDWR)
        try: self.mmap: Union[mmap.mmap, _EmptyMmap] = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        except (ValueError, OSError): self.mmap = _EmptyMmap()
        finally: os.close(fd)
        if self.mmap.size() % ENTRY.size != 0: raise IOError()
        for entry in self:
            key = entry[0]
            binary_entry = struct.pack('>QHHI', key, entry[1], entry[2], entry[3])
            unpacked_entry = [original_move(entry[1]), entry[2], entry[3]]
            if key in self.book and binary_entry not in self.book[key]: self.book[key].append(binary_entry)
            else: self.book[key] = [binary_entry]
            if key in self.unpacked and unpacked_entry not in self.unpacked[key]: self.unpacked[key].append(unpacked_entry)
            else: self.unpacked[key] = [unpacked_entry]


