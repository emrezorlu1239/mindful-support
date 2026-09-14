import { Client } from '@gradio/client';
import assert from 'node:assert/strict';
const base=process.env.MINDFUL_FIXTURE_URL || 'http://127.0.0.1:18765';
const headers={'Origin':'http://localhost:3000','Content-Type':'application/json'};
const boot=await fetch(base+'/api/bootstrap',{method:'POST',headers});
assert.equal(boot.status,200);
headers.Cookie=boot.headers.get('set-cookie').split(';')[0];
async function call(path, body) {
 const r=await fetch(base+path,{method:'POST',headers,body:JSON.stringify(body)});
 assert.ok(r.ok, `${path}: ${r.status}`); return r.json();
}
const b=await call('/api/bookings',{first_name:'Synthetic',last_name:'Protocol',gender:'unspecified',language:'en',adult_consent:true});
try {
 assert.equal((await call('/api/admission/join',{booking_id:b.id})).state,'active');
 const client=await Client.connect(base+'/api/gpu',{headers:{Origin:headers.Origin,Cookie:headers.Cookie},events:['data','status']});
 try {
  for(let i=0;i<3;i++) {
   const t=await call('/api/chat',{booking_id:b.id,request_id:crypto.randomUUID(),message:'A difficult day '+i});
   const result=await client.predict('/reply',[t.ticket]);
   assert.deepEqual(result.data,['ready']);
   const r=await fetch(base+'/api/chat/result?ticket='+t.ticket,{headers});
   assert.equal(r.status,200);assert.ok((await r.json()).reply);
  }
  const history=await (await fetch(base+'/api/chat/history?booking_id='+b.id,{headers})).json();
  assert.equal(history.messages.length,6);
  console.log('Official JS client: three turns and parent history passed.');
 }finally{client.close();}
}finally{await call('/api/admission/leave',{booking_id:b.id});}
