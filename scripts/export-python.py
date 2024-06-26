#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "  "
INNER_INDENT = DEFAULT_INDENT + "  "

PYTHON_TYPE = {
  "bool": "bool",
  "string": "str",
}

PYTHON_WRITER = {
  "byte":   "writeByte",
  "double": "writeDouble",
  "float":  "writeFloat",
  "int":    "writeInt",
  "long":   "writeLong",
  "packet": "writeBluePacket",
  "short":  "writeShort",
  "string": "writeString",
  "ubyte":  "writeUnsignedByte",
  "ushort": "writeUnsignedShort",
}

PYTHON_READER = {
  "byte":   "bpr.readByte()",
  "double": "bpr.readDouble()",
  "float":  "bpr.readFloat()",
  "int":    "bpr.readInt()",
  "long":   "bpr.readLong()",
  "packet": "registry.deserialize_internal(bpr)",
  "short":  "bpr.readShort()",
  "string": "bpr.readString()",
  "ubyte":  "bpr.readUnsignedByte()",
  "ushort": "bpr.readUnsignedShort()",
}


def header(out, data):
    println(out, "# WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "import enum")
    println(out)
    if not data.is_enum:
      println(out, "from blue_packet import BluePacket, assertType, toQuotedString")
      not_import = { data.name, 'bool' }
      not_import.update(PYTHON_READER)
      not_import.update(data.inner)
      not_import.update(data.enums)
      needed_imports = {
        pf.type
        for pf in data.fields
        if pf.name and pf.type not in not_import
      }
      for ftype in needed_imports:
        println(out, f"from .{ftype} import {ftype}")
      for ftype in data.abstracts:
        println(out, f"from .{ftype} import {ftype}")
      for ftype in data.converts:
        println(out, f"from .{ftype} import {ftype}")
      println(out)


def produceDocstring(out, indent, docstring):
  if docstring:
    first = docstring[0]
    if first[-1] != '.':
      first += '.'
    if len(docstring) == 1:
      println(out, f'{indent}"""{first}"""')
    else:
      println(out, f'{indent}"""{first}')
      if len(docstring) > 1:
        println(out)
        for line in docstring[1:]:
          println(out, f"{indent}{line}")
      println(out, f'{indent}"""')
    println(out)


def produceTypeInfo(out, fields, indent):
  println(out, indent + "TYPE_INFO = {")
  println(out, indent + "  # name: (type, is_list)")
  for pf in fields:
    if not pf.name:
      continue
    println(out, f'{indent}  "{pf.name}": ("{pf.type}", {pf.is_list}),')
  println(out, indent + "}")


def produceConstructor(out, data, field_is_enum, parent_name, indent):
  println(out)
  println(out, indent + f"def __init__(")
  println(out, f"{indent}    self, *,")

  for pf in data.fields:
    if pf.name:
      fopt = "[]" if pf.is_list else ""
      println(out, f"{indent}    {pf.name} = None,  # {pf.type}{fopt}")

  println(out, indent + f"):")

  for pf in data.fields:
    if pf.docstring:
      println(out)
    for line in pf.docstring:
      println(out, f"{indent}  # {line}")
    if pf.type in data.enums:
      println(out, f"{indent}  self.{pf.name} = {pf.name} or self.{pf.type}(0)")
    elif pf.type in field_is_enum and not pf.is_list:
      if parent_name:
        println(out, f"{indent}  self.{pf.name} = {pf.name} or {parent_name}.{pf.type}(0)")
      else:
        println(out, f"{indent}  self.{pf.name} = {pf.name} or {pf.type}(0)")
    elif pf.name:
      println(out, f"{indent}  self.{pf.name} = {pf.name}")
    else:
      println(out)


def produceSetAttr(out, name, indent):
  println(out)
  println(out, indent +  "def __setattr__(self, name, value):")
  println(out, indent + f"  assertType(value, *{name}.TYPE_INFO[name])")
  println(out, indent +  "  self.__dict__[name] = value")


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  println(out, indent + "def serializeData(self, bpw):")

  if not any(pf.name for pf in fields):
    println(out, f"{indent}    pass")
    return

  bool_counter = 0
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  # boolean fields are packed into bytes")
      println(out, f"{indent}  bin = 0")
    elif  bool_counter % 8 == 0:
      println(out, f"{indent}  bpw.writeUnsignedByte(bin)")
      println(out, f"{indent}  bin = 0")

    println(out, f"{indent}  if self.{pf.name}: bin |= {1<<(bool_counter%8)}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"{indent}  bpw.writeUnsignedByte(bin)")

  println(out, f"{indent}  # Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool' or not pf.name):
      continue
    if pf.is_list:
      if pf.type == 'bool':
        println(out, f"{indent}  bpw.writeListBool(self.{pf.name})")
      elif pf.type in PYTHON_WRITER:
        println(out, f"{indent}  bpw.writeArrayNative(self.{pf.name}, bpw.{PYTHON_WRITER[pf.type]})")
      elif pf.type in field_is_enum:
        if field_is_enum.get(pf.type, 0) > 256:
          println(out, f"{indent}  bpw.writeArrayLargeEnum(self.{pf.name})")
        else:
          println(out, f"{indent}  bpw.writeArrayEnum(self.{pf.name})")
      else:
        println(out, f"{indent}  bpw.writeArray(self.{pf.name})")
    elif pf.type in field_is_enum:
      if field_is_enum.get(pf.type, 0) <= 256:
        println(out, f"{indent}  bpw.writeUnsignedByte(0 if self.{pf.name} is None else self.{pf.name}.value)")
      else:
        println(out, f"{indent}  bpw.writeUnsignedShort(0 if self.{pf.name} is None else self.{pf.name}.value)")
    elif pf.type in PYTHON_WRITER:
      println(out, f"{indent}  bpw.{PYTHON_WRITER[pf.type]}(self.{pf.name})")
    else:
      println(out, f"{indent}  if (self.{pf.name} is None):")
      println(out, f"{indent}    bpw.writeByte(0)")
      println(out, f"{indent}  else:")
      println(out, f"{indent}    bpw.writeByte(1)")
      println(out, f"{indent}    self.{pf.name}.serializeData(bpw)")


def produceDeserializer(out, data, fields, indent, field_is_enum, parent_name):
  println(out)
  println(out, indent + "def populateData(self, registry, bpr):")

  if not any(pf.name for pf in fields):
    println(out, f"{indent}    pass")
    return

  bool_counter = 0
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  # boolean fields are packed into bytes")
    if  bool_counter % 8 == 0:
      println(out, f"{indent}  bin = bpr.readByte()")

    println(out, f"{indent}  self.{pf.name} = (bin & {1<<(bool_counter%8)}) != 0")
    bool_counter += 1

  println(out, f"{indent}  # Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool') or not pf.name:
      continue
    ftype = "self." + pf.type if pf.type in data.inner or pf.type in data.enums else pf.type
    if pf.is_list:
      if pf.type == 'bool':
        println(out, f"{indent}  self.{pf.name} = bpr.readListBool();")
        continue
      println(out, f"{indent}  self.{pf.name} = []")
      println(out, f"{indent}  for _ in range(bpr.readUnsignedByte()):")
      if pf.type in PYTHON_READER:
        println(out, f"{indent}    x = {PYTHON_READER[pf.type]}")
      elif pf.type in field_is_enum:
        if field_is_enum.get(pf.type, 0) <= 256:
          println(out, f"{indent}    x = {ftype}(bpr.readUnsignedByte())")
        else:
          println(out, f"{indent}    x = {ftype}(bpr.readUnsignedShort())")
      else:
        println(out, f"{indent}    x = {ftype}()")
        println(out, f"{indent}    x.populateData(registry, bpr)")
      println(out, f"{indent}    self.{pf.name}.append(x)")
    elif pf.type in field_is_enum:
      if parent_name:
        prefix = parent_name + "."
      elif ftype in data.enums:
        prefix = "self."
      else:
        prefix = ""
      read_size = "readUnsignedByte" if field_is_enum.get(pf.type, 0) <= 256 else "readUnsignedShort"
      println(out, f"{indent}  self.{pf.name} = {prefix}{ftype}(bpr.{read_size}())")
    elif ftype in PYTHON_READER:
      println(out, f"{indent}  self.{pf.name} = {PYTHON_READER[pf.type]}")
    else:
      println(out, f"{indent}  if bpr.readUnsignedByte() > 0:")
      println(out, f"{indent}    self.{pf.name} = {ftype}()")
      println(out, f"{indent}    self.{pf.name}.populateData(registry, bpr)")


def produceFieldsToString(out, name, fields, indent, field_is_enum, is_inner=False):
  println(out)
  println(out, indent + "def fieldsStr(self):")

  if not any(pf.name for pf in fields):
    println(out, f"{indent}    pass")

  for pf in fields:
    if not pf.name:
      continue
    if pf.is_list:
      println(out, f'{indent}    if self.{pf.name}:')
      println(out, f'{indent}      yield " {pf.name}={{{pf.type} *" + str(len(self.{pf.name})) + "|"')
      if pf.type == 'bool':
        println(out, f'{indent}      yield "|".join("1" if x else "0" for x in self.{pf.name}) + "}}"')
      elif pf.type == 'string':
        println(out, f'{indent}      yield "|".join(toQuotedString(x) for x in self.{pf.name}) + "}}"')
      elif pf.type in PYTHON_WRITER:
        println(out, f'{indent}      yield "|".join(str(x) for x in self.{pf.name}) + "}}"')
      elif pf.type in field_is_enum:
        println(out, f'{indent}      yield "|".join(x.name for x in self.{pf.name}) + "}}"')
      else:
        println(out, f'{indent}      yield "|".join("".join(x.fieldsStr()) for x in self.{pf.name}) + "}}"')
    elif pf.type in field_is_enum:
      println(out, f'{indent}    if self.{pf.name}.value: yield " {pf.name}=" + self.{pf.name}.name')
    elif pf.type == 'bool':
      println(out, f'{indent}    if self.{pf.name}: yield " {pf.name}=1"')
    elif pf.type == 'string':
      println(out, f'{indent}    if self.{pf.name}: yield " {pf.name}=" + toQuotedString(self.{pf.name})')
    else:
      println(out, f'{indent}    if self.{pf.name}: yield " {pf.name}=" + str(self.{pf.name})')

  println(out)
  println(out, indent + "def __str__(self):")
  if is_inner:
    println(out, f'{indent}    return "{{{name}" + "".join(self.fieldsStr()) + "}}"')
  elif any(pf.name for pf in fields):
    println(out, f'{indent}    return "{{{name} " + self.packetHex + "".join(self.fieldsStr()) + "}}"')
  else:
    println(out, f'{indent}    return "{{{name} " + self.packetHex + "}}"')

def produceConvertAll(out, name, converts, indent):
  if not converts:
    return
  println(out)
  produceDocstring(out, indent,
    [
      "Get all the convertible BluePackets",
      "Returns:",
      "    List of BluePacket instances",
    ]
  )
  println(out, indent + "@staticmethod")
  println(out, f"{indent}def convert():")
  println(out, indent + "  return [")
  println(out, f"{indent}    " + ", ".join(c + "()" for c in converts))
  println(out, indent + "  ]")


def produceConvert(out, name, ctype, copts, other_fields, indent):
  println(out)
  println(out, indent + "@staticmethod")
  println(out, f"{indent}def convert{ctype}(other):")
  produceDocstring(out, indent + "  ",
    [
      f"Converter method to build a {name} from an instance of {ctype}",
      f"Args:",
      f"    other: populated instance of {ctype}",
      f"Returns:",
      f"    new instance of {name} populated with data from other"
    ]
  )
  println(out, f"{indent}  assertType(other, {ctype}, False)")
  println(out, f"{indent}  return {name}(")

  for pf in other_fields:
    if pf.name:
      println(out, f"{indent}      {pf.name}=other.{pf.name},")

  println(out, indent + f"  )")


def exportInnerEnum(out, data, indent0):
  println(out, f"{indent0}class {data.name}(enum.Enum):")
  indent = indent0 + "    "
  produceDocstring(out, indent, data.docstring)
  i = 0
  for pf in data.fields:
    if pf.docstring:
      println(out)
      for line in pf.docstring:
        println(out, f"{indent}# {line}")
    if pf.name:
      println(out, f"{indent}{pf.name} = {i}")
      i += 1
    elif pf.docstring:
      println(out)


def exportInnerClass(out, data, field_is_enum, parentName):
  sorted_fields = list(sorted(data.fields, key=str))
  println(out)
  println(out, f"{DEFAULT_INDENT}class {data.name}(BluePacket):")
  produceDocstring(out, INNER_INDENT, data.docstring)
  produceTypeInfo(out, sorted_fields, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "### CONSTRUCTOR ###")
  produceConstructor(out, data, field_is_enum, parentName, INNER_INDENT)
  produceSetAttr(out, parentName + '.' + data.name, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "### HELPER FUNCTIONS ###")
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data, sorted_fields, INNER_INDENT, field_is_enum, parentName)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT, field_is_enum, is_inner=True)


def exportClass(out_dir, data, version, all_data):
  path = os.path.join(out_dir, data.name + ".py")
  print("[ExporterPython] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, data)

    sorted_fields = list(sorted(data.fields, key=str))
    if data.abstracts:
      abstracts_str = ", " + ", ".join(data.abstracts)
    else:
      abstracts_str = ""
    println(out, f"class {data.name}(BluePacket{abstracts_str}):")
    produceDocstring(out, "  ", data.docstring)
    println(out, f"  packetHash = {version}")
    println(out, f'  packetHex = "0x{version & 0xFFFFFFFFFFFFFFFF:0X}"')
    produceTypeInfo(out, data.fields, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "### CONSTRUCTOR ###")
    if any(pf.name for pf in data.fields):
      produceConstructor(out, data, data.field_is_enum, None, DEFAULT_INDENT)
      produceSetAttr(out, data.name, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "### HELPER FUNCTIONS ###")
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data, sorted_fields, DEFAULT_INDENT, data.field_is_enum, None)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceConvertAll(out, data.name, data.converts, DEFAULT_INDENT)
    for ctype, copts in data.converts.items():
      other = all_data.get(ctype)
      if not other:
        raise SourceException("Converter from unknown type", what=ctype)
      cfields = list(sorted(other.fields, key=str))
      produceConvert(out, data.name, ctype, copts, cfields, DEFAULT_INDENT)

    if data.inner:
      println(out)
      println(out, DEFAULT_INDENT + "### INNER CLASSES ###")
    for x in data.inner.values():
      exportInnerClass(out, x, data.field_is_enum, data.name)

    if data.enums:
      println(out)
      println(out, DEFAULT_INDENT + "### INNER ENUMS ###")
    for x in data.enums.values():
      exportInnerEnum(out, x, DEFAULT_INDENT)


def exportEnum(out_dir, data):
  path = os.path.join(out_dir, data.name + ".py")
  print("[ExporterPython] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, data)
    exportInnerEnum(out, data, "")


def exportAbstract(out_dir, data):
  path = os.path.join(out_dir, data.name + ".py")
  print("[ExporterPython] BluePacket abstract", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, data)
    println(out, f"class {data.name}():")
    produceDocstring(out, "    ", data.docstring)
    println(out, f"    pass")


def exportApiVersion(out_dir, api_version):
  path = os.path.join(out_dir, "blue_packet_api.py")
  print("[ExporterPython] API Version", path, file=sys.stderr)
  with open(path, "w") as out:
    println(out, "# WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out)
    produceDocstring(out, "", ["API information for this package."])
    println(out, "class BluePacketAPI:")
    produceDocstring(out, "  ", ["API Version calculated for all the packets in this package."])
    println(out, f"  VERSION = {api_version}")
    println(out, f'  VERSION_HEX = "0x{api_version & 0xFFFFFFFFFFFFFFFF:0X}"')


def exportInit(out_dir, all_data):
  path = os.path.join(out_dir, "__init__.py")
  print("[ExporterPython] __init__", path, file=sys.stderr)
  with open(path, "w") as out:
    for _, data in all_data.items():
      println(out, f"from .{data.name} import {data.name}")
    println(out, f"from .blue_packet_api import BluePacketAPI")


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', help='Directory where the sources will be generated')
  parser.add_argument('--debug', action='store_true', help='Print parser debug info')
  parser.add_argument('packets', nargs='+', help='List of .bp files to process')
  return parser.parse_args()


if __name__ == "__main__":
  args = get_args()
  p = Parser()
  all_data = p.parse(args.packets)
  if args.debug:
    for cl, lf in all_data.items():
      print(cl, lf)

  exportInit(args.output_dir, all_data)
  for _, data in all_data.items():
    if data.is_enum:
      exportEnum(args.output_dir, data)
    elif data.is_abstract:
      exportAbstract(args.output_dir, data)
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, data, version, all_data)
  exportApiVersion(args.output_dir, p.api_version)
