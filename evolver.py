import json
import logging
from queue import Queue
from threading import Thread
from time import sleep
import wave
import mido

import parameters

log = logging.getLogger("evolver")
log_format = logging.Formatter("[%(levelname)s:%(asctime)s] %(message)s")
log_format.datefmt = '%Y%m%d_%H%M%S'
log_stdout = logging.StreamHandler()
log_stdout.setFormatter(log_format)
log.addHandler(log_stdout)
log.setLevel(logging.INFO)


MIDI_IN = "MidiKliK 3"
MIDI_OUT = "MidiKliK 4"

OUT_SPEED = 1 / 10

CC_MODWHEEL = 0x01
CC_BANK_CHANGE = 0x20

SYSEX_ID = (0x01, 0x20, 0x01)
EVOLVER_ID = 0x20

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

main_memory = {}
edit_memory = {}
program_memory = {bank: {program: {} for program in range(128)} for bank in range(4)}
wave_memory = {waveshape: [0 for n in range(128)] for waveshape in range(128)}
queue_out = Queue(maxsize=2048)


def encode_ls_ms(b: int) -> tuple:
    return b & 0xF, b >> 4


def decode_ls_ms(ls: int, ms: int) -> int:
    return ls + (ms << 4)


def encode_string(name: str) -> list:
    if len(name) in range(17):
        return [ord(c) for c in name] + [ord(" ") for n in range(16 - len(name))]
    else:
        raise OverflowError("[ERROR]: string too long (16 characters maximum)")


def decode_string(packed_name: tuple) -> str:
    readable = [c if c in range(32, 127) else 32 for c in packed_name]
    return bytes(readable).decode(encoding="ascii")


def pack_ms_bit(data: list) -> tuple:
    packed_data = []
    count = 0
    for n, byte in enumerate(data):
        count, cycle = divmod(n, 7)
        ms_bit = byte >> 7
        # growing from 7 bytes to 8 bytes per cycle:
        ms_bits_index = n + count - cycle
        if cycle == 0:
            # cycle starts with ms_bit_byte is 8th byte
            packed_data.append(ms_bit)
            packed_data.append(byte & 0x7F)
        else:
            packed_data.append(byte & 0x7F)
            packed_data[ms_bits_index] = packed_data[ms_bits_index] | (ms_bit << cycle)
    return tuple(packed_data)


def unpack_ms_bit(packed_data: tuple) -> tuple:
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


def assemble_program(packed_data: tuple) -> dict:
    program_dict = {}
    data = unpack_ms_bit(packed_data)
    for n, val in enumerate(data[:128]):
        par = parameters.program[n]
        program_dict.update({par: val})
    program_dict.update({"seq": data[128:192]})
    return program_dict


def assemble_waveshape(packed_data: tuple) -> dict:
    waveshape = []
    # pack to 16-bit values
    idat = iter(unpack_ms_bit(packed_data))
    for ls, ms in zip(idat, idat):
        waveshape.append(ls + (ms << 8))
    return waveshape


def assemble_main(packed_data: tuple) -> dict:
    main_dict = {}
    idat = iter(packed_data)
    for n, (ls, ms) in enumerate(zip(idat, idat)):
        par = parameters.main[n]
        val = decode_ls_ms(ls, ms)
        main_dict.update({par: val})
    return main_dict


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


def save_json(filename: str, memory_dict: dict = edit_memory):
    with open(filename, "w") as file:
        json.dump(memory_dict, file, indent=2)


def load_json(filename: str) -> dict:
    with open(filename, "r") as file:
        return json.load(file)


def save_sysex(filename: str, memory_dict: dict = edit_memory):
    # TODO serialize output and write valid sysex strings
    # mido.write_syx_file(filename)
    # file.write(mido.Message(type='sysex', data=(*SYSEX_ID, *pdata)).bytes())
    pass


def load_sysex(filename: str) -> dict:
    # sysex_stream = mido.read_syx_file(filename)
    # TODO deserialize sysex, first chop it in parts
    #      then put it through receive message
    pass


def save_waveshape(filename: str, wave_number: int):
    with wave.open(filename, 'wb') as wavefile:
        wavefile.setnchannels(1)
        wavefile.setframerate(44100)
        wavefile.setsampwidth(2)
        wavefile.setnframes(128)
        for point in wave_memory[wave_number]:
            wavefile.writeframes(bytes([point & 0xff, point >> 8]))


def load_waveshape(filename: str) -> dict:
    # TODO load from standard pcm .wav
    with wave.open(filename, 'rb') as wavefile:
        pass
    waveshape = [0 for n in range(128)]
    return waveshape


