from enum import IntEnum

class AddrType(IntEnum):
    """the addressing modes that can be used in this instruction set."""
    IMM = 1
    ZP = 2
    ZPX = 3
    ZPY = 4
    ABS = 5
    ABSX = 6
    ABSY = 7
    INDX = 8
    INDY = 9
    LABEL = 10
    BYTE = 11
    ACC = 12
    IMPLIED = 13
    IND = 14
    REL = 15