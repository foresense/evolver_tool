import json
import logging
import struct
import wave

import mido


def get_logger(name: str) -> logging.Logger:
    log_format = logging.Formatter(
        "[%(asctime)s %(levelname)s] %(message)s", datefmt="%Y.%m.%d %H:%M:%S"
    )
    log_stdout = logging.StreamHandler(format=log_format)
    return logging.getLogger(name, handler=log_stdout)


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


def open_input(portname: str):
    """Open the first input port that starts with 'portname'"""
    for p in mido.get_input_names():
        if p.startswith(portname):
            return mido.open_input(p)
    raise ValueError(f"No such port: {portname=}")


def open_output(portname: str):
    """Open the first output port that starts with 'portname'"""
    for p in mido.get_output_names():
        if p.startswith(portname):
            return mido.open_output(p)
    raise ValueError(f"No such port: {portname=}")


def encode_nibble(b: int) -> bytes:
    """encode 8-bit integer to 4-bit bytestream"""
    if b in range(256):
        return bytes([b & 0xF, b >> 4])
    else:
        raise ValueError(f"{b} is not byte sized ({range(256)=})")


def decode_nibble(ls: int, ms: int) -> int:
    """combine 4-bit bytestream to 8-bit integer"""
    if ls in range(16) and ms in range(16):
        return ls | ms << 4
    else:
        raise ValueError(f"{ls=} or {ms=} is not nibble sized ({range(16)=})")


def unpack_nibbles(packed_data: bytes, endian: str = "little") -> tuple:
    """unpack a stream of nibbles in bytes format"""
    if type(packed_data) is not bytes:
        raise ValueError(f"{type(packed_data)=}. should be bytes.")
    if len(packed_data) % 2:
        raise ValueError(f"{len(packed_data)=}. should be even.")

    idat = iter(packed_data)
    zdat = zip(idat, idat)

    match endian:
        case "little":
            return tuple(decode_nibble(ls, ms) for (ls, ms) in zdat)
        case "big":
            return tuple(decode_nibble(ls, ms) for (ms, ls) in zdat)


def unpack_str(data: bytes) -> str:
    return data.decode(encoding="ascii")


def pack_str(string: str) -> bytes:
    return bytes([ord(c) for c in string])


# def encode_string(name: str) -> list:
#    if len(name) in range(17):
#        return [ord(c) for c in name] + [ord(" ") for n in range(16 - len(name))]
#    else:
#        raise OverflowError("[ERROR]: string too long (16 characters maximum)")


def pack_msbit(data: tuple) -> bytes:
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
            packed_data[ms_bits_index] = packed_data[ms_bits_index] | (
                ms_bit << cycle
            )
    return bytes(packed_data)


def unpack_msbit(packed_data: bytes) -> tuple:
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
    return tuple(data)
