"""Browser-safe schemas for Widget bootstrap and administration."""

from __future__ import annotations

from datetime import datetime

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


HexColor = Annotated[
    str,
    StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$"),
]
PublicWidgetId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=24,
        max_length=64,
        pattern=r"^wgt_[A-Za-z0-9_-]+$",
    ),
]
AllowedOrigin = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class WidgetTheme(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    primary_color: HexColor = Field("#2563EB", alias="primaryColor")
    text_color: HexColor = Field("#FFFFFF", alias="textColor")
    launcher_color: HexColor = Field("#2563EB", alias="launcherColor")
    header_color: HexColor = Field("#2563EB", alias="headerColor")
    user_message_color: HexColor = Field(
        "#2563EB",
        alias="userMessageColor",
    )
    position: Literal["left", "right"] = "right"
    appearance: Literal["light", "dark"] = "light"

    @field_validator(
        "primary_color",
        "text_color",
        "launcher_color",
        "header_color",
        "user_message_color",
    )
    @classmethod
    def normalize_hex_color(cls, value: str) -> str:
        return value.upper()

    @staticmethod
    def _relative_luminance(color: str) -> float:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    @classmethod
    def _contrast_ratio(cls, foreground: str, background: str) -> float:
        first = cls._relative_luminance(foreground)
        second = cls._relative_luminance(background)
        lighter, darker = max(first, second), min(first, second)
        return (lighter + 0.05) / (darker + 0.05)

    @model_validator(mode="after")
    def validate_accessible_contrast(self) -> "WidgetTheme":
        backgrounds = {
            "primaryColor": self.primary_color,
            "launcherColor": self.launcher_color,
            "headerColor": self.header_color,
            "userMessageColor": self.user_message_color,
        }
        failing = [
            name
            for name, color in backgrounds.items()
            if self._contrast_ratio(self.text_color, color) < 4.5
        ]
        if failing:
            raise ValueError(
                "textColor must have a WCAG AA contrast ratio of at least "
                f"4.5:1 against {', '.join(failing)}."
            )
        return self


class WidgetBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    widget_id: PublicWidgetId


class WidgetPublicConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    widget_id: str
    display_name: str
    greeting: str | None
    theme: WidgetTheme


class WidgetBootstrapResponse(BaseModel):
    session_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(gt=0)
    session_id: str
    widget: WidgetPublicConfig


class WidgetSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    is_enabled: bool = False
    display_name: str | None = Field(default=None, max_length=255)
    greeting: str | None = Field(default=None, max_length=500)
    theme: WidgetTheme = Field(default_factory=WidgetTheme)
    allowed_origins: list[AllowedOrigin] = Field(
        default_factory=list,
        max_length=50,
    )


class WidgetSettingsResponse(BaseModel):
    tenant_id: str
    agent_id: str
    public_widget_id: str
    is_enabled: bool
    display_name: str | None
    greeting: str | None
    theme: WidgetTheme
    allowed_origins: list[str]

ConnectorType = Literal[
    "wordpress",
    "react_next",
    "managed",
    "custom",
]


class WidgetConnectorPairingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: AllowedOrigin
    connector_type: ConnectorType


class WidgetConnectorPairingCreated(BaseModel):
    pairing_id: str
    pairing_code: str
    origin: str
    connector_type: ConnectorType
    expires_at: datetime
    expires_in: int = Field(gt=0)


class WidgetConnectorPairingRedeem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(
        min_length=8,
        max_length=64,
    )

    @field_validator("pairing_code")
    @classmethod
    def normalize_pairing_code(
        cls,
        value: str,
    ) -> str:
        return value.strip().upper()


class WidgetConnectorPairingConnected(BaseModel):
    connected: Literal[True] = True
    widget_id: PublicWidgetId
    origin: str
    connector_type: ConnectorType


WidgetInstallationState = Literal[
    "pending",
    "verified",
    "expired",
    "failed",
]


class WidgetInstallationChecks(BaseModel):
    script_loaded: bool
    origin_valid: bool
    public_config_loaded: bool
    bootstrap_succeeded: bool


class WidgetInstallationStatus(BaseModel):
    pairing_id: str | None = None
    status: WidgetInstallationState
    origin: str | None = None
    expires_at: datetime | None = None
    connected_at: datetime | None = None
    error_code: str | None = None
    detail: str
    checks: WidgetInstallationChecks