def program_change(bank: int, program: int):
    if bank in range(4):
        main_memory["bank"] = bank
        queue_out.put(
            mido.Message(type="control_change", control=CC_BANK_CHANGE, value=bank)
        )
    if program in range(128):
        main_memory["program"] = program
        queue_out.put(mido.Message(type="program_change", program=program))


def queue_sysex(data: list):
    message = mido.Message(type="sysex", data=(*SYSEX_ID, *data))
    queue_out.put(message)
    log.debug(f"queued {message} ({queue_out.qsize()=})")


def send_program(bank: int, program: int, memory_dict: dict = edit_memory):
    queue_sysex([PROG_DUMP, bank, program, *serialize_program(memory_dict)])


def send_name(bank: int, program: int, name: str):
    queue_sysex([NAME_DUMP, bank, program, *encode_string(name)])


def send_edit(memory_dict: dict = edit_memory):
    queue_sysex([EDIT_DUMP, *serialize_program(memory_dict)])


def req_program(bank: int, program: int):
    queue_sysex([PROG_REQ, bank, program])


def req_edit():
    queue_sysex([EDIT_REQ])


def req_wave(wave_number: int):
    queue_sysex([WAVE_REQ, wave_number])


def req_main():
    queue_sysex([MAIN_REQ])


def req_name(bank: int, program: int):
    queue_sysex([NAME_REQ, bank, program])



def midi_in_callback(message: mido.Message):
    if message.type == "program_change":
        main_memory.update({"program": message.program})
    elif message.type == "control_change" and message.control == 32:
        main_memory.update({"bank": message.value})
    elif message.type == "sysex" and message.data[:3] == SYSEX_ID:
        identifier = packed_data[0]
        data = packed_data[1:]
        if identifier == PROG_DUMP:
            bank = data[0]
            program = data[1]
            prog_dict = assemble_program(data[2:])
            program_memory.get(bank).get(program).update(prog_dict)
            log.info(f"received {bank=} {program=} -> {prog_dict=}")
        elif identifier == EDIT_DUMP:
            prog_dict = assemble_program(data)
            edit_memory.update(prog_dict)
            log.info(f"received {prog_dict}")
        elif identifier == WAVE_DUMP:
            wave_number = data[0]
            wave_shape = assemble_waveshape(data[1:])
            wave_memory[wave_number] = wave_shape
            log.info(f"received waveshape {wave_number}: {wave_memory[wave_number]}")
        elif identifier == MAIN_DUMP:
            main_dict = assemble_main(data)
            main_memory.update(main_dict)
            log.info(f"received {main_dict}")
        elif identifier == NAME_DUMP:
            bank = data[0]
            program = data[1]
            name_str = decode_string(data[2:])
            program_memory.get(bank).get(program).update({"name": name_str})
            log.info(f"received {bank=} {program=} -> {name_str=}")
        elif identifier == MAIN_PAR:
            par = parameters.main[data[0]]
            val = decode_ls_ms(data[1], data[2])
            main_memory.update({par: val})
            log.info(f"received {par=} {val=}")
        elif identifier == PROG_PAR:
            par = parameters.program[data[0]]
            val = decode_ls_ms(data[1], data[2])
            edit_memory.update({par: val})
            log.info(f"received {par=} {val=}")
        elif identifier == SEQ_PAR:
            step = data[0]
            val = decode_ls_ms(data[1], data[2])
            edit_memory.get("seq")[step] = val
            log.info(f"received {step=} {val=}")
        else:
            log.warning(f"received unknown {data=}")
    else:
        log.warning(f"received unknown {message}")


def queue_out_thread():
    bank = None
    program = None
    while not midi_out.closed:
        if bank != main_memory.get("bank") or program != main_memory.get("program"):
            bank = main_memory.get("bank")
            program = main_memory.get("program")
            log.info(f"program change {bank=} {program=}")
            req_edit()
            program_memory.get(bank).get(program).update(edit_memory)
        if not queue_out.empty():
            message = queue_out.get()
            midi_out.send(message)
            queue_out.task_done()
            log.info(f"sent {message}")
            log.debug(f"{queue_out.qsize()=}")
        sleep(OUT_SPEED)
    log.info(f"goodbye! {midi_out.closed=}")


def test_ls_ms(o):
    a = iter(unpack_ms_bit(wave_memory[o]))
    for x, y in zip(a, a):
        print(f"{x:08b} {y:08b}")


if __name__ == "__main__":
    midi_in = mido.open_input(MIDI_IN, callback=midi_in_callback)
    midi_out = mido.open_output(MIDI_OUT)
    req_main()
    qot = Thread(target=queue_out_thread)
    qot.start()
