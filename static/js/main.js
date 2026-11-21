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
  if (canvas && window.chartLabels && window.chartCurrentYear && window.chartPrevYear) {
    renderSalesChart(canvas, window.chartLabels, window.chartCurrentYear, window.chartPrevYear);
  }
});

function renderSalesChart(canvas, labels, currentData, prevData) {
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  const padding = 45;

  ctx.clearRect(0, 0, width, height);

  const maxVal = Math.max(...currentData, ...prevData, 5000);
  const chartHeight = height - padding * 2;
  const chartWidth = width - padding * 2;
  const stepX = chartWidth / (labels.length - 1);

  // Background Grid Lines
  ctx.strokeStyle = '#E5E7EB';
  ctx.lineWidth = 1;
  const gridRows = 4;
  for (let i = 0; i <= gridRows; i++) {
    const y = padding + (chartHeight / gridRows) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();

    // Labels
    const val = maxVal - (maxVal / gridRows) * i;
    ctx.fillStyle = '#9CA3AF';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('R$ ' + Math.round(val), padding - 8, y + 3);
  }

  // X Labels
  ctx.textAlign = 'center';
  labels.forEach((lbl, idx) => {
    const x = padding + stepX * idx;
    ctx.fillText(lbl, x, height - padding + 18);
  });

  // Draw Line Function
  function drawLine(data, color, isDashed) {
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    if (isDashed) {
      ctx.setLineDash([4, 4]);
    } else {
      ctx.setLineDash([]);
    }

    data.forEach((val, idx) => {
      const x = padding + stepX * idx;
      const y = padding + chartHeight - (val / maxVal) * chartHeight;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw Points
    data.forEach((val, idx) => {
      const x = padding + stepX * idx;
      const y = padding + chartHeight - (val / maxVal) * chartHeight;
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  // Previous year (grey dashed)
  drawLine(prevData, '#94A3B8', true);
  // Current year (solid emerald)
  drawLine(currentData, '#10B981', false);
}
