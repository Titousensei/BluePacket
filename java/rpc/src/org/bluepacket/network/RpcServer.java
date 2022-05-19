package org.bluepacket.network;

import java.util.*;
import java.io.*;
import java.util.concurrent.ArrayBlockingQueue;
import java.lang.reflect.Constructor;

import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.function.UnaryOperator;

import org.bluepacket.BluePacket;
import org.bluepacket.BluePacketRegistry;

/**
 * Server class
 *
 * Runs in an infinite loop, waiting for incoming requests ("jobs") and offers them to worker threads pool.
 *
 * Also provides packet methods to worker threads.
 */
public class RpcServer
{
  public final static int DEFAULT_PORT = 5900;
  public final static int DEFAULT_NUM_THREAD = 10;
  public final static int TIMEOUT_REMOVE_IDLE = 3000; // MILLISECONDS

  // thread exit notification
  public final static Socket NULL_SOCKET = new Socket();

  protected ArrayBlockingQueue<Socket> jobs_ = new ArrayBlockingQueue<>(1000);
  protected List<RpcServerThread> threadPool_;
  protected Map<Class<? extends BluePacket>, UnaryOperator<BluePacket>> dispatchHandler_ = new HashMap<>();
  protected Function<Exception, BluePacket> errorHandler_ = null;

  protected final BluePacketRegistry registry_;

  /**
   * Constructor
   *
   * @param registry the deserialization registry
   */
  public RpcServer(BluePacketRegistry registry)
  {
    registry_ = registry;
  }

  /**
   * run in an infinite loop with default number of threads and default port
   */
  public void run()
  {
    run(DEFAULT_NUM_THREAD, DEFAULT_PORT);
  }

  /**
   * run in an infinite loop
   *
   * @param numthreads initial size of the thread pool
   * @param port port to listen to
   */
  public void run(int numthreads, int port)
  {
    threadPool_ = Collections.synchronizedList(new ArrayList<>(numthreads));
    addThreads(numthreads);

    try {
      ServerSocket listener = new ServerSocket(port, 50*numthreads);
      System.err.println("[RpcServer] listening to port " + port);

      while (true) {
        Socket conn = listener.accept();
        jobs_.offer(conn);
      }
    }
    catch (IOException ioe) {
      ioe.printStackTrace();
    }
    removeThreads(threadPool_.size());
    System.err.println("[RpcServer] exiting");
  }

  /**
   * Increase the size of the thread pool
   *
   * Each thread will be initialized and ready to handle incoming requests immediately.
   * Can be called while running.
   *
   * @param num number of worker threads to add to the pool
   */
  public void addThreads(int num)
  {
    System.err.println("[RpcServer] Adding " + num + " threads");
    for (int i=0 ; i<num ; i++) {
      RpcServerThread t = new RpcServerThread(this);
      t.start();
      threadPool_.add(t);
    }
  }

  /**
   * Decrease the size of the thread pool
   *
   * Idle threads will receive a termination signal instead of a job offer and will exit cleanly.
   * Can be called while running.
   *
   * @param num number of worker threads to remove from the pool
   */
  public void removeThreads(int num)
  {
    System.err.println("[RpcServer] Notifying " + num + " threads to exit when done processing");
    for (int i=0 ; i<num ; i++) {
      try {
        jobs_.offer(NULL_SOCKET, TIMEOUT_REMOVE_IDLE, TimeUnit.MILLISECONDS);
      }
      catch(InterruptedException iex) {
        iex.printStackTrace();
      }
    }
  }

  /**
   * Method for worker threads to request a job.
   *
   * This is blocking, so each thread is waiting here.
   * If there's an incoming request, the socket is returned to the thread for processing.
   * If the job is the special termination marker, the waiting threads is removed from the pool and notified to exit.
   *
   * @param t the thread requesting a job
   * @return the socket with an incoming request, or null
   */
  public Socket getJob(RpcServerThread t)
  {
    try {
      Socket s = jobs_.take();
      if (s != NULL_SOCKET) {
        return s;
      }
    }
    catch (InterruptedException iex) {
      iex.printStackTrace();
    }

    threadPool_.remove(t);
    return null;
  }

  /**
   * Helper deserialization method
   *
   * Use the registry to deserialize bytes into a packet
   *
   * @param is the stream containing the bytes to deserialize
   * @return the packet
   */
  public BluePacket deserialize(InputStream is) {
    return BluePacket.deserialize(registry_, is);
  }

  /**
   * Execute the function associated with the request packet
   *
   * @param pk request packet
   * @param response packet
   * @throws if request packet does not have an associated function
   */
  public BluePacket execute(BluePacket pk) {
     System.out.println("[RpcServer] execute " + pk);
     UnaryOperator<BluePacket> handlerFn =  dispatchHandler_.get(pk.getClass());
     if (handlerFn == null) {
       throw new RuntimeException("No handler for packet class: " + pk.getClass());
     }
     return handlerFn.apply(pk);
  }

  /**
   * Execute the function associated with exception handling
   *
   * @param ex the exception
   * @return packet wrapping the exception
   */
  public BluePacket executeError(Exception ex) {
     if (errorHandler_ == null) {
       ex.printStackTrace();
       return null;
     }
     return errorHandler_.apply(ex);
  }

  /**
   * Declaration of the function that will handle exceptions
   *
   * Use if exceptions should be returned to the client.
   * If not declared, exceptions will print a stack trace on the server side.
   *
   * @param handlerFn the function associated with exceptions handling
   * @return this (builder pattern)
   */
  public RpcServer onError(Function<Exception, BluePacket> handlerFn) {
    errorHandler_ = handlerFn;
    return this;
  }

  /**
   * Declaration of the function that will handle one packet class
   *
   * @param packetClass the packet class
   * @param handlerFn the function associated with this packet class
   * @return this (builder pattern)
   */
  public RpcServer onReceive(Class<? extends BluePacket> packetClass, UnaryOperator<BluePacket> handlerFn) {
    dispatchHandler_.put(packetClass, handlerFn);
    return this;
  }
}
