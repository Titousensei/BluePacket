#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, SourceException, println, versionHash

DEFAULT_INDENT = "  "
INNER_INDENT = DEFAULT_INDENT + "  "

JAVA_TYPE = {
  "bool": "boolean",
  "ubyte": "byte",
  "ushort": "short",
  "packet": "BluePacket",
  "string": "String",
}

SIGNED_TYPE = { "byte", "short" }
UNSIGNED_TYPE = { "ubyte", "ushort" }

JAVA_WRITER = {
  "byte":   "s.writeByte(",
  "double": "s.writeDouble(",
  "float":  "s.writeFloat(",
  "int":    "s.writeInt(",
  "long":   "s.writeLong(",
  "packet": "writeBluePacket(s, ",
  "short":  "s.writeShort(",
  "string": "writeString(s, ",
  "ubyte":  "s.writeByte(",
  "ushort": "s.writeShort(",
}

JAVA_READER = {
  "byte":   "s.readByte()",
  "double": "s.readDouble()",
  "float":  "s.readFloat()",
  "int":    "s.readInt()",
  "long":   "s.readLong()",
  "packet": "deserialize(registry, s)",
  "short":  "s.readShort()",
  "string": "readString(s)",
  "ubyte":  "s.readByte()",
  "ushort": "s.readShort()",
}


def header(out, package, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "package " + package + ';')
    println(out)
    if not data.is_enum and not data.is_abstract:
      println(out, "import java.util.Collection;")
      println(out, "import org.bluepacket.BluePacket;")
      println(out)


def produceDocstring(out, indent, docstring):
  out.write(indent)
  out.write(f"/**\n")
  for line in docstring:
    out.write(indent)
    out.write(" * ")
    out.write(line)
    out.write("<br/>\n")
  out.write(indent)
  out.write(" */\n")


def produceFields(out, fields, enum_fields, indent):
  for pf in fields:
    ftype = JAVA_TYPE.get(pf.type, pf.type)
    if pf.is_list:
      produceDocstring(out, indent, pf.docstring)
      println(out, f"{indent}public {ftype}[] {pf.name};")
    elif ftype in enum_fields:
      produceDocstring(out, indent, pf.docstring)
      println(out, f"{indent}public {ftype} {pf.name} = {ftype}.valueOf(0);")
    elif pf.name:
      produceDocstring(out, indent, pf.docstring)
      println(out, f"{indent}public {ftype} {pf.name};")
    elif pf.docstring:
      for line in pf.docstring:
        println(out, indent + "// " + line)
    else:
      println(out)


def produceListSetters(out, name, fname, ftype, indent):
  # Array
  produceDocstring(out, indent, [f"Chaining setter for {fname} from an array or varargs.", "@param val value", "@return this"])
  out.write(f"{indent}public {name} set{fname[0].upper()}{fname[1:]}")
  out.write(f"({ftype}... val)")
  println(out, f" {{ {fname} = val; return this; }}")

  if ftype == "String" or (ftype not in JAVA_WRITER and ftype != 'boolean'):
    # Collection
    produceDocstring(out, indent, [f"Chaining setter for {fname} from a collection.", "@param val value", "@return this"])
    out.write(f"{indent}public {name} set{fname[0].upper()}{fname[1:]}")
    out.write(f"(Collection<{ftype}> val)")
    println(out, f" {{ {fname} = val.toArray(new {ftype}[0]); return this; }}")


def produceSetters(out, name, fields, indent):
  println(out)
  for pf in fields:
    if not pf.name:
      continue

    ftype = JAVA_TYPE.get(pf.type, pf.type)
    if pf.is_list:
      produceListSetters(out, name, pf.name, ftype, indent)
    else:
      produceDocstring(out, indent, [f"Chaining setter for {pf.name}.", "@param val value", "@return this"])
      out.write(f"{indent}public {name} set{pf.name[0].upper()}{pf.name[1:]}")
      out.write(f"({ftype} val)")
      println(out, f" {{ {pf.name} = val; return this; }}")


