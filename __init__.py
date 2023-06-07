import os
import mmap
import struct
import functools
from typing import Union

import chess
import chess.polyglot



from utils import polyglot_move, original_move


STRUCT      = ">QHHI"
ENTRY       = struct.Struct(STRUCT)
INF         = float("inf")


class _EmptyMmap(bytearray):
    def size(self) -> int:
        return 0

    def close(self) -> None:
        pass

class PolyglotBook:
    def __init__(self, file: str = None):
        # revise the structure of the book to be more efficient
        # (i.e. remove the unnecessary dicts)
        self.book = {}
        self.unpacked = {}
        self.packmap = {}
        self.mmap = None
        if file: self.read(file)
    
    def prune_by_weights(self, upperbound: float = INF, lowerbound: float = -INF):
        for hashed in self.unpacked.copy():
            for entry in self.unpacked[hashed][:]:
                if entry[1] > upperbound or entry[1] < lowerbound:
                    self.unpacked[hashed].remove(entry) 
                    if self.unpacked[hashed] == []: del self.unpacked[hashed]; break
        self.pack()
        
    def prune_by_position(self, position: chess.Board):
        del self.unpacked[chess.polyglot.zobrist_hash(position)]
        self.pack()
        
    def flush_book(self):
        self.book = {}
        
    def pack(self):
        self.flush_book()
        for hashed in self.unpacked:
            for entry in self.unpacked[hashed]:
                packed_entry = self.packmap[hash(str(entry))]
                if hashed in self.book: self.book[hashed].append(packed_entry)
                else: self.book[hashed] = [packed_entry]

    def add_entry(self, board: chess.Board, move: chess.Move, weight: int, learn: int = 0):
        key = chess.polyglot.zobrist_hash(board)
        convmove = polyglot_move(board, move)
        entry = struct.pack(STRUCT, key, convmove, weight, learn)
        unpacked_entry = [original_move(convmove), weight, learn]
        if key in self.book: self.book[key].append(entry)
        else: self.book[key] = [entry];
        if key in self.unpacked:
            if not unpacked_entry in self.unpacked[key]:
                 self.unpacked[key].append(unpacked_entry)
        else: self.unpacked[key] = [unpacked_entry]
        self.packmap[hash(str(unpacked_entry))] = entry

    def get_entries(self, key: int):
        return None if key not in self.book else self.book[key]
    
    def get_moves(self, board: chess.Board, include_weights: bool = False):
        key = chess.polyglot.zobrist_hash(board)
        if key not in self.unpacked: return None
        if include_weights:
            for move in self.unpacked[key]: yield tuple(move[:2])
        else:
            for move in self.unpacked[key]: yield move[0]
    

    def write(self, file: str):
        # Should be noted that this function is destructive and closes the memory mapped file
        try: self.mmap.close()
        except:
            try: del self.mmap
            except Exception: raise IOError('File could not be closed.')
        try: os.remove(file)
        except FileNotFoundError: pass
        with open(file, "wb") as wrbook:
            for key in sorted(self.book):
                entries = self.book[key]
                for entry in entries: wrbook.write(entry)

    def read(self, file: str):
        try: fd = os.open(file, os.O_RDWR | os.O_BINARY)
        except: fd = os.open(file, os.O_RDWR)
        try: self.mmap: Union[mmap.mmap, _EmptyMmap] = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        except (ValueError, OSError): self.mmap = _EmptyMmap()
        finally: os.close(fd)
        if self.mmap.size() % ENTRY.size != 0: raise IOError()
        for entry in self:
            key = entry[0]
            binary_entry = struct.pack(STRUCT, key, entry[1], entry[2], entry[3])
            unpacked_entry = [original_move(entry[1]), entry[2], entry[3]]
            if key in self.unpacked:
                if any(unpacked_entry[0] in i for i in self.unpacked[key]):
                    continue
                self.unpacked[key].append(unpacked_entry)
            else: self.unpacked[key] = [unpacked_entry]
            if key in self.book: self.book[key].append(binary_entry)
            else: self.book[key] = [binary_entry]
            self.packmap[hash(str(unpacked_entry))] = binary_entry

    def __len__(self) -> int:
        return self.mmap.size() // ENTRY.size

    def __getitem__(self, index: int):
        if index < 0: index = len(self) + index
        try: key, raw_move, weight, learn = ENTRY.unpack_from(self.mmap, index * ENTRY.size)
        except struct.error as e: raise IndexError() from e
        return key, raw_move, weight, learn
    
    def __add__(self, other):
        # !!! Weight priorization is not implemented yet !!!
        if not isinstance(other, PolyglotBook): raise TypeError()
        new = PolyglotBook()
        #new.book = {**self.book, **other.book}  -> fails merging nested lists
        new.book = self.book.copy()
        for key in other.book:
            if key in new.book:
                for entries in other.book[key]:
                    if not entries in new.book[key]: new.book[key].append(entries)
            else: new.book[key] = other.book[key]
        new.unpacked = self.unpacked.copy()
        for key in other.unpacked:
            if key in new.unpacked:
                for entries in other.unpacked[key]:
                    if not entries in new.unpacked[key]: new.unpacked[key].append(entries)
            else: new.unpacked[key] = other.unpacked[key]
        new.packmap = self.packmap.copy()
        for key in other.packmap:
            if key in new.packmap:
                for entries in other.packmap[key]:
                    if not entries in new.packmap[key]: new.packmap[key].append(entries)
            else: new.packmap[key] = other.packmap[key]
        return new






