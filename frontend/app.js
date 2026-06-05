let generoAtivo = "";
let tipoAtivo   = "";
let buscaTimer  = null;

async function carregarGeneros() {
  const params = tipoAtivo ? `?tipo=${tipoAtivo}` : "";
  const r    = await fetch(`/api/generos${params}`);
  const data = await r.json();
  const list = document.getElementById("generos-list");
  list.innerHTML = "";

  data.forEach(g => {
    const btn = document.createElement("button");
    btn.className    = "genre-btn";
    btn.dataset.genero = g.genero;
    const label = g.genero === "Horror Cosmico" ? "🐙 Horror Cósmico" : g.genero;
    btn.innerHTML    = `${label} <span class="count">${g.total}</span>`;
    btn.onclick      = () => selecionarGenero(g.genero, btn);
    list.appendChild(btn);
  });

  const total = data.reduce((s, g) => s + g.total, 0);
  document.getElementById("count-total").textContent = total;
}

function selecionarGenero(genero, btnEl) {
  generoAtivo = genero;
  document.querySelectorAll(".genre-btn").forEach(b => b.classList.remove("active"));
  btnEl.classList.add("active");
  carregarFilmes();
}

async function carregarFilmes() {
  if (tipoAtivo === "serie") {
    await carregarSeries();
    return;
  }

  const busca  = document.getElementById("busca").value.trim();
  const params = new URLSearchParams();
  if (generoAtivo) params.set("genero", generoAtivo);
  if (busca)       params.set("busca",  busca);
  if (tipoAtivo)   params.set("tipo",   tipoAtivo);

  const grid  = document.getElementById("grid");
  const empty = document.getElementById("no-results");
  grid.innerHTML = "";

  // Filmes/docs
  const rFilmes = await fetch(`/api/filmes?${params}`);
  const filmes  = await rFilmes.json();

  // Agrupa por titulo_pt — um card por título, guarda todas as versões
  const porTitulo = new Map();
  for (const f of filmes) {
    if (!porTitulo.has(f.titulo_pt)) {
      porTitulo.set(f.titulo_pt, { ...f, _versoes: [] });
    }
    const grupo = porTitulo.get(f.titulo_pt);
    // Prefere poster que não seja da pasta _organizer
    const melhorPoster = p => p && !p.includes("_organizer");
    if (f.poster_local && (!grupo.poster_local || (!melhorPoster(grupo.poster_local) && melhorPoster(f.poster_local)))) {
      grupo.poster_local = f.poster_local;
    }
    if (!grupo._versoes.some(v => v.arquivo_novo === f.arquivo_novo)) {
      grupo._versoes.push({ id: f.id, arquivo_novo: f.arquivo_novo, idioma: f.idioma });
    }
  }
  const unicos = [...porTitulo.values()];

  // Séries (modo Todos)
  let seriesCards = [];
  if (!tipoAtivo) {
    const rSeries = await fetch("/api/series");
    const series  = await rSeries.json();
    seriesCards = series.filter(s =>
      (!generoAtivo || s.genero === generoAtivo) &&
      (!busca || (s.titulo_pt || "").toLowerCase().includes(busca.toLowerCase()))
    );
  }

  // Coleções de documentários
  let docsCards = [];
  if (!tipoAtivo || tipoAtivo === "documentario") {
    const rDocs = await fetch("/api/colecoes");
    const docs  = await rDocs.json();
    docsCards = docs.filter(d =>
      (!generoAtivo || d.genero === generoAtivo) &&
      (!busca || d.colecao.toLowerCase().includes(busca.toLowerCase()))
    );
  }

  const total = unicos.length + seriesCards.length + docsCards.length;
  const label = generoAtivo || "Todos";
  document.getElementById("section-title").textContent = `${label} (${total})`;

  if (!total) { empty.style.display = "block"; return; }
  empty.style.display = "none";

  unicos.forEach(f => grid.appendChild(criarCard(f)));
  seriesCards.forEach(s => grid.appendChild(criarCardSerie(s)));
  docsCards.forEach(d => grid.appendChild(criarCardColecao(d)));
}

