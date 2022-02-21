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
  
  private void AssertEquals(object expected, object actual, string msg)
  {
    Debug.Assert(
      actual == expected,
      msg + ":\nExpected:" + expected + "\nActual  :" + actual
    );
  }

  private void AssertEquals(byte[] expected, byte[] actual, string msg)
  {
    Debug.Assert(
      expected.SequenceEqual(actual),
      msg + ":\nExpected:" + expected + "\nActual  :" + actual
    );
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

    DemoPacket.MyInner[] inner = new DemoPacket.MyInner[2] {
      new DemoPacket.MyInner { iInteger = 777 },
      new DemoPacket.MyInner { iInteger = 6666 }
    };
    demoPacket.aInner = inner;
    demoPacket.fOuter = new DemoOuter { oInt = 191 };

    demoPacket.aOuter = new DemoOuter[1] {
      new DemoOuter { oInt = 282, oString = ":-)" }
    };
  
    demoPacketBin = File.ReadAllBytes(TESTDATA_DIR + "DemoPacket.bin");
  }


  private void TestPacketHash()
  {
    Console.Write("testVersionHash: ");
    AssertEquals(3909449246358733856L, demoPacket.GetPacketHash(), "GetPacketHash()");
    Console.WriteLine("PASS");
  }
  
  private void TestDeserialize()
  {
    Console.Write("testDeserialize: ");
    BluePacket bp = BluePacket.Deserialize(demoPacketBin, false);
    AssertEquals(demoPacket.ToString(), bp.ToString(), "ToString()");
    Console.WriteLine("PASS");
  }
  
  private void TestSerialize()
  {
    Console.Write("testSerialize: ");
    byte[] data = demoPacket.Serialize();
    File.WriteAllBytes("gen/DemoPacket.serialized", data);
    AssertEquals(demoPacketBin, data, "Serialize()");
    Console.WriteLine("PASS");
  }
  
  private void TestToString()
  {
    Console.Write("testToString: ");
    
    var strings = File.ReadAllLines(TESTDATA_DIR + "toString.txt");
    AssertEquals(demoPacket.ToString(), strings[0], "ToString()");
    Console.WriteLine("PASS");
  }
  
  static void Main(string[] args)
  {
    TestBluePacket test = new TestBluePacket();
    
    test.SetUp();
    test.TestToString();
    test.TestPacketHash();
    test.TestDeserialize();
    test.TestSerialize();
  }
}
