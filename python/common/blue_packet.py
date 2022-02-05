from collections import deque
from math import floor, log10
import inspect
import struct

_MAX_UNSIGNED_BYTE = 255

class FieldTypeException(Exception):
  def __init__(self, ftype, value):
    self.ftype = ftype
    self.value = value
    
  def __str__(self):
    return f"Not a {self.ftype}: {self.value}"
    

def _assertBool(x, *_):
  if type(x) != bool:
    raise FieldTypeException("bool", x)

def _assertByte(x, *_):
  if type(x) != int or x < -128 or x > 127:
    raise FieldTypeException("byte", x)

def _assertFloat(x, t, _):
  if type(x) != float:
    raise FieldTypeException(t, x)

def _assertInt(x, t, _):
  if type(x) != int:
    raise FieldTypeException(t, x)

def _assertShort(x, t, _):
  if type(x) != int or x < -32768 or x > 32767:
    raise FieldTypeException("short", x)

def _assertString(x, t, _):
  if type(x) != str:
    raise FieldTypeException("string", x)

def _assertOther(x, t, is_list):
  if is_list:
    if type(x) != list:
      raise FieldTypeException("list " + t, x)
    for elem in x:
      if type(elem).__name__ != t:
        raise FieldTypeException(t + " in list", elem)
  elif type(x).__name__ != t:
    raise FieldTypeException(t, x)

_TYPE_VALIDATOR = {
  "bool": _assertBool,
  "byte": _assertByte,
  "double": _assertFloat,
  "float": _assertFloat,
  "int": _assertInt,
  "long": _assertInt,
  "short": _assertShort,
  "string": _assertString,
}

    
class BluePacket(bytearray):

  PACKETID_TO_CLASS = {}

  @classmethod
  def registerBluePackets(cls, module):
    for name, cl in inspect.getmembers(module):
      if not name.startswith("__"):
        h = getattr(cl, "packetHash", None)
        if h is not None:
          cls.PACKETID_TO_CLASS[h] = cl

  @classmethod
  def assertType(cls, value, ftype, is_list):
    if value is None:
      return
    _TYPE_VALIDATOR.get(ftype, _assertOther)(value, ftype, is_list)
    
  @classmethod
  def deserialize(cls, buffer, hasSequenceId):
    bpr = _BluePacketReader(buffer)
    
    # Header
    packetHash = bpr.readLong();
    if packetHash not in cls.PACKETID_TO_CLASS:
      raise Exception("Unknown packetHash received: " + packetHash)
    
    packet = cls.PACKETID_TO_CLASS[packetHash]()

    if hasSequenceId:
      packet.sequenceId = bpr.readLong()

    # Body
    packet.populateData(bpr)

    return packet

  def serialize(self, packet, sequenceId = None):
    # Header
    self.writeLong(packet.packetHash)
    if sequenceId is not None:
      self.writeLong(sequenceId)
    # Body
    packet.serializeData(self)

  def writeBool(self, field):
    self.extend(struct.pack('!b', 1 if field else 0))

  def writeByte(self, field):
    self.extend(struct.pack('!b', field))

  def writeShort(self, field):
    self.extend(struct.pack('!h', field))
  
  def writeInt(self, field):
    self.extend(struct.pack('!i', field))
  
  def writeLong(self, field):
    self.extend(struct.pack('!q', field))
  
  def writeFloat(self, field):
    self.extend(struct.pack('!f', field))
  
  def writeDouble(self, field):
    self.extend(struct.pack('!d', field))
  
  def _writeSeqLength(self, length):
    if (length < _MAX_UNSIGNED_BYTE):
      self.writeByte(length);
    else:
      self.writeByte(_MAX_UNSIGNED_BYTE)
      self.writeInt(length)
  
  def writeString(self, field):
    if field is None:
        self.writeByte(0)
    else:
        b = field.encode('utf-8')
        self._writeSeqLength(len(b))
        self.extend(b)

  def writeArray(self, field):
    if field is None:
        self.writeByte(0)
    else:
        self._writeSeqLength(len(field))
        for b in field:
            b.serializeData(self)


class _BluePacketReader(deque):

  def __init__(self, buffer):
    self.buffer = buffer
    self.offset = 0

  def _readStruct(self, format, size):
    i = self.offset
    self.offset += size
    return struct.unpack_from(format, self.buffer, i)[0]
    
  def readBoolean(self):
    return self.readByte() != 0
    
  def readUnsignedByte(self):
    return self._readStruct('!B', 1)
    
  def readByte(self):
    return self._readStruct('!b', 1)
    
  def readDouble(self):
    return self._readStruct('!d', 8)
    
  def readFloat(self):
    value = self._readStruct('!f', 4)
    sig = 6 - int(floor(log10(abs(value))))
    return round(value, sig)
    
  def readInt(self):
    return self._readStruct('!i', 4)
    
  def readLong(self):
    return self._readStruct('!q', 8)
    
  def readShort(self):
    return self._readStruct('!h', 2)
    
  def readString(self):
    l = self.readUnsignedByte()
    if l == _MAX_UNSIGNED_BYTE:
      l = self.readLong()
    i = self.offset
    self.offset += l
    return self.buffer[i:self.offset].decode('utf-8')
