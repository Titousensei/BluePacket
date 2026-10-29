#! /usr/bin/env python3
import ast, json, math, os, re, sys

from hashlib import md5
from struct import unpack

PRIMITIVE_TYPES = {
  "bool", "byte", "double", "float", "int", "long", "packet", "short", "string", "ubyte", "ushort"
}

LIST_LABEL = "list"
CONVERT_LABEL = "convert"

CONVERT_COPY = "<-"
CONVERT_WIDEN = "<="
CONVERT_FORCE = "<!"
CONVERT_CONST = "="
CONVERT_IGNORE = "_"

SCALAR_CONVERT_TYPES = {
  "bool", "byte", "ubyte", "short", "ushort", "int", "long", "float", "double", "string",
}

INT_RANGES = {
  "byte": (-(2 ** 7), 2 ** 7 - 1),
  "ubyte": (0, 2 ** 8 - 1),
  "short": (-(2 ** 15), 2 ** 15 - 1),
  "ushort": (0, 2 ** 16 - 1),
  "int": (-(2 ** 31), 2 ** 31 - 1),
  "long": (-(2 ** 63), 2 ** 63 - 1),
}

# Widening that never loses value or precision.
SAFE_WIDENING = {
  "byte": {"short", "int", "long", "float", "double"},
  "ubyte": {"short", "ushort", "int", "long", "float", "double"},
  "short": {"int", "long", "float", "double"},
  "ushort": {"int", "long", "float", "double"},
  "int": {"long", "double"},
  "float": {"double"},
}

