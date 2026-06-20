/* ===== GetSitter — client-side data layer (localStorage) =====
   Standalone demo persistence. No server, no real PII handling. */
(function (global) {
  const K = {
    USERS: 'gs_users',
    SITTERS: 'gs_sitters',
    BOOKINGS: 'gs_bookings',
    REVIEWS: 'gs_reviews',
    SESSION: 'gs_session',
    SEEDED: 'gs_seeded_v1',
  };

  const SEED_SITTERS = [
    {id:'s1',name:'נועה לוי',age:24,city:'תל אביב',dist:1.2,rating:4.9,reviews:182,rate:65,exp:6,
     tags:['גילאי 0-3','עזרה בשיעורים'],bio:'סטודנטית לחינוך, מנוסה עם תינוקות ופעוטות. אוהבת פעילות יצירתית ומשחקי תנועה.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
    {id:'s2',name:'יואב כהן',age:28,city:'רמת גן',dist:2.4,rating:4.8,reviews:97,rate:70,exp:8,
     tags:['גילאי 3-8','ספורט'],bio:'מדריך נוער ותיק, מתמחה בפעילות חוץ וספורט. סבלני ואחראי.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
    {id:'s3',name:'מאיה פרידמן',age:22,city:'תל אביב',dist:0.8,rating:5.0,reviews:64,rate:60,exp:4,
     tags:['גילאי 0-3','דוברת אנגלית'],bio:'דו-לשונית, נהדרת עם תינוקות. לומדת ריפוי בעיסוק.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות'],seed:true},
    {id:'s4',name:'דניאל ביטון',age:31,city:'הרצליה',dist:5.1,rating:4.7,reviews:210,rate:80,exp:11,
     tags:['גילאי 6-12','עזרה בשיעורים'],bio:'מורה פרטי במתמטיקה ומדעים, משלב למידה והנאה. ניסיון רב עם משפחות.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
    {id:'s5',name:'שירה אזולאי',age:26,city:'גבעתיים',dist:3.0,rating:4.9,reviews:143,rate:68,exp:7,
     tags:['גילאי 0-3','צרכים מיוחדים'],bio:'בעלת הכשרה לעבודה עם ילדים עם צרכים מיוחדים. רגישה, חמה ומקצועית.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
    {id:'s6',name:'איתי שלום',age:23,city:'רמת גן',dist:2.9,rating:4.6,reviews:51,rate:58,exp:3,
     tags:['גילאי 3-8','מוזיקה'],bio:'מורה לגיטרה, אוהב להעביר חוגי מוזיקה קטנים לילדים. אנרגטי ומלא סבלנות.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות'],seed:true},
    {id:'s7',name:'ליאל מזרחי',age:29,city:'תל אביב',dist:1.9,rating:4.95,reviews:176,rate:75,exp:9,
     tags:['גילאי 0-3','לינה'],bio:'אחות בהכשרתה, זמינה גם למשמרות לילה ולינה. מקצועית ואמינה.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
    {id:'s8',name:'תמר גולן',age:25,city:'הרצליה',dist:4.7,rating:4.8,reviews:88,rate:66,exp:5,
     tags:['גילאי 3-8','יצירה'],bio:'אומנית ומדריכת יצירה, הופכת כל בית להרפתקה. אחראית ומסורה.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות'],seed:true},
    {id:'s9',name:'עומר נחום',age:27,city:'גבעתיים',dist:3.4,rating:4.7,reviews:120,rate:64,exp:6,
     tags:['גילאי 6-12','עזרה בשיעורים'],bio:'מורה לאנגלית, עוזר בשיעורי בית ומשלב משחקי חשיבה.',
     verif:['רקע פלילי','תעודת יושר','אימות זהות','עזרה ראשונה'],seed:true},
  ];

  function read(k, def) {
    try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : def; }
    catch (e) { return def; }
  }
  function write(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
  }
  function uid(p) { return p + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

  function seed() {
    if (read(K.SEEDED, false)) return;
    write(K.SITTERS, SEED_SITTERS);
    write(K.SEEDED, true);
  }

  const GS = {
    K,
    seed,
    uid,

    // ---- sitters ----
    sitters() { return read(K.SITTERS, []); },
    getSitter(id) { return this.sitters().find(s => s.id === id); },
    saveSitter(s) {
      const list = this.sitters();
      const i = list.findIndex(x => x.id === s.id);
      if (i >= 0) list[i] = s; else list.push(s);
      write(K.SITTERS, list);
      return s;
    },

    // ---- users ----
    users() { return read(K.USERS, []); },
    findUserByEmail(email) {
      email = (email || '').toLowerCase().trim();
      return this.users().find(u => u.email === email);
    },
    addUser(u) {
      const list = this.users();
      u.id = u.id || uid('u_');
      u.email = u.email.toLowerCase().trim();
      list.push(u);
      write(K.USERS, list);
      return u;
    },
    getUser(id) { return this.users().find(u => u.id === id); },

    // ---- session ----
    session() { return read(K.SESSION, null); },
    login(userId) { write(K.SESSION, { userId }); return this.currentUser(); },
    logout() { localStorage.removeItem(K.SESSION); },
    currentUser() {
      const s = this.session();
      return s ? this.getUser(s.userId) : null;
    },

    // ---- bookings ----
    bookings() { return read(K.BOOKINGS, []); },
    addBooking(b) {
      const list = this.bookings();
      b.id = uid('b_');
      b.status = 'pending';
      b.createdAt = Date.now();
      b.rated = false;
      list.push(b);
      write(K.BOOKINGS, list);
      return b;
    },
    updateBooking(id, patch) {
      const list = this.bookings();
      const i = list.findIndex(b => b.id === id);
      if (i < 0) return null;
      list[i] = Object.assign(list[i], patch);
      write(K.BOOKINGS, list);
      return list[i];
    },
    bookingsForParent(pid) { return this.bookings().filter(b => b.parentId === pid).sort((a, b) => b.createdAt - a.createdAt); },
    bookingsForSitter(sid) { return this.bookings().filter(b => b.sitterId === sid).sort((a, b) => b.createdAt - a.createdAt); },

    // ---- reviews ----
    reviews(sitterId) { return read(K.REVIEWS, []).filter(r => r.sitterId === sitterId); },
    addReview(r) {
      const list = read(K.REVIEWS, []);
      r.id = uid('r_');
      r.createdAt = Date.now();
      list.push(r);
      write(K.REVIEWS, list);
      // update sitter aggregate rating
      const sit = this.getSitter(r.sitterId);
      if (sit) {
        const all = this.reviews(r.sitterId);
        const avg = all.reduce((s, x) => s + x.rating, 0) / all.length;
        sit.rating = Math.round(avg * 10) / 10;
        sit.reviews = (sit.reviews || 0) + 1;
        this.saveSitter(sit);
      }
      return r;
    },
  };

  seed();
  global.GS = GS;
})(window);
