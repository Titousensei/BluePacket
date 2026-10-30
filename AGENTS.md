## Project Overview

BluePacket is a multi-language serialization/deserialization library. Custom `.bp` definition files are compiled into native data structures (classes/structs) with binary serialization for each supported language. The core is a Python 3 parser/code-generator; each target language has a hand-written runtime base class and per-exporter code generation.

## Project Guidelines

- no external dependencies: avoid all external dependencies for runtime (parsers, libraries, etc.)
- no dependencies for testing, expect for the necessary compiler and runtime
- simple native and idiomatic data structures with few helper methods to simplify usage

## Common Commands

### Run all language tests
```bash
./run_tests.sh
```

### Run RPC tests
```bash
./run_tests_rpc.sh
```

### Run a single language's tests
```bash
cd <language>/test && ./run_tests.sh
```
Languages: `java`, `python`, `csharp`, `golang`, `javascript`

### Run the parser/library unit tests
```bash
cd scripts/test && ./run_tests.sh                  # all tests
cd scripts/test && python3 -m unittest test-libexport.TestLibExport.<test_name>  # single test
```

### Generate code for a language
```bash
scripts/export-python.py --output_dir <dir> <.bp files>
scripts/export-java.py --package <pkg> --output_dir <dir> <.bp files>
scripts/export-csharp.py --namespace <ns> --output_dir <dir> <.bp files>
scripts/export-golang.py --package <pkg> --output_dir <dir> <.bp files>
scripts/export-javascript.py --output_dir <dir> <.bp files>
```

### Debug parser output (no code generation)
```bash
python3 scripts/libexport.py <.bp files>
```

## Architecture

### Two-layer design

1. **Parser** (`scripts/libexport.py`): Reads `.bp` files → produces a dict of `PacketData` objects (in-memory IR). This is shared by all exporters.
2. **Exporters** (`scripts/export-*.py`): Each traverses `PacketData` and emits language-specific source files. Each exporter imports from `libexport`.

### Key abstractions in `scripts/libexport.py`

- `Parser` — state-machine parser: `read_class` → `read_field` / `read_enums` / `read_abstracts`
- `PacketData` — IR node for a packet, enum, or abstract class (fields, inner classes, enums, converts)
- `PacketField` — a field with name, type, is_list, docstring
- `versionHash()` / `versionString()` — MD5-based 64-bit compatibility hash from the structural representation of a packet
- `api_version` — XOR of all non-deprecated packet hashes, emitted as `BluePacketAPI.<ext>`

### Per-language structure

Each target language directory follows the same layout:
```
<lang>/common/     # Hand-written BluePacket runtime base class + helpers
<lang>/test/       # Test harness: run_tests.sh, TestBluePacket.*, gen/ (generated output)
<lang>/rpc/        # RPC client/server examples (where implemented: Java, Python, JavaScript)
```

### Binary wire format

`[8-byte packet hash (big-endian)] [field values in declared order]`

- Boolean fields are packed 8-per-byte
- Strings: length-prefixed (1 byte, or `0xFF` + 4-byte int for >255 chars)
- Lists: length-prefixed then elements
- Enums: byte if ≤256 values, unsigned short otherwise
- Nested packets: their hash + body

### .bp definition syntax

```
PacketName:
  type fieldName
  list type arrayField
  InnerType inner

InnerType:
  int value

MyEnum: enum
  VAL1, VAL2, VAL3
```

- Indentation defines nesting (inner classes/enums)
- `#` comments become docstrings in generated code
- `: abstract` for abstract markers, `: enum` for enums
- `convert OtherType` directives generate converter methods
- Deprecated packets: name suffix `__<hex_hash>` (validated by parser)

### Versioning and deprecation

Each packet gets a deterministic 64-bit hash from its structure. Deprecated packets must be named `OriginalName__<hash>`. The parser validates this naming convention. The `api_version` is the XOR of all non-deprecated packet hashes.

## Packet conversion (`convert` / auto-convert)

### What it is

A `.bp` file can declare that one packet type replaces another:

```text
packet DemoSecond {
  convert DemoFirst:
    enabled = true
}
```

During deserialization, a `DemoFirst` becomes a `DemoSecond` automatically. There is no version negotiation and no upgrade path: this is for renaming or replacing a packet type while old payloads are still in flight, not for schema evolution. Both types must exist in the same generated package set.

Each line inside the `convert` block names a target field and how it is mapped from a source field or constant. Every field of the target must end up mapped: fields you list take exactly what you wrote, and a field you leave out is copied implicitly when the source has a field with the same name and an identical type. There is no "keeps its default" fallback — an unmapped target field with no same-named source field is rejected (`Missing mapping and no source field with the same name`), and so is a leftover source field (`Source field is not mapped, use _ <- field to ignore it`). The validation is in `Parser._validateConvert`. The source packet itself is unchanged on the wire; it still serializes as itself.

The mapping operators are:
- `<-`: copy the source field value
- `<=`: cast (widen only) the source field value to the target field type
- `<!`: cast (force to fit, clamp to max values) the source field to the target field type
- `=`: assign a constant

`<-` requires identical field types, except when both sides are enums and the target enum declares a convert from the source enum. `<=` only widens primitive numerics, cast to string always allowed; `<!` only applies to scalar and enum fields.

If the target field is `_` the operator must be `<-` and the source field is ignored.