async function carregarSeries() {
  const grid  = document.getElementById("grid");
  const empty = document.getElementById("no-results");
  grid.innerHTML = "";

  const r    = await fetch("/api/series");
  const data = await r.json();

  const busca = document.getElementById("busca").value.trim().toLowerCase();
  const lista = data.filter(s =>
    (!generoAtivo || s.genero === generoAtivo) &&
    (!busca || (s.titulo_pt || "").toLowerCase().includes(busca))
  );

  document.getElementById("section-title").textContent = `Séries (${lista.length})`;

  if (!lista.length) { empty.style.display = "block"; return; }
  empty.style.display = "none";
  lista.forEach(s => grid.appendChild(criarCardSerie(s)));
}

function criarCardSerie(s) {
  const div = document.createElement("div");
  div.className = "card";
  div.onclick   = () => location.href = `/series?pasta=${encodeURIComponent(s.pasta)}&nome=${encodeURIComponent(s.titulo_pt)}`;

  const posterHtml = s.poster_local
    ? `<img class="card-poster" src="/poster?path=${encodeURIComponent(s.poster_local)}"
           alt="${s.titulo_pt}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
    : "";
  const fallback = `<div class="card-poster-fallback" ${s.poster_local ? 'style="display:none"' : ""}>📺</div>`;

  div.innerHTML = `
    ${posterHtml}${fallback}
    <div class="card-info">
      <div class="card-title">${s.titulo_pt || "Sem título"}</div>
      <div class="card-year">${s.ano || ""} · ${s.total_eps} ep</div>
    </div>`;
  return div;
}

function criarCard(f) {
  const div = document.createElement("div");
  div.className = "card";
  const versoes = f._versoes || [{ id: f.id }];
  if (versoes.length > 1) {
    div.onclick = () => location.href = `/filme?titulo=${encodeURIComponent(f.titulo_pt)}`;
  } else {
    div.onclick = () => location.href = `/player?id=${versoes[0].id}`;
  }

  const posterHtml = f.poster_local
    ? `<img class="card-poster" src="/poster?path=${encodeURIComponent(f.poster_local)}"
           alt="${f.titulo_pt || f.titulo}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
    : "";
  const fallback = `<div class="card-poster-fallback" ${f.poster_local ? 'style="display:none"' : ""}>🎬</div>`;
  const horror   = f.subgenero === "Horror Cosmico"
    ? `<span class="badge-horror">🐙</span>` : "";

  div.innerHTML = `
    ${posterHtml}${fallback}
    ${horror}
    <div class="card-info">
      <div class="card-title">${f.titulo_pt || f.titulo || "Sem título"}</div>
      <div class="card-year">${f.ano || ""} · ${f.genero || ""}</div>
    </div>
  `;
  return div;
}

function criarCardColecao(d) {
  const div = document.createElement("div");
  div.className = "card";
  div.onclick   = () => location.href = `/documentario?colecao=${encodeURIComponent(d.colecao)}`;

  const posterHtml = d.poster_local
    ? `<img class="card-poster" src="/poster?path=${encodeURIComponent(d.poster_local)}"
           alt="${d.colecao}" loading="lazy"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
    : "";
  const fallback = `<div class="card-poster-fallback" ${d.poster_local ? 'style="display:none"' : ""}>📽️</div>`;

  div.innerHTML = `
    ${posterHtml}${fallback}
    <div class="card-info">
      <div class="card-title">${d.colecao}</div>
      <div class="card-year">${d.genero || ""} · ${d.total} ep</div>
    </div>`;
  return div;
}

// Eventos
document.getElementById("busca").addEventListener("input", () => {
  clearTimeout(buscaTimer);
  buscaTimer = setTimeout(carregarFilmes, 300);
});

document.getElementById("tipo-filter").addEventListener("change", e => {
  tipoAtivo = e.target.value;
  generoAtivo = "";
  carregarGeneros();
  carregarFilmes();
});

document.querySelector(".genre-btn[data-genero='']").addEventListener("click", function() {
  selecionarGenero("", this);
});

// Init
carregarGeneros();
carregarFilmes();
