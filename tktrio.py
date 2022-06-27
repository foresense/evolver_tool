# tktrio.py
#
# modified from:
# https://github.com/richardsheridan/trio-guest/blob/master/trio_guest_tkinter.py


from collections import deque
from outcome import Error
import traceback

import tkinter
from tkinter import ttk

import trio


class TkTrio(tkinter.Tk):
    def __init__(self, *args, **kwargs):
        self._tk_func_name = self.register(self._tk_func)
        self._q = deque()
        super().__init__(self, *args, **kwargs)

    def _tk_func(self):
        self._q.popleft()()

    def run_sync_soon_threadsafe(self, func):
        self._q.append(func)
        self.call("after", "idle", self._tk_func_name)

    def run_sync_soon_not_threadsafe(self, func):
        self._q.append(func)
        self.call("after", "idle", "after", 0, self._tk_func_name)

    def done_callback(self, outcome):
        print(f"Outcome: {outcome}")
        if isinstance(outcome, Error):
            exc = outcome.error
            traceback.print_exception(type(exc), exc, exc.__traceback__)
        self.destroy()


class TkDisplay:
    def __init__(self, master):
        self.master = master
        self.progress = ttk.Progressbar(master, length="6i")
        self.progress.pack(fill=tkinter.BOTH, expand=1)
        self.cancel_button = tkinter.Button(master, text="Cancel")
        self.cancel_button.pack()
        self.prev_downloaded = 0

    def set_title(self, title):
        self.master.wm_title(title)

    def set_max(self, maximum):
        self.progress.configure(maximum=maximum)

    def set_value(self, downloaded):
        self.progress.step(downloaded - self.prev_downloaded)
        self.prev_downloaded = downloaded

    def set_cancel(self, fn):
        self.cancel_button.configure(command=fn)
        self.master.protocol(
            "WM_DELETE_WINDOW", fn
        )  # calls .destroy() by default


async def count(display, period=0.1, max=60):
    display.set_title(f"Counting every {period} seconds...")
    display.set_max(60)
    with trio.CancelScope() as cancel_scope:
        display.set_cancel(cancel_scope.cancel)
        for i in range(max):
            await trio.sleep(period)
            display.set_value(i)
    return 1


def main(task):
    root = TkTrio()
    display = TkDisplay(root)
    trio.lowlevel.start_guest_run(
        task,
        display,
        run_sync_soon_threadsafe=root.run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=root.run_sync_soon_not_threadsafe,
        done_callback=root.done_callback,
    )
    root.mainloop()


if __name__ == "__main__":
    main(count)
