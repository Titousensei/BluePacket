#! /usr/bin/env nodejs
"use strict";

const fs = require('fs');
const T = require(process.argv[2] || './gen/gen.js')
const TESTDATA_DIR = "../../testdata/"

// ============================================================================
// Test framework
// ============================================================================

let _testsPassed = 0;
let _testsFailed = 0;
let _currentTest = "";

function _assertTrue(x1, msg)
{
    if (!x1) {
        throw new Error("AssertTrue: " + msg);
    }
}

function _assertEqual(x1, x2, msg)
{
    // Deep array comparison
    if (Array.isArray(x1) && Array.isArray(x2)) {
        if (x1.length !== x2.length) {
            throw new Error("AssertEqual: array length " + x1.length + " != " + x2.length + " - " + msg);
        }
        for (let i = 0; i < x1.length; i++) {
            if (x1[i] !== x2[i]) {
                throw new Error("AssertEqual: index " + i + " " + x1[i] + " != " + x2[i] + " - " + msg);
            }
        }
        return;
    }
    if (typeof x1 === 'bigint' || typeof x2 === 'bigint') {
        if (BigInt(x1) !== BigInt(x2)) {
            throw new Error("AssertEqual: " + x1 + " != " + x2 + " - " + msg);
        }
    } else if (x1 !== x2) {
        throw new Error("AssertEqual: " + x1 + " != " + x2 + " - " + msg);
    }
}

function _assertNotEqual(x1, x2, msg)
{
    if (x1 === x2) {
        throw new Error("AssertNotEqual: " + x1 + " == " + x2 + " - " + msg);
    }
}

function _assertThrows(fn, ftype, value, msg)
{
    let caught = false;
    try {
        fn();
    } catch (ex) {
        caught = true;
        if (ex.ftype !== undefined) {
            _assertEqual(ex.ftype, ftype, msg + " ftype");
            _assertEqual(ex.value, value, msg + " value");
        } else if (ftype !== undefined) {
            throw new Error("AssertThrows: expected FieldTypeException with ftype=" + ftype + " but got: " + ex);
        }
    }
    if (!caught) {
        throw new Error("AssertThrows: no exception thrown - " + msg);
    }
}

function _assertThrowsType(fn, msg)
{
    let caught = false;
    try {
        fn();
    } catch (ex) {
        caught = true;
        // just check that any exception was thrown
    }
    if (!caught) {
        throw new Error("AssertThrowsType: no exception thrown - " + msg);
    }
}

function _assertThrowsMessage(fn, expected, msg)
{
    try {
        fn();
    } catch (ex) {
        if (!String(ex.message).includes(expected)) {
            throw new Error("AssertThrowsMessage: expected '" + expected + "' got '" + ex.message + "' - " + msg);
        }
        return;
    }
    throw new Error("AssertThrowsMessage: no exception thrown - " + msg);
}

function _runTest(name, fn)
{
    _currentTest = name;
    try {
        fn();
        _testsPassed++;
        console.log("  PASS: " + name);
    } catch (ex) {
        _testsFailed++;
        console.log("  FAIL: " + name + " - " + ex.message);
    }
}

// ============================================================================
// Test data setup
// ============================================================================

const _TEST_DATA = {};

// DemoPacket
let demoPacket = new T.DemoPacket()
demoPacket.fBoolean = true;
demoPacket.fByte = 99;
demoPacket.fDouble = 1.23456789;
demoPacket.fFloat = 3.14;
demoPacket.fInt = 987654321;
demoPacket.fLong = 101112131415n;
demoPacket.fShort = 2345;
demoPacket.fString = "abcdefåäöàê";
demoPacket.fEnum = T.DemoPacket.MyEnum.MAYBE;
demoPacket.oEnum = T.DemoEnum.NO_DOUBT;
demoPacket.fInner = new T.DemoPacket.MyInner({iInteger: 88});

demoPacket.aInner = [
  new T.DemoPacket.MyInner({iInteger: 777, iEnum: T.DemoPacket.MyEnum.WHOKNOWS}),
  new T.DemoPacket.MyInner({iInteger: 6666}),
];

demoPacket.fOuter = new T.DemoOuter({oInt: 191});
demoPacket.aOuter = [new T.DemoOuter({oInt: 282, oString: ":-)"})];

// DemoPacket2
let demoPacket2 = new T.DemoPacket2();
demoPacket2.aBoolean = [
    true,  false, true,  false, true,  false, true,  false,
    false, true,  false, true,  false, true,  false, true,
    false, false, true
];
demoPacket2.aByte = [99, 98, 97, 96];
demoPacket2.aDouble = [1.23456789, 2.3456789];
demoPacket2.aFloat = [3.14];
demoPacket2.aInt = [987654321, 87654321];
demoPacket2.aLong = [101112131415n, 1617181920n];
demoPacket2.aShort = [2345, 3456, 4567];
demoPacket2.aString = ["abcdef", "xyz", "w", null, "asdfghjkl;"];
demoPacket2.aEmpty = [];
demoPacket2.largeEnum1 = T.DemoEnum260.z8;
demoPacket2.largeEnum2 = T.DemoEnum260.b3;
demoPacket2.aLargeEnum = [T.DemoEnum260.z3, T.DemoEnum260.d7, T.DemoEnum260.z7];

