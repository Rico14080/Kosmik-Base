const STORAGE_KEY = 'kosmik-circles-content';
const CART_KEY = 'kosmik-circles-cart';
const API_BASE = (location.protocol === 'http:' || location.protocol === 'https:') ? `${location.origin}/api` : 'http://127.0.0.1:8080/api';
const defaultContent = {
  home: { eyebrow:'Independent objects / Est. 2024', titleLineOne:'Made for', titleLineTwo:'elsewhere.', intro:'Small-batch goods for people who keep looking up. Wearable signals, useful artifacts, and a little cosmic noise.', cta:'Enter the orbit', heroImage:'https://images.unsplash.com/photo-1534791547706-5c292f749e1b?auto=format&fit=crop&w=1200&q=85', heroAlt:'Orange light cutting through a dark concert atmosphere', signalText:'new objects for old souls', orbitLabelTop:'38° 11′ 52″ N', orbitLabelBottom:'signal / 001', heroIndex:'01 / 04', sectionNumber:'[ 001 ]', signalStripLabel:'Currently transmitting', introEyebrow:'The short version', introTitleLineOne:'Good things can', introTitleLineTwo:'still feel unknown.', introDescription:'Kosmik Circles is a design studio making limited-run pieces with a point of view. We work slowly, source carefully, and leave enough room for the weirdness to get in.' },
  pages: { shop:{eyebrow:'Available now / Dispatching worldwide',titleLineOne:'Objects with',titleLineTwo:'an orbit.',note:'Four small-batch pieces. No restocks promised.'}, live:{eyebrow:'Transmission schedule / 2026',titleLineOne:'Come',titleLineTwo:'through.',note:'Night flights, deep rooms, high frequencies.'}, contact:{eyebrow:'Open frequency / gus@kosmikcircles.com',titleLineOne:'Send a',titleLineTwo:'signal.',note:''}, cart:{eyebrow:'Your selected objects',titleLineOne:'Enter the',titleLineTwo:'cart.',note:'Leave your email and send the order signal.'} },
  ticker:{text:'NEW TRANSMISSION SOON ✳ KOSMIK CIRCLES / SMALL BATCH / LIVE AUDIOVISUAL SIGNALS',speed:28,fontSize:11}, matrix:{speed:0.45},
  contact:{email:'gus@kosmikcircles.com',instagram:'Instagram',instagramUrl:'',youtube:'YouTube',youtubeUrl:'',sectionNumber:'[ 003 ]',description:'Kosmik Circles offers live electronic music, audiovisual performances, DJ sets, and sound direction for clubs, festivals, brands, and private spaces. Tell us what you are building and we will shape the frequency with you.',serviceTitleOne:'We create',serviceTitleTwo:'signals.',formIntro:'Start with an email. We answer within 2-3 Earth days.'}, live:[{date:'18.10.24',isoDate:'2024-10-18',location:'Milano, IT',venue:'Magazzini Generali / 23:00',signal:'Circles / 01',detail:'Full live set',action:'Tickets',ticketUrl:'',past:true},{date:'02.11.24',isoDate:'2024-11-02',location:'Berlin, DE',venue:'Ritter Butzke / 00:30',signal:'Night Channel',detail:'2 hour live set',action:'Tickets',ticketUrl:'',past:true},{date:'24.01.25',isoDate:'2025-01-24',location:'Lisboa, PT',venue:'Lux Frágil / 01:00',signal:'Outer Room',detail:'Live + visual show',action:'Tickets',ticketUrl:'',past:true},{date:'31.08.24',isoDate:'2024-08-31',location:'Paris, FR',venue:'La Machine / 23:30',signal:'Soft Landing',detail:'Archive recording',action:'Archive',ticketUrl:'',past:true}], shop:[],
  visuals:{liveBackgroundImage:'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=85'},
  images:{home:{primary:{motion:'none'},secondary:{image:'',alt:'',motion:'none'}},live:{primary:{image:'',alt:'',motion:'none'},secondary:{image:'',alt:'',motion:'none'}},contact:{primary:{image:'',alt:'',motion:'none'},secondary:{image:'',alt:'',motion:'none'}},shop:{primary:{image:'',alt:'',motion:'none'},secondary:{image:'',alt:'',motion:'none'}}},
  siteText:{skipToContent:'Skip to content',liveUpdates:'Live updates',nav:{home:'Home',shop:'Shop',live:'Live',contact:'Contact',bag:'Bag',cart:'Cart'},home:{currentlyTransmitting:'Currently transmitting'},shop:{addToCart:'Add to cart'},live:{date:'Date',location:'Location',signal:'Signal',noTicket:'Tickets'},contact:{name:'Your name',email:'Your email',message:'Your message',submit:'Transmit'},cart:{yourName:'Your name',yourEmail:'Your email',phone:'Phone',address:'Address',city:'City',postcode:'Postcode',country:'Country',sendOrder:'Send order',remove:'Remove',empty:'Your cart is orbiting empty.',sending:'Sending order…',quantity:'quantity',total:'Total'},footer:{tagline:'Made on Earth, for now',homeCta:'Say hello',shopCta:'Say hello',liveCta:'Book a transmission',contactCta:'Browse objects',cartCta:'Back to shop'}}
};
let remoteContent = null;
let backendReady=false,siteConfig={};
Object.assign(defaultContent.home,{groupEyebrow:'Who we are',groupTitleLineOne:'One circle.',groupTitleLineTwo:'Many signals.',groupDescription:'Kosmik Circles is an independent collective exploring electronic music, visual experimentation and live experiences. We bring together sound, light and creative practice to build shared spaces, performances and collaborations.',groupSecondary:'Born from a shared interest in electronic culture, Kosmik Circles moves between DJ sets, audiovisual performance, experimental projects and events.',groupCta:'Send a signal'});
function deepMerge(base,saved){if(Array.isArray(base))return Array.isArray(saved)?saved:JSON.parse(JSON.stringify(base));if(base&&typeof base==='object'){const out={...base};if(saved&&typeof saved==='object'&&!Array.isArray(saved))for(const k of Object.keys(saved))out[k]=k in out?deepMerge(out[k],saved[k]):saved[k];return out;}return saved===undefined?base:saved;}
function mergeContent(saved){const content=deepMerge(defaultContent,saved||{});delete content.us;delete content.pages?.us;delete content.siteText?.nav?.us;delete content.siteText?.footer?.usCta;return content}
function getContent(){return remoteContent||defaultContent}
async function fetchContent(){try{const [content,config]=await Promise.all([publicApi('/content'),publicApi('/config')]);remoteContent=mergeContent(content);siteConfig=config;backendReady=true;}catch{backendReady=false;}return getContent()}
function isSafeUrl(v='',opts={}){const raw=String(v).trim();if(!raw||raw.startsWith('//')||raw.includes('\\'))return false;try{const u=new URL(raw,location.href);return u.protocol==='https:'||(u.origin===location.origin&&u.protocol===location.protocol)||(opts.allowMailto&&u.protocol==='mailto:')}catch{return false}}
function safeExternalUrl(v=''){return isSafeUrl(v)?String(v).trim():''}
function safeImageUrl(v=''){return isSafeUrl(v,{allowDataImage:true})?String(v).trim():''}
function cssUrl(v=''){const s=String(v||'');return `url(${JSON.stringify(s)})`}
function parsePrice(v=''){const raw=String(v).trim().replace(/[^0-9,.]/g,'');if(!raw)return 0;const n=raw.includes(',')&&raw.includes('.')?(raw.lastIndexOf(',')>raw.lastIndexOf('.')?raw.replace(/\./g,'').replace(',','.'):raw.replace(/,/g,'')):raw.replace(',','.');const p=Number.parseFloat(n);return Number.isFinite(p)?p:0}
function normalizeQuantity(v){const n=Number.parseInt(v,10);return Number.isFinite(n)?Math.min(99,Math.max(1,n)):1}
function normalizeCart(cart){return Array.isArray(cart)?cart.filter(i=>Number.isInteger(i?.productId)&&i.productId>0&&(i.variantId==null||Number.isInteger(i.variantId))&&Number.isInteger(i.quantity)&&i.quantity>0&&i.quantity<=99).map(i=>({...i,variantId:i.variantId||null,priceCents:Number.isInteger(i.priceCents)?i.priceCents:0})):[]}
function getCart(){try{return normalizeCart(JSON.parse(localStorage.getItem(CART_KEY)||'[]'))}catch{return []}}
function saveCart(c){localStorage.setItem(CART_KEY,JSON.stringify(normalizeCart(c)))}
function escapeHtml(v=''){return String(v).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function updateCopyrightYear(){const y=String(new Date().getFullYear());document.querySelectorAll('[data-current-year]').forEach(e=>e.textContent=y)}
function updateBagCount(){const count=getCart().reduce((n,i)=>n+i.quantity,0);document.querySelectorAll('[data-cart-count]').forEach(e=>e.textContent=count)}
function bindImageFallbacks(){document.querySelectorAll('img').forEach(img=>{if(img.dataset.fallbackBound)return;img.dataset.fallbackBound='1';img.addEventListener('error',()=>{img.classList.add('image-load-error');const art=img.closest('.product-art,.orbit-art');if(art&&img.dataset.managedImage==='true'){art.classList.remove('has-image');if(art.classList.contains('orbit-art'))art.style.backgroundImage='none';img.hidden=true;img.removeAttribute('src');img.classList.remove('image-ready');}},{once:true})})}
function navLabel(k){return getContent().siteText?.nav?.[k]||defaultContent.siteText.nav[k]}
function renderHeaderText(){const c=getContent();const t=c.siteText||defaultContent.siteText;document.querySelectorAll('[data-nav-label]').forEach(el=>{const key=el.dataset.navLabel;el.textContent=t.nav?.[key]||defaultContent.siteText.nav[key]||key});const shopCount=String((c.shop||[]).length).padStart(2,'0');document.querySelectorAll('[data-shop-count]').forEach(el=>el.textContent=shopCount);const bag=document.querySelector('.bag-link');if(bag){const isCart=location.pathname.toLowerCase().endsWith('cart.html');const label=bag.querySelector('[data-nav-label]');if(label)label.textContent=isCart?t.nav.cart:t.nav.bag;bag.setAttribute('aria-label',isCart?t.nav.cart:t.nav.bag)}}
function renderPublicContent(){const c=getContent(), text=c.siteText||defaultContent.siteText;
  renderHeaderText();
  document.querySelectorAll('.skip-link').forEach(e=>e.textContent=text.skipToContent);
  document.querySelectorAll('.market-ticker').forEach(e=>e.setAttribute('aria-label',text.liveUpdates));
  const mainPage = document.querySelector('main');
  const pageKey = mainPage?.classList.contains('shop-page')?'shop':mainPage?.classList.contains('live-page')?'live':mainPage?.classList.contains('contact-page')?'contact':mainPage?.classList.contains('cart-page')?'cart':null;
  if(pageKey){const p=c.pages[pageKey]||{};const heading=mainPage.querySelector('.page-heading');if(heading){const e=heading.querySelector('.eyebrow'),h=heading.querySelector('h1'),n=heading.querySelector('.heading-note');if(e){let ey=p.eyebrow||'';if(pageKey==='contact'&&c.contact.email)ey=ey.replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/,c.contact.email);e.textContent=ey;}if(h)h.innerHTML=`${escapeHtml(p.titleLineOne||'')}<br><em>${escapeHtml(p.titleLineTwo||'')}</em>`;if(n)n.textContent=p.note||'';}}
  const h=c.home||{};document.querySelectorAll('[data-home-eyebrow]').forEach(e=>e.textContent=h.eyebrow);document.querySelectorAll('[data-home-title-one]').forEach(e=>e.textContent=h.titleLineOne);document.querySelectorAll('[data-home-title-two]').forEach(e=>e.textContent=h.titleLineTwo);document.querySelectorAll('[data-home-intro]').forEach(e=>e.textContent=h.intro);document.querySelectorAll('[data-home-cta]').forEach(e=>{e.childNodes[0].textContent=h.cta+' '});document.querySelectorAll('.orbit-art').forEach(art=>{const u=safeImageUrl(h.heroImage);const img=art.querySelector('[data-home-hero-image]');const reset=()=>{art.classList.remove('has-image');art.style.backgroundImage='none';if(img){img.hidden=true;img.removeAttribute('src');img.classList.remove('image-ready');}};if(!img){art.classList.remove('has-image');art.style.backgroundImage='none';return;}reset();if(!u){return;}img.alt=h.heroAlt||'';img.onload=()=>{art.classList.add('has-image');img.hidden=false;img.classList.add('image-ready');};img.onerror=()=>{reset();};img.src=u;});document.querySelectorAll('.label-top').forEach(e=>e.textContent=h.orbitLabelTop||'');document.querySelectorAll('.label-bottom').forEach(e=>e.textContent=h.orbitLabelBottom||'');document.querySelectorAll('.hero-index').forEach(e=>{e.innerHTML=escapeHtml(h.heroIndex||'01 / 04').replace(' / ',' <span>/</span> ')});document.querySelectorAll('.home-hero .section-number,.home-intro .section-number').forEach(e=>e.textContent=h.sectionNumber||'[ 001 ]');document.querySelectorAll('.signal-strip > p:first-child').forEach(e=>e.textContent=h.signalStripLabel||text.home.currentlyTransmitting);document.querySelectorAll('[data-home-signal]').forEach(e=>e.textContent=h.signalText);document.querySelectorAll('[data-home-intro-eyebrow]').forEach(e=>e.textContent=h.introEyebrow);document.querySelectorAll('[data-home-intro-title-one]').forEach(e=>e.textContent=h.introTitleLineOne);document.querySelectorAll('[data-home-intro-title-two]').forEach(e=>e.textContent=h.introTitleLineTwo);document.querySelectorAll('[data-home-intro-description]').forEach(e=>e.textContent=h.introDescription);
  document.querySelectorAll('[data-ticker]').forEach(t=>{t.innerHTML=`<span>${escapeHtml(c.ticker.text)}</span><b>✳</b><span>${escapeHtml(c.ticker.text)}</span><b>✳</b>`;t.style.setProperty('--ticker-speed',`${Math.max(8,Number(c.ticker.speed)||28)}s`);t.style.setProperty('--ticker-font-size',`${Math.max(8,Number(c.ticker.fontSize)||11)}px`)});
  document.querySelectorAll('[data-contact-description], .contact-details .body-copy').forEach(e=>e.textContent=c.contact.description);document.querySelectorAll('[data-contact-email]').forEach(e=>{e.textContent=`${c.contact.email} ↗`;e.href=`mailto:${c.contact.email}`});[['instagram','Instagram'],['youtube','YouTube']].forEach(([key,label])=>document.querySelectorAll(`[data-contact-${key}]`).forEach(e=>{const u=safeExternalUrl(c.contact?.[`${key}Url`]);if(u){e.textContent=`${c.contact?.[key]||label} ↗`;e.href=u;e.target='_blank';e.rel='noopener noreferrer';e.hidden=false}else e.hidden=true}));document.querySelectorAll('[data-contact-section-number]').forEach(e=>e.textContent=c.contact.sectionNumber||'[ 003 ]');document.querySelectorAll('.contact-page .section-number').forEach(e=>e.textContent=c.contact.sectionNumber||'[ 003 ]');document.querySelectorAll('[data-contact-service-title-one]').forEach(e=>e.textContent=c.contact.serviceTitleOne||'We create');document.querySelectorAll('[data-contact-service-title-two]').forEach(e=>e.textContent=c.contact.serviceTitleTwo||'signals.');document.querySelectorAll('[data-contact-form-intro]').forEach(e=>e.textContent=c.contact.formIntro||'');document.querySelectorAll('[data-home-group-eyebrow]').forEach(e=>e.textContent=h.groupEyebrow);document.querySelectorAll('[data-home-group-title-one]').forEach(e=>e.textContent=h.groupTitleLineOne);document.querySelectorAll('[data-home-group-title-two]').forEach(e=>e.textContent=h.groupTitleLineTwo);document.querySelectorAll('[data-home-group-description]').forEach(e=>e.textContent=h.groupDescription);document.querySelectorAll('[data-home-group-secondary]').forEach(e=>e.textContent=h.groupSecondary);document.querySelectorAll('[data-home-group-cta]').forEach(e=>e.childNodes[0].textContent=(h.groupCta||'Send a signal')+' ');
  document.querySelectorAll('[data-contact-label]').forEach(e=>{const k=e.dataset.contactLabel;const node=[...e.childNodes].find(n=>n.nodeType===3);if(node)node.textContent=(text.contact[k]||node.textContent)+' '});document.querySelectorAll('[data-contact-submit]').forEach(e=>{e.childNodes[0].textContent=(text.contact.submit||'Transmit')+' '});
  const events=document.querySelector('[data-live-events]')||document.querySelector('.live-page .events');if(events){events.innerHTML=(c.live||[]).map(ev=>{const past=Boolean(ev.past)||(ev.isoDate&&new Date(`${ev.isoDate}T23:59:59`)<new Date()),u=safeExternalUrl(ev.ticketUrl),href=u?escapeHtml(u):'#',target=u?' target="_blank" rel="noopener noreferrer"':'',disabled=u?'':' aria-disabled="true" data-no-ticket="true"';return `<a class="event${past?' event-past':''}" href="${href}"${target}${disabled}><time datetime="${escapeHtml(ev.isoDate||'')}">${escapeHtml(ev.date||'')}</time><span>${escapeHtml(ev.location||'')}<small>${escapeHtml(ev.venue||'')}</small></span><span>${escapeHtml(ev.signal||'')}<small>${escapeHtml(ev.detail||'')}</small></span><strong>${escapeHtml(ev.action||text.live.noTicket||'Tickets')} ↗</strong></a>`}).join('');}
  document.querySelectorAll('.event-head span').forEach((e,i)=>{e.textContent=[text.live.date,text.live.location,text.live.signal,''][i]??e.textContent});
  const shopCount=document.querySelectorAll('[data-shop-count]');shopCount.forEach(e=>e.textContent=String((c.shop||[]).length).padStart(2,'0'));const liveBg=safeImageUrl(c.visuals?.liveBackgroundImage);if(liveBg)document.documentElement.style.setProperty('--live-background-image',`url(${JSON.stringify(liveBg)})`);
  document.querySelectorAll('[data-footer-tagline]').forEach(e=>e.textContent=text.footer.tagline);const path=(location.pathname||'').toLowerCase();let footerKey=path.endsWith('shop.html')?'shopCta':path.endsWith('live.html')?'liveCta':path.endsWith('contact.html')?'contactCta':path.endsWith('cart.html')?'cartCta':'homeCta';document.querySelectorAll('.site-footer > a').forEach(e=>e.childNodes[0].textContent=(text.footer[footerKey]||e.textContent.replace(' ↗',''))+' ');
}

