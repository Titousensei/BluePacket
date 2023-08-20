package test;

import java.io.*;
import java.util.*;
import java.nio.file.Files;
import java.nio.file.Paths;

import org.bluepacket.BluePacket;
import org.bluepacket.BluePacketRegistry;

class TestBluePacket
{
  private static final String TESTDATA_DIR = "../../testdata/";

  private BluePacketRegistry registry_;

  private DemoPacket demoPacket;
  private byte[] demoPacketBin;

  private DemoPacket2 demoPacket2;
  private byte[] demoPacket2Bin;

  private DemoPacket3 demoPacket3;
  private byte[] demoPacket3Bin;

  private DemoUnsigned demoPacketU;
  private byte[] demoPacketUBin;

  private String[] myStrings = new String[] {"abcdef", "xyz", "w", null, "asdfghjkl;"};

  private void assertEquals(int expected, int actual, String msg)
  {
    if (actual != expected) {
      System.out.println("assertEquals failed!");
      System.out.println("  Expected:" + expected);
      System.out.println("  Actual  :" + actual);
      throw new AssertionError(msg);
    }
  }

  private void assertEquals(Object expected, Object actual, String msg)
  {
    if (!actual.equals(expected)) {
      System.out.println("assertEquals failed!");
      System.out.println("  Expected:" + expected);
      System.out.println("  Actual  :" + actual);
      throw new AssertionError(msg);
    }
  }