// DemoPacket3
let demoPacket3 = new T.DemoPacket3();
demoPacket3.possible = [T.DemoEnum.NO_DOUBT, T.DemoEnum.YES];
demoPacket.xPacket = demoPacket3;
demoPacket.emptyPacket = new T.DemoPacket0();

// DemoUnsigned
let demoPacketU = new T.DemoUnsigned();
demoPacketU.ub = 200;
demoPacketU.us = 45678;
demoPacketU.lub = [201, 5];
demoPacketU.lus = [43210, 1234];

demoPacketU.a0 = true;
demoPacketU.a1 = false;
demoPacketU.a2 = true;
demoPacketU.a3 = false;
demoPacketU.a4 = true;
demoPacketU.a5 = false;
demoPacketU.a6 = true;
demoPacketU.a7 = false;
demoPacketU.b0 = false;
demoPacketU.b1 = true;
demoPacketU.b2 = false;
demoPacketU.b3 = true;
demoPacketU.b4 = false;
demoPacketU.b5 = true;
demoPacketU.b6 = false;
demoPacketU.b7 = true;
demoPacketU.c0 = false;
demoPacketU.c1 = false;
demoPacketU.c2 = true;

_TEST_DATA['DemoPacket'] = demoPacket;
_TEST_DATA['DemoPacket2'] = demoPacket2;
_TEST_DATA['DemoPacket3'] = demoPacket3;
_TEST_DATA['DemoPacketU'] = demoPacketU;
_TEST_DATA['DemoPacket0'] = new T.DemoPacket0();
_TEST_DATA['BinaryTreeNode'] = new T.BinaryTreeNode({
    data: "root",
    left: new T.BinaryTreeNode({data: "left"}),
    right: new T.BinaryTreeNode({data: "right", left: new T.BinaryTreeNode({data: "right.left"})}),
});

// Load binary test vectors
_TEST_DATA['DemoPacket.bin'] = fs.readFileSync(TESTDATA_DIR + "DemoPacket.bin");
_TEST_DATA['DemoPacket2.bin'] = fs.readFileSync(TESTDATA_DIR + "DemoPacket2.bin");
_TEST_DATA['DemoPacket3.bin'] = fs.readFileSync(TESTDATA_DIR + "DemoPacket3.bin");
_TEST_DATA['DemoPacketU.bin'] = fs.readFileSync(TESTDATA_DIR + "DemoPacketU.bin");
_TEST_DATA['DemoPacket0.bin'] = fs.readFileSync(TESTDATA_DIR + "DemoPacket0.bin");
_TEST_DATA['OuterContainer_list_DemoOuter.bin'] = fs.readFileSync(TESTDATA_DIR + "OuterContainer_list_DemoOuter.bin");
_TEST_DATA['PolyContainer_list_packet_empty.bin'] = fs.readFileSync(TESTDATA_DIR + "PolyContainer_list_packet_empty.bin");
_TEST_DATA['PolyContainer_list_packet.bin'] = fs.readFileSync(TESTDATA_DIR + "PolyContainer_list_packet.bin");

// Load toString expected data
_TEST_DATA['toString.txt'] = fs.readFileSync(TESTDATA_DIR + "toString.txt", "utf-8").trim();
_TEST_DATA['toString2.txt'] = fs.readFileSync(TESTDATA_DIR + "toString2.txt", "utf-8").trim();
_TEST_DATA['toString3.txt'] = fs.readFileSync(TESTDATA_DIR + "toString3.txt", "utf-8").trim();
_TEST_DATA['toStringU.txt'] = fs.readFileSync(TESTDATA_DIR + "toStringU.txt", "utf-8").trim();
_TEST_DATA['toString0.txt'] = fs.readFileSync(TESTDATA_DIR + "toString0.txt", "utf-8").trim();
_TEST_DATA['toStringBT.txt'] = fs.readFileSync(TESTDATA_DIR + "toStringBT.txt", "utf-8").trim();

// ============================================================================
// Packet Hash Tests
// ============================================================================

function testPacketHash(expected, packetClass, label)
{
    _assertEqual(expected, packetClass.packetHash, "testPacketHash " + label);
}

_runTest("testPacketHash DemoPacket", () => {
    testPacketHash(-7655671355778935868n, T.DemoPacket, "DemoPacket");
});

_runTest("testPacketHash DemoPacket2", () => {
    testPacketHash(-2843842372215306214n, T.DemoPacket2, "DemoPacket2");
});

_runTest("testPacketHash DemoPacket3", () => {
    testPacketHash(7017743869305026213n, T.DemoPacket3, "DemoPacket3");
});

_runTest("testPacketHash DemoUnsigned", () => {
    testPacketHash(4436886959950420991n, T.DemoUnsigned, "DemoUnsigned");
});

_runTest("testPacketHash DemoPacket0", () => {
    testPacketHash(-5693327742438229220n, T.DemoPacket0, "DemoPacket0");
});

