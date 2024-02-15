#! /usr/bin/env python3
import argparse
import copy
import os, sys

from libexport import MARKER_DEPRECATED, Parser, println, versionHash

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
  "packet": "*bluepacket.BluePacket",
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
  "packet": "bluepacket.WriteBluePacket(w, %s)",
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
  "packet": "ReadBluePacket(r)",
  "short":  "ReadShort(r)",
  "string": "ReadString(r)",
  "ubyte":  "ReadByte(r)",
  "ushort": "ReadUShort(r)",
}

def header(out, package, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, f"package {package}")
    println(out)
    if data.is_enum:
      pass
    elif data.is_abstract:
      println(out, 'import (\n\t"bytes"\n\t"strings"\n)')
    elif any(pf.name for pf in data.fields):
      println(out, 'import (\n\t"bytes"\n\t"github.com/bluepacket"\n\t"strings"\n)')
    else:
      println(out, 'import (\n\t"bytes"\n\t"strings"\n)')
    println(out)


def produceDocstring(out, indent, docstring):
  for line in docstring:
    out.write(indent)
    out.write("// ")
    out.write(line)
    out.write("\n")


_GOLANG_DEPRECATED = '\u0394'


def _getGoType(ftype):
  return ftype.replace(MARKER_DEPRECATED, _GOLANG_DEPRECATED) if ftype is not None else None


def produceStructDef(out, name, fields, field_is_enum):
  println(out, f"type {name} struct {{")
  first = True
  for pf in fields:
    ftype = _getGoType(pf.type)
    if pf.is_list:
      produceDocstring(out, "\t", pf.docstring)
      if pf.type in GO_WRITER:  # native type
        println(out, f"\t{pf.name} []{GO_TYPE.get(ftype, ftype)}")
      elif ftype in field_is_enum:
        println(out, f"\t{pf.name} []{ftype}")
      else:
        println(out, f"\t{pf.name} []*{ftype}")
      first = False
    elif pf.name:
      produceDocstring(out, "\t", pf.docstring)
      if ftype in GO_WRITER:  # native type
        println(out, f"\t{pf.name} {GO_TYPE.get(ftype, ftype)}")
      elif ftype in field_is_enum:
        println(out, f"\t{pf.name} {ftype}")
      else:
        println(out, f"\t{pf.name} *{ftype}")
      first = False
    elif pf.docstring:
      if not first:
        println(out)
      produceDocstring(out, "\t", pf.docstring)
      println(out)
    else:
      println(out)
  println(out, "}")
  println(out)


