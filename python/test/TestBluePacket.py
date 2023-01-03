#! /usr/bin/env python3
import os, sys
import unittest

sys.path.append("../common")

from blue_packet import BluePacket, FieldTypeException, toSignedByte, toSignedShort, toUnsignedByte, toUnsignedShort
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

  @classmethod
  def setUpClass(cls):
    BluePacket.registerBluePackets(t)

    _TEST_DATA['DemoPacket'] = demoPacket = t.DemoPacket()
    demoPacket.fBoolean = True
    demoPacket.fByte = 99
    demoPacket.fDouble = 1.23456789
    demoPacket.fFloat = 3.14
    demoPacket.fInt = 987654321
    demoPacket.fLong = 101112131415
    demoPacket.fShort = 2345
    demoPacket.fString = "abcdef"
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
    demoPacket2.aBoolean = [True, False, True]
    demoPacket2.aByte = [99, 98, 97, 96]
    demoPacket2.aDouble = [1.23456789, 2.3456789]
    demoPacket2.aFloat = [3.14]
    demoPacket2.aInt = [987654321, 87654321]
    demoPacket2.aLong = [101112131415, 1617181920]
    demoPacket2.aShort = [2345, 3456, 4567]
    demoPacket2.aString = ["abcdef", "xyz", "w", None, "asdfghjkl;"]
    demoPacket2.aEmpty = []

    with open(TESTDATA_DIR + "DemoPacket2.bin", "rb") as f:
      _TEST_DATA['DemoPacket2.bin'] = f.read()

    _TEST_DATA['DemoPacket3'] = demoPacket3 = t.DemoPacket3()
    demoPacket3.possible = [t.DemoEnum.NO_DOUBT, t.DemoEnum.YES]

    with open(TESTDATA_DIR + "DemoPacket3.bin", "rb") as f:
      _TEST_DATA['DemoPacket3.bin'] = f.read()

    _TEST_DATA['DemoPacketU'] = demoPacketU = t.DemoUnsigned()
    demoPacketU.ub = 200
    demoPacketU.us = 45678
    demoPacketU.lub = [201, 5]
    demoPacketU.lus = [43210, 1234]

    with open(TESTDATA_DIR + "DemoPacketU.bin", "rb") as f:
      _TEST_DATA['DemoPacketU.bin'] = f.read()

  @parameters(
    (3909449246358733856, "DemoPacket"),
    (-7277881074505903123, "DemoPacket2"),
    (3706623474888074790, "DemoPacket3"),
    (-2484828727609685089, "DemoPacketU"),
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
    bp = BluePacket.deserialize(_TEST_DATA[bin], False)
    self.assertEqual(str(_TEST_DATA[packet]), str(bp))

  @parameters(
    ("DemoPacket.bin", "DemoPacket"),
    ("DemoPacket2.bin", "DemoPacket2"),
    ("DemoPacket3.bin", "DemoPacket3"),
    ("DemoPacketU.bin", "DemoPacketU"),
  )
  def testSerialize(self, bin, packet):
    data = BluePacket()
    data.serialize(_TEST_DATA[packet])
    self.assertEqual(_TEST_DATA[bin], bytes(data))

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


if __name__ == '__main__':
    unittest.main()
