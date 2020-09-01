#!/usr/bin/env python3

"""
Python 3.6+ type hinting interface.
"""

from abc import ABC
from collections import abc
from enum import IntEnum
from io import BytesIO
from typing import Any, ByteString, ClassVar, Dict, Iterable, List, Tuple, Type, TypeVar, Union, get_type_hints

from pure_protobuf import serializers, types
from pure_protobuf.enums import WireType
from pure_protobuf.fields import Field, NonRepeatedField, PackedRepeatedField, UnpackedRepeatedField
from pure_protobuf.io_ import IO
from pure_protobuf.serializers import IntEnumSerializer, MessageSerializer, PackingSerializer, Serializer
from pure_protobuf.types import NoneType, BoolValue

try:
    import dataclasses
except ImportError:
    raise ImportError('dataclasses interface requires dataclasses support')

T = TypeVar('T')


@dataclasses.dataclass
class Message(ABC):
    """
    Virtual base class for a message type.
    See also: https://docs.python.org/3/library/abc.html#abc.ABCMeta.register
    """

    serializer: ClassVar[Serializer]
    type_url: ClassVar[str]

    def validate(self):
        self.serializer.validate(self)

    def dump(self, io: IO):
        """
        Serializes a message into a file-like object.
        """
        self.validate()
        self.serializer.dump(self, io)

    def dumps(self) -> bytes:
        """
        Serializes a message into a byte string.
        """
        with BytesIO() as io:
            self.dump(io)
            return io.getvalue()

    def merge_from(self: T, other: T):
        """
        Merge another message into the current one, as if with the ``Message::MergeFrom`` method.
        """
        for field_ in self.__protobuf_fields__.values():  # type: Field
            setattr(self, field_.name, field_.merge(
                getattr(self, field_.name),
                getattr(other, field_.name),
            ))


class OneOf:
    """
    Defines an oneof field.
    See also: https://developers.google.com/protocol-buffers/docs/proto3#oneof
    """

    def __init__(self, *fields: Field):
        self.fields = fields
        # TODO: implement automatic clearing.

    def __get__(self, message_: Message, owner: Type = None) -> Any:
        """
        Retrieve the currently set value (if any).
        """
        for field_ in self.fields:
            value = getattr(message_, field_.name)
            if value is not None:
                return value
        return None


def load(cls: Type[T], io: IO) -> T:
    """
    Deserializes a message from a file-like object.
    """
    return cls.serializer.load(io)


def loads(cls: Type[T], bytes_: bytes) -> T:
    """
    Deserializes a message from a byte string.
    """
    with BytesIO(bytes_) as io:
        return load(cls, io)


def field(number: int, *args, **kwargs) -> dataclasses.Field:
    """
    Convenience function to assign field numbers.
    Calls the standard ``dataclasses.field`` function with the metadata assigned.
    """
    return dataclasses.field(*args, metadata={'number': number}, **kwargs)


def optional_field(number: int, *args, **kwargs) -> dataclasses.Field:
    """
    Convenience function to define a field which is assigned `None` by default.
    """
    return field(number, *args, default=None, **kwargs)


def to_proto(cls: Type[T], indent_level: int = 0) -> str:
    def _add_repeated(field_) -> str:
        return "repeated " if isinstance(field_, UnpackedRepeatedField) or isinstance(field_, PackedRepeatedField) else ""

    return "\n".join(
        f"{' ' * 4 * indent_level}{msg_line}" for msg_line in [
            f"message {cls.__name__} {{",
            *[inner_class.to_proto(indent_level=indent_level + 1) for inner_class in [c for c in vars(cls).values() if isinstance(c, type(cls))]],
            *[f"{' ' * 4}{_add_repeated(field_)}{field_.proto_type} {field_.name} = {number};" for number, field_ in cls.__protobuf_fields__.items()],
            "}"
        ]
    )


def message(cls: Type[T]) -> Type[T]:
    """
    Returns the same class as was passed in, with additional dunder attributes needed for
    serialization and deserialization.
    """

    type_hints = get_type_hints(cls)

    # Used to list all fields and locate fields by field number.
    cls.__protobuf_fields__: Dict[int, Field] = dict(
        make_field(field_.metadata['number'], field_.name, type_hints[field_.name])
        for field_ in dataclasses.fields(cls)
    )

    # noinspection PyUnresolvedReferences
    Message.register(cls)
    cls.serializer = MessageSerializer(cls)
    cls.type_url = f'type.googleapis.com/{cls.__module__}.{cls.__name__}'
    cls.validate = Message.validate
    cls.dump = Message.dump
    cls.dumps = Message.dumps
    cls.merge_from = Message.merge_from
    cls.load = classmethod(load)
    cls.loads = classmethod(loads)
    cls.to_proto = classmethod(to_proto)

    return cls


