"""Small, explicit Ethereum ABI and CID helpers used by the verifier."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from Crypto.Hash import keccak

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def function_selector(signature: str) -> str:
    digest = keccak.new(digest_bits=256)
    digest.update(signature.encode("ascii"))
    return "0x" + digest.hexdigest()[:8]


def event_topic(signature: str) -> str:
    """Return the full Keccak-256 topic for an Ethereum event signature."""

    digest = keccak.new(digest_bits=256)
    digest.update(signature.encode("ascii"))
    return "0x" + digest.hexdigest()


def encode_uint(value: int) -> str:
    if value < 0 or value >= 2**256:
        raise ValueError("uint256 value out of range")
    return value.to_bytes(32, "big").hex()


def encode_address(address: str) -> str:
    raw = address.removeprefix("0x")
    if len(raw) != 40:
        raise ValueError(f"invalid Ethereum address: {address}")
    try:
        int(raw, 16)
    except ValueError as error:
        raise ValueError(f"invalid Ethereum address: {address}") from error
    return "0" * 24 + raw.lower()


def encode_call(signature: str, *arguments: str) -> str:
    return function_selector(signature) + "".join(arguments)


def decode_uint(result: str) -> int:
    return int(result, 16)


def decode_bytes32(result: str) -> str:
    raw = result.removeprefix("0x")
    if len(raw) < 64:
        raw = raw.rjust(64, "0")
    if len(raw) != 64:
        raise ValueError(f"expected one bytes32 word, got {len(raw) // 2} bytes")
    return "0x" + raw.lower()


def decode_address_array(result: str) -> list[str]:
    raw = result.removeprefix("0x")
    if len(raw) < 128 or len(raw) % 64:
        raise ValueError("invalid ABI-encoded address array")
    offset_words = int(raw[:64], 16) // 32
    length_index = offset_words * 64
    count = int(raw[length_index : length_index + 64], 16)
    values_index = length_index + 64
    end = values_index + count * 64
    if end > len(raw):
        raise ValueError("truncated ABI-encoded address array")
    return [
        "0x" + raw[index + 24 : index + 64].lower()
        for index in range(values_index, end, 64)
    ]


def base58_encode(data: bytes) -> str:
    number = int.from_bytes(data, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = _BASE58_ALPHABET[remainder] + encoded
    zero_prefix = len(data) - len(data.lstrip(b"\0"))
    return "1" * zero_prefix + encoded


def digest_to_cid_v0(digest: str) -> str | None:
    """Convert the contract's SHA-256 digest to its CIDv0 representation."""

    normalized = digest.removeprefix("0x")
    if normalized == "00" * 32:
        return None
    if len(normalized) != 64:
        raise ValueError("CID digest must be exactly 32 bytes")
    return base58_encode(bytes.fromhex("1220" + normalized))


def single_block_file_cid_v0(content: bytes) -> str:
    """Compute the CIDv0 produced by the UnixFS importer for one file block."""

    unixfs = (
        b"\x08\x02"
        + b"\x12"
        + _protobuf_varint(len(content))
        + content
        + b"\x18"
        + _protobuf_varint(len(content))
    )
    dag_pb_node = b"\x0a" + _protobuf_varint(len(unixfs)) + unixfs
    multihash = b"\x12\x20" + hashlib.sha256(dag_pb_node).digest()
    return base58_encode(multihash)


@dataclass(frozen=True)
class _UnixFsNode:
    multihash: bytes
    file_size: int
    cumulative_size: int


def file_cid_v0(
    path: Path,
    *,
    chunk_size: int = 256 * 1024,
    max_links: int = 174,
) -> str:
    """Reproduce the default balanced UnixFS CIDv0 importer for a local file."""

    if chunk_size <= 0 or max_links <= 1:
        raise ValueError("invalid UnixFS importer parameters")
    leaves: list[_UnixFsNode] = []
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            leaves.append(_unixfs_leaf(chunk))
    if not leaves:
        leaves.append(_unixfs_leaf(b""))
    nodes = leaves
    while len(nodes) > 1:
        nodes = [
            _unixfs_parent(nodes[start : start + max_links])
            for start in range(0, len(nodes), max_links)
        ]
    return base58_encode(nodes[0].multihash)


def _unixfs_leaf(content: bytes) -> _UnixFsNode:
    unixfs = (
        b"\x08\x02"
        + b"\x12"
        + _protobuf_varint(len(content))
        + content
        + b"\x18"
        + _protobuf_varint(len(content))
    )
    dag_pb_node = b"\x0a" + _protobuf_varint(len(unixfs)) + unixfs
    multihash = b"\x12\x20" + hashlib.sha256(dag_pb_node).digest()
    return _UnixFsNode(multihash, len(content), len(dag_pb_node))


def _unixfs_parent(children: list[_UnixFsNode]) -> _UnixFsNode:
    file_size = sum(child.file_size for child in children)
    unixfs = b"\x08\x02" + b"\x18" + _protobuf_varint(file_size)
    # The historical Go UnixFS encoder emitted repeated uint64 fields unpacked.
    unixfs += b"".join(
        b"\x20" + _protobuf_varint(child.file_size) for child in children
    )
    links = b""
    for child in children:
        link = (
            b"\x0a"
            + _protobuf_varint(len(child.multihash))
            + child.multihash
            + b"\x12\x00"
            + b"\x18"
            + _protobuf_varint(child.cumulative_size)
        )
        links += b"\x12" + _protobuf_varint(len(link)) + link
    # dag-pb's historical Go marshaler writes Links before Data.
    dag_pb_node = links + b"\x0a" + _protobuf_varint(len(unixfs)) + unixfs
    multihash = b"\x12\x20" + hashlib.sha256(dag_pb_node).digest()
    cumulative_size = len(dag_pb_node) + sum(
        child.cumulative_size for child in children
    )
    return _UnixFsNode(multihash, file_size, cumulative_size)


def _protobuf_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("protobuf varint must be non-negative")
    encoded = bytearray()
    while value >= 0x80:
        encoded.append((value & 0x7F) | 0x80)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)
