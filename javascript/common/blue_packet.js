"use strict";

const _MAX_UNSIGNED_BYTE = 255;
const _ENUM_TYPE_NAME = Symbol('enumTypeName');

const _TYPE_DEFAULT = {
  bool: false,
  byte: 0,
  double: 0,
  float: 0,
  int: 0,
  long: 0n,
  packet: null,
  short: 0,
  string: '',
  ubyte: 0,
  ushort: 0,
};

class FieldTypeException extends Error {
  constructor(ftype, value) {
    super(`Not a ${ftype}: ${value}`);
    this.ftype = ftype;
    this.value = value;
  }
}

function _checkByte(x, _) {
  return typeof x === 'number' && Number.isInteger(x) && -128 <= x && x <= 127;
}

function _checkUByte(x, _) {
  return typeof x === 'number' && Number.isInteger(x) && 0 <= x && x <= 255;
}

function _checkDouble(x, _) {
  return typeof x === 'number';
}

function _checkLong(x, _) {
  return typeof x === 'bigint';
}

function _checkBluePacket(x, _) {
  return x instanceof BluePacket;
}

function _checkShort(x, _) {
  return typeof x === 'number' && Number.isInteger(x) && -32768 <= x && x <= 32767;
}

function _checkUShort(x, _) {
  return typeof x === 'number' && Number.isInteger(x) && 0 <= x && x <= 65535;
}

function _checkString(x, _) {
  return x === null || x === undefined || typeof x === 'string';
}

function _assertOther(x, type) {
  if (typeof type === 'function') return x instanceof type;
  if (typeof x !== 'object' || x === null) return false;
  if (x.constructor && x.constructor.name === type) return true;
  return x.type === type;
}

function _checkBool(x, _) {
  return typeof x === 'boolean';
}

function _checkInt(x, _) {
  return typeof x === 'number' && Number.isInteger(x) && -2147483648 <= x && x <= 2147483647;
}

function _checkFloat(x, _) {
  return typeof x === 'number';
}

const _TYPE_VALIDATOR = {
  bool: _checkBool,
  byte: _checkByte,
  int: _checkInt,
  float: _checkFloat,
  double: _checkDouble,
  long: _checkLong,
  packet: _checkBluePacket,
  short: _checkShort,
  string: _checkString,
  ubyte: _checkUByte,
  ushort: _checkUShort,
};

function assertType(value, ftype, isList) {
  if (value === null || value === undefined) return;
  if (isList) {
    if (!Array.isArray(value)) {
      throw new FieldTypeException('list ' + ftype, value);
    }
    for (const elem of value) {
      const validator = _TYPE_VALIDATOR[ftype] || _assertOther;
      if (!validator(elem, ftype)) {
        throw new FieldTypeException(ftype + ' in list', elem);
      }
    }
  } else {
    const validator = _TYPE_VALIDATOR[ftype] || _assertOther;
    if (!validator(value, ftype)) {
      throw new FieldTypeException(ftype, value);
    }
  }
}

function toSignedByte(x) {
  if (0 <= x && x <= 127) return x;
  else if (128 <= x && x <= 255) return x - 256;
  throw new FieldTypeException('ubyte', x);
}

function toSignedShort(x) {
  if (0 <= x && x <= 32767) return x;
  else if (32768 <= x && x <= 65535) return x - 65536;
  throw new FieldTypeException('ushort', x);
}

function toUnsignedByte(x) {
  if (-128 <= x && x < 128) return 255 & x;
  throw new FieldTypeException('byte', x);
}

function toUnsignedShort(x) {
  if (-32768 <= x && x < 32768) return 65535 & x;
  throw new FieldTypeException('short', x);
}

