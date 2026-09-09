(()=>{
const API=(location.protocol==='http:'||location.protocol==='https:')?`${location.origin}/api`:'http://127.0.0.1:8080/api';
const CART_KEY='kosmik-circles-cart';
const getCart=()=>{try{const v=JSON.parse(localStorage.getItem(CART_KEY)||'[]');return Array.isArray(v)?v:[]}catch{return[]}};
const clearCart=()=>{localStorage.removeItem(CART_KEY);document.querySelectorAll('[data-cart-count], .bag-link span').forEach(e=>e.textContent='0');};
document.addEventListener('submit',async e=>{
  const form=e.target;
  if(!form.matches('[data-order-form]')||form.dataset.checkoutFixBound==='1')return;
  form.dataset.checkoutFixBound='1';
  e.preventDefault(); e.stopImmediatePropagation();
  if(form.dataset.submitting==='1')return;
  const submit=form.querySelector('button[type="submit"]'),status=document.querySelector('[data-cart-status]');
  form.dataset.submitting='1'; if(submit)submit.disabled=true; if(status)status.textContent='Sending order…';
  const fd=new FormData(form),items=getCart();
  try{
    if(!items.length)throw new Error('Your cart is empty.');
    const r=await fetch(`${API}/checkout`,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({email:String(fd.get('email')||'').trim(),customer:{name:fd.get('name'),phone:fd.get('phone'),address:fd.get('address'),city:fd.get('city'),postcode:fd.get('postcode'),country:fd.get('country')},items})});
    const d=await r.json().catch(()=>({})); if(!r.ok)throw new Error(d.error||'Checkout failed');
    if(d.checkoutUrl){sessionStorage.setItem('kosmik_pending_order',String(d.orderId||''));window.location.href=d.checkoutUrl;return;}
    if(d.orderId){clearCart();if(status)status.textContent=d.message||`Order ${d.orderId} created.`;}
  }catch(err){if(status)status.textContent=err.message||'Unable to send order.';form.dataset.submitting='0';if(submit)submit.disabled=false;}
},true);
const settlePayment=async()=>{
 const params=new URLSearchParams(location.search),payment=params.get('payment'),order=params.get('order');
 if(payment!=='success'||!order)return;
 try{
  const r=await fetch(`${API}/orders/status?id=${encodeURIComponent(order)}`,{headers:{Accept:'application/json'},cache:'no-store'}),d=await r.json().catch(()=>({}));
  if(r.ok&&d.paymentStatus==='PAID'){clearCart();sessionStorage.removeItem('kosmik_pending_order');}
 }catch{}
};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',settlePayment,{once:true});else settlePayment();
})();
