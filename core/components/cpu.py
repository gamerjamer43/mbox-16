from enum import IntEnum

class Flag(IntEnum):
    """processor status flags."""
    C = 0x01  # carry flag
    Z = 0x02  # zero flag
    I = 0x04  # interrupt disable
    D = 0x08  # decimal mode
    B = 0x10  # break command
    U = 0x20  # unused (always set to 1)
    V = 0x40  # overflow flag
    N = 0x80  # negative flag

class CPU:
    def __init__(self, memory):
        """initialize the CPU with a memory object and reset."""
        self.memory = memory              # expects a Memory obj
        self.reset()

    def reset(self):
        """reset the CPU state to initial values."""
        self.A = 0                        # accumulator
        self.X = 0                        # x register
        self.Y = 0                        # y register
        self.SP = 0xFD                    # stack pointer
        self.PC = self.read_word(0xFFFC)  # reset vector
        self.P = 0x24                     # processor status: NV-BDIZC
        self.cycles = 0                   # cycle count

        # initialize opcode dispatch table
        self._init_opcodes()


    # --- memory helpers ---
    def read(self, addr):
        """read a byte from memory at the specified address."""
        return self.memory.read(addr & 0xFFFF)

    def write(self, addr, value):
        """write a byte to memory at the specified address."""
        self.memory.write(addr & 0xFFFF, value & 0xFF)

    def read_word(self, addr):
        """read a 16-bit word from memory at the specified address."""
        lo = self.read(addr)
        hi = self.read(addr + 1)
        return (hi << 8) | lo
    
    def read_immediate(self) -> int:
        """read an immediate value from the current program counter."""
        value = self.memory[self.PC]
        self.PC += 1
        return value

    def read_zero_page(self) -> int:
        """read a zero-page value from the current program counter."""
        addr = self.memory[self.PC]
        self.PC += 1
        return self.memory[addr]
    

    # --- stack helpers ---
    def push(self, value):
        """push a byte onto the stack."""
        self.write(0x100 + self.SP, value)
        self.SP = (self.SP - 1) & 0xFF

    def pull(self):
        """pull a byte from the stack."""
        self.SP = (self.SP + 1) & 0xFF
        return self.read(0x100 + self.SP)
    

    # --- status flags ---
    def set_flag(self, flag, cond):
        """set or clear a status flag based on a condition."""
        if cond:
            self.P |= flag
        else:
            self.P &= ~flag

    def get_flag(self, flag):
        """check if a status flag is set."""
        return (self.P & flag) != 0
    

    # --- addressing modes ---
    def immediate(self):
        """read an immediate value from the current program counter."""
        value = self.read(self.PC)
        self.PC += 1
        return value

    def zero_page(self):
        """read a zero-page address from the current program counter."""
        addr = self.read(self.PC)
        self.PC += 1
        return addr

    def zero_page_x(self):
        """read a zero-page address with X offset from the current program counter."""
        addr = (self.read(self.PC) + self.X) & 0xFF
        self.PC += 1
        return addr

    def zero_page_y(self):
        """read a zero-page address with Y offset from the current program counter."""
        addr = (self.read(self.PC) + self.Y) & 0xFF
        self.PC += 1
        return addr

    def absolute(self):
        """read an absolute address from the current program counter."""
        addr = self.read_word(self.PC)
        self.PC += 2
        return addr

    def absolute_x(self):
        """read an absolute address with X offset from the current program counter."""
        base = self.read_word(self.PC)
        self.PC += 2
        return (base + self.X) & 0xFFFF

    def absolute_y(self):
        """read an absolute address with Y offset from the current program counter."""
        base = self.read_word(self.PC)
        self.PC += 2
        return (base + self.Y) & 0xFFFF

    def indirect(self):
        """read an indirect address from the current program counter."""
        ptr = self.read_word(self.PC)
        self.PC += 2
        # emulated 6502 bug: indirect JMP wraps page
        if (ptr & 0xFF) == 0xFF:
            lo = self.read(ptr)
            hi = self.read(ptr & 0xFF00)
        else:
            lo = self.read(ptr)
            hi = self.read(ptr + 1)
        return (hi << 8) | lo

    def indexed_indirect(self):
        """read an indexed indirect address from the current program counter."""
        zp = (self.read(self.PC) + self.X) & 0xFF
        self.PC += 1
        lo = self.read(zp)
        hi = self.read((zp + 1) & 0xFF)
        return (hi << 8) | lo

    def indirect_indexed(self):
        """read an indirect indexed address from the current program counter."""
        zp = self.read(self.PC)
        self.PC += 1
        lo = self.read(zp)
        hi = self.read((zp + 1) & 0xFF)
        return ((hi << 8) | lo) + self.Y

    def relative(self):
        """read a relative address from the current program counter."""
        offset = self.read(self.PC)
        self.PC += 1
        if offset < 0x80:
            return self.PC + offset
        else:
            return self.PC + offset - 0x100
        

    # --- instruction implementations ---
    def lda(self, value):
        """load accumulator with a value."""
        self.A = value & 0xFF
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def ldx(self, value):
        """load x register with a value."""
        self.X = value & 0xFF
        self.set_flag(Flag.Z, self.X == 0)
        self.set_flag(Flag.N, self.X & 0x80)

    def ldy(self, value):
        """load y register with a value."""
        self.Y = value & 0xFF
        self.set_flag(Flag.Z, self.Y == 0)
        self.set_flag(Flag.N, self.Y & 0x80)


    def sta(self, addr):
        """store accumulator to memory."""
        self.write(addr, self.A)

    def stx(self, addr):
        """store x register to memory."""
        self.write(addr, self.X)

    def sty(self, addr):
        """store y register to memory."""
        self.write(addr, self.Y)


    def tax(self):
        """transfer accumulator to x register."""
        self.X = self.A
        self.set_flag(Flag.Z, self.X == 0)
        self.set_flag(Flag.N, self.X & 0x80)

    def tay(self):
        """transfer accumulator to y register."""
        self.Y = self.A
        self.set_flag(Flag.Z, self.Y == 0)
        self.set_flag(Flag.N, self.Y & 0x80)

    def txa(self):
        """transfer x register to accumulator."""
        self.A = self.X
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def tya(self):
        """transfer y register to accumulator."""
        self.A = self.Y
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def tsx(self):
        """transfer stack pointer to x register."""
        self.X = self.SP
        self.set_flag(Flag.Z, self.X == 0)
        self.set_flag(Flag.N, self.X & 0x80)

    def txs(self):
        """transfer x register to stack pointer."""
        self.SP = self.X


    def pha(self):
        """push accumulator onto the stack."""
        self.push(self.A)

    def php(self):
        """push processor status onto the stack."""
        self.push(self.P | Flag.B | Flag.U)

    def pla(self):
        """pull accumulator from the stack."""
        self.A = self.pull()
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def plp(self):
        """pull processor status from the stack."""
        self.P = (self.pull() & ~Flag.B) | Flag.U


    def adc(self, value):
        """add with carry to accumulator."""
        carry = 1 if self.get_flag(Flag.C) else 0
        result = self.A + value + carry
        self.set_flag(Flag.C, result > 0xFF)
        self.set_flag(Flag.Z, (result & 0xFF) == 0)
        self.set_flag(Flag.N, result & 0x80)
        self.set_flag(Flag.V, (~(self.A ^ value) & (self.A ^ result)) & 0x80)
        self.A = result & 0xFF

    def sbc(self, value):
        """subtract with carry from accumulator."""
        carry = 1 if self.get_flag(Flag.C) else 0
        value ^= 0xFF
        result = self.A + value + carry
        self.set_flag(Flag.C, result > 0xFF)
        self.set_flag(Flag.Z, (result & 0xFF) == 0)
        self.set_flag(Flag.N, result & 0x80)
        self.set_flag(Flag.V, (~(self.A ^ value) & (self.A ^ result)) & 0x80)
        self.A = result & 0xFF


    def and_(self, value):
        """logical and with accumulator."""
        self.A &= value
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def ora(self, value):
        """logical or with accumulator."""
        self.A |= value
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)

    def eor(self, value):
        """exclusive or with accumulator."""
        self.A ^= value
        self.set_flag(Flag.Z, self.A == 0)
        self.set_flag(Flag.N, self.A & 0x80)


    def cmp(self, value):
        """compare accumulator with a value."""
        temp = self.A - value
        self.set_flag(Flag.C, self.A >= value)
        self.set_flag(Flag.Z, (temp & 0xFF) == 0)
        self.set_flag(Flag.N, temp & 0x80)

    def cpx(self, value):
        """compare x register with a value."""
        temp = self.X - value
        self.set_flag(Flag.C, self.X >= value)
        self.set_flag(Flag.Z, (temp & 0xFF) == 0)
        self.set_flag(Flag.N, temp & 0x80)

    def cpy(self, value):
        """compare y register with a value."""
        temp = self.Y - value
        self.set_flag(Flag.C, self.Y >= value)
        self.set_flag(Flag.Z, (temp & 0xFF) == 0)
        self.set_flag(Flag.N, temp & 0x80)


    def inc(self, addr):
        """increment a value in memory or a register."""
        value = (self.read(addr) + 1) & 0xFF
        self.write(addr, value)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)

    def inx(self):
        """increment x register."""
        self.X = (self.X + 1) & 0xFF
        self.set_flag(Flag.Z, self.X == 0)
        self.set_flag(Flag.N, self.X & 0x80)

    def iny(self):
        """increment y register."""
        self.Y = (self.Y + 1) & 0xFF
        self.set_flag(Flag.Z, self.Y == 0)
        self.set_flag(Flag.N, self.Y & 0x80)


    def dec(self, addr):
        """decrement a value in memory or a register."""
        value = (self.read(addr) - 1) & 0xFF
        self.write(addr, value)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)

    def dex(self):
        """decrement x register."""
        self.X = (self.X - 1) & 0xFF
        self.set_flag(Flag.Z, self.X == 0)
        self.set_flag(Flag.N, self.X & 0x80)

    def dey(self):
        """decrement y register."""
        self.Y = (self.Y - 1) & 0xFF
        self.set_flag(Flag.Z, self.Y == 0)
        self.set_flag(Flag.N, self.Y & 0x80)


    def asl(self, addr=None):
        """arithmetic shift left: shifts bits left, setting C flag to bit 7."""
        if addr is None:
            value = self.A
            self.set_flag(Flag.C, value & 0x80)
            value = (value << 1) & 0xFF
            self.A = value
        else:
            value = self.read(addr)
            self.set_flag(Flag.C, value & 0x80)
            value = (value << 1) & 0xFF
            self.write(addr, value)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)

    def lsr(self, addr=None):
        """logical shift right: shifts bits right, setting c flag to bit 0."""
        if addr is None:
            value = self.A
            self.set_flag(Flag.C, value & 0x01)
            value = (value >> 1) & 0xFF
            self.A = value
        else:
            value = self.read(addr)
            self.set_flag(Flag.C, value & 0x01)
            value = (value >> 1) & 0xFF
            self.write(addr, value)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)


    def rol(self, addr=None):
        """rotate left: shifts bits left, setting c flag to bit 7 and moving c to bit 0."""
        carry_in = 1 if self.get_flag(Flag.C) else 0
        if addr is None:
            value = self.A
            carry_out = value & 0x80
            value = ((value << 1) | carry_in) & 0xFF
            self.A = value
        else:
            value = self.read(addr)
            carry_out = value & 0x80
            value = ((value << 1) | carry_in) & 0xFF
            self.write(addr, value)
        self.set_flag(Flag.C, carry_out)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)

    def ror(self, addr=None):
        """rotate right: shifts bits right, setting c flag to bit 0 and moving c to bit 7."""
        carry_in = 1 if self.get_flag(Flag.C) else 0
        if addr is None:
            value = self.A
            carry_out = value & 0x01
            value = ((carry_in << 7) | (value >> 1)) & 0xFF
            self.A = value
        else:
            value = self.read(addr)
            carry_out = value & 0x01
            value = ((carry_in << 7) | (value >> 1)) & 0xFF
            self.write(addr, value)
        self.set_flag(Flag.C, carry_out)
        self.set_flag(Flag.Z, value == 0)
        self.set_flag(Flag.N, value & 0x80)


    def bit(self, value):
        """bit test: sets flags based on the value ANDed with accumulator."""
        self.set_flag(Flag.Z, (self.A & value) == 0)
        self.set_flag(Flag.N, value & 0x80)
        self.set_flag(Flag.V, value & 0x40)


    def jmp(self, addr):
        """jump to an absolute address."""
        self.PC = addr

    def jsr(self, addr):
        """jump to subroutine: pushes return address onto stack and jumps to addr."""
        self.push((self.PC - 1) >> 8)
        self.push((self.PC - 1) & 0xFF)
        self.PC = addr


    def rts(self):
        """return from subroutine: pulls return address from stack and continues execution."""
        lo = self.pull()
        hi = self.pull()
        self.PC = ((hi << 8) | lo) + 1

    def rti(self):
        """return from interrupt: pulls processor status and program counter from stack."""
        self.P = (self.pull() & ~Flag.B) | Flag.U
        lo = self.pull()
        hi = self.pull()
        self.PC = (hi << 8) | lo


    def clc(self):
        """clear carry flag."""
        self.set_flag(Flag.C, False)

    def sec(self):
        """set carry flag."""
        self.set_flag(Flag.C, True)

    def cli(self):
        """clear interrupt disable flag."""
        self.set_flag(Flag.I, False)

    def sei(self):
        """set interrupt disable flag."""
        self.set_flag(Flag.I, True)

    def clv(self):
        """clear overflow flag."""
        self.set_flag(Flag.V, False)

    def cld(self):
        """clear decimal mode flag."""
        self.set_flag(Flag.D, False)

    def sed(self):
        """set decimal mode flag."""
        self.set_flag(Flag.D, True)


    def brk(self):
        """break: pushes program counter and processor status onto stack, sets interrupt disable flag, and jumps to interrupt vector."""
        self.PC += 1
        self.push(self.PC >> 8)
        self.push(self.PC & 0xFF)
        self.php()
        self.set_flag(Flag.I, True)
        self.PC = self.read_word(0xFFFE)

    def nop(self):
        """no operation: does nothing."""
        pass


    # --- branches ---
    def branch(self, cond):
        """branch to a relative address if the condition is met."""
        addr = self.relative()
        if cond:
            self.PC = addr
            

    # --- opcode Table Initialization ---
    def _init_opcodes(self):
        """
        Initializes opcode dispatch table for the CPU.
        The opcode table maps each opcode (byte value) to the corresponding handler function/lambda,
        implementing the instruction's behavior for the following instruction groups:

        # Load/Store Operations:
            - LDA, LDX, LDY: Load accumulator/X/Y register from memory (various addressing modes)
            - STA, STX, STY: Store accumulator/X/Y register to memory (various addressing modes)

        # Register Transfers:
            - TAX, TAY, TXA, TYA, TSX, TXS: Transfer values between registers and stack pointer

        # Stack Operations:
            - PHA, PHP, PLA, PLP: Push/Pull accumulator and processor status to/from stack

        # Arithmetic Operations:
            - ADC: Add with carry (various addressing modes)
            - SBC: Subtract with carry (various addressing modes)

        # Logical Operations:
            - AND, ORA, EOR: Logical AND, OR, XOR with accumulator (various addressing modes)
            - BIT: Bit test (zero page, absolute)

        # Comparison Operations:
            - CMP, CPX, CPY: Compare accumulator/X/Y with memory (various addressing modes)

        # Increment/Decrement Operations:
            - INC, INX, INY: Increment memory, X, or Y register
            - DEC, DEX, DEY: Decrement memory, X, or Y register

        # Shift/Rotate Operations:
            - ASL, LSR: Arithmetic shift left, logical shift right (accumulator and memory)
            - ROL, ROR: Rotate left/right (accumulator and memory)

        # Jump/Call/Return Operations:
            - JMP: Jump to address (absolute, indirect)
            - JSR: Jump to subroutine
            - RTS, RTI: Return from subroutine/interrupt
            - BRK: Force interrupt

        # No Operation:
            - NOP: No operation

        # Flag Operations:
            - CLC, SEC, CLI, SEI, CLV, CLD, SED: Clear/set processor status flags

        # Branch Operations:
            - BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS: Conditional branches based on processor flags
        """
        # initialize opcode table
        self.opcode_table = {}

        # load accumulator: lda
        self.opcode_table[0xA9] = lambda: self.lda(self.immediate())
        self.opcode_table[0xA5] = lambda: self.lda(self.read(self.zero_page()))
        self.opcode_table[0xB5] = lambda: self.lda(self.read(self.zero_page_x()))
        self.opcode_table[0xAD] = lambda: self.lda(self.read(self.absolute()))
        self.opcode_table[0xBD] = lambda: self.lda(self.read(self.absolute_x()))
        self.opcode_table[0xB9] = lambda: self.lda(self.read(self.absolute_y()))
        self.opcode_table[0xA1] = lambda: self.lda(self.read(self.indexed_indirect()))
        self.opcode_table[0xB1] = lambda: self.lda(self.read(self.indirect_indexed()))

        # load x register: ldx
        self.opcode_table[0xA2] = lambda: self.ldx(self.immediate())
        self.opcode_table[0xA6] = lambda: self.ldx(self.read(self.zero_page()))
        self.opcode_table[0xB6] = lambda: self.ldx(self.read(self.zero_page_y()))
        self.opcode_table[0xAE] = lambda: self.ldx(self.read(self.absolute()))
        self.opcode_table[0xBE] = lambda: self.ldx(self.read(self.absolute_y()))

        # load y register: ldy
        self.opcode_table[0xA0] = lambda: self.ldy(self.immediate())
        self.opcode_table[0xA4] = lambda: self.ldy(self.read(self.zero_page()))
        self.opcode_table[0xB4] = lambda: self.ldy(self.read(self.zero_page_x()))
        self.opcode_table[0xAC] = lambda: self.ldy(self.read(self.absolute()))
        self.opcode_table[0xBC] = lambda: self.ldy(self.read(self.absolute_x()))

        # store accumulator: sta
        self.opcode_table[0x85] = lambda: self.sta(self.zero_page())
        self.opcode_table[0x95] = lambda: self.sta(self.zero_page_x())
        self.opcode_table[0x8D] = lambda: self.sta(self.absolute())
        self.opcode_table[0x9D] = lambda: self.sta(self.absolute_x())
        self.opcode_table[0x99] = lambda: self.sta(self.absolute_y())
        self.opcode_table[0x81] = lambda: self.sta(self.indexed_indirect())
        self.opcode_table[0x91] = lambda: self.sta(self.indirect_indexed())

        # store x register: stx
        self.opcode_table[0x86] = lambda: self.stx(self.zero_page())
        self.opcode_table[0x96] = lambda: self.stx(self.zero_page_y())
        self.opcode_table[0x8E] = lambda: self.stx(self.absolute())

        # store y register: sty
        self.opcode_table[0x84] = lambda: self.sty(self.zero_page())
        self.opcode_table[0x94] = lambda: self.sty(self.zero_page_x())
        self.opcode_table[0x8C] = lambda: self.sty(self.absolute())

        # transfers: TAX, TAY, TXA, TYA, TSX, TXS
        self.opcode_table[0xAA] = self.tax
        self.opcode_table[0xA8] = self.tay
        self.opcode_table[0x8A] = self.txa
        self.opcode_table[0x98] = self.tya
        self.opcode_table[0xBA] = self.tsx
        self.opcode_table[0x9A] = self.txs
        
        # push/pull accumulator and status: PHA, PHP, PLA, PLP
        self.opcode_table[0x48] = self.pha
        self.opcode_table[0x08] = self.php
        self.opcode_table[0x68] = self.pla
        self.opcode_table[0x28] = self.plp

        # add with carry: ADC
        self.opcode_table[0x69] = lambda: self.adc(self.immediate())
        self.opcode_table[0x65] = lambda: self.adc(self.read(self.zero_page()))
        self.opcode_table[0x75] = lambda: self.adc(self.read(self.zero_page_x()))
        self.opcode_table[0x6D] = lambda: self.adc(self.read(self.absolute()))
        self.opcode_table[0x7D] = lambda: self.adc(self.read(self.absolute_x()))
        self.opcode_table[0x79] = lambda: self.adc(self.read(self.absolute_y()))
        self.opcode_table[0x61] = lambda: self.adc(self.read(self.indexed_indirect()))
        self.opcode_table[0x71] = lambda: self.adc(self.read(self.indirect_indexed()))

        # subtract with carry: SBC
        self.opcode_table[0xE9] = lambda: self.sbc(self.immediate())
        self.opcode_table[0xE5] = lambda: self.sbc(self.read(self.zero_page()))
        self.opcode_table[0xF5] = lambda: self.sbc(self.read(self.zero_page_x()))
        self.opcode_table[0xED] = lambda: self.sbc(self.read(self.absolute()))
        self.opcode_table[0xFD] = lambda: self.sbc(self.read(self.absolute_x()))
        self.opcode_table[0xF9] = lambda: self.sbc(self.read(self.absolute_y()))
        self.opcode_table[0xE1] = lambda: self.sbc(self.read(self.indexed_indirect()))
        self.opcode_table[0xF1] = lambda: self.sbc(self.read(self.indirect_indexed()))

        # logical AND with accumulator: AND
        self.opcode_table[0x29] = lambda: self.and_(self.immediate())
        self.opcode_table[0x25] = lambda: self.and_(self.read(self.zero_page()))
        self.opcode_table[0x35] = lambda: self.and_(self.read(self.zero_page_x()))
        self.opcode_table[0x2D] = lambda: self.and_(self.read(self.absolute()))
        self.opcode_table[0x3D] = lambda: self.and_(self.read(self.absolute_x()))
        self.opcode_table[0x39] = lambda: self.and_(self.read(self.absolute_y()))
        self.opcode_table[0x21] = lambda: self.and_(self.read(self.indexed_indirect()))
        self.opcode_table[0x31] = lambda: self.and_(self.read(self.indirect_indexed()))

        # Logical OR with accumulator: ORA
        self.opcode_table[0x09] = lambda: self.ora(self.immediate())
        self.opcode_table[0x05] = lambda: self.ora(self.read(self.zero_page()))
        self.opcode_table[0x15] = lambda: self.ora(self.read(self.zero_page_x()))
        self.opcode_table[0x0D] = lambda: self.ora(self.read(self.absolute()))
        self.opcode_table[0x1D] = lambda: self.ora(self.read(self.absolute_x()))
        self.opcode_table[0x19] = lambda: self.ora(self.read(self.absolute_y()))
        self.opcode_table[0x01] = lambda: self.ora(self.read(self.indexed_indirect()))
        self.opcode_table[0x11] = lambda: self.ora(self.read(self.indirect_indexed()))
        
        # exclusive OR with accumulator: EOR
        self.opcode_table[0x49] = lambda: self.eor(self.immediate())
        self.opcode_table[0x45] = lambda: self.eor(self.read(self.zero_page()))
        self.opcode_table[0x55] = lambda: self.eor(self.read(self.zero_page_x()))
        self.opcode_table[0x4D] = lambda: self.eor(self.read(self.absolute()))
        self.opcode_table[0x5D] = lambda: self.eor(self.read(self.absolute_x()))
        self.opcode_table[0x59] = lambda: self.eor(self.read(self.absolute_y()))
        self.opcode_table[0x41] = lambda: self.eor(self.read(self.indexed_indirect()))
        self.opcode_table[0x51] = lambda: self.eor(self.read(self.indirect_indexed()))

        # compare accumulator: CMP
        self.opcode_table[0xC9] = lambda: self.cmp(self.immediate())
        self.opcode_table[0xC5] = lambda: self.cmp(self.read(self.zero_page()))
        self.opcode_table[0xD5] = lambda: self.cmp(self.read(self.zero_page_x()))
        self.opcode_table[0xCD] = lambda: self.cmp(self.read(self.absolute()))
        self.opcode_table[0xDD] = lambda: self.cmp(self.read(self.absolute_x()))
        self.opcode_table[0xD9] = lambda: self.cmp(self.read(self.absolute_y()))
        self.opcode_table[0xC1] = lambda: self.cmp(self.read(self.indexed_indirect()))
        self.opcode_table[0xD1] = lambda: self.cmp(self.read(self.indirect_indexed()))

        # compare X register: CPX
        self.opcode_table[0xE0] = lambda: self.cpx(self.immediate())
        self.opcode_table[0xE4] = lambda: self.cpx(self.read(self.zero_page()))
        self.opcode_table[0xEC] = lambda: self.cpx(self.read(self.absolute()))

        # compare Y register: CPY
        self.opcode_table[0xC0] = lambda: self.cpy(self.immediate())
        self.opcode_table[0xC4] = lambda: self.cpy(self.read(self.zero_page()))
        self.opcode_table[0xCC] = lambda: self.cpy(self.read(self.absolute()))

        # increment memory: INC
        self.opcode_table[0xE6] = lambda: self.inc(self.zero_page())
        self.opcode_table[0xF6] = lambda: self.inc(self.zero_page_x())
        self.opcode_table[0xEE] = lambda: self.inc(self.absolute())
        self.opcode_table[0xFE] = lambda: self.inc(self.absolute_x())

        # increment X or Y register: INX, INY
        self.opcode_table[0xE8] = self.inx
        self.opcode_table[0xC8] = self.iny

        # decrement memory: DEC
        self.opcode_table[0xC6] = lambda: self.dec(self.zero_page())
        self.opcode_table[0xD6] = lambda: self.dec(self.zero_page_x())
        self.opcode_table[0xCE] = lambda: self.dec(self.absolute())
        self.opcode_table[0xDE] = lambda: self.dec(self.absolute_x())

        # decrement X or Y register: DEX, DEY
        self.opcode_table[0xCA] = self.dex
        self.opcode_table[0x88] = self.dey

        # arithmetic shift left: ASL
        self.opcode_table[0x0A] = lambda: self.asl()
        self.opcode_table[0x06] = lambda: self.asl(self.zero_page())
        self.opcode_table[0x16] = lambda: self.asl(self.zero_page_x())
        self.opcode_table[0x0E] = lambda: self.asl(self.absolute())
        self.opcode_table[0x1E] = lambda: self.asl(self.absolute_x())

        # logical shift right: LSR
        self.opcode_table[0x4A] = lambda: self.lsr()
        self.opcode_table[0x46] = lambda: self.lsr(self.zero_page())
        self.opcode_table[0x56] = lambda: self.lsr(self.zero_page_x())
        self.opcode_table[0x4E] = lambda: self.lsr(self.absolute())
        self.opcode_table[0x5E] = lambda: self.lsr(self.absolute_x())

        # rotate left: ROL
        self.opcode_table[0x2A] = lambda: self.rol()
        self.opcode_table[0x26] = lambda: self.rol(self.zero_page())
        self.opcode_table[0x36] = lambda: self.rol(self.zero_page_x())
        self.opcode_table[0x2E] = lambda: self.rol(self.absolute())
        self.opcode_table[0x3E] = lambda: self.rol(self.absolute_x())

        # rotate right: ROR
        self.opcode_table[0x6A] = lambda: self.ror()
        self.opcode_table[0x66] = lambda: self.ror(self.zero_page())
        self.opcode_table[0x76] = lambda: self.ror(self.zero_page_x())
        self.opcode_table[0x6E] = lambda: self.ror(self.absolute())
        self.opcode_table[0x7E] = lambda: self.ror(self.absolute_x())

        # bit test: BIT
        self.opcode_table[0x89] = lambda: self.bit(self.immediate())
        self.opcode_table[0x24] = lambda: self.bit(self.read(self.zero_page()))
        self.opcode_table[0x2C] = lambda: self.bit(self.read(self.absolute()))

        # jump to address: JMP
        self.opcode_table[0x4C] = lambda: self.jmp(self.absolute())
        self.opcode_table[0x6C] = lambda: self.jmp(self.indirect())

        # jump to subroutine: JSR, return from Subroutine: RTS, return from Interrupt: RTI, break: BRK
        self.opcode_table[0x20] = lambda: self.jsr(self.absolute())
        self.opcode_table[0x60] = self.rts
        self.opcode_table[0x40] = self.rti
        self.opcode_table[0x00] = self.brk

        # no operation: NOP
        self.opcode_table[0xEA] = self.nop

        # clear carry flag: CLC, set carry flag: SEC, clear interrupt disable flag: CLI, set interrupt disable flag: SEI, clear overflow flag: CLV, clear decimal mode: CLD, set decimal mode: SED
        self.opcode_table[0x18] = self.clc
        self.opcode_table[0x38] = self.sec
        self.opcode_table[0x58] = self.cli
        self.opcode_table[0x78] = self.sei
        self.opcode_table[0xB8] = self.clv
        self.opcode_table[0xD8] = self.cld
        self.opcode_table[0xF8] = self.sed

        # branch instructions: BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS
        self.opcode_table[0x90] = lambda: self.branch(not self.get_flag(Flag.C))  # BCC: branch if carry clear
        self.opcode_table[0xB0] = lambda: self.branch(self.get_flag(Flag.C))      # BCS: branch if carry set
        self.opcode_table[0xF0] = lambda: self.branch(self.get_flag(Flag.Z))      # BEQ: branch if equal (zero flag set)
        self.opcode_table[0x30] = lambda: self.branch(self.get_flag(Flag.N))      # BMI: branch if minus (negative flag set)
        self.opcode_table[0xD0] = lambda: self.branch(not self.get_flag(Flag.Z))  # BNE: branch if not equal (zero flag clear)
        self.opcode_table[0x10] = lambda: self.branch(not self.get_flag(Flag.N))  # BPL: branch if plus (negative flag clear)
        self.opcode_table[0x50] = lambda: self.branch(not self.get_flag(Flag.V))  # BVC: branch if overflow clear
        self.opcode_table[0x70] = lambda: self.branch(self.get_flag(Flag.V))      # BVS: branch if overflow set

    # --- CPU step ---
    def step(self):
        """execute a single CPU instruction."""
        opcode = self.read(self.PC)
        self.PC += 1
        handler = self.opcode_table[opcode]

        if handler is not None:
            handler()

        else:
            raise NotImplementedError(f"Warning: Unimplemented opcode 0x{opcode:02X} at address 0x{self.PC - 1:04X}")

    # --- run for n instructions ---
    def run(self, n):
        """run the CPU for n instructions."""
        for _ in range(n):
            if self.read(self.PC) != 0x00: self.step()