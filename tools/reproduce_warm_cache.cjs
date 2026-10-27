'use strict'
const {createServer}=require('node:http')
const {once}=require('node:events')
;(async()=>{
 const source=process.argv[2]
 const {Client,interceptors,cacheStores}=require(source)
 let originCalls=0
 const server=createServer((req,res)=>{
  originCalls++
  const actor=req.headers.cookie
  res.setHeader('cache-control','public, max-age=300')
  res.setHeader('set-cookie','session-for-'+actor)
  res.end('response for '+actor)
 })
 server.listen(0,'127.0.0.1');await once(server,'listening')
 const origin='http://127.0.0.1:'+server.address().port
 const store=new cacheStores.MemoryCacheStore()
 const privateClient=new Client(origin).compose(interceptors.cache({store,type:'private'}))
 const sharedClient=new Client(origin).compose(interceptors.cache({store,type:'shared'}))
 try{
  const warm=await privateClient.request({origin,path:'/',method:'GET',headers:{cookie:'alice'}})
  const first={body:await warm.body.text(),cookie:warm.headers['set-cookie']}
  const read=await sharedClient.request({origin,path:'/',method:'GET',headers:{cookie:'bob'}})
  const second={body:await read.body.text(),cookie:read.headers['set-cookie']}
  console.log(JSON.stringify({source,public_subject_calls:2,origin_calls:originCalls,first,second,
    private_entry_replayed_to_bob:second.body==='response for alice'||second.cookie==='session-for-alice'}))
 }finally{await privateClient.close();await sharedClient.close();await new Promise(resolve=>server.close(resolve))}
})().catch(error=>{console.error(error);process.exitCode=1})
