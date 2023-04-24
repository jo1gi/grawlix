from Crypto.Cipher import AES
from typing import Union
from dataclasses import dataclass


@dataclass(slots=True)
class AESEncryption:
    key: bytes
    iv: bytes


@dataclass(slots=True)
class AESCTREncryption:
    key: bytes
    nonce: bytes
    initial_value: bytes


@dataclass(slots=True)
class XOrEncryption:
    key: bytes

Encryption = Union[
    AESCTREncryption,
    AESEncryption,
    XOrEncryption
]

def decrypt(data: bytes, encryption: Encryption) -> bytes:
    """
    Decrypt data with specified encryption algorithm

    :param data: Bytes to decrypt
    :param encryption: Information about how to decrypt
    :returns: Decrypted data
    """
    if isinstance(encryption, AESCTREncryption):
        cipher = AES.new(
            key = encryption.key,
            mode = AES.MODE_CTR,
            nonce = encryption.nonce,
            initial_value = encryption.initial_value
        )
        return cipher.decrypt(data)
    if isinstance(encryption, AESEncryption):
        cipher = AES.new(encryption.key, AES.MODE_CBC, encryption.iv)
        return cipher.decrypt(data)
    if isinstance(encryption, XOrEncryption):
        key_length = len(encryption.key)
        decoded = []
        for i in range(0, len(data)):
            decoded.append(data[i] ^ encryption.key[i % key_length])
        return bytes(decoded)
    raise NotImplemented
