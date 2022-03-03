# from collections import deque
from queue import Queue
from threading import Thread
from time import sleep
# from time import perf_counter

import mido


VERBOSE = 1

# TODO WHEN ARE THINGS A TUPLE AND WHEN ARE THEY A LIST AND WHEN ARE THEY A DEQUE

OUT_SPEED = 1 / 10         

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


queue_out = Queue(maxsize=64)
main_memory = {}
edit_memory = {}
edit_name = None
memory = {bank: {program: {} for program in range(128)} for bank in range(4)}


def encode_ls_ms(b: int) -> tuple:
    return b & 0xF, b >> 4


def decode_ls_ms(ls: int, ms: int) -> int:
    return ls + (ms << 4)


def encode_string(name: str) -> list:
    if len(name) in range(17):
        return [ord(c) for c in name] + [ord(" ") for n in range(16 - len(name))]
    raise OverflowError("[ERROR]: string too long (16 characters maximum)")


def decode_string(packed_name: tuple) -> str:
    return bytes(packed_name).decode(encoding='ascii', errors='replace')


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
        edit_memory.update(assemble_program(data))
        if VERBOSE:
            print(f"[RECEIVED] {edit_memory=}")
    elif identifier == PROG_DUMP:
        bank_n = data[0]
        prog_n = data[1]
        prog_data = data[2:]
        memory.get(bank_n).get(prog_n).update(assemble_program(prog_data))
        if VERBOSE:
            print(f"[RECEIVED] Program: {bank_n:01}_{prog_n:03} {memory.get(bank_n).get(prog_n)}")
    elif identifier == NAME_DUMP:
        bank_n = data[0]
        prog_n = data[1]
        ascii_list = data[2:]
        name_dict = {"name": decode_string(ascii_list)}
        memory.get(bank_n).get(prog_n).update(name_dict)
        if(VERBOSE):
            print(f"[RECEIVED] {name_dict}")
    elif identifier == MAIN_PAR:
        par = data[0]
        ls = data[1]
        ms = data[2]
        main_memory.update({main_parameters[par]: decode_ls_ms(ls, ms)})
    elif identifier == PROG_PAR:
        edit_memory.update({program_parameters[data[0]]: decode_ls_ms(data[1], data[2])})
    elif identifier == SEQ_PAR:
        edit_memory.get("seq")[data[0]] = decode_ls_ms(data[1], data[2])
    else:
        if(VERBOSE):
            print(f"[NOTICE] {data=}")


def save_edit_memory(bank: int, program: int, name: str):
    queue_message([PROG_DUMP, bank, program, *serialize_program(edit_memory)])
    queue_message([NAME_DUMP, bank, program, *encode_string(name)])


# TODO find out if this is working
def save_sysex(data: list, filename: str):
    with open(filename, 'w') as file:
        file.write(mido.Message(type='sysex', data=(*SYSEX_ID, *data)).bytes())


# TODO something like this. make sure the interface is consequent.
def load_sysex(filename: str) -> dict:
    pass


def queue_message(data: list):
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
            print(f"[WARNING]: Unknown SysEx")
    #else:
    #     print(f"[NOTICE] unrecognized {message=})")


def queue_out_thread():
    bank = None
    program = None
    
    while(not midi_out.closed):
        if bank != main_memory["bank"] or program != main_memory["program"]:
            bank = main_memory["bank"]
            program = main_memory["program"]
            if VERBOSE:
                print(f"[RECEIVED] program change {bank}-{program}")
            queue_message([NAME_REQ, bank, program])
            queue_message([EDIT_REQ])
            #queue_message([PROG_REQ, bank, program])
            memory.get(bank).get(program).update(edit_memory)
        if not queue_out.empty():
            message = queue_out.get()
            if VERBOSE:
                (f"[SENDING]: {message}")
            midi_out.send(message)
            queue_out.task_done()
        sleep(OUT_SPEED)


if __name__ == "__main__":
    midi_in = mido.open_input('MidiKliK 1', callback=midi_in_callback)
    midi_out = mido.open_output('MidiKliK 2')

    main_memory.update({"program": None})
    main_memory.update({"bank": None})

    # update memory
    queue_message([MAIN_REQ])
    #send_message(MAIN_REQ)

    qt = Thread(target=queue_out_thread)
    qt.start()
