from sys import argv, stdin
import os
import pygame

# assembler and components
from core.asm.asm import Assembler
from core.components.cpu import CPU
from core.components.mem import Memory
from core.components.screen import Screen 

# makes prints colored
from rich import print

printdata = False  # set to True to print all data in ROM after execution


def main():
    if len(argv) < 2:
        raise FileNotFoundError("No program file provided. Please specify a file containing the assembly code or a .rom file.")

    filepath = argv[1]
    ext = os.path.splitext(filepath)[1].lower()

    # based on ext, load raw rom or assemble source code
    if ext in ['.rom', '.bin']:
        # load binary ROM directly
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # put code in a bytearray and set origin to default $A000
        code = bytearray(data)
        origin = 0xA000
        print(f"Loaded raw ROM '{filepath}' ({len(code)} bytes) at default origin ${origin:04X}")

    else:
        # assemble source file
        with open(filepath, 'r') as f:
            program_text = f.read()

        asm = Assembler()
        code = asm.assemble(program_text)
        origin = getattr(asm, 'origin', 0xA000) or 0xA000
        print(f"Assembled '{filepath}' ({len(code)} bytes) at origin ${origin:04X}")

    # initialize memory and load ROM
    mem = Memory()
    mem.load_rom(code, origin)

    # register print handler at $D020 (for output)
    mem.register_write_handler(0xD020, lambda addr, val: print(chr(val), end='', flush=True))

    # register read handler at $D010 (for input)
    mem.register_read_handler(0xD010, lambda addr: ord(stdin.read(1)))

    # init cpu
    cpu = CPU(mem)
    cpu.PC = origin

    # start the screen separately
    screen = Screen(mem)
    screen.start()

    # run the program (ending when cpu.PC equals 0x00)
    while True:
        try:
            if cpu.read(cpu.PC) == 0x00:
                cpu.step()  # execute BRK
                break
            cpu.step()
        except KeyboardInterrupt:
            print("\n[bold red]Execution interrupted by user.[/bold red]")
            break
    
    # keep screen up when BRK is reached until user closes it
    while screen.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                screen.running = False
        pygame.time.wait(100)

    # stop screen thread
    screen.stop()
    pygame.quit()

    # print all data in ROM if flag is enabled
    if printdata:
        print("\n[green]ROM Data Dump:[/green]")
        start = origin
        for i, byte in enumerate(code):
            addr = start + i
            print(f"[blue]${addr:04X}:[/blue] [green]{byte:02X}[/green]")


if __name__ == '__main__':
    main()