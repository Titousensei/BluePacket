package org.bluesaga.network;

import java.io.*;
import java.util.*;
import java.util.zip.*;
import java.lang.reflect.*;

//import network.packets.*;

public abstract class BluePacket
{
  public static final int MASK_COMPRESSED = 1;
  public static final int MASK_LEGACY = 128;

  public static boolean DEBUG = true;

  public static Map<Long, BluePacket> PACKETID_TO_CLASS = null;

  private static final int MAX_UNSIGNED_BYTE = 255;

  public String sequenceId = null;

  public static void init(String pkg)
  {
    if (PACKETID_TO_CLASS != null) {
      throw new RuntimeException("BluePacket already initialized.");
    }
    PACKETID_TO_CLASS = new HashMap<>();

    for (Class<? extends BluePacket> cl : ClassUtils.findSubClasses(pkg, BluePacket.class)) {
      try {
        recognize(cl);
      } catch (NoSuchMethodException | IllegalAccessException | IllegalArgumentException ex) {
        throw new RuntimeException("Class " + cl.getSimpleName() + " must have a public constructor without parameters");
      } catch (InstantiationException | InvocationTargetException ex) {
        throw new RuntimeException("Class " + cl.getSimpleName() + " can't be instantiated: " + ex);
      }
    }
  }

  public long getPacketHash() { return 0L; }
  public void fieldsToString(StringBuilder sb) {}
  public void serializeData(DataOutputStream dos) throws IOException {}
  public void populateData(DataInputStream dis) throws IOException {}

  public static boolean isKnown(BluePacket bp) {
    return PACKETID_TO_CLASS.containsKey(bp.getPacketHash());
  }

  private static void recognize(Class<? extends BluePacket> clazz)
  throws NoSuchMethodException, InstantiationException, IllegalAccessException, InvocationTargetException
  {
    BluePacket bp = clazz.getDeclaredConstructor().newInstance();
    long id = bp.getPacketHash();
    if (PACKETID_TO_CLASS.containsKey(id)) {
      throw new RuntimeException("ID " + id + " reserved for multiple Packets: "
          + clazz.getSimpleName() + " & " + PACKETID_TO_CLASS.get(id).getClass().getSimpleName());
    }
    if (DEBUG) {
      System.err.println("DEBUG - BluePacket recognized " + clazz.getSimpleName());
    }
    PACKETID_TO_CLASS.put(id, bp);
  }

  /*
   * From object to bytes
   *
   * Serialization format:
   * - 2 bytes: packet ID, mapping to a Packet class
   * - 4 bytes: version hash representing the class name and the public field names in order
   * - (optional) 10 bytes: sequenceId (only for BluePacket from client to server)
   * - N*x bytes: field values in field names alphabetical order.
   */
  public final byte[] serialize()
  throws IOException, IllegalAccessException
  {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    DataOutputStream dos = new DataOutputStream(out);

    // Header
    dos.writeLong(getPacketHash());
    if (sequenceId != null) {
      dos.writeBytes(sequenceId);
    }

    // Body
    serializeData(dos);

    dos.flush();
    return out.toByteArray();
  }

  protected void writeSequenceLength(DataOutputStream dos, int length)
  throws IOException
  {
    if (length < MAX_UNSIGNED_BYTE) {
      dos.writeByte(length);
    } else {
      dos.writeByte(MAX_UNSIGNED_BYTE);
      dos.writeInt(length);
    }
  }

  protected void writeString(DataOutputStream dos, String val)
  throws IOException
  {
    if (val == null) {
      dos.writeByte(0);
    } else {
      writeSequenceLength(dos, val.length());
      dos.writeBytes(val);
    }
  }

  protected void writeArray(DataOutputStream dos, BluePacket[] arr)
  throws IOException
  {
    if (arr == null) {
      dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(BluePacket p : arr) {
        p.serializeData(dos);
      }
    }
  }


  /**
   * From bytes to object.
   *
   * Knowing the class ID, this will create an instance and populate all the fields
   * in order by reading the correct number of bytes.
   * If the message contains a SequenceID (only for packets from client to server),
   * there should be 10 extra bytes for this purpose.
   */
  public static BluePacket deserialize(byte[] data, boolean containsSequenceId)
  throws IOException, ReflectiveOperationException
  {
    ByteArrayInputStream in = new ByteArrayInputStream(data);
    DataInputStream dis = new DataInputStream(in);

    // Header
    long packetHash = dis.readLong();
    BluePacket proto = PACKETID_TO_CLASS.get(packetHash);
    if (proto == null) {
      throw new RuntimeException("Unknown packetHash received: " + packetHash);
    }
    BluePacket packet = proto.getClass().getDeclaredConstructor().newInstance();

    if (containsSequenceId) {
      byte[] sequenceIdBytes = new byte[10];
      int sequenceIdcount = dis.read(sequenceIdBytes, 0, 10);
      if (sequenceIdcount != 10) {
        throw new RuntimeException("Can't read enough bytes for sequenceId " + packet.getClass().getSimpleName()
            + ": " + Arrays.toString(data));
      }
      packet.sequenceId = new String(sequenceIdBytes);
    }

    // Body
    packet.populateData(dis);

    return packet;
  }

  protected int readSequenceLength(DataInputStream dis)
  throws IOException
  {
    int length = dis.readUnsignedByte();
    if (length == MAX_UNSIGNED_BYTE) {
      length = dis.readInt();
    }
    return length;
  }

  protected String readString(DataInputStream dis)
  throws IOException
  {
    int length = readSequenceLength(dis);
    if (length > 0) {
      byte[] strBytes = new byte[length];
      int actual = dis.read(strBytes, 0, length);
      if (actual != length) {
        throw new RuntimeException("Can't read enough bytes for String of " + getClass().getSimpleName()
          + ": got " + actual + ", expected " + length);
      }
      return new String(strBytes);
    }
    return null;
  }

  @Override
  public String toString()
  {
    StringBuilder sb = new StringBuilder();
    sb.append('{').append(getClass().getSimpleName());
    fieldsToString(sb);
    sb.append('}');
    return sb.toString();
  }

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

  private static boolean isNotEmpty(Object obj)
  {
    if (obj == null) {
      return false;
    }
    Class<?> t = obj.getClass();
    if (t == Integer.TYPE || t == Integer.class) {
      return (int) obj != 0;
    } else if (t == String.class) {
      return !((String) obj).isEmpty();
    } else if (t == Boolean.TYPE || t == Boolean.class) {
      return (boolean) obj;
    } else if (t == Byte.TYPE || t == Byte.class) {
      return (byte) obj != 0;
    } else if (t == Short.TYPE || t == Short.class) {
      return (short) obj != 0;
    } else if (t == Long.TYPE || t == Long.class) {
      return (long) obj != 0;
    } else if (t == Float.TYPE || t == Float.class) {
      return (float) obj != 0.0f;
    } else if (t == Double.TYPE || t == Double.class) {
      return (double) obj != 0.0;
    } else if (t.isEnum()) {
      return obj != null;
    } else if (t.isArray()) {
      return ((Object[]) obj).length != 0;
    }
    return true;
  }

  public static void appendIfNotEmpty(StringBuilder sb, String fname, Object obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append(obj);
    }
  }

  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, BluePacket[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (BluePacket p : obj) {
      sb.append('|');
      p.fieldsToString(sb);
    }
    sb.append('}');
  }
}