def produceGetters(out, name, fields, indent):
  println(out)
  for pf in fields:
    if pf.is_list or not pf.name:
      continue

    if pf.type in UNSIGNED_TYPE:
      produceDocstring(out, indent, [f"Getter for {pf.name} unsigned as an int.", "@return unsigned value as int"])
      out.write(f"{indent}public int get{pf.name[0].upper()}{pf.name[1:]}AsInt()")
      println(out, f" {{ return unsigned({pf.name}); }}")
    elif pf.type in SIGNED_TYPE:
      produceDocstring(out, indent, [f"Getter for {pf.name} signed as an int.", "@return signed value as int"])
      out.write(f"{indent}public int get{pf.name[0].upper()}{pf.name[1:]}AsInt()")
      println(out, f" {{ return {pf.name}; }}")


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to serialize to bytes", "@param s stream to write the bytes to"])
  println(out, indent + "@Override")
  println(out, indent + "public void serializeData(java.io.DataOutputStream s)")
  println(out, indent + "throws java.io.IOException")
  println(out, indent + "{")

  bool_counter = 0
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  byte bin = 0;")
    elif  bool_counter % 8 == 0:
      println(out, f"{indent}  s.writeByte(bin);")
      println(out, f"{indent}  bin = 0;")

    println(out, f"{indent}  if (this.{pf.name}) {{ bin |= {1<<(bool_counter%8)}; }}")
    bool_counter += 1

  if  bool_counter % 8 != 0:
    println(out, f"{indent}  s.writeByte(bin);")

  println(out, f"{indent}  // Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if field_is_enum.get(pf.type, 0) > 256:
        println(out, f"{indent}  writeArrayLargeEnum(s, this.{pf.name});")
      else:
        println(out, f"{indent}  writeArray(s, this.{pf.name});")
    elif pf.type in field_is_enum:
      if field_is_enum[pf.type] <= 256:
        println(out, f"{indent}  s.writeByte(this.{pf.name} == null ? 0 : this.{pf.name}.ordinal());")
      else:
        println(out, f"{indent}  s.writeShort(this.{pf.name} == null ? 0 : this.{pf.name}.ordinal());")
    elif pf.type in JAVA_WRITER:
      println(out, f"{indent}  {JAVA_WRITER[pf.type]}this.{pf.name});")
    else:
      println(out, f"{indent}  if ({pf.name} == null) s.writeByte(0);")
      println(out, f"{indent}  else {{")
      println(out, f"{indent}    s.writeByte(1);")
      println(out, f"{indent}    this.{pf.name}.serializeData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceDeserializer(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to deserialize from bytes into this object fields", "@param s stream to read the bytes from"])
  println(out, indent + "@Override")
  println(out, indent + "public void populateData(org.bluepacket.BluePacketRegistry registry, java.io.DataInputStream s)")
  println(out, indent + "throws java.io.IOException")
  println(out, indent + "{")

  bool_counter = 0
  for pf in fields:
    if pf.is_list or pf.type != 'bool':
      continue
    if bool_counter == 0:
      println(out, f"{indent}  // boolean fields are packed into bytes")
      println(out, f"{indent}  int bin;")
    if  bool_counter % 8 == 0:
      println(out, f"{indent}  bin = s.readByte();")

    println(out, f"{indent}  this.{pf.name} = (bin & {1<<(bool_counter%8)}) != 0;")
    bool_counter += 1

  println(out, f"{indent}  // Non-boolean fields")
  for pf in fields:
    if (not pf.is_list and pf.type == 'bool') or not pf.name:
      continue
    if pf.is_list:
      if pf.type == 'bool':
        println(out, f"{indent}  this.{pf.name} = readListBool(s);")
        continue
      println(out, f"{indent}  this.{pf.name} = new {JAVA_TYPE.get(pf.type, pf.type)}[readSequenceLength(s)];")
      println(out, f"{indent}  for (int i = 0; i < this.{pf.name}.length; ++i) {{")
      if pf.type in JAVA_READER:
        println(out, f"{indent}    this.{pf.name}[i] = {JAVA_READER[pf.type]};")
      elif pf.type in field_is_enum:
        if field_is_enum[pf.type] <= 256:
          println(out, f"{indent}    this.{pf.name}[i] = {pf.type}.valueOf(s.readUnsignedByte());")
        else:
          println(out, f"{indent}    this.{pf.name}[i] = {pf.type}.valueOf(s.readUnsignedShort());")
      else:
        println(out, f"{indent}    {pf.type} obj = new {pf.type}();")
        println(out, f"{indent}    obj.populateData(registry, s);")
        println(out, f"{indent}    this.{pf.name}[i] = obj;")
      println(out, indent + "  }")
    elif pf.type in field_is_enum:
      if field_is_enum[pf.type] <= 256:
        println(out, f"{indent}  this.{pf.name} = {pf.type}.valueOf(s.readUnsignedByte());")
      else:
        println(out, f"{indent}  this.{pf.name} = {pf.type}.valueOf(s.readUnsignedShort());")
    elif pf.type in JAVA_READER:
      println(out, f"{indent}  this.{pf.name} = {JAVA_READER[pf.type]};")
    else:
      println(out, f"{indent}  if (s.readUnsignedByte() > 0) {{")
      println(out, f"{indent}    this.{pf.name} = new {pf.type}();")
      println(out, f"{indent}    this.{pf.name}.populateData(registry, s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceFieldsToString(out, name, fields, indent):
  println(out)
  produceDocstring(out, indent, ["Internal helper method for toString()", "@param sb builder to write the fields and their values"])
  println(out, indent + "@Override")
  println(out, indent + "public void fieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for pf in fields:
    if not pf.name:
      continue
    fn = "appendIfNotEmptyUnsigned" if pf.type in UNSIGNED_TYPE else "appendIfNotEmpty"
    if pf.is_list:
      println(out, f'{indent}  {fn}(sb, "{pf.name}", "{pf.type}", {pf.name});')
    else:
      println(out, f'{indent}  {fn}(sb, "{pf.name}", {pf.name});')

  println(out, indent + "}")


def produceConvertAll(out, name, converts, indent):
  if not converts:
    return
  println(out)
  produceDocstring(out, indent,
    [
      "{@inheritDoc}"
    ]
  )
  println(out, f"{indent}public java.util.List<? extends BluePacket> convert()")
  println(out, indent + "{")
  println(out, indent + "  return java.util.List.of(")
  println(out, f"{indent}    " + ", ".join("new " + c + "()" for c in converts))
  println(out, indent + "  );")
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
  println(out, indent + f"  return new {name}()")

  for pf in other_fields:
    if pf.name:
      println(out, f"{indent}      .set{pf.name[0].upper()}{pf.name[1:]}(other.{pf.name})")

  println(out, indent + "  ;")
  println(out, indent + "}")


def exportInnerEnum(out, data, indent0):
  println(out)
  produceDocstring(out, indent0, data.docstring)
  println(out, f"{indent0}public enum {data.name}")
  println(out, f"{indent0}{{")
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
      for line in pf.docstring:
        out.write(indent)
        out.write("// ")
        out.write(line)
        out.write("\n")
  println(out, f"{indent0};")
  println(out)
  println(out, f"{indent}private static java.util.Map<Integer, {data.name}> map = new java.util.HashMap<>();")
  println(out, f"{indent}static {{")
  println(out, f"{indent}  for ({data.name} en : {data.name}.values()) map.put(en.ordinal(), en);")
  println(out, f"{indent}}}")
  println(out)
  produceDocstring(out, indent, ["Helper to lookup enum.", "@param v ordinal value ", "@return enum type value"])
  println(out, f"{indent}public static {data.name} valueOf(int v) {{ return map.get(v); }}")
  println(out, f"{indent0}}}")


def exportInnerClass(out, data, field_is_enum):
  println(out)
  produceDocstring(out, DEFAULT_INDENT, data.docstring)
  println(out, f"{DEFAULT_INDENT}public static class {data.name}")
  println(out, f"{DEFAULT_INDENT}extends BluePacket")
  println(out, DEFAULT_INDENT + "{")

  println(out, INNER_INDENT + "/* --- DATA FIELDS --- */")
  println(out)
  produceFields(out, data.fields, field_is_enum, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "/* --- HELPER FUNCTIONS --- */")
  sorted_fields = list(sorted(data.fields, key=str))
  produceSetters(out, data.name, sorted_fields, INNER_INDENT)
  produceGetters(out, data.name, sorted_fields, INNER_INDENT)
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, package, data, version, all_data):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    produceDocstring(out, "", data.docstring)
    println(out, f"public final class {data.name}")
    println(out,  "extends BluePacket")
    if data.abstracts:
      println(out,  "implements " + ", ".join(data.abstracts))
    println(out,  "{")
    produceDocstring(out, "  ", ["Internal method to get the hash version number of this packet.", "@return version hash"])
    println(out,  "  @Override")
    println(out, f"  public long getPacketHash() {{ return {version}L; }}")
    println(out)
    produceDocstring(out, "  ", ["Internal method to get the hash version number of this packet.", "@return version hash hexadecimal"])
    println(out,  "  @Override")
    println(out, f'  public String getPacketHex() {{ return "0x{version & 0xFFFFFFFFFFFFFFFF:0X}"; }}')
    println(out)

    println(out, DEFAULT_INDENT + "/* --- DATA FIELDS --- */")
    println(out)
    produceFields(out, data.fields, data.field_is_enum, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "/* --- HELPER FUNCTIONS --- */")
    sorted_fields = list(sorted(data.fields, key=str))
    produceSetters(out, data.name, sorted_fields, DEFAULT_INDENT)
    produceGetters(out, data.name, sorted_fields, DEFAULT_INDENT)
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT)
    produceConvertAll(out, data.name, data.converts, DEFAULT_INDENT)
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
      exportInnerEnum(out, x, "  ")

    println(out, "}")


