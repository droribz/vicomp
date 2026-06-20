/* ===== GetSitter prototype logic — front-end app on top of GS store =====
   Demo only: no real background checks, no real payments. Data persists in
   the browser (localStorage) so accounts, bookings and reviews survive reloads. */

const AV_COLORS = ['#5B4FE5','#ff6b81','#18b26b','#f5a524','#7a6cff','#e8568c','#2bb3c0','#9b59b6'];
function avatarColor(name){let h=0;for(const c of (name||'?'))h=(h*31+c.charCodeAt(0))>>>0;return AV_COLORS[h%AV_COLORS.length];}
function initials(name){const p=(name||'?').trim().split(/\s+/);return (p[0][0]+(p[1]?p[1][0]:'')).toUpperCase();}
function starsStr(r){const n=Math.round(r);return '★'.repeat(n)+'☆'.repeat(5-n);}
const $=(s,el=document)=>el.querySelector(s);
const $$=(s,el=document)=>[...el.querySelectorAll(s)];

const STATUS = {
  pending:{label:'ממתין לאישור',color:'var(--warn)'},
  confirmed:{label:'מאושר',color:'var(--safe)'},
  completed:{label:'הושלם',color:'var(--primary)'},
  cancelled:{label:'בוטל',color:'#c0392b'},
};

/* ---------- modal / toast ---------- */
const overlay=()=>$('#overlay'), modalEl=()=>$('#modal');
function openModal(html){ modalEl().innerHTML=html; overlay().classList.add('show'); document.body.style.overflow='hidden'; }
function closeModal(){ overlay().classList.remove('show'); document.body.style.overflow=''; }
let toastT;
function toast(msg){const t=$('#toast');t.innerHTML='✔ '+msg.replace(/^✔\s*/,'');t.classList.add('show');clearTimeout(toastT);toastT=setTimeout(()=>t.classList.remove('show'),3200);}

