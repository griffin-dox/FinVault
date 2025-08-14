from typing import Optional
from pydantic import BaseModel, Field


class DeviceTelemetry(BaseModel):
    browser: Optional[str] = Field(None, description="e.g., Chrome 139")
    os: Optional[str] = Field(None, description="e.g., Windows, macOS")
    screen: Optional[str] = Field(None, description="e.g., 1920x1080")
    timezone: Optional[str] = None
    language: Optional[str] = None

    # Optional richer fields (ignored by backend if missing)
    userAgent: Optional[str] = None
    deviceClass: Optional[str] = None
    screenWidth: Optional[int] = None
    screenHeight: Optional[int] = None
    viewportWidth: Optional[int] = None
    viewportHeight: Optional[int] = None
    pixelRatio: Optional[float] = None
    hardwareConcurrency: Optional[int] = None
    deviceMemory: Optional[float] = None
    touchSupport: Optional[bool] = None


class TelemetryIn(BaseModel):
    device: DeviceTelemetry


class TelemetryOut(BaseModel):
    ok: bool = True
    device_id: Optional[str] = None
    ip_id: Optional[str] = None
    device_hash: Optional[str] = None
