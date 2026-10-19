'use strict';
const menu=document.querySelector('#mobile-menu');
const toggle=document.querySelector('.menu-toggle');
if(menu&&toggle){
 toggle.addEventListener('click',()=>{menu.showModal();toggle.setAttribute('aria-expanded','true');document.body.classList.add('menu-open');});
 document.querySelector('.menu-close').addEventListener('click',()=>menu.close());
 menu.addEventListener('close',()=>{toggle.setAttribute('aria-expanded','false');document.body.classList.remove('menu-open');toggle.focus();});
 menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>menu.close()));
}
/* ---- Ereignisse an GA4 --------------------------------------------------
Nur bei erteilter Einwilligung. gtag ist zwar immer definiert, den
Schnipsel im Kopf legt es an, aber ohne Zustimmung ist das Tag gar
nicht geladen. Ein Push landete dann im dataLayer und wuerde beim
spaeteren Zustimmen nachtraeglich mitgesendet. Die
Datenschutzerklaerung sagt zu, dass vorher nichts uebertragen wird,
also fragen wir den gespeicherten Stand ab.

Der Lesezugriff steht in einem try: Im privaten Fenster und bei
gesperrten Websitedaten wirft bereits das Lesen. Ein fehlgeschlagenes
Ereignis darf das Absenden des Formulars nicht aufhalten. */
function ereignis(name, daten){
 try { if (localStorage.getItem('aaa-consent') !== 'granted') return; }
 catch (e) { return; }
 try { if (typeof gtag === 'function') gtag('event', name, daten || {}); }
 catch (e) { /* Messung ist nie wichtiger als die Anfrage. */ }
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
   // generate_lead ist das von GA4 vorgesehene Ereignis fuer genau
   // diesen Fall. Es laesst sich mit einem Klick zum Schluesselereignis
   // erklaeren und spaeter nach Google Ads uebernehmen.
   ereignis('generate_lead', {
    formular_ort: location.pathname,
    anliegen: checked.map(b=>b.value).join(',') || 'sonstiges',
    utm_source: payload.utm_source,
    utm_medium: payload.utm_medium,
    utm_campaign: payload.utm_campaign
   });
   say('success',[icon,head,
    p('Vielen Dank, '+(payload.name.split(' ')[0]||'vielen Dank')+'. Wir haben Ihre Nachricht erhalten und melden uns in der Regel innerhalb eines Werktags bei Ihnen, telefonisch oder per E-Mail.'),
    p('Dringend? Sie erreichen uns direkt unter +49 151 56289700.')]);
   form.scrollIntoView({behavior:'smooth',block:'center'});
  }catch(error){
   // Ohne das bleibt unsichtbar, wenn n8n Anfragen verliert: Der
   // Besucher sieht den Hinweis, wir sehen gar nichts.
   ereignis('formular_fehler', { formular_ort: location.pathname });
   say('error',[
    p('Die Anfrage konnte gerade nicht übermittelt werden. Bitte senden Sie uns Ihre Nachricht als E-Mail. Ihre Angaben sind bereits vorbereitet.'),
    draftLink(labels),
    p('Alternativ erreichen Sie uns direkt unter info@aaa-hostpro.de oder +49 151 56289700. Ihre Angaben bleiben oben im Formular erhalten.')
   ]);
  }finally{
   clearTimeout(timer);
   button.removeAttribute('aria-busy');
  }
 });
}

/* Sprachmenü: <details> kann aufklappen, aber nicht von selbst wieder zu.
   Escape und Klick daneben ergänzt das Skript. */
const sprachmenue = document.querySelector('details.lang');
if (sprachmenue) {
 document.addEventListener('click', e => {
  if (sprachmenue.open && !sprachmenue.contains(e.target)) sprachmenue.open = false;
 });
 document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && sprachmenue.open) {
   sprachmenue.open = false;
   sprachmenue.querySelector('summary').focus();
  }
 });
}

/* Abschnitte blenden beim Scrollen sanft ein.
   Die Klasse .bewegung setzt erst das Skript – ohne JavaScript ist alles
   von Anfang an sichtbar. Inhalt darf nie von einem Skript abhängen.
   Der Hero bleibt ausgenommen: Seine Überschrift ist meist das
   LCP-Element, ein Einblenden darauf verschlechtert die Messung. */
