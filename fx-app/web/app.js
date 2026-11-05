(() => {
  const API = "/api/v1";
  const PRIMARY = ["USD", "JPY", "HKD", "AUD", "EUR", "GBP", "KRW"];
  const STATUS_TXT = { live: "已接入", local_test: "待本地测试", app_only: "仅App/公众号", unknown: "待确认机构" };
  const $ = (s) => document.querySelector(s);
  const state = { currency: "USD", region: "mainland", channel: "spot", sort: { col: "buy", dir: "asc" },
                  data: null, currencies: [], open: new Set(), calcDir: "buy" };
  let timer;

  const fmt = (v) => (v == null ? "—" : v.toFixed(4));
  const money = (v) => v.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const ccyName = (c) => (state.currencies.find((x) => x.code === c) || {}).name || c;
  function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 1800); }

  // ------------------------------------------------ currency selector
  function renderCcy() {
    const g = $("#ccyGrid");
    const inPrimary = PRIMARY.includes(state.currency);
    g.innerHTML = PRIMARY.map((c) =>
      `<button data-c="${c}" class="${c === state.currency ? "on" : ""}">${ccyName(c)}</button>`).join("") +
      `<button class="more ${inPrimary ? "" : "on"}" id="moreBtn">${inPrimary ? "更多" : ccyName(state.currency)}</button>`;
    $("#moreGrid").innerHTML = state.currencies.map((c) =>
      `<button data-c="${c.code}" class="${c.code === state.currency ? "on" : ""}">${c.name}</button>`).join("");
  }
  $("#ccyGrid").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.id === "moreBtn") return openSheet("#moreSheet");
    setCurrency(b.dataset.c);
  });
  $("#moreGrid").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return; closeSheets(); setCurrency(b.dataset.c);
  });
  function setCurrency(c) { state.currency = c; state.open.clear(); renderCcy(); load(); }

  // ------------------------------------------------ toggles & sort
  function bindSwitch(sel, key, a, b) {
    const sw = $(sel);
    sw.addEventListener("click", (e) => {
      e.preventDefault();
      state[key] = state[key] === a ? b : a;
      const on = state[key] === b;
      sw.setAttribute("aria-checked", on);
      const [l, r] = [sw.previousElementSibling, sw.nextElementSibling];
      l.classList.toggle("on", !on); r.classList.toggle("on", on);
      load();
    });
  }
  bindSwitch("#swRegion", "region", "mainland", "hk");
  bindSwitch("#swChannel", "channel", "spot", "cash");

  document.querySelectorAll(".th-sort").forEach((b) => b.addEventListener("click", () => {
    const col = b.dataset.col, s = state.sort;
    if (s.col === col) s.dir = s.dir === "asc" ? "desc" : "asc";
    else { s.col = col; s.dir = col === "buy" ? "asc" : "desc"; }   // default: best first
    render();
  }));

  // ------------------------------------------------ data
  async function load() {
    clearTimeout(timer);
    try {
      const q = new URLSearchParams({ currency: state.currency, region: state.region, channel: state.channel });
      const r = await fetch(`${API}/rates?${q}`);
      if (!r.ok) throw new Error(r.status);
      state.data = await r.json();
      render();
      timer = setTimeout(load, (state.data.cache_ttl || 60) * 1000);
    } catch (e) {
      $("#rows").innerHTML = `<li class="empty-row">加载失败，请稍后重试</li>`;
      timer = setTimeout(load, 15000);
    }
  }

  function badge(rank) {
    return rank && rank <= 3 ? `<i class="badge r${rank}">${rank}</i>` : `<i class="badge ph"></i>`;
  }

  function render() {
    const d = state.data; if (!d) return;
    // central parity
    const p = $("#parity");
    if (d.central_parity) {
      p.hidden = false;
      $("#parityVal").textContent = `${ccyName(d.currency)} ${d.central_parity.price.toFixed(4)}`;
      $("#parityDate").textContent = d.central_parity.date;
    } else p.hidden = true;

    // sort headers
    document.querySelectorAll(".th-sort").forEach((b) => {
      b.classList.toggle("on", b.dataset.col === state.sort.col);
      b.classList.toggle("asc", b.dataset.col === state.sort.col && state.sort.dir === "asc");
      b.classList.toggle("desc", b.dataset.col === state.sort.col && state.sort.dir === "desc");
    });

    const rows = $("#rows");
    if (!d.banks.length) {
      rows.innerHTML = `<li class="empty-row">${d.region === "hk"
        ? "香港银行数据源尚在接入中<br><span class='muted'>（南洋、恒生等香港本地牌价）</span>"
        : `暂无银行挂牌 ${ccyName(d.currency)}`}</li>`;
      $("#meta").textContent = ""; return;
    }
    const { col, dir } = state.sort;
    const list = [...d.banks].sort((a, b) => {
      if (a[col] == null) return 1; if (b[col] == null) return -1;
      return dir === "asc" ? a[col] - b[col] : b[col] - a[col];
    });
    const bestBuy = Math.min(...d.banks.map((b) => b.buy).filter((v) => v != null));
    const bestSell = Math.max(...d.banks.map((b) => b.sell).filter((v) => v != null));
    const mid = d.central_parity && d.central_parity.price;

    let html = "";
    list.forEach((b, i) => {
      const diffBuy = b.buy != null ? ((b.buy - bestBuy) / 100 * 10000).toFixed(2) : null;
      const diffSell = b.sell != null ? ((bestSell - b.sell) / 100 * 10000).toFixed(2) : null;
      html += `<li class="${state.open.has(b.code) ? "open" : ""}" data-code="${b.code}">
        <button class="row">
          <span class="bname">${b.short}<i class="caret"></i>${b.source === "live" ? '<i class="tag live">实时</i>' : '<i class="tag demo">示例</i>'}</span>
          <span class="price ${b.buy == null ? "na" : ""}">${badge(b.buy_rank)}${fmt(b.buy)}</span>
          <span class="price ${b.sell == null ? "na" : ""}">${badge(b.sell_rank)}${fmt(b.sell)}</span>
        </button>
        <div class="detail"><dl>
          <dt>银行</dt><dd>${b.name}</dd>
          <dt>数据</dt><dd class="${b.source === "live" ? "" : "warn"}">${b.source === "live"
            ? `实时 · 银行发布于 ${b.published_at || "—"}`
            : `示例数据（${STATUS_TXT[b.status] || "未接入"}），非实时牌价`}</dd>
          ${diffBuy != null ? `<dt>购汇 1 万${ccyName(d.currency)}</dt><dd>${+diffBuy === 0 ? "全场最低" : `比最优多付 ¥${diffBuy}`}</dd>` : ""}
          ${diffSell != null ? `<dt>结汇 1 万${ccyName(d.currency)}</dt><dd>${+diffSell === 0 ? "全场最高" : `比最优少收 ¥${diffSell}`}</dd>` : ""}
          ${mid && b.buy != null ? `<dt>较中间价</dt><dd>购汇 +${(b.buy - mid).toFixed(2)} / 结汇 ${(b.sell - mid).toFixed(2)}</dd>` : ""}
        </dl></div></li>`;
    });
    rows.innerHTML = html;
    const live = d.banks.filter((b) => b.source === "live").length;
    $("#meta").textContent = `共 ${d.banks.length} 家 · 实时 ${live} 家 · 更新于 ${d.server_time.slice(11, 19)} · 每 ${d.cache_ttl} 秒刷新`;
    if (!$("#calcSheet").hidden) calc();
  }

  $("#rows").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-code]");
    if (li) { const c = li.dataset.code; state.open.has(c) ? state.open.delete(c) : state.open.add(c); li.classList.toggle("open"); }
  });

  // ------------------------------------------------ calculator
  function fillBanks() {
    const d = state.data; if (!d) return;
    const key = state.calcDir;
    const list = d.banks.filter((b) => b[key] != null)
      .sort((a, b) => key === "buy" ? a.buy - b.buy : b.sell - a.sell);
    const sel = $("#calcBank"), prev = sel.value;
    sel.innerHTML = list.map((b, i) => `<option value="${b.code}">${b.short}${i === 0 ? "（最优）" : ""} ${b[key].toFixed(4)}</option>`).join("");
    if (list.some((b) => b.code === prev)) sel.value = prev;
  }
  function calc() {
    const d = state.data; if (!d) return;
    const key = state.calcDir, amt = parseFloat($("#calcAmt").value) || 0;
    const name = ccyName(d.currency);
    $("#calcInUnit").textContent = name;
    $("#calcInLabel").textContent = key === "buy" ? "我想买" : "我要卖";
    $("#calcOutLabel").textContent = key === "buy" ? "需支付人民币" : "可得人民币";
    const banks = d.banks.filter((b) => b[key] != null);
    const b = banks.find((x) => x.code === $("#calcBank").value);
    if (!b) { $("#calcOut").textContent = "—"; $("#calcSave").textContent = ""; return; }
    const cny = amt * b[key] / 100;
    $("#calcOut").textContent = `¥${money(cny)}`;
    const worst = key === "buy" ? Math.max(...banks.map((x) => x.buy)) : Math.min(...banks.map((x) => x.sell));
    const save = Math.abs(amt * (worst - b[key]) / 100);
    $("#calcSave").textContent = save > 0.005 ? `比最差银行${key === "buy" ? "少花" : "多得"} ¥${money(save)}` : "";
  }
  $("#fab").addEventListener("click", () => {
    if (!state.data || !state.data.banks.length) return toast("暂无可用牌价");
    fillBanks(); calc(); openSheet("#calcSheet");
  });
  $("#calcDir").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.calcDir = b.dataset.v;
    $("#calcDir").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    $("#calcBank").value = ""; fillBanks(); calc();
  });
  $("#calcAmt").addEventListener("input", calc);
  $("#calcBank").addEventListener("change", calc);

  // ------------------------------------------------ sheets
  function openSheet(sel) { $("#mask").hidden = false; $(sel).hidden = false; }
  function closeSheets() { $("#mask").hidden = true; document.querySelectorAll(".sheet").forEach((s) => (s.hidden = true)); }
  $("#mask").addEventListener("click", closeSheets);
  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeSheets));

  // ------------------------------------------------ tabs
  const TITLES = { gold: "黄金", "rate-interest": "利率", tips: "经验" };
  document.querySelectorAll(".tabbar button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".tabbar button").forEach((x) => x.classList.toggle("on", x === b));
    const t = b.dataset.tab;
    $("#page-rate").hidden = t !== "rate";
    $("#page-mine").hidden = t !== "mine";
    $("#page-soon").hidden = !TITLES[t];
    if (TITLES[t]) $("#soonTitle").textContent = TITLES[t];
    if (t === "mine") loadSources();
    window.scrollTo(0, 0);
  }));
  $("#loginBtn").addEventListener("click", () => toast("H5 原型：小程序内调用 wx.login 完成登录"));

  async function loadSources() {
    const list = await (await fetch(`${API}/sources`)).json();
    const live = list.filter((s) => s.status === "live").length;
    $("#srcCount").textContent = `${live}/${list.length} 已接入`;
    $("#srcList").innerHTML = list.map((s) =>
      `<li class="${s.status === "live" ? "live" : "red"}"><i class="dot ${s.status === "live" ? "live" : "red"}" style="margin:0"></i>${s.short}<em>${STATUS_TXT[s.status]}</em></li>`).join("");
  }

  // ------------------------------------------------ boot
  (async () => {
    try { state.currencies = await (await fetch(`${API}/currencies`)).json(); } catch { state.currencies = []; }
    renderCcy(); load();
  })();
})();
