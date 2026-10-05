'use strict';
const menu=document.querySelector('#mobile-menu');
const toggle=document.querySelector('.menu-toggle');
if(menu&&toggle){
 toggle.addEventListener('click',()=>{menu.showModal();toggle.setAttribute('aria-expanded','true');document.body.classList.add('menu-open');});
 document.querySelector('.menu-close').addEventListener('click',()=>menu.close());
 menu.addEventListener('close',()=>{toggle.setAttribute('aria-expanded','false');document.body.classList.remove('menu-open');toggle.focus();});
 menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>menu.close()));
}
const form=document.querySelector('#contact-form');
if(form){
 const ENDPOINT='https://n8n.srv1450872.hstgr.cloud/webhook/kontakt';
 const boxes=[...form.querySelectorAll('input[name="anliegen"]')];
 const status=form.querySelector('#form-status');
 const button=form.querySelector('button[type="submit"]');
 const params=new URLSearchParams(location.search);
 const requested=params.get('anliegen');
 const preselected=boxes.find(b=>b.value===requested);
 if(preselected)preselected.checked=true;
 const say=(state,nodes)=>{status.replaceChildren();status.dataset.state=state;status.hidden=false;status.append(...nodes);status.focus();};
 const p=t=>{const e=document.createElement('p');e.textContent=t;return e;};
 const draftLink=labels=>{
  const data=new FormData(form);
  const subject='Anfrage: '+(labels.length?labels.join(', '):'Sonstiges');
  const body=`Guten Tag AAA HostPro,\n\n${data.get('message')}\n\nMein Anliegen: ${labels.length?labels.join(', '):'Sonstiges'}\nName: ${data.get('name')}\nE-Mail: ${data.get('email')}\nTelefon: ${data.get('phone')||'Nicht angegeben'}`;
  const a=document.createElement('a');
  a.href=`mailto:info@aaa-hostpro.de?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  a.textContent='E-Mail-Entwurf öffnen';a.className='text-link';
  return a;
 };
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!form.reportValidity())return;
  const data=new FormData(form);
  const checked=boxes.filter(b=>b.checked);
  const labels=checked.map(b=>b.dataset.label);
  const payload={
   formular:'Kontaktformular',
   anliegen:checked.map(b=>b.value),
   anliegen_labels:labels,
   name:data.get('name'),
   email:data.get('email'),
   telefon:data.get('phone')||'',
   nachricht:data.get('message'),
   seite:location.href,
   referrer:document.referrer||'',
   utm_source:params.get('utm_source')||'',
   utm_medium:params.get('utm_medium')||'',
   utm_campaign:params.get('utm_campaign')||'',
   zeitpunkt:new Date().toISOString(),
   hp:form.querySelector('#website').value
  };
  button.setAttribute('aria-busy','true');
  const ctrl=new AbortController();
  const timer=setTimeout(()=>ctrl.abort(),12000);
  try{
   const response=await fetch(ENDPOINT,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:ctrl.signal});
   if(!response.ok)throw new Error(response.status);
   form.reset();
   boxes.forEach(b=>{b.checked=false});
   if(preselected)preselected.checked=true;
   const icon=document.createElementNS('http://www.w3.org/2000/svg','svg');
   icon.setAttribute('viewBox','0 0 24 24');icon.setAttribute('class','sent-icon');icon.setAttribute('aria-hidden','true');
   const path=document.createElementNS('http://www.w3.org/2000/svg','path');
   path.setAttribute('d','M4 12.5 9.5 18 20 6.5');path.setAttribute('fill','none');
   path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','2.4');
   path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');
   icon.append(path);
   const head=document.createElement('p');head.className='sent-head';head.textContent='Ihre Anfrage ist angekommen.';
   form.classList.add('sent');
   say('success',[icon,head,
    p('Vielen Dank, '+(payload.name.split(' ')[0]||'vielen Dank')+'. Wir haben Ihre Nachricht erhalten und melden uns in der Regel innerhalb eines Werktags bei Ihnen – telefonisch oder per E-Mail.'),
    p('Dringend? Sie erreichen uns direkt unter +49 151 56289700.')]);
   form.scrollIntoView({behavior:'smooth',block:'center'});
  }catch(error){
   say('error',[
    p('Die Anfrage konnte gerade nicht übermittelt werden. Bitte senden Sie uns Ihre Nachricht als E-Mail – Ihre Angaben sind bereits vorbereitet.'),
    draftLink(labels),
    p('Alternativ erreichen Sie uns direkt unter info@aaa-hostpro.de oder +49 151 56289700. Ihre Angaben bleiben oben im Formular erhalten.')
   ]);
  }finally{
   clearTimeout(timer);
   button.removeAttribute('aria-busy');
  }
 });
}
