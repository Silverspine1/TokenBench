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

describe('pre-aborted signal handling', () => {
  it('pre-aborted signal causes request to fail immediately', async (t) => {
    let serverHit = false
    const server = await startServer((req, res) => {
      serverHit = true
      res.writeHead(200)
      res.end('ok')
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    ac.abort()

    let error = null
    try {
      await client.request({ path: '/', method: 'GET', signal: ac.signal })
    } catch (e) {
      error = e
    }

    assert.ok(error !== null, 'pre-aborted signal should cause an error')
    assert.ok(
      error.message.toLowerCase().includes('abort') ||
      error.code === 'UND_ERR_ABORTED' ||
      error.name === 'AbortError',
      `expected an abort error, got: ${error.message} (code=${error.code})`
    )
    assert.strictEqual(serverHit, false, 'server should not be hit when signal is pre-aborted')
  })

  it('pre-aborted signal with POST body fails immediately', async (t) => {
    let serverHit = false
    const server = await startServer((req, res) => {
      serverHit = true
      res.writeHead(200)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    ac.abort()

    let error = null
    try {
      await client.request({ path: '/', method: 'POST', body: 'data=test', signal: ac.signal })
    } catch (e) {
      error = e
    }

    assert.ok(error !== null, 'pre-aborted POST should also fail')
    assert.strictEqual(serverHit, false, 'server should not be hit')
  })

  it('non-aborted signal allows request to succeed', async (t) => {
    const server = await startServer((req, res) => {
      res.writeHead(200)
      res.end('success')
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    const { statusCode } = await client.request({ path: '/', method: 'GET', signal: ac.signal })
    assert.strictEqual(statusCode, 200, 'non-aborted signal should allow request to complete')
  })

  it('signal aborted after request starts cancels the request', async (t) => {
    const server = await startServer((req, res) => {
      setTimeout(() => { res.writeHead(200); res.end('late') }, 300)
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const ac = new AbortController()
    setTimeout(() => ac.abort(), 50)

    let error = null
    try {
      await client.request({ path: '/', method: 'GET', signal: ac.signal })
    } catch (e) {
      error = e
    }

    assert.ok(error !== null, 'mid-request abort should produce an error')
  })

  it('request without signal completes normally', async (t) => {
    const server = await startServer((req, res) => {
      res.writeHead(204)
      res.end()
    })
    t.after(() => server.close())

    const client = new Client(`http://127.0.0.1:${server.address().port}`)
    t.after(() => client.close())

    const { statusCode } = await client.request({ path: '/', method: 'GET' })
    assert.strictEqual(statusCode, 204, 'request without signal should succeed')
  })
})