/* ---------- sitter cards / search ---------- */
let activeFilter='all';
function sitterCard(s){
  return `<article class="sitter" data-id="${s.id}">
    <div class="top">
      <div class="av-lg" style="background:${avatarColor(s.name)}">${initials(s.name)}</div>
      <div>
        <div class="nm">${s.name} <span class="vbadge" title="מאומת/ת">✔</span></div>
        <div class="meta">גיל ${s.age} · ${s.city} · ${s.dist} ק"מ ממך</div>
        <div class="rating"><span class="stars">${starsStr(s.rating)}</span> ${s.rating} <span class="meta">(${s.reviews})</span></div>
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
function renderSitters(){
  const city=($('#f-city')?.value||'').trim();
  let list=GS.sitters().slice();
  if(city) list=list.filter(s=>s.city.includes(city)||city.includes(s.city));
  if(activeFilter!=='all') list=list.filter(s=>s.tags.some(t=>t.includes(activeFilter)));
  const wrap=$('#sitter-grid');
  if(!list.length){wrap.innerHTML=`<div class="empty">לא נמצאו שמרטפים תואמים. נסו לשנות את הסינון 🙂</div>`;return;}
  list.sort((a,b)=>b.rating-a.rating);
  wrap.innerHTML=list.map(sitterCard).join('');
}

/* ---------- auth ---------- */
let pendingAfterAuth=null;
function openAuth(tab='login', after=null){
  pendingAfterAuth=after;
  const isLogin=tab==='login';
  openModal(`
    <div class="modal-head"><h3>${isLogin?'התחברות':'הרשמה כהורה'}</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body">
      <div class="filters" style="margin:0 0 1.2rem">
        <span class="chip ${isLogin?'active':''}" data-auth="login">התחברות</span>
        <span class="chip ${!isLogin?'active':''}" data-auth="signup">הרשמה</span>
      </div>
      <form id="auth-form">
        ${isLogin?'':`
        <div class="form-row"><label>שם מלא *</label><input id="a-name" placeholder="שם פרטי ומשפחה"></div>
        <div class="form-row"><label>טלפון *</label><input id="a-phone" inputmode="tel" placeholder="05X-XXXXXXX"></div>`}
        <div class="form-row"><label>אימייל *</label><input id="a-email" placeholder="name@email.com"></div>
        <div class="form-row"><label>סיסמה *</label><input id="a-pass" type="password" placeholder="לפחות 4 תווים"></div>
        <button type="submit" class="btn btn-primary btn-block">${isLogin?'כניסה':'יצירת חשבון'}</button>
      </form>
      <p class="meta center" style="margin-top:.8rem">רוצים לעבוד כשמרטף/ית? <a href="#become" data-close style="color:var(--primary);font-weight:700">הצטרפו כאן</a></p>
    </div>`);
  $$('[data-auth]').forEach(c=>c.addEventListener('click',()=>openAuth(c.dataset.auth, pendingAfterAuth)));
  $('#auth-form').addEventListener('submit',e=>{
    e.preventDefault(); clearErrs();
    const email=$('#a-email').value.trim().toLowerCase(), pass=$('#a-pass').value;
    if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){markErr($('#a-email'),'אימייל לא תקין');return;}
    if(pass.length<4){markErr($('#a-pass'),'סיסמה קצרה מדי');return;}
    if(isLogin){
      const u=GS.findUserByEmail(email);
      if(!u||u.pass!==pass){markErr($('#a-pass'),'אימייל או סיסמה שגויים');return;}
      GS.login(u.id);
    } else {
      const name=$('#a-name').value.trim(), phone=$('#a-phone').value.trim();
      if(name.length<2){markErr($('#a-name'),'נא להזין שם');return;}
      if(!/^0\d{1,2}-?\d{7}$/.test(phone.replace(/\s/g,''))){markErr($('#a-phone'),'טלפון לא תקין');return;}
      if(GS.findUserByEmail(email)){markErr($('#a-email'),'האימייל כבר רשום');return;}
      const u=GS.addUser({name,email,phone,pass,role:'parent'});
      GS.login(u.id);
    }
    renderNav(); closeModal(); toast('התחברת בהצלחה 👋');
    const cb=pendingAfterAuth; pendingAfterAuth=null; if(cb) cb();
  });
}

function renderNav(){
  const area=$('#auth-area'); if(!area) return;
  const u=GS.currentUser();
  if(!u){
    area.innerHTML=`<a href="#" class="btn btn-ghost btn-sm" id="login-btn">התחברות</a>`;
    $('#login-btn').addEventListener('click',e=>{e.preventDefault();openAuth('login');});
  } else {
    area.innerHTML=`<a href="#" class="btn btn-ghost btn-sm" id="acct-btn">
      <span class="av" style="width:24px;height:24px;border-radius:50%;display:inline-grid;place-items:center;background:${avatarColor(u.name)};color:#fff;font-size:.7rem;font-weight:800">${initials(u.name)}</span>
      ${u.name.split(' ')[0]}</a>`;
    $('#acct-btn').addEventListener('click',e=>{e.preventDefault();openAccount();});
  }
}

/* ---------- profile + booking ---------- */
function requireParent(after){
  const u=GS.currentUser();
  if(u&&u.role==='parent'){after(u);return;}
  if(u&&u.role==='sitter'){toast('התחברת כשמרטף/ית. להזמנה יש להתחבר כהורה');return;}
  openAuth('login',()=>{const cu=GS.currentUser();if(cu&&cu.role==='parent')after(cu);});
}

function openProfile(id){
  const s=GS.getSitter(id); if(!s)return;
  const revs=GS.reviews(id);
  openModal(`
    <div class="modal-head"><h3>פרופיל שמרטף/ית</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body">
      <div class="profile-hero">
        <div class="av-lg" style="background:${avatarColor(s.name)}">${initials(s.name)}</div>
        <div>
          <div class="nm" style="font-size:1.3rem;font-weight:900">${s.name} <span class="vbadge">✔</span></div>
          <div class="meta">גיל ${s.age} · ${s.city} · ${s.dist} ק"מ ממך</div>
          <div class="rating"><span class="stars">${starsStr(s.rating)}</span> ${s.rating} (${s.reviews} ביקורות)</div>
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
      ${revs.length?`<h4 style="margin:.6rem 0 .4rem;font-weight:900">ביקורות אחרונות</h4>
        ${revs.slice(-3).reverse().map(r=>`<div class="k" style="margin-bottom:.5rem"><div class="stars">${starsStr(r.rating)}</div><div>${r.text||''}</div><small style="color:var(--muted)">— ${r.author}</small></div>`).join('')}`:''}
      <h4 style="margin:.6rem 0 .6rem;font-weight:900">בקשת הזמנה</h4>
      <form id="book-form">
        <div class="form-2">
          <div class="form-row"><label>תאריך</label><input type="date" id="b-date" required></div>
          <div class="form-row"><label>שעת התחלה</label><input type="time" id="b-time" required></div>
        </div>
        <div class="form-2">
          <div class="form-row"><label>משך (שעות)</label>
            <select id="b-hours"><option>2</option><option>3</option><option selected>4</option><option>5</option><option>6</option><option>8</option></select></div>
          <div class="form-row"><label>מספר ילדים</label>
            <select id="b-kids"><option>1</option><option selected>2</option><option>3</option><option>4+</option></select></div>
        </div>
        <div class="form-row"><label>הערות (אלרגיות, שגרת שינה...)</label><textarea id="b-notes" rows="2" placeholder="לדוגמה: אלרגיה לאגוזים, שינה ב-20:00"></textarea></div>
        <div class="kv" style="grid-template-columns:1fr"><div class="k" id="b-summary"></div></div>
        <button type="submit" class="btn btn-primary btn-block">שלחו בקשת הזמנה</button>
        <p class="meta" style="text-align:center;margin-top:.6rem">לא תחויבו עד שהשמרטף/ית יאשר/תאשר את הבקשה</p>
      </form>
    </div>`);
  const sum=$('#b-summary'), hours=$('#b-hours');
  const upd=()=>{const h=parseInt(hours.value);sum.innerHTML=`<small>הערכת עלות</small><b>₪${s.rate*h} · ${h} שעות × ₪${s.rate}</b>`;};
  upd(); hours.addEventListener('change',upd);
  $('#book-form').addEventListener('submit',e=>{
    e.preventDefault();
    const date=$('#b-date').value, time=$('#b-time').value;
    if(!date||!time){toast('נא לבחור תאריך ושעה');return;}
    const draft={sitterId:s.id,date,time,hours:+hours.value,kids:$('#b-kids').value,notes:$('#b-notes').value.trim(),rate:s.rate,total:s.rate*(+hours.value)};
    requireParent(u=>{
      const b=GS.addBooking(Object.assign({parentId:u.id,parentName:u.name,sitterName:s.name},draft));
      openModal(`<div class="modal-head"><h3>הבקשה נשלחה</h3><button class="x" data-close>&times;</button></div>
        <div class="modal-body"><div class="success">
          <div class="big-ck">✓</div>
          <h3 style="font-weight:900;font-size:1.3rem">הבקשה נשלחה ל${s.name}!</h3>
          <p class="meta" style="margin:.6rem 0 1rem">תקבלו התראה כשהבקשה תאושר. אפשר לעקוב אחר הסטטוס וההגעה ב"החשבון שלי".</p>
          <div class="wizard-foot"><button class="btn btn-ghost" data-close>סגירה</button><button class="btn btn-primary" id="goto-bookings">החשבון שלי</button></div>
        </div></div>`);
      $('#goto-bookings').addEventListener('click',openAccount);
      toast('בקשת ההזמנה נשלחה ✔');
    });
  });
}

/* ---------- account dashboards ---------- */
function bookingRow(b, role){
  const st=STATUS[b.status]||STATUS.pending;
  const who = role==='parent' ? b.sitterName : b.parentName;
  let actions='';
  if(role==='parent'){
    if(b.status==='pending'||b.status==='confirmed') actions+=`<button class="btn btn-ghost btn-sm" data-act="cancel" data-id="${b.id}">ביטול</button>`;
    if(b.status==='confirmed') actions+=`<button class="btn btn-safe btn-sm" data-act="complete" data-id="${b.id}">סיום ותשלום</button>`;
    if(b.status==='completed'&&!b.rated) actions+=`<button class="btn btn-primary btn-sm" data-act="rate" data-id="${b.id}">דרגו</button>`;
  } else {
    if(b.status==='pending'){actions+=`<button class="btn btn-safe btn-sm" data-act="accept" data-id="${b.id}">אישור</button><button class="btn btn-ghost btn-sm" data-act="decline" data-id="${b.id}">דחייה</button>`;}
    if(b.status==='confirmed') actions+=`<button class="btn btn-primary btn-sm" data-act="finish" data-id="${b.id}">סמן כהושלם</button>`;
  }
  return `<div class="k" style="margin-bottom:.6rem">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
      <div><b>${who}</b><br><small style="color:var(--muted)">${b.date} · ${b.time} · ${b.hours} שעות · ${b.kids} ילדים</small></div>
      <span style="font-weight:800;color:${st.color}">${st.label}</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:.5rem;flex-wrap:wrap;gap:8px">
      <b style="color:var(--primary)">₪${b.total}</b>
      <div style="display:flex;gap:.4rem">${actions}</div>
    </div>
    ${b.notes?`<small style="color:var(--muted);display:block;margin-top:.4rem">📝 ${b.notes}</small>`:''}
  </div>`;
}

function openAccount(){
  const u=GS.currentUser(); if(!u){openAuth('login');return;}
  const isSitter=u.role==='sitter';
  const list=isSitter?GS.bookingsForSitter(u.sitterId):GS.bookingsForParent(u.id);
  const rows=list.length?list.map(b=>bookingRow(b,u.role)).join(''):`<div class="empty">אין הזמנות עדיין.</div>`;
  openModal(`
    <div class="modal-head">
      <h3>👋 ${u.name}</h3>
      <div style="display:flex;gap:.5rem;align-items:center"><button class="btn btn-ghost btn-sm" id="logout-btn">יציאה</button><button class="x" data-close>&times;</button></div>
    </div>
    <div class="modal-body">
      <p class="meta" style="margin-bottom:1rem">${isSitter?'הבקשות שהתקבלו עבורך:':'ההזמנות שלך:'} </p>
      <div id="acct-list">${rows}</div>
      ${isSitter?'':`<button class="btn btn-primary btn-block" data-close style="margin-top:.6rem" onclick="document.querySelector('#sitters').scrollIntoView({behavior:'smooth'})">הזמנת שמרטף/ית חדש/ה</button>`}
    </div>`);
  $('#logout-btn').addEventListener('click',()=>{GS.logout();renderNav();closeModal();toast('התנתקת');});
  $('#acct-list').addEventListener('click',e=>{
    const btn=e.target.closest('[data-act]'); if(!btn)return;
    const id=btn.dataset.id, act=btn.dataset.act;
    if(act==='cancel'||act==='decline') GS.updateBooking(id,{status:'cancelled'});
    if(act==='accept') GS.updateBooking(id,{status:'confirmed'});
    if(act==='complete'||act==='finish') GS.updateBooking(id,{status:'completed'});
    if(act==='rate'){openRate(id);return;}
    if(act==='accept') toast('ההזמנה אושרה ✔');
    if(act==='complete'||act==='finish') toast('ההזמנה הושלמה ✔');
    openAccount(); // refresh
  });
}

function openRate(bookingId){
  const b=GS.bookings().find(x=>x.id===bookingId); if(!b)return;
  let chosen=5;
  openModal(`
    <div class="modal-head"><h3>דרגו את ${b.sitterName}</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body">
      <div id="rate-stars" style="font-size:2.4rem;text-align:center;color:#f5a524;cursor:pointer;letter-spacing:.2rem">★★★★★</div>
      <div class="form-row"><label>מה דעתכם? (אופציונלי)</label><textarea id="rate-text" rows="3" placeholder="ספרו להורים הבאים על החוויה"></textarea></div>
      <button class="btn btn-primary btn-block" id="rate-submit">שליחת דירוג</button>
    </div>`);
  const wrap=$('#rate-stars');
  const draw=n=>wrap.textContent='★'.repeat(n)+'☆'.repeat(5-n);
  wrap.addEventListener('mousemove',e=>{const i=Math.ceil((e.offsetX/wrap.offsetWidth)*5);draw(Math.max(1,Math.min(5,6-i)));});
  wrap.addEventListener('click',e=>{const i=Math.ceil((e.offsetX/wrap.offsetWidth)*5);chosen=Math.max(1,Math.min(5,6-i));draw(chosen);});
  $('#rate-submit').addEventListener('click',()=>{
    const u=GS.currentUser();
    GS.addReview({sitterId:b.sitterId,rating:chosen,text:$('#rate-text').value.trim(),author:u?u.name:'הורה'});
    GS.updateBooking(bookingId,{rated:true});
    renderSitters(); closeModal(); toast('תודה על הדירוג! ⭐');
  });
}

/* ---------- become-a-sitter wizard ---------- */
const wizState={step:0,data:{},police:false};
const WIZ_STEPS=['פרטים אישיים','ניסיון והכשרה','בטיחות ובדיקות','סיום'];
function field(id){return $('#'+id);}
function markErr(el,msg){el.classList.add('err');if(!el.nextElementSibling||!el.nextElementSibling.classList.contains('err-msg')){const s=document.createElement('div');s.className='err-msg';s.textContent=msg;el.after(s);}}
function clearErrs(){$$('.err').forEach(e=>e.classList.remove('err'));$$('.err-msg').forEach(e=>e.remove());}

function openWizard(){wizState.step=0;wizState.data={};wizState.police=false;renderWizard();}
function renderWizard(){
  const bar=WIZ_STEPS.map((_,i)=>`<div class="sb ${i<=wizState.step?'on':''}"></div>`).join('');
  let body='';
  if(wizState.step===0){
    body=`
      <div class="step-label">שלב 1 מתוך 4 · ${WIZ_STEPS[0]}</div>
      <div class="form-2">
        <div class="form-row"><label>שם מלא *</label><input id="w-name" value="${wizState.data.name||''}" placeholder="שם פרטי ומשפחה"></div>
        <div class="form-row"><label>תעודת זהות *</label><input id="w-id" value="${wizState.data.idnum||''}" inputmode="numeric" placeholder="9 ספרות"></div>
      </div>
      <div class="form-2">
        <div class="form-row"><label>גיל *</label><input id="w-age" value="${wizState.data.age||''}" inputmode="numeric" placeholder="18+"></div>
        <div class="form-row"><label>טלפון *</label><input id="w-phone" value="${wizState.data.phone||''}" inputmode="tel" placeholder="05X-XXXXXXX"></div>
      </div>
      <div class="form-2">
        <div class="form-row"><label>אימייל *</label><input id="w-email" value="${wizState.data.email||''}" placeholder="name@email.com"></div>
        <div class="form-row"><label>סיסמה *</label><input id="w-pass" type="password" value="${wizState.data.pass||''}" placeholder="לפחות 4 תווים"></div>
      </div>
      <div class="form-row"><label>עיר מגורים *</label><input id="w-city" value="${wizState.data.city||''}" placeholder="עיר"></div>`;
  } else if(wizState.step===1){
    body=`
      <div class="step-label">שלב 2 מתוך 4 · ${WIZ_STEPS[1]}</div>
      <div class="form-2">
        <div class="form-row"><label>שנות ניסיון *</label><input id="w-exp" value="${wizState.data.exp||''}" inputmode="numeric" placeholder="לדוגמה: 3"></div>
        <div class="form-row"><label>תעריף לשעה (₪) *</label><input id="w-rate" value="${wizState.data.rate||''}" inputmode="numeric" placeholder="לדוגמה: 65"></div>
      </div>
      <div class="form-row"><label>טווח גיל מועדף *</label>
        <select id="w-ages"><option value="">בחרו...</option><option>גילאי 0-3</option><option>גילאי 3-8</option><option>גילאי 6-12</option><option>כל הגילאים</option></select></div>
      <div class="form-row"><label>הכשרות והסמכות (אופציונלי)</label><textarea id="w-cert" rows="2" placeholder="עזרה ראשונה, חינוך, סיעוד, חוגים...">${wizState.data.cert||''}</textarea></div>
      <div class="form-row"><label>ספרו על עצמכם (יוצג בפרופיל) *</label><textarea id="w-bio" rows="3" placeholder="כמה משפטים שיגרמו להורים לבחור בכם">${wizState.data.bio||''}</textarea></div>`;
  } else if(wizState.step===2){
    body=`
      <div class="step-label">שלב 3 מתוך 4 · ${WIZ_STEPS[2]}</div>
      <p class="meta" style="margin-bottom:1rem">הבטיחות של הילדים היא הדבר החשוב ביותר. כדי להתקבל חובה לעבור את כל הבדיקות הבאות.</p>
      <label class="consent"><input type="checkbox" id="c-bg"><span><b>הסכמה לבדיקת רקע פלילי.</b> אני מאשר/ת ל-GetSitter לבצע בדיקת רקע פלילי מקיפה דרך גורם מוסמך.</span></label>
      <label class="consent"><input type="checkbox" id="c-police"><span><b>הצהרה על היעדר עבר פלילי.</b> אני מצהיר/ה שאין לי הרשעות פליליות, ובפרט לא בעבירות מין או אלימות.</span></label>
      <label class="consent"><input type="checkbox" id="c-id"><span><b>אימות זהות.</b> אני מסכים/ה לאימות זהות ביומטרי מול תעודה מזהה רשמית.</span></label>
      <label class="consent"><input type="checkbox" id="c-terms"><span><b>תקנון ומדיניות.</b> קראתי ואני מסכים/ה לתקנון, למדיניות הפרטיות ולכללי ההתנהגות.</span></label>
      <div class="form-row" style="margin-top:.4rem"><label>העלאת תעודת יושר ממשטרת ישראל *</label>
        <div class="upload ${wizState.police?'done':''}" id="w-upload">${wizState.police?'✔ תעודת יושר הועלתה':'📎 לחצו להעלאת קובץ (PDF / תמונה)'}</div></div>`;
  } else {
    finishWizard(); return;
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
  const up=$('#w-upload');
  if(up) up.addEventListener('click',()=>{wizState.police=true;up.classList.add('done');up.textContent='✔ תעודת יושר הועלתה';});
  $('#w-back')?.addEventListener('click',()=>{wizState.step--;renderWizard();});
  $('#w-next')?.addEventListener('click',()=>{if(validateStep()){wizState.step++;renderWizard();}});
}

function validateStep(){
  clearErrs(); let ok=true;
  const d=wizState.data;
  const req=(id,key,test,msg)=>{const el=field(id);if(!el)return;const v=el.value.trim();if(!test(v)){markErr(el,msg);ok=false;}else{d[key]=v;}};
  if(wizState.step===0){
    req('w-name','name',v=>v.length>1,'נא להזין שם מלא');
    req('w-id','idnum',v=>/^\d{9}$/.test(v),'תעודת זהות = 9 ספרות');
    req('w-age','age',v=>+v>=18&&+v<=80,'הגיל המינימלי הוא 18');
    req('w-phone','phone',v=>/^0\d{1,2}-?\d{7}$/.test(v.replace(/\s/g,'')),'מספר טלפון לא תקין');
    req('w-email','email',v=>/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v),'אימייל לא תקין');
    req('w-pass','pass',v=>v.length>=4,'סיסמה קצרה מדי');
    req('w-city','city',v=>v.length>1,'נא להזין עיר');
    if(ok&&GS.findUserByEmail(d.email)){markErr(field('w-email'),'האימייל כבר רשום');ok=false;}
  } else if(wizState.step===1){
    req('w-exp','exp',v=>v!==''&&+v>=0,'נא להזין שנות ניסיון');
    req('w-rate','rate',v=>+v>=30,'תעריף מינימלי ₪30');
    req('w-ages','ages',v=>v!=='','נא לבחור טווח גיל');
    req('w-bio','bio',v=>v.length>=15,'נא לכתוב לפחות משפט');
    const c=field('w-cert'); if(c) d.cert=c.value;
  } else if(wizState.step===2){
    ['c-bg','c-police','c-id','c-terms'].forEach(id=>{const el=field(id);if(el&&!el.checked){el.closest('.consent').style.borderColor='var(--accent)';ok=false;}else if(el)el.closest('.consent').style.borderColor='';});
    if(!wizState.police){const u=$('#w-upload');if(u){u.style.borderColor='var(--accent)';u.style.color='var(--accent)';}ok=false;}
    if(!ok) toast('יש לאשר את כל הסעיפים ולהעלות תעודת יושר');
  }
  return ok;
}

function finishWizard(){
  const d=wizState.data;
  // create sitter profile + linked user account, then log in
  const sitterId=GS.uid('s_');
  GS.saveSitter({
    id:sitterId,name:d.name,age:+d.age,city:d.city,dist:+(Math.random()*4+0.5).toFixed(1),
    rating:5.0,reviews:0,rate:+d.rate,exp:+d.exp,
    tags:[d.ages,...(d.cert&&/עזרה ראשונה/.test(d.cert)?['עזרה ראשונה']:[])].filter(Boolean),
    bio:d.bio,verif:['רקע פלילי','תעודת יושר','אימות זהות'],pending:true,
  });
  const user=GS.addUser({name:d.name,email:d.email,phone:d.phone,pass:d.pass,role:'sitter',sitterId});
  GS.login(user.id); renderNav(); renderSitters();
  openModal(`
    <div class="modal-head"><h3>הבקשה התקבלה</h3><button class="x" data-close>&times;</button></div>
    <div class="modal-body"><div class="success">
      <div class="big-ck">✓</div>
      <h3 style="font-weight:900;font-size:1.35rem">תודה ${d.name}! נרשמת בהצלחה</h3>
      <p class="meta" style="margin:.7rem auto 1.2rem;max-width:420px">
        השלב הבא: צוות הבטיחות יבצע בדיקת רקע פלילי, יאמת את תעודת היושר וזהותך, ויזמן אותך לראיון אישי קצר.
        התהליך נמשך בדרך כלל 3–5 ימי עסקים. בינתיים החשבון שלך פעיל ותוכל/י לראות בקשות הזמנה ב"החשבון שלי".
      </p>
      <div class="kv" style="text-align:right">
        <div class="k"><small>סטטוס</small><b style="color:var(--warn)">⏳ ממתין לבדיקת רקע</b></div>
        <div class="k"><small>מספר בקשה</small><b>GS-${Math.floor(100000+Math.random()*900000)}</b></div>
      </div>
      <button class="btn btn-primary btn-block" id="goto-acct">למעבר לחשבון שלי</button>
    </div></div>`);
  $('#goto-acct').addEventListener('click',openAccount);
  toast('בקשת ההצטרפות נשלחה ✔');
}

/* ---------- wiring ---------- */
document.addEventListener('DOMContentLoaded',()=>{
  renderSitters(); renderNav();

  $('#search-form')?.addEventListener('submit',e=>{
    e.preventDefault(); renderSitters();
    $('#sitters').scrollIntoView({behavior:'smooth'}); toast('מציג שמרטפים זמינים באזורך');
  });
  $$('.chip[data-filter]').forEach(c=>c.addEventListener('click',()=>{
    $$('.chip[data-filter]').forEach(x=>x.classList.remove('active'));
    c.classList.add('active'); activeFilter=c.dataset.filter; renderSitters();
  }));

  document.addEventListener('click',e=>{
    const book=e.target.closest('[data-book]'); if(book){openProfile(book.dataset.book);return;}
    const card=e.target.closest('.sitter'); if(card&&!e.target.closest('[data-book]')){openProfile(card.dataset.id);return;}
    if(e.target.closest('[data-close]')||e.target===overlay()){closeModal();return;}
    if(e.target.closest('[data-wizard]')){openWizard();return;}
    if(e.target.closest('[data-login]')){openAuth('login');return;}
  });
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});

  $$('.qa button').forEach(b=>b.addEventListener('click',()=>b.closest('.qa').classList.toggle('open')));
  $('#burger')?.addEventListener('click',()=>$('#nav-links').classList.toggle('open'));
  $$('#nav-links a').forEach(a=>a.addEventListener('click',()=>$('#nav-links').classList.remove('open')));
});
