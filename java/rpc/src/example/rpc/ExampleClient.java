package example.rpc;

import java.util.*;
import java.io.IOException;

import org.bluepacket.BluePacket;
import org.bluepacket.BluePacketRegistry;
import org.bluepacket.network.RpcClient;
import org.bluepacket.network.RpcServer;

import example.packet.*;

/**
 * Example implementation of BluePacket RPC Client for a calculator service.
 */
public class ExampleClient
{
  private final RpcClient client_;

  /**
   * Constructor
   */
  public ExampleClient(String host, BluePacketRegistry registry)
  {
    client_ = new RpcClient(host, RpcServer.DEFAULT_PORT, registry);
  }

  /**
   * Execute request
   *
   * @param request the BluePacket containing the request
   * @return RpcResult value field if successful
   * @throws RpcError message field
   */
  private float rpcExec(BluePacket request)
  throws IOException
  {
    BluePacket response = client_.send(request);
    try {
      RpcResult result = (RpcResult) response;
      return result.value;
    } catch(ClassCastException ex) {
      RpcError err = (RpcError) response;
      throw new RuntimeException(err.message);
    }
  }

  /**
   * Transform input strings into floats
   *
   * @param start the starting position of the values in the input arguments
   * @param argv the array of arguments
   * @return the values in float array
   */
  private static float[] parseValues(int start, String... argv)
  {
    float[] input = new float[argv.length - start];
    for (int i = start ; i < argv.length ; i++) {
      input[i - start] = Float.parseFloat(argv[i]);
    }
    return input;
  }

  /**
   * Client entry point
   *
   * Example commands:
   * - Add 1 2 3 4
   *   -> 10.0
   * - Mean Arithmetic 4 36 45 50 75
   *   -> 42.0
   * - Mean Geometric 4 36 45 50 75
   *   -> 30.0
   * - Mean Harmonic 4 36 45 50 75
   *   -> 15.0
   */
  public static void main(String... argv)
  throws Exception
  {
    BluePacketRegistry registry = new BluePacketRegistry();
    registry.register("example/packet");
    ExampleClient client = new ExampleClient("localhost", registry);

    BluePacket request;
    if ("Add".equals(argv[0])) {
      float[] input = parseValues(1, argv);
      request = new CalcSum().setValues(input);
    } else if ("Mean".equals(argv[0])) {
      CalcMean.Type t = CalcMean.Type.valueOf(argv[1]);
      float[] input = parseValues(2, argv);
      request = new CalcMean().setType(t).setValues(input);
    } else {
      throw new RuntimeException("ERROR - Unknown operation: " + argv[0]);
    }

    float value = client.rpcExec(request);
    System.out.println(value);
  }
}
