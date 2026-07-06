from tokenbench.manual.public import (
    PRIVATE_MANIFEST_FIELDS,
    PUBLIC_MANIFEST_FIELDS,
    public_manifest,
    safe_prompt,
)


def test_prompt_has_no_private_token_or_hidden_command(demo_task, tmp_path):
    manifest = demo_task["manifest"]
    prompt = safe_prompt(manifest, tmp_path / "workspace")
    assert demo_task["private_token"] not in prompt
    # The hidden command must never appear in an operator-facing prompt.
    assert "sys.exit" not in prompt
    # The task itself is present.
    assert "add()" in prompt


def test_public_manifest_excludes_every_private_field(demo_task):
    pub = public_manifest(demo_task["manifest"])
    for field in PRIVATE_MANIFEST_FIELDS:
        assert field not in pub
    assert set(pub) == set(PUBLIC_MANIFEST_FIELDS)
    assert demo_task["private_token"] not in str(pub)


def test_public_and_private_field_sets_are_disjoint():
    assert not (set(PUBLIC_MANIFEST_FIELDS) & set(PRIVATE_MANIFEST_FIELDS))
