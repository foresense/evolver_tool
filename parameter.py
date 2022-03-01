# probably not use this


class Parameter:

    def __init__(self, par_name: str, par_number: int, par_range: range, par_default: int = 0):

        if par_default not in par_range:
            raise ValueError(f"default value ({par_default}) not in parameter {par_range}")

        self._name = par_name
        self._number = par_number
        self._range = par_range
        self._value = par_default

    def __get__(self, obj, objtype=None):
        if self._value not in self._range:
            raise ValueError(f"value ({self._value}) not in {self._range}")
        else:
            print(f"[NOTICE] {self._name} [{self._number}]: {self._value}")
            return self._name, self._number, self._value
    
    def __set__(self, obj, val):
        if val not in self._range:
            print(f"[WARNING] value ({val}) not in {self._range}.")
        else:
            print(f"[NOTICE] {self._name} [{self._number}] = {val}")
            self._value = val


def parameter(par_name: str, par_number: int, par_range: range, par_default: int):

    if par_default not in par_range:
        raise ValueError(f"default value ({par_default}) not in parameter {par_range}")

    def getter(self) -> tuple:
        pass