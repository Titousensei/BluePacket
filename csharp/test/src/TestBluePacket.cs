using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.IO;

using Test;
using BluePackets;

class TestBluePacket
{
  private const string TESTDATA_DIR = "../../testdata/";

  private DemoPacket demoPacket;
  private byte[] demoPacketBin;

  private DemoPacket2 demoPacket2;
  private byte[] demoPacket2Bin;

  private DemoPacket3 demoPacket3;
  private byte[] demoPacket3Bin;

  private DemoUnsigned demoPacketU;
  private byte[] demoPacketUBin;

  private void AssertEquals(object expected, object actual, string msg)
  {
    if (!expected.Equals(actual)) {
      throw new ArgumentException(msg + ": Not equal\nExpected:" + expected + "\nActual  :" + actual);
    }
  }

  private void AssertEquals(byte[] expected, byte[] actual, string msg)
  {
    if (!expected.SequenceEqual(actual)) {
      throw new ArgumentException(msg + ": Not equal\nExpected:"
          + BitConverter.ToString(expected) + "\nActual  :"
          + BitConverter.ToString(actual));
    }
  }

  private void AssertInstanceOf(Type abstract_type, Type packet_type, string msg)
  {
    if (!abstract_type.IsAssignableFrom(packet_type)) {
      throw new ArgumentException(msg + ": Does not implement\nExpected:" + abstract_type + "\nActual  :" + packet_type);
    }
  }

  private void AssertNotInstanceOf(Type abstract_type, Type packet_type, string msg)
  {
    if (abstract_type.IsAssignableFrom(packet_type)) {
      throw new ArgumentException(msg + ": Should not implement\nExpected:" + abstract_type + "\nActual  :" + packet_type);
    }
  }

  private void AssertTrue(bool val, string msg)
  {
    if (!val) {
      throw new ArgumentException(msg + ": Not true");
    }
  }

  private void SetUp()
  {
    //BluePacket.Init("test");

    demoPacket = new DemoPacket {
      fBoolean = true,
      fByte = (sbyte) 99,
      fDouble = 1.23456789,
      fFloat = 3.14f,
      fInt = 987654321,
      fLong = 101112131415L,
      fShort = (short) 2345,
      fString = "abcdefåäöàê",
      fEnum = DemoPacket.MyEnum.MAYBE,
      oEnum = DemoEnum.NO_DOUBT,
      fInner = new DemoPacket.MyInner { iInteger = 88 }
    };

    DemoPacket.MyInner[] inner = new DemoPacket.MyInner[] {
      new DemoPacket.MyInner { iInteger = 777, iEnum = DemoPacket.MyEnum.WHOKNOWS },
      new DemoPacket.MyInner { iInteger = 6666 }
    };
    demoPacket.aInner = inner;
    demoPacket.fOuter = new DemoOuter { oInt = 191 };

    demoPacket.aOuter = new DemoOuter[] {
      new DemoOuter { oInt = 282, oString = ":-)" }
    };

    demoPacketBin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket.bin");

    demoPacket2 = new DemoPacket2 {
        aBoolean = new bool[] {
            true, false, true, false, true, false, true, false,
            false, true, false, true, false, true, false, true,
            false, false, true
        },
        aByte = new sbyte[] {99, 98, 97, 96},
        aDouble = new double[] {1.23456789, 2.3456789},
        aFloat = new float[] {3.14f},
        aInt = new int[] {987654321, 87654321},
        aLong = new long[] {101112131415L, 1617181920L},
        aShort = new short[] {2345, 3456, 4567},
        aString = new String[] {"abcdef", "xyz", "w", null, "asdfghjkl;"},
        aEmpty = new String[0],
        largeEnum1 = DemoEnum260.z8,
        largeEnum2 = DemoEnum260.b3,
        aLargeEnum = new DemoEnum260[] {DemoEnum260.z3, DemoEnum260.d7, DemoEnum260.z7}
    };

    demoPacket2Bin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket2.bin");

    demoPacket3 = new DemoPacket3 {
        possible = new DemoEnum[] {DemoEnum.NO_DOUBT, DemoEnum.YES}
    };

    demoPacket3Bin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket3.bin");

    demoPacket.xPacket = demoPacket3;
    demoPacket.emptyPacket = new DemoPacket0();

    demoPacketU = new DemoUnsigned {
        ub = 200,
        us = 45678,
        lub = new byte[] {201, 5},
        lus = new ushort[] {43210, 1234},
        a0 = true,
        a1 = false,
        a2 = true,
        a3 = false,
        a4 = true,
        a5 = false,
        a6 = true,
        a7 = false,
        b0 = false,
        b1 = true,
        b2 = false,
        b3 = true,
        b4 = false,
        b5 = true,
        b6 = false,
        b7 = true,
        c0 = false,
        c1 = false,
        c2 = true
    };

    demoPacketUBin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacketU.bin");
  }