function createEnum(typeName, ...names) {
  const e = {};
  const byValue = {};
  names.forEach((name, value) => {
    const entry = Object.freeze({ type: typeName, name, value });
    Object.defineProperty(e, name, { value: entry, enumerable: true });
    byValue[value] = entry;
  });
  Object.defineProperty(e, _ENUM_TYPE_NAME, { value: typeName });
  Object.defineProperty(e, 'valueOf', { value: (v) => byValue[v] });
  return Object.freeze(e);
}

function enumFromWire(enumType, value) {
  const entry = enumType.valueOf(value);
  if (entry === undefined) {
    throw new Error(`Unknown ${enumType[_ENUM_TYPE_NAME]} value: ${value}`);
  }
  return entry;
}

function toQuotedString(x) {
  return x ? '"' + x + '"' : '';
}

function _elemToString(elem, type) {
  if (type === 'string') return toQuotedString(elem);
  if (type === 'bool') return elem ? '1' : '0';
  if (elem instanceof BluePacket) return elem._fieldsToString();
  if (elem && elem.type !== undefined) return elem.name;
  return String(elem);
}

function defineTypedProperties(obj, typeInfo) {
  for (const [name, [type, isList]] of Object.entries(typeInfo)) {
    const priv = '_' + name;
    Object.defineProperty(obj, priv, { value: undefined, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(obj, name, {
      get() { return this[priv]; },
      set(v) { assertType(v, type, isList); this[priv] = v; },
      enumerable: true,
      configurable: true,
    });
  }
}

function _isOptionsObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function _defaultValue(type) {
  return Object.prototype.hasOwnProperty.call(_TYPE_DEFAULT, type) ? _TYPE_DEFAULT[type] : null;
}

/** Initialize an instance from an options object, applying defaults and validating field names. */
function initFields(instance, cls, args) {
  const typeInfo = cls.TYPE_INFO;
  const options = args[0];
  if (args.length > 1 || (args.length === 1 && !_isOptionsObject(options))) {
    throw new TypeError(cls.name + ' constructor expects a single options object');
  }

  const opts = options || {};
  for (const name of Object.keys(opts)) {
    if (!Object.prototype.hasOwnProperty.call(typeInfo, name)) {
      throw new TypeError(cls.name + ' has no field: ' + name);
    }
  }

  defineTypedProperties(instance, typeInfo);
  for (const [name, entry] of Object.entries(typeInfo)) {
    const [type, isList] = entry;
    let value;
    if (Object.prototype.hasOwnProperty.call(opts, name)) {
      value = opts[name];
    } else if (isList) {
      value = [];
    } else {
      value = entry.length > 2 ? entry[2] : _defaultValue(type);
    }
    instance[name] = value;
  }
  Object.seal(instance);
}

class BluePacket {
  get packetHash() {
    return this.constructor.packetHash;
  }

  serialize() {
    const bpw = new BluePacketWriter();
    bpw.writeLong(this.packetHash);
    this.serializeData(bpw);
    return bpw.toBuffer();
  }

  convert() {
    return [];
  }

  _fieldsToString() {
    const typeInfo = this.constructor.TYPE_INFO || {};
    let s = '';
    for (const name of Object.keys(typeInfo).sort()) {
      const [type, isList] = typeInfo[name];
      const value = this[name];
      if (isList) {
        if (value && value.length) {
          s += ' ' + name + '={' + type + ' *' + value.length + '|' + value.map((x) => _elemToString(x, type)).join('|') + '}';
        }
      } else if (type === 'bool') {
        if (value) s += ' ' + name + '=1';
      } else if (type === 'string') {
        if (value) s += ' ' + name + '=' + toQuotedString(value);
      } else if (value instanceof BluePacket) {
        s += ' ' + name + '=' + value.toString();
      } else if (value && value.type !== undefined) {
        if (value.value) s += ' ' + name + '=' + value.name;
      } else if (value) {
        s += ' ' + name + '=' + value;
      }
    }
    return s;
  }

  toString() {
    const cls = this.constructor;
    return '{' + cls.name + (cls.packetHex ? ' ' + cls.packetHex : '') + this._fieldsToString() + '}';
  }

  // Longs become decimal strings; convert them back with BigInt before constructing.
  toJSON() {
    return _toJSONValue(this, new WeakSet());
  }
}

function _toJSONValue(value, seen) {
  if (typeof value === 'bigint') return value.toString();
  if (value === null || typeof value !== 'object') return value;
  if (value instanceof BluePacket) {
    if (seen.has(value)) {
      throw new Error('Cannot convert a circular BluePacket structure to JSON');
    }
    seen.add(value);
    const out = {};
    for (const name of Object.keys(value.constructor.TYPE_INFO || {})) {
      out[name] = _toJSONValue(value[name], seen);
    }
    seen.delete(value);
    return out;
  }
  if (Array.isArray(value)) {
    return value.map((elem) => _toJSONValue(elem, seen));
  }
  return value;
}

class BluePacketRegistry {
  constructor() {
    this._packetIdToClass = new Map();
  }

  register(cls) {
    if (cls.packetHash !== undefined) {
      this._packetIdToClass.set(cls.packetHash, cls);
    }
  }

  deserialize(buffer) {
    const bpr = new BluePacketReader(buffer);
    return this._deserializeInternal(bpr);
  }

  _deserializeInternal(bpr) {
    const packetHash = bpr.readLong();
    if (packetHash === 0n) return null;
    const cls = this._packetIdToClass.get(packetHash);
    if (!cls) throw new Error('Unknown packetHash received: ' + packetHash);
    const packet = new cls();
    packet.populateData(this, bpr);
    return packet;
  }
}

class BluePacketWriter {
  constructor() {
    this.buffer = Buffer.alloc(64);
    this.offset = 0;
  }

  _ensure(size) {
    if (this.offset + size > this.buffer.length) {
      const newSize = Math.max(this.buffer.length * 2, this.offset + size);
      const newBuf = Buffer.alloc(newSize);
      this.buffer.copy(newBuf);
      this.buffer = newBuf;
    }
  }

  serialize(packet) {
    this.writeLong(packet.constructor.packetHash);
    packet.serializeData(this);
  }

  writeByte(v) { this._ensure(1); this.offset = this.buffer.writeInt8(v, this.offset); }
  writeUnsignedByte(v) { this._ensure(1); this.offset = this.buffer.writeUInt8(v, this.offset); }
  writeShort(v) { this._ensure(2); this.offset = this.buffer.writeInt16BE(v, this.offset); }
  writeUnsignedShort(v) { this._ensure(2); this.offset = this.buffer.writeUInt16BE(v, this.offset); }
  writeInt(v) { this._ensure(4); this.offset = this.buffer.writeInt32BE(v, this.offset); }
  writeLong(v) { this._ensure(8); this.offset = this.buffer.writeBigInt64BE(typeof v === 'bigint' ? v : BigInt(v), this.offset); }
  writeFloat(v) { this._ensure(4); this.offset = this.buffer.writeFloatBE(v, this.offset); }
  writeDouble(v) { this._ensure(8); this.offset = this.buffer.writeDoubleBE(v, this.offset); }

  _writeSeqLength(length) {
    if (length < _MAX_UNSIGNED_BYTE) {
      this.writeUnsignedByte(length);
    } else {
      this.writeUnsignedByte(_MAX_UNSIGNED_BYTE);
      this.writeInt(length);
    }
  }

  writeString(field) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      const b = Buffer.from(field, 'utf-8');
      this._writeSeqLength(b.length);
      this._ensure(b.length);
      b.copy(this.buffer, this.offset);
      this.offset += b.length;
    }
  }

  writeBluePacket(field) {
    if (field == null) {
      this.writeLong(0n);
    } else {
      this.serialize(field);
    }
  }

  writeArray(field) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      this._writeSeqLength(field.length);
      for (const b of field) {
        b.serializeData(this);
      }
    }
  }

  writeArrayNative(field, serializeFn) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      this._writeSeqLength(field.length);
      for (const b of field) {
        serializeFn.call(this, b);
      }
    }
  }

  writeArrayEnum(field) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      this._writeSeqLength(field.length);
      for (const b of field) {
        this.writeUnsignedByte(b.value);
      }
    }
  }

  writeArrayLargeEnum(field) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      this._writeSeqLength(field.length);
      for (const b of field) {
        this.writeUnsignedShort(b.value);
      }
    }
  }

  writeListBool(field) {
    if (field == null) {
      this.writeUnsignedByte(0);
    } else {
      this._writeSeqLength(field.length);
      let bin = 0;
      for (let i = 0; i < field.length; i++) {
        if (field[i]) bin |= (1 << (i % 8));
        if ((i % 8) === 7) {
          this.writeUnsignedByte(bin);
          bin = 0;
        }
      }
      if ((field.length % 8) !== 0) {
        this.writeUnsignedByte(bin);
      }
    }
  }

  toBuffer() {
    return this.buffer.slice(0, this.offset);
  }
}

