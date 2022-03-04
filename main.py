import json
from queue import Queue
from threading import Thread
from time import sleep

import mido


VERBOSE = 1

MIDI_IN = "MidiKliK 1"
MIDI_OUT = "MidiKliK 2"

# TODO WHEN ARE THINGS A TUPLE AND WHEN ARE THEY A LIST AND WHEN ARE THEY A DEQUE

OUT_SPEED = 1 / 10         

# CC
BANK_CHANGE = 0x20

# SYSEX
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


main_parameters = (
    "program", "bank", "volume", "transpose", "bpm", "clock_div", "program_tempo", "midi_clock",
    "lock_seq", "poly_chain", "input_gain", "fine_tune", "midi_rec", "midi_xmit", "midi_chan", "midi_dump"
)

program_parameters = (
    "osc1_freq", "osc1_fine", "osc1_shape", "osc1_level", "osc2_freq", "osc2_fine", "osc2_shape", "osc2_level",
    "osc3_freq", "osc3_fine", "osc3_shape", "osc3_level", "osc4_freq", "osc4_fine", "osc4_shape", "osc4_level",
    "filt_freq", "filt_env", "filt_attack", "filt_decay", "filt_sustain", "filt_release", "filt_resonance", "filt_key",
    "vca_level", "vca_env", "vca_attack", "vca_decay", "vca_sustain", "vca_release", "output_pan", "volume",
    "fb_freq", "fb_level", "fb_grunge", "delay_t1", "delay_l1", "delay_fb1", "delay_fb2", "output_hack",
    "lfo1_freq", "lfo1_shape", "lfo1_amount", "lfo1_dest", "lfo2_freq", "lfo2_shape", "lfo2_amount", "lfo2_dest",
    "env3_amount", "env3_dest", "env3_attack", "env3_decay", "env3_sustain", "env3_release", "trigger_sel", "key_offset",
    "seq1_dest", "seq2_dest", "seq3_dest", "seq4_dest", "noise_vol", "ext_in_vol", "ext_in_mode", "input_hack",
    "osc1_glide", "sync_2-1", "bpm", "clock_div", "osc2_glide", "osc_slop", "pb_range", "key_mode",
    "osc3_glide", "fm_4-3", "osc3_shape_seq", "rm_4-3", "osc4_glide", "fm_3-4", "osc4_shape_seq", "rm_3-4",
    "filt_poles", "filt_vel", "filt_audio_mod", "filt_split", "highpass", "mod1_source", "mod1_amount", "mod1_dest",
    "exp-lin_env", "vca_vel", "mod2_source", "mod2_amount", "mod2_dest", "mod3_source", "mod3_amount", "mod3_dest",
    "mod4_source", "mod4_amount", "mod4_dest", "delay_t2", "delay_l2", "delay_t3", "delay_l3", "distortion",
    "lfo3_freq", "lfo3_shape", "lfo3_amount", "lfo3_dest", "lfo4_freq", "lfo4_shape", "lfo4_amount", "lfo4_dest",
    "env3_delay", "env3_vel", "in_peak_amount", "in_peak_dest", "in_env_amount", "in_env_dest", "vel_amount", "vel_dest",
    "modwheel_amount", "modwheel_dest", "pressure_amount", "pressure_dest", "breath_amount", "breath_dest", "foot_amount", "foot_dest"
)

main_memory = {}
edit_memory = {}
edit_name = None
program_memory = {bank: {program: {} for program in range(128)} for bank in range(4)}

queue_out = Queue(maxsize=1024)


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
    return bytes(readable).decode(encoding='ascii')


def pack_ms_bit(data: list) -> tuple:
    packed_data = []
    counter = 0
    for n, byte in enumerate(data):
        counter, cycle = divmod(n, 7)
        ms_bit = byte >> 7
        # our list is growing from 7 to 8 bytes per packet so we need to count that to be able to update the ms_bits byte
        ms_bits_index = n + counter - cycle
        if cycle == 0:
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
    data = unpack_ms_bit(packed_data)
    program_dict = {}
    for n, val in enumerate(data[:128]):
        program_dict.update({program_parameters[n]: val})
    program_dict.update({"seq": data[128:192]})
    return program_dict


def serialize_program(program: dict) -> tuple:
    data = []
    for parameter in program_parameters:
        data.append(program.get(parameter))
    data.extend(program.get('seq'))
    return pack_ms_bit(data)


def assemble_main(packed_data: tuple) -> dict:
    idat = iter(packed_data)
    main_dict = {}
    for n, (ls, ms) in enumerate(zip(idat, idat)):
        main_dict.update({main_parameters[n]: decode_ls_ms(ls, ms)})
    return main_dict


def serialize_main(main: dict) -> tuple:
    pass


