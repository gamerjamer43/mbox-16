from .opcodes import OPCODES
from .addrtype import AddrType
from re import match

class Assembler:
    def __init__(self, origin=0xA000):
        """initialize the assembler with an origin address."""
        # init labels, output, and a private lines list
        self.labels = {}
        self.output = bytearray()
        self._lines = []

        # address where the assembled code starts loading
        self.origin = origin
        self.pc = origin


    def parse_operand(self, operand, mnemonic=None):
        """parse an operand and return its addressing type and value."""
        operand = operand.strip()

        # immediate
        if operand.startswith('#'):
            value = operand[1:]
            return AddrType.IMM, value

        # indirect,X
        if operand.startswith('(') and operand.endswith(',X)'):
            value = operand[1:-3]
            return AddrType.INDX, value

        # (indirect),Y
        if operand.startswith('(') and operand.endswith('),Y'):
            value = operand[1:-3]
            return AddrType.INDY, value

        # indirect JMP
        if operand.startswith('(') and operand.endswith(')'):
            value = operand[1:-1]
            return AddrType.IND, value

        # absolute,X
        if operand.endswith(',X'):
            value = operand[:-2]
            if value.startswith('$') or value.isdigit() or value.isidentifier():
                return AddrType.ABSX, value.strip()

        # absolute,Y
        if operand.endswith(',Y'):
            value = operand[:-2]
            if value.startswith('$') or value.isdigit() or value.isidentifier():
                return AddrType.ABSY, value.strip()

        # zero page,X
        if operand.endswith(',X'):
            value = operand[:-2]
            if value.startswith('$') and len(value) <= 3:
                return AddrType.ZPX, value.strip()

        # zero page,Y
        if operand.endswith(',Y'):
            value = operand[:-2]
            if value.startswith('$') and len(value) <= 3:
                return AddrType.ZPY, value.strip()

        # accumulator
        if operand.upper() == 'A':
            return AddrType.ACC, None

        # implied
        if operand == '':
            return AddrType.IMPLIED, None

        # branch instructions
        branch_mnemonics = {
            'BCC', 'BCS', 'BEQ', 'BMI', 'BNE', 'BPL', 'BVC', 'BVS'
        }
        if mnemonic in branch_mnemonics and operand.isidentifier():
            return AddrType.REL, operand

        # absolute or zero page
        if operand.startswith('$'):
            if len(operand) <= 3:
                return AddrType.ZP, operand
            else:
                return AddrType.ABS, operand

        # decimal
        if operand.isdigit():
            val = int(operand)
            if val < 0x100:
                return AddrType.ZP, operand
            else:
                return AddrType.ABS, operand

        # label expressions like LABEL+1 or LABEL-1
        expr_match = match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*([\+\-])\s*(\d+)$', operand)
        if expr_match:
            # We don't know the value yet, so treat as ABS for now
            return AddrType.ABS, operand

        # label (for all other cases)
        if operand.isidentifier():
            return AddrType.ABS, operand

        # fallback
        return AddrType.BYTE, operand


    def parse_line(self, line):
        """parse a single line of assembly code and return its type and content."""
        # remove comments
        line = line.split(';', 1)[0].strip()
        if not line:
            return None
        
        # label
        if line.endswith(':'):
            return ('label', line[:-1].strip())
        lower = line.lower()

        # .org directive
        if lower.startswith('.org'):
            val_str = line.split()[1]
            value = int(val_str[1:], 16) if val_str.startswith('$') else int(val_str, 0)
            return ('org', value)

        # .word directive
        if lower.startswith('.word'):
            args = line.split(None, 1)[1]
            return ('word', [a.strip() for a in args.split(',')])
        
        # .byte directive
        if lower.startswith('.byte'):
            args = line.split(None, 1)[1]
            return ('byte', [a.strip() for a in args.split(',')])
        
        # .res directive
        if lower.startswith('.res'):
            arg = line.split(None, 1)[1].strip()
            return ('res', int(arg))
        
        # .string and .stringz directives
        if lower.startswith('.stringz'):
            # Null-terminated string
            arg = line.split(None, 1)[1].strip()
            return ('string', arg, True)
        
        if lower.startswith('.string'):
            arg = line.split(None, 1)[1].strip()
            return ('string', arg, False)
        
        # instruction
        m = match(r'^([A-Za-z]{2,3})(?:\s+(.*))?$', line)
        if m:
            mnemonic = m.group(1).upper()
            operand = m.group(2) or ''
            return ('instr', mnemonic, operand.strip())
        
        return None


    def first_pass(self, lines):
        """first pass to collect labels and calculate program counter."""
        self.pc = self.origin
        for line in lines:
            code = line.split(';', 1)[0].strip()

            if ':' in code:
                lbl, rest = code.split(':', 1)
                lbl = lbl.strip()
                self.labels[lbl] = self.pc
                self._lines.append((lbl + ':', ('label', lbl)))

                if rest.strip():
                    parsed_rest = self.parse_line(rest)

                    if parsed_rest:
                        kind = parsed_rest[0]

                        if kind == 'org':
                            self.pc = parsed_rest[1]

                        elif kind == 'word':
                            self.pc += 2 * len(parsed_rest[1])

                        elif kind == 'byte':
                            self.pc += len(parsed_rest[1])

                        elif kind == 'res':
                            self.pc += parsed_rest[1]

                        elif kind == 'instr':
                            mnem, op = parsed_rest[1], parsed_rest[2]
                            at, _ = self.parse_operand(op, mnem)
                            self.pc += self.instr_size(at)
                        self._lines.append((rest, parsed_rest))
                continue

            parsed = self.parse_line(line)
            if not parsed:
                continue
            kind = parsed[0]
            
            if kind == 'label':
                self.labels[parsed[1]] = self.pc

            elif kind == 'org':
                self.pc = parsed[1]

            elif kind == 'word':
                self.pc += 2 * len(parsed[1])
                
            elif kind == 'byte':
                self.pc += len(parsed[1])

            elif kind == 'res':
                self.pc += parsed[1]

            elif kind == 'instr':
                mnem, op = parsed[1], parsed[2]
                at, _ = self.parse_operand(op, mnem)
                self.pc += self.instr_size(at)

            elif kind == 'string':
                s = parsed[1]
                if s.startswith('"') and s.endswith('"'):
                    slen = len(eval(s))

                else:
                    slen = len(s)

                if parsed[2]:
                    slen += 1

                self.pc += slen
            self._lines.append((line, parsed))


    def instr_size(self, addrtype):
        """return the size of the instruction based on its addressing mode."""
        # instruction size by addressing mode
        if addrtype in (AddrType.IMPLIED, AddrType.ACC):
            return 1
        
        if addrtype == AddrType.IMM:
            return 2
        
        if addrtype in (AddrType.ZP, AddrType.ZPX, AddrType.ZPY, AddrType.INDX, AddrType.INDY, AddrType.REL):
            return 2
        
        if addrtype in (AddrType.ABS, AddrType.ABSX, AddrType.ABSY, AddrType.IND):
            return 3
        
        if addrtype == AddrType.BYTE:
            return 1
        return 1


    def second_pass(self):
        """second pass to generate the binary output."""
        # preallocate a buffer covering addresses from self.origin to 0x10000
        SIZE = 0x10000 - self.origin
        self.output = bytearray(SIZE)
        self.pc = self.origin
        max_written = 0

        for line, parsed in self._lines:
            if not parsed: continue
            kind = parsed[0]

            if kind == 'label':
                continue

            elif kind == 'org':
                self.pc = parsed[1]

            elif kind == 'word':
                for val in parsed[1]:
                    addr_val = self.resolve_value(val)
                    offset = self.pc - self.origin
                    self.output[offset:offset+2] = bytes([addr_val & 0xFF, (addr_val >> 8) & 0xFF])
                    max_written = max(max_written, offset+2)
                    self.pc += 2

            elif kind == 'byte':
                for val in parsed[1]:
                    b = self.resolve_value(val) & 0xFF
                    offset = self.pc - self.origin
                    self.output[offset] = b
                    max_written = max(max_written, offset+1)
                    self.pc += 1

            elif kind == 'res':
                self.pc += parsed[1]

            elif kind == 'instr':
                mnem, op = parsed[1], parsed[2]
                at, value = self.parse_operand(op, mnem)
                opcode, ops = self.encode_instr(mnem, at, value, self.pc)
                offset = self.pc - self.origin
                self.output[offset] = opcode
                self.output[offset+1:offset+1+len(ops)] = ops
                max_written = max(max_written, offset+1+len(ops))
                self.pc += 1 + len(ops)

            elif kind == 'string':
                s = parsed[1]
                nullterm = parsed[2]
                if s.startswith('"') and s.endswith('"'):
                    bytestr = bytes(s[1:-1], "utf-8").decode("unicode_escape").encode("ascii")

                else:
                    bytestr = s.encode('ascii')

                offset = self.pc - self.origin
                self.output[offset:offset+len(bytestr)] = bytestr
                max_written = max(max_written, offset+len(bytestr))
                self.pc += len(bytestr)

                if nullterm:
                    offset = self.pc - self.origin
                    self.output[offset] = 0
                    max_written = max(max_written, offset+1)
                    self.pc += 1

        # return the buffer up to the highest address written or the final PC offset, whichever is larger.
        end = max(self.pc - self.origin, max_written)
        return self.output[:end]


    def resolve_value(self, val):
        """resolve a value to its numeric representation."""
        val = val.strip()
        # handle character literals enclosed in single quotes
        if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
            return ord(val[1:-1])

        # handle operands with indexing, e.g., "LABEL,X" or "LABEL,Y"
        if isinstance(val, str) and ',' in val:
            base, reg = val.split(',')
            return self.resolve_value(base.strip())

        # handle expressions like LABEL+1 or LABEL-1
        expr_match = match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*([\+\-])\s*(\d+)$', val)
        if expr_match:
            base_label = expr_match.group(1)
            op = expr_match.group(2)
            offset = int(expr_match.group(3))
            if base_label in self.labels:
                base_addr = self.labels[base_label]
                if op == '+':
                    return base_addr + offset
                else:
                    return base_addr - offset
            else:
                raise ValueError(f"Unknown label in expression: {val}")

        if val.startswith('$'):
            return int(val[1:], 16)

        elif val.isdigit():
            return int(val)

        elif val in self.labels:
            return self.labels[val]

        # if value is a number literal or label, resolve it here.
        raise ValueError(f"Unknown value: {val}")


    def encode_instr(self, mnemonic, addrtype, value, pc):
        """encode an instruction into its opcode and operand bytes."""
        # map mnemonic + addressing mode to opcode
        key = None
        operand_bytes = b''

        if addrtype == AddrType.IMM:
            key = f"{mnemonic}_IMM"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.ZP:
            key = f"{mnemonic}_ZP"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.ZPX:
            key = f"{mnemonic}_ZPX"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.ZPY:
            key = f"{mnemonic}_ZPY"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.ABS:
            key = f"{mnemonic}_ABS"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF, (v >> 8) & 0xFF])

        elif addrtype == AddrType.ABSX:
            key = f"{mnemonic}_ABSX"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF, (v >> 8) & 0xFF])

        elif addrtype == AddrType.ABSY:
            key = f"{mnemonic}_ABSY"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF, (v >> 8) & 0xFF])

        elif addrtype == AddrType.IND:
            key = f"{mnemonic}_IND"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF, (v >> 8) & 0xFF])

        elif addrtype == AddrType.INDX:
            key = f"{mnemonic}_INDX"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.INDY:
            key = f"{mnemonic}_INDY"
            v = self.resolve_value(value)
            operand_bytes = bytes([v & 0xFF])

        elif addrtype == AddrType.ACC:
            key = f"{mnemonic}_ACC"

        elif addrtype == AddrType.IMPLIED:
            key = mnemonic

        elif addrtype == AddrType.REL:
            key = mnemonic
            if value in self.labels:
                target = self.labels[value]
                offset = (target - (pc + 2)) & 0xFF
                operand_bytes = bytes([offset])

            else:
                raise ValueError(f"Unknown branch label: {value}")
            
        elif addrtype == AddrType.BYTE:
            key = mnemonic

        else:
            raise ValueError(f"Unknown addressing mode for {mnemonic} {value}")
        
        if key not in OPCODES:
            raise ValueError(f"Opcode not found for line: {key} {value}")
        
        opcode = OPCODES[key]
        return opcode, operand_bytes


    def assemble(self, text):
        """assemble the provided assembly code text into binary."""
        # split lines and make two passes
        lines = text.splitlines()
        self.first_pass(lines)
        return self.second_pass()