def produceSerializer(out, name, fields, field_is_enum):
  println(out)
  println(out, f"func (bp *{name}) SerializeData(w *bytes.Buffer) {{")

  bool_counter = 0
  for pf in fields:
    ftype = _getGoType(pf.type)
    if pf.is_list or ftype != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"\t// boolean fields are packed into bytes")
      println(out, f"\tbin := byte(0)")
    elif  bool_counter % 8 == 0:
      println(out, f"\tw.WriteByte(bin)")
      println(out, f"\tbin = 0")

    println(out, f"\tif bp.{pf.name} {{ bin |= {1<<(bool_counter%8)} }}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"\tw.WriteByte(bin)")

  println(out, f"\t// Non-boolean fields")
  for pf in fields:
    ftype = _getGoType(pf.type)
    if (not pf.is_list and ftype == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if ftype == 'bool':
        println(out, f"\tbluepacket.WriteListBool(w, bp.{pf.name})")
        continue
      println(out, f"\tbluepacket.WriteSequenceLength(w, len(bp.{pf.name}))")
      println(out, f"\tfor _, p := range bp.{pf.name} {{")
      if ftype in GO_WRITER:
        println(out,  "\t\t" + GO_WRITER[ftype] % "p")
      elif ftype in field_is_enum:
        if field_is_enum[ftype] <= 256:
          println(out, f"\t\tw.WriteByte(byte(p))")
        else:
          println(out, f"\t\tbluepacket.WriteUShort(w, uint16(p))")
      else:
        println(out, f"\t\tp.SerializeData(w)")
      println(out, "\t}")
    elif ftype in field_is_enum:
      if field_is_enum[ftype] <= 256:
        println(out, f"\tw.WriteByte(byte(bp.{pf.name}))")
      else:
        println(out, f"\tbluepacket.WriteUShort(w, uint16(bp.{pf.name}))")
    elif ftype in GO_WRITER:
      println(out,  "\t" + GO_WRITER[ftype] % f"bp.{pf.name}")
    else:
      println(out, f"\tif bp.{pf.name} == nil {{")
      println(out, f"\t\tw.WriteByte(0)")
      println(out,  "\t} else {")
      println(out, f"\t\tw.WriteByte(1)")
      println(out, f"\t\tbp.{pf.name}.SerializeData(w)")
      println(out,  "\t}")

  println(out, "}")


def produceDeserializer(out, name, fields, field_is_enum):
  println(out)
  println(out, f"func (bp *{name}) PopulateData(r *bytes.Reader) {{")

  bool_counter = 0
  for pf in fields:
    ftype = _getGoType(pf.type)
    if pf.is_list or ftype != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"\t// boolean fields are packed into bytes")
      println(out, f"\tvar bin byte")
    if  bool_counter % 8 == 0:
      println(out, f"\tbin = bluepacket.ReadByte(r)")

    println(out, f"\tbp.{pf.name} = (bin & {1<<(bool_counter%8)}) != 0")
    bool_counter += 1

  println(out, f"\t// Non-boolean fields")
  for pf in fields:
    ftype = _getGoType(pf.type)
    if (not pf.is_list and ftype == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if ftype == 'bool':
        println(out, f"\tbp.{pf.name} = bluepacket.ReadListBool(r)")
        continue
      println(out, f"\tsize{pf.name} := bluepacket.ReadSequenceLength(r)")
      if ftype in GO_TYPE or ftype in field_is_enum:
        gotype = GO_TYPE.get(ftype, ftype)
      else:
        gotype = "*" + ftype
      println(out, f'\tbp.{pf.name} = make([]{gotype}, size{pf.name})')
      println(out, f"\tfor i := 0; i < size{pf.name}; i++ {{")
      if ftype in GO_READER:
        println(out, f"\t\tbp.{pf.name}[i] = bluepacket.{GO_READER[ftype]}")
      elif ftype in field_is_enum:
        if field_is_enum[ftype] <= 256:
          println(out, f"\t\tbp.{pf.name}[i] = {ftype}(bluepacket.ReadByte(r))")
        else:
          println(out, f"\t\tbp.{pf.name}[i] = {ftype}(bluepacket.ReadUShort(r))")
      else:
        println(out, f"\t\tobj := {ftype}{{}}")
        println(out, f"\t\tobj.PopulateData(r)")
        println(out, f"\t\tbp.{pf.name}[i] = &obj")
      println(out, "\t}")
    elif ftype in field_is_enum:
      if field_is_enum[ftype] <= 256:
        println(out, f"\tbp.{pf.name} = {ftype}(bluepacket.ReadByte(r))")
      else:
        println(out, f"\tbp.{pf.name} = {ftype}(bluepacket.ReadUShort(r))")
    elif ftype in GO_READER:
      println(out, f"\tbp.{pf.name} = bluepacket.{GO_READER[ftype]}")
    else:
      println(out, f"\tif bluepacket.ReadByte(r) > 0 {{")
      println(out, f"\t\tbp.{pf.name} = &{ftype}{{}}")
      println(out, f"\t\tbp.{pf.name}.PopulateData(r)")
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
  for pf in fields:
    ftype = _getGoType(pf.type)
    if not pf.name:
      continue
    if pf.is_list:
      if ftype == "bool":
        println(out, f'\tbluepacket.AppendIfNotEmptyListBool(sb, "{pf.name}", bp.{pf.name})')
      elif ftype == "string":
        println(out, f'\tbluepacket.AppendIfNotEmptyListString(sb, "{pf.name}", bp.{pf.name})')
      elif ftype in GO_EMPTY or ftype in field_is_enum:
        println(out, f'\tbluepacket.AppendIfNotEmptyList(sb, "{pf.name}", "{ftype}", bp.{pf.name})')
      else:
        println(out, f'\tbluepacket.AppendIfNotEmptyListBP(sb, "{pf.name}", "{ftype}", bp.{pf.name})')
    elif ftype in field_is_enum:
      println(out, f'\tbluepacket.AppendIfNotEmptyEnum(sb, "{pf.name}", bp.{pf.name}, bp.{pf.name})')
    elif ftype == "bool":
      println(out, f'\tbluepacket.AppendIfNotEmptyBool(sb, "{pf.name}", bp.{pf.name})')
    elif ftype == "string":
      println(out, f'\tbluepacket.AppendIfNotEmptyString(sb, "{pf.name}", bp.{pf.name})')
    elif ftype in GO_EMPTY:
      println(out, f'\tbluepacket.AppendIfNotEmpty(sb, "{pf.name}", bp.{pf.name}, {GO_EMPTY[ftype]})')
    elif ftype == "packet":
      println(out, f'\tbluepacket.AppendIfNotNilPacket(sb, "{pf.name}", bp.{pf.name})')
    else:
      println(out, f'\tbluepacket.AppendIfNotNil(sb, "{pf.name}", bp.{pf.name})')
  println(out,  "}")


def exportStructFunc(out, data, field_is_enum, namespace):
  println(out, "////// HELPER FUNCTIONS /////")
  sorted_fields = list(sorted(data.fields, key=str))
  goname = _getGoType(data.name)
  produceSerializer(out, namespace + goname, sorted_fields, data.field_is_enum)
  produceDeserializer(out, namespace + goname, sorted_fields, data.field_is_enum)
  produceToString(out, namespace + goname, sorted_fields, data.field_is_enum)

def produceConvert(out, name, ctype, copts, other_fields, indent):
  println(out)
  produceDocstring(out, indent,
    [
      f"Converter function to build an instance of {name} from an instance of {ctype}",
    ]
  )
  println(out, f"func (other *{ctype}) New{name}() *{name} {{")
  println(out, indent + f"\treturn &{name}{{")
  for pf in other_fields:
    if pf.name:
      println(out, f"{indent}\t\t{pf.name[0].upper()}{pf.name[1:]}: other.{pf.name[0].upper()}{pf.name[1:]},")
  println(out, indent + "\t}")
  println(out, "}")

def _innerFieldsWithNamespace(data):
  goname = _getGoType(data.name)
  for pf in data.fields:
    ret = copy.copy(pf)
    if pf.name:
      # capitalize all field names to make them public
      ret.name = pf.name[0].upper() + pf.name[1:]
    if pf.type in data.inner or pf.type in data.enums:
      ret.type = goname + pf.type
    yield ret


def _innerFieldIsEnumWithNamespace(data):
  goname = _getGoType(data.name)
  for info, num in data.field_is_enum.items():
    if info in data.inner or info in data.enums:
      yield goname + info, num
    else:
      yield info, num


def exportStruct(out_dir, package, data, version, all_data):
  # namespace inner definition by using the parent package as prefix
  data.fields = list(_innerFieldsWithNamespace(data))
  data.field_is_enum = {k: v for k, v in _innerFieldIsEnumWithNamespace(data)}

  goname = _getGoType(data.name)
  path = os.path.join(out_dir, goname + ".go")
  print("[ExporterGo] BluePacket struct", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    produceDocstring(out, "", data.docstring)
    produceStructDef(out, goname, data.fields, data.field_is_enum)
    println(out, f"func (bp *{goname}) GetPacketHash() int64 {{ return {version} }}")
    println(out, f'func (bp *{goname}) GetPacketHex() string {{ return "0x{version & 0xFFFFFFFFFFFFFFFF:0X}" }}')
    println(out)
    exportStructFunc(out, data, data.field_is_enum, "")

    for ctype, copts in data.converts.items():
      other = all_data.get(ctype)
      if not other:
        raise SourceException("Converter from unknown type", what=ctype)
      cfields = list(sorted(other.fields, key=str))
      produceConvert(out, data.name, ctype, copts, cfields, "")

    if data.inner:
      println(out)
      println(out, "///// INNER CLASSES /////")
      println(out)
    for x in data.inner.values():
      x.fields = list(_innerFieldsWithNamespace(x))
      produceDocstring(out, "", x.docstring)
      produceStructDef(out, goname + x.name, x.fields, data.field_is_enum)
      println(out, f"func (bp *{goname}{x.name}) GetPacketHash() int64 {{ return 0 }}")
      println(out, f'func (bp *{goname}{x.name}) GetPacketHex() string {{ return "" }}')
      println(out)
      exportStructFunc(out, x, data.field_is_enum, goname)

    if data.enums:
      println(out)
      println(out, "///// INNER ENUMS /////")
      println(out)
      for x in data.enums.values():
        produceDocstring(out, "", x.docstring)
        exportEnumDef(out, x, goname)


def exportEnum(out_dir, package, data):
  goname = _getGoType(data.name)
  path = os.path.join(out_dir, goname + ".go")
  print("[ExporterGo] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)
    produceDocstring(out, "", data.docstring)
    exportEnumDef(out, data, "")


def exportEnumDef(out, data, namespace):
    goname = _getGoType(data.name)
    num = sum(1 for pf in data.fields if pf.name)
    subtype = "byte" if num <=256 else "uint16"
    println(out, f"type {namespace}{goname} {subtype}")
    println(out, f"const (")
    i = 0
    for pf in data.fields:
      if not pf.name:
        println(out)
      produceDocstring(out, "\t", pf.docstring)
      if pf.name:
        println(out, f"\t{namespace}{goname}{pf.name} {namespace}{goname} = {i}")
        i += 1
      else:
        println(out)
    println(out, ")")
    println(out)
    println(out, f"func (en {namespace}{goname}) String() string {{")
    println(out, f"\tshortName{namespace}{goname} := [{num}]string {{")
    for pf in data.fields:
      if pf.name:
        println(out, f'\t\t"{pf.name}",')
    println(out, "\t}")
    println(out, f"\treturn shortName{namespace}{goname}[int(en)]")
    println(out, "}")


def exportApiVersion(out_dir, package, api_version):
  path = os.path.join(out_dir, "BluePacketAPI.go")
  print("[ExporterGo] API Version", path, file=sys.stderr)
  with open(path, "w") as out:
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "package " + package)
    println(out)
    produceDocstring(out, "", ["API information for this package."])
    println(out, "const (")
    produceDocstring(out, "\t", ["API Version calculated for all the packets in this package."])
    println(out, f"\tBluePacketApiVersion int64 = {api_version}")
    println(out, f'\tBluePacketApiVersionHex string = "0x{api_version & 0xFFFFFFFFFFFFFFFF:0X}"')
    println(out, ")")


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', help='Directory where the sources will be generated')
  parser.add_argument('--package', help='Package for the generated classes')
  parser.add_argument('--debug', action='store_true', help='Print parser debug info')
  # Golint might not like __ in names, so there's an option to replace this marker with another string. 
  # We should pick special letters that look like separators and are easy to distinguish from alphabetic letters.
  # Recommended: U+0394     GREEK CAPITAL LETTER DELTA     Δ
  parser.add_argument('--marker_deprecated', default='\u0394', help='string to replace __ in deprecated packet names') 
  parser.add_argument('packets', nargs='+', help='List of .bp files to process')
  return parser.parse_args()


if __name__ == "__main__":
  args = get_args()
  p = Parser()
  _GOLANG_DEPRECATED = args.marker_deprecated
  all_data = p.parse(args.packets)
  if args.debug:
    for cl, lf in all_data.items():
      print(cl, lf)

  # compute version hashes before fields are capitalized
  versions = {
     _getGoType(data.name): versionHash(data, all_data)
    for _, data in all_data.items()
  }

  # now produce the go code
  for _, data in all_data.items():
    if data.is_enum:
      exportEnum(args.output_dir, args.package, data)
    else:
      exportStruct(args.output_dir, args.package, data, versions[_getGoType(data.name)], all_data)
  exportApiVersion(args.output_dir, args.package, p.api_version)
