# BluePackets

BluePackets is a serialization / deserialization library for many programing languages, focused on simple native data structures.

## Features

- All BluePacket definitions are compiled into simple data structures (classes or structs) native to each language.
- Serialization and deserialization into binary is fast and compact. The binary representations can be further compacted using common compression algorithms, such as gzip.
- BluePacket definitions are composed of common basic data types (byte, int, string, etc.), arrays, and enums.
- BluePacket definitions are compiled into structs or classes source code for your language and are easy to read.
- BluePacket definitions can contain comments that are carried over the generated source code in their native docstring format.
- BluePackets can reference each other (even recursively) within their namespace.
- Compiled BluePackets are native data structures and can be extended or sub-classed normally.

## Usage

To use BluePackets you only need to add one library source file to your project.
You compile BluePackets definitions separately for the languages you need and include them to your projects.

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

All types (built-in and defined) can be in a `list`.

Enums are encoded as a byte and start a zero.