  private void assertEquals(Object[] expected, Object[] actual, String msg)
  {
    if (!Arrays.equals(actual, expected)) {
      System.out.println("assertEquals failed!");
      System.out.println("  Expected:" + Arrays.toString(expected));
      System.out.println("  Actual  :" + Arrays.toString(actual));
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
    registry_ = new BluePacketRegistry();
    registry_.register("test");

    demoPacket = new DemoPacket()
        .setFBoolean(true)
        .setFByte((byte)99)
        .setFDouble(1.23456789)
        .setFFloat(3.14f)
        .setFInt(987654321)
        .setFLong(101112131415L)
        .setFShort((short)2345)
        .setFString("abcdefåäöàê")
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
        .setABoolean(new boolean[] {
            true, false, true, false, true, false, true, false,
            false, true, false, true, false, true, false, true,
            false, false, true
        })
        .setAByte(new byte[] {99, 98, 97, 96})
        .setADouble(new double[] {1.23456789, 2.3456789})
        .setAFloat(new float[] {3.14f})
        .setAInt(new int[] {987654321, 87654321})
        .setALong(new long[] {101112131415L, 1617181920L})
        .setAShort(new short[] {2345, 3456, 4567})
        .setAString(myStrings)
        .setAEmpty(new String[0])
        .setLargeEnum1(DemoEnum260.z8)
        .setLargeEnum2(DemoEnum260.b3)
        .setALargeEnum(new DemoEnum260[] {DemoEnum260.z3, DemoEnum260.d7, DemoEnum260.z7});

    demoPacket2Bin = readBinary(TESTDATA_DIR + "DemoPacket2.bin");

    demoPacket3 = new DemoPacket3()
        .setPossible(new DemoEnum[] {DemoEnum.NO_DOUBT, DemoEnum.YES});

    demoPacket3Bin = readBinary(TESTDATA_DIR + "DemoPacket3.bin");

    demoPacket.xPacket = demoPacket3;

    demoPacketU = new DemoUnsigned()
        .setUb((byte) 200)
        .setUs((short) 45678)
        .setLub(new byte[] {(byte) 201, (byte) 5})
        .setLus(new short[] {(short) 43210, (short) 1234})
        .setA0(true)
        .setA1(false)
        .setA2(true)
        .setA3(false)
        .setA4(true)
        .setA5(false)
        .setA6(true)
        .setA7(false)
        .setB0(false)
        .setB1(true)
        .setB2(false)
        .setB3(true)
        .setB4(false)
        .setB5(true)
        .setB6(false)
        .setB7(true)
        .setC0(false)
        .setC1(false)
        .setC2(true);

    demoPacketUBin = readBinary(TESTDATA_DIR + "DemoPacketU.bin");
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
    BluePacket bp = BluePacket.deserialize(registry_, bin);
    assertEquals(packet.toString(), bp.toString(), "deserialize()");
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

  private void testSetters(String name)
  throws Exception
  {
    System.out.print(name + ": ");
    List<String> strings = new ArrayList<>();
    strings.add("A2");
    strings.add("B1");

    DemoPacket2 packet = new DemoPacket2().setAString(strings);
    assertEquals(new String[] {"A2", "B1"}, packet.aString, "set collection");

    packet.setAString("abcdef", "xyz", "w", null, "asdfghjkl;");
    assertEquals(myStrings, packet.aString, "set varargs");

    System.out.println("PASS");
  }

  private void testUnsigned(String name)
  throws Exception
  {
    System.out.print(name + ": ");

    assertEquals(-56, demoPacketU.ub, "unsigned as signed byte");
    assertEquals(200, demoPacketU.getUbAsInt(), "get unsigned byte as intended");
    assertEquals(-19858, demoPacketU.us, "unsigned as signed short");
    assertEquals(45678, demoPacketU.getUsAsInt(), "get unsigned short as intended");

    DemoPacket packet = new DemoPacket()
        .setFByte((byte) -99)
        .setFShort((short) -2345);

    assertEquals(-99, packet.fByte, "signed byte");
    assertEquals(-99, packet.getFByteAsInt(), "get signed byte as intended");
    assertEquals(-2345, packet.fShort, "signed short");
    assertEquals(-2345, packet.getFShortAsInt(), "get signed short as intended");

    assertEquals(-56, (byte) 200, "cast unsigned byte to signed byte as int");
    assertEquals(-19858, (short) 45678, "cast unsigned short to signed short as int");
    assertEquals(200, BluePacket.unsigned((byte) -56), "cast signed byte to unsigned byte as int");
    assertEquals(45678, BluePacket.unsigned((short) -19858), "cast signed short to unsigned short as int");

    System.out.println("PASS");
  }

  public static void main(String[] args)
  throws Exception
  {
    TestBluePacket test = new TestBluePacket();

    test.setUp();
    test.testToString("testToString", "toString.txt", test.demoPacket);
    test.testToString("testToString2", "toString2.txt", test.demoPacket2);
    test.testToString("testToString3", "toString3.txt", test.demoPacket3);
    test.testToString("testToStringU", "toStringU.txt", test.demoPacketU);
    test.testPacketHash("testVersionHash", test.demoPacket, -3377904526771042813L);
    test.testPacketHash("testVersionHash2", test.demoPacket2, -4035910894404497038L);
    test.testPacketHash("testVersionHash3", test.demoPacket3, 3706623474888074790L);
    test.testPacketHash("testVersionHashU", test.demoPacketU, 4436886959950420991L);
    test.testSerialize("testSerialize", test.demoPacket, test.demoPacketBin);
    test.testSerialize("testSerialize2", test.demoPacket2, test.demoPacket2Bin);
    test.testSerialize("testSerialize3", test.demoPacket3, test.demoPacket3Bin);
    test.testSerialize("testSerializeU", test.demoPacketU, test.demoPacketUBin);
    test.testDeserialize("testDeserialize", test.demoPacket, test.demoPacketBin);
    test.testDeserialize("testDeserialize2", test.demoPacket2, test.demoPacket2Bin);
    test.testDeserialize("testDeserialize3", test.demoPacket3, test.demoPacket3Bin);
    test.testDeserialize("testDeserializeU", test.demoPacketU, test.demoPacketUBin);
    test.testSetters("testSetters");
    test.testUnsigned("testUnsigned");
  }
}
