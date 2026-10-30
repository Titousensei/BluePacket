from collections import deque
from math import floor, inf, isnan, log10
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

def _checkBluePacket(x, _):
  return hasattr(x, 'packetHash')

def _checkShort(x, _):
  return type(x) == int and -32768 <= x <= 32767

def _checkUShort(x, _):
  return type(x) == int and 0 <= x <= 65535

def _checkString(x, _):
  return x is None or type(x) == str

def _assertOther(x, t):
  return type(x).__name__ == t or type(x) == t

def assertType(value, ftype, is_list):
  if value is None:
    return
  if is_list:
    if type(value) != list:
      raise FieldTypeException("list " + ftype, value)
    for elem in value:
      if not _TYPE_VALIDATOR.get(ftype, _assertOther)(elem, ftype):
        raise FieldTypeException(ftype + " in list", elem)
  elif not _TYPE_VALIDATOR.get(ftype, _assertOther)(value, ftype):
    raise FieldTypeException(ftype, value)


_TYPE_VALIDATOR = {
  "byte": _checkByte,
  "double": _checkDouble,
  "long": _checkLong,
  "packet": _checkBluePacket,
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


def toQuotedString(x):
  return f'"{x}"' if x else ""


class BluePacket:
  def serialize(self):
    bpw = _BluePacketWriter()
    bpw.serialize(self)
    return bytes(bpw)

  @staticmethod
  def convert():
    return []


class BluePacketRegistry:

  def __init__(self, ):
        self._packet_id_to_class = {}
        self._packet_name_to_class = {}

  def register(self, module):
    for name, cl in inspect.getmembers(module):
      if not name.startswith("__"):
        h = getattr(cl, "packetHash", None)
        if h is not None:
          self._packet_id_to_class[h] = cl
          self._packet_name_to_class[name] = cl

  def deserialize(self, buffer):
    bpr = _BluePacketReader(buffer)
    return self.deserialize_internal(bpr)

  def deserialize_internal(self, bpr):
    # Header
    packetHash = bpr.readLong()
    if packetHash == 0:
      return None
    if packetHash not in self._packet_id_to_class:
      raise Exception(f"Unknown packetHash received: {packetHash}")

    packet = self._packet_id_to_class[packetHash]()

    # Body
    packet.populateData(self, bpr)

    # Convert when the packet type declares a mapping to another packet
    return self.convert_if_possible(packet)

  def convert_if_possible(self, packet):
    target = getattr(type(packet), "convertTo", None)
    if target is None:
      return packet
    # convertTo holds the class name, since importing that class here would
    # create a cycle with the target's import of this packet for its converter
    if not isinstance(target, type):
      target = self._packet_name_to_class.get(target)
      if target is None:
        # Target packet is not registered in this registry
        return packet

    converter = getattr(target, "convert" + type(packet).__name__, None)
    if converter is None:
      raise Exception(f"Packet {target.__name__} has no convert{type(packet).__name__} method")
    return converter(packet)

  def __str__(self):
    return f"BluePacketRegistry{self._packet_id_to_class}"


class _BluePacketWriter(bytearray):

  def serialize(self, packet):
    self.writeLong(packet.packetHash)
    packet.serializeData(self)

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
      self.writeUnsignedByte(length)
    else:
      self.writeUnsignedByte(_MAX_UNSIGNED_BYTE)
      self.writeInt(length)

  def writeString(self, field):
    if field is None:
        self.writeByte(0)
    else:
        b = field.encode('utf-8')
        self._writeSeqLength(len(b))
        self.extend(b)

  def writeBluePacket(self, field):
    if field is None:
        self.writeLong(0)
    else:
        self.serialize(field)

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
            self.writeUnsignedByte(b.value)

  def writeArrayLargeEnum(self, field):
    if field is None:
        self._writeSeqLength(0)
    else:
        self._writeSeqLength(len(field))
        for b in field:
            self.writeUnsignedShort(b.value)

  def writeListBool(self, field):
    if field is None:
        self.writeByte(0)
    else:
        self._writeSeqLength(len(field))
        bin = 0
        for i, b in enumerate(field):
          if b:
            bin |= (1 << (i % 8))
          if (i % 8) == 7:
            self.writeUnsignedByte(bin)
            bin = 0
        if (len(field) % 8) != 0:
          self.writeUnsignedByte(bin)


class _BluePacketReader(deque):

  def __init__(self, buffer):
    self.buffer = buffer
    self.offset = 0

  def _readStruct(self, format, size):
    i = self.offset
    self.offset += size
    return struct.unpack_from(format, self.buffer, i)[0]

  def readUnsignedByte(self):
    return self._readStruct('!B', 1)

  def readByte(self):
    return self._readStruct('!b', 1)

  def readSequenceLength(self):
    l = self.readUnsignedByte()
    if l == _MAX_UNSIGNED_BYTE:
      l = self.readInt()
    return l

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

  def readListBool(self):
    l = self.readSequenceLength()
    ret = []
    for i in range(l):
      if i % 8 == 0:
        bin = self.readUnsignedByte()
      masked = bin & (1 << (i % 8))
      ret.append(masked != 0)
    return ret

  def readString(self):
    l = self.readSequenceLength()
    i = self.offset
    self.offset += l
    return self.buffer[i:self.offset].decode('utf-8')


# Canonical cross-language conversion helpers.
_BP_FALSE_STRINGS = {"", "false", "f", "0", "no", "n", "off", "null", "none"}

_BP_INT_RANGES = {
  "byte": (-(2 ** 7), 2 ** 7 - 1),
  "ubyte": (0, 2 ** 8 - 1),
  "short": (-(2 ** 15), 2 ** 15 - 1),
  "ushort": (0, 2 ** 16 - 1),
  "int": (-(2 ** 31), 2 ** 31 - 1),
  "long": (-(2 ** 63), 2 ** 63 - 1),
}


def bpFormatFloat(value):
  if value != value:
    return "nan"
  if value == inf:
    return "inf"
  if value == -inf:
    return "-inf"
  text = repr(value)
  if '.' in text or 'e' in text or 'E' in text:
    return text
  return text + ".0"


def bpToString(value, is_enum=False):
  if is_enum:
    return value.name
  if type(value) == bool:
    return "true" if value else "false"
  if type(value) == float:
    return bpFormatFloat(value)
  return str(value)


def bpStringToBool(value):
  return value.strip().lower() not in _BP_FALSE_STRINGS


def bpToBool(value, is_enum=False):
  if is_enum:
    return True
  if type(value) == bool:
    return value
  if type(value) in (int, float):
    return value != 0
  return bpStringToBool(value)


def _bpParseInt(value):
  text = value.strip()
  try:
    return int(text, 10)
  except ValueError:
    pass
  try:
    number = float(text)
  except ValueError:
    return 0
  if isnan(number):
    return 0
  if number in (inf, -inf):
    return number
  return int(number)


def bpToInt(value, target, is_enum=False):
  if is_enum:
    value = value.value
  elif type(value) == bool:
    value = 1 if value else 0
  elif type(value) == str:
    value = _bpParseInt(value)
  low, high = _BP_INT_RANGES[target]
  if type(value) == float:
    if isnan(value):
      return 0
    if value == inf:
      return high
    if value == -inf:
      return low
    value = int(value)
  return max(low, min(high, value))


def bpToFloat(value, target, is_enum=False):
  if is_enum:
    value = value.value
  elif type(value) == bool:
    value = 1.0 if value else 0.0
  elif type(value) == str:
    try:
      value = float(value.strip())
    except ValueError:
      value = 0.0
  result = float(value)
  if target == "float" and not isnan(result):
    limit = 3.4028234663852886e38
    result = max(-limit, min(limit, result))
  return result


def bpEnumFromOrdinal(enum_type, ordinal):
  try:
    return enum_type(int(ordinal))
  except (ValueError, TypeError, OverflowError):
    return next(iter(enum_type))


def bpEnumFromString(enum_type, text):
  name = text.strip()
  try:
    return enum_type[name]
  except KeyError:
    pass
  try:
    return bpEnumFromOrdinal(enum_type, _bpParseInt(name))
  except ValueError:
    return next(iter(enum_type))
