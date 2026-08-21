
(function(){
  var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
  if(!tiles.length) return;
  var lb = document.getElementById('lightbox');
  var lbImg = document.getElementById('lbImg');
  var lbText = document.getElementById('lbText');
  var current = -1;
  function render(){
    var t = tiles[current];
    lbImg.src = t.dataset.full;
    lbImg.alt = t.dataset.caption;
    lbText.textContent = t.dataset.caption;
  }
  function open(idx){ current = idx; render(); lb.classList.add('open'); lb.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
  function close(){ lb.classList.remove('open'); lb.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  function step(d){ current = (current + d + tiles.length) % tiles.length; render(); }
  tiles.forEach(function(t, i){ t.addEventListener('click', function(){ open(i); }); });
  document.getElementById('lbClose').addEventListener('click', close);
  document.getElementById('lbPrev').addEventListener('click', function(){ step(-1); });
  document.getElementById('lbNext').addEventListener('click', function(){ step(1); });
  lb.addEventListener('click', function(e){ if(e.target === lb) close(); });
  document.addEventListener('keydown', function(e){
    if(!lb.classList.contains('open')) return;
    if(e.key === 'Escape') close();
    if(e.key === 'ArrowRight') step(1);
    if(e.key === 'ArrowLeft') step(-1);
  });
})();
