/* ==========================================================================
   4.5room — v3（全ページ共通）
   ・_dir/content/*.json を読み、data-fill などの印に差し込む
     （数値は直書きしない。取得できなければ「—」のまま＝古い値を出さない）
   ・ヘッダーの切り替え／出現／ストリップの送り
   JSON の置き場所は <html data-content="…/"> で指定する。
   ========================================================================== */
(function(){
  "use strict";

  var root = document.documentElement;
  var BASE = root.getAttribute("data-content") || "../content/";

  /* --- 書式 ------------------------------------------------------------- */
  function fmtNum(n){ return (typeof n === "number") ? n.toLocaleString("ja-JP") : "—"; }
  // "2026-09-04" → "2026.09.04"、"2023-03" → "2023.03"
  function fmtDate(s){ return (typeof s === "string" && s) ? s.replace(/-/g, ".") : "—"; }
  function get(obj, path){
    return path.split(".").reduce(function(o, k){ return (o == null) ? undefined : o[k]; }, obj);
  }
  function el(tag, cls, text){
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function ytUrl(id){ return "https://www.youtube.com/watch?v=" + encodeURIComponent(id); }

  // 経過（年・か月）。月単位で切り捨て
  function elapsed(from){
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(from || "");
    if (!m) return null;
    var now = new Date();
    var months = (now.getFullYear() - +m[1]) * 12 + (now.getMonth() + 1 - +m[2]);
    if (now.getDate() < +m[3]) months -= 1;
    if (months < 0) return null;
    return { y: Math.floor(months / 12), m: months % 12 };
  }

  /* --- JSON を読む ------------------------------------------------------ */
  function load(name){
    return fetch(BASE + name + ".json", { cache: "no-cache" })
      .then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function(){ return null; });
  }

  Promise.all(["channel", "lab", "notes", "carry", "site"].map(load)).then(function(res){
    var data = { channel: res[0], lab: res[1], notes: res[2], carry: res[3], site: res[4] };

    // 持ちものの点数は carry.json から数える（表示と実体を一致させる）
    if (data.carry && data.carry.groups){
      data.carry.count = data.carry.groups.reduce(function(s, g){ return s + (g.items || []).length; }, 0);
    }

    fill(data);
    fillElapsed(data.channel);
    fillLatest(data);
    fillGroupCounts(data.carry);
    fillCarryFull(data.carry);
    fillMedia(data.site);
    fillTop(data.channel);
    fillMail(data.site);
  });

  // data-fill="channel.subscribers" など。数値は桁区切り、日付は YYYY.MM.DD
  function fill(data){
    document.querySelectorAll("[data-fill]").forEach(function(node){
      var key = node.getAttribute("data-fill");
      var v = get(data, key);
      if (v == null) return;
      node.textContent = (typeof v === "number") ? fmtNum(v)
        : /(^|\.)(measured_at|first_upload|published|date|opened)$/.test(key) ? fmtDate(v) : v;
    });
  }

  function fillElapsed(ch){
    var e = ch && elapsed(ch.first_upload);
    if (!e) return;
    document.querySelectorAll("[data-elapsed]").forEach(function(node){
      node.textContent = "";
      node.appendChild(document.createTextNode(e.y));
      node.appendChild(el("span", "u", "年"));
      node.appendChild(document.createTextNode(e.m));
      node.appendChild(el("span", "u", "か月"));
      node.setAttribute("aria-label", e.y + "年" + e.m + "か月");
    });
  }

  // 行き先の最新1本（本編・Lab・note）
  function fillLatest(data){
    document.querySelectorAll("[data-latest]").forEach(function(a){
      var src = a.getAttribute("data-latest");
      var item, href, date;
      if (src === "notes"){
        item = data.notes && data.notes.items && data.notes.items[0];
        if (!item) return;
        href = item.url; date = item.date;
      } else {
        item = data[src] && data[src].latest && data[src].latest[0];
        if (!item) return;
        href = ytUrl(item.id); date = item.published;
      }
      a.href = href;
      a.querySelector(".tt").textContent = item.title;
      a.querySelector(".d").textContent = fmtDate(date);
    });
  }

  // グループごとの点数（トップの写真4枚の見出し）
  function fillGroupCounts(carry){
    if (!carry || !carry.groups) return;
    document.querySelectorAll("[data-count-group]").forEach(function(node){
      var g = carry.groups.filter(function(x){ return x.name === node.getAttribute("data-count-group"); })[0];
      if (g) node.textContent = String((g.items || []).length);
    });
  }

  // 持ちものページ：グループごとに品名の行（行全体が購入先へのリンク）
  function fillCarryFull(carry){
    document.querySelectorAll("[data-carry-group]").forEach(function(box){
      var name = box.getAttribute("data-carry-group");
      var g = carry && carry.groups && carry.groups.filter(function(x){ return x.name === name; })[0];
      if (!g) return;
      var head = box.querySelector("[data-carry-head]");
      if (head){
        head.textContent = g.name;
        head.appendChild(el("span", "n", String(g.items.length)));
      }
      var list = box.querySelector("[data-carry-rows]");
      if (!list) return;
      list.textContent = "";
      g.items.forEach(function(it){
        var li = el("li");
        var a = el("a", "row");
        a.href = it.url; a.target = "_blank"; a.rel = "noopener sponsored";
        a.appendChild(el("span", "br", it.brand));
        a.appendChild(el("span", "nm", it.name + " ↗"));
        a.appendChild(el("span", "d mono", fmtDate(it.since) + " から ・ " + (it.shop || "")));
        li.appendChild(a);
        list.appendChild(li);
      });
    });
  }

  // メディア掲載（site.json work.media）
  function fillMedia(site){
    var list = site && site.work && site.work.media;
    if (!list || !list.length) return;
    document.querySelectorAll("[data-media]").forEach(function(box){
      box.textContent = "";
      list.forEach(function(m){
        var row = el("div", "m");
        row.appendChild(el("span", "mono", fmtDate(m.date)));
        row.appendChild(document.createTextNode(m.text));
        box.appendChild(row);
      });
    });
  }

  // よく見られている動画（channel.json top）
  function fillTop(ch){
    var box = document.querySelector("[data-top]");
    if (!box || !ch || !ch.top) return;
    box.textContent = "";
    ch.top.forEach(function(v){
      var li = el("li");
      var a = el("a", "row");
      a.href = ytUrl(v.id); a.target = "_blank"; a.rel = "noopener";
      a.appendChild(el("span", "nm", v.title + " ↗"));
      a.appendChild(el("span", "d mono", fmtNum(v.views) + " 回 ・ " + fmtDate(v.published)));
      li.appendChild(a);
      box.appendChild(li);
    });
  }

  // メールのリンク（件名・本文つき）
  function fillMail(site){
    var m = site && site.work && site.work.mail;
    if (!m || !m.address) return;
    var href = "mailto:" + m.address + "?subject=" + encodeURIComponent(m.subject || "") +
      "&body=" + encodeURIComponent(m.body || "");
    document.querySelectorAll("[data-mail]").forEach(function(a){ a.href = href; });
  }

  /* --- ヘッダー：ヒーローを過ぎたら白い地に ----------------------------- */
  var hd = document.querySelector(".hd");
  var hero = document.querySelector(".hero");
  if (hd){
    if (!hero || !("IntersectionObserver" in window)){
      hd.classList.add("on");
    } else {
      new IntersectionObserver(function(es){
        es.forEach(function(e){ hd.classList.toggle("on", e.intersectionRatio < 0.2); });
      }, { threshold: [0, 0.2, 1] }).observe(hero);
    }
  }

  /* --- 出現 ------------------------------------------------------------- */
  var rvs = document.querySelectorAll(".rv");
  if ("IntersectionObserver" in window){
    var io = new IntersectionObserver(function(es){
      es.forEach(function(e){
        if (e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    rvs.forEach(function(n){ io.observe(n); });
  } else {
    rvs.forEach(function(n){ n.classList.add("in"); });
  }

  /* --- ストリップの送り -------------------------------------------------- */
  document.querySelectorAll("[data-strip]").forEach(function(nav){
    var strip = document.getElementById(nav.getAttribute("data-strip"));
    if (!strip) return;
    var prev = nav.querySelector("[data-dir='-1']");
    var next = nav.querySelector("[data-dir='1']");
    function step(){ var a = strip.querySelector("a"); return a ? a.getBoundingClientRect().width + 16 : 600; }
    // 動きを減らす設定のときは、送りもアニメーションさせない
    function how(){ return (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) ? "auto" : "smooth"; }
    function sync(){
      prev.disabled = strip.scrollLeft <= 2;
      next.disabled = strip.scrollLeft + strip.clientWidth >= strip.scrollWidth - 2;
    }
    prev.addEventListener("click", function(){ strip.scrollBy({ left: -step(), behavior: how() }); });
    next.addEventListener("click", function(){ strip.scrollBy({ left: step(), behavior: how() }); });
    // キーボードで次の1枚に移ったとき、写真ごと見える位置まで送る
    strip.addEventListener("focusin", function(e){
      var a = e.target.closest("a");
      if (a) a.scrollIntoView({ block: "nearest", inline: "start", behavior: how() });
    });
    strip.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    sync();
  });
})();
