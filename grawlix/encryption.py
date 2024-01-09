from Crypto.Cipher import AES
from typing import Union, Protocol
from dataclasses import dataclass


@dataclass(slots=True)
class AESEncryption:
    key: bytes
    iv: bytes

    def decrypt(self, data: bytes) -> bytes:
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return cipher.decrypt(data)


@dataclass(slots=True)
class AESCTREncryption:
    key: bytes
    nonce: bytes
    initial_value: bytes

    def decrypt(self, data: bytes) -> bytes:
        cipher = AES.new(
            key = self.key,
            mode = AES.MODE_CTR,
            nonce = self.nonce,
            initial_value = self.initial_value
        )
        return cipher.decrypt(data)


@dataclass(slots=True)
class XOrEncryption:
    key: bytes

    def decrypt(self, data: bytes) -> bytes:
        key_length = len(self.key)
        decoded = []
        for i in range(0, len(data)):
            decoded.append(data[i] ^ self.key[i % key_length])
        return bytes(decoded)


class Encryption(Protocol):
    def decrypt(self, data: bytes) -> bytes: ...


def decrypt(data: bytes, encryption: Encryption) -> bytes:
    """
    Decrypt data with specified encryption algorithm

    :param data: Bytes to decrypt
    :param encryption: Information about how to decrypt
    :returns: Decrypted data
    """
    return encryption.decrypt(data)
