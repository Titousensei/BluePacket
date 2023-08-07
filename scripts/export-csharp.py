#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "    "
INNER_INDENT = DEFAULT_INDENT + "  "

CS_TYPE = {
  "byte": "sbyte",
  "ubyte": "byte",
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
  "ubyte":  "WriteByte",
  "ushort": "WriteUShort",
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
  "ubyte":  "ReadByte",
  "ushort": "ReadUShort",
}

def header(out, namespace, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    if not data.is_enum:
      println(out, "using System;")
      println(out, "using System.IO;")
      println(out, "using System.Text;")
      println(out, "using BluePackets;")
      println(out)
    println(out, f"namespace {namespace}")
    println(out, "{")


def produceDocstring(out, indent, summary, docstring=None):
  if summary:
    println(out, f"{indent}/// <summary>")
    println(out, f"{indent}/// {summary[0]}")
    for line in summary[1:]:
      println(out, f"{indent}/// <para>{line}</para>")
    println(out, f"{indent}/// </summary>")
  for line in docstring or []:
    println(out, f"{indent}/// {line}")


def produceFields(out, fields, indent):
  for fname, ftype, opt, docstring in fields:
    if 'list' in opt:
      produceDocstring(out, indent, docstring)
      println(out, f"{indent}public {CS_TYPE.get(ftype, ftype)}[] {fname};")
    elif fname:
      produceDocstring(out, indent, docstring)
      println(out, f"{indent}public {CS_TYPE.get(ftype, ftype)} {fname};")
    elif docstring:
      println(out)
      for line in docstring:
        println(out, indent + "// " + line)
      println(out)
    else:
      println(out)


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to serialize to bytes"], ['<param name="s">stream to write the bytes to</param>'])
  println(out, f"{indent}override public void SerializeData(Stream s)")
  println(out, indent + "{")

  bool_counter = 0
  for fname, ftype, *opt in fields:
    if ftype != 'bool' or 'list' in opt:
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  byte bin = 0;")
    elif  bool_counter % 8 == 0:
      println(out, f"{indent}  s.WriteByte(bin);")
      println(out, f"{indent}  bin = 0;")

    println(out, f"{indent}  if (this.{fname}) {{ bin |= {1<<(bool_counter%8)}; }} else {{ bin &= {255 & ~(1<<(bool_counter%8))}; }}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"{indent}  s.WriteByte(bin);")

  println(out, f"{indent}  // Non-boolean fields")
  for fname, ftype, *opt in fields:
    if not fname or (ftype == 'bool' and 'list' not in opt):
      continue
    if 'list' in opt:
      println(out, f"{indent}  if (this.{fname} == null) s.WriteByte(0); else {{")
      println(out, f"{indent}    WriteSequenceLength(s, this.{fname}.Length);")
      if ftype in CS_WRITER:
        println(out, f"{indent}    for (int i = 0; i < this.{fname}.Length; ++i)")
        println(out, f"{indent}      {CS_WRITER[ftype]}(s, this.{fname}[i]);")
      elif ftype in field_is_enum:
        println(out, f"{indent}    foreach ({ftype} p in this.{fname})")
        println(out, f"{indent}      WriteEnum(s, p);")
      else:
        println(out, f"{indent}    foreach (BluePacket p in this.{fname})")
        println(out, f"{indent}      p.SerializeData(s);")
      println(out, indent + "  }")
    elif ftype in field_is_enum:
      println(out, f"{indent}  WriteEnum(s, this.{fname});")
    elif ftype in CS_WRITER:
      println(out, f"{indent}  {CS_WRITER[ftype]}(s, this.{fname});")
    else:
      println(out, f"{indent}  if (this.{fname} == null) s.WriteByte(0);")
      println(out, indent + "  else {")
      println(out, f"{indent}    s.WriteByte(1);")
      println(out, f"{indent}    this.{fname}.SerializeData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceDeserializer(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to deserialize from bytes into this object fields"], ['<param name="s">stream to read the bytes from</param>'])
  println(out, f"{indent}override public void PopulateData(Stream s)")
  println(out, indent + "{")

  bool_counter = 0
  for fname, ftype, *opt in fields:
    if ftype != 'bool' or 'list' in opt:
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  int bin;")
    if  bool_counter % 8 == 0:
      println(out, f"{indent}  bin = s.ReadByte();")

    println(out, f"{indent}  this.{fname} = (bin & {1<<(bool_counter%8)}) != 0;")
    bool_counter += 1

  println(out, f"{indent}  // Non-boolean fields")
  for fname, ftype, *opt in fields:
    if not fname or (ftype == 'bool' and 'list' not in opt):
      continue
    if 'list' in opt:
      println(out, f"{indent}  {fname} = new {CS_TYPE.get(ftype, ftype)}[ReadSequenceLength(s)];")
      println(out, f"{indent}  for (int i = 0; i < {fname}.Length; ++i) {{")
      if ftype in CS_READER:
        println(out, f"{indent}    {fname}[i] = {CS_READER[ftype]}(s);")
      elif ftype in field_is_enum:
        println(out, f"{indent}    {fname}[i] = ({ftype})ReadEnum(typeof({ftype}), s);")
      else:
        println(out, f"{indent}    {ftype} obj = new {ftype}();")
        println(out, f"{indent}    obj.PopulateData(s);")
        println(out, f"{indent}    {fname}[i] = obj;")
      println(out, indent + "  }")
    elif ftype in field_is_enum:
      println(out, f"{indent}  {fname} = ({ftype})ReadEnum(typeof({ftype}), s);")
    elif ftype in CS_READER:
      println(out, f"{indent}  {fname} = {CS_READER[ftype]}(s);")
    else:
      println(out, f"{indent}  if (ReadByte(s) > 0) {{")
      println(out, f"{indent}    {fname} = new {ftype}();")
      println(out, f"{indent}    {fname}.PopulateData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceFieldsToString(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal helper method for ToString()"], ['<param name="sb">builder to write the fields and their values</param>'])
  println(out, indent + "override public void FieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      if ftype in CS_READER:
        println(out, f'{indent}  AppendIfNotEmptyArray<{CS_TYPE.get(ftype, ftype)}>(sb, "{fname}", "{ftype}", {fname});')
      elif ftype in field_is_enum:
        println(out, f'{indent}  AppendIfNotEmptyArray<String>(sb, "{fname}", "{ftype}", Array.ConvertAll({fname}, value => value.ToString()));')
      else:
        println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", "{ftype}", {fname});')
    elif ftype in CS_READER:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", {fname});')
    elif ftype in field_is_enum:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", {fname});')
    else:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{fname}", {fname});')

  println(out, indent + "}")


def exportInnerEnum(out, data, indent0):
  produceDocstring(out, indent0, data.docstring)
  println(out, f"{indent0}public enum {data.name} : byte")
  println(out, indent0 + "{")
  indent =  indent0 + "  "
  last = [f for f, *_ in data.fields if f][-1]
  for f, _, _, docstring in data.fields:
    if f:
      produceDocstring(out, indent, docstring)
      out.write(indent)
      out.write(f)
      if f == last:
        out.write("\n")
      else:
        out.write(",\n")
    else:
      out.write("\n")
      for line in docstring:
        out.write(indent)
        out.write("// ")
        out.write(line)
        out.write("\n")
      out.write("\n")
  println(out, indent0 + "}")


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
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, namespace, data, version):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)

    produceDocstring(out, "  ", data.docstring)
    println(out, f"  public sealed class {data.name} : BluePacket")
    println(out,  "  {")
    produceDocstring(out, DEFAULT_INDENT, ["Internal method to get the hash version number of this packet."], ["<returns>version hash</returns>"])
    println(out, f"    override public long GetPacketHash() {{ return {version}; }}")
    println(out)
    produceDocstring(out, DEFAULT_INDENT, ["Internal method to get the hash version number of this packet."], ["<returns>version hash hexadecimal</returns>"])
    println(out, f'    override public string GetPacketHex() {{ return "0x{version & 0xFFFFFFFFFFFFFFFF:0X}"; }}')
    println(out)

    println(out, DEFAULT_INDENT + "/* --- DATA FIELDS --- */")
    println(out)
    produceFields(out, data.fields, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "/* --- HELPER FUNCTIONS --- */")
    sorted_fields = list(sorted(data.fields))
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)

    if data.inner:
      println(out)
      println(out, DEFAULT_INDENT + "/* --- INNER CLASSES --- */")
    for x in data.inner.values():
      exportInnerClass(out, x, data.field_is_enum)

    if data.enums:
      println(out)
      println(out, DEFAULT_INDENT + "/* --- INNER ENUMS --- */")
    for x in data.enums.values():
      exportInnerEnum(out, x, DEFAULT_INDENT)

    println(out, "  }")
    println(out, "}")


def exportEnum(out_dir, namespace, data):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)
    exportInnerEnum(out, data, "  ")
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
