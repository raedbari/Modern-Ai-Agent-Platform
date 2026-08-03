"""Tests for administrative agent configuration schemas."""

import pytest
from pydantic import ValidationError

from backend.app.api.schemas.admin import AgentConfigUpdate


def test_empty_patch_has_no_changes() -> None:
    update = AgentConfigUpdate()

    assert update.model_fields_set == set()
    assert not update.has_changes()


def test_name_is_normalized_and_marked_as_changed() -> None:
    update = AgentConfigUpdate(name="  Support Agent  ")

    assert update.name == "Support Agent"
    assert update.model_fields_set == {"name"}
    assert update.has_changes()


@pytest.mark.parametrize(
    "payload",
    [
        {"name": None},
        {"knowledge_mode": None},
    ],
)
def test_non_nullable_fields_reject_explicit_null(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(**payload)


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        "     ",
    ],
)
def test_name_rejects_empty_normalized_values(name: str) -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(name=name)


def test_name_rejects_more_than_255_characters() -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(name="a" * 256)


@pytest.mark.parametrize(
    "mode",
    [
        "required",
        "preferred",
        "disabled",
    ],
)
def test_accepts_supported_knowledge_modes(mode: str) -> None:
    update = AgentConfigUpdate(knowledge_mode=mode)

    assert update.knowledge_mode == mode
    assert update.model_fields_set == {"knowledge_mode"}


def test_rejects_unknown_knowledge_mode() -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(knowledge_mode="automatic")


def test_nullable_fields_can_be_explicitly_cleared() -> None:
    update = AgentConfigUpdate(
        system_prompt=None,
        contact_message=None,
    )

    assert update.system_prompt is None
    assert update.contact_message is None
    assert update.model_fields_set == {
        "system_prompt",
        "contact_message",
    }


def test_empty_strings_are_distinct_from_null_for_nullable_fields() -> None:
    update = AgentConfigUpdate(
        system_prompt="",
        contact_message="",
    )

    assert update.system_prompt == ""
    assert update.contact_message == ""


def test_system_prompt_length_limit() -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(system_prompt="a" * 10_001)


def test_contact_message_length_limit() -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(contact_message="a" * 1_001)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentConfigUpdate(
            name="Agent",
            unsupported_field="value",
        )


def test_absent_fields_are_not_marked_as_changed() -> None:
    update = AgentConfigUpdate(name="Agent")

    assert "name" in update.model_fields_set
    assert "system_prompt" not in update.model_fields_set
    assert "knowledge_mode" not in update.model_fields_set
    assert "contact_message" not in update.model_fields_set


def test_json_schema_does_not_advertise_null_for_required_values() -> None:
    properties = AgentConfigUpdate.model_json_schema()["properties"]

    assert properties["name"]["type"] == "string"
    assert properties["knowledge_mode"]["type"] == "string"
    assert set(properties["knowledge_mode"]["enum"]) == {
        "required",
        "preferred",
        "disabled",
    }