  private void TestPacketHash(String name, BluePacket packet, long hash)
  {
    Console.Write(name + ": ");
    AssertEquals(hash, packet.GetPacketHash(), "GetPacketHash()");
    Console.WriteLine("PASS");
  }

  private void TestDeserialize(String name, BluePacket packet, byte[] bin)
  {
    Console.Write(name + ": ");
    BluePacket bp = BluePacket.Deserialize(bin);
    AssertEquals(packet.ToString(), bp.ToString(), "Deserialize()");
    Console.WriteLine("PASS");
  }

  private void TestSerialize(String name, BluePacket packet, byte[] bin)
  {
    Console.Write(name + ": ");
    byte[] data = packet.Serialize();
    File.WriteAllBytes("gen/" + name + ".bin", data);
    AssertEquals(bin, data, "Serialize()");
    Console.WriteLine("PASS");
  }

  private void TestToString(String name, String filename, BluePacket packet)
  {
    Console.Write(name + ": ");
    var strings = File.ReadAllLines(TESTDATA_DIR + filename);
    AssertEquals(strings[0], packet.ToString(), "ToString()");
    Console.WriteLine("PASS");
  }

  private void TestUnsigned(String name)
  {
    Console.Write(name + ": ");
    AssertEquals((sbyte) -56, (sbyte) demoPacketU.ub, "cast to sbyte");
    AssertEquals((byte) 200, demoPacketU.ub, "get byte");
    AssertEquals((short) -19858, (short) demoPacketU.us, "cast to short");
    AssertEquals((ushort) 45678, demoPacketU.us, "get ushort");

    DemoPacket packet = new DemoPacket {
      fByte = (sbyte) -56,
      fShort = (short) -19858
    };

    AssertEquals(200, (int) demoPacketU.ub, "ubyte to int");
    AssertEquals(45678, (int) demoPacketU.us, "ushort to int");
    AssertEquals(-56, (int) packet.fByte, "signed byte to int");
    AssertEquals(-19858, (int) packet.fShort, "signed short to int");

    Console.WriteLine("PASS");
  }

  private void TestAbstracts(String name, Type packet_type, params Type[] abstracts)
  {
    Console.Write(name + ": ");
    foreach (Type abstract_type in abstracts) {
      AssertInstanceOf(abstract_type, packet_type, "typeof");
    }
    Console.WriteLine("PASS");
  }

  private void TestNotAbstracts(String name, Type packet_type, params Type[] abstracts)
  {
    Console.Write(name + ": ");
    foreach (Type abstract_type in abstracts) {
      AssertNotInstanceOf(abstract_type, packet_type, "!typeof");
    }
    Console.WriteLine("PASS");
  }

  private void testForceConvert(String name)
  {
    Console.Write(name + ": ");

    ForceSource source = new ForceSource {
      intValue = 1,
      intText = "300",
      boolText = "false",
      boolValue = true,
      longValue = 5000000000L,
      enumValue = ConvertEnum.TWO,
      intList = new int[] {-1, 0, 70000},
    };
    ForceTarget target = ForceTarget.convert(source);
    AssertEquals(false, target.boolFromText, "force string to bool");
    AssertEquals(true, target.boolFromInt, "force int to bool");
    AssertEquals(true, target.boolFromEnum, "force enum to bool");
    AssertEquals(300, target.intFromText, "force string to int");
    AssertEquals(2147483647, target.intFromLong, "force long to int clamps");
    AssertEquals(255, (int) target.byteFromText, "force string to ubyte clamps");
    AssertEquals("true", target.stringFromBool, "force bool to string");
    AssertEquals("TWO", target.stringFromEnum, "force enum to string");
    AssertEquals(0.0, target.doubleFromText, "force string to double");
    AssertEquals(ConvertEnum.ZERO, target.enumFromText, "force string to enum default");
    AssertEquals(ConvertEnum.ONE, target.enumFromInt, "force int to enum");
    AssertEquals("-1,0,70000", string.Join(",", target.listDoubled), "force list copy");
    AssertEquals("-1,0,70000", string.Join(",", target.listText), "force list conversion");

    StringSource strings = new StringSource {
      flag = true,
      number = -42,
      ratio = 1.5,
      color = ConvertEnum.TWO,
      text = "raw",
      flags = new bool[] {true, false},
    };
    StringTarget widened = StringTarget.convert(strings);
    AssertEquals("true", widened.fromFlag, "widen bool to string");
    AssertEquals("-42", widened.fromNumber, "widen int to string");
    AssertEquals("1.5", widened.fromRatio, "widen double to string");
    AssertEquals("TWO", widened.fromColor, "widen enum to string");
    AssertEquals("raw", widened.fromText, "widen string to string");
    AssertEquals("true,false", string.Join(",", widened.fromFlags), "widen list bool to string");

    Console.WriteLine("PASS");
  }