const ruhe = window.matchMedia('(prefers-reduced-motion: reduce)');
if (!ruhe.matches && 'IntersectionObserver' in window) {
 document.documentElement.classList.add('bewegung');
 const beobachter = new IntersectionObserver((eintraege, o) => {
  for (const e of eintraege) {
   if (!e.isIntersecting) continue;
   e.target.classList.add('sichtbar');
   o.unobserve(e.target);
  }
 }, { rootMargin: '0px 0px -8% 0px', threshold: 0.04 });
 const abschnitte = document.querySelectorAll('main > section:not(.hero)');
 abschnitte.forEach(a => beobachter.observe(a));
 /* Was beim Laden schon im Bild steht, soll nicht erst einblenden,
    wenn der Besucher scrollt. */
 requestAnimationFrame(() => {
  abschnitte.forEach(a => {
   if (a.getBoundingClientRect().top < window.innerHeight) a.classList.add('sichtbar');
  });
 });
}

/* ---- Datenschutzeinstellungen ------------------------------------------
Der gtag-Schnipsel im Kopf setzt alle Einwilligungsarten auf "denied".
Erst eine Zustimmung hebt analytics_storage auf "granted". Werbung
bleibt dauerhaft gesperrt: Wir schalten keine, also gibt es dafuer
auch nichts zu erlauben - ein Schalter ohne Wirkung waere eine Luege
im Interface.

Geoeffnet wird mit showModal(). Damit uebernimmt der Browser die
Fokusfalle, macht den Hintergrund inert und liefert das
cancel-Ereignis. Nachgebaut waere all das schlechter.

Die Entscheidung liegt im localStorage und verlaesst den Browser
nicht. Jeder Zugriff steht in einem try: Im privaten Fenster und bei
gesperrten Websitedaten wirft bereits das Lesen, und ein
Einwilligungsfenster, das daran scheitert, sperrt die Seite aus. */
(function () {
 var SCHLUESSEL = 'aaa-consent';
 var fenster = document.getElementById('consent');
 if (!fenster) return;
 var haken = document.getElementById('consent-statistik');

 function lesen() {
  try { return localStorage.getItem(SCHLUESSEL); } catch (e) { return null; }
 }

 var geladen = false;

 // Einfacher Consent Mode: Das Google-Tag wird erst nach einer
 // Zustimmung ueberhaupt angefordert. Im erweiterten Modus laedt es
 // sofort und sendet auch ohne Einwilligung cookielose Signale -
 // die tragen Zeitstempel, Browserangaben, Verweisquelle und die
 // IP-Adresse. Die Datenschutzerklaerung sagt zu, dass vor der
 // Zustimmung nichts uebertragen wird; das ist nur so zu halten.
 function tagLaden() {
  if (geladen) return;
  geladen = true;
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=G-72D2GSX9RW';
  document.head.appendChild(s);
 }

 function anwenden(wert) {
  if (typeof gtag === 'function') gtag('consent', 'update', { analytics_storage: wert });
  if (wert === 'granted') tagLaden();
 }

 function oeffnen() {
  // Den Schalter auf den gespeicherten Stand setzen, damit das
  // Fenster beim Wiederaufruf zeigt, was gerade gilt.
  if (haken) haken.checked = lesen() === 'granted';
  if (!fenster.open) fenster.showModal();
 }

 function entscheiden(wert) {
  if (wert === 'auswahl') wert = (haken && haken.checked) ? 'granted' : 'denied';
  anwenden(wert);
  try { localStorage.setItem(SCHLUESSEL, wert); } catch (e) {}
  if (fenster.open) fenster.close();
 }

 var gespeichert = lesen();
 if (gespeichert === 'granted') {
  anwenden('granted');
 } else if (gespeichert !== 'denied') {
  // Weder zugestimmt noch abgelehnt: fragen. Eine Ablehnung wird
  // nicht erneut vorgelegt - das waere die Frage so lange zu
  // wiederholen, bis die gewuenschte Antwort kommt.
  oeffnen();
 }

 fenster.addEventListener('click', function (e) {
  var knopf = e.target.closest('[data-consent]');
  if (knopf) entscheiden(knopf.getAttribute('data-consent'));
 });

 // Escape schliesst ein dialog von sich aus. Ohne Zutun waere das ein
 // Weggehen ohne Entscheidung, und beim naechsten Aufruf stuende das
 // Fenster wieder da. Escape gilt deshalb als Ablehnung - dieselbe
 // Wirkung wie das Kreuz, auf das es beschriftet ist.
 fenster.addEventListener('cancel', function (e) {
  e.preventDefault();
  entscheiden('denied');
 });

 document.addEventListener('click', function (e) {
  var ausloeser = e.target.closest('[data-consent-oeffnen]');
  if (!ausloeser) return;
  e.preventDefault();
  oeffnen();
 });
})();


