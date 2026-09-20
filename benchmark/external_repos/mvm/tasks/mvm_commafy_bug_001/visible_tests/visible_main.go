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
	// A four-figure value should carry a single comma after the leading digit.
	got, err := run("vis", `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.Commafy(1234)) }`)
	ok := err == nil && got == "1,234\n"
	if ok {
		fmt.Println("ok - commafy grouping")
	} else {
		fmt.Printf("not ok - commafy grouping: got %q err %v\n", got, err)
	}
	if !ok {
		os.Exit(1)
	}
}
