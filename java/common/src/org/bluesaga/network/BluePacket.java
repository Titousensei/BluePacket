package org.bluesaga.network;

import java.io.*;
import java.util.*;
import java.util.zip.*;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;


/**
 * The base class for all generated BluePackets
 * Provides many util methods to serialize, deserialized, toString, etc.
 */
public abstract class BluePacket
{
  /**
   */
  public static final int MASK_COMPRESSED = 1;

  /**
   */
  public static final int MASK_LEGACY = 128;

  /**
   */
  public static boolean DEBUG = true;

  /**
   */
  public static Map<Long, BluePacket> PACKETID_TO_CLASS = null;

  /**
   */
  private static final int MAX_UNSIGNED_BYTE = 255;

  /**
   * Initialize the packet registry
   * @param pkg package contening all the generated BluePacket classes
   */
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

  /**
   * Internal method to get the hash version number of this packet.
   * To be overridden by generated classes.
   * @return version hash
   */
  public long getPacketHash() { return 0L; }

  /**
   * Internal method to get the hash version number of this packet.
   * To be overridden by generated classes.
   * @return version hash hexadecimal
   */
  public String getPacketHex() { return null; }

  /**
   * Internal helper method for toString()
   * To be overridden by generated classes.
   * @param sb to write the fields and their values
   */
  public void fieldsToString(StringBuilder sb) {}

  /**
   * Internal method to serialize to bytes
   * To be overridden by generated classes.
   * @param dos stream to write the bytes to
   * @throws IOException if output stream cannot write the next byte
   */
  public void serializeData(DataOutputStream dos) throws IOException {}

  /**
   * Internal method to deserialize from bytes into this object fields
   * To be overridden by generated classes.
   * @param dis stream to read the bytes from
   * @throws IOException if input stream cannot read the next byte
   */
  public void populateData(DataInputStream dis) throws IOException {}

  /**
   * Internal method to see if a packet class was registered.
   * @param bp the packet instance to lookup
   * @return whether this BluePacket is registered or not
   */
  public static boolean isKnown(BluePacket bp) {
    return PACKETID_TO_CLASS.containsKey(bp.getPacketHash());
  }

  /**
   * Internal method to register a packet class
   * @param clazz the generater packet class to register
   * @throws NoSuchMethodException if packet class does not have a constructor
   * @throws InstantiationException if packet class cannot be instantiated
   * @throws IllegalAccessException if packet constructor is not public
   * @throws InvocationTargetException if packet class constructor throws an exception
   */
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

  /**
   * Internal method to get unsigned byte
   * @param x the byte
   * @return the unsigned byte as an int
   */
  public static int unsigned(byte x) {
    return 255 & x;
  }

  /**
   * Internal method to get unsigned short
   * @param x the short
   * @return the unsigned short as an int
   */
  public static int unsigned(short x) {
    return 65535 & x;
  }

  /**
   * From object to bytes
   *
   * Serialization format:
   * - 8 bytes: version hash representing the class name and the public field names in order
   * - N*x bytes: field values in field names alphabetical order.
   *
   * @return packet instance serialized
   * @throws IOException if cannot write to byte stream
   * @throws IllegalAccessException if serialization uses non-public methods
   */
  public final byte[] serialize()
  throws IOException, IllegalAccessException
  {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    DataOutputStream dos = new DataOutputStream(out);

    dos.writeLong(getPacketHash());
    serializeData(dos);

    dos.flush();
    return out.toByteArray();
  }

  /**
   * Internal method to start serializing a sequence.
   * If length is small (byte), write just one byte.
   * If lenght is bigger than a byte, first write a max byte marker, then 
   * write actual length as an int (4 bytes).
   *
   * @param dos the byte output stream
   * @param length the size of the sequence that will be written next
   * @throws IOException if cannot write to byte stream
   */
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

  /**
   * Internal method to serialize a String.
   * First write the length, then the bytes of the String.
   *
   * @param dos the byte output stream
   * @param val the String to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeString(DataOutputStream dos, String val)
  throws IOException
  {
    if (val == null) {
      dos.writeByte(0);
    } else {
      byte[] data = val.getBytes(StandardCharsets.UTF_8);
      writeSequenceLength(dos, data.length);
      dos.write(data, 0, data.length);
    }
  }

  /**
   * Internal method to serialize a BluePacket array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, BluePacket[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(BluePacket p : arr) p.serializeData(dos);
    }
  }

  /**
   * Internal method to serialize an Enum array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, Enum<?>[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(Enum<?> p : arr) dos.writeByte(p.ordinal());
    }
  }

  /**
   * Internal method to serialize a boolean array
   * First write the length, then serialize each array element as one byte.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, boolean[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(boolean p : arr) dos.writeBoolean(p);
    }
  }

  /**
   * Internal method to serialize a byte array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, byte[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(byte p : arr) dos.writeByte(p);
    }
  }

  /**
   * Internal method to serialize a double array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, double[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(double p : arr) dos.writeDouble(p);
    }
  }

  /**
   * Internal method to serialize a float array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, float[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(float p : arr) dos.writeFloat(p);
    }
  }

  /**
   * Internal method to serialize an int array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, int[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(int p : arr) dos.writeInt(p);
    }
  }

  /**
   * Internal method to serialize a long array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, long[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(long p : arr) dos.writeLong(p);
    }
  }

  /**
   * Internal method to serialize a short array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, short[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(short p : arr) dos.writeShort(p);
    }
  }

  /**
   * Internal method to serialize a String array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArray(DataOutputStream dos, String[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(String p : arr) writeString(dos, p);
    }
  }


  /**
   * From bytes to object.
   *
   * Knowing the class ID, this will create an instance and populate all the fields
   * in order by reading the correct number of bytes.
   *
   * @param data the bytes to deserialize
   * @return the deserialized BluePacket
   * @throws IOException if cannot write to byte stream
   * @throws ReflectiveOperationException if cannot instantiate a new BluePacket of this class
   */
  public static BluePacket deserialize(byte[] data)
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

