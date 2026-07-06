"""Demo fix for the pulseboard local-command runner. cwd == workspace."""

import pathlib

p = pathlib.Path("src/export.js")
broken = (
    "function selectInvoices(invoices, filter) {\n"
    "  // BUG: ignores the filter and returns every invoice.\n"
    "  return invoices.slice();\n"
    "}"
)
fixed = (
    "function selectInvoices(invoices, filter) {\n"
    "  if (!filter || !filter.status) {\n"
    "    return invoices.slice();\n"
    "  }\n"
    "  return invoices.filter((inv) => inv.status === filter.status);\n"
    "}"
)
p.write_text(p.read_text().replace(broken, fixed))
print("fixed src/export.js")
