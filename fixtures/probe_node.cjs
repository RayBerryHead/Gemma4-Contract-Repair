'use strict'
// Execute one observable contract against the pinned upstream JavaScript code.
const fs = require('node:fs')
const path = require('node:path')
const { createServer } = require('node:http')
const { once } = require('node:events')
const { execFileSync } = require('node:child_process')

async function listen(server) {
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  return 'http://127.0.0.1:' + server.address().port
}
async function close(server) {
  await new Promise(resolve => server.close(resolve))
}
async function run(spec) {
  const { case: id, source, params } = spec
  if (id === 'CD1' || id === 'CD2') {
    const { newCache } = await import(require('node:url').pathToFileURL(path.join(source, 'subject.mjs')).href)
    const cache = newCache()
    return params.steps.map(([actor, key]) => cache.fetch(actor, key))
  }
  if (id.startsWith('C')) {
    const { Client, Agent, interceptors, cacheStores } = require(source)
    if (id === 'C2') {
      let redirectEnabled = !params.no_redirect
      let originCalls = 0
      const attacker = createServer((req, res) => {
        res.writeHead(200, { 'cache-control': 'public, max-age=86400' })
        res.end('attacker-controlled-content')
      })
      const attackerOrigin = await listen(attacker)
      const trusted = createServer((req, res) => {
        originCalls++
        if (redirectEnabled) {
          res.writeHead(302, { location: attackerOrigin + '/payload' })
          return res.end()
        }
        res.writeHead(200, { 'cache-control': params.public_control ? 'public, max-age=300' : 'no-store' })
        res.end('legitimate-content')
      })
      const origin = await listen(trusted)
      const agent = new Agent().compose(interceptors.redirect({ maxRedirections: 2 }), interceptors.cache({ store: new cacheStores.MemoryCacheStore(), type: 'shared' }))
      try {
        const first = await agent.request({ origin, path: params.path || '/resource', method: 'GET' })
        const firstBody = await first.body.text()
        redirectEnabled = false
        const second = await agent.request({ origin, path: params.path || '/resource', method: 'GET' })
        return { bodies: [firstBody, await second.body.text()], origin_calls: originCalls }
      } finally { await agent.close(); await close(trusted); await close(attacker) }
    }
    if (id === 'C1' && params.lifecycle) {
      let calls = 0
      let revalidationSeen = false
      let completeReplacement
      const replacement = new Promise(resolve => { completeReplacement = resolve })
      const originalNow = Date.now
      let clock = originalNow()
      Date.now = () => clock
      const server = createServer((req, res) => {
        calls++
        const actor = req.headers.cookie || 'anon'
        if (calls === 1) {
          res.writeHead(200, {
            'cache-control': params.lifecycle === 'swr' ? 'public, max-age=1, stale-while-revalidate=300' : 'public, max-age=300',
            etag: '"paper-v1"'
          })
          return res.end('public-body')
        }
        revalidationSeen ||= Boolean(req.headers['if-none-match'])
        res.on('finish', () => completeReplacement())
        res.writeHead(req.headers['if-none-match'] ? 304 : 200, {
          'cache-control': 'public, max-age=300',
          etag: '"paper-v1"',
          'set-cookie': 'session-for-' + actor
        })
        res.end(req.headers['if-none-match'] ? '' : 'public-body')
      })
      const origin = await listen(server)
      const store = new cacheStores.MemoryCacheStore()
      const client = new Client(origin).compose(interceptors.cache({ store, type: 'shared' }))
      let following
      let clientClosed = false
      const responses = []
      async function read(from, actor) {
        const headers = { cookie: actor }
        if (params.lifecycle === 'revalidate' && actor === (params.owner || 'alice')) headers['cache-control'] = 'no-cache'
        const response = await from.request({ origin, path: '/lifecycle', method: 'GET', headers })
        responses.push({ body: await response.body.text(), cookie: response.headers['set-cookie'] || null })
      }
      try {
        await read(client, 'warm-public')
        if (params.lifecycle === 'swr') clock += 2000
        await read(client, params.owner || 'alice')
        if (params.lifecycle === 'swr') {
          await replacement
          await client.close()
          clientClosed = true
          following = new Client(origin).compose(interceptors.cache({ store, type: 'shared' }))
        }
        await read(following || client, params.reader || 'bob')
        return { responses, origin_calls: calls, revalidation_seen: revalidationSeen }
      } finally {
        Date.now = originalNow
        if (!clientClosed) await client.close()
        if (following) await following.close()
        await close(server)
      }
    }
    let calls = 0
    const server = createServer((req, res) => {
      calls++
      const actor = req.headers.cookie || req.headers.authorization || 'anon'
      res.setHeader('cache-control', params.directive || 'public, max-age=300')
      if (id === 'C1' && !params.public) res.setHeader('set-cookie', 'session-for-' + actor)
      res.end(params.public ? 'public' : 'response for ' + actor)
    })
    const origin = await listen(server)
    const store = new cacheStores.MemoryCacheStore()
    const client = new Client(origin).compose(interceptors.cache({ store, type: params.private ? 'private' : 'shared' }))
    const privateClient = params.warm_private ? new Client(origin).compose(interceptors.cache({ store, type: 'private' })) : null
    const responses = []
    try {
      if (privateClient) {
        const response = await privateClient.request({ origin, path: '/', method: 'GET', headers: { cookie: params.actors[0] } })
        await response.body.text()
      }
      for (const actor of params.actors) {
        const headers = id === 'C7' ? (actor === 'anon' ? {} : { authorization: actor }) : { cookie: actor }
        const response = await client.request({ origin, path: '/', method: 'GET', headers })
        responses.push({ body: await response.body.text(), cookie: response.headers['set-cookie'] || null })
      }
      return { responses, origin_calls: calls }
    } finally { await client.close(); if (privateClient) await privateClient.close(); await close(server) }
  }
  const runtime = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../configs/runtime.free.json'), 'utf8'))
  const esbuild = process.env.PAPER_ESBUILD || path.join(runtime.artifact_root, 'node-runtime/node_modules/.bin/esbuild')
  const destination = path.join(fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'paper-bundle-')), 'module.cjs')
  const entry = id === 'T7' ? 'src/luxon.js' : 'src/differenceInDays/index.js'
  execFileSync(esbuild, [path.join(source, entry), '--bundle', '--platform=node', '--format=cjs', '--outfile=' + destination, '--log-level=error'])
  const module = require(destination)
  if (id === 'T7') {
    const { DateTime } = module
    const value = DateTime.fromObject({ ...params.date, zone: params.source_zone })
    const result = value.setZone(params.target_zone, { keepLocalTime: params.keep_local })
    return { wall: result.toFormat('yyyy-MM-dd HH:mm'), instant_preserved: result.toMillis() === value.toMillis(), valid: result.isValid }
  }
  if (id === 'T8') {
    const difference = module.default || module
    return difference(new Date(...params.end), new Date(...params.start))
  }
  throw new Error('Unsupported JavaScript case ' + id)
}
;(async () => {
  const spec = JSON.parse(fs.readFileSync(0, 'utf8'))
  try {
    console.log(JSON.stringify({ execution: 'VALID', observed: await run(spec) }))
  } catch (error) {
    console.log(JSON.stringify({ execution: error.code === 'MODULE_NOT_FOUND' ? 'INFRA_ERROR' : 'PRODUCT_EXCEPTION', error_type: error.name, error: error.message }))
    process.exitCode = 0
  }
})()
