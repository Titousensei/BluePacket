package test;

import java.io.*;
import java.util.*;
import java.nio.file.Files;
import java.nio.file.Paths;

import org.bluesaga.network.BluePacket;

class TestBluePacket
{
  private static final String TESTDATA_DIR = "../../testdata/";

  private DemoPacket demoPacket;
  private byte[] demoPacketBin;
  
  private void assertEquals(Object expected, Object actual, String msg)
  {
    if (!actual.equals(expected)) {
      System.out.println("assertEquals failed!");
      System.out.println("  Expected:" + expected);
      System.out.println("  Actual  :" + actual);
      throw new AssertionError(msg);
    }
  }

  private void assertEquals(byte[] expected, byte[] actual, String msg)
  {
    if (!Arrays.equals(actual, expected)) {
      System.out.println("assertEquals failed!");
      System.out.println("  Expected:" + Arrays.toString(expected));
      System.out.println("  Actual  :" + Arrays.toString(actual));
      throw new AssertionError(msg);
    }
  }
  
  private byte[] readBinary(String path)
  throws FileNotFoundException, IOException
  {
    byte[] data = null;
    try (FileInputStream in = new FileInputStream(TESTDATA_DIR + "DemoPacket.bin")) {
      data = new byte[in.available()];
      in.read(data);
    }
    return data;
  }

  private void setUp()
  throws Exception
  {
    BluePacket.init("test");
  
    demoPacket = new DemoPacket()
        .setFBoolean(true)
        .setFByte((byte)99)
        .setFDouble(1.23456789)
        .setFFloat(3.14f)
        .setFInt(987654321)
        .setFLong(101112131415L)
        .setFShort((short)2345)
        .setFString("abcdef")
        .setFEnum(DemoPacket.MyEnum.MAYBE)
        .setOEnum(DemoEnum.NO_DOUBT)
        .setFInner(new DemoPacket.MyInner().setIInteger(88));

    DemoPacket.MyInner[] inner = new DemoPacket.MyInner[2];
    inner[0] = new DemoPacket.MyInner();
    inner[0].iInteger = 777;
    inner[1] = new DemoPacket.MyInner();
    inner[1].iInteger = 6666;
    demoPacket.setAInner(inner);

    demoPacket.fOuter = new DemoOuter().setOInt(191);

    demoPacket.setAOuter(new DemoOuter[1]);
    demoPacket.aOuter[0] = new DemoOuter().setOInt(282).setOString(":-)");
    
    demoPacketBin = readBinary(TESTDATA_DIR + "DemoPacket.bin");
  }


  private void testPacketHash()
  throws Exception
  {
    System.out.print("testVersionHash: ");
    assertEquals(3909449246358733856L, demoPacket.getPacketHash(), "getPacketHash()");
    System.out.println("PASS");
  }
  
  private void testDeserialize()
  throws Exception
  {
    System.out.print("testDeserialize: ");
    BluePacket bp = BluePacket.deserialize(demoPacketBin, false);
    assertEquals(demoPacket.toString(), bp.toString(), "toString()");
    System.out.println("PASS");
  }
  
  private void testSerialize()
  throws Exception
  {
    System.out.print("testSerialize: ");
    byte[] data = demoPacket.serialize();
    try (FileOutputStream out = new FileOutputStream("gen/DemoPacket.serialized")) {
      out.write(data);
    }
    
    assertEquals(demoPacketBin, data, "serialize()");
    System.out.println("PASS");
  }
  
  private void testToString()
  throws Exception
  {
    System.out.print("testToString: ");
    List<String> strings = Files.readAllLines(Paths.get(TESTDATA_DIR + "toString.txt"));
    assertEquals(demoPacket.toString(), strings.get(0), "toString()");
    System.out.println("PASS");
  }
  
  public static void main(String[] args)
  throws Exception
  {
    TestBluePacket test = new TestBluePacket();
    
    test.setUp();
    test.testToString();
    test.testPacketHash();
    test.testDeserialize();
    test.testSerialize();
  }
}
