'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { Agent, interceptors, request } = require(process.env.TOKENBENCH_WORKSPACE)

async function startServer (handler) {
  const server = createServer(handler)
  server.listen(0)
  await once(server, 'listening')
  return server
}

async function doRedirectRequest (originPort, method, body) {
  const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 1 }))
  try {
    const res = await request(`http://127.0.0.1:${originPort}/`, { method, body, dispatcher: agent })
    await res.body.dump()
  } finally {
    await agent.close()
  }
}

describe('307 redirect preserves POST body', () => {
  it('307 redirect preserves request body', async (t) => {
    let receivedBody = ''
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      let body = ''
      req.on('data', d => { body += d })
      req.on('end', () => { receivedBody = body; res.writeHead(200); res.end('ok') })
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(307, { location: `http://127.0.0.1:${target.address().port}/submit` })
      res.end()
    })
    t.after(() => origin.close())

    await doRedirectRequest(origin.address().port, 'POST', 'payload=hello')

    assert.strictEqual(receivedMethod, 'POST', '307 should preserve POST method')
    assert.strictEqual(
      receivedBody, 'payload=hello',
      `307 should preserve request body; got: ${JSON.stringify(receivedBody)}`
    )
  })

  it('307 redirect preserves method (not changed to GET)', async (t) => {
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      res.writeHead(200); res.end()
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(307, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    await doRedirectRequest(origin.address().port, 'POST', 'x=1')

    assert.strictEqual(receivedMethod, 'POST', '307 must not change POST to GET')
  })

  it('301+POST still changes to GET (unchanged)', async (t) => {
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      res.writeHead(200); res.end()
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(301, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    await doRedirectRequest(origin.address().port, 'POST', 'data')

    assert.strictEqual(receivedMethod, 'GET', '301+POST should still become GET')
  })

  it('303 redirect always uses GET regardless of original method', async (t) => {
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      res.writeHead(200); res.end()
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(303, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    await doRedirectRequest(origin.address().port, 'POST', 'form=data')

    assert.strictEqual(receivedMethod, 'GET', '303 should always use GET')
  })

  it('308 redirect preserves method and body', async (t) => {
    let receivedBody = ''
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      let body = ''
      req.on('data', d => { body += d })
      req.on('end', () => { receivedBody = body; res.writeHead(200); res.end() })
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(308, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    await doRedirectRequest(origin.address().port, 'POST', 'keep=me')

    assert.strictEqual(receivedMethod, 'POST', '308 should preserve POST method')
    assert.strictEqual(receivedBody, 'keep=me', '308 should preserve body')
  })
})
