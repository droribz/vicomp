/* ===== GetSitter prototype logic — standalone front-end demo =====
   Demo data only. No real users / no real background checks are performed here. */

const AV_COLORS = ['#5B4FE5','#ff6b81','#18b26b','#f5a524','#7a6cff','#e8568c','#2bb3c0','#9b59b6'];
function avatarColor(name){
  let h=0; for(const c of name) h=(h*31+c.charCodeAt(0))>>>0;
  return AV_COLORS[h%AV_COLORS.length];
}
function initials(name){
  const p=name.trim().split(/\s+/);
  return (p[0][0]+(p[1]?p[1][0]:'')).toUpperCase();
}

/* ---- demo sitters ---- */
const SITTERS = [
  {id:1,name:'נועה לוי',age:24,city:'תל אביב',dist:1.2,rating:4.9,reviews:182,rate:65,exp:6,
   tags:['גילאי 0-3','עזרה בשיעורים'],bio:'סטודנטית לחינוך, מנוסה עם תינוקות ופעוטות. אוהבת פעילות יצירתית ומשחקי תנועה.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
  {id:2,name:'יואב כהן',age:28,city:'רמת גן',dist:2.4,rating:4.8,reviews:97,rate:70,exp:8,
   tags:['גילאי 3-8','ספורט'],bio:'מדריך נוער ותיק, מתמחה בפעילות חוץ וספורט. סבלני ואחראי.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
  {id:3,name:'מאיה פרידמן',age:22,city:'תל אביב',dist:0.8,rating:5.0,reviews:64,rate:60,exp:4,
   tags:['גילאי 0-3','דוברת אנגלית'],bio:'דו-לשונית, נהדרת עם תינוקות. לומדת ריפוי בעיסוק.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות']},
  {id:4,name:'דניאל ביטון',age:31,city:'הרצליה',dist:5.1,rating:4.7,reviews:210,rate:80,exp:11,
   tags:['גילאי 6-12','עזרה בשיעורים'],bio:'מורה פרטי במתמטיקה ומדעים, משלב למידה והנאה. ניסיון רב עם משפחות.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
  {id:5,name:'שירה אזולאי',age:26,city:'גבעתיים',dist:3.0,rating:4.9,reviews:143,rate:68,exp:7,
   tags:['גילאי 0-3','צרכים מיוחדים'],bio:'בעלת הכשרה לעבודה עם ילדים עם צרכים מיוחדים. רגישה, חמה ומקצועית.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
  {id:6,name:'איתי שלום',age:23,city:'רמת גן',dist:2.9,rating:4.6,reviews:51,rate:58,exp:3,
   tags:['גילאי 3-8','מוזיקה'],bio:'מורה לגיטרה, אוהב להעביר חוגי מוזיקה קטנים לילדים. אנרגטי ומלא סבלנות.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות']},
  {id:7,name:'ליאל מזרחי',age:29,city:'תל אביב',dist:1.9,rating:4.95,reviews:176,rate:75,exp:9,
   tags:['גילאי 0-3','לינה'],bio:'אחות בהכשרתה, זמינה גם למשמרות לילה ולינה. מקצועית ואמינה.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
  {id:8,name:'תמר גולן',age:25,city:'הרצליה',dist:4.7,rating:4.8,reviews:88,rate:66,exp:5,
   tags:['גילאי 3-8','יצירה'],bio:'אומנית ומדריכת יצירה, הופכת כל בית להרפתקה. אחראית ומסורה.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות']},
  {id:9,name:'עומר נחום',age:27,city:'גבעתיים',dist:3.4,rating:4.7,reviews:120,rate:64,exp:6,
   tags:['גילאי 6-12','עזרה בשיעורים'],bio:'מורה לאנגלית, עוזר בשיעורי בית ומשלב משחקי חשיבה.',
   verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה']},
];

const $=(s,el=document)=>el.querySelector(s);
const $$=(s,el=document)=>[...el.querySelectorAll(s)];

/* ---- render sitter cards ---- */
function sitterCard(s){
  const stars='★'.repeat(Math.round(s.rating))+'☆'.repeat(5-Math.round(s.rating));
  return `<article class="sitter" data-id="${s.id}">
    <div class="top">
      <div class="av-lg" style="background:${avatarColor(s.name)}">${initials(s.name)}</div>
      <div>
        <div class="nm">${s.name} <span class="vbadge" title="מאומת/ת">✔</span></div>
        <div class="meta">גיל ${s.age} · ${s.city} · ${s.dist} ק"מ ממך</div>
        <div class="rating"><span class="stars">${stars}</span> ${s.rating} <span class="meta">(${s.reviews})</span></div>
      </div>
    </div>
    <div class="body">
      <div class="tags">${s.tags.map(t=>`<span class="tag">${t}</span>`).join('')}</div>
      <div class="verif">${s.verif.map(v=>`<span>✔ ${v}</span>`).join('')}</div>
    </div>
    <div class="foot">
      <div class="price"><b>₪${s.rate}</b> <small>/ שעה</small></div>
      <button class="btn btn-primary btn-sm" data-book="${s.id}">צפו והזמינו</button>
    </div>
  </article>`;
}

let activeFilter='all';
function renderSitters(){
  const city=($('#f-city')?.value||'').trim();
  let list=SITTERS.slice();
  if(city) list=list.filter(s=>s.city.includes(city)||city.includes(s.city));
  if(activeFilter!=='all') list=list.filter(s=>s.tags.some(t=>t.includes(activeFilter)));
  const wrap=$('#sitter-grid');
  if(!list.length){wrap.innerHTML=`<div class="empty">לא נמצאו שמרטפים תואמים. נסו לשנות את הסינון 🙂</div>`;return;}
  // sort by rating
  list.sort((a,b)=>b.rating-a.rating);
  wrap.innerHTML=list.map(sitterCard).join('');
}

/* ---- modal helpers ---- */
const overlay=$('#overlay'), modal=$('#modal');
function openModal(html){ modal.innerHTML=html; overlay.classList.add('show'); document.body.style.overflow='hidden'; }
function closeModal(){ overlay.classList.remove('show'); document.body.style.overflow=''; }

/* ---- sitter profile + booking ---- */
function openProfile(id){
  const s=SITTERS.find(x=>x.id===id); if(!s)return;
  const stars='★'.repeat(Math.round(s.rating))+'☆'.repeat(5-Math.round(s.rating));
  openModal(`
    <div class="modal-head"><h3>פרופיל שמרטף/ית</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body">
      <div class="profile-hero">
        <div class="av-lg" style="background:${avatarColor(s.name)}">${initials(s.name)}</div>
        <div>
          <div class="nm" style="font-size:1.3rem;font-weight:900">${s.name} <span class="vbadge">✔</span></div>
          <div class="meta">גיל ${s.age} · ${s.city} · ${s.dist} ק"מ ממך</div>
          <div class="rating"><span class="stars">${stars}</span> ${s.rating} (${s.reviews} ביקורות)</div>
        </div>
      </div>
      <p class="bio">${s.bio}</p>
      <div class="verif" style="margin-bottom:.4rem">${s.verif.map(v=>`<span>✔ ${v}</span>`).join('')}</div>
      <div class="kv">
        <div class="k"><small>תעריף</small><b>₪${s.rate} / שעה</b></div>
        <div class="k"><small>ניסיון</small><b>${s.exp} שנים</b></div>
        <div class="k"><small>התמחות</small><b>${s.tags.join(', ')}</b></div>
        <div class="k"><small>זמן הגעה משוער</small><b>~${Math.round(s.dist*5+8)} דק'</b></div>
      </div>
      <h4 style="margin:.4rem 0 .6rem;font-weight:900">בקשת הזמנה</h4>
      <form id="book-form">
        <div class="form-2">
          <div class="form-row"><label>תאריך</label><input type="date" id="b-date" required></div>
          <div class="form-row"><label>שעת התחלה</label><input type="time" id="b-time" required></div>
        </div>
        <div class="form-2">
          <div class="form-row"><label>משך (שעות)</label>
            <select id="b-hours"><option>2</option><option>3</option><option selected>4</option><option>5</option><option>6</option><option>8</option></select>
          </div>
          <div class="form-row"><label>מספר ילדים</label>
            <select id="b-kids"><option>1</option><option selected>2</option><option>3</option><option>4+</option></select>
          </div>
        </div>
        <div class="form-row"><label>הערות (אלרגיות, שגרת שינה...)</label><textarea id="b-notes" rows="2" placeholder="לדוגמה: אלרגיה לאגוזים, שינה ב-20:00"></textarea></div>
        <div class="kv" style="grid-template-columns:1fr"><div class="k" id="b-summary"></div></div>
        <button type="submit" class="btn btn-primary btn-block">שלחו בקשת הזמנה</button>
        <p class="meta" style="text-align:center;margin-top:.6rem">לא תחויבו עד שהשמרטף/ית יאשר/תאשר את הבקשה</p>
      </form>
    </div>`);
  const sum=$('#b-summary'), hours=$('#b-hours');
  const updateSum=()=>{const h=parseInt(hours.value);sum.innerHTML=`<small>הערכת עלות</small><b>₪${s.rate*h} · ${h} שעות × ₪${s.rate}</b>`;};
  updateSum(); hours.addEventListener('change',updateSum);
  $('#book-form').addEventListener('submit',e=>{
    e.preventDefault();
    openModal(`<div class="modal-head"><h3>הבקשה נשלחה</h3><button class="x" data-close>&times;</button></div>
      <div class="modal-body"><div class="success">
        <div class="big-ck">✓</div>
        <h3 style="font-weight:900;font-size:1.3rem">הבקשה נשלחה ל${s.name}!</h3>
        <p class="meta" style="margin:.6rem 0 1rem">תקבלו התראה ברגע שהבקשה תאושר. תוכלו לעקוב אחר ההגעה במפה החיה ולשתף מיקום עם איש קשר לחירום.</p>
        <button class="btn btn-primary btn-block" data-close>מצוין, סגרו</button>
      </div></div>`);
    toast('בקשת ההזמנה נשלחה ✔');
  });
}

/* ---- become-a-sitter wizard ---- */
const wizState={step:0,data:{},police:false};
const WIZ_STEPS=['פרטים אישיים','ניסיון והכשרה','בטיחות ובדיקות','סיום'];

function openWizard(){ wizState.step=0; wizState.data={}; wizState.police=false; renderWizard(); }

function renderWizard(){
  const bar=WIZ_STEPS.map((_,i)=>`<div class="sb ${i<=wizState.step?'on':''}"></div>`).join('');
  let body='';
  if(wizState.step===0){
    body=`
      <div class="step-label">שלב 1 מתוך 4 · ${WIZ_STEPS[0]}</div>
      <div class="form-2">
        <div class="form-row"><label>שם מלא *</label><input id="w-name" value="${wizState.data.name||''}" placeholder="שם פרטי ומשפחה"></div>
        <div class="form-row"><label>תעודת זהות *</label><input id="w-id" value="${wizState.data.id||''}" inputmode="numeric" placeholder="9 ספרות"></div>
      </div>
      <div class="form-2">
        <div class="form-row"><label>גיל *</label><input id="w-age" value="${wizState.data.age||''}" inputmode="numeric" placeholder="18+"></div>
        <div class="form-row"><label>טלפון *</label><input id="w-phone" value="${wizState.data.phone||''}" inputmode="tel" placeholder="05X-XXXXXXX"></div>
      </div>
      <div class="form-row"><label>אימייל *</label><input id="w-email" value="${wizState.data.email||''}" placeholder="name@email.com"></div>
      <div class="form-row"><label>עיר מגורים *</label><input id="w-city" value="${wizState.data.city||''}" placeholder="עיר"></div>`;
  } else if(wizState.step===1){
    body=`
      <div class="step-label">שלב 2 מתוך 4 · ${WIZ_STEPS[1]}</div>
      <div class="form-2">
        <div class="form-row"><label>שנות ניסיון *</label><input id="w-exp" value="${wizState.data.exp||''}" inputmode="numeric" placeholder="לדוגמה: 3"></div>
        <div class="form-row"><label>תעריף מבוקש לשעה (₪) *</label><input id="w-rate" value="${wizState.data.rate||''}" inputmode="numeric" placeholder="לדוגמה: 65"></div>
      </div>
      <div class="form-row"><label>טווחי גיל שתשמחו לטפל בהם *</label>
        <select id="w-ages"><option value="">בחרו...</option><option>גילאי 0-3</option><option>גילאי 3-8</option><option>גילאי 6-12</option><option>כל הגילאים</option></select></div>
      <div class="form-row"><label>הכשרות והסמכות (אופציונלי)</label>
        <textarea id="w-cert" rows="2" placeholder="עזרה ראשונה, חינוך, סיעוד, חוגים...">${wizState.data.cert||''}</textarea></div>
      <div class="form-row"><label>ספרו על עצמכם (יוצג בפרופיל) *</label>
        <textarea id="w-bio" rows="3" placeholder="כמה משפטים שיגרמו להורים לבחור בכם">${wizState.data.bio||''}</textarea></div>`;
  } else if(wizState.step===2){
    body=`
      <div class="step-label">שלב 3 מתוך 4 · ${WIZ_STEPS[2]}</div>
      <p class="meta" style="margin-bottom:1rem">הבטיחות של הילדים היא הדבר החשוב ביותר. כדי להתקבל כשמרטף/ית ב-GetSitter חובה לעבור את כל הבדיקות הבאות.</p>
      <label class="consent"><input type="checkbox" id="c-bg"><span><b>הסכמה לבדיקת רקע פלילי.</b> אני מאשר/ת ל-GetSitter לבצע בדיקת רקע פלילי מקיפה דרך גורם מוסמך.</span></label>
      <label class="consent"><input type="checkbox" id="c-police"><span><b>הצהרה על היעדר עבר פלילי.</b> אני מצהיר/ה שאין לי הרשעות פליליות, ובפרט לא בעבירות מין או אלימות, ומתחייב/ת להציג תעודת יושר.</span></label>
      <label class="consent"><input type="checkbox" id="c-id"><span><b>אימות זהות.</b> אני מסכים/ה לאימות זהות ביומטרי מול תעודה מזהה רשמית.</span></label>
      <label class="consent"><input type="checkbox" id="c-terms"><span><b>תקנון ומדיניות.</b> קראתי ואני מסכים/ה לתקנון, למדיניות הפרטיות ולכללי ההתנהגות.</span></label>
      <div class="form-row" style="margin-top:.4rem"><label>העלאת תעודת יושר ממשטרת ישראל *</label>
        <div class="upload ${wizState.police?'done':''}" id="w-upload">${wizState.police?'✔ תעודת יושר הועלתה':'📎 לחצו להעלאת קובץ (PDF / תמונה)'}</div></div>`;
  } else {
    const d=wizState.data;
    openModal(`
      <div class="modal-head"><h3>הבקשה התקבלה</h3><button class="x" data-close>&times;</button></div>
      <div class="modal-body"><div class="success">
        <div class="big-ck">✓</div>
        <h3 style="font-weight:900;font-size:1.35rem">תודה ${d.name||''}! הבקשה שלך נקלטה</h3>
        <p class="meta" style="margin:.7rem auto 1.2rem;max-width:420px">
          השלב הבא: צוות הבטיחות שלנו יבצע בדיקת רקע פלילי, יאמת את תעודת היושר וזהותך, ויזמן אותך לראיון אישי קצר.
          התהליך נמשך בדרך כלל 3–5 ימי עסקים. נעדכן אותך במייל ובסמס.
        </p>
        <div class="kv" style="text-align:right">
          <div class="k"><small>סטטוס</small><b style="color:var(--warn)">⏳ ממתין לבדיקת רקע</b></div>
          <div class="k"><small>מספר בקשה</small><b>GS-${Math.floor(100000+Math.random()*900000)}</b></div>
        </div>
        <button class="btn btn-primary btn-block" data-close>סיום</button>
      </div></div>`);
    toast('בקשת ההצטרפות נשלחה ✔');
    return;
  }

  openModal(`
    <div class="modal-head"><h3>הצטרפות כשמרטף/ית</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body">
      <div class="steps-bar">${bar}</div>
      <form id="wiz-form">${body}</form>
      <div class="wizard-foot">
        ${wizState.step>0?'<button class="btn btn-ghost" id="w-back">חזרה</button>':'<span></span>'}
        <button class="btn btn-primary" id="w-next">${wizState.step===2?'שליחת הבקשה':'המשך'}</button>
      </div>
    </div>`);

  // upload mock
  const up=$('#w-upload');
  if(up) up.addEventListener('click',()=>{wizState.police=true;up.classList.add('done');up.textContent='✔ תעודת יושר הועלתה';});
  $('#w-back')?.addEventListener('click',()=>{wizState.step--;renderWizard();});
  $('#w-next')?.addEventListener('click',()=>{ if(validateStep()){wizState.step++;renderWizard();} });
}

function field(id){return $('#'+id);}
function markErr(el,msg){
  el.classList.add('err');
  if(!el.nextElementSibling||!el.nextElementSibling.classList.contains('err-msg')){
    const s=document.createElement('div');s.className='err-msg';s.textContent=msg;el.after(s);
  }
}
function clearErrs(){$$('.err').forEach(e=>e.classList.remove('err'));$$('.err-msg').forEach(e=>e.remove());}

function validateStep(){
  clearErrs(); let ok=true;
  const req=(id,test,msg)=>{const el=field(id);if(!el)return;const v=el.value.trim();if(!test(v)){markErr(el,msg);ok=false;}else{wizState.data[id.replace('w-','')]=v;}};
  if(wizState.step===0){
    req('w-name',v=>v.length>1,'נא להזין שם מלא');
    req('w-id',v=>/^\d{9}$/.test(v),'תעודת זהות = 9 ספרות');
    req('w-age',v=>+v>=18 && +v<=80,'הגיל המינימלי הוא 18');
    req('w-phone',v=>/^0\d{1,2}-?\d{7}$/.test(v.replace(/\s/g,'')),'מספר טלפון לא תקין');
    req('w-email',v=>/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v),'אימייל לא תקין');
    req('w-city',v=>v.length>1,'נא להזין עיר');
  } else if(wizState.step===1){
    req('w-exp',v=>v!==''&&+v>=0,'נא להזין שנות ניסיון');
    req('w-rate',v=>+v>=30,'תעריף מינימלי ₪30');
    req('w-ages',v=>v!=='','נא לבחור טווח גיל');
    req('w-bio',v=>v.length>=15,'נא לכתוב לפחות משפט');
    const c=field('w-cert'); if(c) wizState.data.cert=c.value;
  } else if(wizState.step===2){
    ['c-bg','c-police','c-id','c-terms'].forEach(id=>{
      const el=field(id); if(el && !el.checked){el.closest('.consent').style.borderColor='var(--accent)';ok=false;}
      else if(el) el.closest('.consent').style.borderColor='';
    });
    if(!wizState.police){const u=$('#w-upload');if(u){u.style.borderColor='var(--accent)';u.style.color='var(--accent)';}ok=false;}
    if(!ok) toast('יש לאשר את כל הסעיפים ולהעלות תעודת יושר');
  }
  return ok;
}

/* ---- toast ---- */
let toastT;
function toast(msg){
  let t=$('#toast'); t.innerHTML='✔ '+msg.replace('✔','').trim(); t.classList.add('show');
  clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('show'),3200);
}

/* ---- event wiring ---- */
document.addEventListener('DOMContentLoaded',()=>{
  renderSitters();

  // search
  $('#search-form')?.addEventListener('submit',e=>{
    e.preventDefault(); renderSitters();
    document.querySelector('#sitters').scrollIntoView({behavior:'smooth'});
    toast('מציג שמרטפים זמינים באזורך');
  });

  // filter chips
  $$('.chip').forEach(c=>c.addEventListener('click',()=>{
    $$('.chip').forEach(x=>x.classList.remove('active'));
    c.classList.add('active'); activeFilter=c.dataset.filter; renderSitters();
  }));

  // delegate book + close + open wizard
  document.addEventListener('click',e=>{
    const book=e.target.closest('[data-book]');
    if(book){openProfile(+book.dataset.book);return;}
    const card=e.target.closest('.sitter');
    if(card && !e.target.closest('[data-book]')){openProfile(+card.dataset.id);return;}
    if(e.target.closest('[data-close]')||e.target===overlay){closeModal();return;}
    if(e.target.closest('[data-wizard]')){openWizard();return;}
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});

  // faq
  $$('.qa button').forEach(b=>b.addEventListener('click',()=>b.closest('.qa').classList.toggle('open')));

  // mobile nav
  $('#burger')?.addEventListener('click',()=>$('#nav-links').classList.toggle('open'));
  $$('#nav-links a').forEach(a=>a.addEventListener('click',()=>$('#nav-links').classList.remove('open')));
});
