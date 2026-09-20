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

// prog builds a guest program that prints tbx.ExpandRange(in).
func prog(in string) string {
	return `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.ExpandRange(` + fmt.Sprintf("%q", in) + `)) }`
}

type check struct{ name, in, want string }

func main() {
	checks := []check{
		// Controls: pure single-number lists, no ranges, no surrounding
		// whitespace.
		{"one", "5", "5\n"},
		{"several", "2,4,9", "2,4,9\n"},
		{"pair", "7,8", "7,8\n"},
		{"chain", "1,2,3,4", "1,2,3,4\n"},
		{"two", "11,22", "11,22\n"},
		{"five", "3,6,9,12,15", "3,6,9,12,15\n"},

		// Inclusive upper bound must be emitted.
		{"single_range", "1-3", "1,2,3\n"},
		{"incl_pair", "20-21", "20,21\n"},
		{"degenerate", "10-10", "10\n"},

		// Mixed lists that contain ranges.
		{"basic_mix", "1-3,5,7-8", "1,2,3,5,7,8\n"},

		// Whitespace around items is ignored.
		{"ws_item", " 5 ", "5\n"},
		{"ws_list", "2, 4 ,9", "2,4,9\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, prog(c.in))
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
