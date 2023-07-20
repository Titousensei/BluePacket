# BluePacket

BluePacket is a serialization / deserialization library for many programing languages, focused on simple native data structures.
We aim to support as many languages as possible, from the mainstream ones to the more experimental.

## Features

- BluePacket definitions are compiled into simple data structures (classes or structs) native and idiomatic to each language.
- Serialization and deserialization into binary is fast and compact. The binary representations can be further compacted using common compression algorithms, such as gzip.
- BluePacket definitions are composed of common basic data types (byte, int, string, etc.), arrays, and enums.
- BluePacket definitions can contain comments that are carried over the generated source code in their native docstring format.
- BluePackets can reference each other (even recursively) within their namespace.

## Usage

To use BluePacket you only need to add one library source file to your project, as well as one exporter for each language supported. The exporter script is in python 3.
You compile BluePacket definitions into source code separately for the languages you need, and include them to your projects.

## Example

```
Person:
  string firstName
  string lastName
  Date birthDate
  list Phone phoneNumbers

  # inner struct defined inside Person
  Phone:
    string number
    PhoneType type

  PhoneType: enum
    Mobile, Home, Work

# Global definition, usable everywhere
Date:
  short year
  byte month
  byte day
```

## Built-in types:

- byte (signed)
- short (signed)
- int (signed)
- long (signed)
- ubyte (unsigned)
- ushort (unsigned)
- bool
- string

In addition to built-in types, fields can be a defined BluePacket type, or an Enums. All types (built-in and defined) can be in a `list`.

Enums are encoded as a byte or a short, start a zero and are auto-incremented.

## Implemented Features

| Language | de/ser | const | bptext | bpbin | distri | rpc client | rpc server | connected client | connected server |
| -------- | ------ | ----- | ------ | ----- | ------ | ---------- | ---------- | ---------------- | ---------------- |
| Java     |    Y   |       |        |       |        |     Y      |     Y      |                  |                  |
| Python   |    Y   |       |        |       |        |     Y      |            |                  |                  |
| C#       |    Y   |       |        |       |        |            |            |                  |                  |
| Go       |    Y   |       |        |       |        |            |            |                  |                  |
| C / C++  |        |       |        |       |        |            |            |                  |                  |
| Rust     |        |       |        |       |        |            |            |                  |                  |
| Zig      |        |       |        |       |        |            |            |                  |                  |
| Javascript |      |       |        |       |        |            |            |                  |                  |
| Lua      |        |       |        |       |        |            |            |                  |                  |

## F.A.Q.

- (java) why are the generated files final? I want to subclass some of them.
  - subclasses would not be de/serializable while still being of type BluePacket, so we have to prevent subclassing.
  - if what you want is to add information (member variables): you can create your own class that has your BluePacket as one member variable (composition)
  - if what you want is to add methods: you can have util static methods that use your BluePacket class as one input parameter
