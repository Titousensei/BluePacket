#! /usr/bin/env python3
import os, sys

from hashlib import md5
from struct import unpack

PRIMITIVE_TYPES = {
  "bool", "byte", "double", "float", "int", "long", "packet", "short", "string", "ubyte", "ushort"
}

FORBIDDEN_NAMES = {
  "bool", "boolean", "byte",
  "char", "class",
  "decimal", "double", "dynamic",
  "float",
  "import", "int",
  "list",
  "long",
  "nint", "nuint",
  "object",
  "package",
  "sbyte", "short", "static", "string",
  "uint", "ulong", "ushort",
  "int8", "int16", "int32", "int64",
  "uint8", "uint16", "uint32", "uint64", "uintptr",
  "rune",
  "float32", "float64",
  "complex64", "complex128",
}

MARKER_DEPRECATED = "__"
# golang might use: U+0394     GREEK CAPITAL LETTER DELTA     Δ

class SourceException(Exception):
  def __init__(self, message, what=None, filename=None, line_number=0):
    self.message = message
    self.what = what
    self.filename = filename
    self.line_number = line_number

  def __str__(self):
    if self.what:
      return self.message + ": " + self.what
    else:
      return self.message


class PacketData:
  def __init__(self):
    self.name = None
    self.docstring = []
    self.version = None
    self.is_enum = False
    self.origin_name = None
    self.indent: 0
    # format: [name?, type?, 'list'|'', [doc*]]
    self.fields = []
    self.inner = {}
    self.enums = {}
    self.field_is_enum = {}
    self.field_names = set()

  def __repr__(self):
    return f"{{{self.origin_name}/{'E' if self.is_enum else 'C'} F={self.fields} C{list(self.inner.values())} E{list(self.enums.values())} D{self.docstring}}}"


def println(out, line=''):
  out.write(line)
  out.write(os.linesep)


def _mergeUniquely(a, b, msg):
  overlap = a.keys() & b.keys()
  if overlap:
    raise SourceException(f"Duplicate definition of in {msg}", what=", ".join(sorted(overlap)))
  ret = {}
  ret.update(a)
  ret.update(b)
  return ret


def versionString(data, all_data, my_enums, my_inner, seen):
  ret = data.origin_name or data.name
  if data.name not in PRIMITIVE_TYPES:
    seen.add(data.name)
  if data.name in all_data:
    my_inner = _mergeUniquely(my_inner, all_data[data.name].inner, data.name)
    my_enums = _mergeUniquely(my_enums, all_data[data.name].enums, data.name)
  for fname, ftype, *opt in sorted(data.fields):
    if not fname:
      continue
    # un-deprecate
    fname, *_ = fname.split(MARKER_DEPRECATED)

    ret += f"+{fname}:"
    if ftype in seen:
      ary = "[]" if 'list' in opt else ""
      ret += f"{{{ary}{ftype}+...}}"
      continue
    if 'list' in opt:
      if ftype in my_inner:
        ret += "{[]" + versionString(my_inner[ftype], all_data, my_enums, my_inner, seen) + "}"
      elif ftype in data.field_is_enum:
        if ftype in my_enums:
          ret += f"[]{{{ftype}+" + "+".join(f for f, *_ in my_enums[ftype].fields if f) + "}"
        elif ftype in all_data:
          ret += f"[]{{{ftype}+" + "+".join(f for f, *_ in all_data[ftype].fields if f) + "}"
        else:
          raise Exception(f"Unknown enum type in {ftype} {fname} in {ret}")
      elif ftype in all_data:
        ret += "{[]" + versionString(all_data[ftype], all_data, my_enums, my_inner, seen) + "}"
      elif ftype in PRIMITIVE_TYPES:
        ret += "[]" + ftype
      else:
        # Should never happen, but we raise in case of a bug in this lib
        raise SourceException("Unexpected: Unknown list field type", what=f"list {ftype} {fname}")
    elif ftype in data.field_is_enum:
      if ftype in my_enums:
        ret += f"{{{ftype}+" + "+".join(f for f, *_ in my_enums[ftype].fields if f) + "}"
      elif ftype in all_data:
        ret += f"{{{ftype}+" + "+".join(f for f, *_ in all_data[ftype].fields if f) + "}"
      else:
        # Should never happen, but we raise in case of a bug in this lib
        raise SourceException("Unexpected: Unknown enum type", what=f"{ftype} {fname}")
    elif ftype in PRIMITIVE_TYPES:
        ret += ftype
    elif ftype in my_inner:
        ret += "{" + versionString(my_inner[ftype], all_data, my_enums, my_inner, seen) + "}"
    elif ftype in my_enums:
        ret += f"{{{ftype}+" + "+".join(my_enums[ftype].fields) + "}"
    elif ftype in all_data:
        ret += "{" + versionString(all_data[ftype], all_data, my_enums, my_inner, seen) + "}"
    elif not data.is_enum:
      # Should never happen, but we raise in case of a bug in this lib
      raise SourceException("Unexpected: Unknown field type", what=f"{ftype} {fname}")
  return ret


def versionHash(data, all_data, prefix=""):
  s = prefix+versionString(data, all_data, {}, {}, set())
  h = md5(s.encode("utf-8"))
  ret, _ = unpack("!2q", h.digest())
  return ret