def exportEnum(out_dir, package, data):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)
    exportInnerEnum(out, data, "")


def exportAbstract(out_dir, package, data):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket abstract", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)
    println(out)
    produceDocstring(out, "", data.docstring)
    println(out, f"interface {data.name}")
    println(out, "{}")


def exportApiVersion(out_dir, package, api_version):
  path = os.path.join(out_dir, "BluePacketAPI.java")
  print("[ExporterJava] API Version", path, file=sys.stderr)
  with open(path, "w") as out:
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "package " + package + ';')
    println(out)
    produceDocstring(out, "", ["API information for this package."])
    println(out, "public final class BluePacketAPI {")
    produceDocstring(out, "  ", ["API Version calculated for all the packets in this package."])
    println(out, f"  public final static long version = {api_version}L;")
    println(out, f'  public final static String versionHex = "0x{api_version & 0xFFFFFFFFFFFFFFFF:0X}";')
    println(out, "}")


def get_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--output_dir', help='Directory where the sources will be generated')
  parser.add_argument('--package', help='Java package for the generated classes')
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
      exportEnum(args.output_dir, args.package, data)
    elif data.is_abstract:
      exportAbstract(args.output_dir, args.package, data)
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, args.package, data, version, all_data)
  exportApiVersion(args.output_dir, args.package, p.api_version)
