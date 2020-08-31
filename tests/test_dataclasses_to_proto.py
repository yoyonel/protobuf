# noinspection PyCompatibility
from dataclasses import dataclass
from typing import Type, Any, Tuple, List

from pytest import fixture

from pure_protobuf.dataclasses_ import field, message
from pure_protobuf.types import uint32, UInt32Value, BoolValue, StringValue


@fixture
def class_git_info() -> Tuple[Type, str]:
    @message
    @dataclass
    class GitInfo:
        branch_name: str = field(1)
        committed_datetime: str = field(2)
        hexsha: str = field(3)

    return GitInfo, """message GitInfo {
    string branch_name = 1;
    string committed_datetime = 2;
    string hexsha = 3;
}"""


@fixture
def class_input_ref_data_category() -> Tuple[Type, str]:
    @message
    @dataclass
    class InputRefDataCategory:
        id: uint32 = field(1)
        name: str = field(2)
        parent_id: UInt32Value = field(3)

    return InputRefDataCategory, """message InputRefDataCategory {
    uint32 id = 1;
    string name = 2;
    google.protobuf.UInt32Value parent_id = 3;
}"""


@fixture
def class_input_ref_data_skill() -> Tuple[Type, str]:
    @message
    @dataclass
    class InputRefDataSkill:
        name: str = field(2)
        occurrences: uint32 = field(4)

        skill_id: UInt32Value = field(1)
        category_id: UInt32Value = field(3)
        parent_id: UInt32Value = field(5)
        active: BoolValue = field(6)

    return InputRefDataSkill, """message InputRefDataSkill {
    string name = 2;
    uint32 occurrences = 4;
    google.protobuf.UInt32Value skill_id = 1;
    google.protobuf.UInt32Value category_id = 3;
    google.protobuf.UInt32Value parent_id = 5;
    google.protobuf.BoolValue active = 6;
}"""


@fixture
def class_formation() -> Tuple[Type, str]:
    @message
    @dataclass
    class Formation:
        line: str = field(9)
        score: uint32 = field(10)
        code: StringValue = field(1)
        name: StringValue = field(2)
        university: StringValue = field(3)
        location: StringValue = field(4)
        start_year: UInt32Value = field(5)
        start_month: UInt32Value = field(6)
        end_year: UInt32Value = field(7)
        end_month: UInt32Value = field(8)
        country: StringValue = field(11)

    return Formation, """message Formation {
    string line = 9;
    uint32 score = 10;
    google.protobuf.StringValue code = 1;
    google.protobuf.StringValue name = 2;
    google.protobuf.StringValue university = 3;
    google.protobuf.StringValue location = 4;
    google.protobuf.UInt32Value start_year = 5;
    google.protobuf.UInt32Value start_month = 6;
    google.protobuf.UInt32Value end_year = 7;
    google.protobuf.UInt32Value end_month = 8;
    google.protobuf.StringValue country = 11;
}"""


@fixture
def class_palability_skill() -> Tuple[Type, str]:
    @message
    @dataclass
    class PalabilitySkill:
        score: float = field(1)
        skills: List[str] = field(2)

    return PalabilitySkill, """message PalabilitySkill {
    float score = 1;
    repeated string skills = 2;
}"""


@fixture
def class_full_location() -> Tuple[Type, str]:
    @message
    @dataclass
    class FullLocation:
        score: float = field(1)
        skills: List[str] = field(2)

    return FullLocation, """message FullLocation {
    float score = 1;
    repeated string skills = 2;
}"""


@fixture
def class_compared_location(class_full_location: Tuple[Type, str]) -> Tuple[Type, str]:
    class_full_location, protobuf_full_location = class_full_location

    @message
    @dataclass
    class ComparedLocation:
        inside: bool = field(1)
        hierarchy: List[class_full_location] = field(2)
        likes: bool = field(3)
        location: str = field(4)
        result: List[str] = field(5)

    return ComparedLocation, """message ComparedLocation {
    bool inside = 1;
    repeated FullLocation hierarchy = 2;
    bool likes = 3;
    string location = 4;
    repeated string result = 5;
}"""


def test_class_git_info_to_proto(class_git_info: Tuple[Any, str]):
    class_git_info, expected_result = class_git_info
    assert class_git_info.to_proto() == expected_result


def test_class_input_ref_data_category_to_proto(class_input_ref_data_category: Tuple[Any, str]):
    class_input_ref_data_category, expected_result = class_input_ref_data_category
    assert class_input_ref_data_category.to_proto() == expected_result


def test_class_input_ref_data_skill_to_proto(class_input_ref_data_skill: Tuple[Any, str]):
    class_input_ref_data_skill, expected_result = class_input_ref_data_skill
    assert class_input_ref_data_skill.to_proto() == expected_result


def test_class_formation_to_proto(class_formation: Tuple[Any, str]):
    class_formation, expected_result = class_formation
    assert class_formation.to_proto() == expected_result


def test_class_palability_skill_to_proto(class_palability_skill: Tuple[Any, str]):
    class_palability_skill, expected_result = class_palability_skill
    assert class_palability_skill.to_proto() == expected_result


def test_class_compared_location_to_proto(class_full_location: Tuple[Any, str], class_compared_location: Tuple[Any, str]):
    class_full_location, expected_protobuf_full_location = class_full_location
    class_compared_location, expected_protobuf_compared_location = class_compared_location
    assert class_full_location.to_proto() == expected_protobuf_full_location
    assert class_compared_location.to_proto() == expected_protobuf_compared_location
