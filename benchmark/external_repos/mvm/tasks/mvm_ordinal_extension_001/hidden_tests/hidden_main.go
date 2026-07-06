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

type check struct{ name, src, want string }

// prog builds a guest program that prints tbx.Ordinalize(n).
func prog(n int) string {
	return fmt.Sprintf(`package main
import ("fmt"; "tbx")
func main(){ fmt.Println(tbx.Ordinalize(%d)) }`, n)
}

func main() {
	checks := []check{
		// suffix driven by the final digit
		{"three", prog(3), "3rd\n"},
		{"twenty_three", prog(23), "23rd\n"},
		{"hundred_three", prog(103), "103rd\n"},
		// final two digits land in the teens, above one hundred
		{"one_eleven", prog(111), "111th\n"},
		{"one_twelve", prog(112), "112th\n"},
		// negative ranks
		{"minus_one", prog(-1), "-1st\n"},
		{"minus_twenty_two", prog(-22), "-22nd\n"},
		// values the current code already renders the way the contract expects
		{"one", prog(1), "1st\n"},
		{"two", prog(2), "2nd\n"},
		{"five", prog(5), "5th\n"},
		{"twenty_one", prog(21), "21st\n"},
		{"zero", prog(0), "0th\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, c.src)
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
