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
	// 42 should spell out as "forty-two" (tens joined to units by a hyphen).
	got, err := run("vis", `package main
import ("fmt"; "tbx")
func main(){ fmt.Printf("%q\n", tbx.NumToWords(42)) }`)
	ok := err == nil && got == "\"forty-two\"\n"
	if ok {
		fmt.Println("ok - numtowords forty-two")
	} else {
		fmt.Printf("not ok - numtowords forty-two: got %q err %v\n", got, err)
	}
	if !ok {
		os.Exit(1)
	}
}
