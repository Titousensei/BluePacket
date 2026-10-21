# Implementing BluePacket for a New Language

This guide is the practical checklist for adding a target language to BluePacket. It describes
the contract you must reproduce, the pieces you have to write, and the traps that have already
bitten the existing implementations.

The short version:

1. Write **one hand-written runtime file** for the language (serialization primitives, the packet
   base type, registry, enum helper, `toString` helpers).
2. Write **one exporter** (`scripts/export-<lang>.py`) that consumes the shared parser IR and emits
   idiomatic native code.
3. Port the **shared test suite** and run it against generated code for `testdata/Demo*.bp`.
4. Add the language to the root `run_tests.sh` and the README table.

The byte format and the hash values are the contract. Any individual implementation is only a
reference; when two of them disagree, the fixtures in `testdata/` (and the format documented below)
win.

---

## 1. Read these files first

In this order:

| File | Why |
|------|-----|
| `scripts/libexport.py` | The parser and the IR you will consume. You do not need to modify it. |
| `python/common/blue_packet.py` | The shortest complete runtime. Best starting point for the wire layer. |
| `java/common/src/org/bluepacket/` | The most complete runtime (registry, enums, `toString`, RPC support). |
| `python/test/TestBluePacket.py` | The most complete test list; port this one. |
| `scripts/export-python.py` | Smallest exporter; shows the IR traversal cleanly. |
| `scripts/export-javascript.py` | Single-bundle exporter; useful if your language has no package/namespace files. |
| `testdata/Demo.bp`, `DemoDeprecated.bp`, `DemoConvert.bp` | The shared definitions every language must handle. |
| `BUGS.txt` | Known open issues and cross-language inconsistencies. Check before "fixing" another language. |

Useful commands while working:

```bash
# Dump the IR (packets, fields, versions) without generating code
python3 scripts/libexport.py testdata/Demo.bp

# Generate for one language
scripts/export-python.py --output_dir /tmp/out testdata/Demo.bp

# Inspect a language's generated output and tests
less python/test/gen/test/DemoPacket.py
cd python/test && ./run_tests.sh
```

---

## 2. The architecture you are plugging into

```
testdata/*.bp  ──►  scripts/libexport.py  ──►  PacketData IR  ──►  scripts/export-<lang>.py
                          (parser)                                      (your code)
                                                                              │
                                                              generated classes + API
                                                                              │
                                                              <lang>/common/ runtime (yours)
                                                                              │
                                                              <lang>/test/TestBluePacket
```

Three hard rules:

- **The parser is shared.** All languages must accept the same `.bp` files and produce the same
  structural hashes. Do not fork the parser.
- **The runtime is hand-written per language.** It is one source file (or one small directory) with
  no external dependencies. Generated code may only depend on the language standard library and
  that runtime.
