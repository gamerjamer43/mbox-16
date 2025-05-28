# path management and args
from os import getcwd, makedirs, path
from sys import argv

# makes prints colored
from rich import print

from core.asm.asm import Assembler

def main():
    # if args are not provided, print usage and exit
    if len(argv) < 2:
        print("[red]Usage: python dump.py <file.asm> [hex|bin|both][/red]")
        exit(1)

    # determine output type
    output_type = argv[2].lower() if len(argv) > 2 else "both"
    if output_type not in ("hex", "bin", "both"):
        print("[red]Output type must be one of: hex, bin, both[/red]")
        exit(1)

    # open assembly file from first arg
    asmfile = argv[1]
    with open(asmfile, 'r') as f:
        program_text = f.read()

    # create assembler instance and assemble the code
    asm = Assembler()
    code = asm.assemble(program_text)

    # find bin directory
    bin_dir = path.join(getcwd(), 'bin')
    makedirs(bin_dir, exist_ok=True)

    # write binary if requested
    if output_type in ("bin", "both"):
        binpath = path.join(bin_dir, path.splitext(path.basename(asmfile))[0] + '.bin')
        with open(binpath, 'wb') as f:
            f.write(code)

        print(f"[green]Binary written to: {binpath}[/green]")

    # write hex dump if requested
    if output_type in ("hex", "both"):
        hexpath = path.join(bin_dir, path.splitext(path.basename(asmfile))[0] + '.hex')
        with open(hexpath, 'w') as f:
            for i, b in enumerate(code):
                addr = asm.origin + i
                f.write(f"${addr:04X}: {b:02X}\n")
                
        print(f"[green]Hex dump written to: {hexpath}[/green]")

if __name__ == "__main__":
    main()