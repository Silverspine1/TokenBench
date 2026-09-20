'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')

describe('top-level exports - visible checks', () => {
  it('known top-level exports are still present', () => {
    const undici = require('..')
    assert.ok(typeof undici.Client === 'function', 'Client should be exported')
    assert.ok(typeof undici.Pool === 'function', 'Pool should be exported')
    assert.ok(typeof undici.Agent === 'function', 'Agent should be exported')
  })

  it('RedirectHandler export is present and unchanged', () => {
    const { RedirectHandler } = require('..')
    assert.ok(typeof RedirectHandler === 'function', 'RedirectHandler should be exported')
  })
})
