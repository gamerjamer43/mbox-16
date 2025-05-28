from sys import argv, stdin
import pygame  # new import for event processing
from core.asm.asm import Assembler
from core.components.cpu import CPU
from core.components.mem import Memory
from core.components.screen import Screen  # new import

# makes prints colored
from rich import print

printdata = False  # set to True to print all data in ROM after execution

def main():
    # get program text from file if given
    if len(argv) > 1:
        with open(argv[1], 'r') as f:
            program_text = f.read()

    else:
        raise FileNotFoundError("No program file provided. Please specify a file containing the assembly code.")
    
    # assemble and load
    asm = Assembler()
    code = asm.assemble(program_text)

    # load at assembler origin
    mem = Memory()
    mem.load_rom(code, asm.origin)

    # register print handler at $D020
    mem.register_write_handler(0xD020, lambda addr, val: print(chr(val), end='', flush=True))
    mem.register_read_handler(0xD010, lambda addr: ord(stdin.read(1)))

    # also init cpu
    cpu = CPU(mem)
    cpu.PC = asm.origin

    screen = Screen(mem)  # new screen instance
    screen.start()        # start asynchronous screen updates

    # run the program
    while True:
        try:
            if cpu.read(cpu.PC) == 0x00:
                cpu.step()  # execute BRK
                break
                
            cpu.step()
        except KeyboardInterrupt:
            print("\n[bold red]Execution interrupted by user.[/bold red]")
            break
    
    while screen.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                screen.running = False
        pygame.time.wait(100)

    screen.stop()
    pygame.quit()

    # print all data in ROM if flag is enabled
    if printdata == True:
        print("\n[green]ROM Data Dump:[/green]")
        for addr in range(mem.BASIC_ROM_START, mem.BASIC_ROM_START + len(code)):
            print(f"[blue]${addr:04X}:[/blue] [green]{mem.data[addr]:02X}[green]")

if __name__ == '__main__':
    main()