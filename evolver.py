import json
#import yaml
import logging
import wave

from queue import Queue
from threading import Thread
from time import sleep
from enum import IntEnum

import mido
from mido import Message

import parameters


log = logging.getLogger("evolver")
log_format = logging.Formatter("[%(asctime)s %(levelname)s] %(message)s")
log_format.datefmt = "%Y.%m.%d %H:%M:%S"
log_stdout = logging.StreamHandler()
log_stdout.setFormatter(log_format)
log.addHandler(log_stdout)
log.setLevel(logging.DEBUG)


MIDI_IN = "MidiKliK 1"
MIDI_OUT = "MidiKliK 2"

OUT_SPEED = 1 / 10

# OLD WAY
EVOLVER_ID = 0x01, 0x20, 0x01
# NEW WAY
SYSEX_ID = 0x01, 0x20, 0x01


class CC(IntEnum):
    MODWHEEL = 0x01
    BANK_CHANGE = 0x20


class Parameter(IntEnum):
    PROGRAM = 0x01
    SEQUENCER = 0x08
    MAIN = 0x09


class Dump(IntEnum):
    PROGRAM = 0x02
    EDIT = 0x03
    WAVESHAPE = 0x0A
    MAIN = 0x0F
    NAME = 0x11


# TODO change class name
class DumpLength(IntEnum):
    PROGRAM = 220
    WAVESHAPE = 293
    MAIN = 32
    NAME = 16


class Request(IntEnum):
    PROGRAM = 0x05
    EDIT = 0x06
    WAVESHAPE = 0x0B
    MAIN = 0x0E
    NAME = 0x10


class Command(IntEnum):
    RESET = 0x04
    START_STOP = 0x12
    SHIFT_ON = 0x13
    SHIFT_OFF = 0x14


memory = {
    "main": {parameters.main[n]: 0 for n in range(16)},
    "edit": {parameters.program[n]: 0 for n in range(128)},
    "patch": {b: {p: {parameters.program[n]: 0 for n in range(128)} for p in range(128)} for b in range(4)},
    "waveshape": {w: bytes(256) for w in range(128)},
    "name": {b: {p: "unknown         " for p in range(128)} for b in range(4)}
}

# TODO main and edit should be a dataclass


queue_out = Queue(maxsize=2048)


def encode_ls_ms(b: int) -> tuple:
    return b & 0xF, b >> 4


def decode_ls_ms(ls: int, ms: int) -> int:
    return ls | ms << 4


def encode_string(name: str) -> list:
    if len(name) in range(17):
        return [ord(c) for c in name] + [ord(" ") for n in range(16 - len(name))]
    else:
        raise OverflowError("[ERROR]: string too long (16 characters maximum)")


def unpack_ls_ms(data: tuple) -> tuple:
    i = iter(data)
    return tuple(ls | ms << 4 for (ls, ms) in zip(i, i))


def unpack_str(data: tuple) -> str:
    return bytes(data).decode(encoding="ascii")


def pack_ms_bit(data: list) -> tuple:
    packed_data = []
    count = 0
    for n, byte in enumerate(data):
        count, cycle = divmod(n, 7)
        ms_bit = byte >> 7
        # growing from 7 bytes to 8 bytes per cycle
        ms_bits_index = n + count - cycle
        if cycle == 0:
            # cycle starts with ms_bit_byte is 8th byte
            packed_data.append(ms_bit)
            packed_data.append(byte & 0x7F)
        else:
            packed_data.append(byte & 0x7F)
            packed_data[ms_bits_index] = packed_data[ms_bits_index] | (ms_bit << cycle)
    return tuple(packed_data)


def unpack_ms_bit(packed_data: tuple) -> list:
    data = []
    for n, byte in enumerate(packed_data):
        cycle = n % 8
        if cycle == 0:
            ms_bits = byte
        else:
            if ms_bits & (1 << (cycle - 1)):
                data.append(byte | 0x80)
            else:
                data.append(byte)
    return data


def save_json(filename: str, memory_dict: dict = memory.get("edit")):
    with open(filename, "w") as file:
        json.dump(memory_dict, file, indent=2)


def load_json(filename: str) -> dict:
    with open(filename, "r") as file:
        return json.load(file)


def save_sysex(filename: str, memory_dict: dict = memory.get("edit")):
    # TODO serialize output and write valid sysex strings
    # mido.write_syx_file(filename)
    # file.write(Message(type='sysex', data=(*SYSEX_ID, *pdata)).bytes())
    pass


def load_sysex(filename: str) -> dict:
    # sysex_stream = mido.read_syx_file(filename)
    # TODO deserialize sysex, first chop it in parts
    #      then put it through receive message
    pass


def save_waveshape(filename: str, n: int):
    with wave.open(filename, "wb") as wavefile:
        wavefile.setnchannels(1)
        wavefile.setframerate(44100)
        wavefile.setsampwidth(2)
        wavefile.setnframes(128)
        wavefile.writeframes(memory["waveshape"][n])


def load_waveshape(filename: str) -> dict:
    # TODO load from standard pcm .wav
    with wave.open(filename, "rb") as wavefile:
        pass


def program_change(bank: int = None, program: int = None):
    if bank in range(4):
        memory.get("main").update({"bank": bank})
        queue_out.put(Message(type="control_change", control=CC.BANK_CHANGE, value=bank))
    if program in range(128):
        memory.get("main").update({"program": program})
        queue_out.put(Message(type="program_change", program=program))


def serialize_program(program: dict) -> list:
    data = []
    for parameter in parameters.program:
        data.append(program.get(parameter))
    data.extend(program.get("seq"))    
    return pack_ms_bit(data)


