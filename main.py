import mido


# Evolver Sysex id

SYSEX_ID = (0x01, 0x20, 0x01)

PROG_PAR = 0x01
SEQ_PAR = 0x08
MAIN_PAR = 0x09

PROG_DUMP = 0x02
EDIT_DUMP = 0x03
WAVE_DUMP = 0x0A
MAIN_DUMP = 0x0F
NAME_DUMP = 0x11

PROG_REQ = 0x05
EDIT_REQ = 0x06
WAVE_REQ = 0x0B

RESET = 0x04
START_STOP = 0x12
SHIFT_ON = 0x13
SHIFT_OFF = 0x14


def pack(input: list) -> list:

    # pack input should be 7, or maybe we can figure something out something else

    eight = 0
    output = []

    for index, value in enumerate(input):
        hi, lo = divmod(value, 128)
        eight = hi << index | eight
        output.append(lo)
        # print(f"{bin(value)} -> {hi:1b} | {lo:08b} -> add: {[eight]} + {output}")

    # print(f"{[eight] + output}")

    return [eight] + output


def unpack(packed: tuple) -> tuple:
    
    output = []

    return unpacked


# test
p = pack([0xC0, 0xA0, 0x90, 0x88, 0x82, 0x84, 0x82])
