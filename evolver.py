# evolver.py
# sysex translation engine
# 

import json
import wave
from enum import IntEnum

from mido import Message

import utils
import parameters


log = utils.get_logger("evolver")
log.setLevel(20)


sysex_id = 0x01, 0x20, 0x01


class CC(IntEnum):
    MODWHEEL = 0x01
    BANK_CHANGE = 0x20


class Parameter(IntEnum):
    PROGRAM = 0x01
    SEQUENCER = 0x08
    MAIN = 0x09


class Partition(IntEnum):
    PROGRAM = 0x02
    EDIT = 0x03
    WAVESHAPE = 0x0A
    MAIN = 0x0F
    NAME = 0x11


class Length(IntEnum):
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



def program_change(bank: int = None, program: int = None):
    if bank in range(4):
        # memory.get("main").update({"bank": bank})
        # queue_out.put(Message(type="control_change", control=CC.BANK_CHANGE, value=bank))
        pass

    if program in range(128):
        # memory.get("main").update({"program": program})
        # queue_out.put(Message(type="program_change", program=program))
        pass


def serialize_program(program: dict) -> list:
    data = []
    for parameter in parameters.program:
        data.append(program.get(parameter))
    data.extend(program.get("seq"))    
    return utils.pack_msbit(data)


def serialize_main(main: dict) -> list:
    data = []
    for parameter in parameters.main:
        data.extend(utils.encode_nibble(main.get(parameter)))
    return data


def serialize_waveshape(waveshape: list) -> list:
    data = []
    for point in waveshape:
        data.append(point & 0xFF)
        data.append(point >> 8)
    return utils.pack_msbit(data)


def serialize(data: list) -> tuple:
    match data:
        case [Partition.PROGRAM, bank, program]:
            return bytes([Partition.PROGRAM.value, bank, program, *serialize_program(memory.get("edit"))])
        case [Partition.PROGRAM, bank, prog, *part] if len(part) == Length.PROGRAM:
            return Partition.PROGRAM.value, bank, prog, *part
        case [Partition.EDIT, *part] if len(part) == Length.PROGRAM:
            return Partition.EDIT.value, *part
        case [Partition.WAVESHAPE, n, *part] if len(part) == Length.WAVESHAPE:
            return Partition.WAVESHAPE.value, n, *part
        case [Partition.MAIN, *part] if len(part) == Length.MAIN:
            return Partition.MAIN.value, *part
        case [Partition.NAME, bank, program, *part] if len(part) == Length.NAME:
            return Partition.NAME.value, bank, program, *part
        case [Partition.NAME, *part] if len(part) == Length.NAME:
            return Partition.NAME.value, memory["main"]["bank"], memory["main"]["program"], *part
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
            return Parameter.PROGRAM.value, parameters.program[par], *utils.encode_nibble(val)
        case _:
            log.warning(f"unknown command: {data=}")
            return None

# TODO WHAT

#def queue_message(*data: list):
#    queue_out.put(Message(type="sysex", data=(*EVOLVER_ID, *serialize(data))))


def assemble(data: bytes) -> dict | list:
    match len(data):
        case Length.PROGRAM:
            data = utils.unpack_msbit(data)
            return {parameters.program[n]: val for n, val in enumerate(data[:128])} | {"seq": list(data[128:])}
        case Length.MAIN:
            d = {parameters.main[n]: val for n, val in enumerate(utils.unpack_nibbles(data))}
        case Length.WAVESHAPE:
            d = utils.unpack_msbit(data)
        case Length.NAME:
            d = bytes(data).decode(encoding="ascii")
    return d


def receive_sysex(data: tuple):
    match data:
        case [Partition.PROGRAM, bank, prog, *part]:
            return {"bank": bank, "prog": prog, "patch": assemble(part)}
        case [Partition.EDIT, *part]:
            return {"edit": assemble(part)}
        case [Partition.WAVESHAPE, wave, *part]:
            return {"wave": wave, "shape": assemble(part)}
        case [Partition.MAIN, *part]:
            return {"main": assemble(part)}
        case [Partition.NAME, bank, prog, *part]:
            return {"bank": bank, "prog": prog, "name": assemble(part)}

        case [Parameter.PROGRAM, parameter, ls, ms]:
            memory["edit"].update({parameters.program[parameter]: utils.decode_nibble(ls, ms)})
        case [Parameter.SEQUENCER, step, ls, ms]:
            memory.get("edit").get("seq")[step] = utils.decode_nibble(ls, ms)
        case [Parameter.MAIN, parameter, ls, ms]:
            memory["main"].update({parameters.main[parameter]: utils.decode_nibble(ls, ms)})

        case _:
            log.warning(f"received unknown: {data=}")


class Evolver:

