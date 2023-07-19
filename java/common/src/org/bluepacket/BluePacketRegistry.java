package org.bluepacket;

import java.io.*;
import java.util.*;
import java.util.zip.*;
import java.lang.reflect.*;

/**
 * The base class for all generated BluePackets
 * Provides many util methods to serialize, deserialized, toString, etc.
 */
public class BluePacketRegistry
{
  /**
   */
  public static boolean DEBUG = true;

  /**
   */
  public Map<Long, BluePacket> packet_id_to_class_ = new HashMap<>();

  /**
   * Initialize the packet registry
   * @param pkg package contening all the generated BluePacket classes
   */
  public void register(String pkg)
  {
    pkg = pkg.replace('.','/');
    if (DEBUG) {
      System.err.println("[BluePacketRegistry] DEBUG - Searching BluePacket classes in path: " + pkg);
    }
    for (Class<? extends BluePacket> cl : ClassUtils.findSubClasses(pkg, BluePacket.class)) {
      register(cl);
    }
  }

  /**
   * Internal method to see if a packet class was registered.
   * @param bp the packet instance to lookup
   * @return whether this BluePacket is registered or not
   */
  public boolean isKnown(BluePacket bp) {
    return packet_id_to_class_.containsKey(bp.getPacketHash());
  }

  /**
   * Method to register a single packet class
   * @param clazz the generater packet class to register
   */
  public void register(Class<? extends BluePacket> clazz)
  {
    BluePacket bp;
    try {
      bp = clazz.getDeclaredConstructor().newInstance();
    } catch (NoSuchMethodException | IllegalAccessException | IllegalArgumentException ex) {
      throw new RuntimeException("Class " + clazz.getSimpleName() + " must have a public constructor without parameters");
    } catch (InstantiationException | InvocationTargetException ex) {
      throw new RuntimeException("Class " + clazz.getSimpleName() + " can't be instantiated: " + ex);
    }
    
    long id = bp.getPacketHash();
    
    if (packet_id_to_class_.containsKey(id)) {
      throw new RuntimeException("ID " + id + " reserved for multiple Packets: "
          + clazz.getSimpleName() + " & " + packet_id_to_class_.get(id).getClass().getSimpleName());
    }
    if (DEBUG) {
      System.err.println("[BluePacketRegistry] DEBUG - Registered: " + clazz.getSimpleName());
    }
    packet_id_to_class_.put(id, bp);
  }

  /**
   * Method to instantiate a registered BluePacket from its hash value
   * @param packetHash the hash value of the packet class
   * @return a new empty instance of the BluePacket corresponding to this hash
   */
  public BluePacket newInstance(long packetHash)
  {
    BluePacket proto = packet_id_to_class_.get(packetHash);
    if (proto == null) {
      throw new RuntimeException("Unknown packetHash: " + packetHash);
    }
    try {
      return proto.getClass().getDeclaredConstructor().newInstance();
    }
    catch (NoSuchMethodException | InstantiationException | IllegalAccessException | InvocationTargetException ex) {
      throw new RuntimeException(ex);
    }
  }

  /**
   * Utility method to compress a byte array
   * @param data the uncompressed bytes
   * @return the compressed bytes
   */
  public static byte[] gzipCompress(byte[] data)
  {
    try (
      ByteArrayOutputStream buffer = new ByteArrayOutputStream(data.length * 2);
      GZIPOutputStream os = new GZIPOutputStream(buffer)
    ) {
      os.write(data);
      os.finish();
      os.flush();
      return buffer.toByteArray();
    } catch (IOException ex) {
      throw new RuntimeException(ex);
    }
  }

  /**
   * Utility method to uncompress a byte array
   * @param data the compressed bytes
   * @return the uncompressed bytes
   */
  public static byte[] gzipUncompress(byte[] data)
  {
    try (
      ByteArrayOutputStream os = new ByteArrayOutputStream();
      InputStream is = new GZIPInputStream(new ByteArrayInputStream(data))
    ) {
      byte[] buffer = new byte[1024];
      int len = 0;
      while ((len = is.read(buffer)) >= 0) {
        os.write(buffer, 0, len);
      }
      return os.toByteArray();
    } catch (IOException ex) {
      throw new RuntimeException(ex);
    }
  }
}
