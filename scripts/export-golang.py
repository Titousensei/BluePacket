#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

GO_TYPE = {
  "bool": "bool",
  "byte": "int8",
  "ubyte": "byte",
  "short": "int16",
  "ushort": "uint16",
  "int": "int32",
  "long": "int64",
  "float": "float32",
  "double": "float64",
  "string": "string",
}

GO_EMPTY = {
  "bool":   "false",
  "byte":   "int8(0)",
  "double": "float64(0.0)",
  "float":  "float32(0.0)",
  "int":    "int32(0)",
  "long":   "int64(0)",
  "short":  "int16(0)",
  "string": '""',
  "ubyte":  "uint8(0)",
  "ushort": "uint16(0)",
}

GO_WRITER = {
  "bool":   "bluepacket.WriteBool(w, %s)",
  "byte":   "w.WriteByte(byte(%s))",
  "double": "bluepacket.WriteDouble(w, %s)",
  "float":  "bluepacket.WriteFloat(w, %s)",
  "int":    "bluepacket.WriteInt(w, %s)",
  "long":   "bluepacket.WriteLong(w, %s)",
  "short":  "bluepacket.WriteShort(w, %s)",
  "string": "bluepacket.WriteString(w, %s)",
  "ubyte":  "w.WriteByte(%s)",
  "ushort": "bluepacket.WriteUShort(w, %s)",
}

GO_READER = {
  "bool":   "ReadBool(r)",
  "byte":   "ReadSByte(r)",
  "double": "ReadDouble(r)",
  "float":  "ReadFloat(r)",
  "int":    "ReadInt(r)",
  "long":   "ReadLong(r)",
  "short":  "ReadShort(r)",
  "string": "ReadString(r)",
  "ubyte":  "ReadByte(r)",
  "ushort": "ReadUShort(r)",
}

def header(out, package, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, f"package {package}")
    println(out)
    if not data.is_enum:
      println(out, 'import (\n\t"bytes"\n\t"github.com/bluepacket"\n\t"strings"\n)')
      println(out)
    println(out)


def produceDocstring(out, indent, docstring):
  for line in docstring:
    out.write(indent)
    out.write("// ")
    out.write(line)
    out.write("\n")


def produceStructDef(out, name, fields, field_is_enum):
  println(out, f"type {name} struct {{")
  first = True
  for fname, ftype, opt, docstring in fields:
    if 'list' in opt:
      produceDocstring(out, "\t", docstring)
      if ftype in GO_WRITER:  # native type
        println(out, f"\t{fname} []{GO_TYPE.get(ftype, ftype)}")
      elif ftype in field_is_enum:
        println(out, f"\t{fname} []{ftype}")
      else:
        println(out, f"\t{fname} []*{ftype}")
      first = False
    elif fname:
      produceDocstring(out, "\t", docstring)
      if ftype in GO_WRITER:  # native type
        println(out, f"\t{fname} {GO_TYPE.get(ftype, ftype)}")
      elif ftype in field_is_enum:
        println(out, f"\t{fname} {ftype}")
      else:
        println(out, f"\t{fname} *{ftype}")
      first = False
    elif docstring:
      if not first:
        println(out)
      produceDocstring(out, "\t", docstring)
      println(out)
    else:
      println(out)
  println(out, "}")
  println(out)


