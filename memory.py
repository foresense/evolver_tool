# memory.py
# memory primitives

import parameters

main = {parameters.main[n]: 0 for n in range(16)}
edit = {parameters.program[n]: 0 for n in range(128)}
protgram = {b: {p: {parameters.program[n]: 0 for n in range(128)} for p in range(128)} for b in range(4)}
waveshape = {w: bytes(256) for w in range(128)}
name = {b: {p: "unknown         " for p in range(128)} for b in range(4)}