- **Default round-trips are idempotent.** Serializing a default-constructed packet and
  deserializing it must produce the same field values, not merely the same bytes. Each type's
  default must match what the reader produces for the encoded default (for example an empty list,
  the reader's empty-string value, and the first enum value). Explicitly assigning non-canonical
  values such as `null`/`undefined` to a string may normalize on the wire; that is the caller's
  responsibility.

### Bias: idiomatic first

Developer convenience, the language's best practices, and idiomatic implementation take precedence
over strict type/API enforcement. When in doubt, prefer convenience and the language's conventions.
This applies to class/struct
design — do not try to emulate OOP in a language that has no classes — and to helper methods. Keep
helpers minimal and idiomatic; do not build a framework around the generated types. If the language
lacks a data type that BluePacket uses, implement the closest natural equivalent with the minimum
effort and document the gap.

This is about type/API strictness, not the wire format: the bytes and hashes must stay exact.
Example: seal instances rather than classes; sealing instances protects the field set, while
sealing or freezing classes fights the language and blocks static registration.

Recommended layout (match the existing languages):

```
<lang>/
  common/                 # hand-written runtime, no generated code
  test/
    run_tests.sh          # clean → export → compile → run
    TestBluePacket.*      # ported test suite
    gen/                  # generated output, gitignored
  rpc/                    # optional, only if you implement RPC
```

---

## 3. The IR your exporter consumes

`Parser().parse(paths)` returns `(packet_list, api_version)` where `packet_list` is an insertion-
ordered `dict[str, PacketData]`. Inspect it with `python3 scripts/libexport.py ...`.

### `PacketData`

| Attribute | Meaning |
|-----------|---------|
| `name` | Declared name, including the `__<HEX>` suffix for deprecated packets. |
| `origin_name` | Name without the deprecated suffix (equals `name` for current packets). |
| `docstring` | `list[str]` of comment lines, already stripped. |
| `is_enum` / `is_abstract` | Kind flags. Enums and abstracts have no `version`. |
| `fields` | `list[PacketField]` in **source order**. This includes enum values for enums. |
| `inner` / `enums` | Direct inner classes / inner enums, `dict[name, PacketData]`. |
| `field_is_enum` | `dict[type_name, value_count]`; use it to pick enum encoding width. |
| `converts` | `dict[other_type_name, option_str]` from `convert OtherType` directives. |
| `abstracts` | Concrete packet's list of abstract marker names. |
| `version` | Signed 64-bit structural hash, `None` for enums/abstracts. |

### `PacketField`

| Attribute | Meaning |
|-----------|---------|
| `name` | Field name. **`None` for a standalone comment paragraph**; skip those. |
| `type` | Primitive name, packet name, inner class name, or enum name. |
| `is_list` | `True` for `list <type> <name>`. |
| `docstring` | `list[str]`. |

Primitive type names are exactly:

```
bool byte ubyte short ushort int long float double string packet
```

`packet` is the polymorphic base type (any concrete packet, encoded with its hash). Any other type
name refers to a packet, enum, or inner class in the same parse.

Important exporter rules:

- **Never use `fields` order for serialization.** Sort by `field.name` (see §4.2). Source order is
  only for emitting field declarations and docstrings.
- `field_is_enum` is set on the *owning top-level packet*, including enum fields from its inner
  classes. Inner classes themselves do not have it populated.
- Inner classes/enums are flattened one level: they live in the top-level packet's `inner`/`enums`
  and can reference each other by bare name.
- The parser does **not** reject two packets declaring an inner type with the same name. If your
  language puts inner types in a flat module/package scope (JS does), your exporter must
  use a namespace prefix to avoid collisions instead of emitting invalid code.
- `version` and `api_version` are computed by the parser. Emit them as constants; do **not**
  reimplement MD5 hashing in the target language.

---

## 4. The wire format (normative)

All multi-byte values are **big-endian**. The format has no schema header beyond the packet hash.

### 4.1 Primitives

| `.bp` type | Encoding |
|------------|----------|
| `bool` | Bit-packed; see §4.2. |
| `byte` | Signed 8-bit. |
| `ubyte` | Unsigned 8-bit. |
| `short` | Signed 16-bit, big-endian. |
| `ushort` | Unsigned 16-bit, big-endian. |
| `int` | Signed 32-bit, big-endian. |
| `long` | Signed 64-bit, big-endian. |
| `float` | IEEE-754 binary32, big-endian. |
| `double` | IEEE-754 binary64, big-endian. |
| `string` | Sequence length in **UTF-8 bytes**, then the bytes. `null` and `""` both encode as length 0. |
| `packet` | 8-byte signed hash, then the concrete packet's body. Hash 0 means `null`. |
| concrete packet type | One presence byte (`0` = null, `1` = present), then the body **without** a hash. |
| enum | Unsigned ordinal. 1 byte if the enum has **≤ 256** values, else 2 bytes (unsigned short). The width comes from the enum type, not the value. |
| list | Sequence length = element count, then elements. |

### 4.2 Field order and boolean packing

Two rules, in this order:

1. **Scalar booleans are written first**, regardless of their name, packed into bytes.
   - Collect all non-list `bool` fields, sorted by name.
   - Bit `i % 8` of byte `i // 8` is `1` for `true`, LSB-first within each byte.
   - Write `ceil(n / 8)` bytes. A partial last byte is still written.
2. **All remaining fields are written sorted by field name** (plain string sort), skipping scalar
   booleans.

Consequences:

- A packet with no scalar booleans writes no boolean block at all.
- `bool` inside a list is *not* part of the scalar block; it is a normal list field.
- Field declaration order never affects bytes or hashes.

### 4.3 Sequences (strings, lists, and length prefixes)

A "sequence length" is:

- one unsigned byte when `length < 255`;
- otherwise `0xFF` followed by a signed 32-bit big-endian integer.

Note that **255 itself uses the extended form**. Strings use the UTF-8 **byte** length, not the
character count. Lists use the element count.

A list of booleans is special: the sequence length is the number of elements, followed by
`ceil(n / 8)` packed bytes with the same LSB-first bit order as scalar booleans. It is *not* a list
of one-byte booleans.

### 4.4 Packets inside packets

| Field declaration | Bytes |
|-------------------|-------|
| `DemoOuter o` (concrete) | `0x00` or `0x01`, then `o`'s body (no hash). |
| `packet p` (polymorphic) | 8-byte hash of the actual class, then its body. `0` hash for null. |
| `list DemoOuter l` | length, then each element's body (no presence byte, no hash). Null elements cannot be represented. |
| `list packet l` | length, then each element's 8-byte hash + body. |

The last row is where implementations currently disagree: Python and JavaScript write the hash per
element; Java's `writeArray(BluePacket[])` writes only the body while its reader expects a hash.
There is no fixture for `list packet`, so the bug is latent. Follow Python/JS: polymorphic lists must
carry the hash per element.

### 4.5 Worked example

`DemoOuter` with `oInt = 1` and `oString = "A"`:

```
B0 60 E8 38 9E C9 B2 01     # packet hash 0xB060E8389EC9B201
00 00 00 01                 # oInt (int32, sorted first: oInt < oString)
00 00 00 01 41              # oString length 1, UTF-8 'A'
```

`DemoPacket` with `fBoolean = true` and everything else empty/zero starts with one boolean byte
`0x01`, followed by the non-boolean fields in sorted order.

---

## 5. Hashes, deprecation, and API version

The exporter does not implement this logic; it consumes `PacketData.version` and
`Parser.api_version`. You only need to emit them. Still, understand what they mean so you can debug.

- The structural version string is built recursively from `origin_name` and the sorted fields
  (`+name:type`), expanding enum value names and referenced packet structures. Recursion is cut with
  `{Type+...}`. Field names and deprecated packet names are normalized by stripping `__<HEX>`.
- `versionHash` = first 64 bits of `md5(version_string)` interpreted as a **signed big-endian
  int64** (`unpack("!2q", digest)[0]`).
- Deprecated packets must be named `Original__<UPPERCASE_HEX>` where the hex is the unsigned
  64-bit form of the hash. The parser rejects anything else.
- `api_version` = XOR of the `version` of every non-deprecated concrete packet in the export set.
  It therefore depends on **which files you export together**. Export a complete API surface at
  once; do not compare `api_version` across different file sets.
- `packetHash` on a generated class is the signed decimal value; `packetHex` is the unsigned
  `0x...` form. The wire uses the signed 64-bit value, but the bytes are identical.

Generated classes must carry both the hash and hex (or a way to format the hex), because `toString`
uses the hex and the registry uses the hash.

---

## 6. Step 1: the runtime

Write `<lang>/common/<runtime>.*`. It has no dependency other than the standard library. The
following is the required surface; names and signatures should follow the language's idiom.

### 6.1 Writer and reader

A writer wrapping a byte buffer / output stream, and a reader wrapping a byte buffer / input stream,
with one method per primitive:

```
writeByte / writeUByte / writeShort / writeUShort / writeInt / writeLong
writeFloat / writeDouble / writeString
readByte / readUByte / readShort / readUShort / readInt / readLong
readFloat / readDouble / readString
```

Implement exactly the encodings in §4. Multi-byte writes must be big-endian even if the host is
little-endian.

Higher-level helpers that generated code can call (adapt names):

```
writeSequenceLength(n)          readSequenceLength()
writeArray(writerFn, list)      readArray(elementReader)
writeArrayBool(list)            readArrayBool()
writeArrayEnum(list)            readArrayEnum()
writeArrayLargeEnum(list)       readArrayLargeEnum()
writeBluePacket(pkt)            readBluePacket(registry)
```

`writeString(null)` and `writeString("")` both produce a single `0x00`. Java reads `null`;
Python and JS read `""`. Defaults must match the decoded form (see §2): a language that decodes to
`""` must default to `""`. Explicitly assigning `null`/`undefined` may normalize on the wire; that
is the caller's responsibility.

### 6.2 Packet base type

All generated packets extend/implement a base type with:

```
packetHash                    # signed 64-bit constant, set by generated class
packetHex                     # "0x..." string
serialize() -> bytes          # write hash, then serializeData
serializeData(writer)         # body only
populateData(registry, reader)# body only
fieldsToString() -> string    # the " f=v ..." part, or an equivalent helper
toString() -> string          # see §6.5
```

`serializeData` writes only the body. `serialize()` (or the registry) writes the 8-byte hash.
`populateData` reads only the body; the caller has already consumed the hash.

If the language's 64-bit integer type is not JSON-serializable (JS BigInt is the example), provide a
`toJSON` that recursively emits longs as decimal strings and nested packets/arrays as plain values.
Document the inverse conversion; never convert 64-bit values to floating point.

Generated packets are data schemas: keep the type open for behavior (subclass methods, prototype
helpers, mixins) but fix its field set. Seal instances after initialization where the language
supports it; do not seal or freeze the class itself, because that locks statics/registration and
does not prevent subclassing. Never extend a packet by adding fields; serializers only know
`TYPE_INFO`. Helpers defined on a subclass are absent from instances created by the registry, so use
prototype helpers when helpers must apply to deserialized packets.

### 6.3 Registry

The registry maps a signed 64-bit hash to a way to construct that class:

```
register(packet_instance_or_class)
deserialize(bytes) -> packet | null
deserializeInternal(reader) -> packet | null
```

`deserializeInternal` must:

1. Read the signed 64-bit hash.
2. Return `null` if the hash is 0.
3. Look up the constructor; throw a clear error if unknown.
4. Construct an empty instance, call `populateData(registry, reader)`, return it.

Generated output must register **every non-abstract concrete packet**, including deprecated ones.
Do not register enums, abstract markers, or inner classes (inner classes never appear as a top-level
hash; they are reached through their owning packet's fields). The registry may be an instance passed
around (Python/Java/JS) or a package-level/static map (Go/C#); both are fine as long as generated
code and users can deserialize without extra setup beyond loading the generated module.

### 6.4 Type validation

Dynamic languages validate on assignment (Python `__setattr__`, JS setters). Static languages rely
on the type system, but still need explicit checks where the type system is too wide:

- `byte`: -128..127; `ubyte`: 0..255; `short`: -32768..32767; `ushort`: 0..65535.
- `int`: 32-bit; `long`: 64-bit. Do not silently truncate.
- `string`: string or null.
- lists: must be a list/array, and every element must pass the element type check.
- packet fields: `null` or an instance of the packet base type. Concrete-typed fields should check
  the concrete class where the language allows it.
- enums: type-strict. A value from a different enum type must be rejected, not accepted by ordinal.
- The error should carry the expected type and the offending value so tests can assert the message.

The negative tests in `python/test/TestBluePacket.py` and `javascript/test/TestBluePacket.js` are the
specification for dynamic languages. Port them.

### 6.5 `toString`

`toString` is part of the test contract, because `toString*.txt` fixtures are shared. Format:

- Top-level packet: `{TypeName 0xHEX f=v f2=v2}`.
- Inner class: `{InnerName f=v}` — no hash.
- Fields appear in **alphabetical order**.
- Skip "empty" fields: `false`, numeric zero, empty string, `null`, empty list, and enum ordinal 0.
- `bool` prints `1` (only when true).
- `string` prints `"value"` with no escaping (existing implementations do not escape).
- enum prints its name.
- A list prints `{Type *count|elem|elem}`. Elements of packet type print their **fields only**, no
  braces and no hash. A scalar packet field prints its full `toString` (with hash).
- Floats read back from the wire are widened. Python rounds to
  `6 - floor(log10(|v|))` decimal places; JS returns the shortest decimal that round-trips to the
  same float32 (1..9 significant digits). Both keep `3.14` from printing as `3.140000104904175`.
  Match the fixtures; formatting of large/small values still differs between languages.

The fixtures are `testdata/toString*.txt`; compare exactly, including spaces.

---

## 7. Step 2: the exporter

Create `scripts/export-<lang>.py`. Follow the existing CLI conventions:

```bash
scripts/export-<lang>.py --output_dir <dir> [language-specific options] <files...>
```

Common options: `--output_dir` (required), plus `--package` (Java, Go), `--namespace` (C#), and
`--runtime` (JS). Keep `--debug` if other exporters have it.

Skeleton:

```python
from libexport import Parser, PacketData, PacketField, SourceException

def export_class(out_dir, data, all_data, package):
    ...

def get_args():
    ...

def main():
    args = get_args()
    p = Parser()
    all_data = p.parse(args.packets)
    # emit enums, inner types, packets, abstracts, api version, exports/registry
    ...
    print(f"[Exporter<Lang>] ...")
```

### 7.1 Order of emission

1. Header/warning and imports (including the runtime).
2. Enums, top-level first, then inner enums. Emit enum tables as `name <-> ordinal` lookups and a
   typed enum representation (native enum where possible).
3. Inner classes, before the packet that owns them (or nested inside if the language allows).
4. Concrete packets and abstract markers.
5. Registry population and API version.
6. Module exports / registration.

Enums and inner types may be referenced by any packet, so they must be available before bodies.
If the language has hoisting or types are order-independent, this is less critical.

### 7.2 Per concrete packet, emit

- Docstring in the native doc-comment format.
- `packetHash` (signed decimal) and `packetHex`.
- The native structure: one public field per named `PacketField`, in **source order**, with the
  language's default values. Recommended defaults:
  - bool `false`, numeric `0`, long `0`, list empty (fresh per instance),
  - string equal to the reader's value for length 0 (`""` in most languages),
  - enum first value (ordinal 0),
  - packet/inner `null`.
- A constructor/setters following the local idiom (see §7.4).
- `serializeData`: scalar bool block first, then sorted non-bool fields.
- `populateData`: same order as the writer.
- `fieldsToString`, if the runtime's `toString` needs it.
- Converter methods when `data.converts` is non-empty.
- Type validation, if it is not in the base runtime.

### 7.3 Field dispatch in the serializer/deserializer

Use the same case order as the existing exporters:

```
if field is a list:
    bool -> writeArrayBool
    enum -> writeArrayEnum / writeArrayLargeEnum
    'packet' -> writeArray(pkt -> writeBluePacket)   # hash per element
    other primitive -> writeArray(element writer)
    concrete packet -> writeArray(pkt -> pkt.serializeData)  # no hash
elif type in field_is_enum:
    writeUByte/writeUShort(ordinal)
elif type == 'packet':
    writeBluePacket(value)                           # 8-byte hash + body
elif type in primitives:
    write primitive
else:
    # concrete packet
    presence byte, then serializeData
```

`field_is_enum[type] > 256` selects the 2-byte form; `<= 256` selects 1 byte. `packet` is a
primitive: its scalar form is hash+body, not presence+body.

Check `field_is_enum` before the primitive/else branches; enum names are not primitives and would
otherwise fall into the concrete-packet branch.

### 7.4 Language idioms

The project goal is native, idiomatic data structures with few helper methods. Existing choices:

| Language | Shape | Construction |
|----------|-------|--------------|
| Java | `final class X extends BluePacket`, public fields | chaining setters `setFoo(v)` returning `this`; default enum = first value |
| Python | class with keyword-only constructor args | `X(foo=1, bar=...)`; `__setattr__` validation |
| C# | `sealed class X : BluePacket`, public fields | direct field initialization |
| Go | struct with exported fields, package-level `Serialize`/`Deserialize` | composite literals; `Register` in `init()` |
| JavaScript | class, one bundle, sealed instances | options object `new X({foo: 1})` |

Do not invent a parallel getter/setter API when public fields are idiomatic. Do not freeze/seal
classes in a way that blocks static registration; seal instances if you want closed structs (JS does),
but leave the class object mutable.

### 7.5 Enums

- Emit the enum with docstrings and stable ordinal order.
- Provide `valueOf(int)` (returns the enum or null/undefined for unknown values) and access to the
  ordinal/name for serialization and `toString`.
- Enforce type identity in dynamic languages; ordinal alone is not enough.
- `> 256` values uses 2 bytes. Exactly 256 still uses 1 byte.

### 7.6 Abstract markers

`X: abstract` is a marker, not a serializable packet. Concrete packets declare `P: A B`. Emit marker
types such that `p instanceof A` (or the language's equivalent) is true for every declared abstract.
JS uses `Symbol.hasInstance` over an `_IMPLEMENTORS` list assigned after all packets; Java uses an
interface; Python uses a base class. Markers are not registered and have no hash.

### 7.7 Converters

`convert OtherType` generates:

- `X.convertOtherType(other)` / `X.convert_other_type(other)` building an `X` from an `OtherType`.
- `X.convert()` returning a list of new `OtherType` instances (or empty). The exact behavior is
  pinned by `DemoConvert.bp` and the `testConvert*` tests.

The source type must be a top-level packet in the same export (same limitation as Python/Java).
Do not silently skip an unknown convert source.

### 7.8 Docstrings

`#` comments become native doc comments. Emit them for packets, fields, enums, and enum values.
They are not part of the wire format, but they are part of the "generated code is readable" goal and
are checked by inspection, not tests.

---

## 8. Step 3: tests

Create `<lang>/test/run_tests.sh` following the existing pattern:

```bash
#!/bin/bash
set -e

echo "=== CLEANING ==="
rm -rf gen build doc

echo "=== EXPORTING ==="
mkdir -p gen
../../scripts/export-<lang>.py --output_dir gen \
  ../../testdata/Demo.bp ../../testdata/DemoDeprecated.bp ../../testdata/DemoConvert.bp

echo "=== COMPILING ==="
# language-specific build step

echo "=== TESTING ==="
# run the test binary/module
```

Port `python/test/TestBluePacket.py` (or the JS suite, which is the same list plus more). Use the
shared fixtures in `testdata/`; never copy them into the language directory.

Required coverage:

| Area | What to assert |
|------|----------------|
| Packet hashes | Exact signed values for `DemoPacket`, `DemoPacket2`, `DemoPacket3`, `DemoPacketU`, `DemoVersion`, deprecated variants, `DemoIncludeVersion`. |
| Serialization | `packet.serialize()` equals `testdata/<Packet>.bin` byte-for-byte. |
| Deserialization | `registry.deserialize(bin)` round-trips and `toString` matches. |
| Default round-trip | A default-constructed packet deserializes to identical field values, not just identical bytes. |
| `toString` | Exact strings from `testdata/toString*.txt`. |
| Unsigned | `DemoPacketU` round-trip and boundaries. |
| Enums | Small and >256-value enums, lists, type strictness, unknown values. |
| Abstracts | Concrete packets are instances of declared markers; others are not. |
| Converters | `convert()` / `convertType()` behavior, including the empty case. |
| API version | `BluePacketAPI.VERSION` equals the parser's `api_version`. |
| Deprecation | Deprecated hashes and names; registry can deserialize them. |
| Negatives | Wrong scalar types, out-of-range byte/short/unsigned, wrong list element types, wrong enum type, wrong packet type. |

Then add the language to the root `run_tests.sh` (it already iterates the language directories) and,
if applicable, to `run_tests_rpc.sh`.

When you add a new cross-language fixture:

- Generate it with the reference implementation only after the byte layout is agreed.
- Verify at least two independent implementations produce the same bytes.
- Prefer adding a `.bin` + `toString` fixture together so a format change is caught in both directions.

---

## 9. Step 4: RPC (optional)

RPC is layered on top of packet serialization and is not required to claim de/ser support. Java has
both client and server; Python and JavaScript have client examples. If you implement RPC, reuse the
runtime's framing and keep the protocol in `<lang>/rpc/`, with `run_tests.sh` and a
`result_tests.expected` so the root `run_tests_rpc.sh` can pick it up.

---

## 10. Known hazards and implementation differences

These are real issues found while implementing the existing languages. Read them before debugging a
mismatch; some are intentionally left open in `BUGS.txt`.

1. **Sequence-length sentinel is 32-bit.** `0xFF` is followed by a 4-byte int. Python's
   `readString` and `readListBool` read the extended value as **64-bit**, and Python's generated list
   reader does not handle the sentinel at all (it reads a single byte), so Python cannot read
   sequences ≥255 written by Java/JS. Do not copy that bug.
2. **Field order is alphabetical, not declaration order.** This is the most common first-run
   failure.
3. **Scalar booleans come before all other fields**, even if their names sort later.
4. **Boolean lists are bit-packed**, not one byte per element.
5. **Enum width is a type property.** `<= 256` values = 1 byte; `> 256` = 2 bytes. The list and
   scalar paths must agree.
6. **Unknown enum ordinals are handled differently.** Java's `valueOf` returns null, Python raises,
   and JS throws `Unknown <Enum> value: N`. Follow the language's natural convention, but never
   silently remap an unknown ordinal to a different enum value.
7. **`null`, `undefined`, and `""` strings are indistinguishable on the wire.** All encode as
   length 0. Java canonicalizes to `null` (read returns null); Python and JS decode to `""`.
   Defaults must match the decoded form for round-trip idempotence: JS defaults to `""`; Python
   still defaults to `None`. Explicitly assigning null/undefined may normalize; that is the
   caller's responsibility.
8. **`packet` vs concrete packet fields** use different encodings (hash vs presence byte). A
   `list packet` must write a hash per element; Java currently does not (latent bug, no fixture).
9. **64-bit values must not go through double.** Use a real 64-bit integer (`long`, `int64`, `BigInt`)
   for `long`, packet hashes, and `api_version`. JS uses `BigInt`.
10. **Inner types can collide** across packets. The parser allows it; flat-scope languages (JS) must
    reject it in the exporter. Namespaced languages should still be aware of the collision.
11. **Deprecated packets must stay registered.** Old data uses old hashes. Do not drop deprecated
    classes from the registry, and do not rename them.
12. **`api_version` depends on the exported file set.** Export the whole API together.
13. **Floats lose precision on the wire.** `float` is binary32. Runtimes round on read to keep
    `toString` fixtures stable (JS uses shortest-round-trip; Python uses the log10 formula); this
    is lossy and text formatting still differs for extreme values.
14. **Enums default to ordinal 0**, so a default-constructed packet omits that field from `toString`.
15. **No external dependencies.** Not for runtime, not for tests beyond the language toolchain.
16. **The registry may be instance-based or global**, but generated code must be usable without
    manual registration beyond importing the generated module/package.
17. **Don't freeze/seal classes** to enforce finality; it blocks static registration and inner-type
    aliases. Seal instances if the language supports it and closed structs are desired.

---

## 11. Acceptance checklist

Before calling a language supported:

- [ ] Parser and IR untouched; `.bp` files are shared.
- [ ] `<lang>/common/` runtime has no external dependencies.
- [ ] Exporter handles: primitives, lists, nested/concrete packets, `packet`, enums (small/large),
      inner classes/enums, docstrings, abstracts, converters, deprecated packets, API version.
- [ ] `<lang>/test/run_tests.sh` exports `Demo.bp`, `DemoDeprecated.bp`, `DemoConvert.bp`, builds,
      and runs the full suite green from a clean tree.
- [ ] Serialization is byte-identical to `testdata/*.bin` for all fixtures.
- [ ] `toString` matches `testdata/toString*.txt` exactly.
- [ ] `packetHash` matches the expected signed values; `BluePacketAPI.VERSION` matches.
- [ ] Dynamic-language negative tests pass (types, bounds, enum identity).
- [ ] Language added to root `run_tests.sh` and the README features table.
- [ ] Any newly discovered cross-language mismatch is recorded in `BUGS.txt` with which
      implementation is considered correct.

If you had to choose a reference while implementing, choose **Python** for the wire layer (it is the
shortest), **Java** for the class/registry/enum surface, and the **fixtures** whenever they disagree.
