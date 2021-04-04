import Connection
import Device
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import random

def rsa_decrypt(key, encrypted):
    data = key.decrypt(
        encrypted,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return data

class Server(Device.Device):
    def __init__(self, name=None, ipAddress=None, torNetwork=None):
        super().__init__(name, ipAddress, torNetwork)

    def create_connection(self, packet):
        data = rsa_decrypt(self.privateKey,packet[4]).split(b"<<_<<")  # decrypt packet[3] with self.privateKey before split
        nextPort = random.randint(4000, 4294967295)
        nextAddr = data[0].decode()
        newConnection = Connection.Connection(packet[0], packet[2], nextPort, nextAddr)
        newConnection.symmetricKeys.append(data[1])
        newConnection.initVectors.append(data[2])
        if any(nextAddr == host.ipAddress for host in self.torNetwork.computerList):
            newConnection.isEndNode = True
        self.connectionList.append(newConnection)
        print("{}:\tnew/con from: {}\tto: {}\tlength: {}\tdata: {}".format(self, newConnection.sourceAddr, newConnection.destAddr, len(b"<<_<<".join(data)), b"<<_<<".join(data)))

    def forward_connection(self, connection, counter, dataList):
        message = b""
        for block in dataList:
            part = Device.aes_decrypt(connection.symmetricKeys[0], connection.initVectors[0], block)
            if part == 128 * b"0":
                print("{}:\trem/con from: {}\tto: {}".format(self, connection.sourceAddr, connection.destAddr))
                self.connectionList.remove(connection)
                break
            else:
                message += Device.unpadder(part)
        else:
            self.send_data(connection.destAddr, connection.destPort, counter, message)
            print("{}:\tfwd/con from: {}\tto: {}\tlength: {}\tdata: {}".format(self, connection.sourceAddr, connection.destAddr, len(message), message))

    def backward_connection(self, connection, counter, data):
        data = Device.aes_encrypt(connection.symmetricKeys[0], connection.initVectors[0], data)
        self.send_data(connection.sourceAddr, connection.sourcePort, counter, data)
        print("{}:\tbck/con from: {}\tto: {}\tlength: {}\tdata: {}". format(self, connection.destAddr, connection.sourceAddr, len(data), data))

    def buffer_check(self):
            while len(self.buffer) != 0:
                packet = self.buffer.pop(0)
                try:
                    conn = next(filter(lambda c: c.sourcePort == packet[2], self.connectionList))
                    if not conn.isEndNode:
                        self.forward_connection(conn, packet[3], [packet[4]])
                    elif packet[3] != 0:
                        conn.dataBuffer.append(packet[4])
                    else:
                        self.forward_connection(conn, 0, conn.dataBuffer + [packet[4]])
                        conn.dataBuffer = []
                except StopIteration:
                    try:
                        conn = next(filter(lambda c: c.destPort == packet[2], self.connectionList))
                        if not conn.isEndNode:
                            self.backward_connection(conn, packet[3], packet[4])
                        else:
                            blocks = Device.packets(packet[4])
                            for i,block in enumerate(blocks):
                                self.backward_connection(conn, len(blocks)-i-1, block)
                    except StopIteration:
                        self.create_connection(packet)