class BluePacketReader {
  constructor(buffer) {
    this.buffer = buffer;
    this.offset = 0;
  }

  _readStruct(size) {
    const i = this.offset;
    this.offset += size;
    return { start: i, end: this.offset };
  }

  readUnsignedByte() {
    const v = this.buffer.readUInt8(this.offset);
    this.offset += 1;
    return v;
  }

  readByte() {
    const v = this.buffer.readInt8(this.offset);
    this.offset += 1;
    return v;
  }

  readDouble() {
    const v = this.buffer.readDoubleBE(this.offset);
    this.offset += 8;
    return v;
  }

  readFloat() {
    const v = this.buffer.readFloatBE(this.offset);
    this.offset += 4;
    if (v === 0) return v;
    // Shortest decimal that round-trips to the same float32.
    for (let precision = 1; precision <= 9; precision++) {
      const candidate = parseFloat(v.toPrecision(precision));
      if (Math.fround(candidate) === v) return candidate;
    }
    return v;
  }

  readInt() {
    const v = this.buffer.readInt32BE(this.offset);
    this.offset += 4;
    return v;
  }

  readLong() {
    const v = this.buffer.readBigInt64BE(this.offset);
    this.offset += 8;
    return v;
  }

  readShort() {
    const v = this.buffer.readInt16BE(this.offset);
    this.offset += 2;
    return v;
  }

