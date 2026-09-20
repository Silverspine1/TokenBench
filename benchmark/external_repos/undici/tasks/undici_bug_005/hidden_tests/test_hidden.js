'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')

describe('DecoratorHandler top-level export', () => {
  it('DecoratorHandler is exported from the top-level package', () => {
    const undici = require(process.env.TOKENBENCH_WORKSPACE)
    assert.ok(
      undici.DecoratorHandler !== undefined,
      'require("undici").DecoratorHandler should not be undefined'
    )
    assert.strictEqual(
      typeof undici.DecoratorHandler,
      'function',
      'DecoratorHandler should be a constructor/class'
    )
  })

  it('DecoratorHandler can be destructured from top-level import', () => {
    const { DecoratorHandler } = require(process.env.TOKENBENCH_WORKSPACE)
    assert.ok(typeof DecoratorHandler === 'function', 'Destructured DecoratorHandler should be a function')
  })

  it('DecoratorHandler is instantiatable with a handler object', () => {
    const { DecoratorHandler } = require(process.env.TOKENBENCH_WORKSPACE)
    const handler = {
      onRequestStart () {},
      onResponseStart () {},
      onResponseData () {},
      onResponseEnd () {},
      onResponseError () {}
    }
    let instance
    assert.doesNotThrow(() => {
      instance = new DecoratorHandler(handler)
    }, 'DecoratorHandler should be instantiatable with a handler')
    assert.ok(instance !== null)
  })

  it('existing exports are unaffected after fix', () => {
    const undici = require(process.env.TOKENBENCH_WORKSPACE)
    assert.ok(typeof undici.Client === 'function', 'Client export must be unchanged')
    assert.ok(typeof undici.Pool === 'function', 'Pool export must be unchanged')
    assert.ok(typeof undici.Agent === 'function', 'Agent export must be unchanged')
    assert.ok(typeof undici.RedirectHandler === 'function', 'RedirectHandler must be unchanged')
  })

  it('DecoratorHandler from top-level matches internal implementation', () => {
    const { DecoratorHandler: TopLevel } = require(process.env.TOKENBENCH_WORKSPACE)
    const Internal = require(`${process.env.TOKENBENCH_WORKSPACE}/lib/handler/decorator-handler`)
    assert.strictEqual(
      TopLevel,
      Internal,
      'top-level DecoratorHandler should be identical to the internal one'
    )
  })
})
