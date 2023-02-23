#! /usr/bin/env python3
import os, sys

from hashlib import md5
from struct import unpack

PRIMITIVE_TYPES = {
  "bool", "byte", "double", "float", "int", "long", "short", "string", "ubyte", "ushort"
}

FORBIDDEN_NAMES = {
  "bool", "boolean", "byte",
  "char", "class",
  "decimal", "double", "dynamic",
  "float",
  "import", "int",
  "long",
  "nint", "nuint",
  "object",
  "package",
  "sbyte", "short", "static", "string",
  "uint", "ulong", "ushort",
}


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
    self.is_enum = False
    self.indent: 0
    self.fields = []
    self.inner = {}
    self.enums = {}
    self.field_is_enum = set()
    self.field_names = set()

  def __repr__(self):
    return f"{{{self.name}/{'E' if self.is_enum else 'C'} F={self.fields} C{list(self.inner.values())} E{list(self.enums.values())}}}"


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
  ret = data.name
  if data.name not in PRIMITIVE_TYPES:
    seen.add(data.name)
  if data.name in all_data:
    my_inner = _mergeUniquely(my_inner, all_data[data.name].inner, data.name)
    my_enums = _mergeUniquely(my_enums, all_data[data.name].enums, data.name)
  for fname, ftype, *opt in sorted(data.fields):
    if not fname:
      continue
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
          ret += f"[]{{{ftype}+" + "+".join(my_enums[ftype].fields) + "}"
        elif ftype in all_data:
          ret += f"[]{{{ftype}+" + "+".join(all_data[ftype].fields) + "}"
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
        ret += f"{{{ftype}+" + "+".join(my_enums[ftype].fields) + "}"
      elif ftype in all_data:
        ret += f"{{{ftype}+" + "+".join(all_data[ftype].fields) + "}"
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

  def read_enums(self, line, indent):
    if indent == 0 or ':' in line:
      self.read_class(line, indent)
      return

    for en in line.strip().split(','):
      en = en.strip()
      if en in self.data.field_names:
        raise SourceException(f"Duplicate enum value", what=f"{self.data.name}.{en}")
      self.data.fields.append(en)
      self.data.field_names.add(en)

  def read_field(self, line, indent):
    if indent == 0 or ':' in line:
      if self.data.fields[-1][1] == '':
        self.data.fields.pop()
      self.read_class(line, indent)
      return

    info = line.strip().split()[::-1]
    if info[1] == "String":
      raise SourceException("Forbidden fields type  'String': should be 'string' (lowercase)", what=info[1] + ' ' + info[0])
    elif info[1][0].islower() and info[1] not in PRIMITIVE_TYPES:
      raise SourceException("Unknown primitive field type", what=info[1] + ' ' + info[0])
    elif info[0] in self.data.field_names:
      raise SourceException("Duplicate field name", what=f"{self.data.name}.{info[0]}")
    elif info[0] in FORBIDDEN_NAMES:
      raise SourceException("Field name can't be reserved keyword", what=info[1] + ' ' + info[0])
    self.data.fields.append(info)
    self.data.field_names.add(info[0])

  def read_class(self, line, indent):
    current = self.data
    self.data = PacketData()
    if indent == 0:
      self.top = self.top or self.data

    name, option = (x.strip() for x in line.split(':'))
    self.data.name = name

    if indent == 0:
      if name in self.packet_list:
        raise SourceException("Duplicate Packet name", what=name)
      self.packet_list[name] = self.data
      self.top = self.data
    elif option == "enum":
      self.top.enums[self.data.name] = self.data
    else:
      self.top.inner[self.data.name] = self.data

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
        for lnum, line in enumerate(f, 1):
          sline = line.strip()
          if annotations is not None and sline.startswith('# @'):
            _, key, value = sline.split(' ', 2)
            annotations[key] = value
            continue
          if not sline or sline.startswith('#'):
            if self.data and not self.data.is_enum and (sline or self.data.fields[-1][1] != ''):
                self.data.fields.append(['', sline, None])
            continue
          try:
            indent = len(line) - len(line.lstrip())
            self.state(line, indent)
          except SourceException as ex:
            ex.filename = path
            ex.line_number = lnum
            raise ex
          except Exception as ex:
            raise SourceException(''.join(ex.args), filename=path, line_number=lnum)

    #find all enum type fields
    for _, data in self.packet_list.items():
      inner_enums = {en.name for en in data.enums.values()}
      for _, ftype, *_ in data.fields:
        if ftype in inner_enums or (ftype in self.packet_list and self.packet_list[ftype].is_enum):
          data.field_is_enum.add(ftype)
      for inner in data.inner.values():
        for _, ftype, *_ in inner.fields:
          if ftype in inner_enums or (ftype in self.packet_list and self.packet_list[ftype].is_enum):
            data.field_is_enum.add(ftype)

    return self.packet_list


if __name__ == "__main__":
  p = Parser()
  all_data = p.parse(sys.argv[1:])
  for _, data in all_data.items():
    if data.is_enum:
      print(data)
    else:
      print(versionString(data, all_data))
