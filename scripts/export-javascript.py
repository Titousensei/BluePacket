#! /usr/bin/env python3
import argparse
import os
import sys

from libexport import Parser, SourceException, println, versionHash

OUTPUT_FILE = "gen.js"
INDENT = "    "
DEFAULT_RUNTIME = "./blue_packet.js"

JS_WRITER = {
  "byte":   "writeByte",
  "double": "writeDouble",
  "float":  "writeFloat",
  "int":    "writeInt",
  "long":   "writeLong",
  "short":  "writeShort",
  "string": "writeString",
  "ubyte":  "writeUnsignedByte",
  "ushort": "writeUnsignedShort",
}

JS_READER = {
  "byte":   "readByte",
  "double": "readDouble",
  "float":  "readFloat",
  "int":    "readInt",
  "long":   "readLong",
  "short":  "readShort",
  "string": "readString",
  "ubyte":  "readUnsignedByte",
  "ushort": "readUnsignedShort",
}


def produceDocstring(out, indent, docstring):
  if not docstring:
    return
  println(out, indent + "/**")
  for line in docstring:
    println(out, indent + " * " + line)
  println(out, indent + " */")


def produceComment(out, indent, lines):
  for line in lines or []:
    println(out, indent + "// " + line)


def sortedFields(fields):
  return sorted((pf for pf in fields if pf.name), key=lambda pf: pf.name)


def enumOf(ftype, owner, all_data):
  if ftype in owner.enums:
    return owner.enums[ftype]
  data = all_data.get(ftype)
  if data and data.is_enum:
    return data
  return None


def produceTypeInfo(out, data, owner, all_data, indent):
  println(out, indent + "static TYPE_INFO = {")
  for pf in sortedFields(data.fields):
    produceComment(out, indent + INDENT, pf.docstring)
    entry = f'["{pf.type}", {str(pf.is_list).lower()}'
    en = enumOf(pf.type, owner, all_data)
    if en and not pf.is_list:
      first = next((f.name for f in en.fields if f.name), None)
      if first is None:
        raise SourceException("Enum without values", what=en.name)
      entry += f", {pf.type}.{first}"
    println(out, f"{indent}{INDENT}{pf.name}: {entry}],")
  println(out, indent + "};")

def produceSetters(out, data, indent):
  """Generate fluent setXxx() methods for chaining, matching Java API."""
  fields = sortedFields(data.fields)
  if not fields:
    return
  println(out)
  for pf in fields:
    produceComment(out, indent, [f"Fluent setter for {pf.name}.", "@param val value", "@return this"])
    method_name = "set" + pf.name[0].upper() + pf.name[1:]
    if pf.is_list:
      println(out, indent + f"{method_name}(val) {{")
      println(out, indent + INDENT + f"this.{pf.name} = val;")
      println(out, indent + INDENT + "return this;")
      println(out, indent + "}")
    else:
      println(out, indent + f"{method_name}(val) {{")
      println(out, indent + INDENT + f"this.{pf.name} = val;")
      println(out, indent + INDENT + "return this;")
      println(out, indent + "}")


def produceSerializer(out, data, owner, indent):
  field_is_enum = owner.field_is_enum
  fields = sortedFields(data.fields)
  bools = [pf for pf in fields if not pf.is_list and pf.type == "bool"]

  println(out, indent + "serializeData(bpw) {")
  if bools:
    println(out, indent + INDENT + "let bin = 0;")
    for i, pf in enumerate(bools):
      if i and i % 8 == 0:
        println(out, indent + INDENT + "bpw.writeUnsignedByte(bin);")
        println(out, indent + INDENT + "bin = 0;")
      println(out, indent + INDENT + f"if (this.{pf.name}) bin |= {1 << (i % 8)};")
    println(out, indent + INDENT + "bpw.writeUnsignedByte(bin);")

  for pf in fields:
    if not pf.is_list and pf.type == "bool":
      continue
    produceFieldWrite(out, pf, field_is_enum, indent + INDENT)
  println(out, indent + "}")


