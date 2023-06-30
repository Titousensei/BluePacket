#! /usr/bin/env python3
import argparse
import os, sys

from libexport import Parser, println, versionHash

DEFAULT_INDENT = "  "
INNER_INDENT = DEFAULT_INDENT + "  "

JAVA_TYPE = {
  "bool": "boolean",
  "ubyte": "byte",
  "ushort": "short",
  "string": "String",
}

SIGNED_TYPE = { "byte", "short" }
UNSIGNED_TYPE = { "ubyte", "ushort" }

JAVA_WRITER = {
  "bool":   "s.writeBoolean(",
  "byte":   "s.writeByte(",
  "double": "s.writeDouble(",
  "float":  "s.writeFloat(",
  "int":    "s.writeInt(",
  "long":   "s.writeLong(",
  "short":  "s.writeShort(",
  "string": "writeString(s, ",
  "ubyte":  "s.writeByte(",
  "ushort": "s.writeShort(",
}

JAVA_READER = {
  "bool":   "s.readBoolean()",
  "byte":   "s.readByte()",
  "double": "s.readDouble()",
  "float":  "s.readFloat()",
  "int":    "s.readInt()",
  "long":   "s.readLong()",
  "short":  "s.readShort()",
  "string": "readString(s)",
  "ubyte":  "s.readByte()",
  "ushort": "s.readShort()",
}


def header(out, package, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "package " + package + ';')
    println(out)
    if not data.is_enum:
      println(out, "import java.util.Collection;")
      println(out, "import org.bluepacket.network.BluePacket;")
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


def produceFields(out, fields, indent):
  for fname, ftype, opt, docstring in fields:
    ftype = JAVA_TYPE.get(ftype, ftype)
    if opt == 'list':
      produceDocstring(out, indent, docstring)
      println(out, f"{indent}public {ftype}[] {fname};")
    elif fname:
      produceDocstring(out, indent, docstring)
      println(out, f"{indent}public {ftype} {fname};")
    elif docstring:
      for line in docstring:
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
  for fname, ftype, opt, _ in fields:
    if not fname:
      continue

    ftype = JAVA_TYPE.get(ftype, ftype)
    if opt == 'list':
      produceListSetters(out, name, fname, ftype, indent)
    else:
      produceDocstring(out, indent, [f"Chaining setter for {fname}.", "@param val value", "@return this"])
      out.write(f"{indent}public {name} set{fname[0].upper()}{fname[1:]}")
      out.write(f"({ftype} val)")
      println(out, f" {{ {fname} = val; return this; }}")


def produceGetters(out, name, fields, indent):
  println(out)
  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      continue

    if ftype in UNSIGNED_TYPE:
      produceDocstring(out, indent, [f"Getter for {fname} unsigned as an int.", "@return unsigned value as int"])
      out.write(f"{indent}public int get{fname[0].upper()}{fname[1:]}AsInt()")
      println(out, f" {{ return unsigned({fname}); }}")
    elif ftype in SIGNED_TYPE:
      produceDocstring(out, indent, [f"Getter for {fname} signed as an int.", "@return signed value as int"])
      out.write(f"{indent}public int get{fname[0].upper()}{fname[1:]}AsInt()")
      println(out, f" {{ return {fname}; }}")


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to serialize to bytes", "@param s stream to write the bytes to"])
  println(out, indent + "@Override")
  println(out, indent + "public void serializeData(java.io.DataOutputStream s)")
  println(out, indent + "throws java.io.IOException")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f"{indent}  writeArray(s, {fname});")
    elif ftype in field_is_enum:
      println(out, f"{indent}  s.writeByte({fname} == null ? 0 : {fname}.ordinal());")
    elif ftype in JAVA_WRITER:
      println(out, f"{indent}  {JAVA_WRITER[ftype]}{fname});")
    else:
      println(out, f"{indent}  if ({fname} == null) s.writeByte(0);")
      println(out, f"{indent}  else {{")
      println(out, f"{indent}    s.writeByte(1);")
      println(out, f"{indent}    {fname}.serializeData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceDeserializer(out, name, fields, indent, field_is_enum):
  println(out)
  produceDocstring(out, indent, ["Internal method to deserialize from bytes into this object fields", "@param s stream to read the bytes from"])
  println(out, indent + "@Override")
  println(out, indent + "public void populateData(java.io.DataInputStream s)")
  println(out, indent + "throws java.io.IOException")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' in opt:
      println(out, f"{indent}  {fname} = new {JAVA_TYPE.get(ftype, ftype)}[readSequenceLength(s)];")
      println(out, f"{indent}  for (int i = 0; i < {fname}.length; ++i) {{")
      if ftype in JAVA_READER:
        println(out, f"{indent}    {fname}[i] = {JAVA_READER[ftype]};")
      elif ftype in field_is_enum:
        println(out, f"{indent}    {fname}[i] = {ftype}.valueOf(s.readUnsignedByte());")
      else:
        println(out, f"{indent}    {ftype} obj = new {ftype}();")
        println(out, f"{indent}    obj.populateData(s);")
        println(out, f"{indent}    {fname}[i] = obj;")
      println(out, indent + "  }")
    elif ftype in field_is_enum:
      println(out, f"{indent}  {fname} = {ftype}.valueOf(s.readUnsignedByte());")
    elif ftype in JAVA_READER:
      println(out, f"{indent}  {fname} = {JAVA_READER[ftype]};")
    else:
      println(out, f"{indent}  if (s.readUnsignedByte() > 0) {{")
      println(out, f"{indent}    {fname} = new {ftype}();")
      println(out, f"{indent}    {fname}.populateData(s);")
      println(out, indent + "  }")

  println(out, indent + "}")


def produceFieldsToString(out, name, fields, indent):
  println(out)
  produceDocstring(out, indent, ["Internal helper method for toString()", "@param sb builder to write the fields and their values"])
  println(out, indent + "@Override")
  println(out, indent + "public void fieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    fn = "appendIfNotEmptyUnsigned" if ftype in UNSIGNED_TYPE else "appendIfNotEmpty"
    if 'list' not in opt:
      println(out, f'{indent}  {fn}(sb, "{fname}", {fname});')
    else:
      println(out, f'{indent}  {fn}(sb, "{fname}", "{ftype}", {fname});')

  println(out, indent + "}")


def exportInnerEnum(out, data, indent0):
  println(out)
  produceDocstring(out, indent0, data.docstring)
  println(out, f"{indent0}public enum {data.name}")
  println(out, f"{indent0}{{")
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
      for line in docstring:
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
  produceFields(out, data.fields, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "/* --- HELPER FUNCTIONS --- */")
  sorted_fields = list(sorted(data.fields))
  produceSetters(out, data.name, sorted_fields, INNER_INDENT)
  produceGetters(out, data.name, sorted_fields, INNER_INDENT)
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, package, data, version):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    produceDocstring(out, "", data.docstring)
    println(out, f"public final class {data.name}")
    println(out,  "extends BluePacket")
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
    produceFields(out, data.fields, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "/* --- HELPER FUNCTIONS --- */")
    sorted_fields = list(sorted(data.fields))
    produceSetters(out, data.name, sorted_fields, DEFAULT_INDENT)
    produceGetters(out, data.name, sorted_fields, DEFAULT_INDENT)
    produceSerializer(out, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceDeserializer(out, data.name, sorted_fields, DEFAULT_INDENT, data.field_is_enum)
    produceFieldsToString(out, data.name, sorted_fields, DEFAULT_INDENT)

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
    else:
      version = versionHash(data, all_data)
      exportClass(args.output_dir, args.package, data, version)
