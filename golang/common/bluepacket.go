package bluepacket

import (
	"bytes"
	"errors"
	"fmt"
	"math"
	"reflect"
	"strconv"
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

func WriteBluePacket(w *bytes.Buffer, packet *BluePacket) {
	if (packet == nil) {
		WriteLong(w, 0)
	} else {
		WriteLong(w, (*packet).GetPacketHash())
		(*packet).SerializeData(w)
	}
}

func WriteListBool(w *bytes.Buffer, val []bool) {
	l := len(val)
	WriteSequenceLength(w, l)
	bin := byte(0)
	for i := 0 ; i < l ; i++ {
		if val[i] {
			bin |= 1 << (i % 8)
		}
		if i % 8 == 7 {
			w.WriteByte(bin)
			bin = byte(0)
		}
	}
	if l % 8 != 0 {
		w.WriteByte(bin)
	}
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
	return deserializeFromReader(r)
}

// From Reader to object.
//
// Knowing the class packetHash, this will create an instance and populate all the fields
// in order by reading the correct number of bytes.
func deserializeFromReader(r *bytes.Reader) (*BluePacket, error) {
	// Header
	packetHash := ReadLong(r)
	if packetHash == 0 {
		return nil, nil
	}
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

func ReadBluePacket(r *bytes.Reader) *BluePacket {
	packet, _ := deserializeFromReader(r)
	return packet
}

func ReadListBool(r *bytes.Reader) []bool {
	length := ReadSequenceLength(r)
	ret := make([]bool, length)
	bin := byte(0)
	for i := 0 ; i < length ; i++ {
		if i % 8 == 0 {
			bin, _ = r.ReadByte()
		}
		if bin & (1 << (i % 8)) != 0 {
			ret[i] = true
		}
	}
	return ret
}

func ReadFloat(r *bytes.Reader) float32 {
	return math.Float32frombits(uint32(ReadInt(r)))
}

func ReadDouble(r *bytes.Reader) float64 {
	return math.Float64frombits(uint64(ReadLong(r)))
}

// Utils

func AppendIfNotEmptyList[T any](sb *strings.Builder, fname string, ftype string, values []T) {
	if values == nil || len(values) == 0 {
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
	if value == 0 {
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

func AppendIfNotNilPacket(sb *strings.Builder, fname string, value *BluePacket) {
	if value == nil {
		return
	}
	sb.WriteString(" ")
	sb.WriteString(fname)
	sb.WriteString("=")
	sb.WriteString((*value).String())
}

// BpFalseStrings are the case-insensitive strings treated as false by force conversion.
var BpFalseStrings = map[string]bool{
	"": true, "false": true, "f": true, "0": true,
	"no": true, "n": true, "off": true, "null": true, "none": true,
}

// BpFormatFloat renders a shortest round-trip float with a decimal point.
func BpFormatFloat(value float64, bits int) string {
	if math.IsNaN(value) {
		return "nan"
	}
	if math.IsInf(value, 1) {
		return "inf"
	}
	if math.IsInf(value, -1) {
		return "-inf"
	}
	text := strconv.FormatFloat(value, 'g', -1, bits)
	if !strings.ContainsAny(text, ".eE") {
		text += ".0"
	}
	return text
}

// BpToString returns the canonical string representation used by convert mappings.
func BpToString(value any) string {
	switch v := value.(type) {
	case bool:
		if v {
			return "true"
		}
		return "false"
	case float32:
		return BpFormatFloat(float64(v), 32)
	case float64:
		return BpFormatFloat(v, 64)
	case string:
		return v
	default:
		return fmt.Sprintf("%v", v)
	}
}

// BpStringToBool interprets a string using the canonical false list.
func BpStringToBool(value string) bool {
	return !BpFalseStrings[strings.ToLower(strings.TrimSpace(value))]
}

// BpToBool performs a best-effort conversion to bool.
func BpToBool(value any) bool {
	switch v := value.(type) {
	case bool:
		return v
	case string:
		return BpStringToBool(v)
	case float32:
		return v != 0
	case float64:
		return v != 0
	case int:
		return v != 0
	case int8:
		return v != 0
	case int16:
		return v != 0
	case int32:
		return v != 0
	case int64:
		return v != 0
	case uint:
		return v != 0
	case uint8:
		return v != 0
	case uint16:
		return v != 0
	case uint32:
		return v != 0
	case uint64:
		return v != 0
	}
	return false
}

// BpParseInt64 parses a decimal integer with a floating point fallback.
func BpParseInt64(value string) (int64, bool) {
	text := strings.TrimSpace(value)
	if number, err := strconv.ParseInt(text, 10, 64); err == nil {
		return number, true
	}
	number, err := strconv.ParseFloat(text, 64)
	if err != nil && !math.IsInf(number, 0) {
		return 0, false
	}
	if math.IsNaN(number) {
		return 0, false
	}
	if number >= math.MaxInt64 {
		return math.MaxInt64, true
	}
	if number <= math.MinInt64 {
		return math.MinInt64, true
	}
	return int64(number), true
}

// BpToInt performs a best-effort conversion to int64.
func BpToInt(value any) int64 {
	switch v := value.(type) {
	case bool:
		if v {
			return 1
		}
		return 0
	case string:
		number, _ := BpParseInt64(v)
		return number
	case float32:
		return BpFloatToInt64(float64(v))
	case float64:
		return BpFloatToInt64(v)
	case int:
		return int64(v)
	case int8:
		return int64(v)
	case int16:
		return int64(v)
	case int32:
		return int64(v)
	case int64:
		return v
	case uint:
		if uint64(v) > math.MaxInt64 {
			return math.MaxInt64
		}
		return int64(v)
	case uint8:
		return int64(v)
	case uint16:
		return int64(v)
	case uint32:
		return int64(v)
	case uint64:
		if v > math.MaxInt64 {
			return math.MaxInt64
		}
		return int64(v)
	}
	return 0
}

func BpFloatToInt64(value float64) int64 {
	if math.IsNaN(value) {
		return 0
	}
	if value >= math.MaxInt64 {
		return math.MaxInt64
	}
	if value <= math.MinInt64 {
		return math.MinInt64
	}
	return int64(value)
}

// BpClampInt64 clamps a value to the inclusive range.
func BpClampInt64(value, low, high int64) int64 {
	if value < low {
		return low
	}
	if value > high {
		return high
	}
	return value
}

// BpToFloat performs a best-effort conversion to float64.
func BpToFloat(value any) float64 {
	switch v := value.(type) {
	case bool:
		if v {
			return 1
		}
		return 0
	case string:
		number, err := strconv.ParseFloat(strings.TrimSpace(v), 64)
		if err != nil {
			return 0
		}
		return number
	case float32:
		return float64(v)
	case float64:
		return v
	case int:
		return float64(v)
	case int8:
		return float64(v)
	case int16:
		return float64(v)
	case int32:
		return float64(v)
	case int64:
		return float64(v)
	case uint:
		return float64(v)
	case uint8:
		return float64(v)
	case uint16:
		return float64(v)
	case uint32:
		return float64(v)
	case uint64:
		return float64(v)
	}
	return 0
}

// BpToFloat32 performs a best-effort conversion clamped to the float32 range.
func BpToFloat32(value any) float32 {
	number := BpToFloat(value)
	if math.IsNaN(number) {
		return float32(number)
	}
	if math.IsInf(number, 1) {
		return math.MaxFloat32
	}
	if math.IsInf(number, -1) {
		return -math.MaxFloat32
	}
	if number > math.MaxFloat32 {
		return math.MaxFloat32
	}
	if number < -math.MaxFloat32 {
		return -math.MaxFloat32
	}
	return float32(number)
}
