'use strict'
const { describe, it } = require('node:test')
const assert = require('node:assert')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { Agent, interceptors, request } = require('..')

async function startServer (handler) {
  const server = createServer(handler)
  server.listen(0)
  await once(server, 'listening')
  return server
}

describe('redirect body handling - visible checks', () => {
  it('301 with POST changes method to GET', async (t) => {
    let receivedMethod = null

    const target = await startServer((req, res) => {
      receivedMethod = req.method
      res.writeHead(200)
      res.end()
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
      method: 'POST',
      body: 'data',
      dispatcher: agent
    })

    assert.strictEqual(receivedMethod, 'GET', '301+POST should redirect as GET')
  })

  it('redirect follows location header', async (t) => {
    let hitTarget = false

    const target = await startServer((req, res) => {
      hitTarget = true
      res.writeHead(200)
      res.end('ok')
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
      dispatcher: agent
    })

    assert.ok(hitTarget, 'Should have followed redirect to target')
  })
})