    // Body
    packet.populateData(dis);

    return packet;
  }

  /**
   * Internal method to start deserializing a sequence.
   *
   * @param dis the input stream containing the bytes of the serialized BluePacket
   * @return the length of the sequence following
   * @throws IOException if cannot write to byte stream
   */
  protected int readSequenceLength(DataInputStream dis)
  throws IOException
  {
    int length = dis.readUnsignedByte();
    if (length == MAX_UNSIGNED_BYTE) {
      length = dis.readInt();
    }
    return length;
  }

  /**
   * Internal method to read a String.
   * First read the length of the String, then the bytes.
   *
   * @param dis the input stream containing the bytes of the serialized BluePacket
   * @return the String
   * @throws IOException if cannot write to byte stream
   */
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
      return new String(strBytes, StandardCharsets.UTF_8);
    }
    return null;
  }

  /**
   * Standard String representation of this packet and its data.
   * @return a string representation of this BluePacket
   */
  @Override
  public String toString()
  {
    StringBuilder sb = new StringBuilder();
    sb.append('{').append(getClass().getSimpleName());
    if (getPacketHex() != null) {
      sb.append(' ').append(getPacketHex());
    }
    fieldsToString(sb);
    sb.append('}');
    return sb.toString();
  }

  /**
   * Internal method to compress a serialized packet
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
   * Internal method to uncompress a serialized packet
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

  /**
   * Internal method to check if a field is empty.
   * Empty fields are skipped during toString.
   * @param obj the field value to check
   * @return whether the value represents "empty" or not
   */
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

  /**
   * Internal method to construct the toString value of a boolean field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not false
   * @param obj the field value to append if it's not false
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, boolean obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append(obj?'1':'0');
    }
  }

  /**
   * Internal method to construct the toString value of a Object field (non-native).
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, Object obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append(obj);
    }
  }

  /**
   * Internal method to construct the toString value of a String field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not null
   * @param obj the field value to append if it's not null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append('"').append(obj).append('"');
    }
  }

  /**
   * Internal method to construct the toString value of an unsigned byte field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not 0
   * @param obj the field value to append if it's not 0
   */
  public static void appendIfNotEmptyUnsigned(StringBuilder sb, String fname, byte obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append(unsigned(obj));
    }
  }

  /**
   * Internal method to construct the toString value of a short field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not 0
   * @param obj the field value to append if it's not 0
   */
  public static void appendIfNotEmptyUnsigned(StringBuilder sb, String fname, short obj)
  {
    if(isNotEmpty(obj)) {
      sb.append(' ').append(fname).append('=').append(unsigned(obj));
    }
  }

  /**
   * Internal method to construct the toString value of a BluePacket array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field class name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
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

  /**
   * Internal method to construct the toString value of a boolean array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, boolean[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (boolean p : obj) sb.append('|').append(p?'1':'0');
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a byte array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, byte[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (byte p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of an unsigned byte array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmptyUnsigned(StringBuilder sb, String fname, String ftype, byte[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (byte p : obj) sb.append('|').append(unsigned(p));
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a double array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, double[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (double p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a float array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, float[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (float p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of an int array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, int[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (int p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a long array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, long[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (long p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a short array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, short[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (short p : obj) sb.append('|').append(p);
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of an unsigned short array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmptyUnsigned(StringBuilder sb, String fname, String ftype, short[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (short p : obj) sb.append('|').append(unsigned(p));
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of an Enum array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, Enum<?>[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (Enum<?> p : obj) {
        sb.append('|');
        if (p!=null) sb.append(p);
    }
    sb.append('}');
  }

  /**
   * Internal method to construct the toString value of a String array field.
   * @param sb the buffer for toString
   * @param fname the field name to append if it's not empty or null
   * @param ftype the field element type name to append if it's not empty or null
   * @param obj the field value to append if it's not empty or null
   */
  public static void appendIfNotEmpty(StringBuilder sb, String fname, String ftype, String[] obj)
  {
    if (obj == null || obj.length == 0) return;

    sb.append(' ').append(fname).append("={").append(ftype).append(" *").append(obj.length);
    for (String p : obj) {
        sb.append('|');
        if (p!=null && !p.isEmpty()) sb.append('"').append(p).append('"');
    }
    sb.append('}');
  }
}
