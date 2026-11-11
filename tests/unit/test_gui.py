"""GUI smoke and safety tests (offscreen Qt)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from conftest import make_onion_card
from onion_desktop.core.models import Disk, Partition
from onion_desktop.gui import dialogs
from onion_desktop.gui.main_window import PAGES, MainWindow
from onion_desktop.gui.pages.sdcards import FormatDialog
from onion_desktop.gui.state import AppState
from onion_desktop.linux.disk_manager import DiskManager
from onion_desktop.settings import Settings

pytestmark = pytest.mark.gui


class Backend:
    name, can_modify = "fake", True

    def __init__(self, disks):
        self.disks = disks

    def list_disks(self):
        return self.disks


def _disks(mount):
    return [Disk("/dev/sda", "sda", 500 * 10**9, model="System SSD", bus="sata",
                 partitions=(Partition("/dev/sda1", 1, 1, "ext4", mount_points=("/",)),)),
            Disk("/dev/sdb", "sdb", 32 * 10**9, model="Reader", bus="usb", removable=True, hotplug=True,
                 partitions=(Partition("/dev/sdb1", 1, 1, "vfat", "FAT32", mount_points=(str(mount),)),)),
            Disk("/dev/sdc", "sdc", 64 * 10**9, model="Reader2", bus="usb", removable=True, hotplug=True)]


@pytest.fixture
def state(qtbot, tmp_path):
    card = make_onion_card(tmp_path / "card")
    mgr = DiskManager(Backend(_disks(card)), system_probe=lambda: {"sda": ["hosts system mount point /"]})
    st = AppState(Settings(downloads_dir=str(tmp_path / "dl"), backups_dir=str(tmp_path / "bk")), mgr)
    return st


def test_main_window_pages_and_single_card_autoselect(qtbot, state):
    win = MainWindow(state)
    qtbot.addWidget(win)
    state.refresh()
    qtbot.waitUntil(lambda: state.card is not None, timeout=5000)
    assert state.target is not None and str(state.target.path).endswith("card")
    for i, (key, _) in enumerate(PAGES):
        win.sidebar.setCurrentRow(i)
        assert win.stack.currentWidget() is win.pages[key]


def test_format_dialog_has_no_default_and_hides_system_disk(qtbot, state):
    state.refresh()
    qtbot.waitUntil(lambda: bool(state.disks), timeout=5000)
    dlg = FormatDialog(state)
    qtbot.addWidget(dlg)
    assert dlg.selected() is None and not dlg.next.isEnabled()
    devices = [dlg.combo.itemData(i).device for i in range(1, dlg.combo.count())]
    assert devices == ["/dev/sdb", "/dev/sdc"]
    dlg.combo.setCurrentIndex(1)
    assert dlg.next.isEnabled() and "everything will be lost" in dlg.warn.text().lower()


def test_typed_confirmation(qtbot):
    dlg = dialogs.TypedConfirmDialog(None, "t", "m", "/dev/sdb")
    qtbot.addWidget(dlg)
    assert not dlg.ok.isEnabled()
    dlg.edit.setText("/dev/sd")
    assert not dlg.ok.isEnabled()
    dlg.edit.setText("/dev/sdb")
    assert dlg.ok.isEnabled()
