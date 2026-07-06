package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"

	"github.com/mvm-sh/mvm/interp"
	"github.com/mvm-sh/mvm/lang/golang"
	"github.com/mvm-sh/mvm/stdlib"
	_ "github.com/mvm-sh/mvm/stdlib/core"
)

func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

func main() {
	// "IV" is four: the leading I sits before the larger V, so it should be
	// taken away from the total rather than added on.
	got, err := run("vis", `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.RomanTo("IV")) }`)
	ok := err == nil && got == "4\n"
	if ok {
		fmt.Println("ok - roman numeral value")
	} else {
		fmt.Printf("not ok - roman numeral value: got %q err %v\n", got, err)
	}
	if !ok {
		os.Exit(1)
	}
}
