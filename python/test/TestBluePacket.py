#! /usr/bin/env python3
import os, sys
import unittest

sys.path.append("../common")

from blue_packet import BluePacket, FieldTypeException
import gen.test as t

TESTDATA_DIR = "../../testdata/"


def parameters(*param_list):
  def _test(f):
    def wrapper(self):
      for params in param_list:
        f(self, *params)
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

  @parameters(
    (3909449246358733856, "DemoPacket"),
    (-7277881074505903123, "DemoPacket2"),
  )
  def testPacketHash(self, expected, packet):
    hash = _TEST_DATA[packet].packetHash
    self.assertEqual(expected, hash)

  @parameters(
    ("DemoPacket.bin", "DemoPacket"),
    ("DemoPacket2.bin", "DemoPacket2"),
  )  
  def testDeserialize(self, bin, packet):
    bp = BluePacket.deserialize(_TEST_DATA[bin], False)
    self.assertEqual(str(_TEST_DATA[packet]), str(bp))
  
  @parameters(
    ("DemoPacket.bin", "DemoPacket"),
    ("DemoPacket2.bin", "DemoPacket2"),
  )  
  def testSerialize(self, bin, packet):
    data = BluePacket()
    data.serialize(_TEST_DATA[packet])
    self.assertEqual(_TEST_DATA[bin], bytes(data))
  
  @parameters(
    ("toString.txt", "DemoPacket"),
    ("toString2.txt", "DemoPacket2"),
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

  def testSetByteNegative1(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fByte = -1000
    self.assertEqual(ex.exception.ftype, "byte")
    self.assertEqual(ex.exception.value, -1000)
    
  def testSetByteNegative2(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fByte = 1000
    self.assertEqual(ex.exception.ftype, "byte")
    self.assertEqual(ex.exception.value, 1000)
    
  def testSetByteNegative3(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fByte = True
    self.assertEqual(ex.exception.ftype, "byte")
    self.assertEqual(ex.exception.value, True)
    
  def testSetShortNegative1(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fShort = -1000000
    self.assertEqual(ex.exception.ftype, "short")
    self.assertEqual(ex.exception.value, -1000000)  
    
  def testSetShortNegative2(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fShort = 1000000
    self.assertEqual(ex.exception.ftype, "short")
    self.assertEqual(ex.exception.value, 1000000)
    
  def testSetShortNegative3(self):
    data = t.DemoPacket()
    with self.assertRaises(FieldTypeException) as ex:
      data.fShort = True
    self.assertEqual(ex.exception.ftype, "short")
    self.assertEqual(ex.exception.value, True)
    
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
    
    
if __name__ == '__main__':
    unittest.main()
