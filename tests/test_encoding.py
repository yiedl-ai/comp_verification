from comp_verification.encoding import (
    decode_address_array,
    digest_to_cid_v0,
    encode_address,
    file_cid_v0,
    function_selector,
    single_block_file_cid_v0,
)


def test_contract_function_selectors_match_solidity() -> None:
    assert function_selector("getDatasetHash(uint32)") == "0x39e28777"
    assert function_selector("getAllSubmitters(uint32)") == "0x56740500"
    assert function_selector("getHistoricalStakers(uint32)") == "0x253122ec"
    assert function_selector("getSubmission(uint32,address)") == "0x60cdb6cc"


def test_first_dataset_digest_converts_to_expected_cid() -> None:
    digest = "0x92462fb3bd6ad5065a0597ea244f0a8d34c7288f52bbe2d25a0ebffcd3423714"
    assert digest_to_cid_v0(digest) == "QmYBeJjXhYAd58BDjjMZ577m3j6ZzrSEpHu6eYm12zxcsD"


def test_single_block_unixfs_cid_v0() -> None:
    assert (
        single_block_file_cid_v0(b"previously downloaded result evidence")
        == "QmWnnVnb1v4QvC7fBLAkcJe5ZXoR6zZrw6rjNCngt7aJdQ"
    )


def test_balanced_multiblock_unixfs_cid_v0(tmp_path) -> None:
    path = tmp_path / "large.bin"
    path.write_bytes(b"a" * 300_000)

    assert file_cid_v0(path) == "QmYCTciJdFNMNUPCHSNS6dKMmUAqkGQ9tQQeGgbELhQQcn"


def test_decode_address_array() -> None:
    addresses = [
        "0x1111111111111111111111111111111111111111",
        "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
    ]
    encoded = "0x" + "".join(
        [
            (32).to_bytes(32, "big").hex(),
            (2).to_bytes(32, "big").hex(),
            encode_address(addresses[0]),
            encode_address(addresses[1]),
        ]
    )
    assert decode_address_array(encoded) == addresses
