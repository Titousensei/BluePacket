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
  
  private DemoPacket2 demoPacket2;
  private byte[] demoPacket2Bin;
  
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
    try (FileInputStream in = new FileInputStream(path)) {
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
    demoPacket2 = new DemoPacket2()
        .setFBoolean(new boolean[] {true, false, true})
        .setFByte(new byte[] {99, 98, 97, 96})
        .setFDouble(new double[] {1.23456789, 2.3456789})
        .setFFloat(new float[] {3.14f})
        .setFInt(new int[] {987654321, 87654321})
        .setFLong(new long[] {101112131415L, 1617181920L})
        .setFShort(new short[] {2345, 3456, 4567})
        .setFString(new String[] {"abcdef", "xyz", "w", "asdfghjkl;"});

    demoPacket2Bin = readBinary(TESTDATA_DIR + "DemoPacket2.bin");
  }

  private void testPacketHash(String name, BluePacket packet, long hash)
  throws Exception
  {
    System.out.print(name + ": ");
    assertEquals(hash, packet.getPacketHash(), "getPacketHash()");
    System.out.println("PASS");
  }
  
  private void testDeserialize(String name, BluePacket packet, byte[] bin)
  throws Exception
  {
    System.out.print(name + ": ");
    BluePacket bp = BluePacket.deserialize(bin, false);
    assertEquals(packet.toString(), bp.toString(), "toString()");
    System.out.println("PASS");
  }
  
  private void testSerialize(String name, BluePacket packet, byte[] bin)
  throws Exception
  {
    System.out.print(name + ": ");
    byte[] data = packet.serialize();
    try (FileOutputStream out = new FileOutputStream("gen/" + name + ".bin")) {
      out.write(data);
    }
    
    assertEquals(bin, data, "serialize()");
    System.out.println("PASS");
  }
  
  private void testToString(String name, String filename, BluePacket packet)
  throws Exception
  {
    System.out.print(name + ": ");
    List<String> strings = Files.readAllLines(Paths.get(TESTDATA_DIR + filename));
    assertEquals(strings.get(0), packet.toString(), "toString()");
    System.out.println("PASS");
  }
  
  public static void main(String[] args)
  throws Exception
  {
    TestBluePacket test = new TestBluePacket();
    
    test.setUp();
    test.testToString("testToString", "toString.txt", test.demoPacket);
    test.testToString("testToString2", "toString2.txt", test.demoPacket2);
    test.testPacketHash("testVersionHash", test.demoPacket, 3909449246358733856L);
    test.testPacketHash("testVersionHash2", test.demoPacket2, -2936897381744985570L);
    test.testSerialize("testSerialize", test.demoPacket, test.demoPacketBin);
    test.testSerialize("testSerialize2", test.demoPacket2, test.demoPacket2Bin);
    test.testDeserialize("testDeserialize", test.demoPacket, test.demoPacketBin);
    test.testDeserialize("testDeserialize2", test.demoPacket2, test.demoPacket2Bin);
  }
}