_runTest("testPacketHash BinaryTreeNode", () => {
    testPacketHash(-7371488707278340539n, T.BinaryTreeNode, "BinaryTreeNode");
});

_runTest("testPacketHash DemoPacketAbs1", () => {
    testPacketHash(3438895385741716791n, T.DemoPacketAbs1, "DemoPacketAbs1");
});

_runTest("testPacketHash DemoPacketAbs2", () => {
    testPacketHash(4772161707595727023n, T.DemoPacketAbs2, "DemoPacketAbs2");
});

_runTest("testPacketHash DemoPacketAbs12", () => {
    testPacketHash(7137313653103464500n, T.DemoPacketAbs12, "DemoPacketAbs12");
});

_runTest("testPacketHash deprecated", () => {
    testPacketHash(4595915063677747513n, T.DemoVersion__3FC7F86674610139, "DemoVersion deprecated");
    testPacketHash(7260826007793545337n, T.DemoVersion, "DemoVersion");
    testPacketHash(4428920953148694937n, T.DemoIncludeVersion__3D76B02436B66199, "DemoIncludeVersion deprecated");
    testPacketHash(-4044184110803273943n, T.DemoIncludeVersion, "DemoIncludeVersion");
});

// ============================================================================
// Serialize Tests
// ============================================================================

function _testSerialize(binKey, packetKey)
{
    let data = _TEST_DATA[packetKey].serialize();
    let expected = _TEST_DATA[binKey];
    _assertEqual(expected.length, data.length, "_testSerialize length " + packetKey);
    for (let i = 0; i < expected.length; i++) {
        _assertEqual(expected[i], data[i], "_testSerialize byte[" + i + "] " + packetKey);
    }
}

_runTest("testSerialize DemoPacket", () => {
    _testSerialize('DemoPacket.bin', 'DemoPacket');
});

_runTest("testSerialize DemoPacket2", () => {
    _testSerialize('DemoPacket2.bin', 'DemoPacket2');
});

_runTest("testSerialize DemoPacket3", () => {
    _testSerialize('DemoPacket3.bin', 'DemoPacket3');
});

_runTest("testSerialize DemoUnsigned", () => {
    _testSerialize('DemoPacketU.bin', 'DemoPacketU');
});

_runTest("testSerialize DemoPacket0", () => {
    _testSerialize('DemoPacket0.bin', 'DemoPacket0');
});

_runTest("testSerialize BinaryTreeNode round-trip", () => {
    let tree = _TEST_DATA['BinaryTreeNode'];
    let round = T.registry.deserialize(tree.serialize());
    _assertEqual(tree.toString(), round.toString(), "BinaryTreeNode round-trip");
    _assertEqual("right.left", round.right.left.data, "BinaryTreeNode nested field");
});

// ============================================================================
// Deserialize Tests
// ============================================================================

function _testDeserialize(binKey, packetKey)
{
    let bp = T.registry.deserialize(_TEST_DATA[binKey]);
    _assertEqual(_TEST_DATA[packetKey].toString(), bp.toString(), "_testDeserialize " + packetKey);
}

_runTest("testDeserialize DemoPacket", () => {
    _testDeserialize('DemoPacket.bin', 'DemoPacket');
});

_runTest("testDeserialize DemoPacket2", () => {
    _testDeserialize('DemoPacket2.bin', 'DemoPacket2');
});

_runTest("testDeserialize DemoPacket3", () => {
    _testDeserialize('DemoPacket3.bin', 'DemoPacket3');
});

_runTest("testDeserialize DemoUnsigned", () => {
    _testDeserialize('DemoPacketU.bin', 'DemoPacketU');
});

_runTest("testDeserialize DemoPacket0", () => {
    _testDeserialize('DemoPacket0.bin', 'DemoPacket0');
});

// ============================================================================
// ToString Tests
// ============================================================================

function _testToString(tostringKey, packetKey)
{
    _assertEqual(_TEST_DATA[tostringKey], _TEST_DATA[packetKey].toString(), "_testToString " + packetKey);
}

_runTest("testToString DemoPacket", () => {
    _testToString('toString.txt', 'DemoPacket');
});

_runTest("testToString DemoPacket2", () => {
    _testToString('toString2.txt', 'DemoPacket2');
});

_runTest("testToString DemoPacket3", () => {
    _testToString('toString3.txt', 'DemoPacket3');
});

_runTest("testToString DemoUnsigned", () => {
    _testToString('toStringU.txt', 'DemoPacketU');
});

_runTest("testToString DemoPacket0", () => {
    _testToString('toString0.txt', 'DemoPacket0');
});

_runTest("testToString BinaryTreeNode", () => {
    _testToString('toStringBT.txt', 'BinaryTreeNode');
});

// ============================================================================
// Unsigned Tests
// ============================================================================

_runTest("testUnsigned values", () => {
    let p0 = _TEST_DATA["DemoPacketU"];
    _assertEqual(200, p0.ub, "ub");
    _assertEqual(45678, p0.us, "us");
    _assertEqual([201, 5], p0.lub, "lub");
    _assertEqual([43210, 1234], p0.lus, "lus");
});

