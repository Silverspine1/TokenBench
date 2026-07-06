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

function makeRetry (client, opts, innerHandler) {
  const { AutoRetryHandler } = require(process.env.TOKENBENCH_WORKSPACE)
  return new AutoRetryHandler(client.dispatch.bind(client), opts, innerHandler)
}

describe('AutoRetryHandler Stage 2 - onRetry callback and signal support', () => {
  it('onRetry is called with correct retryCount for each retry', async (t) => {
    let serverCalls = 0
    const server = await startServer((req, res) => {
      serverCalls++
      if (serverCalls < 3) {
        res.writeHead(503)
      } else {
        res.writeHead(200)
      }
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const retryLog = []
    const opts = {
      path: '/', method: 'GET',
      maxRetries: 3, retryOnStatus: [503], retryDelayMs: 0,
      onRetry: (retryCount, statusCode) => retryLog.push({ retryCount, statusCode })
    }

    await new Promise((resolve, reject) => {
      client.dispatch(opts, makeRetry(client, opts, {
        onRequestStart () {},
        onResponseStart () {},
        onResponseData () {},
        onResponseEnd () { resolve() },
        onResponseError (_, err) { reject(err) }
      }))
    })

    assert.strictEqual(retryLog.length, 2, 'should have 2 retries logged')
    assert.strictEqual(retryLog[0].retryCount, 1, 'first retry should be retryCount=1')
    assert.strictEqual(retryLog[0].statusCode, 503, 'statusCode should be 503')
    assert.strictEqual(retryLog[1].retryCount, 2, 'second retry should be retryCount=2')
  })

  it('onRetry is not called on a successful first attempt', async (t) => {
    const server = await startServer((req, res) => {
      res.writeHead(200)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const retryLog = []
    const opts = {
      path: '/', method: 'GET',
      maxRetries: 3, retryOnStatus: [503], retryDelayMs: 0,
      onRetry: (retryCount, statusCode) => retryLog.push({ retryCount, statusCode })
    }

    await new Promise((resolve, reject) => {
      client.dispatch(opts, makeRetry(client, opts, {
        onRequestStart () {},
        onResponseStart () {},
        onResponseData () {},
        onResponseEnd () { resolve() },
        onResponseError (_, err) { reject(err) }
      }))
    })

    assert.strictEqual(retryLog.length, 0, 'onRetry should not be called on first-attempt success')
  })

  it('aborting signal during retryDelayMs cancels pending retry', async (t) => {
    let serverCalls = 0
    const server = await startServer((req, res) => {
      serverCalls++
      res.writeHead(503)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    let error = null

    try {
      await new Promise((resolve, reject) => {
        const opts = {
          path: '/', method: 'GET',
          maxRetries: 5, retryOnStatus: [503], retryDelayMs: 500,
          signal: ac.signal
        }
        client.dispatch(opts, makeRetry(client, opts, {
          onRequestStart () {},
          onResponseStart () { setTimeout(() => ac.abort(), 50) },
          onResponseData () {},
          onResponseEnd () {},
          onResponseError (_, err) { reject(err) }
        }))
      })
    } catch (e) {
      error = e
    }

    assert.ok(error !== null, 'aborted signal should cause an error')
    assert.ok(
      error.message.toLowerCase().includes('abort') ||
      error.code === 'UND_ERR_ABORTED' ||
      error.name === 'AbortError',
      `expected abort error, got: ${error.message}`
    )
    assert.ok(serverCalls < 5, `abort during delay should prevent full retry cycle; got ${serverCalls} calls`)
  })

  it('omitting onRetry and signal preserves Stage 1 behavior', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(calls === 1 ? 503 : 200)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    let finalStatus = null
    const opts = {
      path: '/', method: 'GET',
      maxRetries: 1, retryOnStatus: [503], retryDelayMs: 0
    }

    await new Promise((resolve, reject) => {
      client.dispatch(opts, makeRetry(client, opts, {
        onRequestStart () {},
        onResponseStart (_, code) { finalStatus = code },
        onResponseData () {},
        onResponseEnd () { resolve() },
        onResponseError (_, err) { reject(err) }
      }))
    })

    assert.strictEqual(calls, 2, 'should retry once without onRetry or signal')
    assert.strictEqual(finalStatus, 200, 'final status should be 200 after retry')
  })
})
