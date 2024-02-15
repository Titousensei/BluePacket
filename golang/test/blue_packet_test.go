package test

import (
	"encoding/hex"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"

	"github.com/bluepacket"
	. "github.com/bluepacketdemo"
)

const testDataDir = "../../testdata/"

func assertEquals(t *testing.T, testid string, expected any, actual any) {
	if expected == actual {
		return
	}
	t.Log(
		fmt.Sprintf("ERROR - %s: should be %s (%s), but got %s (%s)",
			testid,
			fmt.Sprint(expected),
			reflect.TypeOf(expected),
			fmt.Sprint(actual),
			reflect.TypeOf(actual),
		),
	)
	t.Fail()
}

func assertTrue(t *testing.T, testid string, value bool) {
	if value {
		return
	}
	t.Log(fmt.Sprintf("ERROR - %s not true", testid))
	t.Fail()
}

type testData struct {
	demoPacket    DemoPacket
	demoPacketBin []byte

	demoPacket2    DemoPacket2
	demoPacket2Bin []byte

	demoPacket3    DemoPacket3
	demoPacket3Bin []byte

	demoPacketU    DemoUnsigned
	demoPacketUBin []byte
}

func readFile(t *testing.T, path string) []byte {
	bin, ok := os.ReadFile(testDataDir + path)
	if ok != nil {
		t.Log("ERROR - Can't load " + testDataDir + path)
		t.Fail()
	}
	return bin
}

func setUp(t *testing.T) testData {

	data := testData{
		demoPacket: DemoPacket{
			FBoolean: true,
			FByte:    int8(99),
			FDouble:  1.23456789,
			FFloat:   3.14,
			FInt:     987654321,
			FLong:    101112131415,
			FShort:   2345,
			FString:  "abcdefåäöàê",
			FEnum:    DemoPacketMyEnumMAYBE,
			OEnum:    DemoEnumNO_DOUBT,
			FInner:   &DemoPacketMyInner{IInteger: 88},
		},

		demoPacketBin: readFile(t, "DemoPacket.bin"),

		demoPacket2: DemoPacket2{
			ABoolean:   []bool{
				true, false, true, false, true, false, true, false,
				false, true, false, true, false, true, false, true,
				false, false, true,
			},
			AByte:      []int8{99, 98, 97, 96},
			ADouble:    []float64{1.23456789, 2.3456789},
			AFloat:     []float32{3.14},
			AInt:       []int32{987654321, 87654321},
			ALong:      []int64{101112131415, 1617181920},
			AShort:     []int16{2345, 3456, 4567},
			AString:    []string{"abcdef", "xyz", "w", "", "asdfghjkl;"},
			AEmpty:     []string{},
		        LargeEnum1: DemoEnum260z8,
		        LargeEnum2: DemoEnum260b3,
		        ALargeEnum: []DemoEnum260{DemoEnum260z3, DemoEnum260d7, DemoEnum260z7},
		},

		demoPacket2Bin: readFile(t, "DemoPacket2.bin"),

		demoPacket3: DemoPacket3{
			Possible: []DemoEnum{DemoEnumNO_DOUBT, DemoEnumYES},
		},

		demoPacket3Bin: readFile(t, "DemoPacket3.bin"),

		demoPacketU: DemoUnsigned{
			Ub:  200,
			Us:  45678,
			Lub: []byte{201, 5},
			Lus: []uint16{43210, 1234},
			A0: true,
			A1: false,
			A2: true,
			A3: false,
			A4: true,
			A5: false,
			A6: true,
			A7: false,
			B0: false,
			B1: true,
			B2: false,
			B3: true,
			B4: false,
			B5: true,
			B6: false,
			B7: true,
			C0: false,
			C1: false,
			C2: true,
		},

		demoPacketUBin: readFile(t, "DemoPacketU.bin"),
	}
	inner := []*DemoPacketMyInner{
		&DemoPacketMyInner{IInteger: 777},
		&DemoPacketMyInner{IInteger: 6666},
	}

	data.demoPacket.AInner = inner
	data.demoPacket.FOuter = &DemoOuter{OInt: 191}
	data.demoPacket.AOuter = []*DemoOuter{
		&DemoOuter{OInt: 282, OString: ":-)"},
	}

	// FIXME: is there a better way to cast?
	var packet3 bluepacket.BluePacket
	packet3 = &data.demoPacket3
	data.demoPacket.XPacket = &packet3

	bluepacket.Register(&DemoPacket{})
	bluepacket.Register(&DemoPacket2{})
	bluepacket.Register(&DemoPacket3{})
	bluepacket.Register(&DemoUnsigned{})

	return data
}

func testToString(t *testing.T, testname string, filename string, packet bluepacket.BluePacket) {
	t.Log("-- " + testname)
	bin, _ := os.ReadFile(testDataDir + filename)
	expected := strings.ToLower(strings.Trim(string(bin), "\n "))
	actual := strings.ToLower(packet.String())
	actual = strings.Replace(actual, "demopacketmyinner", "myinner", -1)
	assertEquals(t, "String().ToLower()", expected, actual)
}

func testPacketHash(t *testing.T, testname string, packet bluepacket.BluePacket, expected int64) {
	t.Log("-- " + testname)
	actual := packet.GetPacketHash()
	assertEquals(t, "GetPacketHash()", expected, actual)
}