_runTest("testUnsigned signed byte/short round-trip", () => {
    let p1 = new T.DemoPacket();
    p1.fByte = -99;
    p1.fShort = -2345;
    _assertEqual(-99, p1.fByte, "fByte");
    _assertEqual(-2345, p1.fShort, "fShort");

    let p2 = new T.DemoPacket2();
    p2.aByte = [-99, 98, -97, 96];
    p2.aShort = [2345, -3456, 4567];
    _assertEqual([-99, 98, -97, 96], p2.aByte, "aByte");
    _assertEqual([2345, -3456, 4567], p2.aShort, "aShort");
});

_runTest("testUnsigned toSignedByte", () => {
    _assertEqual(-56, T.toSignedByte(200), "toSignedByte(200)");
});

_runTest("testUnsigned toSignedShort", () => {
    _assertEqual(-19858, T.toSignedShort(45678), "toSignedShort(45678)");
});

_runTest("testUnsigned toUnsignedByte", () => {
    _assertEqual(200, T.toUnsignedByte(-56), "toUnsignedByte(-56)");
});

_runTest("testUnsigned toUnsignedShort", () => {
    _assertEqual(45678, T.toUnsignedShort(-19858), "toUnsignedShort(-19858)");
});

_runTest("testUnsigned boundaries", () => {
    _assertEqual(127, T.toSignedByte(127), "toSignedByte(127)");
    _assertEqual(-1, T.toSignedByte(255), "toSignedByte(255)");
    _assertEqual(32767, T.toSignedShort(32767), "toSignedShort(32767)");
    _assertEqual(-1, T.toSignedShort(65535), "toSignedShort(65535)");
});

// ============================================================================
// Long Tests
// ============================================================================

_runTest("testLong default is BigInt", () => {
    let p = new T.DemoPacket();
    _assertEqual(0n, p.fLong, "fLong default");
});

_runTest("testLong 64-bit values", () => {
    let p = new T.DemoPacket();
    p.fLong = 0x7FFFFFFFFFFFFFFFn;
    _assertEqual(0x7FFFFFFFFFFFFFFFn, p.fLong, "fLong max");
    _assertEqual(0x7FFFFFFFFFFFFFFFn, T.registry.deserialize(p.serialize()).fLong, "fLong max round-trip");

    p.fLong = -1n;
    _assertEqual(-1n, T.registry.deserialize(p.serialize()).fLong, "fLong -1 round-trip");

    let p2 = new T.DemoPacket2();
    p2.aLong = [0x7FFFFFFFFFFFFFFFn, -1n];
    _assertEqual([0x7FFFFFFFFFFFFFFFn, -1n], T.registry.deserialize(p2.serialize()).aLong, "aLong round-trip");
});

// ============================================================================
// Sequence Length Tests
// ============================================================================

_runTest("testLongString round-trip", () => {
    let text = "x".repeat(300);
    let round = T.registry.deserialize(new T.DemoPacket({fLongstring: text}).serialize());
    _assertEqual(text, round.fLongstring, "fLongstring 300 chars");
});

_runTest("testLongList round-trip", () => {
    let text = [];
    for (let i = 0; i < 300; i++) text.push("v" + i);
    let round = T.registry.deserialize(new T.DemoPacket2({aString: text}).serialize());
    _assertEqual(300, round.aString.length, "aString length");
    _assertEqual(text, round.aString, "aString 300 elements");
});

// ============================================================================
// Float Tests
// ============================================================================

_runTest("testFloat large values", () => {
    for (const v of [1e7, 1234567, 3.4e38]) {
        const round = T.registry.deserialize(new T.DemoPacket({fFloat: v}).serialize());
        _assertEqual(v, round.fFloat, "fFloat " + v);
    }
});

_runTest("testFloat shortest precision", () => {
    const round = T.registry.deserialize(new T.DemoPacket({fFloat: 1.23456789}).serialize());
    _assertEqual(1.2345679, round.fFloat, "fFloat shortest precision");
});

_runTest("testFloat small values", () => {
    const round = T.registry.deserialize(new T.DemoPacket({fFloat: 1e-45}).serialize());
    _assertTrue(round.fFloat > 0 && round.fFloat < 1e-44, "fFloat subnormal");
});

// ============================================================================
// Unknown Enum Tests
// ============================================================================

_runTest("testUnknownEnum scalar", () => {
    const b = new T.DemoPacket({oEnum: T.DemoEnum.NO_DOUBT}).serialize();
    b[b.length - 9] = 99; // oEnum precedes the 8-byte xPacket hash
    _assertThrowsMessage(() => T.registry.deserialize(b), "Unknown DemoEnum value: 99", "unknown scalar enum");
});

_runTest("testUnknownEnum list", () => {
    const inner = new T.DemoPacket.MyInner({
        aEnum: [T.DemoPacket.MyEnum.MAYBE],
        iEnum: T.DemoPacket.MyEnum.POSSIBLE,
        iInteger: 5,
    });
    const b = new T.DemoPacket({fInner: inner}).serialize();
    const marker = Buffer.from([0x01, 0x01, 0x01, 0x02, 0x00, 0x00, 0x00, 0x05]);
    const at = b.indexOf(marker);
    _assertTrue(at >= 0, "inner marker not found");
    b[at + 2] = 99;
    _assertThrowsMessage(() => T.registry.deserialize(b), "Unknown MyEnum value: 99", "unknown enum in list");
});

