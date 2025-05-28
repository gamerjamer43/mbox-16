class Memory:
    def __init__(self):
        """initialize the memory with a size of 64 KB and set up ROM regions."""
        # 64 KB addressable memory
        self.size = 0x10000
        self.data = bytearray(self.size)

        # ROM regions (loaded once at startup)
        self.BASIC_ROM_START  = 0xA000  # 8 KB
        self.KERNAL_ROM_START = 0xE000  # 8 KB

        # I/O and character ROM at $D000-$DFFF
        self.IO_START = 0xD000
        self.IO_END   = 0xDFFF
        
        # screen RAM: default text start at $0400 (16384 bytes for 128x128)
        self.SCREEN_RAM_START = 0x0400
        self.SCREEN_RAM_SIZE  = 16384

        # store handlers for reading and writing which can be used to implement I/O, memory-mapped devices, etc
        self.read_handlers = {}
        self.write_handlers = {}

        # allocation pointer for auto-allocation of data (default starting at $B000) will be used in the future
        self.alloc_ptr = 0xB000

    def read(self, addr):
        """read a byte from memory at the given address."""
        addr &= 0xFFFF
        if addr in self.read_handlers:
            return self.read_handlers[addr](addr)
        return self.data[addr]

    def write(self, addr, val):
        """write a byte to memory at the given address."""
        addr &= 0xFFFF
        if addr in self.write_handlers:
            self.write_handlers[addr](addr, val & 0xFF)
            return
        
        # writes to ROM and I/O are ignored or trap as needed
        if self.BASIC_ROM_START <= addr < self.BASIC_ROM_START + 0x2000: return
        if self.KERNAL_ROM_START <= addr < self.KERNAL_ROM_START + 0x2000: return
        self.data[addr] = val & 0xFF

    # loads ROM data @ a given base address
    def load_rom(self, code, base):
        """load ROM data into memory at the specified base address."""
        for i,b in enumerate(code):
            self.data[base + i] = b

    # handler helpers (registration for read/write handlers)
    def register_read_handler(self, addr, handler):
        """register a read handler for a specific address."""
        self.read_handlers[addr & 0xFFFF] = handler

    def register_write_handler(self, addr, handler):
        """register a write handler for a specific address."""
        self.write_handlers[addr & 0xFFFF] = handler

    # unused for rn
    def allocate(self, length, start=None):
        """allocate a block of memory of the given length, starting from the specified address."""
        if start is None:
            candidate = self.alloc_ptr

        else:
            candidate = start

        while candidate + length <= self.size:
            if all(self.data[i] == 0 for i in range(candidate, candidate + length)):
                self.alloc_ptr = candidate + length
                return candidate
            
            candidate += 1

        # if no free block found, raise an error
        raise MemoryError("No free memory block available.")