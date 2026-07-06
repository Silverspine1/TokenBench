// Package bizflow is the module root. It embeds the deterministic fixture data
// used to seed the in-memory database for the CLI and the visible tests.
package bizflow

import "embed"

// FixturesFS holds the JSON seed data shipped with the service.
//
//go:embed fixtures/*.json
var FixturesFS embed.FS
