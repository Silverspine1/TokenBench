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

describe('abort signal - visible checks', () => {
  it('non-aborted signal allows request to complete', async (t) => {
    const server = await startServer((req, res) => {
      res.writeHead(200)
      res.end('ok')
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    const { statusCode } = await client.request({ path: '/', method: 'GET', signal: ac.signal })
    assert.strictEqual(statusCode, 200, 'non-aborted signal should allow request to complete')
  })
})