func testSerialize(t *testing.T, testname string, packet bluepacket.BluePacket, expected []byte) {
	t.Log("-- " + testname)
	data := bluepacket.Serialize(&packet)
	os.WriteFile("gen/"+testname+".bin", data, 0666)
	assertEquals(t, "Serialize()", hex.EncodeToString(expected), hex.EncodeToString(data))
}

func testDeserialize(t *testing.T, testname string, expected bluepacket.BluePacket, bin []byte) {
	t.Log("-- " + testname)
	bp, err := bluepacket.Deserialize(bin)
	if err != nil {
		t.Log("ERROR - " + err.Error())
		t.FailNow()
	}
	assertEquals(t, "Deserialize()", expected.String(), (*bp).String())
}

func testUnsigned(t *testing.T, testname string, demoPacketU *DemoUnsigned) {
	t.Log("-- testUnsigned")
	assertEquals(t, "cast uint8 to int8", int8(-56), int8(demoPacketU.Ub))
	assertEquals(t, "get uint8", uint8(200), demoPacketU.Ub)

	assertEquals(t, "cast uint16 to int16", int16(-19858), int16(demoPacketU.Us))
	assertEquals(t, "get uint16", uint16(45678), demoPacketU.Us)

	assertEquals(t, "cast uint8 to int32", int32(200), int32(demoPacketU.Ub))
	assertEquals(t, "cast uint16 to int32", int32(45678), int32(demoPacketU.Us))
	assertEquals(t, "cast uint8 to int", 200, int(demoPacketU.Ub))
	assertEquals(t, "cast uint16 to int", 45678, int(demoPacketU.Us))

	packet := DemoPacket{
		FByte:  int8(-56),
		FShort: int16(-19858),
	}
	assertEquals(t, "cast field int8 to int32", int32(-56), int32(packet.FByte))
	assertEquals(t, "cast field int16 to int32", int32(-19858), int32(packet.FShort))
	assertEquals(t, "cast field int8 to int", -56, int(packet.FByte))
	assertEquals(t, "cast field int16 to int", -19858, int(packet.FShort))
}

func TestDemoBluePacketToString(t *testing.T) {
	test := setUp(t)
	testToString(t, "testToString", "toString.txt", &test.demoPacket)
	testToString(t, "testToString2", "toString2.txt", &test.demoPacket2)
	testToString(t, "testToString3", "toString3.txt", &test.demoPacket3)
	testToString(t, "testToStringU", "toStringU.txt", &test.demoPacketU)
}

func TestDemoBluePacketHash(t *testing.T) {
	test := setUp(t)
	testPacketHash(t, "testVersionHash", &test.demoPacket, -3377904526771042813)
	testPacketHash(t, "testVersionHash2", &test.demoPacket2, -4035910894404497038)
	testPacketHash(t, "testVersionHash3", &test.demoPacket3, 3706623474888074790)
	testPacketHash(t, "testVersionHashU", &test.demoPacketU, 4436886959950420991)

	testPacketHash(t, "testDeprecated1", &DemoVersionΔ3FC7F86674610139{}, 4595915063677747513)
	testPacketHash(t, "testDeprecated2", &DemoVersion{}, 7260826007793545337)
	testPacketHash(t, "testIncludeDeprecated1", &DemoIncludeVersionΔ3D76B02436B66199{}, 4428920953148694937)
	testPacketHash(t, "testIncludeDeprecated2", &DemoIncludeVersion{}, -4044184110803273943)
}

func TestDemoBluePacketSerialize(t *testing.T) {
	test := setUp(t)
	testSerialize(t, "testSerialize", &test.demoPacket, test.demoPacketBin)
	testSerialize(t, "testSerialize2", &test.demoPacket2, test.demoPacket2Bin)
	testSerialize(t, "testSerialize3", &test.demoPacket3, test.demoPacket3Bin)
	testSerialize(t, "testSerializeU", &test.demoPacketU, test.demoPacketUBin)
}

func TestDemoBluePacketDeserialize(t *testing.T) {
	test := setUp(t)
	testDeserialize(t, "testDeserialize", &test.demoPacket, test.demoPacketBin)
	testDeserialize(t, "testDeserialize2", &test.demoPacket2, test.demoPacket2Bin)
	testDeserialize(t, "testDeserialize3", &test.demoPacket3, test.demoPacket3Bin)
	testDeserialize(t, "testDeserializeU", &test.demoPacketU, test.demoPacketUBin)
}

func TestDemoBluePacketUnsigned(t *testing.T) {
	test := setUp(t)
	testUnsigned(t, "testUnsigned", &test.demoPacketU)
}

func TestDemoConvert(t *testing.T) {
	t.Log("-- testDemoConvert")
	id := int32(123)
	text := []string {"line1", "line2"}
	d1 := &DemoFirst { Id: id, Text: text }
	d2 := d1.NewDemoSecond()
	assertEquals(t, "Converted 'id' field value", id, d2.Id)
	assertEquals(t, "Converted 'text' field length", len(text), len(d2.Text))
	for i, _ := range text {
		assertEquals(t, "Converted 'text' field value[i]", text[i], d2.Text[i])
	}
}

func TestApiVersion(t *testing.T) {
	t.Log("-- testApiVersion")
	assertTrue(t, "BluePacketAPIVersion calculated", BluePacketApiVersion != 0)
	assertTrue(t, "BluePacketAPIVersionHex calculated", BluePacketApiVersionHex != "")
}
