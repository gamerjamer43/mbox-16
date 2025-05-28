import sys, os
from core.asm.asm import Assembler

def main():
    if len(sys.argv) < 2:
        print("Usage: dumprom.py <source.asm>")
        sys.exit(1)
    
    source = sys.argv[1]
    try:
        with open(source, 'r') as f:
            text = f.read()
        asm = Assembler()
        bytecode = asm.assemble(text)

    except Exception as e:
        print("Assembly error:", e)
        sys.exit(1)
    
    # place ROM file in the roms directory
    base, _ = os.path.splitext(os.path.basename(source))
    roms_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roms")
    if not os.path.exists(roms_dir):
        os.makedirs(roms_dir)
        
    outname = os.path.join(roms_dir, base + ".rom")
    with open(outname, "wb") as f:
        f.write(bytecode)

    print(f"Created ROM file: {outname}")

if __name__ == "__main__":
    main()