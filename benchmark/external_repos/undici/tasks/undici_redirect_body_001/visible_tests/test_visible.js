'use strict'
// Shallow visible checks: surface the symptom only (POST body across a redirect).
const { test } = require('node:test')
const assert = require('node:assert')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { Agent, interceptors, request } = require('..')

async function startServer (handler) {
  const s = createServer(handler); s.listen(0); await once(s, 'listening'); return s
}

test('a POST redirected with 307 keeps its body', async (t) => {
  let received = ''
  const target = await startServer((req, res) => {
    let b = ''; req.on('data', d => b += d); req.on('end', () => { received = b; res.writeHead(200); res.end() })
  })
  t.after(() => target.close())
  const origin = await startServer((req, res) => {
    res.writeHead(307, { location: `http://127.0.0.1:${target.address().port}/` }); res.end()
  })
  t.after(() => origin.close())
  const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 2 }))
  t.after(() => agent.close())
  const res = await request(`http://127.0.0.1:${origin.address().port}/`, { method: 'POST', body: 'hello', dispatcher: agent })
  await res.body.dump()
  assert.strictEqual(received, 'hello', '307 redirect should preserve the POST body')
})