def produceFieldWrite(out, pf, field_is_enum, indent):
  n = pf.name
  if pf.is_list:
    if pf.type == "bool":
      println(out, indent + f"bpw.writeListBool(this.{n});")
    elif pf.type in field_is_enum:
      fn = "writeArrayLargeEnum" if field_is_enum[pf.type] > 256 else "writeArrayEnum"
      println(out, indent + f"bpw.{fn}(this.{n});")
    elif pf.type in JS_WRITER:
      println(out, indent + f"bpw.writeArrayNative(this.{n}, bpw.{JS_WRITER[pf.type]});")
    elif pf.type == "packet":
      println(out, indent + f"bpw.writeArrayNative(this.{n}, bpw.writeBluePacket);")
    else:
      println(out, indent + f"bpw.writeArray(this.{n});")
  elif pf.type in field_is_enum:
    fn = "writeUnsignedShort" if field_is_enum[pf.type] > 256 else "writeUnsignedByte"
    println(out, indent + f"bpw.{fn}(this.{n} == null ? 0 : this.{n}.value);")
  elif pf.type == "packet":
    println(out, indent + f"bpw.writeBluePacket(this.{n});")
  elif pf.type in JS_WRITER:
    println(out, indent + f"bpw.{JS_WRITER[pf.type]}(this.{n});")
  else:
    println(out, indent + f"if (this.{n} == null) {{")
    println(out, indent + INDENT + "bpw.writeUnsignedByte(0);")
    println(out, indent + "} else {")
    println(out, indent + INDENT + "bpw.writeUnsignedByte(1);")
    println(out, indent + INDENT + f"this.{n}.serializeData(bpw);")
    println(out, indent + "}")


def produceDeserializer(out, data, owner, indent):
  field_is_enum = owner.field_is_enum
  fields = sortedFields(data.fields)
  bools = [pf for pf in fields if not pf.is_list and pf.type == "bool"]

  println(out, indent + "populateData(registry, bpr) {")
  if bools:
    println(out, indent + INDENT + "let bin = bpr.readUnsignedByte();")
    for i, pf in enumerate(bools):
      if i and i % 8 == 0:
        println(out, indent + INDENT + "bin = bpr.readUnsignedByte();")
      println(out, indent + INDENT + f"this.{pf.name} = (bin & {1 << (i % 8)}) !== 0;")

  for pf in fields:
    if not pf.is_list and pf.type == "bool":
      continue
    produceFieldRead(out, pf, field_is_enum, indent + INDENT)
  println(out, indent + "}")


def produceFieldRead(out, pf, field_is_enum, indent):
  n = pf.name
  if pf.is_list:
    if pf.type == "bool":
      println(out, indent + f"this.{n} = bpr.readListBool();")
    elif pf.type in field_is_enum:
      fn = "readUnsignedShort" if field_is_enum[pf.type] > 256 else "readUnsignedByte"
      println(out, indent + f"this.{n} = bpr.readArrayNative(() => enumFromWire({pf.type}, bpr.{fn}()));")
    elif pf.type in JS_READER:
      println(out, indent + f"this.{n} = bpr.readArrayNative(bpr.{JS_READER[pf.type]});")
    elif pf.type == "packet":
      println(out, indent + f"this.{n} = bpr.readArrayNative(() => registry._deserializeInternal(bpr));")
    else:
      println(out, indent + f"this.{n} = [];")
      println(out, indent + f"for (let i = 0, n = bpr.readSequenceLength(); i < n; i++) {{")
      println(out, indent + INDENT + f"const x = new {pf.type}();")
      println(out, indent + INDENT + "x.populateData(registry, bpr);")
      println(out, indent + INDENT + f"this.{n}.push(x);")
      println(out, indent + "}")
  elif pf.type in field_is_enum:
    fn = "readUnsignedShort" if field_is_enum[pf.type] > 256 else "readUnsignedByte"
    println(out, indent + f"this.{n} = enumFromWire({pf.type}, bpr.{fn}());")
  elif pf.type == "packet":
    println(out, indent + f"this.{n} = registry._deserializeInternal(bpr);")
  elif pf.type in JS_READER:
    println(out, indent + f"this.{n} = bpr.{JS_READER[pf.type]}();")
  else:
    println(out, indent + "if (bpr.readUnsignedByte() > 0) {")
    println(out, indent + INDENT + f"this.{n} = new {pf.type}();")
    println(out, indent + INDENT + f"this.{n}.populateData(registry, bpr);")
    println(out, indent + "}")


def produceConvertAll(out, data, indent):
  targets = ", ".join(f"new {ctype}()" for ctype in data.converts)
  println(out, indent + "convert() {")
  println(out, indent + INDENT + f"return [{targets}];")
  println(out, indent + "}")