FORBIDDEN_NAMES = {
  LIST_LABEL, CONVERT_LABEL,
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


class PacketField:
  def __init__(self, name=None, type=None, is_list=False, docstring=None):
    self.name = name
    self.type = type
    self.is_list = is_list
    self.docstring = docstring or []

  def __repr__(self):
    ret = []
    if self.name:
      ret.append("N=" + self.name)
    if self.type:
      ret.append("T=" + self.type)
    if self.is_list:
      ret.append(LIST_LABEL)
    if self.docstring:
      ret.append("D=" + str(self.docstring))
    return " ".join(ret)


class ConvertConstant:
  def __init__(self, kind, value):
    self.kind = kind
    self.value = value

  def __repr__(self):
    if self.kind == "enum":
      qualifier, name = self.value
      return f"{qualifier}.{name}" if qualifier else name
    if self.kind == "string":
      return json.dumps(self.value)
    if self.kind == "bool":
      return "true" if self.value else "false"
    return str(self.value)


class ConvertMapping:
  def __init__(self, target, operator, source=None, constant=None):
    self.target = target
    self.operator = operator
    self.source = source
    self.constant = constant
    # Resolved during convert validation.
    self.target_type = None
    self.source_type = None
    self.target_kind = None
    self.source_kind = None
    self.target_is_list = False
    self.source_is_list = False
    # Field mappings between two enum types that are resolved by the target enum's converter.
    self.enum_convert = False

  def __repr__(self):
    if self.operator == CONVERT_CONST:
      return f"{self.target}{self.operator}{self.constant!r}"
    target = self.target or CONVERT_IGNORE
    return f"{target}{self.operator}{self.source}"


class PacketData:
  def __init__(self):
    self.name = None
    self.docstring = []
    self.version = None
    self.is_enum = False
    self.is_abstract = False
    self.origin_name = None
    self.indent: 0
    # format: [name?, type?, 'list'|'', [doc*]]
    self.fields = []
    self.inner = {}
    self.enums = {}
    self.converts = {}
    self.abstracts = []
    self.field_is_enum = {}
    self.field_names = set()

  def __repr__(self):
    if self.is_enum:
      return f"{{{self.origin_name}/E F={self.fields} D{self.docstring}}}"
    elif self.is_abstract:
      return f"{{{self.origin_name}/A D{self.docstring}}}"
    else:
      abstracts_str = ' A[' + ', '.join(self.abstracts) + ']' if self.abstracts else ''
      converts_str = ""
      if self.converts:
        for ctype, opts in self.converts.items():
          converts_str = f"{converts_str} X[{ctype}]={opts}"
      return f"{{{self.origin_name}/C{abstracts_str} F={self.fields} C{list(self.inner.values())} E{list(self.enums.values())}{converts_str} D{self.docstring}}}"


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


def versionString(data, all_data, my_enums, my_inner, seen_objects, prefix="", salt=""):
  """Generate version string for a packet/enum/inner type.

  Args:
    data: PacketData to generate version string for
    all_data: All top-level packets
    my_enums: Local enums dict (merged from parent)
    my_inner: Local inner types dict (merged from parent)
    seen_objects: Set of id(data) for cycle detection (tracks object identity)
    prefix: Qualified name prefix for the current type (e.g., "Container.PacketA.")
    salt: Optional salt prefix to add before hashing
  """
  # Build fully qualified name for this type
  qualified_name = prefix + (data.origin_name or data.name)
  ret = salt + (data.origin_name or data.name)

  # Cycle detection: track object identity
  data_id = id(data)
  if data_id in seen_objects:
    # This type was already expanded - abbreviate to break cycle
    return f"{{{qualified_name}+...}}"
  seen_objects.add(data_id)

  # Merge inner types and enums from the top-level definition if this is a top-level packet
  if data.name in all_data:
    my_inner = _mergeUniquely(my_inner, all_data[data.name].inner, data.name)
    my_enums = _mergeUniquely(my_enums, all_data[data.name].enums, data.name)

  # New prefix for nested types: add this type's name
  nested_prefix = qualified_name + "."

  for pf in sorted(data.fields, key=str):
    if not pf.name:
      continue
    # un-deprecate
    fname, *_ = pf.name.split(MARKER_DEPRECATED)
    ftype = pf.type

    ret += f"+{fname}:"
    if pf.is_list:
      if ftype in my_inner:
        ret += "{[]" + versionString(my_inner[ftype], all_data, my_enums, my_inner, seen_objects, nested_prefix) + "}"
      elif ftype in data.field_is_enum or ftype in my_enums:
        if ftype in my_enums:
          enum_data = my_enums[ftype]
          ret += f"[]{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
        elif ftype in all_data:
          enum_data = all_data[ftype]
          ret += f"[]{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
        else:
          raise Exception(f"Unknown enum type in {pf.type} {pf.name} in {ret}")
      elif ftype in all_data:
        # Top-level packet: use fresh dicts so it uses its own inner/enums
        ret += "{[]" + versionString(all_data[ftype], all_data, {}, {}, seen_objects, nested_prefix) + "}"
      elif ftype in PRIMITIVE_TYPES:
        ret += "[]" + ftype
      else:
        # Should never happen, but we raise in case of a bug in this lib
        print("*** my_enums", my_enums)
        raise SourceException("Unexpected: Unknown {LIST_LABEL} field type", what=f"{LIST_LABEL} {ftype} {fname}")
    elif ftype in data.field_is_enum:
      if ftype in my_enums:
        enum_data = my_enums[ftype]
        ret += f"{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
      elif ftype in all_data:
        enum_data = all_data[ftype]
        ret += f"{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
      else:
        # Should never happen, but we raise in case of a bug in this lib
        raise SourceException("Unexpected: Unknown enum type", what=f"{ftype} {fname}")
    elif ftype in PRIMITIVE_TYPES:
        ret += ftype
    elif ftype in my_inner:
        ret += "{" + versionString(my_inner[ftype], all_data, my_enums, my_inner, seen_objects, nested_prefix) + "}"
    elif ftype in my_enums:
        enum_data = my_enums[ftype]
        ret += f"{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
    elif ftype in all_data:
        if all_data[ftype].is_enum:
            # Top-level enum: use hash format
            enum_data = all_data[ftype]
            ret += f"{{{ftype}__{enum_data.version & 0xFFFFFFFFFFFFFFFF:0X}}}"
        else:
            # Top-level packet: use fresh dicts so it uses its own inner/enums
            ret += "{" + versionString(all_data[ftype], all_data, {}, {}, seen_objects, nested_prefix) + "}"
    elif not data.is_enum:
      # Should never happen, but we raise in case of a bug in this lib
      raise SourceException("Unexpected: Unknown field type", what=f"{ftype} {fname}")
  return ret


def versionHash(data, all_data, prefix="", salt=""):
  s = prefix+versionString(data, all_data, {}, {}, set(), prefix=salt)
  h = md5(s.encode("utf-8"))
  ret, _ = unpack("!2q", h.digest())
  return ret


def _splitComment(line):
  """Split a line at the first '#' that is not inside a quoted string."""
  quote = None
  escaped = False
  for i, char in enumerate(line):
    if quote:
      if escaped:
        escaped = False
      elif char == "\\":
        escaped = True
      elif char == quote:
        quote = None
    elif char in ("'", '"'):
      quote = char
    elif char == "#":
      return line[:i], line[i + 1:]
  return line, None


def _parseConstant(text):
  if text in ("true", "false"):
    return ConvertConstant("bool", text == "true")
  if re.fullmatch(r"[+-]?\d+", text):
    return ConvertConstant("int", int(text))
  if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?", text):
    return ConvertConstant("float", float(text))
  if len(text) >= 2 and text[0] in ("'", '"') and text[-1] == text[0]:
    try:
      value = ast.literal_eval(text)
    except (SyntaxError, ValueError):
      raise SourceException("Invalid string constant", what=text)
    if not isinstance(value, str):
      raise SourceException("Invalid string constant", what=text)
    return ConvertConstant("string", value)
  match = re.fullmatch(r"(?:([A-Za-z_]\w*)\.)?([A-Za-z_]\w*)", text)
  if match:
    return ConvertConstant("enum", match.groups())
  raise SourceException("Invalid convert constant", what=text)


class Parser:
  def __init__(self, salt=""):
    self.packet_list = {}
    self.data = None
    self.indent = 0
    self.state = None
    self.top = None
    self.api_version = None
    self.context_stack = []  # Stack of (data, state, indent, convert_source)
    self.convert_source = None
    self.salt = salt

  def read_enums(self, line, indent, docstring):
    line_info, _ = _splitComment(line)
    text = line_info.strip()
    if text.startswith(CONVERT_LABEL + ' ') or text == CONVERT_LABEL:
      self.start_convert(text, indent)
      return
    for en in text.split(','):
      en = en.strip()
      if en in self.data.field_names:
        raise SourceException(f"Duplicate enum value", what=f"{self.data.name}.{en}")
      self.data.fields.append(PacketField(name=en, docstring=docstring))
      docstring = []
      self.data.field_names.add(en)

  def read_abstracts(self, line, indent, docstring):
    # Abstract bodies are not supported; any indented content is an error
    raise SourceException("Abstract packets cannot have body content", what=line.strip())

  def read_field(self, line, indent, docstring):
    line_info, comment = _splitComment(line)
    info = line_info.split()
    fname = None
    ftype = None
    options = []
    if info and info[0] == CONVERT_LABEL:
      self.start_convert(line_info.strip(), indent)
      return
    if len(info) == 1:
      fname, *_ = info
    else:
      fname, ftype, *options = info[::-1]

    if ftype == "String":
      raise SourceException("Forbidden fields type 'String': should be 'string' (lowercase)", what=ftype + ' ' + fname)
    elif comment is not None:
      raise SourceException("Forbidden field inline comment", what=comment.strip())
    elif ftype and ftype[0].islower() and ftype not in PRIMITIVE_TYPES:
      raise SourceException("Unknown primitive field type", what=ftype + ' ' + fname)
    elif fname in self.data.field_names:
      raise SourceException("Duplicate field name", what=f"{self.data.name}.{fname}")
    elif fname in FORBIDDEN_NAMES:
      raise SourceException("Field name can't be reserved keyword", what=ftype + ' ' + fname)

    is_list = LIST_LABEL in options
    pf = PacketField(name=fname, type=ftype, is_list=is_list, docstring=docstring)
    self.data.fields.append(pf)
    self.data.field_names.add(pf.name)

  def start_convert(self, line, indent):
    rest = line[len(CONVERT_LABEL):].strip()
    if rest.endswith(":"):
      rest = rest[:-1].strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", rest):
      raise SourceException(f"Invalid {CONVERT_LABEL} header", what=line)
    if rest in self.data.converts:
      raise SourceException(f"Duplicate {CONVERT_LABEL} type", what=rest)

    self.data.converts[rest] = []
    self.context_stack.append((self.data, self.state, self.indent, self.convert_source))
    self.convert_source = rest
    self.state = self.read_convert_line
    self.indent = indent

  def read_convert_line(self, line, indent, docstring):
    line_info, _ = _splitComment(line)
    text = line_info.strip()
    if not text:
      return
    match = re.fullmatch(r"(\S+)\s*(<=|<!|<-|=)\s*(.+?)\s*", text)
    if not match:
      raise SourceException(f"Invalid {CONVERT_LABEL} mapping", what=text)
    target, operator, value = match.groups()
    if target == CONVERT_IGNORE and operator != CONVERT_COPY:
      raise SourceException("Ignored field only supports the copy operator", what=text)
    if target == CONVERT_IGNORE:
      source = value.strip()
      if not re.fullmatch(r"[A-Za-z_]\w*", source):
        raise SourceException(f"Invalid {CONVERT_LABEL} source field", what=value)
      mapping = ConvertMapping(target, operator, source=source)
    elif operator == CONVERT_CONST:
      mapping = ConvertMapping(target, operator, constant=_parseConstant(value.strip()))
    else:
      source = value.strip()
      if not re.fullmatch(r"[A-Za-z_]\w*", source):
        raise SourceException(f"Invalid {CONVERT_LABEL} source field", what=value)
      mapping = ConvertMapping(target, operator, source=source)
    if target != CONVERT_IGNORE and not re.fullmatch(r"[A-Za-z_]\w*", target):
      raise SourceException(f"Invalid {CONVERT_LABEL} target field", what=target)
    self.data.converts[self.convert_source].append(mapping)

  def read_class(self, line, indent, docstring):
    # Push current context onto stack when entering a nested class/enum
    if self.data is not None:
      self.context_stack.append((self.data, self.state, self.indent, self.convert_source))

    self.data = PacketData()
    self.data.docstring = docstring
    self.indent = indent
    self.convert_source = None
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
    elif option == "abstract":
      self.state = self.read_abstracts
      self.data.is_abstract = True
    else:
      self.data.abstracts = option.split()
      self.state = self.read_field

  def parse(self, files, annotations=None, manifest_path=None):
    if isinstance(files, str):
      files = [files]
    for path in files:
      print("[Export] Reading", path, file=sys.stderr)
      with open(path) as f:
        self.state = self.read_class
        self.data = None
        self.indent = 0
        self.top = None
        self.context_stack = []
        self.convert_source = None
        docstring = []
        for lnum, line in enumerate(f, 1):
          if annotations is not None and line.startswith('# @'):
            _, key, value = line.strip().split(' ', 2)
            annotations[key] = value.strip()
            continue

          sline = line.strip()
          if not sline:
            if docstring and self.data:
              self.data.fields.append(PacketField(docstring=docstring))
            docstring = []
            continue

          if sline.startswith('#'):
            docstring.append(sline[1:].strip())
            continue

          try:
            indent = len(line) - len(line.lstrip())

            # Handle dedent: if we're in a nested context and the new line's indent
            # is <= the current context's indent, pop back to the parent context
            while self.context_stack and indent <= self.indent:
              self.data, self.state, self.indent, self.convert_source = self.context_stack.pop()

            # Convert mapping lines can contain ':' inside string constants.
            if self.state == self.read_convert_line:
              self.state(line, indent, docstring)
            # If this line starts a new class/enum/abstract (contains ':'),
            # call read_class directly instead of the current state
            elif sline.startswith(CONVERT_LABEL + ' ') or sline == CONVERT_LABEL:
              self.state(line, indent, docstring)
            elif ':' in sline:
              self.read_class(line, indent, docstring)
            else:
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
        version = versionHash(data, self.packet_list, salt=self.salt)
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
      inner_classes = {en.name for en in data.inner.values()}
      for pf in data.fields:
        if pf.type in deprecated and data.origin_name not in deprecated:
          raise SourceException(
              "Packet has field potentially deprecated but does not have its own deprecated version",
              what=pf.type + ' ' + pf.name,
              filename=path,
          )
        if pf.type in inner_enums or (pf.type in self.packet_list and self.packet_list[pf.type].is_enum):
          en = self.packet_list.get(pf.type) or data.enums.get(pf.type)
          data.field_is_enum[pf.type] = sum(1 for f in en.fields if f.name)
        if pf.type and pf.type not in self.packet_list and pf.type not in inner_enums and pf.type not in inner_classes and pf.type not in PRIMITIVE_TYPES:
          raise SourceException("Packet field has unknown type", what=f"{pf.type} {pf.name}", filename=path)

      for inner in data.inner.values():
        for pf in inner.fields:
          if pf.type in inner_enums or (pf.type in self.packet_list and self.packet_list[pf.type].is_enum):
            en = self.packet_list.get(pf.type) or data.enums.get(pf.type)
            data.field_is_enum[pf.type] = sum(1 for f in en.fields if f.name)

    self._validateConverts()

    # Compute version for inner enums first (needed by top-level packets/enums)
    for _, data in self.packet_list.items():
      for inner_enum in data.enums.values():
        inner_enum.version = versionHash(inner_enum, self.packet_list, salt=self.salt)

    # Compute version for top-level enums (needed by packets)
    for _, data in self.packet_list.items():
      if data.is_enum:
        data.version = versionHash(data, self.packet_list, salt=self.salt)

    # Compute version for packets (non-enum, non-abstract)
    for _, data in self.packet_list.items():
      if not data.is_enum and not data.is_abstract:
        data.version = versionHash(data, self.packet_list, salt=self.salt)

    self.api_version = 0
    for pk_name, pk in self.packet_list.items():
      if pk.name == pk.origin_name:
        self.api_version ^= pk.version or 0

    # Generate manifest_bp.csv with (hash, packet name) for all top-level packets and enums
    if manifest_path is not None:
        self._generate_manifest(manifest_path)

    return self.packet_list

  def _typeIdentity(self, owner, ftype):
    if ftype in owner.inner:
      return ("inner", owner.name, ftype)
    if ftype in owner.enums:
      return ("enum", owner.name, ftype)
    data = self.packet_list.get(ftype)
    if data:
      return ("enum" if data.is_enum else "packet", ftype)
    return ("primitive", ftype)

  def _enumType(self, owner, ftype):
    if ftype in owner.enums:
      return owner.enums[ftype]
    data = self.packet_list.get(ftype)
    return data if data and data.is_enum else None

  def _topLevelEnum(self, owner, ftype):
    enum = self._enumType(owner, ftype)
    return enum if enum is not None and self.packet_list.get(ftype) is enum else None

  def _typeKind(self, owner, ftype):
    kind = self._typeIdentity(owner, ftype)[0]
    if kind == "primitive":
      return "scalar" if ftype in SCALAR_CONVERT_TYPES else "other"
    return kind

  def _canWiden(self, source, target, same_type):
    if same_type:
      return True
    if target == "string":
      return True
    return target in SAFE_WIDENING.get(source, set())

  def _conversionError(self, message, target, source, mapping):
    raise SourceException(
      message,
      what=f"{target.name}.{source.name}: {mapping}",
    )

  def _setMappingTypes(self, mapping, target, source, target_field, source_field=None):
    mapping.target_type = target_field.type
    mapping.target_kind = self._typeKind(target, target_field.type)
    mapping.target_is_list = target_field.is_list
    if source_field:
      mapping.source_type = source_field.type
      mapping.source_kind = self._typeKind(source, source_field.type)
      mapping.source_is_list = source_field.is_list
    else:
      mapping.source_type = None
      mapping.source_kind = None
      mapping.source_is_list = False

  def _validateConstant(self, target, source, mapping, target_field):
    if target_field.is_list:
      self._conversionError("Constant cannot initialize a list field", target, source, mapping)
    constant = mapping.constant
    target_type = target_field.type
    if target_type == "bool":
      if constant.kind != "bool":
        self._conversionError("Constant type does not match bool field", target, source, mapping)
      return
    if target_type == "string":
      if constant.kind != "string":
        self._conversionError("Constant type does not match string field", target, source, mapping)
      return
    if target_type in INT_RANGES:
      if constant.kind != "int":
        self._conversionError("Constant type does not match integer field", target, source, mapping)
      low, high = INT_RANGES[target_type]
      if not low <= constant.value <= high:
        self._conversionError(f"Constant out of range for {target_type}", target, source, mapping)
      return
    if target_type in ("float", "double"):
      if constant.kind not in ("int", "float"):
        self._conversionError("Constant type does not match floating point field", target, source, mapping)
      value = float(constant.value)
      if not math.isfinite(value):
        self._conversionError("Floating point constant must be finite", target, source, mapping)
      if target_type == "float" and abs(value) > 3.402823466e38:
        self._conversionError("Constant out of range for float", target, source, mapping)
      return
    enum = self._enumType(target, target_type)
    if enum:
      if constant.kind != "enum":
        self._conversionError("Constant type does not match enum field", target, source, mapping)
      qualifier, value_name = constant.value
      if qualifier is not None and qualifier != target_type:
        self._conversionError("Constant enum type does not match field type", target, source, mapping)
      if value_name not in {pf.name for pf in enum.fields if pf.name}:
        self._conversionError("Unknown enum constant", target, source, mapping)
      return
    self._conversionError("Constant cannot initialize this field type", target, source, mapping)

  def _validateConvert(self, target, source):
    target_fields = {pf.name: pf for pf in target.fields if pf.name}
    source_fields = {pf.name: pf for pf in source.fields if pf.name}
    mappings = target.converts[source.name]
    assigned_targets = set()
    used_sources = set()

    for mapping in mappings:
      if mapping.target == CONVERT_IGNORE:
        source_field = source_fields.get(mapping.source)
        if not source_field:
          self._conversionError("Unknown source field", target, source, mapping)
        used_sources.add(mapping.source)
        continue

      target_field = target_fields.get(mapping.target)
      if not target_field:
        self._conversionError("Unknown target field", target, source, mapping)
      if mapping.target in assigned_targets:
        self._conversionError("Duplicate target field", target, source, mapping)
      assigned_targets.add(mapping.target)
      self._setMappingTypes(mapping, target, source, target_field)

      if mapping.operator == CONVERT_CONST:
        self._validateConstant(target, source, mapping, target_field)
        continue

      source_field = source_fields.get(mapping.source)
      if not source_field:
        self._conversionError("Unknown source field", target, source, mapping)
      self._setMappingTypes(mapping, target, source, target_field, source_field)
      used_sources.add(mapping.source)

      if target_field.is_list != source_field.is_list:
        self._conversionError("Cannot map between list and scalar fields", target, source, mapping)

      same_type = self._typeIdentity(target, target_field.type) == self._typeIdentity(source, source_field.type)
      if mapping.operator == CONVERT_COPY:
        if not same_type:
          target_enum = self._topLevelEnum(target, target_field.type)
          source_enum = self._topLevelEnum(source, source_field.type)
          has_enum_convert = target_enum is not None and source_enum is not None and source_enum.name in target_enum.converts
          if has_enum_convert:
            mapping.enum_convert = True
          else:
            self._conversionError("Copy requires identical field types, use <=", target, source, mapping)
      elif mapping.operator == CONVERT_FORCE:
        supported = mapping.target_kind in ("scalar", "enum") and mapping.source_kind in ("scalar", "enum")
        if not supported:
          self._conversionError("Force mapping only supports scalar and enum fields", target, source, mapping)
      elif mapping.target_kind in ("scalar", "enum") and mapping.source_kind in ("scalar", "enum"):
        if not self._canWiden(source_field.type, target_field.type, same_type):
          self._conversionError("Field types are not safely widening", target, source, mapping)
      elif not same_type:
        self._conversionError("Only primitive numeric fields support <=", target, source, mapping)

    for target_field in target.fields:
      if not target_field.name or target_field.name in assigned_targets:
        continue
      source_field = source_fields.get(target_field.name)
      if not source_field:
        self._conversionError(
          "Missing mapping and no source field with the same name",
          target,
          source,
          ConvertMapping(target_field.name, CONVERT_COPY, source=target_field.name),
        )
      same_type = self._typeIdentity(target, target_field.type) == self._typeIdentity(source, source_field.type)
      if not same_type or target_field.is_list != source_field.is_list:
        self._conversionError(
          "Default mapping requires identical field types, add an explicit mapping",
          target,
          source,
          ConvertMapping(target_field.name, CONVERT_COPY, source=target_field.name),
        )
      mapping = ConvertMapping(target_field.name, CONVERT_COPY, source=target_field.name)
      self._setMappingTypes(mapping, target, source, target_field, source_field)
      mappings.append(mapping)
      assigned_targets.add(target_field.name)
      used_sources.add(target_field.name)

    for source_field in source.fields:
      if source_field.name and source_field.name not in used_sources:
        self._conversionError(
          "Source field is not mapped, use _ <- field to ignore it",
          target,
          source,
          ConvertMapping(CONVERT_IGNORE, CONVERT_COPY, source=source_field.name),
        )

  def _validateEnumConvert(self, target, source):
    target_values = {pf.name for pf in target.fields if pf.name}
    source_values = [pf.name for pf in source.fields if pf.name]
    explicit = {}
    for mapping in target.converts[source.name]:
      if mapping.operator != CONVERT_COPY or mapping.target == CONVERT_IGNORE:
        raise SourceException(
          f"Enum {CONVERT_LABEL} only supports the {CONVERT_COPY} operator",
          what=f"{target.name}.{source.name}: {mapping}",
        )
      if mapping.target not in target_values:
        raise SourceException(
          "Unknown target enum value",
          what=f"{target.name}.{source.name}: {mapping}",
        )
      if mapping.source not in source_values:
        raise SourceException(
          "Unknown source enum value",
          what=f"{target.name}.{source.name}: {mapping}",
        )
      if mapping.source in explicit:
        raise SourceException(
          "Duplicate source enum value",
          what=f"{target.name}.{source.name}: {mapping}",
        )
      explicit[mapping.source] = mapping.target

    resolved = []
    for source_name in source_values:
      target_name = explicit.get(source_name)
      if target_name is None:
        if source_name not in target_values:
          raise SourceException(
            "Source enum value is not mapped",
            what=f"{target.name}.{source.name}: {source_name}",
          )
        target_name = source_name
      resolved.append(ConvertMapping(target_name, CONVERT_COPY, source=source_name))
    target.converts[source.name] = resolved

  def _validateConverts(self):
    for target in self.packet_list.values():
      for enum in target.enums.values():
        if enum.converts:
          raise SourceException(
            f"Enum {CONVERT_LABEL} is only supported on top-level enums",
            what=f"{target.name}.{enum.name}",
          )
      for ctype in target.converts:
        source = self.packet_list.get(ctype)
        if target.is_enum:
          if not source or not source.is_enum:
            raise SourceException(
              f"{CONVERT_LABEL} source must be an enum",
              what=f"{target.name}.{ctype}",
            )
          if source is target:
            raise SourceException(
              f"{CONVERT_LABEL} source cannot be the target enum",
              what=f"{target.name}.{ctype}",
            )
          self._validateEnumConvert(target, source)
          continue
        if not source or source.is_enum or source.is_abstract:
          raise SourceException(
            f"{CONVERT_LABEL} source must be a concrete packet",
            what=f"{target.name}.{ctype}",
          )
        if source is target:
          raise SourceException(
            f"{CONVERT_LABEL} source cannot be the target packet",
            what=f"{target.name}.{ctype}",
          )
        self._validateConvert(target, source)

  def _generate_manifest(self, manifest_path):
    """Generate manifest_bp.csv with (hash, packet name, deprecated) for top-level packets and enums."""
    import csv
    import os
    manifest_file = os.path.join(manifest_path, "manifest_bp.csv")

    rows = []
    for name, data in self.packet_list.items():
      if data.is_enum:
        # Top-level enums get their own hash
        version = versionHash(data, self.packet_list, salt=self.salt)
        deprecated = "true" if data.name != data.origin_name else "false"
        rows.append((f"{version & 0xFFFFFFFFFFFFFFFF:0X}", data.origin_name, deprecated))
      elif not data.is_abstract:
        # Top-level packets (not abstract) get their version hash
        deprecated = "true" if data.name != data.origin_name else "false"
        rows.append((f"{data.version & 0xFFFFFFFFFFFFFFFF:0X}", data.origin_name, deprecated))
      # Skip abstracts and inner classes/enums

    # Sort by name for stable output
    rows.sort(key=lambda r: r[1])

    with open(manifest_file, "w", newline="\n") as f:
      writer = csv.writer(f)
      writer.writerow(["hash", "name", "deprecated"])
      writer.writerows(rows)


if __name__ == "__main__":
  p = Parser()
  all_data = p.parse(sys.argv[1:])
  for _, data in all_data.items():
    if data.is_enum or data.is_abstract:
      print(data)
    else:
      print(versionString(data, all_data, {}, {}, set(), salt=p.salt))
