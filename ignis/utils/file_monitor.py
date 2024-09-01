import os
from gi.repository import GObject, Gio
from ignis.gobject import IgnisGObject
from typing import Callable, List, Optional

FLAGS = {
    None: Gio.FileMonitorFlags.NONE,
    "none": Gio.FileMonitorFlags.NONE,
    "watch_mounts": Gio.FileMonitorFlags.WATCH_MOUNTS,
    "send_moved": Gio.FileMonitorFlags.SEND_MOVED,
    "watch_hard_links": Gio.FileMonitorFlags.WATCH_HARD_LINKS,
    "watch_moves": Gio.FileMonitorFlags.WATCH_MOVES,
}

EVENT = {
    Gio.FileMonitorEvent.CHANGED: "changed",
    Gio.FileMonitorEvent.CHANGES_DONE_HINT: "changes_done_hint",
    Gio.FileMonitorEvent.MOVED_OUT: "moved_out",
    Gio.FileMonitorEvent.DELETED: "deleted",
    Gio.FileMonitorEvent.CREATED: "created",
    Gio.FileMonitorEvent.ATTRIBUTE_CHANGED: "attribute_changed",
    Gio.FileMonitorEvent.PRE_UNMOUNT: "pre_unmount",
    Gio.FileMonitorEvent.UNMOUNTED: "unmounted",
    Gio.FileMonitorEvent.MOVED: "moved",
    Gio.FileMonitorEvent.RENAMED: "renamed",
    Gio.FileMonitorEvent.MOVED_IN: "moved_in",
}

file_monitors = []


class FileMonitor(IgnisGObject):
    """
    Monitor changes of the file or directory.

    Signals:
        - **"changed"** (``str``, ``str``): Emitted when the file or directory changed. Passes path and event type as arguments.

    Properties:
        - **path** (``str``, required, read-only): The path to the file or directory to be monitored.
        - **recursive** (``bool``, optional, read-only): Whether monitoring is recursive (monitor all subdirectories and files). Default: ``False``.
        - **flags** (``str | None``, optional, read-only): What the monitor will watch for. Default: ``None``.
        - **callback** (``Callable | None``, optional, read-write): A function to call when the file or directory changes. Default: ``None``.

    **Flags:**
        - **"none"**
        - **"watch_mounts"**
        - **"send_moved"**
        - **"watch_hard_links"**
        - **"watch_moves"**

        See `Gio.FileMonitorFlags <https://lazka.github.io/pgi-docs/Gio-2.0/flags.html#Gio.FileMonitorFlags>`_ for more info.

    **Event types:**
        - **"changed"**
        - **"changes_done_hint"**
        - **"moved_out"**
        - **"deleted"**
        - **"created"**
        - **"attribute_changed"**
        - **"pre_unmount"**
        - **"unmounted"**
        - **"moved"**
        - **"renamed"**
        - **"moved_in"**

        See `Gio.FileMonitorEvent <https://lazka.github.io/pgi-docs/index.html#Gio-2.0/enums.html#Gio.FileMonitorEvent>`_ for more info.

    **Example usage:**

    .. code-block::

        Utils.FileMonitor(
            path="path/to/something",
            recursive=False,
            callback=lambda path, event_type: print(path, event_type),
        )
    """

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str, str)),
    }

    def __init__(
        self,
        path: str,
        recursive: bool = False,
        flags: Optional[str] = None,
        callback: Optional[Callable] = None,
    ):
        super().__init__()
        self._file = Gio.File.new_for_path(path)
        self._monitor = self._file.monitor(FLAGS[flags], None)
        self._monitor.connect("changed", self.__on_change)

        self._path = path
        self._flags = flags
        self._callback = callback
        self._recursive = recursive

        self._sub_monitors: List[Gio.FileMonitor] = []
        self._sub_paths: List[str] = []

        if recursive:
            for root, dirs, _files in os.walk(path):
                for d in dirs:
                    subdir_path = os.path.join(root, d)
                    self.__add_submonitor(subdir_path)

        file_monitors.append(
            self
        )  # to prevent the garbage collector from collecting "self"

    def __on_change(self, file_monitor, file, other_file, event_type) -> None:
        path = file.get_path()
        if self._callback:
            self._callback(path, EVENT[event_type])
            self.emit("changed", path, EVENT[event_type])

        if self.recursive and os.path.isdir(path):
            self.__add_submonitor(path)

    def __add_submonitor(self, path: str) -> None:
        if path in self._sub_paths:
            return

        sub_gfile = Gio.File.new_for_path(path)
        monitor = sub_gfile.monitor(FLAGS[self.flags], None)
        monitor.connect("changed", self.__on_change)
        self._sub_monitors.append(monitor)
        self._sub_paths.append(path)

    @GObject.Property
    def path(self) -> str:
        return self._path

    @GObject.Property
    def flags(self) -> str | None:
        return self._flags

    @GObject.Property
    def callback(self) -> Callable | None:
        return self._callback

    @GObject.Property
    def recursive(self) -> bool:
        return self._recursive

    @callback.setter
    def callback(self, value: Callable) -> None:
        self._callback = value

    def cancel(self) -> None:
        """
        Cancel the monitoring process.
        """
        self._monitor.cancel()
