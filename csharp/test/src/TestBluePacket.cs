using System;
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
      new DemoPacket.MyInner { iInteger = 777 },
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
    AssertEquals(packet.ToString(), strings[0], "ToString()");
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

  private void testConvert(String name)
  {
    Console.Write(name + ": ");
    int id = 123;
    String[] text = new String[] {"line1", "line2"};
    DemoFirst d1 = new DemoFirst { id=id, text=text };
    DemoSecond d2 = DemoSecond.convert(d1);
    AssertEquals(id, d2.id, "converted 'id' field value");
    AssertEquals(text, d2.text, "Converted 'text' field value");
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
    test.TestPacketHash("testVersionHash", test.demoPacket, -3377904526771042813L);
    test.TestPacketHash("testVersionHash2", test.demoPacket2, -4035910894404497038L);
    test.TestPacketHash("testVersionHash3", test.demoPacket3, 3706623474888074790L);
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
  }
}