// ============================================================================
// JSON Tests
// ============================================================================

_runTest("testJSON default long", () => {
    const json = JSON.parse(JSON.stringify(new T.DemoPacket()));
    _assertEqual("0", json.fLong, "default fLong as decimal string");
});

_runTest("testJSON long value", () => {
    const json = JSON.parse(JSON.stringify(new T.DemoPacket({fLong: 101112131415n})));
    _assertEqual("101112131415", json.fLong, "fLong as decimal string");
});

_runTest("testJSON long list", () => {
    const json = JSON.parse(JSON.stringify(new T.DemoPacket2({aLong: [1n, 2n]})));
    _assertEqual(["1", "2"], json.aLong, "aLong as decimal strings");
});

_runTest("testJSON nested long", () => {
    const json = JSON.parse(JSON.stringify(new T.DemoPacket({
        xPacket: new T.DemoPacket({fLong: 5n}),
    })));
    _assertEqual("5", json.xPacket.fLong, "nested fLong as decimal string");
});

_runTest("testJSON long round-trip", () => {
    const packet = new T.DemoPacket({fLong: 101112131415n, fString: "x"});
    const data = JSON.parse(JSON.stringify(packet));
    const restored = new T.DemoPacket({...data, fLong: BigInt(data.fLong)});
    _assertEqual(packet.fLong, restored.fLong, "fLong round-trip");
    _assertEqual(packet.fString, restored.fString, "fString round-trip");
});

_runTest("testJSON circular", () => {
    const packet = new T.DemoPacket();
    packet.xPacket = packet;
    _assertThrowsMessage(() => JSON.stringify(packet), "circular", "circular packet");
});

// ============================================================================
// Default Round-trip Tests
// ============================================================================

_runTest("testDefault string is empty", () => {
    const packet = new T.DemoPacket();
    _assertEqual("", packet.fString, "default fString");
    _assertEqual("", packet.fLongstring, "default fLongstring");
});

_runTest("testDefault round-trip", () => {
    const classes = Object.values(T).filter(
        (v) => typeof v === 'function' && v.TYPE_INFO && v.packetHash !== undefined
    );
    _assertTrue(classes.length > 0, "no packet classes found");
    for (const cls of classes) {
        const packet = new cls();
        const bytes = packet.serialize();
        const round = T.registry.deserialize(bytes);
        _assertEqual(JSON.stringify(packet), JSON.stringify(round), "default values " + cls.name);
        _assertEqual(bytes.toString("hex"), round.serialize().toString("hex"), "default bytes " + cls.name);
    }
});

_runTest("testExplicit null string normalizes", () => {
    const packet = new T.DemoPacket({fString: null});
    const round = T.registry.deserialize(packet.serialize());
    _assertEqual("", round.fString, "null fString becomes empty");
});

// ============================================================================
// Extension Contract Tests
// ============================================================================

_runTest("testSubclass methods", () => {
    class MethodSub extends T.DemoPacket {
        helper() { return 42; }
    }
    const packet = new MethodSub({fInt: 5});
    _assertTrue(packet instanceof T.DemoPacket, "subclass is a DemoPacket");
    _assertEqual(42, packet.helper(), "subclass helper");
    _assertEqual(5, packet.fInt, "subclass inherits fields");
});

_runTest("testSubclass fields rejected", () => {
    class FieldSub extends T.DemoPacket {
        constructor(options) {
            super(options);
            this.extra = 1;
        }
    }
    _assertThrowsType(() => new FieldSub({}), "subclass field");
});

// ============================================================================
// Constructor Tests
// ============================================================================

_runTest("testConstructor options and defaults", () => {
    let inner = new T.DemoPacket.MyInner({iInteger: 7});
    let p = new T.DemoPacket({fInt: 42, aInner: [inner]});

    _assertEqual(42, p.fInt, "fInt from options");
    _assertEqual(1, p.aInner.length, "aInner from options");
    _assertEqual(7, p.aInner[0].iInteger, "inner field from options");
    _assertEqual(false, p.fBoolean, "bool default");
    _assertEqual(0n, p.fLong, "long default");
    _assertEqual("", p.fString, "string default");
    _assertEqual(T.DemoPacket.MyEnum.DUNNO, p.fEnum, "inner enum default");
    _assertEqual(T.DemoEnum.YES, p.oEnum, "outer enum default");
    _assertEqual(null, p.fInner, "packet default");
});

_runTest("testConstructor list defaults are not shared", () => {
    let p1 = new T.DemoPacket();
    let p2 = new T.DemoPacket();
    _assertTrue(p1.aInner !== p2.aInner, "list default instances differ");
});

_runTest("testConstructor unknown field", () => {
    _assertThrowsType(() => new T.DemoPacket({fIntt: 1}), "unknown field");
});

_runTest("testConstructor positional args", () => {
    _assertThrowsType(() => new T.DemoOuter(282, ":-)"), "two positional args");
    _assertThrowsType(() => new T.DemoOuter(282), "one positional arg");
});