def produceConvert(out, data, ctype, all_data, indent):
  other = all_data.get(ctype)
  if not other:
    raise SourceException("Converter from unknown type", what=ctype)
  options = ", ".join(f"{pf.name}: other.{pf.name}" for pf in sortedFields(other.fields))
  println(out, indent + f"static convert{ctype}(other) {{")
  println(out, indent + INDENT + f"assertType(other, {ctype}, false);")
  println(out, indent + INDENT + f"return new {data.name}({{{options}}});")
  println(out, indent + "}")


def produceClass(out, data, owner, all_data, version):
  produceDocstring(out, "", data.docstring)
  println(out, f"class {data.name} extends BluePacket")
  println(out, "{")
  if version is not None:
    println(out, INDENT + f"static packetHash = {version}n;")
    println(out, INDENT + f'static packetHex = "0x{version & 0xFFFFFFFFFFFFFFFF:0X}";')
    println(out)

  aliases = list(data.inner) + list(data.enums)
  if aliases:
    for name in aliases:
      println(out, INDENT + f"static {name} = {name};")
    println(out)

  produceTypeInfo(out, data, owner, all_data, INDENT)
  println(out)
  println(out, INDENT + "constructor(options = {}) {")
  println(out, INDENT + INDENT + "super();")
  println(out, INDENT + INDENT + f"initFields(this, {data.name}, arguments);")
  println(out, INDENT + "}")
  println(out)
  produceSerializer(out, data, owner, INDENT)
  println(out)
  produceDeserializer(out, data, owner, INDENT)
  produceSetters(out, data, INDENT)

  if data.converts:
    println(out)
    produceConvertAll(out, data, INDENT)
    for ctype in data.converts:
      println(out)
      produceConvert(out, data, ctype, all_data, INDENT)
  println(out, "}")


def produceEnum(out, data):
  produceDocstring(out, "", data.docstring)
  println(out, f"const {data.name} = createEnum(")
  println(out, INDENT + f"'{data.name}',")
  for pf in data.fields:
    if pf.name:
      produceComment(out, INDENT, pf.docstring)
      println(out, INDENT + f"'{pf.name}',")
    else:
      produceComment(out, INDENT, pf.docstring)
  println(out, ");")


def produceAbstract(out, data):
  produceDocstring(out, "", data.docstring)
  println(out, f"class {data.name} {{")
  println(out, INDENT + "static [Symbol.hasInstance](instance) {")
  println(out, INDENT + INDENT + f"return {data.name}._IMPLEMENTORS.some((cls) => instance instanceof cls);")
  println(out, INDENT + "}")
  println(out, "}")


