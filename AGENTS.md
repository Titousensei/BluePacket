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

## Implementation Status

| Language | de/ser | rpc client | rpc server |
|----------|--------|------------|------------|
| Java     | Y      | Y          | Y          |
| Python   | Y      | Y          |            |
| C#       | Y      |            |            |
| Go       | Y      |            |            |
| JavaScript | WIP  |            |            |

JavaScript is in-progress — the exporter currently emits Java-flavored code in `.js` files and needs to be rewritten to produce proper JavaScript serialization/deserialization using the `BluePacket` runtime.

## Test Data

- `testdata/Demo.bp` — primary packet definitions for all tests
- `testdata/DemoConvert.bp` — converter feature test definitions
- `testdata/DemoDeprecated.bp` — deprecation feature test definitions
- `testdata/example_rpc.bp` — RPC service definitions
- `testdata/*.bin` — binary test vectors for round-trip verification
- `testdata/Negative*.bp` — parser negative test cases (invalid definitions that must raise `SourceException`)
