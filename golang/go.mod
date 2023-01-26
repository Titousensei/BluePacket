module bluepacket

go 1.18

replace github.com/bluepacket => ./common

require github.com/bluepacketdemo v0.0.0-00010101000000-000000000000

require github.com/bluepacket v0.0.0-00010101000000-000000000000 // indirect

replace github.com/bluepacketdemo => ./test/gen
