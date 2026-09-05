(()=>{
'use strict';
const API=(location.protocol==='http:'||location.protocol==='https:')?`${location.origin}/api`:'http://127.0.0.1:8080/api';
let token=sessionStorage.getItem('kosmik_admin_token')||'';
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const auth=()=>token?{Authorization:`Bearer ${token}`} : {};
async function api(path,opts={}){
  token=sessionStorage.getItem('kosmik_admin_token')||'';
  if(!token)throw new Error('Not authenticated.');
  const headers={Accept:'application/json',...auth(),...(opts.headers||{})};
  if(opts.body&&!(opts.body instanceof Blob))headers['Content-Type']='application/json';
  let r;
  try{r=await fetch(API+path,{...opts,headers})}catch(e){throw new Error(`API connection failed (${API}). Start the backend and open the site through the server URL.`)}
  const d=await r.json().catch(()=>({}));
  if(r.status===401){token='';sessionStorage.removeItem('kosmik_admin_token');throw new Error('Session expired.')}
  if(!r.ok)throw new Error(d.error||'Request failed');
  return d;
}
function statusMessage(message){const el=$('status');if(el)el.textContent=message;}
function formatDate(value){const d=new Date(value);return Number.isNaN(d.getTime())?String(value||''):d.toLocaleString();}
function itemSummary(itemsJson){
  try{
    const items=JSON.parse(itemsJson||'[]');
    return items.map(item=>`${Number(item.quantity)||0} × ${esc(item.name||'Product')} (€ ${(Number(item.priceCents)||0)/100})`).join('<br>');
  }catch{return ''}
}
async function renderOrdersOps(){
  const root=$('orders-list');
  if(!root)return;
  try{
    const d=await api('/admin/orders');
    const orders=Array.isArray(d.orders)?d.orders:[];
    root.innerHTML=orders.length?orders.map(o=>{
      const current=String(o.status||'NEW').toUpperCase();
      const disabledPaid=current==='PAID';
      return `<article class="admin-order"><strong>${esc(o.id)}</strong><span>${esc(o.name||'')} / ${esc(o.email||'')}</span><small>${esc(formatDate(o.created_at))}</small><p>${itemSummary(o.items_json)}</p><label>Status <select data-order-status="${esc(o.id)}"><option value="NEW" ${current==='NEW'?'selected':''}>NEW</option><option value="PAID" disabled ${disabledPaid?'selected':''}>PAID / provider-confirmed</option><option value="PROCESSING" ${current==='PROCESSING'?'selected':''}>PROCESSING</option><option value="SHIPPED" ${current==='SHIPPED'?'selected':''}>SHIPPED</option><option value="DELIVERED" ${current==='DELIVERED'?'selected':''}>DELIVERED</option><option value="CANCELLED" ${current==='CANCELLED'?'selected':''}>CANCELLED</option><option value="REFUNDED" ${current==='REFUNDED'?'selected':''}>REFUNDED</option></select></label></article>`;
    }).join(''):'<p class="admin-muted">No orders received yet.</p>';
  }catch(e){root.innerHTML=`<p class="admin-muted">${esc(e.message)}</p>`}
}
async function renderMessagesOps(){
  const root=$('messages-list');
  if(!root)return;
  try{
    const d=await api('/admin/messages');
    const messages=Array.isArray(d.messages)?d.messages:[];
    root.innerHTML=messages.length?messages.map(m=>`<article class="admin-message" data-message-id="${esc(m.id)}"><strong>${esc(m.name||'Anonymous')}</strong><span>${esc(m.email||'')}</span><small>${esc(formatDate(m.created_at))}</small><p>${esc(m.message||'').replace(/\n/g,'<br>')}</p><button class="admin-button secondary" data-delete-message type="button">Delete</button></article>`).join(''):'<p class="admin-muted">No messages received yet.</p>';
  }catch(e){root.innerHTML=`<p class="admin-muted">${esc(e.message)}</p>`}
}
async function updateOrderStatus(select){
  try{
    await api('/admin/orders/status',{method:'POST',body:JSON.stringify({id:select.dataset.orderStatus,status:select.value})});
    statusMessage('Order status updated.');
    await renderOrdersOps();
  }catch(e){statusMessage(e.message);await renderOrdersOps()}
}
async function deleteMessage(button){
  const card=button.closest('[data-message-id]');
  if(!card)return;
  const id=card.dataset.messageId;
  if(!confirm('Delete this message?'))return;
  try{
    await api(`/admin/messages?id=${encodeURIComponent(id)}`,{method:'DELETE'});
    statusMessage('Message deleted.');
    await renderMessagesOps();
  }catch(e){statusMessage(e.message)}
}
async function waitForAuthentication(){
  for(let i=0;i<120;i++){
    token=sessionStorage.getItem('kosmik_admin_token')||'';
    if(token){await renderOrdersOps();await renderMessagesOps();return}
    await new Promise(resolve=>setTimeout(resolve,250));
  }
}
function bind(){
  document.addEventListener('change',e=>{const s=e.target.closest('[data-order-status]');if(s)updateOrderStatus(s)});
  document.addEventListener('click',e=>{const b=e.target.closest('[data-delete-message]');if(b)deleteMessage(b)});
  waitForAuthentication().catch(e=>statusMessage(e.message));
}
bind();
})();
