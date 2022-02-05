#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "  "
INNER_INDENT = DEFAULT_INDENT + "  "

FORBIDDEN_NAMES = {
  "boolean", "byte", "char", "class", "double", "static",
  "float", "int", "long", "short", "package", "import"
}

PYTHON_TYPE = {
  "bool": "bool",
  "string": "str",
}

PYTHON_WRITER = {
  "bool":   "writeBool",
  "byte":   "writeByte",
  "double": "writeDouble",
  "float":  "writeFloat",
  "int":    "writeInt",
  "long":   "writeLong",
  "short":  "writeShort",
  "string": "writeString",
}

PYTHON_READER = {
  "bool":   "readBoolean",
  "byte":   "readByte",
  "double": "readDouble",
  "float":  "readFloat",
  "int":    "readInt",
  "long":   "readLong",
  "short":  "readShort",
  "string": "readString",
}

def header(out, data):
    println(out, "# WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "import enum")
    println(out)
    if not data.is_enum:
      println(out, "from blue_packet import BluePacket as bp")
      not_import = { data.name }
      not_import.update(PYTHON_READER)
      not_import.update(data.inner)
      not_import.update(data.enums)
      needed_imports = {
        ftype
        for fname, ftype, *_ in data.fields
        if fname and ftype not in not_import
      }
      for ftype in needed_imports:
        println(out, f"from .{ftype} import {ftype}")
      println(out)


def produceTypeInfo(out, fields, indent):
  println(out, indent + "TYPE_INFO = {")
  for fname, ftype, *opt in fields:
    if not fname:
      continue
    println(out, f'{indent}  "{fname}": ("{ftype}", {"list" in opt}),')
  println(out, indent + "}")
      

def produceConstructor(out, fields, indent):
  println(out)
  println(out, indent + f"def __init__(")
  println(out, f"{indent}    self,")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if ftype.startswith('#'):
      println(out, indent + ftype)
      continue
    if fname in FORBIDDEN_NAMES:
      raise Exception(f"Fields name can't be Python reserved keywords: {ftype} {fname}")
    ft = f"list ftype" if 'list' in opt else ftype
    println(out, f"{indent}    {fname} = None,  # {ft}")
      
  println(out, indent + f"):")
  
  for fname, ftype, *opt in fields:
    if not fname:
      continue
    println(out, f"{indent}  self.{fname} = {fname}")


def produceSetAttr(out, name, indent):
  println(out)
  println(out, indent +  "def __setattr__(self, name, value):")
  println(out, indent + f"  bp.assertType(value, *{name}.TYPE_INFO[name])")
  println(out, indent +  "  self.__dict__[name] = value")
      

def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  println(out, indent + "def serializeData(self, bpw):")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f"{indent}  bpw.writeArray(self.{fname})")
    elif ftype in field_is_enum:
      println(out, f"{indent}  bpw.writeByte(0 if self.{fname} is None else self.{fname}.value)")
    elif ftype in PYTHON_WRITER:
      println(out, f"{indent}  bpw.{PYTHON_WRITER[ftype]}(self.{fname})")
    else:
      println(out, f"{indent}  if (self.{fname} is None):")
      println(out, f"{indent}    bpw.writeByte(0)")
      println(out, f"{indent}  else:")
      println(out, f"{indent}    bpw.writeByte(1)")
      println(out, f"{indent}    self.{fname}.serializeData(bpw)")


def produceDeserializer(out, data, fields, indent, field_is_enum):
  println(out)
  println(out, indent + "def populateData(self, bpr):")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if ftype in data.inner:
      ftype = "self." + ftype
    if 'list' in opt:
      println(out, f"{indent}  self.{fname} = []")
      println(out, f"{indent}  for _ in range(bpr.readUnsignedByte()):")
      println(out, f"{indent}    x = {ftype}()")
      println(out, f"{indent}    x.populateData(bpr)")
      println(out, f"{indent}    self.{fname}.append(x)")
    elif ftype in field_is_enum:
      if ftype in data.enums:
        ftype = "self." + ftype
      println(out, f"{indent}  self.{fname} = {ftype}(bpr.readByte())")
    elif ftype in PYTHON_READER:
      println(out, f"{indent}  self.{fname} = bpr.{PYTHON_READER[ftype]}()")
    else:
      println(out, f"{indent}  if bpr.readUnsignedByte() > 0:")
      println(out, f"{indent}    self.{fname} = {ftype}()")
      println(out, f"{indent}    self.{fname}.populateData(bpr)")


def produceFieldsToString(out, name, fields, indent, field_is_enum):
  println(out)
  println(out, indent + "def fieldsStr(self):")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f'{indent}    if self.{fname}:')
      println(out, f'{indent}      yield " {fname}={{{ftype} *" + str(len(self.{fname})) + "|"')
      println(out, f'{indent}      yield "|".join("".join(x.fieldsStr()) for x in self.{fname}) + "}}"')
    elif ftype in field_is_enum:
      println(out, f'{indent}    if self.{fname}.value: yield " {fname}=" + self.{fname}.name')
    elif ftype == 'bool':
      println(out, f'{indent}    if self.{fname}: yield " {fname}=true"')
    else:
      println(out, f'{indent}    if self.{fname}: yield " {fname}=" + str(self.{fname})')

  println(out)
  println(out, indent + "def __str__(self):")
  println(out, f'{indent}  return "{{{name}" + "".join(self.fieldsStr()) + "}}"')



def exportInnerEnum(out, data):
  println(out, f"  class {data.name}(enum.Enum):")
  for i, f in enumerate(data.fields):
    println(out, f"      {f} = {i}")
  println(out)


def exportInnerClass(out, data, field_is_enum, parentName):
  sorted_fields = list(sorted(data.fields))
  println(out)
  println(out, f"{DEFAULT_INDENT}class {data.name}:")
  produceTypeInfo(out, sorted_fields, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "### CONSTRUCTOR ###")
  produceConstructor(out, data.fields, INNER_INDENT)
  produceSetAttr(out, parentName + '.' + data.name, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "### HELPER FUNCTIONS ###")
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)


def exportClass(out_dir, data, version):
  path = os.path.join(out_dir, data.name + ".py")
  print("[ExporterPython] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, data)
    
    sorted_fields = list(sorted(data.fields))
    println(out, f"class {data.name}:")
    println(out, f"  packetHash = {version}")
    produceTypeInfo(out, data.fields, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "### CONSTRUCTOR ###")
    produceConstructor(out, sorted_fields, DEFAULT_INDENT)
    produceSetAttr(out, data.name, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "### HELPER FUNCTIONS ###")
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)

    if data.inner:
      println(out)
      println(out, DEFAULT_INDENT + "### INNER CLASSES ###")
    for x in data.inner.values():
      exportInnerClass(out, x, data.field_is_enum, data.name)

    if data.enums:
      println(out)
      println(out, DEFAULT_INDENT + "### INNER ENUMS ###")
    for x in data.enums.values():
      exportInnerEnum(out, x)


def exportEnum(out_dir, data):
  path = os.path.join(out_dir, data.name + ".py")
  print("[ExporterPython] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, data)

    println(out, f"class {data.name}(enum.Enum):")
    for i, f in enumerate(data.fields):
      println(out, f"  {f} = {i}")
    println(out)

def exportInit(out_dir, all_data):
  path = os.path.join(out_dir, "__init__.py")
  print("[ExporterPython] __init__", path, file=sys.stderr)
  with open(path, "w") as out:
    for _, data in all_data.items():
      println(out, f"from .{data.name} import {data.name}")


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
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, data, version)
