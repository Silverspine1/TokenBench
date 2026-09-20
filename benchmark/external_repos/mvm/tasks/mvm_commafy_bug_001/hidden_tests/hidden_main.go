package main

import (
	"bytes"
	"fmt"
	"os"
	"strconv"
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

// commafyProg builds a guest program that prints tbx.Commafy(in).
func commafyProg(in int) string {
	return `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.Commafy(` + strconv.Itoa(in) + `)) }`
}

type check struct {
	name string
	in   int
	want string
}

func main() {
	checks := []check{
		// Short non-negative values need no separator at all.
		{"zero", 0, "0\n"},
		{"single", 7, "7\n"},
		{"two_digit", 42, "42\n"},
		{"three_digit", 100, "100\n"},
		{"round_hundred", 500, "500\n"},
		{"under_thousand", 999, "999\n"},

		// Grouping: a comma is inserted every three digits from the right.
		{"thousand", 1000, "1,000\n"},
		{"four_digit", 1234, "1,234\n"},
		{"million", 1234567, "1,234,567\n"},

		// Negative values keep their sign in front of the grouped digits.
		{"neg_small", -42, "-42\n"},
		{"neg_thousand", -1500, "-1,500\n"},
		{"neg_million", -1234567, "-1,234,567\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, commafyProg(c.in))
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
