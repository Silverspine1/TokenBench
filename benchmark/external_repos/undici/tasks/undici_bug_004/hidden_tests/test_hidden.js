'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { MockAgent, setGlobalDispatcher, request } = require(process.env.TOKENBENCH_WORKSPACE)

describe('mock query param order matching', () => {
  it('reversed query param order still matches interceptor', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/search?a=1&b=2', method: 'GET' })
      .reply(200, 'order-match')

    const { statusCode } = await request('http://localhost/search?b=2&a=1', { method: 'GET' })
    assert.strictEqual(
      statusCode,
      200,
      'reversed query param order should still match the interceptor'
    )
  })

  it('same-order query params still match (regression guard)', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/api?x=10&y=20', method: 'GET' })
      .reply(200, 'same-order')

    const { statusCode } = await request('http://localhost/api?x=10&y=20', { method: 'GET' })
    assert.strictEqual(statusCode, 200, 'same-order params must still match')
  })

  it('three-param shuffle matches', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/q?c=3&a=1&b=2', method: 'GET' })
      .reply(200, 'three-param')

    const { statusCode } = await request('http://localhost/q?b=2&c=3&a=1', { method: 'GET' })
    assert.strictEqual(statusCode, 200, 'three-param shuffle should match')
  })

  it('path-only interceptor is unaffected', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/noparams', method: 'GET' })
      .reply(200, 'no-params')

    const { statusCode } = await request('http://localhost/noparams', { method: 'GET' })
    assert.strictEqual(statusCode, 200, 'path-only interceptor should still work')
  })

  it('different param values do not match (correctness guard)', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/data?id=1', method: 'GET' })
      .reply(200, 'id-one')

    let error = null
    try {
      await request('http://localhost/data?id=2', { method: 'GET' })
    } catch (e) {
      error = e
    }

    assert.ok(error !== null, 'different param values should NOT match')
  })
})
