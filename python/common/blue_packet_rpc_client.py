#! /usr/bin/env python3
import socket

RPC_DEFAULT_PORT = 5900

_CHUNK_SIZE = 4096


# TODO: make a generator to avoid materializing the chunks
def receive(sock):
    chunks = []
    while True:
        one_chunk = sock.recv(_CHUNK_SIZE)
        if one_chunk == b'':
            break
        chunks.append(one_chunk)
    return b''.join(chunks)


class RpcClient:

    def __init__(self, host, registry):
        self._registry = registry
        self.host = host

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        pass

    def _execute(self, request):
        data = request.serialize()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, RPC_DEFAULT_PORT))
            s.sendall(data)
            response_data = receive(s)
            return self._registry.deserialize(response_data)
