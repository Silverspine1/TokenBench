'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { MockAgent, setGlobalDispatcher, request } = require('..')

describe('mock query param matching - visible checks', () => {
  it('same-order query params always match', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/search?q=hello&page=1', method: 'GET' })
      .reply(200, 'matched')

    const { statusCode } = await request('http://localhost/search?q=hello&page=1', { method: 'GET' })
    assert.strictEqual(statusCode, 200, 'same-order params should match')
  })

  it('path-only interceptor (no query params) matches', async (t) => {
    const mockAgent = new MockAgent()
    mockAgent.disableNetConnect()
    setGlobalDispatcher(mockAgent)
    t.after(async () => { await mockAgent.close() })

    const pool = mockAgent.get('http://localhost')
    pool.intercept({ path: '/api/data', method: 'GET' })
      .reply(200, 'ok')

    const { statusCode } = await request('http://localhost/api/data', { method: 'GET' })
    assert.strictEqual(statusCode, 200)
  })
})
