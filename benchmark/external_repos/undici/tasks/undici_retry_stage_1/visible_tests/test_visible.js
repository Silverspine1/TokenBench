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

describe('AutoRetryHandler - visible checks', () => {
  it('AutoRetryHandler is exported from the top-level package', () => {
    const { AutoRetryHandler } = require('..')
    assert.ok(
      typeof AutoRetryHandler === 'function',
      'AutoRetryHandler should be a constructor exported from undici'
    )
  })

  it('request that succeeds first time is not retried', async (t) => {
    let callCount = 0
    const server = await startServer((req, res) => {
      callCount++
      res.writeHead(200)
      res.end('ok')
    })
    t.after(() => server.close())

    const { AutoRetryHandler } = require('..')
    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const opts = { path: '/', method: 'GET', maxRetries: 3, retryOnStatus: [503], retryDelayMs: 0 }

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

    assert.strictEqual(callCount, 1, 'successful request should only hit server once')
  })
})
