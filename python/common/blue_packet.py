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


def _checkByte(x, _):
  return type(x) == int and -128 <= x <= 127

def _checkUByte(x, _):
  return type(x) == int and 0 <= x <= 255

def _checkDouble(x, _):
  return type(x) == float

def _checkLong(x, _):
  return type(x) == int

def _checkShort(x, _):
  return type(x) == int and -32768 <= x <= 32767

def _checkUShort(x, _):
  return type(x) == int and 0 <= x <= 65535

def _checkString(x, _):
  return x is None or type(x) == str

def _assertOther(x, t):
  return type(x).__name__ == t

def _assertType(x, t, is_list):
  if is_list:
    if type(x) != list:
      raise FieldTypeException("list " + t, x)
    for elem in x:
      if not _TYPE_VALIDATOR.get(t, _assertOther)(elem, t):
        raise FieldTypeException(t + " in list", elem)
  elif not _TYPE_VALIDATOR.get(t, _assertOther)(x, t):
    raise FieldTypeException(t, x)

_TYPE_VALIDATOR = {
  "byte": _checkByte,
  "double": _checkDouble,
  "long": _checkLong,
  "short": _checkShort,
  "string": _checkString,
  "ubyte": _checkUByte,
  "ushort": _checkUShort,
}


def toSignedByte(x):
  if 0 <= x < 127:
    return x
  elif 128 <= x < 255:
    return x - 256
  raise FieldTypeException("ubyte", x)


def toSignedShort(x):
  if 0 <= x < 32767:
    return x
  elif 32768 <= x < 65536:
    return x - 65536
  raise FieldTypeException("ushort", x)


def toUnsignedByte(x):
  if -128 <= x < 128:
    return 255 & x
  raise FieldTypeException("byte", x)


def toUnsignedShort(x):
  if -32768 <= x < 32768:
    return 65535 & x
  raise FieldTypeException("short", x)


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
    _assertType(value, ftype, is_list)

  @classmethod
  def deserialize(cls, buffer):
    bpr = _BluePacketReader(buffer)

    # Header
    packetHash = bpr.readLong();
    if packetHash not in cls.PACKETID_TO_CLASS:
      raise Exception(f"Unknown packetHash received: {packetHash}")

    packet = cls.PACKETID_TO_CLASS[packetHash]()

    # Body
    packet.populateData(bpr)

    return packet

  def serialize(self, packet):
    self.writeLong(packet.packetHash)
    packet.serializeData(self)

  def writeBool(self, field):
    self.extend(struct.pack('!b', 1 if field else 0))

  def writeByte(self, field):
    self.extend(struct.pack('!b', field))

  def writeUnsignedByte(self, field):
    self.extend(struct.pack('!B', field))

  def writeShort(self, field):
    self.extend(struct.pack('!h', field))

  def writeUnsignedShort(self, field):
    self.extend(struct.pack('!H', field))

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

  def writeArrayNative(self, field, serialize_fn):
    if field is None:
        self.writeByte(0)
    else:
        self._writeSeqLength(len(field))
        for b in field:
            serialize_fn(b)

  def writeArrayEnum(self, field):
    if field is None:
        self.writeByte(0)
    else:
        self._writeSeqLength(len(field))
        for b in field:
            self.writeByte(b.value)


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

  def readUnsignedShort(self):
    return self._readStruct('!H', 2)

  def readString(self):
    l = self.readUnsignedByte()
    if l == _MAX_UNSIGNED_BYTE:
      l = self.readLong()
    i = self.offset
    self.offset += l
    return self.buffer[i:self.offset].decode('utf-8')
