using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;

namespace BluePackets
{
  /// <summary>The base class for all generated packets</summary>
  public abstract class BluePacket
  {
    private static Encoding ENCODING = new UTF8Encoding();

    public static Dictionary<long, BluePacket> PACKETID_TO_CLASS;

    private const int MAX_UNSIGNED_BYTE = 255;

    static BluePacket()
    {
      PACKETID_TO_CLASS = new Dictionary<long, BluePacket>();
      foreach (var t in GetPackets())
      {
        Recognize(t);
      }
    }

    /// <summary>
    /// Internal method to get the hash version number of this packet.
    /// To be overridden by generated classes.
    /// </summary>
    /// <returns>version hash</returns>
    virtual public long GetPacketHash() { return 0; }
    /// <summary>
    /// Internal method to get the hash version number of this packet.
    /// To be overridden by generated classes.
    /// </summary>
    /// <returns>version hash hexadecimal</returns>
    virtual public string GetPacketHex() { return null; }
    /// <summary>
    /// Internal helper method for ToString()
    /// To be overridden by generated classes.
    /// </summary>
    /// <param name="sb">builder to write the fields and their values</param>
    abstract public void FieldsToString(StringBuilder sb);
    /// <summary>
    /// Internal method to serialize to bytes
    /// To be overridden by generated classes.
    /// </summary>
    /// <param name="s">stream to write the bytes to</param>
    abstract public void SerializeData(Stream ms);
    /// <summary>
    /// Internal method to deserialize from bytes into this object fields
    /// To be overridden by generated classes.
    /// </summary>
    /// <param name="s">stream to read the bytes from</param>
    abstract public void PopulateData(Stream ms);

    private static object NewInstance(Type clazz)
    {
      ConstructorInfo ci = clazz.GetConstructor(
          BindingFlags.Instance | BindingFlags.Public,
          null,  // Binder?
          CallingConventions.HasThis,
          new Type[0],
          null);  // ParameterModifier[]?
      return ci.Invoke(null);
    }

    /// <summary>
    /// Internal method to see if a packet class was registered.
    /// </summary>
    /// <param name="bp">the packet instance to lookup</param>
    /// <returns>whether this BluePacket is registered or not</returns>
    public static bool IsKnown(Type clazz)
    {
      BluePacket packet = (BluePacket)NewInstance(clazz);
      return PACKETID_TO_CLASS.ContainsKey(packet.GetPacketHash());
    }

    private static List<BluePacket> GetPackets()
    {
      Assembly asm = Assembly.GetExecutingAssembly();
      List<BluePacket> ret = new List<BluePacket>();
      foreach (Type type in asm.GetTypes())
      {
        if (type.BaseType == typeof(BluePacket))
          ret.Add((BluePacket)NewInstance(type));
      }
      return ret;
    }

    private static void Recognize(BluePacket bp)
    {
      long id = bp.GetPacketHash();
      if (id == 0) return;
      if (PACKETID_TO_CLASS.ContainsKey(id))
      {
        throw new ArgumentException("ID " + id + " reserved for multiple Packets: "
            + bp.GetType().Name + " & " + PACKETID_TO_CLASS[id].GetType().Name);
      }
      PACKETID_TO_CLASS[id] = bp;
    }

    /// <summary>
    /// From object to bytes
    /// Serialization format:
    /// - 8 bytes: packetHash representing the class name and the public field names in order
    /// - N*x bytes: field values in field names alphabetical order.
    /// <summary>
    /// <returns>packet instance serialized</returns>
    public byte[] Serialize()
    {
      using (MemoryStream ms = new MemoryStream())
      {
        WriteLong(ms, GetPacketHash());
        SerializeData(ms);

        ms.Flush();
        return ms.ToArray();
      }
    }

    /// <summary>Internal method to write a byte array in a consistent order</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the bytes to write</param>
    private static void WriteBytesBigEndian(Stream ms, byte[] data)
    {
      if (BitConverter.IsLittleEndian)
        Array.Reverse(data);
      ms.Write(data, 0, data.Length);
    }

    /// <summary>Internal method to write a signed byte</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the byte to write</param>
    protected static void WriteSByte(Stream ms, sbyte data)
    {
      ms.WriteByte((byte)data);
    }

    /// <summary>Internal method to write an unsigned byte</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the byte to write</param>
    protected static void WriteByte(Stream ms, byte data)
    {
      ms.WriteByte(data);
    }

