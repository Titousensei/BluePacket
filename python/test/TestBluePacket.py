#! /usr/bin/env python3
import os, sys
import unittest

sys.path.append("../common")

from blue_packet import BluePacketRegistry, FieldTypeException, toSignedByte, toSignedShort, toUnsignedByte, toUnsignedShort
import gen.test as t

TESTDATA_DIR = "../../testdata/"


def parameters(*param_list):
  def _test(f):
    def wrapper(self):
      for params in param_list:
        try:
          f(self, *params)
        except Exception as ex:
          raise AssertionError(f"{type(ex).__name__} in {f.__name__}{params}")
    return wrapper
  return _test


_TEST_DATA = {}

class TestBluePacket(unittest.TestCase):
  _BP_REGISTRY = BluePacketRegistry()

  @classmethod
  def setUpClass(cls):
    cls._BP_REGISTRY.register(t)

    _TEST_DATA['DemoPacket'] = demoPacket = t.DemoPacket()
    demoPacket.fBoolean = True
    demoPacket.fByte = 99
    demoPacket.fDouble = 1.23456789
    demoPacket.fFloat = 3.14
    demoPacket.fInt = 987654321
    demoPacket.fLong = 101112131415
    demoPacket.fShort = 2345
    demoPacket.fString = "abcdefåäöàê"
    demoPacket.fEnum = t.DemoPacket.MyEnum.MAYBE
    demoPacket.oEnum = t.DemoEnum.NO_DOUBT
    demoPacket.fInner = t.DemoPacket.MyInner(iInteger=88)

    demoPacket.aInner = [
      t.DemoPacket.MyInner(iInteger=777),
      t.DemoPacket.MyInner(iInteger=6666),
    ]

    demoPacket.fOuter = t.DemoOuter(oInt=191)
    demoPacket.aOuter = [t.DemoOuter(oInt=282, oString=":-)")]

    with open(TESTDATA_DIR + "DemoPacket.bin", "rb") as f:
      _TEST_DATA['DemoPacket.bin'] = f.read()
    cls.maxDiff = None

    _TEST_DATA['DemoPacket2'] = demoPacket2 = t.DemoPacket2()
    demoPacket2.aBoolean = [
        True, False, True, False, True, False, True, False,
        False, True, False, True, False, True, False, True,
        False, False, True
    ]
    demoPacket2.aByte = [99, 98, 97, 96]
    demoPacket2.aDouble = [1.23456789, 2.3456789]
    demoPacket2.aFloat = [3.14]
    demoPacket2.aInt = [987654321, 87654321]
    demoPacket2.aLong = [101112131415, 1617181920]
    demoPacket2.aShort = [2345, 3456, 4567]
    demoPacket2.aString = ["abcdef", "xyz", "w", None, "asdfghjkl;"]
    demoPacket2.aEmpty = []
    demoPacket2.largeEnum1 = t.DemoEnum260.z8
    demoPacket2.largeEnum2 = t.DemoEnum260.b3
    demoPacket2.aLargeEnum = [t.DemoEnum260.z3, t.DemoEnum260.d7, t.DemoEnum260.z7]

    with open(TESTDATA_DIR + "DemoPacket2.bin", "rb") as f:
      _TEST_DATA['DemoPacket2.bin'] = f.read()

    _TEST_DATA['DemoPacket3'] = demoPacket3 = t.DemoPacket3()
    demoPacket3.possible = [t.DemoEnum.NO_DOUBT, t.DemoEnum.YES]

    with open(TESTDATA_DIR + "DemoPacket3.bin", "rb") as f:
      _TEST_DATA['DemoPacket3.bin'] = f.read()

    demoPacket.xPacket = demoPacket3

    _TEST_DATA['DemoPacketU'] = demoPacketU = t.DemoUnsigned()
    demoPacketU.ub = 200
    demoPacketU.us = 45678
    demoPacketU.lub = [201, 5]
    demoPacketU.lus = [43210, 1234]

    demoPacketU.a0 = True
    demoPacketU.a1 = False
    demoPacketU.a2 = True
    demoPacketU.a3 = False
    demoPacketU.a4 = True
    demoPacketU.a5 = False
    demoPacketU.a6 = True
    demoPacketU.a7 = False
    demoPacketU.b0 = False
    demoPacketU.b1 = True
    demoPacketU.b2 = False
    demoPacketU.b3 = True
    demoPacketU.b4 = False
    demoPacketU.b5 = True
    demoPacketU.b6 = False
    demoPacketU.b7 = True
    demoPacketU.c0 = False
    demoPacketU.c1 = False
    demoPacketU.c2 = True

    with open(TESTDATA_DIR + "DemoPacketU.bin", "rb") as f:
      _TEST_DATA['DemoPacketU.bin'] = f.read()

    _TEST_DATA["DemoVersion__3FC7F86674610139"] = t.DemoVersion__3FC7F86674610139()
    _TEST_DATA["DemoVersion"] = t.DemoVersion()
    _TEST_DATA["DemoIncludeVersion__3D76B02436B66199"] = t.DemoIncludeVersion__3D76B02436B66199()
    _TEST_DATA["DemoIncludeVersion"] = t.DemoIncludeVersion()


  @parameters(
    (-3377904526771042813, "DemoPacket"),
    (-4035910894404497038, "DemoPacket2"),
    (3706623474888074790, "DemoPacket3"),
    (4436886959950420991, "DemoPacketU"),
    (4595915063677747513, "DemoVersion__3FC7F86674610139"),
    (7260826007793545337, "DemoVersion"),
    (4428920953148694937, "DemoIncludeVersion__3D76B02436B66199"),
    (-4044184110803273943, "DemoIncludeVersion"),
  )
  def testPacketHash(self, expected, packet):
    hash = _TEST_DATA[packet].packetHash
    self.assertEqual(expected, hash)

  @parameters(
    ("DemoPacket.bin", "DemoPacket"),
    ("DemoPacket2.bin", "DemoPacket2"),
    ("DemoPacket3.bin", "DemoPacket3"),
    ("DemoPacketU.bin", "DemoPacketU"),
  )
  def testDeserialize(self, bin, packet):
    bp = self._BP_REGISTRY.deserialize(_TEST_DATA[bin])
    self.assertEqual(str(_TEST_DATA[packet]), str(bp))

  @parameters(
    ("DemoPacket.bin", "DemoPacket"),
    ("DemoPacket2.bin", "DemoPacket2"),
    ("DemoPacket3.bin", "DemoPacket3"),
    ("DemoPacketU.bin", "DemoPacketU"),
  )
  def testSerialize(self, bin, packet):
    data = _TEST_DATA[packet].serialize()
    self.assertEqual(_TEST_DATA[bin], data)

  @parameters(
    ("toString.txt", "DemoPacket"),
    ("toString2.txt", "DemoPacket2"),
    ("toString3.txt", "DemoPacket3"),
    ("toStringU.txt", "DemoPacketU"),
  )
  def testToString(self, tostring, packet):
    with open(TESTDATA_DIR + tostring) as f:
      expected = f.read().strip()
      self.assertEqual(str(_TEST_DATA[packet]), expected);

  @parameters(
    (t.DemoPacketAbs1, [t.DemoAbstract1]),
    (t.DemoPacketAbs2, [t.DemoAbstract2]),
    (t.DemoPacketAbs12, [t.DemoAbstract1, t.DemoAbstract1]),
  )
  def testAbstract(self, packet_class, abstract_classes):
    packet = packet_class()
    for cl in abstract_classes:
      self.assertTrue(isinstance(packet, cl))

  # negative testing

  def testSetBoolNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fBoolean = 0
    self.assertEqual(ex.exception.ftype, "bool")
    self.assertEqual(ex.exception.value, 0)

  @parameters(
    (-1000, ),
    (1000, ),
    (True, ),
    (200, ),
    (-129, ),
    (128, ),
  )
  def testSetByteNegative(self, val):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fByte = val
    self.assertEqual(ex.exception.ftype, "byte")
    self.assertEqual(ex.exception.value, val)

  @parameters(
    (-128, ),
    (10,),
    (127, ),
  )
  def testSetByteBoundary(self, val):
    data = t.DemoPacket()
    data.fByte = val
    self.assertEqual(data.fByte, val)

  @parameters(
    (-1000, ),
    (1000, ),
    (True, ),
    (-100, ),
    (-1, ),
    (256, ),
  )
  def testSetUnsignedByteNegative(self, val):
    data = t.DemoUnsigned()
    with self.assertRaises(FieldTypeException) as ex:
      data.ub = val
    self.assertEqual(ex.exception.ftype, "ubyte")
    self.assertEqual(ex.exception.value, val)

  @parameters(
    (0, ),
    (10,),
    (255, ),
  )
  def testSetUnsignedByteBoundary(self, val):
    data = t.DemoUnsigned()
    data.ub = val
    self.assertEqual(data.ub, val)

  @parameters(
    (-1000000, ),
    (1000000, ),
    (True, ),
    (40000, ),
    (-32769, ),
    (32768, ),
  )
  def testSetShortNegative(self, val):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fShort = val
    self.assertEqual(ex.exception.ftype, "short")
    self.assertEqual(ex.exception.value, val)

  @parameters(
    (-32768, ),
    (1000, ),
    (32767, ),
  )
  def testSetShortBoundary(self, val):
    data = t.DemoPacket()
    data.fShort = val
    self.assertEqual(data.fShort, val)

  @parameters(
    (-1000000, ),
    (1000000, ),
    (True, ),
    (90000, ),
    (-1, ),
    (65536, ),
  )
  def testSetUnsignedShortNegative(self, val):
    data = t.DemoUnsigned()
    with self.assertRaises(FieldTypeException) as ex:
      data.us = val
    self.assertEqual(ex.exception.ftype, "ushort")
    self.assertEqual(ex.exception.value, val)

  @parameters(
    (0, ),
    (1000, ),
    (65535, ),
  )
  def testSetUnsignedShortBoundary(self, val):
    data = t.DemoUnsigned()
    data.us = val
    self.assertEqual(data.us, val)

  @parameters(
    (t.DemoPacketAbs1, [t.DemoAbstract2]),
    (t.DemoPacketAbs2, [t.DemoAbstract1]),
  )
  def testNotAbstract(self, packet_class, abstract_classes):
    packet = packet_class()
    for cl in abstract_classes:
      self.assertTrue(not isinstance(packet, cl))

  def testSetIntNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fInt = "abc"
    self.assertEqual(ex.exception.ftype, "int")
    self.assertEqual(ex.exception.value, "abc")

  def testSetLongNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fLong = 1.2
    self.assertEqual(ex.exception.ftype, "long")
    self.assertEqual(ex.exception.value, 1.2)

  def testSetFloatNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fFloat = False
    self.assertEqual(ex.exception.ftype, "float")
    self.assertEqual(ex.exception.value, False)

  def testSetDoubleNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fDouble = "123"
    self.assertEqual(ex.exception.ftype, "double")
    self.assertEqual(ex.exception.value, "123")

  def testSetPacketNegaite(self):
    data = t.DemoPacket()
    val = "x"
    with self.assertRaises(FieldTypeException) as ex:
      data.xPacket = val
    self.assertEqual(ex.exception.ftype, "packet")
    self.assertEqual(ex.exception.value, val)

  def testSetStringNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fString = -1000
    self.assertEqual(ex.exception.ftype, "string")
    self.assertEqual(ex.exception.value, -1000)

  def testSetInnerNegative(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fInner = -1000
    self.assertEqual(ex.exception.ftype, "MyInner")
    self.assertEqual(ex.exception.value, -1000)

  def testSetInnerListNegative1(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.aInner = -1000
    self.assertEqual(ex.exception.ftype, "list MyInner")
    self.assertEqual(ex.exception.value, -1000)

  def testSetInnerListNegative2(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.aInner = [1,2,3]
    self.assertEqual(ex.exception.ftype, "MyInner in list")
    self.assertEqual(ex.exception.value, 1)

  def testSetByteNegative1(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fEnum = -1000
    self.assertEqual(ex.exception.ftype, "MyEnum")
    self.assertEqual(ex.exception.value, -1000)

  def testSetEnumListNegative1(self):
    data = t.DemoPacket3()
    with self.assertRaises(FieldTypeException) as ex:
      data.possible = -999
    self.assertEqual(ex.exception.ftype, "list DemoEnum")
    self.assertEqual(ex.exception.value, -999)

  def testSetEnumListNegative2(self):
    data = t.DemoPacket3()
    with self.assertRaises(FieldTypeException) as ex:
      data.possible = t.DemoEnum.YES
    self.assertEqual(ex.exception.ftype, "list DemoEnum")
    self.assertEqual(ex.exception.value, t.DemoEnum.YES)

  def testUnsigned(self):
    p0 = _TEST_DATA["DemoPacketU"]
    self.assertEqual(200, p0.ub)
    self.assertEqual(45678, p0.us)
    self.assertEqual([201, 5], p0.lub)
    self.assertEqual([43210, 1234], p0.lus)

    p1 = t.DemoPacket()
    p1.fByte = -99
    p1.fShort = -2345
    self.assertEqual(-99, p1.fByte)
    self.assertEqual(-2345, p1.fShort)

    p2 = t.DemoPacket2()
    p2.aByte = [-99, 98, -97, 96]
    p2.aShort = [2345, -3456, 4567]
    self.assertEqual([-99, 98, -97, 96], p2.aByte)
    self.assertEqual([2345, -3456, 4567], p2.aShort)

    self.assertEqual(-56, toSignedByte(200))
    self.assertEqual(-19858, toSignedShort(45678))
    self.assertEqual(200, toUnsignedByte(-56))
    self.assertEqual(45678, toUnsignedShort(-19858))
    
  def testConvert(self):
    id = 123
    text = ["line1", "line2"]
    d1 = t.DemoFirst(id=id, text=text)
    d2 = t.DemoSecond.convertDemoFirst(d1)
    self.assertEqual(id, d2.id)
    self.assertEqual(text, d2.text)
    
  def testApiVersion(self):
    self.assertNotEqual(0, t.BluePacketAPI.VERSION)
    self.assertIsNotNone(t.BluePacketAPI.VERSION_HEX)
    self.assertNotEqual("", t.BluePacketAPI.VERSION_HEX)
    
  def testConvertNegative(self):
    packet = t.DemoOuter(oInt=999)
    with self.assertRaises(FieldTypeException) as ex:
      _ = t.DemoSecond.convertDemoFirst(packet)

  def testForceInitNamedParamsNegative(self):
    with self.assertRaises(TypeError) as ex:
      _ = t.DemoOuter(282, ":-)")


if __name__ == '__main__':
    unittest.main()
