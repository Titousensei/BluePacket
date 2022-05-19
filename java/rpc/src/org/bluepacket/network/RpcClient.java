package org.bluepacket.network;

import java.util.*;
import java.io.*;
import java.net.*;

import org.bluepacket.BluePacket;
import org.bluepacket.BluePacketRegistry;

/**
 * RpcClient can sent one request packet and receive one response packet.
 *
 * The client will open a connection to the server, serialize and send the
 * request packet, then receive and deserialize the response packet, and close
 * the connection.
 */
public class RpcClient
{
  public final static int SOCKET_TIMEOUT = 1000;

  protected final String host_;
  protected final int port_;
  protected final BluePacketRegistry registry_;

  /**
   * Constructor
   *
   * @param host the dns name or ip address of the server
   * @param port the post of the server
   * @param registry the deserialization registry
   */
  public RpcClient(String host, int port, BluePacketRegistry registry)
  {
    host_ = host;
    port_ = port;
    registry_ = registry;
  }

  /**
   * Open a connection to the server
   *
   * @return the connection socket
   */
  private Socket connect()
  {
    try {
      Socket ret = new Socket(host_, port_);
      ret.setPerformancePreferences(2,1,0); // connectionTime, latency, bandwidth
      ret.setSoTimeout(SOCKET_TIMEOUT);
      ret.setSoLinger(true, 500);
      return ret;
    }
    catch (IOException ex) {
      throw new RuntimeException(ex);
    }
  }

  /**
   * Close the connection to the server
   *
   * @param the connection socket
   */
  private void close(Socket request)
  {
    if (request != null && !request.isClosed()) {
      try {
        request.close();
      }
      catch (IOException ioex) {}
    }
  }

  /**
   * Send an RPC
   *
   * @param request the request packet
   * @return the response packet
   */
  public BluePacket send(BluePacket request)
  throws IOException
  {
    Socket conn = connect();
    try {
      request.serialize(conn.getOutputStream());
      return BluePacket.deserialize(registry_, conn.getInputStream());
    }
    finally {
      close(conn);
    }
  }
}