    /// <summary>Internal method to write a signed short</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the short to write</param>
    protected static void WriteShort(Stream ms, short data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>Internal method to write an unsigned short</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the short to write</param>
    protected static void WriteUShort(Stream ms, ushort data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>Internal method to write a signed int</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the int to write</param>
    protected static void WriteInt(Stream ms, int data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>Internal method to write a signed long</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the long to write</param>
    protected static void WriteLong(Stream ms, long data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>Internal method to write a float</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the float to write</param>
    protected static void WriteFloat(Stream ms, float data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>Internal method to write a double</summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the double to write</param>
    protected static void WriteDouble(Stream ms, double data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    /// <summary>
    /// Internal method to write a string.
    /// First write the length, then bytes of the string.
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the string to write</param>
    protected static void WriteString(Stream ms, string data)
    {
      if (data == null)
      {
        ms.WriteByte(0);
      }
      else
      {
        byte[] b = ENCODING.GetBytes(data);
        WriteSequenceLength(ms, b.Length);
        ms.Write(b, 0, b.Length);
      }
    }

    /// <summary>
    /// Internal method to write a BluePacket.
    /// First write the packet hash (0 if null), then the bytes.
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the BluePacket to write</param>
    protected static void WriteBluePacket(Stream ms, BluePacket data)
    {
      if (data == null)
      {
        WriteLong(ms, 0);
      }
      else
      {
        WriteLong(ms, data.GetPacketHash());
        data.SerializeData(ms);
      }
    }

    /// <summary>
    /// Internal method to write a list bool.
    /// First write the lenght, then bytes of packet bits.
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the boolean array to write</param>
    protected static void WriteListBool(Stream ms, bool[] data)
    {
      if (data == null)
      {
        ms.WriteByte(0);
      }
      else
      {
        WriteSequenceLength(ms, data.Length);
        int bin = 0;
        for(int i = 0 ; i < data.Length ; i++) {
          if (data[i]) {
            bin |= 1 << (i % 8);
          }
          if ((i % 8) == 7) {
            ms.WriteByte((byte) bin);
            bin = 0;
          }
        }
        if ((data.Length % 8) != 0) {
          ms.WriteByte((byte) bin);
        }
      }
    }

    /// <summary>
    /// Internal method to write the length of any sequence.
    /// - If length is small (byte), write just one byte.
    /// - If lenght is bigger than a byte, first write a max byte marker,
    ///   then write actual length as an int (4 bytes).
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the length of the sequence</param>
    protected static void WriteSequenceLength(Stream ms, int length)
    {
      if (length < MAX_UNSIGNED_BYTE)
      {
        ms.WriteByte((byte)length);
      }
      else
      {
        ms.WriteByte((byte)MAX_UNSIGNED_BYTE);
        WriteInt(ms, length);
      }
    }

    /// <summary>
    /// Write enum to stream
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the enum</param>
    protected static void WriteEnum(Stream ms, Enum data)
    {
      ms.WriteByte(Convert.ToByte(data));
    }

    /// <summary>
    /// Write large enum to stream
    /// </summary>
    /// <param name="ms">the byte output stream</param>
    /// <param name="data">the enum</param>
    protected static void WriteLargeEnum(Stream ms, Enum data)
    {
      WriteUShort(ms, Convert.ToUInt16(data));
    }

    /// <summary>
    /// From bytes to object.
    ///
    /// Knowing the class packetHash, this will create an instance
    /// and populate all the fields in order by reading the correct number of bytes.
    /// </summary>
    /// <param name="data">the bytes to read</param>
    /// <returns>an instance of the packet</returns>
    public static BluePacket Deserialize(byte[] data)
    {
      using (MemoryStream ms = new MemoryStream(data))
      {
        return Deserialize(ms);
      }
    }

    /// <summary>
    /// From stream to object.
    ///
    /// Knowing the class packetHash, this will create an instance
    /// and populate all the fields in order by reading the correct number of bytes.
    /// </summary>
    /// <param name="data">the stream to read</param>
    /// <returns>an instance of the packet</returns>
    public static BluePacket Deserialize(Stream ms)
    {
      // Header
      long packetHash = ReadLong(ms);
      if (packetHash == 0L) return null;
      object proto = PACKETID_TO_CLASS[packetHash];
      if (proto == null)
      {
        throw new InvalidOperationException("Unknown packetHash received: " + packetHash);
      }
      BluePacket packet = (BluePacket)NewInstance(proto.GetType());

      // Body
      packet.PopulateData(ms);

      return packet;
    }

    /// <summary>Internal method to read a given number of bytes from a stream</summary>
    /// <param name="ms">the byte input stream</param>
    /// <param name="num_bytes">the number of bytes to read</param>
    /// <returns>the bytes read</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    private static byte[] ReadNBytesBigEndian(Stream ms, int num_bytes)
    {
      byte[] data = new byte[num_bytes];
      int l = ms.Read(data, 0, data.Length);
      if (l != data.Length)
      {
        throw new EndOfStreamException("EOF reached in ReadNBytesBigEndian: got " + l + ", expected " + data.Length);
      }
      if (BitConverter.IsLittleEndian)
        Array.Reverse(data);
      return data;
    }

    /// <summary>Internal method to read one unsigned byte from a stream</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the unsigned byte</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static byte ReadByte(Stream ms)
    {
      int data = ms.ReadByte();
      if (data == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadByte");
      }
      return (byte)data;
    }

    /// <summary>Internal method to read one signed byte from a stream</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the signed byte</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static sbyte ReadSByte(Stream ms)
    {
      int data = ms.ReadByte();
      if (data == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadSByte");
      }
      return (sbyte)data;
    }

    /// <summary>Internal method to read one signed short from a stream, encoded as two bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the signed short</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static short ReadShort(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 2);
      return BitConverter.ToInt16(data, 0);
    }

    /// <summary>Internal method to read one unsigned short from a streamm, encoded as two bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the unsigned short</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static ushort ReadUShort(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 2);
      return BitConverter.ToUInt16(data, 0);
    }

    /// <summary>Internal method to read one int from a stream, encoded as 4 bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the int</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static int ReadInt(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 4);
      return BitConverter.ToInt32(data, 0);
    }

    /// <summary>Internal method to read one int from a stream</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the int</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static long ReadLong(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 8);
      return BitConverter.ToInt64(data, 0);
    }

    /// <summary>Internal method to read one float from a stream, encoded as 4 bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the float</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static float ReadFloat(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 4);
      return BitConverter.ToSingle(data, 0);
    }

    /// <summary>Internal method to read one double from a stream, encoded as 8 bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the double</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static double ReadDouble(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 8);
      return BitConverter.ToDouble(data, 0);
    }

