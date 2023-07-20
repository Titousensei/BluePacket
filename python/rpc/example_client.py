4#! /usr/bin/env python3
import sys

sys.path.append("../common")

from blue_packet import BluePacketRegistry
from blue_packet_rpc_client import RPC_DEFAULT_PORT, RpcClient
import gen.example.packet as bp


class ExampleClient(RpcClient):

    def rpcExec(self, request):
        response = self._execute(request)
        if isinstance(response, bp.RpcResult):
            return response.value
        elif isinstance(response, bp.RpcError):
            raise Exception("ERROR - RpcError: " + response.message)
        else:
            raise Exception("ERROR - Unexpected response packet: " + str(response))


def _makeCalcSum(*values):
    v = [float(x) for x in values]
    return bp.CalcSum(values=v)


def _makeCalcMean(mean_type, *values):
    try:
        t = bp.CalcMean.Type[mean_type]
    except KeyError:
        raise Exception("ERROR - Unknown CalcMean.Type: " + mean_type)
    v = [float(x) for x in values]
    return bp.CalcMean(type=t, values=v)


_REQUEST_MAKER = {
    "Add": _makeCalcSum,
    "Mean": _makeCalcMean,
}


def main():
    registry = BluePacketRegistry()
    registry.register(bp)
    #print("registry =", registry, file=sys.stderr)

    op = sys.argv[1]
    if op not in _REQUEST_MAKER:
        raise Exception("ERROR - Unknown operation: " + op)

    request_fn = _REQUEST_MAKER[op]
    request = request_fn(*sys.argv[2:])

    with ExampleClient("127.0.0.1", registry) as client:
        value = client.rpcExec(request)
        print(value)


if __name__ == '__main__':
    main()
