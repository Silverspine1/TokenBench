'use strict'
const assert = require('node:assert')
const { createServer } = require('node:http')
const { Agent, interceptors, request } = require(process.env.TOKENBENCH_WORKSPACE)

let passed = 0, total = 0
async function check (name, fn) {
  total++
  try { await fn(); passed++ } catch (e) { console.log(`not ok - ${name}: ${e.message}`) }
}
function server (handler) {
  return new Promise(res => { const s = createServer(handler); s.listen(0, () => res(s)) })
}

async function main () {
  let got = {}
  const target = await server((req, r) => {
    let b = ''; req.on('data', d => b += d)
    req.on('end', () => { got = { method: req.method, body: b, headers: req.headers }; r.writeHead(200); r.end('ok') })
  })
  const tport = target.address().port
  const origin = await server((req, r) => {
    const code = Number(req.url.slice(1)) || 0
    r.writeHead(code, { location: `http://127.0.0.1:${tport}/` }); r.end()
  })
  const oport = origin.address().port
  const hit = async (code, method, body, headers) => {
    got = {}
    const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 3 }))
    try { const res = await request(`http://127.0.0.1:${oport}/${code}`, { method, body, headers, dispatcher: agent }); await res.body.dump() }
    finally { await agent.close() }
    return got
  }
  const CT = { 'content-language': 'en-US', 'content-type': 'application/json', 'content-encoding': 'identity' }

  let g = await hit(301, 'POST', 'p1')
  await check('301 POST becomes GET', () => assert.strictEqual(g.method, 'GET'))
  await check('301 POST drops body', () => assert.strictEqual(g.body, ''))
  g = await hit(302, 'POST', 'p2')
  await check('302 POST becomes GET', () => assert.strictEqual(g.method, 'GET'))
  await check('302 POST drops body', () => assert.strictEqual(g.body, ''))

  g = await hit(303, 'POST', 'p3', { ...CT })
  await check('303 POST becomes GET', () => assert.strictEqual(g.method, 'GET'))
  await check('303 drops body', () => assert.strictEqual(g.body, ''))
  await check('303 strips content-language', () => assert.ok(!('content-language' in g.headers), g.headers['content-language']))
  await check('303 strips content-type', () => assert.ok(!('content-type' in g.headers), g.headers['content-type']))
  await check('303 strips content-encoding', () => assert.ok(!('content-encoding' in g.headers), g.headers['content-encoding']))

  g = await hit(307, 'POST', 'keep-307', { ...CT })
  await check('307 preserves POST method', () => assert.strictEqual(g.method, 'POST'))
  await check('307 preserves body', () => assert.strictEqual(g.body, 'keep-307'))
  await check('307 preserves content-language', () => assert.strictEqual(g.headers['content-language'], 'en-US'))
  await check('307 preserves content-type', () => assert.strictEqual(g.headers['content-type'], 'application/json'))

  g = await hit(308, 'POST', 'keep-308')
  await check('308 preserves POST method', () => assert.strictEqual(g.method, 'POST'))
  await check('308 preserves body', () => assert.strictEqual(g.body, 'keep-308'))

  g = await hit(301, 'GET')
  await check('GET through 301 stays GET', () => assert.strictEqual(g.method, 'GET'))

  target.close(); origin.close()
  console.log(`TOKENBENCH_CHECKS passed=${passed} total=${total}`)
  process.exitCode = passed === total ? 0 : 1
}
main().catch(e => { console.log('FATAL', e && e.message); console.log(`TOKENBENCH_CHECKS passed=${passed} total=${total}`); process.exitCode = 1 })