def exportBundle(out_dir, runtime, all_data, api_version, browser_mode):
  os.makedirs(out_dir, exist_ok=True)
  path = os.path.join(out_dir, OUTPUT_FILE)
  print("[ExporterJavaScript] BluePacket bundle", path, file=sys.stderr)

  enums = [data for data in all_data.values() if data.is_enum]
  packets = [data for data in all_data.values() if not data.is_enum and not data.is_abstract]
  abstracts = [data for data in all_data.values() if data.is_abstract]

  declared = {}
  def declare(name, what):
    if name in declared:
      raise SourceException("Duplicate JS identifier in bundle", what=f"{name} ({declared[name]} and {what})")
    declared[name] = what

  for data in enums:
    declare(data.name, "enum")
  for data in packets:
    for inner in data.inner.values():
      declare(inner.name, f"inner class of {data.name}")
    for enum in data.enums.values():
      declare(enum.name, f"inner enum of {data.name}")
  for data in packets:
    declare(data.name, "packet")
  for data in abstracts:
    declare(data.name, "abstract")

  with open(path, "w") as out:
    println(out, "// WARNING: Auto-generated bundle - do not edit - any change will be overwritten and lost")
    println(out, "// Packets are open for method extension (subclass/prototype), but their field set is fixed.")
    println(out, "// Do not add fields or override serializeData/populateData.")
    println(out, '"use strict";')
    println(out)

    if browser_mode:
      println(out, "// Browser-compatible bundle (IIFE)")
      println(out, "(function() {")
      println(out)
      println(out, "  // Resolve runtime from globals (set by blue_packet.js) or fall back to require")
      println(out, "  let bp;")
      println(out, "  if (typeof window !== 'undefined' && window.BluePacketLib) {")
      println(out, "    bp = window.BluePacketLib;")
      println(out, "  } else if (typeof globalThis !== 'undefined' && globalThis.BluePacketLib) {")
      println(out, "    bp = globalThis.BluePacketLib;")
      println(out, "  } else if (typeof require !== 'undefined') {")
      println(out, f"    bp = require('{runtime}');")
      println(out, "  } else {")
      println(out, "    throw new Error('BluePacket runtime not found. Include blue_packet.js first or ensure require() is available.');")
      println(out, "  }")
    else:
      println(out, f"const bp = require('{runtime}');")

    for name in ("BluePacket", "BluePacketRegistry", "assertType", "createEnum", "enumFromWire",
                 "initFields", "toSignedByte", "toSignedShort", "toUnsignedByte", "toUnsignedShort"):
      if browser_mode:
        println(out, f"  const {name} = bp.{name};")
      else:
        println(out, f"const {name} = bp.{name};")

    if enums:
      println(out)
      println(out, "// --- enums ---")
      for data in enums:
        println(out)
        produceEnum(out, data)

    for data in packets:
      for en in data.enums.values():
        println(out)
        produceEnum(out, en)

    for data in packets:
      for inner in data.inner.values():
        println(out)
        println(out, f"// --- {inner.name} (inner class of {data.name}) ---")
        println(out)
        produceClass(out, inner, data, all_data, None)
      println(out)
      println(out, f"// --- {data.name} ---")
      println(out)
      produceClass(out, data, data, all_data, versionHash(data, all_data))

    if abstracts:
      println(out)
      println(out, "// --- abstract markers ---")
      for data in abstracts:
        println(out)
        produceAbstract(out, data)

    println(out)
    for data in abstracts:
      impls = ", ".join(p.name for p in packets if data.name in p.abstracts)
      println(out, f"{data.name}._IMPLEMENTORS = [{impls}];")
    println(out)
    println(out, "// --- registry ---")
    println(out)
    println(out, "const registry = new BluePacketRegistry();")
    for data in packets:
      println(out, f"registry.register({data.name});")

    println(out)
    println(out, "// --- BluePacketAPI ---")
    println(out)
    println(out, "class BluePacketAPI {")
    println(out, INDENT + f"static VERSION = {api_version}n;")
    println(out, INDENT + f"static VERSION_HEX = '0x{api_version & 0xFFFFFFFFFFFFFFFF:0X}';")
    println(out, "}")
    println(out, "Object.freeze(BluePacketAPI);")

    println(out)
    println(out, "// --- exports ---")
    println(out)
    if browser_mode:
      println(out, "  const exports = {")
    else:
      println(out, "module.exports = {")
    for data in all_data.values():
      println(out, INDENT + f"{data.name},")
    for name in ("BluePacketRegistry", "registry", "BluePacketAPI",
                 "toSignedByte", "toSignedShort", "toUnsignedByte", "toUnsignedShort"):
      println(out, INDENT + f"{name},")
    if browser_mode:
      println(out, "  };")
      println(out)
      println(out, "  // Global exposure for browser")
      println(out, "  if (typeof window !== 'undefined') {")
      println(out, "    window.BluePacketGen = exports;")
      println(out, "  }")
      println(out, "  if (typeof globalThis !== 'undefined') {")
      println(out, "    globalThis.BluePacketGen = exports;")
      println(out, "  }")
      println(out)
      println(out, "  // Node.js CommonJS export")
      println(out, "  if (typeof module !== 'undefined' && module.exports) {")
      println(out, "    module.exports = exports;")
      println(out, "  }")
      println(out, "})();")
    else:
      println(out, "};")

def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', required=True, help='Directory where the bundle will be generated')
  parser.add_argument('--runtime', default=DEFAULT_RUNTIME,
                      help=f'Module path used to require the BluePacket runtime (default: {DEFAULT_RUNTIME})')
  parser.add_argument('--browser', action='store_true', help='Generate browser-compatible bundle (IIFE with global exposure)')
  parser.add_argument('--debug', action='store_true', help='Print parser debug info')
  parser.add_argument('packets', nargs='+', help='List of .bp files to process')
  return parser.parse_args()


if __name__ == "__main__":
  args = get_args()
  p = Parser()
  all_data = p.parse(args.packets, manifest_path=args.output_dir)
  if args.debug:
    for cl, lf in all_data.items():
      print(cl, lf)
  exportBundle(args.output_dir, args.runtime, all_data, p.api_version, args.browser)