"""Network constants for the historical competition contracts."""

from typing import Final

CHAIN_ID: Final = 137
IPFS_GATEWAY: Final = "https://yiedl-comp.mypinata.cloud/ipfs"
REGISTRY_ADDRESS: Final = "0x2986132c2d6F716bD103e6D33F3e8884AF2b8D71"

CONTRACTS: Final = {
    "UPDOWN": "0xEcB9716867f9300F2706EdbB5b81c7a0AbDC5B29",
    "NEUTRAL": "0xC8519524013348466e18fC1747d11F1feA9473fd",
}

FIRST_CHALLENGE: Final = 1
LAST_CHALLENGE: Final = 10
LAST_DATASET_CHALLENGE: Final = LAST_CHALLENGE + 1

ZERO_BYTES32: Final = "0x" + "00" * 32