// ============================================================================
// Enum Strictness Tests
// ============================================================================

_runTest("testEnum type mismatch", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fEnum = T.DemoEnum.YES; }, "MyEnum", T.DemoEnum.YES, "fEnum=DemoEnum");
    _assertThrows(() => { data.oEnum = T.DemoPacket.MyEnum.MAYBE; }, "DemoEnum", T.DemoPacket.MyEnum.MAYBE, "oEnum=MyEnum");
    _assertThrows(() => { data.fEnum = 1; }, "MyEnum", 1, "fEnum=1");
});

_runTest("testEnum list type mismatch", () => {
    let data = new T.DemoPacket3();
    _assertThrows(() => { data.possible = [T.DemoEnum.YES, T.DemoPacket.MyEnum.MAYBE]; },
        "DemoEnum in list", T.DemoPacket.MyEnum.MAYBE, "possible mixed enums");
});

// ============================================================================
// Empty Packet Field Tests
// ============================================================================

_runTest("testEmptyPacketField", () => {
    let p = new T.DemoPacket({emptyPacket: new T.DemoPacket0()});
    let round = T.registry.deserialize(p.serialize());
    _assertTrue(round.emptyPacket instanceof T.DemoPacket0, "emptyPacket round-trip");
});

_runTest("testUnknownPacketHash", () => {
    _assertThrowsType(() => T.registry.deserialize(Buffer.from([0, 0, 0, 0, 0, 0, 0, 1])), "unknown packet hash");
});

// ============================================================================
// Negative Tests - Bool
// ============================================================================

_runTest("testSetBoolNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fBoolean = 0; }, "bool", 0, "fBoolean=0");
});

// ============================================================================
// Negative Tests - Byte
// ============================================================================

_runTest("testSetByteNegative -1000", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = -1000; }, "byte", -1000, "fByte=-1000");
});

_runTest("testSetByteNegative 1000", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = 1000; }, "byte", 1000, "fByte=1000");
});

_runTest("testSetByteNegative true", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = true; }, "byte", true, "fByte=true");
});

_runTest("testSetByteNegative 200", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = 200; }, "byte", 200, "fByte=200");
});

_runTest("testSetByteNegative -129", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = -129; }, "byte", -129, "fByte=-129");
});

_runTest("testSetByteNegative 128", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fByte = 128; }, "byte", 128, "fByte=128");
});

// Byte boundary
_runTest("testSetByteBoundary -128", () => {
    let data = new T.DemoPacket();
    data.fByte = -128;
    _assertEqual(-128, data.fByte, "fByte=-128");
});

_runTest("testSetByteBoundary 10", () => {
    let data = new T.DemoPacket();
    data.fByte = 10;
    _assertEqual(10, data.fByte, "fByte=10");
});

_runTest("testSetByteBoundary 127", () => {
    let data = new T.DemoPacket();
    data.fByte = 127;
    _assertEqual(127, data.fByte, "fByte=127");
});

// ============================================================================
// Negative Tests - Unsigned Byte
// ============================================================================

_runTest("testSetUnsignedByteNegative -1000", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = -1000; }, "ubyte", -1000, "ub=-1000");
});

_runTest("testSetUnsignedByteNegative 1000", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = 1000; }, "ubyte", 1000, "ub=1000");
});

_runTest("testSetUnsignedByteNegative true", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = true; }, "ubyte", true, "ub=true");
});

_runTest("testSetUnsignedByteNegative -100", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = -100; }, "ubyte", -100, "ub=-100");
});

_runTest("testSetUnsignedByteNegative -1", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = -1; }, "ubyte", -1, "ub=-1");
});

_runTest("testSetUnsignedByteNegative 256", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.ub = 256; }, "ubyte", 256, "ub=256");
});

// Unsigned byte boundary
_runTest("testSetUnsignedByteBoundary 0", () => {
    let data = new T.DemoUnsigned();
    data.ub = 0;
    _assertEqual(0, data.ub, "ub=0");
});

_runTest("testSetUnsignedByteBoundary 10", () => {
    let data = new T.DemoUnsigned();
    data.ub = 10;
    _assertEqual(10, data.ub, "ub=10");
});

_runTest("testSetUnsignedByteBoundary 255", () => {
    let data = new T.DemoUnsigned();
    data.ub = 255;
    _assertEqual(255, data.ub, "ub=255");
});

// ============================================================================
// Negative Tests - Short
// ============================================================================

_runTest("testSetShortNegative -1000000", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = -1000000; }, "short", -1000000, "fShort=-1000000");
});

_runTest("testSetShortNegative 1000000", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = 1000000; }, "short", 1000000, "fShort=1000000");
});

_runTest("testSetShortNegative true", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = true; }, "short", true, "fShort=true");
});

_runTest("testSetShortNegative 40000", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = 40000; }, "short", 40000, "fShort=40000");
});

_runTest("testSetShortNegative -32769", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = -32769; }, "short", -32769, "fShort=-32769");
});

_runTest("testSetShortNegative 32768", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fShort = 32768; }, "short", 32768, "fShort=32768");
});

