from os import getcwd, path
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

def aes_encrypt(key, initVector, data):
    cipher = Cipher(algorithms.AES(key), modes.CBC(initVector))
    encryptor = cipher.encryptor()
    return encryptor.update(data)

def aes_decrypt(key, initVector, encrypted):
    cipher = Cipher(algorithms.AES(key), modes.CBC(initVector))
    return cipher.decryptor().update(encrypted)

def generate_private(device_name=""):
    # generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend())
    # serialise the key
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_txt = device_name + '_private_key.txt'
    keys_path = path.join(getcwd(), 'keys', private_txt)
    # writing key to the file
    with open(keys_path, 'wb') as f:
        f.write(pem)
    return private_key


def generate_public(device_name="", private_key=None):
    # generate public key
    public_key = private_key.public_key()

    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_txt = device_name + '_public_key.txt'
    keys_path = path.join(getcwd(), 'keys', public_txt)
    with open(keys_path, 'wb') as f:
        f.write(pem)
    return public_key


def test_address(testAddress="", testNetwork=None):
    addresses = testAddress.split(".")
    for i in addresses:
        if int(i) < 0 or int(i) > 255:
            print("Invalid address")
            return "0.0.0.0"
    for i in testNetwork.computerList + testNetwork.serverList:
        if i.ipAddress == testAddress:
            print("Reused address")
            return "0.0.0.0"
    return testAddress


class Device:
    def __init__(self, name=None, ipAddress=None, torNetwork=None):
        self.name = name
        self.ipAddress = test_address(ipAddress, torNetwork)
        self.torNetwork = torNetwork

        try:
            self.load_private_key()
        except Exception:
            self.privateKey = generate_private(name)
        try:
            self.load_public_key()
        except Exception:
            self.publicKey = generate_public(name, self.privateKey)

        self.connectionList = []
        self.buffer = []

    def load_private_key(self):
        with open("keys/" + self.name + "_private_key.txt", "rb") as key_file:
            self.privateKey = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )

    def load_public_key(self):
        with open("keys/" + self.name + "_public_key.txt", "rb") as key_file:
            self.publicKey = serialization.load_pem_public_key(
                key_file.read(),
                backend=default_backend()
            )

    def send_data(self, destAddr, port, data):
        packet = [self.ipAddress, destAddr, port, data]
        for host in self.torNetwork.serverList + self.torNetwork.computerList:
            if destAddr == host.ipAddress:
                host.buffer.append(packet)
                break

    def __str__(self):
        return self.ipAddress