function renderPageImages(){
  const content=getContent(), images=content.images||{};
  document.querySelectorAll('.orbit-art').forEach(media=>{const motion=['none','zoom','drift','reveal'].includes(images.home?.primary?.motion)?images.home.primary.motion:'none';media.className=media.className.replace(/\bmotion-\w+\b/g,'').trim();if(motion!=='none')media.classList.add(`motion-${motion}`);});
  document.querySelectorAll('[data-page-image]').forEach(img=>{
    const [page,slot]=img.dataset.pageImage.split('-'), item=page==='home'&&slot==='primary'?{image:content.home?.heroImage,alt:content.home?.heroAlt,motion:images.home?.primary?.motion}:images[page]?.[slot]||{};
    const media=img.closest('[data-page-media]'), url=safeImageUrl(item.image), motion=['none','zoom','drift','reveal'].includes(item.motion)?item.motion:'none';
    if(!url){media.hidden=true;return;} media.hidden=false;media.className=media.className.replace(/\bmotion-\w+\b|\bis-pending\b|\bis-visible\b/g,'').trim();if(motion!=='none')media.classList.add(`motion-${motion}`);img.alt=item.alt||'';img.src=url;
    if(motion==='reveal'){media.classList.add('is-pending');const reveal=()=>{media.classList.remove('is-pending');media.classList.add('is-visible')};if('IntersectionObserver'in window){new IntersectionObserver((entries,observer)=>{if(entries[0].isIntersecting){reveal();observer.disconnect()}},{threshold:.12}).observe(media)}else reveal();}
  });
}

