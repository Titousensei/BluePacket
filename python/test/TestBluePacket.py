#! /usr/bin/env python3
import os, sys
import unittest

sys.path.append("../common")

from blue_packet import BluePacket, FieldTypeException
import gen.test as t

TESTDATA_DIR = "../../testdata/"

class TestBluePacket(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    BluePacket.registerBluePackets(t)
  
    cls.demoPacket = t.DemoPacket()
    cls.demoPacket.fBoolean = True
    cls.demoPacket.fByte = 99
    cls.demoPacket.fDouble = 1.23456789
    cls.demoPacket.fFloat = 3.14
    cls.demoPacket.fInt = 987654321
    cls.demoPacket.fLong = 101112131415
    cls.demoPacket.fShort = 2345
    cls.demoPacket.fString = "abcdef"
    cls.demoPacket.fEnum = t.DemoPacket.MyEnum.MAYBE
    cls.demoPacket.oEnum = t.DemoEnum.NO_DOUBT
    cls.demoPacket.fInner = t.DemoPacket.MyInner(iInteger=88)

    cls.demoPacket.aInner = [
      t.DemoPacket.MyInner(iInteger=777),
      t.DemoPacket.MyInner(iInteger=6666),
    ]
      
    cls.demoPacket.fOuter = t.DemoOuter(oInt=191)
    cls.demoPacket.aOuter = [t.DemoOuter(oInt=282, oString=":-)")]
    
    with open(TESTDATA_DIR + "DemoPacket.bin", "rb") as f:
      cls.demoPacketBin = f.read()
    cls.maxDiff = None

  def testPacketHash(self):
    self.assertEqual(3909449246358733856, self.demoPacket.packetHash)
  
  def testDeserialize(self):
    bp = BluePacket.deserialize(self.demoPacketBin, False)
    self.assertEqual(str(self.demoPacket), str(bp))
  
  def testSerialize(self):
    data = BluePacket()
    data.serialize(self.demoPacket)
    self.assertEqual(self.demoPacketBin, bytes(data))
  
  def testToString(self):
    with open(TESTDATA_DIR + "toString.txt") as f:
      expected = f.read().strip()
      self.assertEqual(str(self.demoPacket), expected);

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
