(()=>{
'use strict';
const STORAGE_KEY='kosmik-circles-cart';
function cartCount(){try{const c=JSON.parse(localStorage.getItem(STORAGE_KEY)||'[]');return Array.isArray(c)?c.reduce((n,i)=>n+Math.max(1,Number.parseInt(i?.quantity,10)||1),0):0}catch{return 0}}
function syncBag(){const count=cartCount();document.querySelectorAll('[data-cart-count]').forEach(el=>{el.textContent=String(count)});const content=window.KosmikCMS?.getContent?.();const labels=content?.siteText?.nav||{};document.querySelectorAll('.bag-link [data-nav-label]').forEach(el=>{const isCart=location.pathname.toLowerCase().endsWith('cart.html');el.textContent=isCart?(labels.cart||'Cart'):(labels.bag||'Bag')})}
function bindNoTicket(){document.querySelectorAll('[data-no-ticket]').forEach(link=>{if(link.dataset.noTicketBound)return;link.dataset.noTicketBound='1';link.addEventListener('click',e=>e.preventDefault())})}
function syncMatrixVisibility(){document.querySelectorAll('#matrix-background').forEach(canvas=>{canvas.style.visibility=document.hidden?'hidden':'visible'})}
function init(){syncBag();bindNoTicket();syncMatrixVisibility();const observer=new MutationObserver(()=>{syncBag();bindNoTicket();syncMatrixVisibility()});observer.observe(document.body,{subtree:true,childList:true});window.addEventListener('storage',syncBag);window.addEventListener('pageshow',syncBag);document.addEventListener('visibilitychange',syncMatrixVisibility)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
