from gi.repository import GObject  # type: ignore
from ignis.base_service import BaseService
from ._imports import GnomeBluetooth
from .device import BluetoothDevice
from .constants import ADAPTER_STATE


class BluetoothService(BaseService):
    """
    A Bluetooth service.
    Requires ``gnome-bluetooth-3.0``.
    """

    def __init__(self) -> None:
        super().__init__()

        self._client = GnomeBluetooth.Client.new()
        self._devices: dict[str, BluetoothDevice] = {}

        self._client.connect("device-added", self.__add_device)
        self._client.connect("device-removed", self.__remove_device)

        for key, value in {
            "default-adapter-powered": "powered",
            "default-adapter-setup-mode": "setup-mode",
            "default-adapter-state": "state",
        }.items():
            self._client.connect(
                f"notify::{key}", lambda x, y, value=value: self.notify(value)
            )

        for gdevice in self._client.get_devices():
            self.__add_device(None, gdevice)  # type: ignore

    @GObject.Signal(arg_types=(BluetoothDevice,))
    def device_added(self, *args):
        """
        - Signal

        Emitted when a Bluetooth device has been added.

        Args:
            device (:class:`~ignis.services.bluetooth.BluetoothDevice`): The instance of the Bluetooth device.
        """

    @GObject.Property
    def client(self) -> GnomeBluetooth.Client:
        """
        - read-only

        An instance of ``GnomeBluetooth.Client``.
        """
        return self._client

    @GObject.Property
    def devices(self) -> list[BluetoothDevice]:
        """
        - read-only

        A list of all Bluetooth devices.
        """
        return list(self._devices.values())

    @GObject.Property
    def connected_devices(self) -> list[BluetoothDevice]:
        """
        - read-only

        A list of currently connected Bluetooth devices.
        """
        return [i for i in self._devices.values() if i.connected]

    @GObject.Property
    def powered(self) -> bool:
        """
        - read-write

        Whether the default Bluetooth adapter is powered.
        """
        return self._client.props.default_adapter_powered

    @powered.setter
    def powered(self, value: bool) -> None:
        self._client.props.default_adapter_powered = value

    @GObject.Property
    def state(self) -> str:
        """
        - read-only

        The current state of the default Bluetooth adapter.

        Adapter state:
            - absent
            - on
            - turning-on
            - turning-off
            - off
        """
        return ADAPTER_STATE.get(self._client.props.default_adapter_state, "absent")

    @GObject.Property
    def setup_mode(self) -> bool:
        """
        - read-write

        Whether the default Bluetooth adapter is in setup mode (discoverable, and discovering).

        Set to ``True`` to start scanning devices.
        """
        return self._client.props.default_adapter_setup_mode

    @setup_mode.setter
    def setup_mode(self, value: bool) -> None:
        self._client.props.default_adapter_setup_mode = value

    def __add_device(self, x, gdevice: GnomeBluetooth.Device) -> None:
        device = BluetoothDevice(self._client, gdevice)
        self._devices[gdevice.get_object_path()] = device
        self.emit("device-added", device)
        device.connect(
            "notify::connected", lambda x, y: self.notify("connected-devices")
        )
        self.notify("devices")

    def __remove_device(self, x, object_path: str) -> None:
        if object_path not in self._devices:
            return

        device = self._devices.pop(object_path)
        device.emit("removed")
        self.notify("connected-devices")
        self.notify("devices")