  private void testEnumConvert(String name)
  {
    Console.Write(name + ": ");

    AssertEquals(ConvertEnumMore.ZERO, ConvertEnumMoreEnumConverter.EnumConvert(ConvertEnum.ZERO), "enum convert identity ZERO");
    AssertEquals(ConvertEnumMore.TWO, ConvertEnumMoreEnumConverter.EnumConvert(ConvertEnum.TWO), "enum convert identity TWO");
    AssertEquals(ConvertEnumNew.ONE, ConvertEnumNewEnumConverter.EnumConvert(ConvertEnum.ZERO), "enum convert ZERO to ONE");
    AssertEquals(ConvertEnumNew.ONE, ConvertEnumNewEnumConverter.EnumConvert(ConvertEnum.ONE), "enum convert ONE to ONE");
    AssertEquals(ConvertEnumNew.TWO, ConvertEnumNewEnumConverter.EnumConvert(ConvertEnum.TWO), "enum convert TWO to TWO");

    EnumFieldSource source = new EnumFieldSource { oldValue = ConvertEnum.ZERO };
    EnumFieldTarget target = EnumFieldTarget.convert(source);
    AssertEquals(ConvertEnumNew.ONE, target.newValue, "packet enum field conversion");

    bool threw = false;
    try {
      ConvertEnumNewEnumConverter.EnumConvert((ConvertEnum) 99);
    } catch (ArgumentException) {
      threw = true;
    }
    AssertTrue(threw, "enum convert should reject unknown value");

    Console.WriteLine("PASS");
  }

  private void testApiVersion(String name)
  {
    Console.Write(name + ": ");
    AssertTrue(BluePacketAPI.version != 0L, "BluePacketAPI.version calculated");
    AssertTrue(BluePacketAPI.versionHex != null && BluePacketAPI.versionHex != "", "BluePacketAPI.versionHex calculated");
    Console.WriteLine("PASS");
  }

  private void testConvert(String name)
  {
    Console.Write(name + ": ");
    int id = 123;
    String[] text = new String[] {"line1", "line2"};
    DemoFirst d1 = new DemoFirst { id=id, text=text };
    DemoSecond d2 = DemoSecond.convert(d1);
    AssertEquals(id, d2.id, "converted 'id' field value");
    AssertEquals(text, d2.text, "Converted 'text' field value");
    AssertEquals(true, d2.enabled, "Converted constant 'enabled' field value");
    DemoThirdOld oldPacket = new DemoThirdOld { field2=42, field4=true, field6="ignored" };
    DemoThirdNew newPacket = DemoThirdNew.convert(oldPacket);
    AssertEquals(42L, newPacket.field1, "Widened 'field1' field value");
    AssertEquals(true, newPacket.field3, "Copied 'field3' field value");
    AssertEquals(123, newPacket.field5, "Constant 'field5' field value");
    
    List<long> expectedConvert1 = new List<long>(0);
    List<long> actualConvert1 = d1.convert().ConvertAll((p) => p.GetPacketHash());
    AssertEquals(string.Join(",", expectedConvert1), string.Join(",", actualConvert1), "Empty List of convertible BluePackets for DemoFirst");

    List<long> expectedConvert2 = new List<long> {d1.GetPacketHash()};
    List<long> actualConvert2 = d2.convert().ConvertAll((p) => p.GetPacketHash());
    AssertEquals(string.Join(",", expectedConvert2), string.Join(",", actualConvert2), "List of convertible BluePackets for DemoSecond");

    Console.WriteLine("PASS");
  }

  private void testAutoConvert(String name)
  {
    Console.Write(name + ": ");

    AssertEquals(typeof(DemoSecond), DemoFirst.convertTo, "DemoFirst convertTo metadata");
    AssertEquals(0, DemoFirst.convertFrom.Length, "DemoFirst convertFrom metadata");
    AssertTrue(DemoSecond.convertTo == null, "DemoSecond convertTo metadata");
    AssertEquals(1, DemoSecond.convertFrom.Length, "DemoSecond convertFrom metadata size");
    AssertEquals(typeof(DemoFirst), DemoSecond.convertFrom[0], "DemoSecond convertFrom metadata");

    DemoFirst first = new DemoFirst { id = 123, text = new String[] {"line1", "line2"} };
    BluePacket converted = BluePacket.Deserialize(first.Serialize());
    AssertEquals(typeof(DemoSecond), converted.GetType(), "deserialized DemoFirst is converted");
    DemoSecond second = (DemoSecond) converted;
    AssertEquals(123, second.id, "converted 'id' field value");
    AssertEquals("line1,line2", string.Join(",", second.text), "converted 'text' field value");
    AssertEquals(true, second.enabled, "converted constant 'enabled' field value");

    Console.WriteLine("PASS");
  }

