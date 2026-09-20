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

type check struct {
	name string
	n    int
	want string
}

// prog builds a guest program that prints tbx.NumToWords(n).
func prog(n int) string {
	return fmt.Sprintf(`package main
import ("fmt"; "tbx")
func main(){ fmt.Printf("%%q\n", tbx.NumToWords(%d)) }`, n)
}

func main() {
	checks := []check{
		// zero is a unique word
		{"zero", 0, "zero"},
		// a plain single-digit unit
		{"seven", 7, "seven"},
		// a teen: must be the unique word, not "ten-five"
		{"fifteen", 15, "fifteen"},
		// another teen near the boundary
		{"eleven", 11, "eleven"},
		// exact ten word, no trailing units
		{"twenty", 20, "twenty"},
		// tens + units joined by a single hyphen
		{"forty_two", 42, "forty-two"},
		// largest two-digit value, hyphenated
		{"ninety_nine", 99, "ninety-nine"},
		// exact hundred, no trailing remainder and no "and"
		{"one_hundred", 100, "one hundred"},
		// hundred + units only (skips the tens slot), no "and"
		{"one_hundred_five", 105, "one hundred five"},
		// hundred + hyphenated tens, no "and"
		{"nine_hundred_ninety_nine", 999, "nine hundred ninety-nine"},
		// exact thousand, no trailing remainder
		{"one_thousand", 1000, "one thousand"},
		// thousand + hundred + hyphenated tens combined
		{"one_thousand_two_hundred_thirty_four", 1234, "one thousand two hundred thirty-four"},
		// thousand + units only (no hundreds, no tens)
		{"two_thousand_three", 2003, "two thousand three"},
		// upper bound: every component present
		{"nine_thousand_nine_hundred_ninety_nine", 9999, "nine thousand nine hundred ninety-nine"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, prog(c.n))
		if err != nil {
			fmt.Fprintf(os.Stderr, "not ok - %s: eval error: %v\n", c.name, err)
			continue
		}
		want := fmt.Sprintf("%q\n", c.want)
		if got == want {
			passed++
		} else {
			fmt.Fprintf(os.Stderr, "not ok - %s: got %s want %s\n", c.name, strings.TrimRight(got, "\n"), strings.TrimRight(want, "\n"))
		}
	}

	fmt.Printf("TOKENBENCH_CHECKS passed=%d total=%d\n", passed, len(checks))
	if passed != len(checks) {
		os.Exit(1)
	}
}
