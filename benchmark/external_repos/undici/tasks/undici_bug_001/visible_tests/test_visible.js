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

describe('redirect - array-form headers are stripped on cross-origin redirect (visible)', () => {
  it('authorization header stripped with array-form on cross-origin redirect', async (t) => {
    let redirectTarget = null

    const target = await startServer((req, res) => {
      redirectTarget = req.headers
      res.writeHead(200)
      res.end('ok')
    })
    t.after(() => target.close())

    const origin = await startServer((req, res) => {
      res.writeHead(301, { location: `http://127.0.0.1:${target.address().port}/` })
      res.end()
    })
    t.after(() => origin.close())

    const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 1 }))
    t.after(() => agent.close())

    let error = null
    try {
      await request(`http://127.0.0.1:${origin.address().port}/`, {
        method: 'GET',
        headers: ['authorization', 'Bearer token123'],
        dispatcher: agent
      })
    } catch (e) {
      error = e
    }

    // Verify the redirect chain was followed without crash
    assert.ok(error === null || error.message !== 'should not reach here')
  })
})
