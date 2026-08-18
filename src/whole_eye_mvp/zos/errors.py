"""Typed failures for the ZOS-API session boundary."""


class ZosSessionError(RuntimeError):
    """Base class for failures while opening or closing a ZOS-API session."""


class ZosEnvironmentError(ZosSessionError):
    """The local OpticStudio/Python.NET environment is missing or inconsistent."""


class ZosInitializationError(ZosSessionError):
    """ZOSAPI_NetHelper could not initialize the requested OpticStudio install."""


class ZosConnectionError(ZosSessionError):
    """A standalone OpticStudio application or PrimarySystem could not be created."""


class ZosLicenseError(ZosSessionError):
    """The OpticStudio license is not valid for ZOS-API use."""


class ZosModeError(ZosSessionError):
    """The ZOS-API application is not running in standalone/server mode."""


class ZosCloseError(ZosSessionError):
    """The standalone OpticStudio application failed to close cleanly."""
