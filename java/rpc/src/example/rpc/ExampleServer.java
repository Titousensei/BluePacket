package example.rpc;

import java.util.*;
import java.io.*;
import java.util.concurrent.ArrayBlockingQueue;

import java.lang.reflect.Constructor;

import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.TimeUnit;

import org.bluepacket.BluePacket;
import org.bluepacket.BluePacketRegistry;
import org.bluepacket.network.RpcServer;

import example.packet.*;

/**
 * Example implementation of a BluePacket RPC Server for a calculator service.
 */
public class ExampleServer
{
  /**
   * Helper for Sum command
   *
   * @param values array of numbers
   * @return the sum of the numbers
   */
  protected static float sum(float[] values)
  {
    float agg = 0.0f;
    for (float f : values) {
      agg += f;
    }
    return agg;
  }

  /**
   * Helper for Mean command, Arithmetic type
   *
   * m = sum(x)/n
   *
   * @param values array of numbers
   * @return the arithmetic mean of the numbers
   */
  protected static float arithmetic(float[] values)
  {
    return sum(values) / values.length;
  }

  /**
   * Helper for Mean command, Geometric type
   *
   * m = mul(x)^(1/n)
   *
   * @param values array of numbers
   * @return the geomtric mean of the numbers
   */
  protected static float geometric(float[] values)
  {
    float agg = 1.0f;
    for (float f : values) {
      agg *= f;
    }
    return (float) Math.pow(agg, 1.0f / values.length);
  }

  /**
   * Helper for Mean command, Harmonic type
   *
   * m = n / sum(1/x)
   *
   * @param values array of numbers
   * @return the harmonic mean of the numbers
   */
  protected static float harmonic(float[] values)
  {
    float agg = 0.0f;
    for (float f : values) {
      agg += 1.0f / f;
    }
    return values.length / agg;
  }

  /**
   * Handler for Sum command
   *
   * @param pk the request packet
   * @return the result packet
   */
  public static RpcResult calculateSum(CalcSum pk)
  {
    float s = sum(pk.values);
    return new RpcResult().setValue(s);
  }

  /**
   * Handler for Mean command
   *
   * @param pk the request packet
   * @return the result packet
   * @throws if request contains no values
   * @throws if enum type is not implemented
   */
  public static RpcResult calculateMean(CalcMean pk)
  {
    float s;
    if (pk.values.length == 0) {
      throw new RuntimeException("No values provided");
    }
    switch (pk.type) {
    case Arithmetic:
      s = arithmetic(pk.values);
      break;
    case Geometric:
      s = geometric(pk.values);
      break;
    case Harmonic:
      s = harmonic(pk.values);
      break;
    default:
      throw new RuntimeException("Unsupported CalcMean.Type: " + pk.type);
    }

    return new RpcResult().setValue(s);
  }

  /**
   * Exception handler
   *
   * to return an error packet when an exception occured
   *
   * @param ex the exception that occured during handling of request
   * @return error packet wrapping the exception message
   */
  public static BluePacket errorHandler(Exception ex)
  {
    return new RpcError().setMessage(ex.getMessage());
  }

  /**
   * Server entry point
   *
   * - initialiaze deserialization registry with all known packets
   * - create a server process:
   *    - handlers for each supported packet
   *    - handler for exceptions
   *    - run in an infinite loop with default thread pool (10) and listen on default port
   */
  public static void main(String argv[])
  throws Exception
  {
    BluePacketRegistry registry = new BluePacketRegistry();
    registry.register("example/packet");

    new RpcServer(registry)
        .onReceive(CalcSum.class, pk -> calculateSum((CalcSum) pk))
        .onReceive(CalcMean.class, pk -> calculateMean((CalcMean) pk))
        .onError(ExampleServer::errorHandler)
        .run();
  }
}
