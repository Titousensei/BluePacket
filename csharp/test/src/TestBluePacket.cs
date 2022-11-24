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
      fString = "abcdef",
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
        aBoolean = new bool[] {true, false, true},
        aByte = new sbyte[] {99, 98, 97, 96},
        aDouble = new double[] {1.23456789, 2.3456789},
        aFloat = new float[] {3.14f},
        aInt = new int[] {987654321, 87654321},
        aLong = new long[] {101112131415L, 1617181920L},
        aShort = new short[] {2345, 3456, 4567},
        aString = new String[] {"abcdef", "xyz", "w", null, "asdfghjkl;"},
        aEmpty = new String[0]
    };

    demoPacket2Bin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket2.bin");

    demoPacket3 = new DemoPacket3 {
        possible = new DemoEnum[] {DemoEnum.NO_DOUBT, DemoEnum.YES}
    };

    demoPacket3Bin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket3.bin");
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
    BluePacket bp = BluePacket.Deserialize(bin, false);
    AssertEquals(packet.ToString(), bp.ToString(), "ToString()");
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

  static void Main(string[] args)
  {
    TestBluePacket test = new TestBluePacket();

    test.SetUp();
    test.TestToString("testToString", "toString.txt", test.demoPacket);
    test.TestToString("testToString2", "toString2.txt", test.demoPacket2);
    test.TestToString("testToString3", "toString3.txt", test.demoPacket3);
    test.TestPacketHash("testVersionHash", test.demoPacket, 3909449246358733856L);
    test.TestPacketHash("testVersionHash2", test.demoPacket2, -7277881074505903123L);
    test.TestPacketHash("testVersionHash3", test.demoPacket3, 3706623474888074790L);
    test.TestSerialize("testSerialize", test.demoPacket, test.demoPacketBin);
    test.TestSerialize("testSerialize2", test.demoPacket2, test.demoPacket2Bin);
    test.TestSerialize("testSerialize3", test.demoPacket3, test.demoPacket3Bin);
    test.TestDeserialize("testDeserialize", test.demoPacket, test.demoPacketBin);
    test.TestDeserialize("testDeserialize2", test.demoPacket2, test.demoPacket2Bin);
    test.TestDeserialize("testDeserialize3", test.demoPacket3, test.demoPacket3Bin);
  }
}
