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

JAVA_TYPE = {
  "bool": "boolean",
  "string": "String",
}

JAVA_WRITER = {
  "bool":   "s.writeBoolean(",
  "byte":   "s.writeByte(",
  "double": "s.writeDouble(",
  "float":  "s.writeFloat(",
  "int":    "s.writeInt(",
  "long":   "s.writeLong(",
  "short":  "s.writeShort(",
  "string": "writeString(s, ",
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
}


def header(out, package, data):
    println(out, "// WARNING: Auto-generated class - do not edit - any change will be overwritten and lost")
    println(out, "package " + package + ';')
    println(out)
    if not data.is_enum:
      println(out, "import org.bluesaga.network.BluePacket;")
      println(out, "import java.util.Arrays;")
      println(out)


def produceFields(out, fields, indent):
  for fname, ftype, *opt in fields:
    if fname in FORBIDDEN_NAMES:
      raise Exception(f"Fields name can't be Java reserved keywords: {ftype} {fname}")
    ftype = JAVA_TYPE.get(ftype, ftype)
    if 'list' in opt:
      println(out, f"{indent}public {ftype}[] {fname};")
    elif fname:
      println(out, f"{indent}public {ftype} {fname};")
    elif ftype.startswith('#'):
      println(out, indent + "//" + ftype[1:])
    else:
      println(out)


def produceSetters(out, name, fields, indent):
  println(out)
  for fname, ftype, *opt in fields:
    if not fname:
      continue
    out.write(f"{indent}public {name} set{fname[0].upper()}{fname[1:]}")
    ftype = JAVA_TYPE.get(ftype, ftype)
    if 'list' in opt:
      out.write(f"({ftype}[] val)")
    else:
      out.write(f"({ftype} val)")
    println(out, f" {{ {fname} = val; return this; }}")


def produceSerializer(out, fields, indent, field_is_enum):
  println(out)
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
  println(out, indent + "@Override")
  println(out, indent + "public void fieldsToString(StringBuilder sb)")
  println(out, indent + "{")

  for fname, ftype, *opt in fields:
    if not fname:
      continue
    if 'list' not in opt:
      println(out, f'{indent}  appendIfNotEmpty(sb, "{fname}", {fname});')
    else:
      println(out, f'{indent}  appendIfNotEmpty(sb, "{fname}", "{ftype}", {fname});')

  println(out, indent + "}")


def exportInnerEnum(out, data):
  println(out)
  println(out, f"  public enum {data.name}")
  println(out,  "{")
  sep =  "    "
  for f in data.fields:
    out.write(sep)
    sep = ", "
    out.write(f)
  println(out, ";")
  println(out)
  println(out, f"    private static java.util.Map<Integer, {data.name}> map = new java.util.HashMap<>();")
  println(out,  "    static {")
  println(out, f"      for ({data.name} en : {data.name}.values()) map.put(en.ordinal(), en);")
  println(out,  "    }")
  println(out, f"    public static {data.name} valueOf(int v) {{ return map.get(v); }}")
  println(out,  "  }")


def exportInnerClass(out, data, field_is_enum):
  println(out)
  println(out, f"{DEFAULT_INDENT}public static class {data.name}")
  println(out, f"{DEFAULT_INDENT}extends BluePacket")
  println(out, DEFAULT_INDENT + "{")

  println(out, INNER_INDENT + "/*** DATA FIELDS ***/")
  println(out)
  produceFields(out, data.fields, INNER_INDENT)
  println(out)
  println(out, INNER_INDENT + "/*** HELPER FUNCTIONS ***/")
  sorted_fields = list(sorted(data.fields))
  produceSetters(out, data.name, sorted_fields, INNER_INDENT)
  produceSerializer(out, sorted_fields, INNER_INDENT, field_is_enum)
  produceDeserializer(out, data.name, sorted_fields, INNER_INDENT, field_is_enum)
  produceFieldsToString(out, data.name, sorted_fields, INNER_INDENT)

  println(out, DEFAULT_INDENT + "}")


def exportClass(out_dir, package, data, version):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket class", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    println(out, f"public final class {data.name}")
    println(out,  "extends BluePacket")
    println(out,  "{")
    println(out,  "  @Override")
    println(out, f"  public long getPacketHash() {{ return {version}L; }}")
    println(out)

    println(out, DEFAULT_INDENT + "/*** DATA FIELDS ***/")
    println(out)
    produceFields(out, data.fields, DEFAULT_INDENT)
    println(out)
    println(out, DEFAULT_INDENT + "/*** HELPER FUNCTIONS ***/")
    sorted_fields = list(sorted(data.fields))
    produceSetters(out, data.name, sorted_fields, DEFAULT_INDENT)
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

    println(out, "}")


def exportEnum(out_dir, package, data):
  path = os.path.join(out_dir, data.name + ".java")
  print("[ExporterJava] BluePacket enum", path, file=sys.stderr)
  with open(path, "w") as out:
    header(out, package, data)

    println(out, f"public enum {data.name}")
    println(out,  "{")
    sep =  "  "
    for f in data.fields:
      out.write(sep)
      sep = ", "
      out.write(f)
    println(out, ";")
    println(out)
    println(out, f"  private static java.util.Map<Integer, {data.name}> map = new java.util.HashMap<>();")
    println(out,  "  static {")
    println(out, f"    for ({data.name} en : {data.name}.values()) map.put(en.ordinal(), en);")
    println(out,  "  }")
    println(out, f"  public static {data.name} valueOf(int v) {{ return map.get(v); }}")
    println(out,  "}")


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
