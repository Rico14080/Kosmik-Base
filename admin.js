'use strict';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=c=>new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(c/100);
let csrf='',dirty=false,saveCurrent=null,tab='dashboard',busy=false;
function status(message){$('#admin-status').textContent=message}
async function api(path,data){
  const response=await fetch('/api/admin'+path,{method:data?'POST':'GET',headers:{Accept:'application/json',...(data?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(30000)});
  const result=await response.json();
  if(!response.ok){if(response.status===401){$('#login-form').hidden=false;status('Session expired. Sign in to continue; unsaved fields are retained.')}throw Error(result.error||'Request failed');}
  return result;
}
function track(){dirty=true;status('Unsaved changes')}
addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue=''}});
async function canLeave(){
  if(!dirty)return true;
  const dialog=$('#unsaved-dialog');dialog.showModal();
  const choice=await new Promise(resolve=>{const click=e=>{if(!e.target.dataset.choice)return;dialog.removeEventListener('click',click);dialog.close();resolve(e.target.dataset.choice)};dialog.addEventListener('click',click);dialog.addEventListener('cancel',()=>{dialog.removeEventListener('click',click);resolve('stay')},{once:true})});
  if(choice==='stay')return false;
  if(choice==='save'){try{await saveCurrent();return !dirty}catch(e){status(e.message);return false}}
  dirty=false;return true;
}
document.addEventListener('click',async e=>{const a=e.target.closest('a[href]');if(a&&dirty){e.preventDefault();if(await canLeave())location.assign(a.href)}});
function field(label,name,value='',type='text',required=false){return `<label>${esc(label)}<input name="${esc(name)}" type="${type}" value="${esc(value)}" ${required?'required':''}></label>`}
function button(text,attrs=''){return `<button class="admin-button" ${attrs}>${esc(text)}</button>`}
function watch(form,save){dirty=false;saveCurrent=save;form.addEventListener('input',track);form.addEventListener('change',track);form.addEventListener('submit',async e=>{e.preventDefault();if(busy)return;busy=true;const buttons=form.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);try{await save()}catch(e){status(e.message)}finally{busy=false;buttons.forEach(b=>b.disabled=false)}})}
function treeFields(value,path=[]){
  if(Array.isArray(value))return value.map((v,i)=>`<fieldset><legend>${esc(path.at(-1))} ${i+1}</legend>${treeFields(v,[...path,i])}</fieldset>`).join('');
  if(value&&typeof value==='object')return Object.entries(value).filter(([k])=>k!=='id').map(([k,v])=>`<div class="admin-field-group">${treeFields(v,[...path,k])}</div>`).join('');
  const name=esc(JSON.stringify(path)),label=esc(path.join(' / '));
  if(typeof value==='boolean')return `<label><input type="checkbox" data-path="${name}" ${value?'checked':''}> ${label}</label>`;
  if(typeof value==='number')return `<label>${label}<input type="number" step="any" data-path="${name}" value="${value}"></label>`;
  const image=/image|photo$/i.test(String(path.at(-1)))&&!/alt/i.test(String(path.at(-1)));
  return `<label>${label}<textarea data-path="${name}" rows="${String(value||'').length>140?4:2}">${esc(value??'')}</textarea></label>${image?`<label>Upload image<input type="file" accept="image/png,image/jpeg,image/webp,image/gif" data-upload-path="${name}"></label><img class="admin-preview" data-preview-path="${name}" alt="Image preview" ${value?`src="${esc(value)}"`:'hidden'}>`:''}`;
}
function collectTree(form,original){const value=structuredClone(original);form.querySelectorAll('[data-path]').forEach(input=>{const path=JSON.parse(input.dataset.path);let target=value;for(const k of path.slice(0,-1))target=target[k];target[path.at(-1)]=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value});return value}
function bindUploads(form){form.querySelectorAll('[data-upload-path]').forEach(input=>input.addEventListener('change',async()=>{const file=input.files[0];if(!file)return;if(file.size>5*1024*1024){status('Image must be under 5 MB');return;}try{const response=await fetch('/api/admin/upload',{method:'POST',headers:{'Content-Type':file.type,'X-CSRF-Token':csrf},body:file});const data=await response.json();if(!response.ok)throw Error(data.error);const target=[...form.querySelectorAll('[data-path]')].find(e=>e.dataset.path===input.dataset.uploadPath);target.value=data.url;const preview=[...form.querySelectorAll('[data-preview-path]')].find(e=>e.dataset.previewPath===input.dataset.uploadPath);preview.src=data.url;preview.hidden=false;track();}catch(e){status(e.message)}}))}
async function loadTab(next){
  if(!(await canLeave()))return;
  tab=next;saveCurrent=null;status('Loading…');$('#admin-nav').querySelectorAll('button').forEach(b=>b.setAttribute('aria-current',b.dataset.tab===tab?'page':'false'));
  try{await ({dashboard:dashboard,orders:orders,products:products,content:content,settings:settings}[tab])();status('Ready')}catch(e){status(e.message)}
}
async function dashboard(){
  const data=await api('/stats');
  $('#admin-view').innerHTML=`<h2>Dashboard</h2><div class="admin-fields">${Object.entries(data).filter(([,v])=>typeof v==='number').map(([k,v])=>`<p><strong>${v}</strong> ${esc(k)}</p>`).join('')}</div><h3>Services</h3><dl>${Object.entries(data.services).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'Not yet created')}</dd>`).join('')}</dl><h3>Recent orders</h3>${data.recentOrders.map(o=>`<p>${esc(o.id)} · ${money(o.total_cents)} · ${esc(o.payment_status)} / ${esc(o.shipping_status)} ${esc(o.issue)}</p>`).join('')||'<p>No orders yet.</p>'}<h3>Email queue</h3>${data.mail.map(m=>`<p>${esc(m.id)} · ${esc(m.recipient)} · ${esc(m.state)} ${m.state==='uncertain'?button('Review and retry',`type="button" data-retry="${esc(m.id)}"`):''}</p>`).join('')||'<p>No pending messages.</p>'}<h3>Activity</h3>${data.activity.map(a=>`<p>${esc(a.created_at)} · ${esc(a.action)} · ${esc(a.reference)}</p>`).join('')}<details><summary>Contact messages</summary><div id="messages"></div></details>`;
  $('#admin-view').querySelectorAll('[data-retry]').forEach(b=>b.addEventListener('click',async()=>{if(!confirm('The message may already have been delivered. Check the mailbox/provider first. Retry now?'))return;try{await api('/mail/retry',{id:b.dataset.retry,confirm:true});await dashboard()}catch(e){status(e.message)}}));
  const messages=await api('/messages');$('#messages').innerHTML=messages.messages.map(m=>`<article><h4>${esc(m.name)} · ${esc(m.email)}</h4><p class="preserve-lines">${esc(m.message)}</p></article>`).join('')||'No messages.';
}
async function orders(){
  const data=await api('/orders');
  $('#admin-view').innerHTML='<h2>Orders</h2><label>Search ID, email or name<input id="order-search" type="search"></label><label>Payment<select id="payment-filter"><option value="">All</option>'+['PENDING','PAID','FAILED','REFUNDED'].map(v=>`<option>${v}</option>`).join('')+'</select></label><label>Fulfillment<select id="fulfillment-filter"><option value="">All</option>'+['NEW','PREPARING','SHIPPED','DELIVERED'].map(v=>`<option>${v}</option>`).join('')+'</select></label><div id="order-list"></div>';
  function render(){const search=$('#order-search').value.toLowerCase(),payment=$('#payment-filter').value,fulfillment=$('#fulfillment-filter').value;
    $('#order-list').innerHTML=data.orders.filter(o=>(!payment||o.payment_status===payment)&&(!fulfillment||o.shipping_status===fulfillment)&&`${o.id} ${o.name} ${o.email}`.toLowerCase().includes(search)).map(o=>`<details class="admin-section"><summary>${esc(o.id)} · ${money(o.total_cents)} · ${esc(o.payment_status)} / ${esc(o.shipping_status)}</summary><p>${esc(o.name)} · ${esc(o.email)} · ${esc(o.phone)}</p><p>${esc([o.address,o.city,o.postcode,o.country].filter(Boolean).join(', '))}</p><p>Delivery: ${esc(o.shipping_method)} · ${money(o.shipping_cents)}</p><ul>${o.items.map(i=>`<li>${esc(i.sku)} · ${esc(i.name)} ${esc(i.variant)} · ${i.quantity} × ${money(i.priceCents)}</li>`).join('')}</ul><p>Stripe session: ${esc(o.stripe_session_id||'Not created')}</p><p>Payment reference: ${esc(o.payment_intent||'Pending')}</p>${o.issue?`<p role="alert">Attention: ${esc(o.issue)}</p>`:''}<form data-order="${esc(o.id)}"><label>Fulfillment<select name="fulfillmentStatus">${['NEW','PREPARING','SHIPPED','DELIVERED'].map(s=>`<option ${s===o.shipping_status?'selected':''}>${s}</option>`).join('')}</select></label>${field('Tracking reference / URL','tracking',o.tracking)}<label>Internal notes<textarea name="notes">${esc(o.notes)}</textarea></label>${button('Save fulfillment','type="submit" '+(o.payment_status!=='PAID'||o.issue?'disabled':''))}</form><p>Refunds: open this payment in Stripe, verify the amount and confirm the refund there. The signed refund webhook updates the payment state here. Stock is restored separately after checking the returned item.</p><a href="https://dashboard.stripe.com/payments" target="_blank" rel="noopener noreferrer">Open Stripe payments</a></details>`).join('')||'<p>No matching orders.</p>';
    $('#order-list').querySelectorAll('form').forEach(form=>{form.addEventListener('input',()=>{track();saveCurrent=()=>save(form)});form.addEventListener('change',()=>{track();saveCurrent=()=>save(form)});form.addEventListener('submit',async e=>{e.preventDefault();try{await save(form)}catch(e){status(e.message)}})});
  }
  async function save(form){await api('/orders/status',{orderId:form.dataset.order,...Object.fromEntries(new FormData(form))});dirty=false;status('Order saved');await orders()}
  for(const id of ['order-search','payment-filter','fulfillment-filter'])$('#'+id).addEventListener('change',async()=>{if(await canLeave())render()});render();
}
async function content(){
  const data=await api('/content');let section=Object.keys(data.content)[0],original;
  $('#admin-view').innerHTML=`<h2>Content</h2><label>Section<select id="content-section">${Object.keys(data.content).map(k=>`<option>${esc(k)}</option>`).join('')}</select></label><div id="content-editor"></div>`;
  function render(){original=structuredClone(data.content[section]);const editor=$('#content-editor');editor.innerHTML=`<form><h3>${esc(section)}</h3>${treeFields(original)}${section==='live'?button('Add event','type="button" id="add-event"'):''}${button('Save this section','type="submit"')}</form>`;const form=editor.querySelector('form');
    watch(form,async()=>{const value=collectTree(form,original),result=await api('/content',{section,value,version:data.version});data.content=result.content;data.version=result.version;dirty=false;render();status('Section saved')});bindUploads(form);
    if(section==='live')$('#add-event').addEventListener('click',()=>{data.content[section]=collectTree(form,original);data.content[section].push({title:'',date:'',isoDate:'',location:'',venue:'',signal:'',detail:'',action:'Tickets',ticketUrl:'',past:false,visible:false});render();track()});
  }
  $('#content-section').addEventListener('change',async e=>{const next=e.target.value;if(await canLeave()){section=next;render()}else e.target.value=section});render();
}
async function products(){
  const data=await api('/products');let selected=null;
  $('#admin-view').innerHTML=`<h2>Products</h2><label>Product<select id="product-select"><option value="">New product</option>${data.products.map(p=>`<option value="${p.id}">${esc(p.sku)} · ${esc(p.name)}${p.active?'':' (hidden)'}</option>`).join('')}</select></label><div id="product-editor"></div><h3>Stock movements</h3><div>${data.history.map(h=>`<p>${esc(h.created_at)} · Product ${h.product_id}${h.variant_id?' / variant '+h.variant_id:''} · ${h.delta>0?'+':''}${h.delta} · ${esc(h.reason)} · ${esc(h.reference)}</p>`).join('')}</div>`;
  function render(p,isNew=!p?.id){selected=p;const original=p||{name:'',sku:'',meta:'',description:'',priceCents:0,image:'',alt:'',active:false,variants:[]};
    const editable={name:original.name,sku:original.sku,meta:original.meta||'',description:original.description||'',priceCents:original.priceCents,image:original.image||'',alt:original.alt||'',active:Boolean(original.active),variants:(original.variants||[]).map(v=>({...v,active:Boolean(v.active)}))};
    editable.variants=editable.variants.map(({id,sku,size,color,active})=>({...id?{id}:{},sku,size,color,active}));
    $('#product-editor').innerHTML=`<form id="product-form">${treeFields(editable)}<p>Prices are in cents. Stock is changed only in the separate form below.</p>${button('Add size / color variant','type="button" id="add-variant"')}${button('Save product details','type="submit"')}</form>${!isNew?`<form id="stock-form"><h3>Adjust stock</h3><label>Inventory<select name="variantId">${p.hasVariants?p.variants.map(v=>`<option value="${v.id}">${esc(v.sku)} — stock ${v.stock}, reserved ${v.reserved_stock}</option>`).join(''):`<option value="">${esc(p.sku)} — stock ${p.stock}, reserved ${p.reserved_stock}</option>`}</select></label>${field('Adjustment (e.g. 5 or -2)','delta',0,'number',true)}${field('Reason','reason','','text',true)}${button('Apply stock adjustment','type="submit"')}</form>`:''}`;
    const form=$('#product-form');watch(form,async()=>{const value=collectTree(form,editable);const result=await api('/products',{...value,...(!isNew?{id:p.id,version:p.version}:{})});dirty=false;status('Product saved');await products();$('#product-select').value=String(result.id);$('#product-select').dispatchEvent(new Event('change'))});bindUploads(form);
    $('#add-variant').addEventListener('click',()=>{const value=collectTree(form,editable);value.variants.push({sku:'',size:'',color:'',active:true});render({...original,...value},isNew);track()});
    const stock=$('#stock-form');if(stock)stock.addEventListener('submit',async e=>{e.preventDefault();if(dirty){status('Save product details before adjusting stock.');return;}const d=Object.fromEntries(new FormData(stock));if(!confirm(`Apply stock adjustment ${d.delta}?`))return;try{await api('/stock',{productId:p.id,variantId:d.variantId?Number(d.variantId):null,delta:Number(d.delta),reason:d.reason});await products();$('#product-select').value=String(p.id);$('#product-select').dispatchEvent(new Event('change'));status('Stock updated')}catch(e){status(e.message)}});
  }
  $('#product-select').addEventListener('change',async e=>{const id=e.target.value;if(await canLeave())render(data.products.find(p=>p.id===Number(id))||null);else e.target.value=selected?.id||''});render(null);
}
async function settings(){
  const data=await api('/settings');const s=data.settings;
  $('#admin-view').innerHTML=`<h2>Settings</h2><form id="settings-form">${treeFields({domain:s.domain,businessEmail:s.businessEmail,links:s.links})}<h3>Shipping</h3><p>One zone per line: name | country codes separated by commas | price in cents.</p><label>Zones<textarea name="zones" rows="5">${esc(s.shipping.zones.map(z=>`${z.name} | ${z.countries.join(',')} | ${z.priceCents}`).join('\n'))}</textarea></label>${field('Free shipping threshold in cents (empty = disabled)','freeThresholdCents',s.shipping.freeThresholdCents??'','number')}<label><input name="pickupEnabled" type="checkbox" ${s.shipping.pickupEnabled?'checked':''}> Enable local pickup</label>${field('Pickup address','pickupAddress',s.shipping.pickupAddress)}<label>Pickup instructions<textarea name="pickupInstructions">${esc(s.shipping.pickupInstructions)}</textarea></label><p>Pickup remains unavailable to customers until both address and instructions are filled.</p>${button('Save settings','type="submit"')}</form><h3>Backup</h3><p>Private backup includes a consistent SQLite snapshot and uploaded images.</p>${button('Create backup now','type="button" id="backup-now"')}<p id="backup-status" role="status"></p><p>Secrets are configured on the server, never in this panel.</p>`;
  const form=$('#settings-form');watch(form,async()=>{const value=collectTree(form,{domain:s.domain,businessEmail:s.businessEmail,links:s.links}),d=Object.fromEntries(new FormData(form));value.shipping={zones:d.zones.trim()?d.zones.trim().split('\n').map(line=>{const [name,countries,price]=line.split('|').map(v=>v.trim());if(!name||!countries||price==null||price==='')throw Error('Each zone needs name | countries | price in cents');return {name,countries:countries.toUpperCase().split(',').map(c=>c.trim()),priceCents:Number(price)}}):[],freeThresholdCents:d.freeThresholdCents===''?null:Number(d.freeThresholdCents),pickupEnabled:form.elements.pickupEnabled.checked,pickupAddress:d.pickupAddress,pickupInstructions:d.pickupInstructions};await api('/settings',{value,version:data.version});dirty=false;await settings();status('Settings saved')});
  $('#backup-now').addEventListener('click',async()=>{const b=$('#backup-now');b.disabled=true;try{const result=await api('/backup',{});$('#backup-status').textContent='Backup created: '+result.createdAt}catch(e){$('#backup-status').textContent=e.message}finally{b.disabled=false}});
}
$('#admin-nav').addEventListener('click',e=>{if(e.target.dataset.tab)loadTab(e.target.dataset.tab)});
$('#login-form').addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget;try{const result=await api('/login',{password:new FormData(form).get('password')});csrf=result.csrfToken;form.reset();$('#login-form').hidden=true;$('#admin-app').hidden=false;$('#logout').hidden=false;if(!dirty)await loadTab(tab);else status('Signed in. Unsaved fields retained.')}catch(e){status(e.message)}});
$('#logout').addEventListener('click',async()=>{if(!(await canLeave()))return;try{await api('/logout',{});csrf='';$('#admin-app').hidden=true;$('#login-form').hidden=false;$('#logout').hidden=true;status('Signed out')}catch(e){status(e.message)}});
(async()=>{try{const data=await api('/session');csrf=data.csrfToken;$('#login-form').hidden=true;$('#admin-app').hidden=false;$('#logout').hidden=false;await loadTab('dashboard')}catch{status('Sign in to manage the site')}})();

