# mapping strings to parameter values in a dictionary


def make_mapping(strings: list, *, offset: int = 0, zero: int = 0) -> dict:
    return {
        n + offset: string
        for n, string in enumerate(strings)
        if string is not None
    }


bank = make_mapping([f"{n + 1:3}" for n in range(4)])
bend_range = make_mapping([f"{n:3}" for n in range(13)])
bpm = make_mapping([f"{n:3}" for n in range(30, 251)], offset=30)
clock_div = make_mapping(
    [
        " 2n",
        " 4n",
        " 8n",
        " 8h",
        " 8s",
        " 8t",
        "16n",
        "16h",
        "16s",
        "16t",
        "32n",
        "32t",
        "64t",
    ]
)
clock_sync = make_mapping(["Off", "Out", "In", "I-O", None, None, "In-"])
default = make_mapping([f"{n + 1:3}" for n in range(128)])
del_time = make_mapping([f"{n:3}" for n in range(167)])
env_time = make_mapping([f"{n:3}" for n in range(111)])
ext_in_mode = make_mapping(
    ["Stereo", "Left In", "Right In", "Left Audio, Right Control"]
)
feedback_freq = make_mapping([f"{n:3}" for n in range(49)])
filter_freq = make_mapping([f"{n:3}" for n in range(165)])
filter_pole = make_mapping(["2 Pole", "4 Pole"])
fine_tune = make_mapping([f"{n:3}" for n in range(-50, 51)], zero=50)
glide = make_mapping(
    [f"{n:3}" for n in range(101)] + [f"{n:2}F" for n in range(99)] + ["Off"]
)
hack = make_mapping([f"{n:3}" for n in range(15)])
high_pass = make_mapping(
    [f"{n:3} Out" for n in range(100)] + [f"{n:3} In" for n in range(100)]
)
input_gain = make_mapping(
    ["0dB", "3dB", "6dB", "9dB", "12d", "15d", "18d", "21d", "24d"]
)
key_mode = make_mapping(
    ["Low", "Low Retrig", "High", "High Retrig", "Last", "Last Retrig"]
)
key_off_transpose = make_mapping(
    ["Off"] + [f"{n:3}" for n in range(-36, 37)], zero=37
)
level = make_mapping([f"{n:3}" for n in range(101)])
lfo_amount = make_mapping(
    [f"{n:3}" for n in range(100)] + [f"{n:3}" for n in range(100)]
)
lfo_shape = make_mapping(["Tri", "Rev", "Saw", "Sqr", "Rnd"])
lfo_speed = make_mapping(
    [f"{n:3}" for n in range(151)]
    + [" 32", " 16", "  8", "  4", "  2", "  1", " /2", " /4", " /8", "/16"]
)
midi_channel = make_mapping([f"{n:3}" if n else "All" for n in range(17)])
midi_dump = make_mapping(["One", "Ban", "All"])
midi_io = make_mapping(["Off", "All", "Prg", "Par"])
mod_amount = make_mapping([f"{n:3}" for n in range(-99, 100)], zero=99)
off_on = make_mapping(["Off", " On"])
osc_shape = make_mapping(["Saw", "Tri", "S/T"] + [f"{n:3}" for n in range(100)])
output_pan = make_mapping(["L-R", "l-r", " lr", "Mono", "rl ", "r-l", "R-L"])
polychain = make_mapping(["Off", "All", "Not"])
shape_mod = make_mapping(["Off", "Seq1", "Seq2", "Seq3", "Seq4"])
slop = make_mapping([f"{n:3}" for n in range(6)])
transpose = make_mapping([f"{n:3}" for n in range(-36, 37)], zero=36)
trigger_select = make_mapping(
    [
        "All",
        "Seq",
        "Midi",
        "Midi Reset",
        "Combo",
        "Combo Reset",
        "Ext Env",
        "Ext Env Reset",
        "Ext Seq",
        "Ext Seq Reset",
        "Once",
        "Once Reset",
        "Ext Trig",
        "Key",
    ]
)
mod_source = make_mapping(
    [
        "Off",
        "Seq1",
        "Seq2",
        "Seq3",
        "Seq4",
        "LFO1",
        "LFO2",
        "LFO3",
        "LFO4",
        "Filter Env",
        "Amp Env",
        "Env3",
        "Ext Peak",
        "Ext Env",
        "PB",
        "MW",
        "Pressure",
        "BC",
        "FT",
        "Note Vel",
        "Note Number",
        "Expression",
        "Noise",
        "Osc3",
        "Osc4",
    ]
)

# notenames
notes = ("C ", "Db", "D ", "Eb", "E ", "F ", "Gb", "G ", "Ab", "A ", "Bb", "B ")
octaves = (" ", "-", "0", "1", "2", "3", "4", "5", "6", "7", "8")
freq = make_mapping(
    [f"{notes[n % 12]}{octaves[n // 12]}" for n in range(121)], zero=60
)

# seq_dest has a few extra parameters then mod_dest
mod_dest = [
    "Off",
    "O1F",
    "O2F",
    "O3F",
    "O4F",
    "OaF",
    "O1L",
    "O2L",
    "O3L",
    "O4L",
    "OaL",
    "Noi",
    "Ext",
    "O1P",
    "O2P",
    "OaP",
    "F43",
    "F34",
    "R43",
    "R34",
    "Frq",
    "FSp",
    "Res",
    "HpF",
    "VCA",
    "Pan",
    "FbF",
    "FbA",
    "Dt1",
    "Dt2",
    "Dt3",
    "DtA",
    "Da1",
    "Da2",
    "Da3",
    "DaA",
    "Df1",
    "Df2",
    "L1F",
    "L2F",
    "L3F",
    "L4F",
    "LaF",
    "L1A",
    "L2A",
    "L3A",
    "L4A",
    "LaA",
    "E1A",
    "E2A",
    "E3A",
    "EaA",
    "E1t",
    "E2t",
    "E3t",
    "Eat",
    "E1d",
    "E2d",
    "E3d",
    "EAd",
    "E1r",
    "E2r",
    "E3r",
    "EAr",
    "F1f",
    "F2f",
    "F1r",
    "F2r",
    "Dst",
]
seq_dest = make_mapping(
    mod_dest
    + [
        "Clock Multiplier",
        "Note",
        "Velocity",
        "ModWheel",
        "Pressure",
        "Breath",
        "Foot",
    ]
)
mod_dest = make_mapping(mod_dest)
