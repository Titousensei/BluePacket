#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "    "
INNER_INDENT = DEFAULT_INDENT + "  "

CS_TYPE = { "byte": "sbyte" }

FORBIDDEN_NAMES = {
  "bool", "byte", "char", "class", "decimal", "double", "dynamic",
  "float", "int", "long", "nint", "nuint", "object", "sbyte", "short",
  "string", "uint", "ulong", "ushort"
}

CS_WRITER = {
  "bool":   "WriteBool",
  "byte":   "WriteSByte",
  "double": "WriteDouble",
  "float":  "WriteFloat",
  "int":    "WriteInt",
  "long":   "WriteLong",
  "short":  "WriteShort",
  "string": "WriteString",
}

CS_READER = {
  "bool":   "ReadBool",
  "byte":   "ReadSByte",
  "double": "ReadDouble",
  "float":  "ReadFloat",
  "int":    "ReadInt",
  "long":   "ReadLong",
  "short":  "ReadShort",
  "string": "ReadString",
}

def header(out, namespace, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    if not data.is_enum:
      println(out, "using System;")
      println(out, "using System.IO;")
      println(out, "using System.Text;")
      println(out)
      println(out, "using BluePackets;")
      println(out)
    println(out, f"namespace {namespace}")
    println(out, "{")
    println(out)


def produceFields(out, fields, indent):
  println(out)
  for fname, ftype, *opt in fields:
    if fname in FORBIDDEN_NAMES:
      raise Exception(f"Fields name can't be C# reserved keywords: {ftype} {fname}")
    if 'list' in opt:
      println(out, f"{indent}public {ftype}[] {fname};")
    elif fname:
      println(out, f"{indent}public {CS_TYPE.get(ftype, ftype)} {fname};")
    elif ftype.startswith('#'):
      println(out, indent + "//" + ftype[1:])
    else:
      println(out)


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  println(out, f"{indent}override public void SerializeData(Stream s)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f"{indent}  WriteArrayLength(s, {fname});")
      println(out, f"{indent}  if ({fname} != null) foreach (BluePacket p in {fname})")
      println(out, f"{indent}    p.SerializeData(s);")
    elif ftype in field_is_enum:
      println(out, f"{indent}  WriteEnum(s, {fname});")
    elif ftype in CS_WRITER:
      println(out, f"{indent}  {CS_WRITER[ftype]}(s, {fname});")
    else:
      println(out, f"{indent}  if ({fname} == null) s.WriteByte(0);")
      println(out, indent + "  {")
      println(out, f"{indent}    s.WriteByte(1);")
      println(out, f"{indent}    {fname}.SerializeData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceDeserializer(out, name, fields, indent, field_is_enum):
  println(out)
  println(out, f"{indent}override public void PopulateData(Stream s)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f"{indent}  {fname} = new {ftype}[ReadSequenceLength(s)];")
      println(out, f"{indent}  for (int i = 0; i < {fname}.Length; ++i)")
      println(out, indent + "  {")
      println(out, f"{indent}    {ftype} obj = new {ftype}();")
      println(out, f"{indent}    obj.PopulateData(s);")
      println(out, f"{indent}    {fname}[i] = obj;")
      println(out, indent + "  }")
    elif ftype in field_is_enum:
      println(out, f"{indent}  {fname} = ({ftype})ReadEnum(typeof({ftype}), s);")
    elif ftype in CS_READER:
      println(out, f"{indent}  {fname} = {CS_READER[ftype]}(s);")
    else:
      println(out, f"{indent}  if (ReadByte(s) > 0)")
      println(out, indent + "  {")
      println(out, f"{indent}    {fname} = new {ftype}();")
      println(out, f"{indent}    {fname}.PopulateData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceFieldsToString(out, name, fields, indent):
  println(out)
  println(out, indent + "override public void FieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", "{ftype}", {fname});')
    else:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", {fname});')

  println(out, indent + "}")


def exportInnerEnum(out, data):
  println(out)
  println(out, f"{DEFAULT_INDENT}public enum {data.name} : byte")
  println(out, DEFAULT_INDENT + "{")
  sep = INNER_INDENT
  for f in data.fields:
    out.write(sep)
    sep = ", "
    out.write(f)
  println(out)
  println(out, DEFAULT_INDENT + "}")


def exportInnerClass(out, data, field_is_enum):
  println(out)
  println(out, f"{DEFAULT_INDENT}public class {data.name} : BluePacket")
  println(out, DEFAULT_INDENT + "{")

  println(out, INNER_INDENT + "/*** DATA FIELDS ***/")
  produceFields(out, data.fields, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "/*** HELPER FUNCTIONS ***/")
  sorted_fields = list(sorted(data.fields))
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, namespace, data, version):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)

    println(out, f"  public sealed class {data.name} : BluePacket")
    println(out,  "  {")
    println(out, f"    override public long GetPacketHash() {{ return {version}; }}")
    println(out)

    println(out, DEFAULT_INDENT + "/*** DATA FIELDS ***/")
    produceFields(out, data.fields, DEFAULT_INDENT)
    sorted_fields = list(sorted(data.fields))
    println(out, DEFAULT_INDENT + "/*** HELPER FUNCTIONS ***/")
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT)

    if data.inner:
      println(out)
      println(out, DEFAULT_INDENT + "/*** INNER CLASSES ***/")
    for x in data.inner.values():
      exportInnerClass(out, x, data.field_is_enum)

    if data.enums:
      println(out)
      println(out, DEFAULT_INDENT + "/*** INNER ENUMS ***/")
    for x in data.enums.values():
      exportInnerEnum(out, x)

    println(out, "  }")
    println(out, "}")


def exportEnum(out_dir, namespace, data):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)

    println(out, f"  public enum {data.name} : byte")
    println(out,  "  {")
    sep =  "    "
    for f in data.fields:
      out.write(sep)
      sep = ", "
      out.write(f)
    println(out)

    println(out, "  }")
    println(out, "}")


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', help='Directory where the sources will be generated')
  parser.add_argument('--namespace', help='Namespace for the generated classes')
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
  for _, data in all_data.items():
    if data.is_enum:
      exportEnum(args.output_dir, args.namespace, data)
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, args.namespace, data, version)
