"""evolute - evolver editor
"""

import evolver
import parameters
import utils
import config

import mido

from mido import Message


def midi_in_callback(message: Message):
    match message:
        case Message(type="program_change"):
            # memory.get("main").update({"program": message.program})
            pass
        case Message(type="control_change", control=CC.BANK_CHANGE):
            # on bank change send out a new dump edit memory sysex command
            # memory.get("main").update({"bank": message.value})
        case Message(type="sysex") if message.data[:3] == sysex_id:
            #receive_sysex(message.data[3:])
        case _:
            log.warning(f"received unknown: {message}")


def queue_out_thread():
    #global memory
    bank = None
    program = None
    # queue_message(Request.MAIN)
    while not midi_out.closed:
        if bank != memory.get("main").get("bank") or program != memory.get("main").get("program"):
            # bank = memory.get("main").get("bank")
            # program = memory.get("main").get("program")
            log.info(f"program change -> {bank=} {program=}")
            # queue_message(Request.EDIT)
            # memory["patch"][bank][program].update(memory.get("edit"))
        if not queue_out.empty():
            message = queue_out.get()
            midi_out.send(message)
            queue_out.task_done()
            log.info(f"sent {message}")
        sleep(OUT_SPEED)


if __name__ == "__main__":
    
    midi_in = utils.open_mido_input(config.midi_in, callback=midi_in_callback)
    midi_out = utils.open_midi_output(config.midi_out)

    qot = Thread(target=queue_out_thread)
    qot.start()



''' TODO


use: asyncio or trio
what ui engine?
ui and midi


widgets / parameters

- direct hardware parameters, directly link to midi hardware
- virtual parameters, link via a method to one or several parameters
- hidden parameters
- parameter groups
- pages


I could generalize this as a library?

'''