    /// <summary>Internal method to read string from a stream, encoded as the length then the bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the string</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static string ReadString(Stream ms)
    {
      int length = ReadSequenceLength(ms);
      if (length == 0) return null;

      byte[] strBytes = new byte[length];
      int actual = ms.Read(strBytes, 0, length);
      if (actual != length)
      {
        throw new EndOfStreamException("EOF reached in ReadString: got " + actual + ", expected " + length);
      }
      return ENCODING.GetString(strBytes, 0, length);
    }

    /// <summary>Internal method to read list bool from a stream, encoded as the length then the packed bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the bool array</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static bool[] ReadListBool(Stream ms)
    {
      int length = ReadSequenceLength(ms);
      if (length == 0) return null;
      bool[] ret = new bool[length];
      int bin = 0;
      for (int i = 0 ; i < length ; i++) {
        if ((i % 8) == 0) {
          bin = ms.ReadByte();
        }
        if ((bin & (1<<(i % 8))) != 0) {
          ret[i] = true;
        }
      }
      return ret;
    }

    /// <summary>
    /// Internal method to read the sequence length from a stream
    /// - First read one byte
    /// - If it's smaller than MAX_UNSIGNED_BYTE return this as the length
    /// - If it's equal to MAX_UNSIGNED_BYTE, read an int (4 bytes) and return this as the length
    /// </summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the length</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static int ReadSequenceLength(Stream ms)
    {
      int length = ms.ReadByte();
      if (length == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadSequenceLength");
      }
      if (length == MAX_UNSIGNED_BYTE)
      {
        length = ReadInt(ms);
      }
      return length;
    }

    /// <summary>Internal method to read and enum from a stream, encoded as one byte</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the enum value</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static object ReadEnum(Type t, Stream ms)
    {
      return Enum.ToObject(t, ms.ReadByte());
    }

    /// <summary>Internal method to read and enum from a stream, encoded as two bytes</summary>
    /// <param name="ms">the byte input stream</param>
    /// <returns>the enum value</returns>
    /// <exception cref="EndOfStreamException">when there's not enough bytes in the stream</exception>
    protected static object ReadLargeEnum(Type t, Stream ms)
    {
      return Enum.ToObject(t, ReadUShort(ms));
    }

