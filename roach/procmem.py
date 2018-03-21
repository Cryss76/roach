# Copyright (C) 2018 Jurriaan Bremer.
# This file is part of Roach - https://github.com/jbremer/roach.
# See the file 'docs/LICENSE.txt' for copying permission.

import mmap
import os
import re
import struct

from roach.disasm import disasm

PAGE_READONLY = 0x00000002
PAGE_READWRITE = 0x00000004
PAGE_WRITECOPY = 0x00000008
PAGE_EXECUTE = 0x00000010
PAGE_EXECUTE_READ = 0x00000020
PAGE_EXECUTE_READWRITE = 0x00000040
PAGE_EXECUTE_WRITECOPY = 0x00000080

page_access = {
    PAGE_READONLY: "r",
    PAGE_READWRITE: "rw",
    PAGE_WRITECOPY: "rwc",
    PAGE_EXECUTE: "rx",
    PAGE_EXECUTE_READ: "rx",
    PAGE_EXECUTE_READWRITE: "rwx",
    PAGE_EXECUTE_WRITECOPY: "rwxc",
}

class Region(object):
    def __init__(self, addr, size, state, type_, protect, offset):
        self.addr = addr
        self.size = size
        self.end = addr + size
        self.state = state
        self.type_ = type_
        self.protect = protect
        self.offset = offset

    def to_json(self):
        return {
            "addr": "0x%08x" % self.addr,
            "end": "0x%08x" % (self.addr + self.size),
            "size": self.size,
            "state": self.state,
            "type": self.type_,
            "protect": page_access.get(self.protect),
            "offset": self.offset,
        }

class ProcessMemory(object):
    """Wrapper object to operate on process memory dumps."""

    def __init__(self, file_or_filepath, load=True):
        if hasattr(file_or_filepath, "read"):
            self.f = file_or_filepath
        else:
            self.f = open(file_or_filepath, "rb")

        # By default mmap(2) the file into memory.
        if load:
            if hasattr(mmap, "PROT_READ"):
                access = mmap.PROT_READ
            elif hasattr(mmap, "ACCESS_READ"):
                access = mmap.ACCESS_READ
            else:
                raise RuntimeError(
                    "Loading process memory is not supported on your OS!"
                )

            self.m = mmap.mmap(self.f.fileno(), 0, access=access)
        else:
            self.m = self.f

        self.load = load
        self._regions = []

    @property
    def regions(self):
        """Read the defined regions in this process memory dump."""
        if self._regions:
            return self._regions

        self.m.seek(0)
        while True:
            buf = self.m.read(24)
            if not buf:
                break

            addr, size, state, typ, protect = struct.unpack("QIIII", buf)

            self._regions.append(
                Region(addr, size, state, typ, protect, self.m.tell())
            )
            try:
                self.m.seek(size, os.SEEK_CUR)
            except ValueError:
                break
        return self._regions

    def v2p(self, addr):
        """Virtual address to physical offset translation."""
        for region in self.regions:
            if addr >= region.addr and addr < region.end:
                return region.offset + addr - region.addr

    def p2v(self, off):
        """Physical offset to virtual address translation."""
        for region in self.regions:
            if off >= region.offset and off < region.offset + region.size:
                return region.addr + off - region.offset

    def addr_range(self, addr):
        """Returns a (start, end) range for an address."""
        for region in self.regions:
            if addr >= region.addr and addr < region.end:
                return region.addr, region.size

    def addr_region(self, addr):
        for region in self.regions:
            if addr >= region.addr and addr < region.end:
                return region

    def read(self, offset, length):
        """Read a chunk of memory from the memory dump."""
        self.m.seek(offset, os.SEEK_SET)
        return self.m.read(length)

    def readv(self, addr, length):
        """Reads a continuous buffer with address and length."""
        ret = []
        while length:
            a, l = self.addr_range(addr)
            l = min(a + l - addr, length)
            ret.append(self.read(self.v2p(addr), l))
            addr, length = addr + l, length - l
        return "".join(ret)

    def read_until(self, addr, s=None):
        """Reads a continuous buffer with address until the stop marker."""
        ret = []
        while True:
            r = self.addr_range(addr)
            if not r:
                break
            a, l = r
            l = a + l - addr
            buf = self.read(self.v2p(addr), l)
            if s and s in buf:
                ret.append(buf[:buf.index(s)])
                break
            ret.append(buf)
            addr = addr + l
        return "".join(ret)

    def uint8p(self, offset):
        """Read unsigned 8-bit value at offset."""
        return ord(self.read(offset, 1))

    def uint16p(self, offset):
        """Read unsigned 16-bit value at offset."""
        return struct.unpack("H", self.read(offset, 2))[0]

    def uint32p(self, offset):
        """Read unsigned 32-bit value at offset."""
        return struct.unpack("I", self.read(offset, 4))[0]

    def uint64p(self, offset):
        """Read unsigned 64-bit value at offset."""
        return struct.unpack("Q", self.read(offset, 8))[0]

    def uint8v(self, addr):
        """Read unsigned 8-bit value at address."""
        return ord(self.readv(addr, 1))

    def uint16v(self, addr):
        """Read unsigned 16-bit value at address."""
        return struct.unpack("H", self.readv(addr, 2))[0]

    def uint32v(self, addr):
        """Read unsigned 32-bit value at address."""
        return struct.unpack("I", self.readv(addr, 4))[0]

    def uint64v(self, addr):
        """Read unsigned 64-bit value at address."""
        return struct.unpack("Q", self.readv(addr, 8))[0]

    def asciiz(self, addr):
        """Read a nul-terminated ASCII string at address."""
        return self.read_until(addr, "\x00")

    def regexp(self, query):
        """Performs a regex on the file, must use mmap(2) loading."""
        if not self.load:
            raise RuntimeError("can only regex on a file!")
        x = re.search(query, self.m)
        return x.start() if x else None

    def regexv(self, query):
        """Performs a regex on the file, must use mmap(2) loading."""
        off = self.regexp(query)
        return self.p2v(off) if off else None

    def disasmv(self, addr, size):
        return disasm(self.readv(addr, size), addr)
