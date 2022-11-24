#! /usr/bin/env python3
import os, sys

from hashlib import md5
from struct import unpack

PRIMITIVE_TYPES = {
  "bool", "byte", "double", "float", "int", "long", "short", "string"
}

class PacketData:
  def __init__(self):
    self.name = None
    self.is_enum = False
    self.indent: 0
    self.fields = []
    self.inner = {}
    self.enums = {}
    self.field_is_enum = set()

  def __repr__(self):
    return f"{{{self.name}/{'E' if self.is_enum else 'C'} F={self.fields} C{list(self.inner.values())} E{list(self.enums.values())}}}"


def println(out, line=''):
  out.write(line)
  out.write(os.linesep)


def _mergeUniquely(a, b, msg):
  overlap = a.keys() & b.keys()
  if overlap:
    raise Exception(f"Duplicate definition of in {msg}: " + ", ".join(overlap))
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
        raise Exception(f"Unknown list field type in {ftype} {fname} in {ret}")
    elif ftype in data.field_is_enum:
      if ftype in my_enums:
        ret += f"{{{ftype}+" + "+".join(my_enums[ftype].fields) + "}"
      elif ftype in all_data:
        ret += f"{{{ftype}+" + "+".join(all_data[ftype].fields) + "}"
      else:
        raise Exception(f"Unknown enum type in {ftype} {fname} in {ret}")
    elif ftype in PRIMITIVE_TYPES:
        ret += ftype
    elif ftype in my_inner:
        ret += "{" + versionString(my_inner[ftype], all_data, my_enums, my_inner, seen) + "}"
    elif ftype in my_enums:
        ret += f"{{{ftype}+" + "+".join(my_enums[ftype].fields) + "}"
    elif ftype in all_data:
        ret += "{" + versionString(all_data[ftype], all_data, my_enums, my_inner, seen) + "}"
    elif not data.is_enum:
      raise Exception(f"Unknown field type in {ftype} {fname} in {ret}")
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
      self.data.fields.append(en.strip())

  def read_field(self, line, indent):
    if indent == 0 or ':' in line:
      self.read_class(line, indent)
      return

    info = line.strip().split()[::-1]
    if info[1] == "String":
      raise Exception(f"Forbidden fields type  'String': should be 'string' (lowercase)")
    elif info[1][0].islower() and info[1] not in PRIMITIVE_TYPES:
      raise Exception(f"Unknown primitive field type: {info[1]} {info[0]}")
    self.data.fields.append(info)

  def read_class(self, line, indent):
    current = self.data
    self.data = PacketData()
    if indent == 0:
      self.top = self.top or self.data

    name, option = (x.strip() for x in line.split(':'))
    self.data.name = name

    if indent == 0:
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

  def parse(self, files):
    for path in files:
      print("[Export] Reading", path, file=sys.stderr)
      with open(path) as f:
        self.state = self.read_class
        for lnum, line in enumerate(f, 1):
          sline = line.strip()
          if not sline or sline.startswith('#'):
            if not self.data.is_enum:
              self.data.fields.append(['', sline, None])
            continue
          try:
            indent = len(line) - len(line.lstrip())
            self.state(line, indent)
          except Exception as ex:
            raise Exception(f"Error at {path}:{lnum} - {''.join(ex.args)}")

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
