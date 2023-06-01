package bluepacket

import (
	"bytes"
	"errors"
	"fmt"
	"math"
	"reflect"
	"strings"
)

const maxUnsignedByte = 255

type BluePacket interface {
	AppendFields(sb *strings.Builder)
	GetPacketHash() int64
	PopulateData(r *bytes.Reader)
	SerializeData(w *bytes.Buffer)
	String() string
}

var registry = map[int64]reflect.Type{}

func Register(bp BluePacket) {
	registry[bp.GetPacketHash()] = reflect.ValueOf(bp).Elem().Type()
}

// From object to bytes
//
// Serialization format:
// - 8 bytes: version hash representing the class name and the public field names in order
// - N*x bytes: field values in field names alphabetical order.
func Serialize(packet *BluePacket) []byte {
	w := bytes.NewBuffer(nil)

	// Header
	WriteLong(w, (*packet).GetPacketHash())

	// Body
	(*packet).SerializeData(w)
	return w.Bytes()
}

func WriteBool(w *bytes.Buffer, val bool) {
	if val {
		w.WriteByte(1)
	} else {
		w.WriteByte(0)
	}
}

func WriteShort(w *bytes.Buffer, val int16) {
	w.WriteByte(byte(val >> 8))
	w.WriteByte(byte(val))
}

func WriteUShort(w *bytes.Buffer, val uint16) {
	w.WriteByte(byte(val >> 8))
	w.WriteByte(byte(val))
}

func WriteInt(w *bytes.Buffer, val int32) {
	w.WriteByte(byte(val >> 24))
	w.WriteByte(byte(val >> 16))
	w.WriteByte(byte(val >> 8))
	w.WriteByte(byte(val))
}

func WriteLong(w *bytes.Buffer, val int64) {
	w.WriteByte(byte(val >> 56))
	w.WriteByte(byte(val >> 48))
	w.WriteByte(byte(val >> 40))
	w.WriteByte(byte(val >> 32))
	w.WriteByte(byte(val >> 24))
	w.WriteByte(byte(val >> 16))
	w.WriteByte(byte(val >> 8))
	w.WriteByte(byte(val))
}

func WriteSequenceLength(w *bytes.Buffer, length int) {
	if length < maxUnsignedByte {
		w.WriteByte(byte(length))
	} else {
		w.WriteByte(byte(maxUnsignedByte))
		WriteInt(w, int32(length))
	}
}

func WriteString(w *bytes.Buffer, val string) {
	WriteSequenceLength(w, len(val))
	w.Write([]byte(val))
}

func WriteFloat(w *bytes.Buffer, val float32) {
	WriteInt(w, int32(math.Float32bits(val)))
}

func WriteDouble(w *bytes.Buffer, val float64) {
	WriteLong(w, int64(math.Float64bits(val)))
}

// From bytes to object.
//
// Knowing the class packetHash, this will create an instance and populate all the fields
// in order by reading the correct number of bytes.
func Deserialize(bin []byte) (*BluePacket, error) {
	r := bytes.NewReader(bin)

	// Header
	packetHash := ReadLong(r)
	proto, ok := registry[packetHash]
	if !ok {
		return nil, errors.New(fmt.Sprintf("No such PacketHash: %d", packetHash))
	}

	// Body
	packet := reflect.New(proto).Interface().(BluePacket)
	packet.PopulateData(r)

	return &packet, nil
}

func ReadByte(r *bytes.Reader) byte {
	b, _ := r.ReadByte()
	return b
}

func ReadSByte(r *bytes.Reader) int8 {
	b, _ := r.ReadByte()
	return int8(b)
}

func ReadBool(r *bytes.Reader) bool {
	b, _ := r.ReadByte()
	return b == 1
}

func ReadShort(r *bytes.Reader) int16 {
	b1, _ := r.ReadByte()
	b0, _ := r.ReadByte()
	return int16(b1)<<8 | int16(b0)
}

func ReadUShort(r *bytes.Reader) uint16 {
	b1, _ := r.ReadByte()
	b0, _ := r.ReadByte()
	return uint16(b1)<<8 | uint16(b0)
}

