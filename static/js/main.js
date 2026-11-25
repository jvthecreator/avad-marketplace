// AVaD Marketplace - Vanilla JS Utilities

document.addEventListener('DOMContentLoaded', function () {
  // 1. Freight Calculator (Product Detail)
  const btnCalcFrete = document.getElementById('btn-calc-frete');
  const inputCep = document.getElementById('input-cep-calc');
  const freteResults = document.getElementById('frete-results');

  if (btnCalcFrete && inputCep) {
    btnCalcFrete.addEventListener('click', function () {
      const cep = inputCep.value.trim().replace(/\D/g, '');
      if (cep.length < 8) {
        alert('Por favor, informe um CEP válido com 8 dígitos.');
        return;
      }
      const prodId = inputCep.dataset.productId;
      btnCalcFrete.innerText = 'Calculando...';
      btnCalcFrete.disabled = true;

      fetch(`/catalog/calculate-frete/?cep=${cep}&product_id=${prodId}`)
        .then(res => res.json())
        .then(data => {
          btnCalcFrete.innerText = 'Calcular frete';
          btnCalcFrete.disabled = false;
          if (data.options) {
            let html = '<div style="margin-top: 12px; border-top: 1px solid #E5E7EB; padding-top: 12px;">';
            data.options.forEach(opt => {
              html += `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; font-size: 13px;">
                  <div>
                    <strong>${opt.method}</strong>
                    <div style="color: #6B7280; font-size: 11px;">Chegará em até ${opt.days} dias úteis</div>
                  </div>
                  <div style="font-weight: 700; color: ${opt.price_value === 0 ? '#10B981' : '#111827'};">
                    ${opt.price}
                  </div>
                </div>
              `;
            });
            html += '</div>';
            freteResults.innerHTML = html;
          }
        })
        .catch(err => {
          btnCalcFrete.innerText = 'Calcular frete';
          btnCalcFrete.disabled = false;
          alert('Erro ao calcular frete. Tente novamente.');
        });
    });
  }

  // 2. Quantity selector (- 1 +)
  const btnMinus = document.getElementById('qty-minus');
  const btnPlus = document.getElementById('qty-plus');
  const inputQty = document.getElementById('qty-input');
  const linkBuy = document.getElementById('btn-buy-now');

  if (btnMinus && btnPlus && inputQty) {
    const updateLinks = () => {
      let val = parseInt(inputQty.value) || 1;
      if (val < 1) val = 1;
      inputQty.value = val;
      if (linkBuy) {
        const baseHref = linkBuy.dataset.baseHref;
        linkBuy.href = `${baseHref}?qtd=${val}`;
      }
    };
    btnMinus.addEventListener('click', () => {
      let v = parseInt(inputQty.value) || 1;
      if (v > 1) {
        inputQty.value = v - 1;
        updateLinks();
      }
    });
    btnPlus.addEventListener('click', () => {
      let v = parseInt(inputQty.value) || 1;
      const max = parseInt(inputQty.getAttribute('max')) || 999;
      if (v < max) {
        inputQty.value = v + 1;
        updateLinks();
      }
    });
    inputQty.addEventListener('change', updateLinks);
  }

  // 3. Checkout Payment Method Tabs
  const paymentRadios = document.querySelectorAll('input[name="forma_pagamento"]');
  const sectionCartao = document.getElementById('payment-section-cartao');
  const sectionPix = document.getElementById('payment-section-pix');
  const sectionBoleto = document.getElementById('payment-section-boleto');

  if (paymentRadios.length > 0) {
    const togglePaymentSections = () => {
      const selected = document.querySelector('input[name="forma_pagamento"]:checked')?.value;
      if (sectionCartao) sectionCartao.style.display = (selected === 'cartao') ? 'block' : 'none';
      if (sectionPix) sectionPix.style.display = (selected === 'pix') ? 'block' : 'none';
      if (sectionBoleto) sectionBoleto.style.display = (selected === 'boleto') ? 'block' : 'none';
    };
    paymentRadios.forEach(r => r.addEventListener('change', togglePaymentSections));
    togglePaymentSections();
  }

  // 4. Interactive Star Rating (PRO009)
  const setupStarRating = (widgetId, hiddenInputId, clearLinkId) => {
    const widget = document.getElementById(widgetId);
    const hiddenInput = document.getElementById(hiddenInputId);
    const clearLink = document.getElementById(clearLinkId);

    if (!widget || !hiddenInput) return;

    const stars = widget.querySelectorAll('.star');

    const setStars = (rating) => {
      hiddenInput.value = rating;
      stars.forEach((s, idx) => {
        if (idx < rating) {
          s.classList.add('active');
          s.innerHTML = '★';
        } else {
          s.classList.remove('active');
          s.innerHTML = '☆';
        }
      });
    };

    stars.forEach(star => {
      star.addEventListener('click', function () {
        const rating = parseInt(this.dataset.value);
        setStars(rating);
      });
    });

    if (clearLink) {
      clearLink.addEventListener('click', function (e) {
        e.preventDefault();
        setStars(0);
      });
    }

    setStars(parseInt(hiddenInput.value) || 0);
  };

  setupStarRating('star-widget-seller', 'nota_vendedor', 'clear-star-seller');
  setupStarRating('star-widget-shipping', 'nota_transporte', 'clear-star-shipping');

  // 5. Mediation Tabs (PRO007)
  const tabButtons = document.querySelectorAll('.mediation-tab-btn');
  const tabPanes = document.querySelectorAll('.mediation-tab-pane');

  if (tabButtons.length > 0) {
    tabButtons.forEach(btn => {
      btn.addEventListener('click', function () {
        tabButtons.forEach(b => b.classList.remove('active'));
        tabPanes.forEach(p => p.style.display = 'none');
        this.classList.add('active');
        const targetId = this.dataset.target;
        const targetPane = document.getElementById(targetId);
        if (targetPane) targetPane.style.display = 'block';
      });
    });
  }

  // 6. Canvas Sales Evolution Chart (PRO012 Dashboard)
  const canvas = document.getElementById('salesEvolutionChart');
  const chartDataEl = document.getElementById('sales-chart-data');
  if (canvas && chartDataEl) {
    const chartData = JSON.parse(chartDataEl.textContent);
    const draw = () => renderSalesChart(canvas, chartData.labels, chartData.atual, chartData.anterior);
    draw();
    let resizeTimer;
    window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(draw, 150); });
  }
});

