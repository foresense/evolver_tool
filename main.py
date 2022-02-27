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


def ms_split(parameter: int) -> tuple:
    pass


def pack(data: tuple) -> tuple:
    pass



def unpack(packed):
    """unpack 8 7-bit bytes into 7 8-bit bytes"""

    byte, out = packed[0], packed[1:]

    for n, val in enumerate(out):

        pass


test_input = [0xC0, 0xA0, 0x90, 0x88, 0x82, 0x84, 0x82]
test_packed = pack(test_input)  # [64, 32, 16, 8, 2, 4, 2, 0]

midi_in = mido.open_input('MidiKliK 1')
midi_out = mido.open_output('MidiKliK 2')

dump_in = mido.Message(type='sysex', data=(1, 32, 1, 2, 1, 20, 0, 36, 45, 1, 100, 48, 80, 1, 0, 100, 24, 50, 0, 33, 36, 50, 0, 0, 33, 88, 117, 0, 33, 50, 0, 33, 0, 0, 0, 100, 0, 23, 0, 50, 67, 0, 100, 0, 33, 0, 0, 112, 33, 100, 0, 0, 3, 0, 0, 7, 31, 80, 1, 23, 20, 99, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 2, 3, 12, 0, 100, 0, 0, 6, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 3, 4, 0, 0, 0, 2, 4, 0, 1, 0, 27, 0, 0, 0, 4, 111, 20, 0, 0, 0, 64, 99, 0, 0, 99, 0, 3, 70, 0, 4, 33, 0, 0, 0, 108, 9, 0, 0, 50, 39, 23, 0, 0, 0, 0, 0, 0, 99, 0, 116, 10, 99, 0, 0, 99, 0, 99, 0, 99, 0, 0, 99, 0, 96, 0, 0, 68, 0, 0, 0, 74, 73, 96, 0, 0, 74, 0, 0, 86, 68, 72, 62, 24, 38, 0, 0, 0, 48, 32, 101, 62, 64, 0, 58, 45, 44, 43, 101, 50, 48, 0, 0, 0, 32, 0, 0, 24, 16, 0, 54, 24, 10, 32, 0, 16, 48, 0, 40, 38, 24, 16, 17, 18, 19, 0, 20, 21, 24, 28, 18, 16, 101, 0, 0, 0, 0))