def receive_message(packed_data: tuple):
    # TODO get NAME into EDIT memory? we need it as working memory
    identifier = packed_data[0]
    data = packed_data[1:]
    if identifier == MAIN_DUMP:
        main_memory.update(assemble_main(data))
    elif identifier == EDIT_DUMP:
        prog_dict = assemble_program(data)
        edit_memory.update(prog_dict)
        if VERBOSE:
            print(f"[RECEIVED] EDIT MEMORY -> {prog_dict}")
    elif identifier == PROG_DUMP:
        bank = data[0]
        program = data[1]
        prog_dict = assemble_program(data[2:])
        program_memory.get(bank).get(program).update(prog_dict)
        if VERBOSE:
            print(f"[RECEIVED] BANK {bank} / PROGRAM {program} -> {prog_dict}")
    elif identifier == NAME_DUMP:
        bank = data[0]
        program = data[1]
        name_str = decode_string(data[2:])
        program_memory.get(bank).get(program).update({"name": name_str})
        if(VERBOSE):
            print(f"[RECEIVED] BANK {bank} / PROGRAM {program} -> {name_str}")
    elif identifier == MAIN_PAR:
        par = data[0]
        val = decode_ls_ms(data[1], data[2])
        main_memory.update({main_parameters[par]: val})
    elif identifier == PROG_PAR:
        par = data[0]
        val = decode_ls_ms(data[1], data[2])
        edit_memory.update({program_parameters[par]: val})
    elif identifier == SEQ_PAR:
        step = data[0]
        val = decode_ls_ms(data[1], data[2])
        edit_memory.get("seq")[step] = val
    else:
        if(VERBOSE):
            print(f"[NOTICE] {data=}")


def send_program(bank: int, program: int, memory_dict: dict = edit_memory):
    queue_sysex([PROG_DUMP, bank, program, *serialize_program(memory_dict)])


def send_name(bank: int, program: int, name: str):
    queue_sysex([NAME_DUMP, bank, program, *encode_string(name)])


def send_edit(memory_dict: dict = edit_memory):
    queue_sysex([EDIT_DUMP, *serialize_program(memory_dict)])


def req_main():
    queue_sysex([MAIN_REQ])


def req_edit():
    queue_sysex([EDIT_REQ])


def req_program(bank: int, program: int):
    queue_sysex([PROG_REQ, bank, program])


def req_name(bank: int, program: int):
    queue_sysex([NAME_REQ, bank, program])


def req_wave(wave_number: int):
    queue_sysex([WAVE_REQ, wave_number])


def save_json(filename: str, memory_dict: dict = edit_memory):
    with open(filename, 'w') as file:
        json.dump(memory_dict, file, indent=2)


def load_json(filename: str) -> dict:
    with open(filename, 'r') as file:
        return json.load(file)


def save_sysex(filename: str, memory_dict: dict = edit_memory):
    # TODO serialize output and write valid sysex strings
    #mido.write_syx_file(filename)
    # file.write(mido.Message(type='sysex', data=(*SYSEX_ID, *pdata)).bytes())
    pass


def load_sysex(filename: str) -> dict:
    sysex_stream = mido.read_syx_file(filename)
    # TODO deserialize sysex, first chop it in parts, then put it through receive message
    pass


def program_change(program: int, *, bank: int = None):
    if bank in range(4):
        main_memory['bank'] = bank
        queue_out.put(mido.Message(type="control_change", control=BANK_CHANGE, value=bank))
    if program in range(128):
        main_memory['program'] = program
        queue_out.put(mido.Message(type="program_change", program=program))


def queue_sysex(data: list):
    queue_out.put(mido.Message(type='sysex', data=(*SYSEX_ID, *data)))


def midi_in_callback(message: mido.Message):
    if message.type == 'program_change':
        main_memory.update({"program": message.program})
    elif message.type == 'control_change' and message.control == 32:
        main_memory.update({"bank": message.value})
    elif message.type == 'sysex':
        if message.data[:3] == SYSEX_ID:
            receive_message(message.data[3:])
        elif VERBOSE:
            print(f"[WARNING]: unknown sysex: {message.data}")


def queue_out_thread():
    bank = None
    program = None
    while(not midi_out.closed):
        if bank != main_memory.get('bank') or program != main_memory.get('program'):
            bank = main_memory.get('bank')
            program = main_memory.get('program')
            req_edit()
            program_memory.get(bank).get(program).update(edit_memory)
        if not queue_out.empty():
            message = queue_out.get()
            if VERBOSE:
                (f"[SENDING]: {message}")
            midi_out.send(message)
            queue_out.task_done()
        sleep(OUT_SPEED)


if __name__ == "__main__":
    midi_in = mido.open_input(MIDI_IN, callback=midi_in_callback)
    midi_out = mido.open_output(MIDI_OUT)
    req_main()
    qot = Thread(target=queue_out_thread)
    qot.start()