def produceSerializer(out, name, fields, field_is_enum):
  println(out)
  println(out, f"func (bp *{name}) SerializeData(w *bytes.Buffer) {{")

  bool_counter = 0
  for fname, ftype, *opt in fields:
    if ftype != 'bool' or 'list' in opt:
      continue
    if bool_counter == 0:
      println(out, f"\t// boolean fields are packed into bytes")
      println(out, f"\tbin := byte(0)")
    elif  bool_counter % 8 == 0:
      println(out, f"\tw.WriteByte(bin)")
      println(out, f"\tbin = 0")

    println(out, f"\tif bp.{fname} {{ bin |= {1<<(bool_counter%8)} }} else {{ bin &= {255 & ~(1<<(bool_counter%8))} }}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"\tw.WriteByte(bin)")

  println(out, f"\t// Non-boolean fields")
  for fname, ftype, opt, _ in fields:
    if not fname or (ftype == 'bool' and 'list' not in opt):
      continue
    if 'list' in opt:
      println(out, f"\tbluepacket.WriteSequenceLength(w, len(bp.{fname}))")
      println(out, f"\tfor _, p := range bp.{fname} {{")
      if ftype in GO_WRITER:
        println(out,  "\t\t" + GO_WRITER[ftype] % "p")
      elif ftype in field_is_enum:
        println(out, f"\t\tw.WriteByte(byte(p))")
      else:
        println(out, f"\t\tp.SerializeData(w)")
      println(out, "\t}")
    elif ftype in field_is_enum:
      println(out, f"\tw.WriteByte(byte(bp.{fname}))")
    elif ftype in GO_WRITER:
      println(out,  "\t" + GO_WRITER[ftype] % f"bp.{fname}")
    else:
      println(out, f"\tif bp.{fname} == nil {{")
      println(out, f"\t\tw.WriteByte(0)")
      println(out,  "\t} else {")
      println(out, f"\t\tw.WriteByte(1)")
      println(out, f"\t\tbp.{fname}.SerializeData(w)")
      println(out,  "\t}")

  println(out, "}")


def produceDeserializer(out, name, fields, field_is_enum):
  println(out)
  println(out, f"func (bp *{name}) PopulateData(r *bytes.Reader) {{")

  bool_counter = 0
  for fname, ftype, *opt in fields:
    if ftype != 'bool' or 'list' in opt:
      continue
    if bool_counter == 0:
      println(out, f"\t// boolean fields are packed into bytes")
      println(out, f"\tvar bin byte")
    if  bool_counter % 8 == 0:
      println(out, f"\tbin = bluepacket.ReadByte(r)")

    println(out, f"\tbp.{fname} = (bin & {1<<(bool_counter%8)}) != 0")
    bool_counter += 1

  println(out, f"\t// Non-boolean fields")
  for fname, ftype, opt, _ in fields:
    if not fname or (ftype == 'bool' and 'list' not in opt):
      continue
    if 'list' in opt:
      println(out, f"\tsize{fname} := bluepacket.ReadSequenceLength(r)")
      if ftype in GO_TYPE or ftype in field_is_enum:
        gotype = GO_TYPE.get(ftype, ftype)
      else:
        gotype = "*" + ftype
      println(out, f'\tbp.{fname} = make([]{gotype}, size{fname})')
      println(out, f"\tfor i := 0; i < size{fname}; i++ {{")
      if ftype in GO_READER:
        println(out, f"\t\tbp.{fname}[i] = bluepacket.{GO_READER[ftype]}")
      elif ftype in field_is_enum:
        println(out, f"\t\tbp.{fname}[i] = {ftype}(bluepacket.ReadByte(r))")
      else:
        println(out, f"\t\tobj := {ftype}{{}}")
        println(out, f"\t\tobj.PopulateData(r)")
        println(out, f"\t\tbp.{fname}[i] = &obj")
      println(out, "\t}")
    elif ftype in field_is_enum:
      println(out, f"\tbp.{fname} = {ftype}(bluepacket.ReadByte(r))")
    elif ftype in GO_READER:
      println(out, f"\tbp.{fname} = bluepacket.{GO_READER[ftype]}")
    else:
      println(out, f"\tif bluepacket.ReadByte(r) > 0 {{")
      println(out, f"\t\tbp.{fname} = &{ftype}{{}}")
      println(out, f"\t\tbp.{fname}.PopulateData(r)")
      println(out, "\t}")

  println(out, "}")


def produceToString(out, name, fields, field_is_enum):
  println(out)
  println(out, f"func (bp *{name}) String() string {{")
  println(out,  "\tsb := strings.Builder{}")
  println(out, f'\tsb.WriteString("{{{name}")')
  println(out,  '\tif bp.GetPacketHex() != "" {')
  println(out, f'\t\tsb.WriteString(" ")')
  println(out, f'\t\tsb.WriteString(bp.GetPacketHex())')
  println(out,  '\t}')
  println(out, f'\tbp.AppendFields(&sb)')
  println(out,  '\tsb.WriteString("}")')
  println(out,  '\treturn sb.String()')
  println(out,  "}")
  println(out)

  println(out, f"func (bp *{name}) AppendFields(sb *strings.Builder) {{")
  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      if ftype == "bool":
        println(out, f'\tbluepacket.AppendIfNotEmptyListBool(sb, "{fname}", bp.{fname})')
      elif ftype == "string":
        println(out, f'\tbluepacket.AppendIfNotEmptyListString(sb, "{fname}", bp.{fname})')
      elif ftype in GO_EMPTY or ftype in field_is_enum:
        println(out, f'\tbluepacket.AppendIfNotEmptyList(sb, "{fname}", "{ftype}", bp.{fname})')
      else:
        println(out, f'\tbluepacket.AppendIfNotEmptyListBP(sb, "{fname}", "{ftype}", bp.{fname})')
    elif ftype in field_is_enum:
      println(out, f'\tbluepacket.AppendIfNotEmptyEnum(sb, "{fname}", bp.{fname}, bp.{fname})')
    elif ftype == "bool":
      println(out, f'\tbluepacket.AppendIfNotEmptyBool(sb, "{fname}", bp.{fname})')
    elif ftype == "string":
      println(out, f'\tbluepacket.AppendIfNotEmptyString(sb, "{fname}", bp.{fname})')
    elif ftype in GO_EMPTY:
      println(out, f'\tbluepacket.AppendIfNotEmpty(sb, "{fname}", bp.{fname}, {GO_EMPTY[ftype]})')
    else:
      println(out, f'\tbluepacket.AppendIfNotNil(sb, "{fname}", bp.{fname})')
  println(out,  "}")


def exportStructFunc(out, data, field_is_enum, namespace):
  println(out, "////// HELPER FUNCTIONS /////")
  sorted_fields = list(sorted(data.fields))
  produceSerializer(out, namespace + data.name, sorted_fields, data.field_is_enum)
  produceDeserializer(out, namespace + data.name, sorted_fields, data.field_is_enum)
  produceToString(out, namespace + data.name, sorted_fields, data.field_is_enum)


def _innerFieldsWithNamespace(data):
  for info in data.fields:
    if info[0]:
      # capitalize all field names to make them public
      info[0] = info[0][0].upper() + info[0][1:]
    if info[1] in data.inner or info[1] in data.enums:
      info[1] = data.name + info[1]
    yield info


def _innerFieldIsEnumWithNamespace(data):
  for info in data.field_is_enum:
    if info in data.inner or info in data.enums:
      yield data.name + info
    else:
      yield info


def exportStruct(out_dir, package, data, version):
  # namespace inner definition by using the parent package as prefix
  data.fields = list(_innerFieldsWithNamespace(data))
  data.field_is_enum = set(_innerFieldIsEnumWithNamespace(data))

  path = os.path.join(out_dir, data.name + ".go")
  print("[ExporterGo] BluePacket struct", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    produceDocstring(out, "", data.docstring)
    produceStructDef(out, data.name, data.fields, data.field_is_enum)
    println(out, f"func (bp *{data.name}) GetPacketHash() int64 {{ return {version} }}")
    println(out, f'func (bp *{data.name}) GetPacketHex() string {{ return "0x{version & 0xFFFFFFFFFFFFFFFF:0X}" }}')
    println(out)
    exportStructFunc(out, data, data.field_is_enum, "")

    if data.inner:
      println(out)
      println(out, "///// INNER CLASSES /////")
      println(out)
    for x in data.inner.values():
      x.fields = list(_innerFieldsWithNamespace(x))
      produceDocstring(out, "", x.docstring)
      produceStructDef(out, data.name + x.name, x.fields, data.field_is_enum)
      println(out, f"func (bp *{data.name}{x.name}) GetPacketHash() int64 {{ return 0 }}")
      println(out, f'func (bp *{data.name}{x.name}) GetPacketHex() string {{ return "" }}')
      println(out)
      exportStructFunc(out, x, data.field_is_enum, data.name)

    if data.enums:
      println(out)
      println(out, "///// INNER ENUMS /////")
      println(out)
      for x in data.enums.values():
        produceDocstring(out, "", x.docstring)
        exportEnumDef(out, x, data.name)


def exportEnum(out_dir, package, data):
  path = os.path.join(out_dir, data.name + ".go")
  print("[ExporterGo] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)
    produceDocstring(out, "", data.docstring)
    exportEnumDef(out, data, "")


def exportEnumDef(out, data, namespace):
    println(out, f"type {namespace}{data.name} byte")
    println(out, f"const (")
    suffix =  f"  {namespace}{data.name} = iota"
    for f, _, _, docstring in data.fields:
      if not f and not suffix:
        println(out)
      produceDocstring(out, "\t", docstring)
      if f:
        println(out, f"\t{namespace}{data.name}{f}  {suffix}")
        suffix = ""
      else:
        println(out)
    println(out, ")")
    println(out)
    println(out, f"func (en {namespace}{data.name}) String() string {{")
    println(out, f"\tshortName{namespace}{data.name} := [{len(data.fields)}]string {{")
    for f, *_ in data.fields:
      if f:
        println(out, f'\t\t"{f}",')
    println(out, "\t}")
    println(out, f"\treturn shortName{namespace}{data.name}[int(en)]")
    println(out, "}")


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', help='Directory where the sources will be generated')
  parser.add_argument('--package', help='Package for the generated classes')
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

  # compute version hashes before fields are capitalized
  versions = {
    data.name: versionHash(data, all_data)
    for _, data in all_data.items()
  }

  # now produce the go code
  for _, data in all_data.items():
    if data.is_enum:
      exportEnum(args.output_dir, args.package, data)
    else:
      exportStruct(args.output_dir, args.package, data, versions[data.name])