// Gráfico de linhas do painel do vendedor.
// currentData/prevData: arrays de números (null = sem ponto, ex.: dias que ainda não chegaram). prevData pode ser null.
function renderSalesChart(canvas, labels, currentData, prevData) {
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 650;
  const height = canvas.clientHeight || 250;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const padLeft = 78, padRight = 20, padTop = 16, padBottom = 30;
  const chartWidth = width - padLeft - padRight;
  const chartHeight = height - padTop - padBottom;
  const n = labels.length;
  // Sem série de comparação (modo "desde o começo") o gráfico vira barras, uma por ano
  const barMode = !prevData;
  const band = chartWidth / Math.max(n, 1);
  const xAt = (idx) => barMode ? padLeft + band * (idx + 0.5)
    : (n > 1 ? padLeft + (chartWidth / (n - 1)) * idx : padLeft + chartWidth / 2);

  // Escala com intervalos "redondos" (1, 2, 2,5 ou 5 x potência de 10) a partir do maior valor real
  const values = [...currentData, ...(prevData || [])].filter((v) => v !== null && v !== undefined);
  const rawMax = Math.max(0, ...values);
  const niceStep = (target) => {
    const exp = Math.pow(10, Math.floor(Math.log10(target)));
    const f = target / exp;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * exp;
  };
  const step = rawMax > 0 ? niceStep(rawMax / 4) : 25;
  const gridRows = rawMax > 0 ? Math.max(1, Math.ceil(rawMax / step - 1e-9)) : 4;
  const niceMax = step * gridRows;
  const yAt = (val) => padTop + chartHeight - (val / niceMax) * chartHeight;
  const decimals = Number.isInteger(step) ? 0 : 2;
  const brl = (v) => 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

  // Linhas de grade + rótulos do eixo Y
  ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  for (let i = 0; i <= gridRows; i++) {
    const val = step * (gridRows - i);
    const y = yAt(val);
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
    ctx.stroke();
    ctx.fillStyle = '#9CA3AF';
    ctx.textAlign = 'right';
    ctx.fillText(brl(val), padLeft - 10, y + 4);
  }

  // Rótulos do eixo X (pula alguns quando há muitos, ex.: 31 dias / 24 horas)
  const maxLabels = Math.max(2, Math.floor(chartWidth / 40));
  const every = Math.ceil(n / maxLabels);
  ctx.textAlign = 'center';
  ctx.fillStyle = '#9CA3AF';
  labels.forEach((lbl, idx) => {
    if (idx % every === 0 || idx === n - 1) ctx.fillText(lbl, xAt(idx), height - padBottom + 18);
  });

  function drawLine(data, color, isDashed) {
    if (!data) return;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.setLineDash(isDashed ? [5, 5] : []);
    ctx.beginPath();
    let started = false;
    data.forEach((val, idx) => {
      if (val === null || val === undefined) { started = false; return; }
      const x = xAt(idx), y = yAt(val);
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    });
    ctx.stroke();
    ctx.setLineDash([]);

    const radius = n > 20 ? 2.5 : 4;
    data.forEach((val, idx) => {
      if (val === null || val === undefined) return;
      ctx.beginPath();
      ctx.arc(xAt(idx), yAt(val), radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  if (barMode) {
    const barWidth = Math.min(64, band * 0.6);
    currentData.forEach((val, idx) => {
      if (val === null || val === undefined) return;
      const x = xAt(idx) - barWidth / 2, y = yAt(val);
      ctx.fillStyle = '#10B981';
      ctx.fillRect(x, y, barWidth, padTop + chartHeight - y);
      ctx.fillStyle = '#374151';
      ctx.textAlign = 'center';
      ctx.fillText('R$ ' + val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }), xAt(idx), y - 6);
    });
    return;
  }

  drawLine(prevData, '#94A3B8', true);      // período anterior (cinza tracejado)
  drawLine(currentData, '#10B981', false);  // período atual (verde)
}