def serialize_main(main: dict) -> list:
    data = []
    for parameter in parameters.main:
        data.extend(encode_ls_ms(main.get(parameter)))
    return data


def serialize_waveshape(waveshape: list) -> list:
    data = []
    for point in waveshape:
        data.append(point & 0xFF)
        data.append(point >> 8)
    return pack_ms_bit(data)


def serialize(data: list) -> tuple:
    match data:
        case [Dump.PROGRAM, bank, program]:
            return Dump.PROGRAM.value, bank, program, *serialize_program(memory.get("edit"))
        case [Dump.PROGRAM, bank, program, *dump] if len(dump) == DumpLength.PROGRAM:
            return Dump.PROGRAM.value, bank, program, *dump
        case [Dump.EDIT, *dump] if len(dump) == DumpLength.PROGRAM:
            return Dump.EDIT.value, *dump
        case [Dump.WAVESHAPE, n, *dump] if len(dump) == DumpLength.WAVESHAPE:
            return Dump.WAVESHAPE.value, n, *dump
        case [Dump.MAIN, *dump] if len(dump) == DumpLength.MAIN:
            return Dump.MAIN.value, *dump
        case [Dump.NAME, bank, program, *dump] if len(dump) == DumpLength.NAME:
            return Dump.NAME.value, bank, program, *dump
        case [Dump.NAME, *dump] if len(dump) == DumpLength.NAME:
            return Dump.NAME.value, memory["main"]["bank"], memory["main"]["program"], *dump
        case [Request.PROGRAM, bank, program]:
            return Request.PROGRAM.value, bank, program
        case [Request.PROGRAM]:
            return Request.PROGRAM.value, memory["main"]["bank"], memory["main"]["program"]
        case [Request.EDIT]:
            return Request.EDIT.value,
        case [Request.WAVESHAPE, n]:
            return Request.WAVESHAPE.value, n
        case [Request.MAIN]:
            return Request.MAIN.value,
        case [Request.NAME, bank, program]:
            return Request.NAME.value, bank, program
        case [Request.NAME]:
            return Request.NAME.value, memory["main"]["bank"], memory["main"]["program"]
        case [Parameter.PROGRAM, par, val]:
            return Parameter.PROGRAM.value, parameters.program[par], *encode_ls_ms(val)
        case _:
            log.warning(f"unknown command: {data=}")
            return None


def queue_message(*data: list):
    queue_out.put(Message(type="sysex", data=(*EVOLVER_ID, *serialize(data))))


def assemble(data: tuple) -> dict | list:
    match len(data):
        case DumpLength.PROGRAM:
            data = unpack_ms_bit(data)
            d = {parameters.program[n]: val for n, val in enumerate(data[:128])}
            d.update({"seq": list(data[128:])})
        case DumpLength.MAIN:
            d = {parameters.main[n]: val for n, val in enumerate(unpack_ls_ms(data))}
        case DumpLength.WAVESHAPE:
            d = unpack_ms_bit(data)
        case DumpLength.NAME:
            d = bytes(data).decode(encoding="ascii")
    return d


def receive_sysex(data: tuple):
    global memory
    match data:
        case [Dump.PROGRAM, bank, program, *dump]:
            memory.get("prog").get(bank).get(program).update(assemble(dump))
        case [Dump.EDIT, *dump]:
            memory.get("edit").update(assemble(dump))
        case [Dump.WAVESHAPE, wave, *dump]:
            memory.get("wave").update({wave: assemble(dump)})
        case [Dump.MAIN, *dump]:
            memory.get("main").update(assemble(dump))
        case [Dump.NAME, bank, program, *dump]:
            memory.get("name").get(bank).get(program).update(assemble(dump))
        case [Parameter.PROGRAM, parameter, ls, ms]:
            memory["edit"].update({parameters.program[parameter]: decode_ls_ms(ls, ms)})
        case [Parameter.SEQUENCER, step, ls, ms]:
            memory.get("edit").get("seq")[step] = decode_ls_ms(ls, ms)
        case [Parameter.MAIN, parameter, ls, ms]:
            memory["main"].update({parameters.main[parameter]: decode_ls_ms(ls, ms)})
        case _:
            log.warning(f"received unknown: {data=}")


def midi_in_callback(message: Message):
    global memory
    match message:
        case Message(type="program_change"):
            memory.get("main").update({"program": message.program})
        case Message(type="control_change", control=CC.BANK_CHANGE):
            memory.get("main").update({"bank": message.value})
        case Message(type="sysex") if message.data[:3] == EVOLVER_ID:
            receive_sysex(message.data[3:])
        case _:
            log.warning(f"received unknown: {message}")


def queue_out_thread():
    global memory
    bank = None
    program = None
    queue_message(Request.MAIN)
    while not midi_out.closed:
        if bank != memory.get("main").get("bank") or program != memory.get("main").get("program"):
            bank = memory.get("main").get("bank")
            program = memory.get("main").get("program")
            log.info(f"program change -> {bank=} {program=}")
            queue_message(Request.EDIT)
            memory["patch"][bank][program].update(memory.get("edit"))
        if not queue_out.empty():
            message = queue_out.get()
            midi_out.send(message)
            queue_out.task_done()
            log.info(f"sent {message}")
        sleep(OUT_SPEED)


if __name__ == "__main__":
    if MIDI_IN in mido.get_input_names():
        midi_in = mido.open_input(MIDI_IN, callback=midi_in_callback)
    else:
        raise ValueError(f"No such port: {MIDI_IN=}")

    if MIDI_OUT in mido.get_output_names():
        midi_out = mido.open_output(MIDI_OUT)
    else:
        raise ValueError(f"No such port: {MIDI_OUT=}")

    qot = Thread(target=queue_out_thread)
    qot.start()
