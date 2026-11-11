"""Exception hierarchy. Every error carries a message suitable for end users."""

from __future__ import annotations


class OdtError(Exception):
    """Base class for expected, user-reportable failures."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def user_text(self) -> str:
        return f"{self.message}\n\n{self.hint}" if self.hint else self.message


class OperationCancelled(OdtError):
    def __init__(self, message: str = "Operation cancelled.") -> None:
        super().__init__(message)


class UnsafePathError(OdtError):
    """A path would escape its root, or uses a symlink / forbidden construct."""


class ArchiveError(OdtError):
    """Archive is invalid, unsafe or not an Onion release."""


class IntegrityError(OdtError):
    """Downloaded or written data does not match its expected size or hash."""


class DownloadError(OdtError):
    pass


class ReleaseMetadataError(OdtError):
    pass


class InsufficientSpaceError(OdtError):
    def __init__(self, required: int, available: int, what: str = "this operation") -> None:
        super().__init__(
            f"Not enough free space for {what}: {required / 1_048_576:.0f} MB required, "
            f"{available / 1_048_576:.0f} MB available."
        )
        self.required = required
        self.available = available


class DeviceError(OdtError):
    """A device operation failed."""


class ProtectedDeviceError(DeviceError):
    """Refused: the device is (or may be) a system disk or otherwise not eligible."""


class DeviceChangedError(DeviceError):
    """The device no longer matches the identity the user confirmed (TOCTOU guard)."""


class BackendUnavailableError(DeviceError):
    """UDisks2 / D-Bus or another required host service is not available."""


class HostToolMissingError(OdtError):
    def __init__(self, tool: str, package_hint: str) -> None:
        super().__init__(
            f"The host program '{tool}' is required but was not found.",
            hint=f"Install it with your distribution's package manager ({package_hint}).",
        )
        self.tool = tool


class ValidationError(OdtError):
    """User input is invalid."""


class NotOnionCardError(OdtError):
    pass
