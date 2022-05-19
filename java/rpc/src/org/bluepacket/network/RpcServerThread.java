package org.bluepacket.network;

import java.util.*;
import java.io.*;

import java.net.Socket;

import org.bluepacket.BluePacket;

/**
 * Worker thread to execute requests.
 */
public class RpcServerThread
extends Thread
{
  private final RpcServer server_;

  /**
   * Constructor
   *
   * @param server the server this thread belongs to
   */
  public RpcServerThread(RpcServer server)
  {
    server_ = server;
  }

  /**
   * Infinite run loop
   *
   * Waits for the server to offer a job (blocking).
   *
   * If job is null (termination signal), do nothing and exit the infinite loop.
   *
   * If job is a socket, execute the request:
   * - deserialize the incoming packet
   * - execute the associated function to get a result
   * - if there's an exception:
   *   - execute the exception handler and use that as a result
   * - serialize the result and send it back as response
   */
  public void run()
  {
    while (true) {
      // Thread doesn't need to sleep because take() is blocking
      Socket s = server_.getJob(this);
      if (s == null) {
        // received message to terminate
        return;
      }

      BluePacket response = null;
      try {
        BluePacket request = server_.deserialize(s.getInputStream());
        response = server_.execute(request);
        if (response != null) {
          response.serialize(s.getOutputStream());
        }
      }
      catch (Exception ex) {
        response = server_.executeError(ex);
      }

      if (response != null) {
        try {
          response.serialize(s.getOutputStream());
        }
        catch (Exception ex) {
          ex.printStackTrace();
        }
      }

      if (!s.isClosed()) {
        try {
          s.close();
        }
        catch(Throwable t) {}
      }
    }
  }
}
