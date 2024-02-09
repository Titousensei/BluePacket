#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "    "
INNER_INDENT = DEFAULT_INDENT + "  "

CS_TYPE = {
  "byte": "sbyte",
  "packet": "BluePacket",
  "ubyte": "byte",
}

CS_WRITER = {
  "byte":   "WriteSByte",
  "double": "WriteDouble",
  "float":  "WriteFloat",
  "int":    "WriteInt",
  "long":   "WriteLong",
  "packet": "WriteBluePacket",
  "short":  "WriteShort",
  "string": "WriteString",
  "ubyte":  "WriteByte",
  "ushort": "WriteUShort",
}

CS_READER = {
  "byte":   "ReadSByte",
  "double": "ReadDouble",
  "float":  "ReadFloat",
  "int":    "ReadInt",
  "long":   "ReadLong",
  "packet": "Deserialize",
  "short":  "ReadShort",
  "string": "ReadString",
  "ubyte":  "ReadByte",
  "ushort": "ReadUShort",
}

def header(out, namespace, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    if not data.is_enum and not data.is_abstract:
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
  for pf in fields:
    if pf.is_list:
      produceDocstring(out, indent, pf.docstring)
      println(out, f"{indent}public {CS_TYPE.get(pf.type, pf.type)}[] {pf.name};")
    elif pf.name:
      produceDocstring(out, indent, pf.docstring)
      println(out, f"{indent}public {CS_TYPE.get(pf.type, pf.type)} {pf.name};")
    elif pf.docstring:
      println(out)
      for line in pf.docstring:
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
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  byte bin = 0;")
    elif  bool_counter % 8 == 0:
      println(out, f"{indent}  s.WriteByte(bin);")
      println(out, f"{indent}  bin = 0;")

    println(out, f"{indent}  if (this.{pf.name}) {{ bin |= {1<<(bool_counter%8)}; }}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"{indent}  s.WriteByte(bin);")

  println(out, f"{indent}  // Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if pf.type == 'bool':
        println(out, f"{indent}  WriteListBool(s, this.{pf.name});")
        continue
      println(out, f"{indent}  if (this.{pf.name} == null) s.WriteByte(0); else {{")
      println(out, f"{indent}    WriteSequenceLength(s, this.{pf.name}.Length);")
      if pf.type in CS_WRITER:
        println(out, f"{indent}    for (int i = 0; i < this.{pf.name}.Length; ++i)")
        println(out, f"{indent}      {CS_WRITER[pf.type]}(s, this.{pf.name}[i]);")
      elif pf.type in field_is_enum:
        println(out, f"{indent}    foreach ({pf.type} p in this.{pf.name})")
        if field_is_enum[pf.type] <= 256:
          println(out, f"{indent}      WriteEnum(s, p);")
        else:
          println(out, f"{indent}      WriteLargeEnum(s, p);")
      else:
        println(out, f"{indent}    foreach (BluePacket p in this.{pf.name})")
        println(out, f"{indent}      p.SerializeData(s);")
      println(out, indent + "  }")
    elif pf.type in field_is_enum:
      if field_is_enum[pf.type] <= 256:
        println(out, f"{indent}  WriteEnum(s, this.{pf.name});")
      else:
        println(out, f"{indent}  WriteLargeEnum(s, this.{pf.name});")
    elif pf.type in CS_WRITER:
      println(out, f"{indent}  {CS_WRITER[pf.type]}(s, this.{pf.name});")
    else:
      println(out, f"{indent}  if (this.{pf.name} == null) s.WriteByte(0);")
      println(out, indent + "  else {")
      println(out, f"{indent}    s.WriteByte(1);")
      println(out, f"{indent}    this.{pf.name}.SerializeData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceDeserializer(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to deserialize from bytes into this object fields"], ['<param name="s">stream to read the bytes from</param>'])
  println(out, f"{indent}override public void PopulateData(Stream s)")
  println(out, indent + "{")

  bool_counter = 0
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  int bin;")
    if  bool_counter % 8 == 0:
      println(out, f"{indent}  bin = s.ReadByte();")

    println(out, f"{indent}  this.{pf.name} = (bin & {1<<(bool_counter%8)}) != 0;")
    bool_counter += 1

  println(out, f"{indent}  // Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if pf.type == 'bool':
        println(out, f"{indent}  this.{pf.name} = ReadListBool(s);")
        continue
      println(out, f"{indent}  {pf.name} = new {CS_TYPE.get(pf.type, pf.type)}[ReadSequenceLength(s)];")
      println(out, f"{indent}  for (int i = 0; i < {pf.name}.Length; ++i) {{")
      if pf.type in CS_READER:
        println(out, f"{indent}    {pf.name}[i] = {CS_READER[pf.type]}(s);")
      elif pf.type in field_is_enum:
        if field_is_enum[pf.type] <= 256:
          println(out, f"{indent}    {pf.name}[i] = ({pf.type})ReadEnum(typeof({pf.type}), s);")
        else:
          println(out, f"{indent}    {pf.name}[i] = ({pf.type})ReadLargeEnum(typeof({pf.type}), s);")
      else:
        println(out, f"{indent}    {pf.type} obj = new {pf.type}();")
        println(out, f"{indent}    obj.PopulateData(s);")
        println(out, f"{indent}    {pf.name}[i] = obj;")
      println(out, indent + "  }")
    elif pf.type in field_is_enum:
      if field_is_enum[pf.type] <= 256:
        println(out, f"{indent}  {pf.name} = ({pf.type})ReadEnum(typeof({pf.type}), s);")
      else:
        println(out, f"{indent}  {pf.name} = ({pf.type})ReadLargeEnum(typeof({pf.type}), s);")
    elif pf.type in CS_READER:
      println(out, f"{indent}  {pf.name} = {CS_READER[pf.type]}(s);")
    else:
      println(out, f"{indent}  if (ReadByte(s) > 0) {{")
      println(out, f"{indent}    {pf.name} = new {pf.type}();")
      println(out, f"{indent}    {pf.name}.PopulateData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceFieldsToString(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal helper method for ToString()"], ['<param name="sb">builder to write the fields and their values</param>'])
  println(out, indent + "override public void FieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for pf in fields:
    if not pf.name:
      continue
    if pf.is_list:
      if pf.type in CS_READER or pf.type == 'bool':
        println(out, f'{indent}  AppendIfNotEmptyArray<{CS_TYPE.get(pf.type, pf.type)}>(sb, "{pf.name}", "{pf.type}", {pf.name});')
      elif pf.type in field_is_enum:
        println(out, f'{indent}  AppendIfNotEmptyArray<String>(sb, "{pf.name}", "{pf.type}", Array.ConvertAll({pf.name}, value => value.ToString()));')
      else:
        println(out, f'{indent}  AppendIfNotEmpty(sb, "{pf.name}", "{pf.type}", {pf.name});')
    elif pf.type in CS_READER:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{pf.name}", {pf.name});')
    elif pf.type in field_is_enum:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{pf.name}", {pf.name});')
    else:
      println(out, f'{indent}  AppendIfNotEmpty(sb, "{pf.name}", {pf.name});')

  println(out, indent + "}")


def produceConvert(out, name, ctype, copts, other_fields, indent):
  println(out)
  produceDocstring(out, indent,
    [
      f"Converter method to build a {name} from an instance of {ctype}",
      f"@param other populated instance of {ctype}",
      f"@return new instance of {name} populated with data from other"
    ]
  )
  println(out, f"{indent}public static {name} convert({ctype} other)")
  println(out, indent + "{")
  println(out, indent + f"  return new {name} {{")

  for pf in other_fields:
    if pf.name:
      println(out, f"{indent}      {pf.name} = other.{pf.name},")

  println(out, indent + "  };")
  println(out, indent + "}")


def exportInnerEnum(out, data, indent0):
  produceDocstring(out, indent0, data.docstring)
  subtype = "byte" if sum(1 for pf in data.fields if pf.name) <=256 else "ushort"
  println(out, f"{indent0}public enum {data.name} : {subtype}")
  println(out, indent0 + "{")
  indent =  indent0 + "  "
  last = None
  for pf in data.fields:
    last = pf.name or last
  for pf in data.fields:
    if pf.name:
      produceDocstring(out, indent, pf.docstring)
      out.write(indent)
      out.write(pf.name)
      if pf.name == last:
        out.write("\n")
      else:
        out.write(",\n")
    else:
      out.write("\n")
      for line in pf.docstring:
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
  sorted_fields = list(sorted(data.fields, key=str))
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, namespace, data, version, all_data):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)

    produceDocstring(out, "  ", data.docstring)
    if data.abstracts:
      abstracts_str = ", " + ", ".join("I" + cl for cl in data.abstracts)
    else:
      abstracts_str = ""
    println(out, f"  public sealed class {data.name} : BluePacket{abstracts_str}")
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
    sorted_fields = list(sorted(data.fields, key=str))
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    for ctype, copts in data.converts.items():
      other = all_data.get(ctype)
      if not other:
        raise SourceException("Converter from unknown type", what=ctype)
      cfields = list(sorted(other.fields, key=str))
      produceConvert(out, data.name, ctype, copts, cfields, DEFAULT_INDENT)

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


def exportAbstract(out_dir, namespace, data):
  path = os.path.join(out_dir, data.name + ".cs")
  print("[ExporterCSharp] BluePacket abstract", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, namespace, data)
    produceDocstring(out, "    ", data.docstring)
    println(out, f"    interface I{data.name} {{}}")
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
    elif data.is_abstract:
      exportAbstract(args.output_dir, args.namespace, data)
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, args.namespace, data, version, all_data)
