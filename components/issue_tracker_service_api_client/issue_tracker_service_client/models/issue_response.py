from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="IssueResponse")


@_attrs_define
class IssueResponse:
    """
    Attributes:
        id (str):
        title (str):
        desc (str):
        status (str):
        board_id (str):
        members (list[str] | None | Unset):
        due_date (None | str | Unset):
    """

    id: str
    title: str
    desc: str
    status: str
    board_id: str
    members: list[str] | None | Unset = UNSET
    due_date: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        title = self.title

        desc = self.desc

        status = self.status

        board_id = self.board_id

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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "title": title,
                "desc": desc,
                "status": status,
                "board_id": board_id,
            }
        )
        if members is not UNSET:
            field_dict["members"] = members
        if due_date is not UNSET:
            field_dict["due_date"] = due_date

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        title = d.pop("title")

        desc = d.pop("desc")

        status = d.pop("status")

        board_id = d.pop("board_id")

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

        issue_response = cls(
            id=id,
            title=title,
            desc=desc,
            status=status,
            board_id=board_id,
            members=members,
            due_date=due_date,
        )

        issue_response.additional_properties = d
        return issue_response

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
