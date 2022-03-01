from queue import Queue
from threading import Thread
from time import sleep

import mido


OUT_SPEED = 1 / 10         # 10 messages per second out rate

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
MAIN_REQ = 0x0E
NAME_REQ = 0x10

RESET = 0x04
START_STOP = 0x12
SHIFT_ON = 0x13
SHIFT_OFF = 0x14


# TODO dictionary for memory

main_parameters = (
    "program", "bank", "volume", "transpose", "bpm", "clock_div", "program_tempo", "midi_clock",
    "lock_seq", "poly_chain", "input_gain", "fine_tune", "midi_rec", "midi_xmit", "midi_chan", "midi_dump"
)

#program_number = None
#bank_number = None

queue_out = Queue(maxsize=128)

main_memory = {}
edit_memory = {}


def pack1111(parameters: list) -> list:
    byte = 0
    out = []
    for n, val in enumerate(parameters):
        high, low = divmod(val, 1 << 7)
        byte = byte | high << n
        out.append(low)
        # print(f"{high=} {low=}, {bin(byte)=}, {n=}")
    return [byte] + out


def pack_data(data: dict) -> list:
    packed = [0]
    for val in reversed(data):
        packed[0] = packed[0] << 1 | val >> 7
        packed.append(val & 0x7f)
    return packed


def unpack_data(packed: tuple):
   
    if packed[0] not in (PROG_PAR, SEQ_PAR, MAIN_PAR, PROG_DUMP, EDIT_DUMP, WAVE_DUMP, MAIN_DUMP, NAME_DUMP):
        print(f"what? {packed}")
    # alternate LS then MS byte
    if packed[0] == MAIN_DUMP:
        print(f"{len(packed[1:]} bytes: packed[1:]))
        for n in packed[1:]:
            pass
            # TODO algorithm that makes LS, MS pairs into one byte

    # TODO algorithm that unpacks 7 bit into 8 bits and then into a dictionary


def queue_message(data: list) -> mido.Message:
    queue_out.put(mido.Message(type='sysex', data=(*SYSEX_ID, *data)))


def midi_in_callback(message: mido.Message):
    if message.type == 'program_change':
        # print(f"program number: {message.program + 1}")
        main_memory.update({"program_number": message.program})
        queue_message([EDIT_REQ])
    
    elif message.type == 'control_change' and message.control == 32:
        # print(f"bank number: {m.value + 1}")
        main_memory.update({"bank_number": message.value})
        queue_message([EDIT_REQ])
    
    elif message.type == 'sysex' and message.data[:3] == SYSEX_ID:
        data = unpack_data(message.data[3:])
    
    else:
        print(message.data)
        


def queue_out_thread():
    while(not midi_out.closed):
        if not queue_out.empty():
            midi_out.send(queue_out.get())
            queue_out.task_done()
        sleep(OUT_SPEED)
    print("bye!")


if __name__ == "__main__":
    midi_in = mido.open_input('MidiKliK 1', callback=midi_in_callback)
    midi_out = mido.open_output('MidiKliK 2')

    t = Thread(target=queue_out_thread)
    t.start()

    queue_message([MAIN_REQ])