// Short boundary
_runTest("testSetShortBoundary -32768", () => {
    let data = new T.DemoPacket();
    data.fShort = -32768;
    _assertEqual(-32768, data.fShort, "fShort=-32768");
});

_runTest("testSetShortBoundary 1000", () => {
    let data = new T.DemoPacket();
    data.fShort = 1000;
    _assertEqual(1000, data.fShort, "fShort=1000");
});

_runTest("testSetShortBoundary 32767", () => {
    let data = new T.DemoPacket();
    data.fShort = 32767;
    _assertEqual(32767, data.fShort, "fShort=32767");
});

// ============================================================================
// Negative Tests - Unsigned Short
// ============================================================================

_runTest("testSetUnsignedShortNegative -1000000", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = -1000000; }, "ushort", -1000000, "us=-1000000");
});

_runTest("testSetUnsignedShortNegative 1000000", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = 1000000; }, "ushort", 1000000, "us=1000000");
});

_runTest("testSetUnsignedShortNegative true", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = true; }, "ushort", true, "us=true");
});

_runTest("testSetUnsignedShortNegative 90000", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = 90000; }, "ushort", 90000, "us=90000");
});

_runTest("testSetUnsignedShortNegative -1", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = -1; }, "ushort", -1, "us=-1");
});

_runTest("testSetUnsignedShortNegative 65536", () => {
    let data = new T.DemoUnsigned();
    _assertThrows(() => { data.us = 65536; }, "ushort", 65536, "us=65536");
});

// Unsigned short boundary
_runTest("testSetUnsignedShortBoundary 0", () => {
    let data = new T.DemoUnsigned();
    data.us = 0;
    _assertEqual(0, data.us, "us=0");
});

_runTest("testSetUnsignedShortBoundary 1000", () => {
    let data = new T.DemoUnsigned();
    data.us = 1000;
    _assertEqual(1000, data.us, "us=1000");
});

_runTest("testSetUnsignedShortBoundary 65535", () => {
    let data = new T.DemoUnsigned();
    data.us = 65535;
    _assertEqual(65535, data.us, "us=65535");
});

// ============================================================================
// Negative Tests - Int, Long, Float, Double
// ============================================================================

_runTest("testSetIntNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fInt = "abc"; }, "int", "abc", "fInt=abc");
});

_runTest("testSetLongNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fLong = 1.2; }, "long", 1.2, "fLong=1.2");
});

_runTest("testSetFloatNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fFloat = false; }, "float", false, "fFloat=false");
});

_runTest("testSetDoubleNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fDouble = "123"; }, "double", "123", "fDouble=123");
});

// ============================================================================
// Negative Tests - Packet
// ============================================================================

_runTest("testSetPacketNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.xPacket = "x"; }, "packet", "x", "xPacket=x");
});

// ============================================================================
// Negative Tests - String
// ============================================================================

_runTest("testSetStringNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fString = -1000; }, "string", -1000, "fString=-1000");
});

// ============================================================================
// Negative Tests - Inner class
// ============================================================================

_runTest("testSetInnerNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fInner = -1000; }, "MyInner", -1000, "fInner=-1000");
});

_runTest("testSetInnerListNegative1", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.aInner = -1000; }, "list MyInner", -1000, "aInner=-1000");
});

_runTest("testSetInnerListNegative2", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.aInner = [1, 2, 3]; }, "MyInner in list", 1, "aInner=[1,2,3]");
});

// ============================================================================
// Negative Tests - Enum
// ============================================================================

_runTest("testSetEnumNegative", () => {
    let data = new T.DemoPacket();
    _assertThrows(() => { data.fEnum = -1000; }, "MyEnum", -1000, "fEnum=-1000");
});

_runTest("testSetEnumListNegative1", () => {
    let data = new T.DemoPacket3();
    _assertThrows(() => { data.possible = -999; }, "list DemoEnum", -999, "possible=-999");
});

_runTest("testSetEnumListNegative2", () => {
    let data = new T.DemoPacket3();
    _assertThrows(() => { data.possible = T.DemoEnum.YES; }, "list DemoEnum", T.DemoEnum.YES, "possible=DemoEnum.YES");
});

// ============================================================================
// Abstract Tests
// ============================================================================

_runTest("testAbstract DemoPacketAbs1", () => {
    let packet = new T.DemoPacketAbs1();
    _assertTrue(packet instanceof T.DemoAbstract1, "DemoPacketAbs1 instanceof DemoAbstract1");
});

_runTest("testAbstract DemoPacketAbs2", () => {
    let packet = new T.DemoPacketAbs2();
    _assertTrue(packet instanceof T.DemoAbstract2, "DemoPacketAbs2 instanceof DemoAbstract2");
});

_runTest("testAbstract DemoPacketAbs12", () => {
    let packet = new T.DemoPacketAbs12();
    _assertTrue(packet instanceof T.DemoAbstract1, "DemoPacketAbs12 instanceof DemoAbstract1");
    _assertTrue(packet instanceof T.DemoAbstract2, "DemoPacketAbs12 instanceof DemoAbstract2");
});