/* ---- Bewegtes Hero ------------------------------------------------------
Die Quellen stehen in data-hero-video, nicht als <source> im Markup.
Nur so laesst sich vor dem ersten Byte entscheiden, ob ueberhaupt
geladen wird - ein Browser beginnt sonst bereits mit dem Puffern,
bevor hier irgendetwas geprueft werden koennte.

Nicht geladen wird in zwei Faellen:

  * prefers-reduced-motion. Dauerbewegung im Sichtfeld loest bei
    vestibulaeren Stoerungen Schwindel und Uebelkeit aus. Das ist
    keine Vorliebe, und die Einstellung ist die ausdrueckliche Bitte
    der Besucherin, es zu lassen.

  * Save-Data. Wer dem Browser gesagt hat, er moege Daten sparen,
    meint nicht "ausser beim Hintergrundvideo".

Das Standbild bleibt in beiden Faellen stehen und ist ohnehin das
LCP-Element. Eingeblendet wird erst bei "playing", nicht schon beim
Start des Ladens: Ein halb gepuffertes Video, das ueber dem
Standbild haengt und ruckelt, ist schlechter als kein Video. */
(function () {
 var video = document.querySelector('.hero-video');
 if (!video) return;

 var ruhig = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 var sparen = navigator.connection && navigator.connection.saveData;
 if (ruhig || sparen) return;

 // Hochkant auf schmalen Fenstern, quer auf breiten. Gewaehlt wird
 // einmal beim Laden und nicht bei jeder Groessenaenderung: Ein
 // Wechsel der Quelle mitten im Lauf setzt das Video zurueck, und
 // ein Telefon dreht sich oefter, als es neu laedt.
 var schmal = window.matchMedia && window.matchMedia('(max-width: 640px)').matches;
 var liste = (schmal && video.getAttribute('data-hero-video-mobil'))
           || video.getAttribute('data-hero-video')
           || video.getAttribute('data-hero-video-mobil');
 if (!liste) return;

 liste.split(',').forEach(function (eintrag) {
  var teile = eintrag.split('|');
  var q = document.createElement('source');
  q.src = teile[0];
  q.type = teile[1];
  video.appendChild(q);
 });

 video.addEventListener('playing', function () { video.classList.add('laeuft'); });
 video.preload = 'auto';
 video.load();
 var versuch = video.play();
 // Scheitert der Start - etwa wegen einer Browsereinstellung -, bleibt
 // das Standbild stehen. Kein Grund, die Seite mit einem Fehler zu
 // behelligen.
 if (versuch && versuch.catch) versuch.catch(function () {});
})();


/* ---- Mitlaufende Kopfzeile ----------------------------------------------
Setzt "fest", sobald die Seite angescrollt ist. Auf Hero-Seiten
wechselt die Kopfzeile damit von durchsichtig auf gedeckt - sonst
staende weisse Schrift auf hellem Grund.

Der Schwellwert richtet sich nach der Hoehe der Kopfzeile, nicht nach
einer festen Zahl: Sobald mehr als diese Hoehe weggescrollt ist, liegt
unter der Kopfzeile sicher Inhalt und nicht mehr der Hero-Anfang.

Gemessen wird in requestAnimationFrame. Ein Scroll-Ereignis feuert
dutzendfach pro Sekunde; jedes Mal das Layout zu lesen und eine Klasse
zu setzen, ruckelt auf schwaecheren Geraeten sichtbar. */
(function () {
 var kopf = document.querySelector('.site-header');
 if (!kopf) return;
 var schwelle = kopf.offsetHeight || 100;
 var wartet = false;

 function pruefen() {
  wartet = false;
  kopf.classList.toggle('fest', window.scrollY > schwelle * 0.6);
 }

 window.addEventListener('scroll', function () {
  if (wartet) return;
  wartet = true;
  requestAnimationFrame(pruefen);
 }, { passive: true });

 pruefen();
})();
