/* ==========================================================================
   4.5room — かばんの中身ページ 共通スクリプト
   やることは2つだけ。
   1. ページ全体のフェードイン
   2. .rv を画面に入った順に立ち上げる
   JSが動かない環境では .js-rv が付かないので、全文がそのまま出る。
   ========================================================================== */
(function () {
  var root = document.documentElement;

  try {
    if (!('IntersectionObserver' in window)) { throw new Error('IntersectionObserver unsupported'); }
    root.classList.add('js-rv');
  } catch (e) {
    return;
  }

  function start() {
    document.body.classList.add('ready');

    var io = new IntersectionObserver(function (entries) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].isIntersecting) {
          entries[i].target.classList.add('in');
          io.unobserve(entries[i].target);
        }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.01 });

    var rvs = document.querySelectorAll('.rv');
    for (var i = 0; i < rvs.length; i++) { io.observe(rvs[i]); }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}());
