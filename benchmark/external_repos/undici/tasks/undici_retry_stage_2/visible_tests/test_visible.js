'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { Client } = require('..')

async function startServer (handler) {
  const server = createServer(handler)
  server.listen(0)
  await once(server, 'listening')
  return server
}

describe('AutoRetryHandler Stage 2 - visible checks', () => {
  it('onRetry callback is invoked on a retry', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(calls === 1 ? 503 : 200)
      res.end()
    })
    t.after(() => server.close())

    const { AutoRetryHandler } = require('..')
    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const retryCounts = []
    const opts = {
      path: '/', method: 'GET',
      maxRetries: 1, retryOnStatus: [503], retryDelayMs: 0,
      onRetry: (retryCount, statusCode) => retryCounts.push({ retryCount, statusCode })
    }

    await new Promise((resolve, reject) => {
      client.dispatch(opts, new AutoRetryHandler(
        client.dispatch.bind(client),
        opts,
        {
          onRequestStart () {},
          onResponseStart () {},
          onResponseData () {},
          onResponseEnd () { resolve() },
          onResponseError (_, err) { reject(err) }
        }
      ))
    })

    assert.ok(retryCounts.length >= 1, 'onRetry should have been called at least once')
    assert.strictEqual(retryCounts[0].retryCount, 1, 'first retry should have retryCount=1')
  })

  it('Stage 1 behavior is preserved (no onRetry, no signal)', async (t) => {
    let calls = 0
    const server = await startServer((req, res) => {
      calls++
      res.writeHead(200)
      res.end()
    })
    t.after(() => server.close())

    const { AutoRetryHandler } = require('..')
    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const opts = { path: '/', method: 'GET', maxRetries: 2, retryOnStatus: [503], retryDelayMs: 0 }

    await new Promise((resolve, reject) => {
      client.dispatch(opts, new AutoRetryHandler(
        client.dispatch.bind(client),
        opts,
        {
          onRequestStart () {},
          onResponseStart () {},
          onResponseData () {},
          onResponseEnd () { resolve() },
          onResponseError (_, err) { reject(err) }
        }
      ))
    })

    assert.strictEqual(calls, 1, 'single success should not retry')
  })
})
