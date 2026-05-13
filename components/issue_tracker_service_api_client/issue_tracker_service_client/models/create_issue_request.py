from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CreateIssueRequest")


@_attrs_define
class CreateIssueRequest:
    """
    Attributes:
        title (str):
        board_id (str):
        desc (None | str | Unset):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
        status (str | Unset):  Default: 'to_do'.
    """

    title: str
    board_id: str
    desc: None | str | Unset = UNSET
    members: list[str] | None | Unset = UNSET
    due_date: None | str | Unset = UNSET
    status: str | Unset = "to_do"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title = self.title

        board_id = self.board_id

        desc: None | str | Unset
        if isinstance(self.desc, Unset):
            desc = UNSET
        else:
            desc = self.desc

        members: list[str] | None | Unset
        if isinstance(self.members, Unset):
            members = UNSET
        elif isinstance(self.members, list):
            members = self.members

        else:
            members = self.members

        due_date: None | str | Unset
        if isinstance(self.due_date, Unset):
            due_date = UNSET
        else:
            due_date = self.due_date

        status = self.status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "board_id": board_id,
            }
        )
        if desc is not UNSET:
            field_dict["desc"] = desc
        if members is not UNSET:
            field_dict["members"] = members
        if due_date is not UNSET:
            field_dict["due_date"] = due_date
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        title = d.pop("title")

        board_id = d.pop("board_id")

        def _parse_desc(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        desc = _parse_desc(d.pop("desc", UNSET))

        def _parse_members(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                members_type_0 = cast(list[str], data)

                return members_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        members = _parse_members(d.pop("members", UNSET))

        def _parse_due_date(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        due_date = _parse_due_date(d.pop("due_date", UNSET))

        status = d.pop("status", UNSET)

        create_issue_request = cls(
            title=title,
            board_id=board_id,
            desc=desc,
            members=members,
            due_date=due_date,
            status=status,
        )

        create_issue_request.additional_properties = d
        return create_issue_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
