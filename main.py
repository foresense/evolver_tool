from queue import Queue
from threading import Thread
from time import sleep, perf_counter

import mido


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
    "flt_freq", "flt_env", "flt_attack", "flt_decay", "flt_sustain", "flt_release", "flt_resonance", "flt_key",
    "vca_level", "vca_env", "vca_attack", "vca_decay", "vca_sustain", "vca_release", "output_pan", "volume",
    "fb_freq", "fb_level", "fb_grunge", "delay_t1", "delay_l1", "delay_fb1", "delay_fb2", "output_hack",
    "lfo1_freq", "lfo1_shape", "lfo1_amount", "lfo1_dest", "lfo2_freq", "lfo2_shape", "lfo2_amount", "lfo2_dest",
    "env3_amount", "env3_dest", "env3_attack", "env3_decay", "env3_sustain", "env3_release", "trigger_sel", "key_offset",
    "seq1_dest", "seq2_dest", "seq3_dest", "seq4_dest", "noise_vol", "ext_in_vol", "ext_in_mode", "input_hack",
    "osc1_glide", "sync_2-1", "bpm", "clock_div", "osc2_glide", "osc_slop", "pb_range", "key_mode",
    "osc3_glide", "fm_4-3", "osc3_shape_seq", "rm_4-3", "osc4_glide", "fm_3-4", "osc4_shape_seq", "rm_3-4",
    "flt_poles", "flt_vel", "flt_audio_mod", "flt_split", "highpass", "mod1_source", "mod1_amount", "mod1_dest",
    "exp-lin_env", "vca_vel", "mod2_source", "mod2_amount", "mod2_dest", "mod3_source", "mod3_amount", "mod3_dest",
    "mod4_source", "mod4_amount", "mod4_dest", "delay_t2", "delay_l2", "delay_t3", "delay_l3", "distortion",
    "lfo3_freq", "lfo3_shape", "lfo3_amount", "lfo3_dest", "lfo4_freq", "lfo4_shape", "lfo4_amount", "lfo4_dest",
    "env3_delay", "env3_vel", "in_peak_amount", "in_peak_dest", "in_env_amount", "in_env_dest", "vel_amount", "vel_dest",
    "modwheel_amount", "modwheel_dest", "pressure_amount", "pressure_dest", "breath_amount", "breath_dest", "foot_amount", "foot_dest"
)

queue_out = Queue(maxsize=32)

main_memory = {}
edit_memory = {}

# initialize programs memory
banks = {}
programs = {}
for x in range(4):
    for y in range(128):
        programs.update({y: dict()})
    banks.update({x: programs})


def unpack_ls_ms(ls: int, ms: int) -> int:
    return ls + (ms << 4)


def unpack_ms_bit(packed_data: tuple) -> list:
    ms_bits: int = 0
    data = []
    for n, byte in enumerate(packed_data):
        if n % 8:
            if ms_bits & (1 << (n - 1)):
                data.append(byte | 0x80)
            else:
                data.append(byte)
        else:
            ms_bits = byte
    return data


def unpack_string(packed_name: tuple) -> str:
    name = bytes(packed_name).decode(encoding='ascii', errors='replace')
    print(name)
    return name


def pack_string(name: str) -> list:
    if len(name) in range(16):
        return [ord(c) for c in name] + [ord(" ") for n in range(16 - len(name))]
    raise("[WARNING]: string too long (16 characters maximum)")


def assemble_program(packed_data: tuple) -> dict:
    data = unpack_ms_bit(packed_data)
    program_dict = {}
    for n, val in enumerate(data[:128]):
        program_dict.update({program_parameters[n]: val})
    program_dict.update({"seq": [data[128:144], data[144:160], data[160:176], data[176:192]]})
    return program_dict


def assemble_main(packed_data: tuple) -> dict:
    pass


# TODO get NAME into EDIT memory? we need it as working memory

def unpack_data(packed_data: tuple):
    identifier = packed_data[0]
    data = packed_data[1:]
    edit_bank = main_memory.get('bank')
    edit_program = main_memory.get('program')
    
    if identifier == MAIN_DUMP:
        idat = iter(data)
        for n, (ls, ms) in enumerate(zip(idat, idat)):
            main_memory.update({main_parameters[n]: unpack_ls_ms(ls, ms)})
    elif identifier == EDIT_DUMP:
        edit_memory.update(assemble_program(data))
        # edit_memory.update()
        banks.get(edit_bank).get(edit_program).update(edit_memory)
    elif identifier == PROG_DUMP:
        # print(f"bank: {data[0]} program: {data[1]}")
        banks[data[0]][data[1]].update(assemble_program(data[2:]))
    elif identifier == NAME_DUMP:
        banks[data[0]][data[1]].update({"name": unpack_string(data[2:])})
    
    elif identifier == MAIN_PAR:
        main_memory.update({main_parameters[data[0]]: unpack_ls_ms(data[1], data[2])})
    elif identifier == PROG_PAR:
        edit_memory.update({program_parameters[data[0]]: unpack_ls_ms(data[1], data[2])})
    elif identifier == SEQ_PAR:
        edit_memory.update({program_})
    
    else:
        print(f"[NOTICE] {data=}")


def pack_data(data: dict):
    pass


def queue_message(data: list) -> mido.Message:
    queue_out.put(mido.Message(type='sysex', data=(*SYSEX_ID, *data)))


def midi_in_callback(message: mido.Message):
    if message.type == 'program_change':
        main_memory.update({"program": message.program})
    elif message.type == 'control_change' and message.control == 32:
        main_memory.update({"bank": message.value})
    elif message.type == 'sysex' and message.data[:3] == SYSEX_ID:
        unpack_data(message.data[3:])
    else:
        print(f"[NOTICE] unrecognized {message=})")


def queue_out_thread():
    bank = None
    program = None
    while(not midi_out.closed):
        if bank != main_memory["bank"] or program != main_memory["program"]:
            bank = main_memory["bank"]
            program = main_memory["program"]
            queue_message([EDIT_REQ])
            queue_message([NAME_REQ, bank, program])
        if not queue_out.empty():
            midi_out.send(queue_out.get())
            queue_out.task_done()
        sleep(OUT_SPEED)


if __name__ == "__main__":
    midi_in = mido.open_input('MidiKliK 1', callback=midi_in_callback)
    midi_out = mido.open_output('MidiKliK 2')

    main_memory.update({"program": None})
    main_memory.update({"bank": None})

    # update memory
    queue_message([MAIN_REQ])

    qt = Thread(target=queue_out_thread)
    qt.start()