def make_field(number: int, name: str, type_: Any) -> Tuple[int, Field]:
    """
    Figure out how to serialize and de-serialize the field.
    Returns the field number and a corresponding ``Field`` instance.
    """
    is_optional, type_ = get_optional(type_)
    is_repeated, type_ = get_repeated(type_)

    serializer: Serializer
    if isinstance(type_, type) and issubclass(type_, Message):
        # Embedded message.
        serializer = PackingSerializer(type_.serializer)
    elif isinstance(type_, type) and issubclass(type_, IntEnum):
        # Enumeration.
        # See also: https://developers.google.com/protocol-buffers/docs/proto3#enum
        serializer = IntEnumSerializer(type_)
    else:
        # Predefined type.
        try:
            serializer = SERIALIZERS[type_]
        except KeyError as e:
            raise TypeError(f'type is not serializable: {type_}') from e

    # is an embedded message ?
    if hasattr(serializer, "inner"):
        # we don't resolve (here) the dependency or "inclusion" of embedded message
        # this resolution will be handle by protoc after in build stage
        # => more simpler for us :p
        protobuf_type = serializer.inner.type_.__name__
    else:
        protobuf_type = PYTHON_TO_PROTOBUF_TYPES.get(type_, None)

    if not is_repeated:
        # Non-repeated field.
        return number, NonRepeatedField(number, name, serializer, is_optional, protobuf_type)
    elif serializer.wire_type != WireType.BYTES:
        # Repeated fields of scalar numeric types are packed by default.
        # See also: https://developers.google.com/protocol-buffers/docs/encoding#packed
        return number, PackedRepeatedField(number, name, serializer, protobuf_type)
    else:
        # Repeated field of other type.
        return number, UnpackedRepeatedField(number, name, serializer, protobuf_type)


def get_optional(type_: Any) -> Tuple[bool, Any]:
    """
    Extracts ``Optional`` type annotation if present.
    This may be useful if a user wants to annotate a field with ``Optional[...]`` and set default to ``None``.
    """
    if getattr(type_, '__origin__', None) is Union:
        args = set(type_.__args__)

        # Check if it's a union of `NoneType` and something else.
        if len(args) == 2 and NoneType in args:
            # Extract inner type.
            type_, = args - {NoneType}
            return True, type_

    return False, type_


def get_repeated(type_: Any) -> Tuple[bool, Any]:
    """
    Extracts ``repeated`` modifier if present.
    """
    if getattr(type_, '__origin__', None) in (list, List, Iterable, abc.Iterable):
        type_, = type_.__args__
        return True, type_
    else:
        return False, type_


SERIALIZERS: Dict[Any, Serializer] = {
    bool: serializers.BooleanSerializer(),
    bytes: serializers.bytes_serializer,
    ByteString: serializers.bytes_serializer,
    float: serializers.FloatSerializer(),
    int: serializers.signed_varint_serializer,  # is not a part of the standard
    str: serializers.StringSerializer(),
    types.double: serializers.DoubleSerializer(),
    types.fixed32: serializers.UnsignedFixed32Serializer(),
    types.fixed64: serializers.UnsignedFixed64Serializer(),
    types.sfixed32: serializers.SignedFixed32Serializer(),
    types.sfixed64: serializers.SignedFixed64Serializer(),
    types.sint32: serializers.SignedInt32Serializer(),
    types.sint64: serializers.SignedInt64Serializer(),
    types.uint32: serializers.UnsignedInt32Serializer(),
    types.uint64: serializers.UnsignedInt64Serializer(),
    types.uint: serializers.unsigned_varint_serializer,  # is not a part of the standard
    # TODO: `map`.
    # google.protobuf
    types.UInt32Value: serializers.UnsignedInt32Serializer(),
    BoolValue: serializers.BooleanSerializer(),
    types.StringValue: serializers.StringSerializer(),
}

PYTHON_TO_PROTOBUF_TYPES: Dict[Any, str] = {
    bool: "bool",
    bytes: "str",
    ByteString: "str",
    float: "float",
    int: "int32",
    str: "string",
    types.double: "double",
    types.fixed32: "fixed32",
    types.fixed64: "fixed64",
    types.sfixed32: "sfixed32",
    types.sfixed64: "sfixed64",
    types.sint32: "sint32",
    types.sint64: "sint64",
    types.uint32: "uint32",
    types.uint64: "uint64",
    types.uint: "uint32",
    # TODO: `map`.
    types.UInt32Value: "google.protobuf.UInt32Value",
    types.BoolValue: "google.protobuf.BoolValue",
    types.StringValue: "google.protobuf.StringValue",
}

__all__ = [
    'field',
    'load',
    'loads',
    'message',
    'Message',
]
