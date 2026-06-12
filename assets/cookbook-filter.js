// Cookbook index — client-side category chips + search filter.
(function () {
  var search = document.querySelector('.cb-search');
  var chips = Array.prototype.slice.call(document.querySelectorAll('.cb-chip'));
  var cats = Array.prototype.slice.call(document.querySelectorAll('.cb-cat'));
  var empty = document.querySelector('.cb-empty');
  if (!cats.length) return;

  var activeCat = 'all';

  function apply() {
    var q = (search && search.value || '').trim().toLowerCase();
    var anyVisible = false;
    cats.forEach(function (cat) {
      var catName = cat.getAttribute('data-cat');
      var catMatch = activeCat === 'all' || activeCat === catName;
      var cards = Array.prototype.slice.call(cat.querySelectorAll('.cb-card'));
      var shown = 0;
      cards.forEach(function (card) {
        var hay = card.getAttribute('data-search') || '';
        var match = catMatch && (!q || hay.indexOf(q) !== -1);
        card.style.display = match ? '' : 'none';
        if (match) shown++;
      });
      cat.style.display = shown ? '' : 'none';
      if (shown) anyVisible = true;
    });
    if (empty) empty.hidden = anyVisible;
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      chips.forEach(function (c) { c.classList.remove('cb-chip-on'); });
      chip.classList.add('cb-chip-on');
      activeCat = chip.getAttribute('data-cat');
      apply();
    });
  });
  if (search) search.addEventListener('input', apply);
  apply();
})();
