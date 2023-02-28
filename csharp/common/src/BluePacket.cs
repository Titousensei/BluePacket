using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;

namespace BluePackets
{

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

    virtual public long GetPacketHash() { return 0; }
    virtual public string GetPacketHex() { return null; }
    abstract public void FieldsToString(StringBuilder sb);
    abstract public void SerializeData(Stream ms);
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

    /*
     * From object to bytes
     *
     * Serialization format:
     * - 8 bytes: packetHash representing the class name and the public field names in order
     * - (optional) 10 bytes: sequenceId (only for BluePacket from client to server)
     * - N*x bytes: field values in field names alphabetical order.
     */
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

    private static void WriteBytesBigEndian(Stream ms, byte[] data)
    {
      if (BitConverter.IsLittleEndian)
        Array.Reverse(data);
      ms.Write(data, 0, data.Length);
    }

    protected static void WriteBool(Stream ms, bool data)
    {
      ms.WriteByte(data ? (byte)1 : (byte)0);
    }

    protected static void WriteSByte(Stream ms, sbyte data)
    {
      ms.WriteByte((byte)data);
    }

    protected static void WriteByte(Stream ms, byte data)
    {
      ms.WriteByte(data);
    }

    protected static void WriteShort(Stream ms, short data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteUShort(Stream ms, ushort data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteInt(Stream ms, int data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteLong(Stream ms, long data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteFloat(Stream ms, float data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteDouble(Stream ms, double data)
    {
      WriteBytesBigEndian(ms, BitConverter.GetBytes(data));
    }

    protected static void WriteString(Stream ms, string data)
    {
      if (data == null)
      {
        ms.WriteByte(0);
      }
      else
      {
        WriteSequenceLength(ms, data.Length);
        WriteStringBytes(ms, data);
      }
    }

    private static void WriteStringBytes(Stream ms, string data)
    {
      byte[] b = ENCODING.GetBytes(data);
      ms.Write(b, 0, b.Length);
    }

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

    protected static void WriteEnum(Stream ms, Enum data)
    {
      ms.WriteByte(Convert.ToByte(data));
    }

    /*
     * From bytes to object.
     *
     * Knowing the class packetHash, this will create an instance and populate all the fields
     * in order by reading the correct number of bytes.
     * If the message contains a SequenceID (only for packets from client to server),
     * there should be 10 extra bytes for this purpose.
     */
    public static BluePacket Deserialize(byte[] data)
    {
      using (MemoryStream ms = new MemoryStream(data))
      {
        // Header
        long packetHash = ReadLong(ms);
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
    }

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

    protected static byte ReadByte(Stream ms)
    {
      int data = ms.ReadByte();
      if (data == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadByte");
      }
      return (byte)data;
    }

    protected static sbyte ReadSByte(Stream ms)
    {
      int data = ms.ReadByte();
      if (data == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadSByte");
      }
      return (sbyte)data;
    }

    protected static bool ReadBool(Stream ms)
    {
      int data = ms.ReadByte();
      if (data == -1)
      {
        throw new EndOfStreamException("EOF reached in ReadBool");
      }
      return (data != 0);
    }

    protected static short ReadShort(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 2);
      return BitConverter.ToInt16(data, 0);
    }

    protected static ushort ReadUShort(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 2);
      return BitConverter.ToUInt16(data, 0);
    }

    protected static int ReadInt(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 4);
      return BitConverter.ToInt32(data, 0);
    }

    protected static long ReadLong(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 8);
      return BitConverter.ToInt64(data, 0);
    }

    protected static float ReadFloat(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 4);
      return BitConverter.ToSingle(data, 0);
    }

    protected static double ReadDouble(Stream ms)
    {
      byte[] data = ReadNBytesBigEndian(ms, 8);
      return BitConverter.ToDouble(data, 0);
    }

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

    protected static object ReadEnum(Type t, Stream ms)
    {
      return Enum.ToObject(t, ms.ReadByte());
    }

    protected int ArrayLength(Object[] obj)
    {
      return (obj == null) ? 0 : obj.Length;
    }

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
        return Convert.ToInt32(obj) != 0;
      } else if (t.IsArray) {
        return (int)t.GetProperty("Length").GetValue(obj) != 0;
      }
      return true;
    }

    public static void AppendIfNotEmpty(StringBuilder sb, String fname, object obj)
    {
      if(IsNotEmpty(obj)) {
        sb.Append(' ').Append(fname).Append('=');
        if (obj.GetType() == typeof(bool)) {
          sb.Append('1');
        } else {
          sb.Append(obj);
        }
      }
    }

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

    public static void AppendIfNotEmptyArray<T>(StringBuilder sb, String fname, String ftype, T[] obj)
    {
      if (obj == null || obj.Length == 0) return;
      var isNotBool = !"bool".Equals(ftype);

      sb.Append(' ').Append(fname).Append("={").Append(ftype).Append(" *").Append(obj.Length);
      foreach (T p in obj)
      {
        sb.Append('|');
        if (p != null) {
          if (isNotBool) {
            sb.Append(p);
          } else if (p.Equals(true)) {
            sb.Append('1');
          } else {
            sb.Append('0');
          }
        }
      }
      sb.Append('}');
    }
  }
}
