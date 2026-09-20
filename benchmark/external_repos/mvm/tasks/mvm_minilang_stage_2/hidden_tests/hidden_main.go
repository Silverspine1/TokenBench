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

// run evaluates a full guest program through a fresh, isolated interpreter and
// returns whatever it wrote to stdout plus any evaluation error.
func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

type check struct{ name, ml, want string }

// prog builds a guest program that prints tbx.Run(ml). The mini-language
// source is embedded in a raw string literal so its newlines survive.
func prog(ml string) string {
	header := "package main\nimport (\"fmt\"; \"tbx\")\nfunc main(){ fmt.Print(tbx.Run(`"
	return header + ml + "`)) }"
}

func main() {
	checks := []check{
		{"num_add", "print 2+3", "5"},
		{"num_precedence", "print 2+3*4", "14"},
		{"num_left_sub", "print 10-3-2", "5"},
		{"num_trunc", "print 7/2", "3"},
		{"num_unary", "print 2 - -3", "5"},
		{"num_let", "let x = 2+3\nprint x", "5"},
		{"num_undef", "print zzz", "error: undefined variable: zzz"},
		{"num_multi", "print 1\nprint 2", "1\n2"},
		{"str_literal", "print \"hello\"", "hello"},
		{"str_concat", "print \"foo\" + \"bar\"", "foobar"},
		{"str_concat_var", "let a = \"x\"\nlet b = \"y\"\nprint a + b", "xy"},
		{"str_len", "print len(\"hello\")", "5"},
		{"str_len_empty", "print len(\"\")", "0"},
		{"str_upper", "print upper(\"abc\")", "ABC"},
		{"str_upper_concat", "print upper(\"ab\") + \"CD\"", "ABCD"},
		{"str_len_of_concat", "print len(\"foo\" + \"bar\")", "6"},
		{"str_escape_quote", "print \"a\\\"b\"", "a\"b"},
		{"str_escape_newline", "print \"a\\nb\"", "a\nb"},
		{"str_mixed_str_int", "print \"x\" + 1", "error: type error: cannot add an integer and a string"},
		{"str_mixed_int_str", "print 1 + \"x\"", "error: type error: cannot add an integer and a string"},
		{"str_print_let", "let s = \"hi\"\nprint s", "hi"},
		{"mix_str_then_num", "let s = \"hi\"\nlet n = 3+4\nprint s\nprint n", "hi\n7"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, prog(c.ml))
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
