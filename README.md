# MBOX-16

MBOX-16 (also known as MOSBOX) is a 6502-based virtual computer and assembler toolkit, created as a project to learn, experiment, and program in a limiting environment. It provides a simple, extensible emulator for the 6502 CPU, a memory subsystem, and an assembler for writing and running assembly code.

---

## Features

- **6502 CPU Emulation**: Implements the core instruction set and addressing modes of the MOS 6502 processor.
- **Assembler**: Converts 6502 assembly code into machine code, supporting labels, directives, and various addressing modes.
- **Memory Model**: 64KB addressable memory with support for ROM, RAM, I/O regions, and memory-mapped devices.
- **I/O Handlers**: Easily register custom read/write handlers for memory-mapped I/O.
- **Simple Loader**: Loads and runs assembled programs, with support for keyboard input and character output.

---

## Getting Started

### Requirements

- Python 3.8+
- [rich](https://pypi.org/project/rich/) (`pip install rich`)

### Running a Program

1. **Write your 6502 assembly code** in a file, e.g., `hello.asm`.

2. **Run the loader** with your assembly file:

   ```sh
   python loader.py hello.asm <optional start addr>
   ```

   The loader will assemble your code, load it into memory, and execute it.

### Example Assembly Program

```assembly
        LDX #$41
        STX $D020   ; Output 'A' to console
        BRK         ; Halt
```

--- 

### Memory Map

- **ROM**: `$A000-$BFFF` (default load address for assembled code)
- **KERNAL ROM**: `$E000-$FFFF`
- **I/O**: `$D000-$DFFF`
- **Screen RAM**: `$0400` (default, 16KB)

### I/O

- **Output**: Writing to `$D020` prints a character to the console.
- **Input**: Reading from `$D010` reads a character from stdin.

---

## Planned Features:
- **Screen:** I tried two renditions of this with a screen, but it created too many problems when trying to pinpoint where bugs took place. Long story short I overlapped Opcode addresses and VRAM addresses when I allocated VRAM in the memory model like a silly gentleman.
- **Basic operating system:** I want to layer a basic OS on top of this that you can plug in like a ROM. This will contain developer tools such as a code editor, a sprite creator, and other features to make development on this computer easy and fun.
- **Higher level language:** To put on top of the assembly model, I want to make a higher level language for this that breaks down into assembly for this. Go take a look at [Boron](https://github.com/gamerjamer43/Boron), I may port it over here and make it compiled!

## Project Structure

- `core/asm/asm.py` — Assembler implementation
- `core/asm/opcodes.py` — Opcode mappings
- `core/asm/addrtype.py` — Addressing mode definitions
- `core/components/cpu.py` — 6502 CPU emulation
- `core/components/mem.py` — Memory subsystem
- `loader.py` — Program loader and entry point

## License

GNU General Public License v3

---

*Made with love by @gamerjamer43*