  readUnsignedShort() {
    const v = this.buffer.readUInt16BE(this.offset);
    this.offset += 2;
    return v;
  }

  readSequenceLength() {
    let length = this.readUnsignedByte();
    if (length === _MAX_UNSIGNED_BYTE) length = this.readInt();
    return length;
  }

  readArrayNative(readerFn) {
    const ret = [];
    const length = this.readSequenceLength();
    for (let i = 0; i < length; i++) {
      ret.push(readerFn.call(this));
    }
    return ret;
  }

  readListBool() {
    const ret = [];
    let bin = 0;
    const length = this.readSequenceLength();
    for (let i = 0; i < length; i++) {
      if (i % 8 === 0) bin = this.readUnsignedByte();
      ret.push((bin & (1 << (i % 8))) !== 0);
    }
    return ret;
  }

  readString() {
    const length = this.readSequenceLength();
    const i = this.offset;
    this.offset += length;
    return this.buffer.toString('utf-8', i, this.offset);
  }
}

module.exports = {
  FieldTypeException,
  assertType,
  initFields,
  toSignedByte,
  toSignedShort,
  toUnsignedByte,
  toUnsignedShort,
  toQuotedString,
  createEnum,
  enumFromWire,
  defineTypedProperties,
  BluePacket,
  BluePacketRegistry,
  BluePacketWriter,
  BluePacketReader,
};