    /// <summary>Internal method to get an array length, returning 0 if null</summary>
    /// <param name="ms">the array</param>
    /// <returns>the length of the array</returns>
    protected int ArrayLength(Object[] obj)
    {
      return (obj == null) ? 0 : obj.Length;
    }

    /// <summary>Method to get a human-readable representation of any packet.</summary>
    /// <returns>the string representing the packet and its fields</returns>
    override public string ToString()
    {
      var cl = GetType();
      StringBuilder sb = new StringBuilder();
      sb.Append('{').Append(cl.Name);
      if (GetPacketHex() != null) {
        sb.Append(' ').Append(GetPacketHex());
      }
      FieldsToString(sb);
      sb.Append('}');
      return sb.ToString();
    }

    /// <summary>Internal method to decide if an object qualifies as "empty": null, 0, "", [], {}, ...</summary>
    /// <param name="ms">the object</param>
    /// <returns>whether the object should be considered empty or not</returns>
    private static bool IsNotEmpty(object obj)
    {
      if (obj == null) {
        return false;
      }
      Type t = obj.GetType();
      if (t == typeof(int)) {
        return (int)obj != 0;
      } else if (t == typeof(string)) {
        return (string)obj != string.Empty;
      } else if (t == typeof(bool)) {
        return (bool)obj;
      } else if (t == typeof(byte)) {
        return (byte)obj != 0;
      } else if (t == typeof(sbyte)) {
        return (sbyte)obj != 0;
      } else if (t == typeof(short)) {
        return (short)obj != 0;
      } else if (t == typeof(long)) {
        return (long)obj != 0;
      } else if (t == typeof(float)) {
        return (float)obj != 0.0f;
      } else if (t == typeof(double)) {
        return (double)obj != 0.0;
      } else if (t.IsEnum) {
        return Convert.ToInt32((Enum) obj) != 0;
      } else if (t.IsArray) {
        return (int)t.GetProperty("Length").GetValue(obj) != 0;
      }
      return true;
    }

    /// <summary>Internal method to populate the value of one field, if it's not "empty"</summary>
    /// <param name="sb">the builder containing the string</param>
    /// <param name="fname">the name of the field</param>
    /// <param name="obj">the object</param>
    public static void AppendIfNotEmpty(StringBuilder sb, String fname, object obj)
    {
      if(IsNotEmpty(obj)) {
        sb.Append(' ').Append(fname).Append('=');
        if (obj.GetType() == typeof(bool)) {
          sb.Append('1');
        } else if (obj.GetType() == typeof(string)) {
          sb.Append('"').Append(obj).Append('"');
        } else {
          sb.Append(obj);
        }
      }
    }

    /// <summary>Internal method to populate the content of one array of packet field, if it's not "empty"</summary>
    /// <param name="sb">the builder containing the string</param>
    /// <param name="fname">the name of the field</param>
    /// <param name="obj">the object</param>
    public static void AppendIfNotEmpty(StringBuilder sb, String fname, String ftype, BluePacket[] obj)
    {
      if (obj == null || obj.Length == 0) return;

      sb.Append(' ').Append(fname).Append("={").Append(ftype).Append(" *").Append(obj.Length);
      foreach (BluePacket p in obj)
      {
        sb.Append('|');
        p.FieldsToString(sb);
      }
      sb.Append('}');
    }

    /// <summary>Internal method to populate the content of one array of primitive type field, if it's not "empty"</summary>
    /// <param name="sb">the builder containing the string</param>
    /// <param name="fname">the name of the field</param>
    /// <param name="obj">the object</param>
    public static void AppendIfNotEmptyArray<T>(StringBuilder sb, String fname, String ftype, T[] obj)
    {
      if (obj == null || obj.Length == 0) return;
      var isBool = "bool".Equals(ftype);
      var isString = "string".Equals(ftype);

      sb.Append(' ').Append(fname).Append("={").Append(ftype).Append(" *").Append(obj.Length);
      foreach (T p in obj)
      {
        sb.Append('|');
        if (p != null) {
          if (isBool) {
            sb.Append(p.Equals(true) ? '1' : '0');
          } else if (isString) {
            sb.Append('"').Append(p).Append('"');
          } else {
            sb.Append(p);
          }

        }
      }
      sb.Append('}');
    }
  }
}
