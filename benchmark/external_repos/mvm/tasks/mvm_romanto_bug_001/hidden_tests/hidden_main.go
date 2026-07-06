package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"

	"github.com/mvm-sh/mvm/interp"
	"github.com/mvm-sh/mvm/lang/golang"
	"github.com/mvm-sh/mvm/stdlib"
	_ "github.com/mvm-sh/mvm/stdlib/core" // register core stdlib; avoid Unix-only stdlib/ext
)

// run evaluates a full program through a fresh, isolated interpreter and returns
// whatever it wrote to stdout plus any evaluation error.
func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

// romanProg builds a guest program that prints tbx.RomanTo(in).
func romanProg(in string) string {
	return `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.RomanTo(` + fmt.Sprintf("%q", in) + `)) }`
}

type check struct{ name, in, want string }

func main() {
	checks := []check{
		// Plain additive numerals with no subtractive pairs.
		{"three", "III", "3\n"},
		{"eight", "VIII", "8\n"},
		{"fifty_eight", "LVIII", "58\n"},
		{"year_2015", "MMXV", "2015\n"},
		{"twenty", "XX", "20\n"},

		// Subtractive notation: a smaller symbol before a larger one subtracts.
		{"four", "IV", "4\n"},
		{"nine", "IX", "9\n"},
		{"year_2024", "MMXXIV", "2024\n"},
		{"four_44", "CDXLIV", "444\n"},
		{"max_3999", "MMMCMXCIX", "3999\n"},

		// Inputs that are not valid Roman numerals report -1.
		{"bad_letter", "IZ", "-1\n"},
		{"bad_digit", "VX5", "-1\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, romanProg(c.in))
		if err != nil {
			fmt.Fprintf(os.Stderr, "not ok - %s: eval error: %v\n", c.name, err)
			continue
		}
		if got == c.want {
			passed++
		} else {
			fmt.Fprintf(os.Stderr, "not ok - %s: got %q want %q\n", c.name, got, c.want)
		}
	}

	fmt.Printf("TOKENBENCH_CHECKS passed=%d total=%d\n", passed, len(checks))
	if passed != len(checks) {
		os.Exit(1)
	}
}
