import mido


def open_input(portname: str):
    """Open the first input port that starts with 'portname'
    """
    for p in mido.get_input_names():
        if p.startswith(portname):
            return mido.open_input(p)
    return None


def open_output(portname: str):
    """Open the first output port that starts with 'portname'
    """
    for p in mido.get_output_names():
        if p.startswith(portname):
            return mido.open_output(p)
    return None
