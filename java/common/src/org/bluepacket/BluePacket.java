package org.bluepacket;

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
  private static final int MAX_UNSIGNED_BYTE = 255;

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
   * Get all the convertible BluePackets",
   * @return List of BluePacket instances"
   */
  public List<? extends BluePacket> convert() { return Collections.<BluePacket>emptyList(); }

  /**
   * Internal helper method for toString()
   * To be overridden by generated classes.
   * @param sb to write the fields and their values
   */
  protected void fieldsToString(StringBuilder sb) {}

  /**
   * Internal method to serialize to bytes
   * To be overridden by generated classes.
   * @param dos stream to write the bytes to
   * @throws IOException if output stream cannot write the next byte
   */
  protected void serializeData(DataOutputStream dos) throws IOException {}

  /**
   * Internal method to deserialize from bytes into this object fields
   * To be overridden by generated classes.
   * @param registry the BluePacketRegistry to create instances of "packet" fields
   * @param dis stream to read the bytes from
   * @throws IOException if input stream cannot read the next byte
   */
  protected void populateData(BluePacketRegistry registry, DataInputStream dis) throws IOException {}

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
   */
  public final byte[] serialize()
  {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    serialize(out);
    return out.toByteArray();
  }

  /**
   * From object to bytes stream
   *
   * Serialization format:
   * - 8 bytes: version hash representing the class name and the public field names in order
   * - N*x bytes: field values in field names alphabetical order.
   *
   * @param out the stream where the bytes will be written
   */
  public final void serialize(OutputStream out)
  {
    DataOutputStream dos = new DataOutputStream(out);

    try {
      dos.writeLong(getPacketHash());
      serializeData(dos);

      dos.flush();
    }
    catch (IOException ex) {
      throw new RuntimeException(ex);
    }
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
   * Internal method to serialize a BluePacket field.
   * First write the PacketHash (0L if null), then the bytes of the packet.
   *
   * @param dos the byte output stream
   * @param val the BluePacket to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeBluePacket(DataOutputStream dos, BluePacket val)
  throws IOException
  {
    if (val == null) {
      dos.writeLong(0L);
    } else {
      val.serialize(dos);
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
   * Internal method to serialize an Enum array
   * First write the length, then serialize each array element.
   *
   * @param dos the byte output stream
   * @param arr the array to write
   * @throws IOException if cannot write to byte stream
   */
  protected void writeArrayLargeEnum(DataOutputStream dos, Enum<?>[] arr)
  throws IOException
  {
    if (arr == null) { dos.writeByte(0);
    } else {
      writeSequenceLength(dos, arr.length);
      for(Enum<?> p : arr) dos.writeShort(p.ordinal());
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
      byte bin = 0;
      for(int i = 0 ; i < arr.length ; i ++) {
        if (arr[i]) {
          bin |= (byte)(1 << (i%8));
        }
        if (i % 8 == 7) {
          dos.writeByte(bin);
          bin = 0;
        }
      }
      if (arr.length % 8 != 0) {
        dos.writeByte(bin);
     }
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
   * From byte stream to object.
   *
   * Knowing the class ID, this will create an instance and populate all the fields
   * in order by reading the correct number of bytes.
   *
   * @param registry where the packet hash was registered
   * @param data the bytes to deserialize
   * @return the deserialized BluePacket
   */
  public static BluePacket deserialize(BluePacketRegistry registry, byte[] data)
  {
    InputStream in = new ByteArrayInputStream(data);
    return deserialize(registry, in);
  }

  /**
   * From bytes to object.
   *
   * Knowing the class ID, this will create an instance and populate all the fields
   * in order by reading the correct number of bytes.
   *
   * @param registry where the packet hash was registered
   * @param in the bytes stream to deserialize
   * @return the deserialized BluePacket
   */
  public static BluePacket deserialize(BluePacketRegistry registry, InputStream in)
  {
    DataInputStream dis = new DataInputStream(in);

    try {
      long packetHash = dis.readLong();
      if (packetHash == 0L) return null;

      // Header
      BluePacket packet = registry.newInstance(packetHash);

      // Body
      packet.populateData(registry, dis);

      return packet;
    }
    catch (IOException ex) {
      throw new RuntimeException(ex);
    }
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
   * Internal method to read a list bool.
   * First read the length of the list, then the bytes that pack the bits.
   *
   * @param dis the input stream containing the bytes of the serialized BluePacket
   * @return the boolean array
   * @throws IOException if cannot write to byte stream
   */
  protected boolean[] readListBool(DataInputStream dis)
  throws IOException
  {
    int length = readSequenceLength(dis);
    if (length > 0) {
      boolean[] ret = new boolean[length];
      int bin = 0;
      for (int i = 0; i < length; ++i) {
        if (i % 8 == 0) {
          bin = dis.readByte();
        }
        ret[i] = (bin & (1 << (i % 8))) != 0;
      }
      return ret;
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
      return obj != null && ((Enum) obj).ordinal() != 0;
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

  /** Case-insensitive strings that force conversion treats as false. */
  private static final java.util.Set<String> BP_FALSE_STRINGS = new java.util.HashSet<>(
      java.util.Arrays.asList("", "false", "f", "0", "no", "n", "off", "null", "none"));

  /**
   * Canonical string representation used by convert mappings.
   * @param value scalar or enum value
   * @return canonical representation
   */
  public static String bpToString(Object value) {
    if (value instanceof Boolean) return ((Boolean) value) ? "true" : "false";
    if (value instanceof Enum) return ((Enum<?>) value).name();
    if (value instanceof Float) return bpFloatToString((Float) value);
    if (value instanceof Double) return bpFloatToString((Double) value);
    return String.valueOf(value);
  }

  private static String bpFloatToString(float value) {
    if (Float.isNaN(value)) return "nan";
    if (value == Float.POSITIVE_INFINITY) return "inf";
    if (value == Float.NEGATIVE_INFINITY) return "-inf";
    return bpEnsureDecimal(Float.toString(value));
  }

  private static String bpFloatToString(double value) {
    if (Double.isNaN(value)) return "nan";
    if (value == Double.POSITIVE_INFINITY) return "inf";
    if (value == Double.NEGATIVE_INFINITY) return "-inf";
    return bpEnsureDecimal(Double.toString(value));
  }

  private static String bpEnsureDecimal(String text) {
    boolean hasDecimal = text.indexOf('.') >= 0 || text.indexOf('E') >= 0 || text.indexOf('e') >= 0;
    return hasDecimal ? text : text + ".0";
  }

  /**
   * Interpret a string as a boolean using the canonical false list.
   * @param value string to parse
   * @return parsed boolean
   */
  public static boolean bpStringToBool(String value) {
    return !BP_FALSE_STRINGS.contains(value.trim().toLowerCase());
  }

  /**
   * Best-effort conversion to boolean.
   * @param value source value
   * @return converted boolean
   */
  public static boolean bpToBool(Object value) {
    if (value instanceof Boolean) return (Boolean) value;
    if (value instanceof Number) return ((Number) value).doubleValue() != 0;
    return bpStringToBool((String) value);
  }

  /**
   * Ordinal of an enum value, zero for null.
   * @param value enum value
   * @return ordinal
   */
  public static long bpEnumOrdinal(Enum<?> value) {
    return value == null ? 0L : value.ordinal();
  }

  /**
   * Best-effort conversion to a clamped 64-bit integer.
   * @param value source value
   * @param low minimum allowed value
   * @param high maximum allowed value
   * @return converted value
   */
  public static long bpToLong(Object value, long low, long high) {
    if (value instanceof Boolean) return ((Boolean) value) ? 1L : 0L;
    if (value instanceof String) return bpStringToLong((String) value, low, high);
    if (value instanceof Float || value instanceof Double) {
      double number = ((Number) value).doubleValue();
      if (Double.isNaN(number)) return 0L;
      if (number <= low) return low;
      if (number >= high) return high;
      return (long) number;
    }
    return Math.max(low, Math.min(high, ((Number) value).longValue()));
  }

  private static long bpStringToLong(String value, long low, long high) {
    String text = value.trim();
    try {
      return Math.max(low, Math.min(high, Long.parseLong(text)));
    } catch (NumberFormatException e) {
      // Fall through to floating point parsing.
    }
    try {
      double number = Double.parseDouble(text);
      if (Double.isNaN(number)) return 0L;
      if (number <= low) return low;
      if (number >= high) return high;
      return (long) number;
    } catch (NumberFormatException e) {
      return 0L;
    }
  }

  /**
   * Best-effort conversion to floating point.
   * @param value source value
   * @param isFloat true to clamp to the 32-bit float range
   * @return converted value
   */
  public static double bpToDouble(Object value, boolean isFloat) {
    double result;
    if (value instanceof Boolean) {
      result = ((Boolean) value) ? 1.0 : 0.0;
    } else if (value instanceof String) {
      try {
        result = Double.parseDouble(((String) value).trim());
      } catch (NumberFormatException e) {
        result = 0.0;
      }
    } else {
      result = ((Number) value).doubleValue();
    }
    if (isFloat && !Double.isNaN(result)) {
      double limit = 3.4028234663852886e38;
      if (result > limit) result = limit;
      else if (result < -limit) result = -limit;
    }
    return result;
  }

  /**
   * Best-effort conversion to an enum value.
   * @param enumType target enum class
   * @param value source value
   * @param <E> enum type
   * @return converted enum value or the first enum constant
   */
  public static <E extends Enum<E>> E bpToEnum(Class<E> enumType, Object value) {
    E[] values = enumType.getEnumConstants();
    if (value != null && enumType.isInstance(value)) return enumType.cast(value);
    if (value instanceof String) {
      String text = ((String) value).trim();
      for (E entry : values) {
        if (entry.name().equals(text)) return entry;
      }
      return bpEnumFromLong(values, bpStringToOrdinal(text));
    }
    if (value instanceof Boolean) return bpEnumFromLong(values, ((Boolean) value) ? 1L : 0L);
    if (value instanceof Enum) return bpEnumFromLong(values, ((Enum<?>) value).ordinal());
    if (value instanceof Float || value instanceof Double) {
      double number = ((Number) value).doubleValue();
      if (Double.isNaN(number)) return bpEnumFromLong(values, 0L);
      return bpEnumFromLong(values, (long) number);
    }
    if (value instanceof Number) return bpEnumFromLong(values, ((Number) value).longValue());
    return bpEnumFromLong(values, 0L);
  }

  private static long bpStringToOrdinal(String text) {
    try {
      return Long.parseLong(text);
    } catch (NumberFormatException e) {
      try {
        return (long) Double.parseDouble(text);
      } catch (NumberFormatException ignored) {
        return 0L;
      }
    }
  }

  private static <E extends Enum<E>> E bpEnumFromLong(E[] values, long ordinal) {
    if (values.length == 0) return null;
    if (ordinal < 0 || ordinal >= values.length) return values[0];
    return values[(int) ordinal];
  }
}