Enum convert only from other enums. Only `<-` is accepted inside an enum convert block — `=` and the casts are rejected. Source values map implicitly by name and an explicit `<-` overrides a name; every source value must be mapped or exist in the target under the same name.

### Compiler and schema rules

- The convert target and the source must both be **concrete packets**. A source that is an enum or an abstract is rejected (`convert source must be a concrete packet`); an abstract target cannot even declare one, since abstract bodies are forbidden by the parser. Enum `convert` blocks are only legal on top-level enums, and a packet cannot convert from itself.
- A source packet may be converted to **exactly one** target. Two targets claiming the same source is a compile error (`testdata/NegativeConvertDuplicateSource.bp` covers it). Without this rule the runtime lookup would be ambiguous.
- Conversion does not walk nesting.

### Runtime semantics (all languages)

- Conversion happens **at deserialize time**, driven by the registry, not at serialize time. 
- It only fires when the **target type is registered**. Call `registry.register(...)` for the module containing the target or you get the original packet back, silently and by design.  That is the documented escape hatch, not a bug: an app that only knows `DemoFirst` keeps receiving `DemoFirst`.
- The registry reads the target from the packet's own class (`convertTo`), and never scans registered classes looking for a matching converter. Keep it that way: resolution is one field read, not a search. Java and C# read that static field reflectively (`Field.get(null)` / `FieldInfo.GetValue(null)`) because a static field cannot carry a per-subclass value on the shared base class; Python instead indexes names in `register()` and never reflects. Go has no static per-type field at all, so the metadata is an optional method (`GetConvertTo`) found by an interface assertion: a packet that does not implement it is not converted.

### Generated metadata

Every top-level concrete packet gets two attributes so the registry never has to guess (inner classes and enums get none — inner classes are deserialized inline, so the registry never asks them):

| Language | `convertTo` | `convertFrom` |
| --- | --- | --- |
| Java | target `Class`, or `null` | `List<Class<? extends BluePacket>>` |
| C# | target `Type`, or `null` | array of source `Type` |
| Python | target **class name string**, or `None` | tuple of source classes, `()` when empty |
| JavaScript | target `Class`, or `null` | array of source classes (a static getter: the bundle's class order would break a field reference) |
| Go | `GetConvertTo() *bluepacket.ConvertInfo` (target hash + converter func), emitted only on packets that have a target | not emitted — the runtime never indexes from sources |

The Python asymmetry is deliberate and must not be "fixed": the target's module already imports the source for its generated converter body, so storing a class object in `convertTo` creates a circular import that fails depending on which module loads first. `convertFrom` points the other way and is safe as real classes. Python converters are also named per source (`convertDemoFirst`), so the runtime looks up `"convert" + type(packet).__name__`.

### Nested concrete-typed packet fields do not convert

A field typed as another concrete packet is deserialized inline (`populateData` in Python, the equivalent in Java/C#) and **bypasses the registry**, so it does not convert. Only fields typed as the generic `packet` type go through the registry's deserialize path and therefore convert. This is intentional and consistent across all three runtimes — do not "fix" one language in isolation; it would make the wire behavior diverge.

The generated converter assigns such a field straight across, so the target shares the nested object with the source rather than deep-copying it. Conversion never recurses.

### Adding conversion to a new language (checklist)

1. Emit `convertTo` / `convertFrom` for concrete packets only, in the class exporter — never for enums, abstracts, or inner classes.
2. Read that metadata at deserialize time, one field read per packet, no scanning of registered classes. A static field can't hold a per-subclass value on the base class, so Java/C# read it reflectively and Python keeps a name index built in `register()`.
3. Hook the conversion into the shared deserialize path, after `populateData`.
4. Require the metadata on every packet that can arrive through the registry, and fail loudly when it is missing (Java/C# throw; Python treats a missing `convertTo` as "no conversion"). Inner classes are exempt — they are deserialized inline and never reach the registry.
5. Test all three cases: converts in both directions, and **target not registered returns the original packet**. (Not all runtimes can express the last one — C# registers assembly-wide, so it is untestable there.)

### Verifying changes

Conversion touches the exporter and the runtime. Every generated tree is gitignored (`**/gen/**`), so a change produces no committed diff — regenerate and run the suites to see its effect, and read `python/test/gen` to confirm the emitted metadata before trusting a green run.

- Python: `python/test/run_tests.sh` (regenerates `gen`, runs the unittest suite).
- Python RPC round-trip: `python/rpc/run_tests.sh` — diffs live client/server output against `result_tests.expected`, so it also catches generated-code regressions.
- Java and C# have their own suites; keep all of them green, and treat a change to one language's convert behavior as needing the other two to keep byte-identical semantics.

## Implementation Status

| Language | de/ser | autoconvert | rpc client | rpc server |
|----------|--------|-------------|------------|------------|
| Java     | Y      | Y           | Y          | Y          |
| Python   | Y      | Y           | Y          |            |
| C#       | Y      | Y           |            |            |
| Go       | Y      | Y           |            |            |
| JavaScript | Y    | Y           |            |            |


## Test Data

- `testdata/Demo.bp` — primary packet definitions for all tests
- `testdata/DemoConvert.bp` — converter feature test definitions
- `testdata/DemoDeprecated.bp` — deprecation feature test definitions
- `testdata/example_rpc.bp` — RPC service definitions
- `testdata/*.bin` — binary test vectors for round-trip verification
- `testdata/Negative*.bp` — parser negative test cases (invalid definitions that must raise `SourceException`)