  static void Main(string[] args)
  {
    TestBluePacket test = new TestBluePacket();

    test.SetUp();
    test.TestToString("testToString", "toString.txt", test.demoPacket);
    test.TestToString("testToString2", "toString2.txt", test.demoPacket2);
    test.TestToString("testToString3", "toString3.txt", test.demoPacket3);
    test.TestToString("testToStringU", "toStringU.txt", test.demoPacketU);
    test.TestPacketHash("testVersionHash", test.demoPacket, -7655671355778935868L);
    test.TestPacketHash("testVersionHash2", test.demoPacket2, -2843842372215306214L);
    test.TestPacketHash("testVersionHash3", test.demoPacket3, 7017743869305026213L);
    test.TestPacketHash("testVersionHashU", test.demoPacketU, 4436886959950420991L);
    test.TestSerialize("testSerialize", test.demoPacket, test.demoPacketBin);
    test.TestSerialize("testSerialize2", test.demoPacket2, test.demoPacket2Bin);
    test.TestSerialize("testSerialize3", test.demoPacket3, test.demoPacket3Bin);
    test.TestSerialize("testSerializeU", test.demoPacketU, test.demoPacketUBin);
    test.TestDeserialize("testDeserialize", test.demoPacket, test.demoPacketBin);
    test.TestDeserialize("testDeserialize2", test.demoPacket2, test.demoPacket2Bin);
    test.TestDeserialize("testDeserialize3", test.demoPacket3, test.demoPacket3Bin);
    test.TestDeserialize("testDeserializeU", test.demoPacketU, test.demoPacketUBin);
    test.TestUnsigned("testUnsigned");
    test.TestAbstracts("testAbstract1", typeof(DemoPacketAbs1), typeof(IDemoAbstract1));
    test.TestAbstracts("testAbstract2", typeof(DemoPacketAbs2), typeof(IDemoAbstract2));
    test.TestAbstracts("testAbstract12", typeof(DemoPacketAbs12), typeof(IDemoAbstract1), typeof(IDemoAbstract2));
    test.TestNotAbstracts("testNotAbstract1", typeof(DemoPacketAbs1), typeof(IDemoAbstract2));
    test.TestNotAbstracts("testNotAbstract2", typeof(DemoPacketAbs2), typeof(IDemoAbstract1));

    test.TestPacketHash("testDeprecated1", new DemoVersion__3FC7F86674610139{}, 4595915063677747513L);
    test.TestPacketHash("testDeprecated2", new DemoVersion{}, 7260826007793545337L);
    test.TestPacketHash("testIncludeDeprecated1", new DemoIncludeVersion__3D76B02436B66199{}, 4428920953148694937L);
    test.TestPacketHash("testIncludeDeprecated2", new DemoIncludeVersion{}, -4044184110803273943L);

    test.testConvert("testConvert");
    test.testAutoConvert("testAutoConvert");
    test.testForceConvert("testForceConvert");
    test.testEnumConvert("testEnumConvert");
    test.testApiVersion("testApiVersion");
    test.TestMutuallyRecursivePackets("testMutuallyRecursivePackets");
  }

  private void TestMutuallyRecursivePackets(String name)
  {
    Console.Write(name + ": ");

    // Test 1: Create instances and set references
    RecursiveA a = new RecursiveA();
    RecursiveB b = new RecursiveB();
    a.b = b;
    AssertEquals(b, a.b, "set reference");

    // Test 2: Serialize/deserialize with reference
    byte[] data = a.Serialize();
    BluePacket bp = BluePacket.Deserialize(data);
    RecursiveA restored = (RecursiveA) bp;
    AssertEquals(b.ToString(), restored.b.ToString(), "deserialize with reference");

    // Test 3: Empty reference
    RecursiveA aEmpty = new RecursiveA();
    byte[] dataEmpty = aEmpty.Serialize();
    BluePacket bpEmpty = BluePacket.Deserialize(dataEmpty);
    RecursiveA restoredEmpty = (RecursiveA) bpEmpty;
    AssertTrue(restoredEmpty.b == null, "deserialize empty reference");

    // Test 4: Reverse direction
    RecursiveB b2 = new RecursiveB();
    RecursiveA a2 = new RecursiveA();
    b2.a = a2;
    byte[] data2 = b2.Serialize();
    BluePacket bp2 = BluePacket.Deserialize(data2);
    RecursiveB restored2 = (RecursiveB) bp2;
    AssertEquals(a2.ToString(), restored2.a.ToString(), "deserialize reverse reference");

    Console.WriteLine("PASS");
  }
}
