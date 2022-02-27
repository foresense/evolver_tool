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


def pack(parameters: list) -> list:
    """pack 7x 8-bit bytes into 8x 7-bit bytes"""

    byte = 0
    out = []

    for n, val in enumerate(parameters):
        high, low = divmod(val, 1 << 7)
        byte = byte | high << n
        out.append(low)
        # print(f"{high=} {low=}, {bin(byte)=}, {n=}")

    return [byte] + out


def unpack(packed):
    """unpack 8 7-bit bytes into 7 8-bit bytes"""

    bits, bytes = packed[0], packed[1:]

    bitlist = bits




test_input = [0xC0, 0xA0, 0x90, 0x88, 0x82, 0x84, 0x82]
test_packed = pack(test_input)  # [64, 32, 16, 8, 2, 4, 2, 0]
