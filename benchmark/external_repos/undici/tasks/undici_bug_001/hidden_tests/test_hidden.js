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

describe('redirect header stripping - object-form headers', () => {
  it('object-form authorization header stripped on cross-origin redirect', async (t) => {
    let receivedHeaders = null

    const target = await startServer((req, res) => {
      receivedHeaders = { ...req.headers }
      res.writeHead(200)
      res.end('done')
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(301, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 1 }))
    t.after(() => agent.close())

    await request(`http://127.0.0.1:${origin.address().port}/`, {
      method: 'GET',
      headers: { authorization: 'Bearer secret', 'x-custom': 'keep-me' },
      dispatcher: agent
    })

    assert.ok(receivedHeaders !== null, 'Target server should have received the request')
    assert.strictEqual(
      receivedHeaders.authorization,
      undefined,
      `authorization should be stripped on cross-origin redirect; got: ${receivedHeaders.authorization}`
    )
    assert.strictEqual(
      receivedHeaders['x-custom'],
      'keep-me',
      'non-sensitive headers should be forwarded'
    )
  })

  it('object-form cookie header stripped on cross-origin redirect', async (t) => {
    let receivedHeaders = null

    const target = await startServer((req, res) => {
      receivedHeaders = { ...req.headers }
      res.writeHead(200)
      res.end('done')
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(302, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 1 }))
    t.after(() => agent.close())

    await request(`http://127.0.0.1:${origin.address().port}/`, {
      method: 'GET',
      headers: { cookie: 'session=abc123', 'accept': 'text/html' },
      dispatcher: agent
    })

    assert.strictEqual(
      receivedHeaders.cookie,
      undefined,
      `cookie should be stripped on cross-origin redirect; got: ${receivedHeaders.cookie}`
    )
    assert.strictEqual(receivedHeaders.accept, 'text/html', 'accept should be kept')
  })

  it('array-form authorization still stripped (existing behavior unchanged)', async (t) => {
    let receivedHeaders = null

    const target = await startServer((req, res) => {
      receivedHeaders = { ...req.headers }
      res.writeHead(200)
      res.end('done')
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(301, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 1 }))
    t.after(() => agent.close())

    await request(`http://127.0.0.1:${origin.address().port}/`, {
      method: 'GET',
      headers: ['authorization', 'Bearer array-token'],
      dispatcher: agent
    })

    assert.strictEqual(
      receivedHeaders.authorization,
      undefined,
      'array-form authorization should also be stripped'
    )
  })
})