class Parser:
  def __init__(self):
    self.packet_list = {}
    self.data = None
    self.indent = 0
    self.state = None
    self.top = None

  def read_enums(self, line, indent, docstring):
    if indent == 0 or ':' in line:
      self.read_class(line, indent, docstring)
      return

    for en in line.strip().split(','):
      en = en.strip()
      if en in self.data.field_names:
        raise SourceException(f"Duplicate enum value", what=f"{self.data.name}.{en}")
      self.data.fields.append([en, '', '', docstring])
      docstring = []
      self.data.field_names.add(en)

  def read_field(self, line, indent, docstring):
    if indent == 0 or ':' in line:
      if self.data.fields[-1][1] == '':
        self.data.fields.pop()
      self.read_class(line, indent, docstring)
      return

    line_info, *line_extra = line.strip().split('#', 1)
    info = line_info.split()[::-1]
    if info[1] == "String":
      raise SourceException("Forbidden fields type 'String': should be 'string' (lowercase)", what=info[1] + ' ' + info[0])
    elif line_extra:
      raise SourceException("Forbidden field inline comment", what=line_extra[0].strip())
    elif info[1][0].islower() and info[1] not in PRIMITIVE_TYPES:
      raise SourceException("Unknown primitive field type", what=info[1] + ' ' + info[0])
    elif info[0] in self.data.field_names:
      raise SourceException("Duplicate field name", what=f"{self.data.name}.{info[0]}")
    elif info[0] in FORBIDDEN_NAMES:
      raise SourceException("Field name can't be reserved keyword", what=info[1] + ' ' + info[0])
    if len(info) == 2:
      info.append('')
    info.append(docstring)
    self.data.fields.append(info)
    self.data.field_names.add(info[0])

  def read_class(self, line, indent, docstring):
    current = self.data
    self.data = PacketData()
    self.data.docstring = docstring
    if indent == 0:
      self.top = self.top or self.data

    name, option = (x.strip() for x in line.split(':'))
    self.data.name = name

    self.data.origin_name, *_ = name.split(MARKER_DEPRECATED)

    if indent == 0:
      if name in self.packet_list:
        raise SourceException("Duplicate Packet name", what=name)
      self.packet_list[name] = self.data
      self.top = self.data
    elif option == "enum":
      self.top.enums[name] = self.data
    else:
      self.top.inner[name] = self.data

    if option == "enum":
      self.state = self.read_enums
      self.data.is_enum = True
    else:
      self.state = self.read_field

  def parse(self, files, annotations=None):
    for path in files:
      print("[Export] Reading", path, file=sys.stderr)
      with open(path) as f:
        self.state = self.read_class
        docstring = []
        for lnum, line in enumerate(f, 1):
          if annotations is not None and line.startswith('# @'):
            _, key, value = line.strip().split(' ', 2)
            annotations[key] = value.strip()
            continue

          if line.startswith('#'):
            docstring.append(line[1:].strip())
            continue

          sline = line.strip()
          if not sline:
            if docstring and self.data:
              self.data.fields.append(['', '', '', docstring])
            docstring = []
            continue

          if sline.startswith('#'):
            docstring.append(sline[1:].strip())
            continue

          try:
            indent = len(line) - len(line.lstrip())
            self.state(line, indent, docstring)
            docstring = []
          except SourceException as ex:
            ex.filename = path
            ex.line_number = lnum
            raise ex
          except Exception as ex:
            raise SourceException(''.join(ex.args), filename=path, line_number=lnum)

    deprecated = {}
    for _, data in self.packet_list.items():
        if data.origin_name == data.name:
            continue
        version = versionHash(data, self.packet_list)
        hexname = f"{data.origin_name}__{version & 0xFFFFFFFFFFFFFFFF:0X}"
        if data.name != hexname:
          raise SourceException(
            "Deprecated packet named with wrong hex version",
            what=data.name + ' should be ' + hexname,
            filename=path,
          )
        if data.origin_name in deprecated:
            deprecated[data.origin_name].add(data.name)
        else:
            deprecated[data.origin_name] = {data.name}

    # verify fields: enum type, deprecated
    for _, data in self.packet_list.items():
      inner_enums = {en.name for en in data.enums.values()}
      for fname, ftype, *_ in data.fields:
        if ftype in deprecated and data.origin_name not in deprecated:
          raise SourceException(
              "Packet has field potentially deprecated but does not have its own deprecated version",
              what=ftype + ' ' + fname,
              filename=path,
          )
        if ftype in inner_enums or (ftype in self.packet_list and self.packet_list[ftype].is_enum):
          en = self.packet_list.get(ftype) or data.enums.get(ftype)
          data.field_is_enum[ftype] = sum(1 for f in en.fields if f[0])
      for inner in data.inner.values():
        for _, ftype, *_ in inner.fields:
          if ftype in inner_enums or (ftype in self.packet_list and self.packet_list[ftype].is_enum):
            en = self.packet_list.get(ftype) or data.enums.get(ftype)
            data.field_is_enum[ftype] = sum(1 for f in en.fields if f[0])

    if not data.is_enum:
        data.version = versionHash(data, self.packet_list)

    return self.packet_list


if __name__ == "__main__":
  p = Parser()
  all_data = p.parse(sys.argv[1:])
  for _, data in all_data.items():
    if data.is_enum:
      print(data)
    else:
      print(versionString(data, all_data))