func ReadInt(r *bytes.Reader) int32 {
	b3, _ := r.ReadByte()
	b2, _ := r.ReadByte()
	b1, _ := r.ReadByte()
	b0, _ := r.ReadByte()
	return int32(b3)<<24 | int32(b2)<<16 | int32(b1)<<8 | int32(b0)
}

func ReadLong(r *bytes.Reader) int64 {
	b7, _ := r.ReadByte()
	b6, _ := r.ReadByte()
	b5, _ := r.ReadByte()
	b4, _ := r.ReadByte()
	b3, _ := r.ReadByte()
	b2, _ := r.ReadByte()
	b1, _ := r.ReadByte()
	b0, _ := r.ReadByte()
	return int64(b7)<<56 | int64(b6)<<48 | int64(b5)<<40 | int64(b4)<<32 | int64(b3)<<24 | int64(b2)<<16 | int64(b1)<<8 | int64(b0)
}

func ReadSequenceLength(r *bytes.Reader) int {
	length, _ := r.ReadByte()
	if length < maxUnsignedByte {
		return int(length)
	} else {
		return int(ReadInt(r))
	}
}

func ReadString(r *bytes.Reader) string {
	length := ReadSequenceLength(r)
	buf := make([]byte, length)
	r.Read(buf)
	return string(buf)
}

func ReadFloat(r *bytes.Reader) float32 {
	return math.Float32frombits(uint32(ReadInt(r)))
}

func ReadDouble(r *bytes.Reader) float64 {
	return math.Float64frombits(uint64(ReadLong(r)))
}

// Utils for String()

func AppendIfNotEmptyList[T any](sb *strings.Builder, fname string, ftype string, values []T) {
	if len(values) == 0 {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("={")
	sb.WriteString(ftype)
	sb.WriteString(" *")
	sb.WriteString(fmt.Sprint(len(values)))
	for _, v := range values {
		sb.WriteString("|")
		sb.WriteString(fmt.Sprint(v))
	}
	sb.WriteString("}")
}

func AppendIfNotEmptyListBP[T BluePacket](sb *strings.Builder, fname string, ftype string, values []T) {
	if len(values) == 0 {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("={")
	sb.WriteString(ftype)
	sb.WriteString(" *")
	sb.WriteString(fmt.Sprint(len(values)))
	for _, v := range values {
		sb.WriteString("|")
		v.AppendFields(sb)
	}
	sb.WriteString("}")
}

func AppendIfNotEmptyListString(sb *strings.Builder, fname string, values []string) {
	if len(values) == 0 {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("={string *")
	sb.WriteString(fmt.Sprint(len(values)))
	for _, v := range values {
		sb.WriteString("|")
		if v != "" {
			sb.WriteString("\"")
			sb.WriteString(v)
			sb.WriteString("\"")
		}
	}
	sb.WriteString("}")
}

func AppendIfNotEmptyListBool(sb *strings.Builder, fname string, values []bool) {
	if len(values) == 0 {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("={bool *")
	sb.WriteString(fmt.Sprint(len(values)))
	for _, v := range values {
		sb.WriteString("|")
		if v {
			sb.WriteString("1")
		} else {
			sb.WriteString("0")
		}
	}
	sb.WriteString("}")
}

func AppendIfNotEmptyString(sb *strings.Builder, fname string, value string) {
	if value == "" {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=\"")
	sb.WriteString(value)
	sb.WriteString("\"")
}

func AppendIfNotEmpty(sb *strings.Builder, fname string, value any, emptyValue any) {
	if value == emptyValue {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=")
	sb.WriteString(fmt.Sprint(value))
}

func AppendIfNotEmptyBool(sb *strings.Builder, fname string, value bool) {
	if !value {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=1")
}

func AppendIfNotEmptyEnum(sb *strings.Builder, fname string, value any, value_str fmt.Stringer) {
	if value == byte(0) {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=")
	sb.WriteString(value_str.String())
}

func AppendIfNotNil(sb *strings.Builder, fname string, value BluePacket) {
	if value == nil || reflect.ValueOf(value).IsNil() {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=")
	sb.WriteString(value.String())
}