_runTest("testNotAbstract DemoPacketAbs1 not DemoAbstract2", () => {
    let packet = new T.DemoPacketAbs1();
    _assertTrue(!(packet instanceof T.DemoAbstract2), "DemoPacketAbs1 not instanceof DemoAbstract2");
});

_runTest("testNotAbstract DemoPacketAbs2 not DemoAbstract1", () => {
    let packet = new T.DemoPacketAbs2();
    _assertTrue(!(packet instanceof T.DemoAbstract1), "DemoPacketAbs2 not instanceof DemoAbstract1");
});

// ============================================================================
// Convert Tests
// ============================================================================

_runTest("testConvert", () => {
    let id = 123;
    let text = ["line1", "line2"];
    let d1 = new T.DemoFirst({id: id, text: text});
    let d2 = T.DemoSecond.convertDemoFirst(d1);
    _assertEqual(id, d2.id, "convert id");
    _assertEqual(text, d2.text, "convert text");

    let actualConvert1 = d1.convert().map(p => p.packetHash);
    _assertEqual(0, actualConvert1.length, "Empty List of convertible BluePackets for DemoFirst");

    let expectedConvert2 = [d1.packetHash];
    let actualConvert2 = d2.convert().map(p => p.packetHash);
    _assertEqual(expectedConvert2, actualConvert2, "List of convertible BluePackets for DemoSecond");
});

_runTest("testConvertNegative", () => {
    let packet = new T.DemoOuter({oInt: 999});
    _assertThrowsType(() => {
        T.DemoSecond.convertDemoFirst(packet);
    }, "convertDemoFirst with wrong type");
});

// ============================================================================
// List Packet Encoding Tests
// ============================================================================

_runTest("testListPacketEncoding list DemoOuter", () => {
    let expected = _TEST_DATA['OuterContainer_list_DemoOuter.bin'];
    let oc = new T.OuterContainer();
    oc.outerList = [
        new T.DemoOuter({oInt: 1, oString: 'a'}),
        new T.DemoOuter({oInt: 2, oString: 'b'})
    ];
    let data = oc.serialize();
    _assertEqual(expected.length, data.length, "list DemoOuter length");
    for (let i = 0; i < expected.length; i++) {
        _assertEqual(expected[i], data[i], "list DemoOuter byte[" + i + "]");
    }
    
    // Round-trip
    let restored = T.registry.deserialize(data);
    _assertEqual(2, restored.outerList.length, "outerList length");
    _assertEqual(1, restored.outerList[0].oInt, "outerList[0].oInt");
    _assertEqual('a', restored.outerList[0].oString, "outerList[0].oString");
    _assertEqual(2, restored.outerList[1].oInt, "outerList[1].oInt");
    _assertEqual('b', restored.outerList[1].oString, "outerList[1].oString");
});

_runTest("testListPacketEncoding list packet empty", () => {
    let expected = _TEST_DATA['PolyContainer_list_packet_empty.bin'];
    let pc = new T.PolyContainer();
    pc.polyList = [];
    let data = pc.serialize();
    _assertEqual(expected.length, data.length, "list packet empty length");
    for (let i = 0; i < expected.length; i++) {
        _assertEqual(expected[i], data[i], "list packet empty byte[" + i + "]");
    }
});

_runTest("testListPacketEncoding list packet", () => {
    let expected = _TEST_DATA['PolyContainer_list_packet.bin'];
    let pc = new T.PolyContainer();
    pc.polyList = [
        new T.DemoOuter({oInt: 10, oString: 'x'}),
        new T.DemoOuter({oInt: 20, oString: 'y'})
    ];
    let data = pc.serialize();
    _assertEqual(expected.length, data.length, "list packet length");
    for (let i = 0; i < expected.length; i++) {
        _assertEqual(expected[i], data[i], "list packet byte[" + i + "]");
    }
    
    // Round-trip
    let restored = T.registry.deserialize(data);
    _assertEqual(2, restored.polyList.length, "polyList length");
    _assertEqual(10, restored.polyList[0].oInt, "polyList[0].oInt");
    _assertEqual('x', restored.polyList[0].oString, "polyList[0].oString");
    _assertEqual(20, restored.polyList[1].oInt, "polyList[1].oInt");
    _assertEqual('y', restored.polyList[1].oString, "polyList[1].oString");
});

// ============================================================================
// API Version Tests
// ============================================================================

_runTest("testApiVersion", () => {
    _assertTrue(T.BluePacketAPI.VERSION !== 0, "VERSION != 0");
    _assertTrue(T.BluePacketAPI.VERSION_HEX !== null, "VERSION_HEX not null");
    _assertTrue(T.BluePacketAPI.VERSION_HEX !== "", "VERSION_HEX not empty");
});

// ============================================================================
// Named Params Constructor Tests
// ============================================================================

_runTest("testForceInitNamedParamsNegative", () => {
    _assertThrowsType(() => {
        new T.DemoOuter(282, ":-)");
    }, "DemoOuter positional args");
});

// ============================================================================
// Results
// ============================================================================

console.log("");
console.log("=== RESULTS ===");
console.log("Passed: " + _testsPassed);
console.log("Failed: " + _testsFailed);
if (_testsFailed > 0) {
    process.exit(1);
}
