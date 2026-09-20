'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { Client } = require(process.env.TOKENBENCH_WORKSPACE)

async function startServer (handler) {
  const server = createServer(handler)
  server.listen(0)
  await once(server, 'listening')
  return server
}

// AutoRetryHandler constructor: new AutoRetryHandler(dispatch, opts, handler)
// where dispatch = client.dispatch.bind(client), opts includes maxRetries/retryOnStatus/retryDelayMs
function makeRetry (client, opts, innerHandler) {
  const { AutoRetryHandler } = require(process.env.TOKENBENCH_WORKSPACE)
  return new AutoRetryHandler(client.dispatch.bind(client), opts, innerHandler)
}

async function dispatchWithRetry (client, opts) {
  return new Promise((resolve, reject) => {
    let finalStatus = null
    client.dispatch(opts, makeRetry(client, opts, {
      onRequestStart () {},
      onResponseStart (_, statusCode) { finalStatus = statusCode },
      onResponseData () {},
      onResponseEnd () { resolve(finalStatus) },
      onResponseError (_, err) { reject(err) }
    }))
  })
}

describe('AutoRetryHandler - retry logic', () => {
  it('AutoRetryHandler is exported and is a function', () => {
    const { AutoRetryHandler } = require(process.env.TOKENBENCH_WORKSPACE)
    assert.strictEqual(typeof AutoRetryHandler, 'function')
  })

  it('retries once on 503 when maxRetries=1, succeeds on second attempt', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      if (calls === 1) {
        res.writeHead(503)
        res.end()
      } else {
        res.writeHead(200)
        res.end('ok')
      }
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 1, retryOnStatus: [503], retryDelayMs: 0
    })

    assert.strictEqual(calls, 2, 'should have hit server twice')
    assert.strictEqual(finalStatus, 200, 'final status should be 200 after retry')
  })

  it('does not retry when maxRetries=0 even on 503', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(503)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 0, retryOnStatus: [503], retryDelayMs: 0
    })

    assert.strictEqual(calls, 1, 'should not retry when maxRetries=0')
    assert.strictEqual(finalStatus, 503, 'should pass through 503 without retrying')
  })

  it('exhausts retries and passes through final status', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(503)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 2, retryOnStatus: [503], retryDelayMs: 0
    })

    assert.strictEqual(calls, 3, 'should try original + 2 retries = 3 total')
    assert.strictEqual(finalStatus, 503, 'should pass through final 503 after retries exhausted')
  })

  it('does not retry non-listed status codes', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(500)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 3, retryOnStatus: [503, 429], retryDelayMs: 0
    })

    assert.strictEqual(calls, 1, 'should not retry 500 (not in retryOnStatus)')
    assert.strictEqual(finalStatus, 500)
  })

  it('retries on 429 when listed in retryOnStatus', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      if (calls === 1) {
        res.writeHead(429)
        res.end()
      } else {
        res.writeHead(200)
        res.end()
      }
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 2, retryOnStatus: [429, 503], retryDelayMs: 0
    })

    assert.strictEqual(calls, 2, 'should retry 429 when in retryOnStatus')
    assert.strictEqual(finalStatus, 200)
  })

  it('successful first attempt is not retried', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(200)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const finalStatus = await dispatchWithRetry(client, {
      path: '/', method: 'GET', maxRetries: 5, retryOnStatus: [503], retryDelayMs: 0
    })

    assert.strictEqual(calls, 1, 'success on first attempt should not retry')
    assert.strictEqual(finalStatus, 200)
  })
})