function renderProducts(){
  const root=document.querySelector('[data-shop-products]');if(!root)return;
  if(!siteConfig.commerceEnabled){root.innerHTML='<p class="cart-empty" role="status">COMING SOON — the next KOSMIK release is preparing its orbit.</p>';return;}
  root.innerHTML=getContent().shop.map((p,i)=>{
    const variants=p.variants||[],stock=p.hasVariants?variants.reduce((n,v)=>n+v.availableStock,0):p.availableStock;
    return `<article class="product product-${String.fromCharCode(97+i)}"><div class="product-art art-${['moon','signal','coral','poster'][i%4]}${p.image?' has-image':''}">${p.image?`<img loading="lazy" decoding="async" data-managed-image="true" src="${escapeHtml(safeImageUrl(p.image))}" alt="${escapeHtml(p.alt||p.name)}">`:''}<span>${String(i+1).padStart(2,'0')}</span></div><div class="product-meta"><h2>${escapeHtml(p.name)}</h2><p>${escapeHtml(p.meta)}</p><p class="product-description">${escapeHtml(p.description)}</p><strong>${money(p.priceCents)}</strong>${p.hasVariants?`<label>Variant<select data-variant-for="${p.id}">${variants.map(v=>`<option value="${v.id}" ${v.availableStock<1?'disabled':''}>${escapeHtml([v.size,v.color].filter(Boolean).join(' / ')||v.sku)}${v.availableStock<1?' — Sold out':''}</option>`).join('')}</select></label>`:''}<button type="button" class="button button-light" data-product-id="${p.id}" ${!backendReady||stock<1?'disabled':''}>${stock<1?'Sold out':escapeHtml(getContent().siteText.shop.addToCart)}</button><p data-product-status="${p.id}" role="status"></p></div></article>`;
  }).join('');
  root.querySelectorAll('[data-product-id]').forEach(button=>button.addEventListener('click',()=>{
    const p=getContent().shop.find(p=>p.id===Number(button.dataset.productId));
    const v=p.hasVariants?p.variants.find(v=>v.id===Number(root.querySelector(`[data-variant-for="${p.id}"]`).value)):null;
    const limit=v?v.availableStock:p.availableStock,cart=getCart(),existing=cart.find(i=>i.productId===p.id&&i.variantId===(v?.id||null));
    const status=root.querySelector(`[data-product-status="${p.id}"]`);
    if((existing?.quantity||0)>=limit){status.textContent='No more stock available.';return;}
    if(existing)existing.quantity++;else cart.push({productId:p.id,variantId:v?.id||null,name:p.name,variant:v?[v.size,v.color].filter(Boolean).join(' / '):'',priceCents:p.priceCents,image:p.image,quantity:1});
    saveCart(cart);updateBagCount();status.textContent='Added to cart.';
  }));
}
function money(cents){return new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(cents/100)}
function normalizedItems(){return getCart().map(({productId,variantId,quantity})=>({productId,variantId,quantity}))}
let cartDraft={},checkoutBusy=false;
function readDraft(){const form=document.querySelector('[data-order-form]');if(form)cartDraft=Object.fromEntries(new FormData(form));return cartDraft}
function renderCartPage(){
  const root=document.querySelector('[data-cart-content]');if(!root)return;
  const cart=getCart(),t=getContent().siteText.cart;
  if(!siteConfig.commerceEnabled){root.innerHTML='<p class="cart-empty" role="status">COMING SOON — checkout is currently unavailable. Your saved cart has not been changed.</p>';return;}
  if(!cart.length){root.innerHTML=`<p>${escapeHtml(t.empty)}</p>`;return;}
  const fields=[['name',t.yourName,'name'],['email',t.yourEmail,'email'],['phone',t.phone,'tel'],['address',t.address,'street-address'],['city',t.city,'address-level2'],['postcode',t.postcode,'postal-code'],['country','Country code (IT, DE, FR…)','country']];
  root.innerHTML=`<div class="cart-items">${cart.map((i,n)=>`<article class="cart-item">${i.image?`<img src="${escapeHtml(safeImageUrl(i.image))}" alt="${escapeHtml(i.name)}">`:''}<div><h2>${escapeHtml(i.name)}</h2><p>${escapeHtml(i.variant||'')} · ${money(i.priceCents)} × ${i.quantity}</p></div><div class="cart-controls"><button type="button" data-cart-action="decrease" data-index="${n}" aria-label="Decrease quantity">−</button><button type="button" data-cart-action="increase" data-index="${n}" aria-label="Increase quantity">+</button><button type="button" data-cart-action="remove" data-index="${n}">${escapeHtml(t.remove)}</button></div></article>`).join('')}</div><p data-order-total>Items: ${money(cart.reduce((n,i)=>n+i.priceCents*i.quantity,0))}. Final prices and shipping are checked before payment.</p><form data-order-form class="order-form">${fields.map(([key,label,autocomplete])=>`<label>${escapeHtml(label)}<input name="${key}" type="${key==='email'?'email':key==='phone'?'tel':'text'}" autocomplete="${autocomplete}" maxlength="${key==='country'?2:250}" value="${escapeHtml(cartDraft[key]||'')}" ${key==='phone'?'':'required'}></label>`).join('')}<label>Delivery<select name="shippingMethod"><option value="shipping">Shipping</option>${siteConfig.shipping?.pickupEnabled?`<option value="pickup" ${siteConfig.shipping.pickupAddress&&siteConfig.shipping.pickupInstructions?'':'disabled'}>Local pickup${siteConfig.shipping.pickupAddress?'':' — not configured'}</option>`:''}</select></label><p data-pickup-instructions></p><button type="button" class="button button-light" data-check-total ${backendReady?'':'disabled'}>Check total</button><button type="submit" class="button button-light" ${backendReady&&siteConfig.paymentsEnabled?'':'disabled'}>Continue to payment</button></form><p class="cart-status" data-cart-status role="status">${backendReady?(siteConfig.paymentsEnabled?'':'Checkout is not configured yet. Your cart is saved.'):'Server unavailable. Your cart is saved.'}</p>`;
  const form=root.querySelector('form');form.elements.shippingMethod.value=cartDraft.shippingMethod||'shipping';
  function deliveryChanged(){const pickup=form.elements.shippingMethod.value==='pickup';for(const key of ['address','city','postcode','country'])form.elements[key].required=!pickup;root.querySelector('[data-pickup-instructions]').textContent=pickup?[siteConfig.shipping.pickupAddress,siteConfig.shipping.pickupInstructions].join(' — '):'';}
  deliveryChanged();form.elements.shippingMethod.addEventListener('change',deliveryChanged);
  root.querySelectorAll('[data-cart-action]').forEach(b=>b.addEventListener('click',()=>{if(checkoutBusy)return;readDraft();const items=getCart(),idx=Number(b.dataset.index);if(b.dataset.cartAction==='increase')items[idx].quantity=Math.min(99,items[idx].quantity+1);if(b.dataset.cartAction==='decrease')items[idx].quantity--;if(b.dataset.cartAction==='remove'||items[idx].quantity<1)items.splice(idx,1);saveCart(items);updateBagCount();renderCartPage()}));
  function payload(){const d=readDraft();return {email:d.email,shippingMethod:d.shippingMethod,customer:Object.fromEntries(fields.filter(f=>f[0]!=='email').map(([key])=>[key,d[key]||''])),items:normalizedItems()}}
  root.querySelector('[data-check-total]').addEventListener('click',async()=>{if(!form.reportValidity())return;try{const q=await publicApi('/checkout/quote',payload());root.querySelector('[data-order-total]').textContent=`Items ${money(q.subtotalCents)} + shipping ${money(q.shippingCents)} = ${money(q.totalCents)}`;root.querySelector('[data-cart-status]').textContent='Total verified.'}catch(e){root.querySelector('[data-cart-status]').textContent=e.message}});
  form.addEventListener('submit',async e=>{
    e.preventDefault();if(checkoutBusy||!backendReady||!siteConfig.paymentsEnabled)return;
    checkoutBusy=true;const submit=form.querySelector('[type=submit]');submit.disabled=true;
    const status=root.querySelector('[data-cart-status]');status.textContent='Checking prices, shipping and availability…';
    try{
      const data=payload(),fingerprint=JSON.stringify(data);let attempt;
      try{attempt=JSON.parse(sessionStorage.getItem('kosmik-checkout')||'null')}catch{}
      const retry=Boolean(attempt&&attempt.fingerprint===fingerprint);
      if(!retry)attempt={fingerprint,key:crypto.randomUUID()};
      sessionStorage.setItem('kosmik-checkout',JSON.stringify(attempt));
      if(!retry){const q=await publicApi('/checkout/quote',data);root.querySelector('[data-order-total]').textContent=`Total ${money(q.totalCents)} (shipping ${money(q.shippingCents)})`;}
      const result=await publicApi('/checkout',{...data,requestKey:attempt.key});
      sessionStorage.setItem('kosmik-order:'+result.orderId,JSON.stringify({token:result.statusToken,cart:JSON.stringify(getCart())}));
      const url=new URL(result.checkoutUrl);if(url.protocol!=='https:'||url.hostname!=='checkout.stripe.com')throw Error('Invalid payment URL');
      location.assign(url.href);
    }catch(e){status.textContent=e.message;checkoutBusy=false;submit.disabled=false;}
  });
}
async function publicApi(path,data){
  const response=await fetch(API_BASE+path,{method:data?'POST':'GET',headers:{Accept:'application/json',...(data?{'Content-Type':'application/json'}:{})},body:data?JSON.stringify(data):undefined,signal:AbortSignal.timeout(25000)});
  let result;try{result=await response.json()}catch{throw Error('Server unavailable. Your cart is saved.')}
  if(!response.ok)throw Error(result.error||'Request failed. Please retry.');return result;
}
async function renderPaymentStatus(){
  const params=new URLSearchParams(location.search),oid=params.get('order'),payment=params.get('payment'),root=document.querySelector('[data-cart-content]');if(!root||!payment)return;
  const note=document.createElement('p');note.setAttribute('role','status');root.before(note);
  if(payment==='cancelled'){note.textContent='Payment cancelled. Your cart is saved.';return;}
  let saved;try{saved=JSON.parse(sessionStorage.getItem('kosmik-order:'+oid)||'null')}catch{}
  if(!saved){note.textContent='Order verification requires the browser used for checkout. Contact us with your order reference.';return;}
  for(let n=0;n<12;n++){
    try{
      const r=await fetch(`${API_BASE}/orders/status?id=${encodeURIComponent(oid)}`,{headers:{'X-Order-Token':saved.token},cache:'no-store',signal:AbortSignal.timeout(8000)});
      if(!r.ok)throw Error();const data=await r.json();
      if(data.paymentStatus==='PAID'){
        if(JSON.stringify(getCart())===saved.cart)saveCart([]);
        sessionStorage.removeItem('kosmik-checkout');renderCartPage();updateBagCount();
        note.textContent=data.needsReview?`Payment received for ${oid}. We will contact you to resolve an order issue.`:`Payment confirmed. Order ${oid}.`;return;
      }
      if(['FAILED','REFUNDED'].includes(data.paymentStatus)){note.textContent=`Order ${oid}: ${data.paymentStatus}. Your cart is saved.`;return;}
    }catch{}
    note.textContent=`Waiting for payment confirmation for ${oid}…`;
    await new Promise(resolve=>setTimeout(resolve,2500));
  }
  note.textContent=`Confirmation is taking longer than expected. Refresh later or contact us with reference ${oid}. Your cart is saved.`;
}
function renderLinksAndLegal(){
  const footer=document.querySelector('.site-footer');if(footer){const nav=document.createElement('nav');nav.setAttribute('aria-label','Legal');nav.innerHTML=['privacy','terms','shipping','returns'].map(key=>`<a href="legal.html?page=${key}">${key[0].toUpperCase()+key.slice(1)}</a>`).join(' · ');footer.append(nav);}
  const target=document.querySelector('.contact-links');
  if(target){const nav=document.createElement('nav');nav.setAttribute('aria-label','Music and social');for(const [key,value] of Object.entries(getContent().links||{})){if(['instagram','youtube'].includes(key))continue;const url=safeExternalUrl(value);if(!url)continue;const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=key;nav.append(a,document.createTextNode(' '));}if(nav.childNodes.length)target.append(nav);}
  const legal=document.querySelector('[data-legal-content]');if(legal){let key=new URLSearchParams(location.search).get('page')||'privacy';if(!['privacy','terms','shipping','returns'].includes(key))key='privacy';document.querySelector('[data-legal-title]').textContent=key[0].toUpperCase()+key.slice(1);legal.textContent=getContent().legal?.[key]||'This information is being prepared. Contact gus@kosmikcircles.com before placing an order.';}
}
function initMatrix(){
  if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)return;
  const canvas=document.createElement('canvas');canvas.id='matrix-background';canvas.setAttribute('aria-hidden','true');document.body.prepend(canvas);
  const context=canvas.getContext('2d');let drops=[],raf=0,last=0;
  function resize(){canvas.width=innerWidth;canvas.height=innerHeight;drops=Array.from({length:Math.min(120,Math.ceil(innerWidth/20))},()=>Math.random()*-40)}
  function draw(ts){if(document.hidden){raf=0;return;}if(ts-last>33){last=ts;context.fillStyle='rgba(9,9,9,.12)';context.fillRect(0,0,canvas.width,canvas.height);context.font='14px monospace';drops.forEach((y,i)=>{context.fillStyle=i%7===0?'rgba(255,90,31,.72)':'rgba(93,255,142,.42)';context.fillText('KOSMIKCIRCLES01'[Math.floor(Math.random()*14)],i*20,y*20);drops[i]=y*20>canvas.height&&Math.random()>.975?0:y+Math.max(.05,Number(getContent().matrix?.speed)||.45)});}raf=requestAnimationFrame(draw)}
  resize();addEventListener('resize',resize,{passive:true});document.addEventListener('visibilitychange',()=>{cancelAnimationFrame(raf);raf=0;if(!document.hidden)raf=requestAnimationFrame(draw)});if(!document.hidden)raf=requestAnimationFrame(draw);
}
document.addEventListener('DOMContentLoaded',async()=>{
  updateCopyrightYear();await fetchContent();
  try {if(backendReady){renderPublicContent();renderPageImages();renderProducts();renderLinksAndLegal();}
  else {const warning=document.createElement('p');warning.setAttribute('role','alert');warning.textContent='Server unavailable. Shop and checkout are temporarily disabled; your cart is saved.';document.querySelector('main')?.prepend(warning);document.querySelectorAll('[data-add-to-cart]').forEach(b=>b.disabled=true);}}
  finally {document.documentElement.classList.remove('content-loading');}
  renderCartPage();updateBagCount();bindImageFallbacks();initMatrix();
  document.querySelectorAll('[data-no-ticket]').forEach(a=>a.addEventListener('click',e=>e.preventDefault()));
  const form=document.querySelector('.contact-form');if(form)form.addEventListener('submit',async e=>{e.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;let status=form.querySelector('[role=status]');if(!status){status=document.createElement('p');status.setAttribute('role','status');form.append(status);}try{const result=await publicApi('/messages',Object.fromEntries(new FormData(form)));form.reset();status.textContent=result.delivery==='saved'?'Message saved. Email delivery is not configured; the team will read it in Admin.':'Message received.';}catch(e){status.textContent=e.message;}finally{button.disabled=false;}});
  renderPaymentStatus();
});

