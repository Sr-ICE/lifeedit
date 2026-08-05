/* =========================================================================
   4.5room — 共通スクリプト
   ・assets/stats.json（YouTube Data API の実測値）を読んでページに流し込む
   ・HTMLに数値を直書きしないためのしくみ。更新は scripts/update_stats.sh
   ========================================================================= */
(function () {
  'use strict';

  var here = document.currentScript && document.currentScript.src;
  var STATS_URL = new URL('stats.json', here || location.href).href;

  /* --- 表示フォーマット -------------------------------------------------- */
  var fmt = {
    comma: function (n) { return Number(n).toLocaleString('ja-JP'); },
    // 12345 → 1.2万 / 1240828 → 124万
    man: function (n) {
      n = Number(n);
      if (n < 10000) { return n.toLocaleString('ja-JP'); }
      var m = n / 10000;
      return (m >= 100 ? Math.round(m) : m.toFixed(1).replace(/\.0$/, '')) + '<span class="u">万</span>';
    },
    date: function (s) { return String(s).replace(/-/g, '.'); },
    // "2022-12-14" → 4（＝4年目）
    year_nth: function (s) {
      var d = new Date(s), now = new Date();
      var y = now.getFullYear() - d.getFullYear();
      var before = now.getMonth() < d.getMonth() ||
                   (now.getMonth() === d.getMonth() && now.getDate() < d.getDate());
      return (before ? y : y + 1) + '<span class="u">年目</span>';
    }
  };

  function dig(obj, path) {
    return path.split('.').reduce(function (o, k) {
      return (o === null || o === undefined) ? o : o[k];
    }, obj);
  }

  /* --- 経過期間ピル（data-since="2026-05"） ------------------------------ */
  function elapsed(since) {
    var p = String(since).split('-');
    var from = new Date(Number(p[0]), Number(p[1] || 1) - 1, Number(p[2] || 1));
    var now = new Date();
    var months = (now.getFullYear() - from.getFullYear()) * 12 + (now.getMonth() - from.getMonth());
    if (months < 1) { return '今月から'; }
    if (months < 12) { return months + 'ヶ月'; }
    var y = Math.floor(months / 12), m = months % 12;
    return y + '年' + (m ? m + 'ヶ月' : '');
  }

  function renderSince() {
    document.querySelectorAll('[data-since]').forEach(function (el) {
      var since = el.getAttribute('data-since');
      el.innerHTML = fmt.date(since) + '〜 <b>' + elapsed(since) + '</b>';
    });
  }

  /* --- 実測値の流し込み --------------------------------------------------- */
  function renderStats(data) {
    document.querySelectorAll('[data-stat]').forEach(function (el) {
      var v = dig(data, el.getAttribute('data-stat'));
      if (v === null || v === undefined) { return; }
      var f = fmt[el.getAttribute('data-fmt') || 'comma'];
      el.innerHTML = f ? f(v) : String(v);
      el.classList.remove('is-loading');
    });
  }

  /* --- 動画リスト ----------------------------------------------------------
     サムネイルは使わない（概要欄由来の煽り文字が焼き込まれているため）。
     data-videos="3"  … 最新3本
     data-top="3"     … よく見られている3本（再生数つき）
     ------------------------------------------------------------------------ */
  function row(v, withViews) {
    var right = withViews && v.views != null
      ? fmt.comma(v.views) + ' 回再生'
      : 'YouTube ↗';
    return '<a href="https://www.youtube.com/watch?v=' + v.id + '"' +
           ' target="_blank" rel="noopener">' +
           '<span class="d">' + fmt.date(v.published) + '</span>' +
           '<div><h3>' + esc(v.title) + '</h3></div>' +
           '<span class="r">' + right + '</span></a>';
  }

  function renderList(data, attr, key, withViews) {
    var host = document.querySelector('[' + attr + ']');
    var list = data[key];
    if (!host || !list) { return; }
    var n = Number(host.getAttribute(attr)) || 3;
    host.innerHTML = list.slice(0, n).map(function (v) { return row(v, withViews); }).join('');
  }

  function renderVideos(data) {
    renderList(data, 'data-videos', 'latest_videos', false);
    renderList(data, 'data-top', 'top_videos', true);
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c];
    });
  }

  /* --- 起動 ----------------------------------------------------------------- */
  renderSince();
  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  fetch(STATS_URL, { cache: 'no-cache' })
    .then(function (r) {
      if (!r.ok) { throw new Error('stats.json ' + r.status); }
      return r.json();
    })
    .then(function (data) { renderStats(data); renderVideos(data); })
    .catch(function (e) {
      // 数値は出さない（古い値・でたらめな値を出さないため「—」のまま）
      console.warn('[4.5room] 実測値を読み込めませんでした:', e.message,
                   '— file:// で開いた場合はローカルサーバー経由で確認してください。');
    });
})();
