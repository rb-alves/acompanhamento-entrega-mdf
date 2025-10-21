// ============================================================
// 🟢 Consulta de pedidos por CPF
// ============================================================
document.getElementById("consultar").addEventListener("click", async () => {
  const botao = document.getElementById("consultar");
  const cpf = document.getElementById("cpf").value.trim();
  const resultado = document.getElementById("resultado");
  resultado.innerHTML = "";

  if (!cpf) {
    resultado.innerHTML = `
      <div class="text-center mt-4">
        <p class="text-danger fw-semibold">Por favor, digite um CPF válido.</p>
      </div>`;
    return;
  }

  // Bloqueia o botão enquanto os dados carregam
  botao.disabled = true;
  botao.classList.add("disabled", "opacity-75");
  const textoOriginal = botao.innerHTML;
  botao.innerHTML = `
    Consultando...
  `;


  resultado.innerHTML = `
    <div class="text-center mt-4">
      <div class="spinner-border text-secondary" role="status"></div>
      <p class="text-muted mt-2 fw-semibold">Buscando pedidos...</p>
    </div>`;

  try {
    const response = await fetch(`/api/pedidos?cpf=${cpf}`);
    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      resultado.innerHTML = `
        <div class="text-center mt-4">
          <p class="text-secondary fw-semibold">Nenhum pedido encontrado.</p>
        </div>`;
      return;
    }

    // Cabeçalho
    let html = `
      <div class="mt-2 mx-auto" style="max-width: 650px;">
        <h5 class="fw-bold pb-2 mb-4 border-bottom">Pedidos Encontrados (${data.length})</h5>
    `;

    // Cards de pedidos
    data.forEach(pedido => {
      let badgeClass = "bg-secondary";
      const situacao = pedido.situacao_pedido?.toLowerCase() || "";

        switch (situacao) {
            case "confirmado":
                badgeClass = "bg-primary";
                break;

            case "faturado":
                badgeClass = "bg-info text-dark";
                break;

            case "separando":
                badgeClass = "bg-warning text-dark";
                break;

            case "reagendamento de entrega":
                badgeClass = "bg-secondary";
                break;

            case "saiu para a entrega":
                badgeClass = "bg-dark text-white";
                break;

            case "entregue":
                badgeClass = "bg-success";
                break;

            case "não entregue":
                badgeClass = "bg-danger";
                break;

            case "montado":
                badgeClass = "bg-success";
                break;

            case "não montado":
                badgeClass = "bg-danger";
                break;
        }

      html += `
        <div class="card shadow-sm mb-3 border-0 rounded-4 cor-card">
          <div class="card-body d-flex justify-content-between align-items-center">
            <div>
              <p class="mb-1 text-muted small">Pedido: ${pedido.pedido}</p>
              <h5 class="fw-bold mb-1">R$ ${(pedido.valor / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</h5>
              <p class="text-muted small mb-0">Data: ${pedido.data}</p>
              <p class="text-muted small mb-0">Última atualização: ${pedido.data_situacao || '—'}</p>
            </div>
            <div class="text-end">
              <span class="badge ${badgeClass} rounded-pill mb-2 px-3 py-2">${pedido.situacao_pedido}</span>
              <br>
              <a 
                href="#" 
                class="btn btn-link btn-sm text-decoration-none text-secondary fw-semibold"
                data-bs-toggle="modal"
                data-bs-target="#verDetalhes"
                data-loja="${pedido.loja}"
                data-pedido="${pedido.pedido}"
                data-cpf="${cpf}">
                Ver Detalhes →
              </a>
            </div>
          </div>
        </div>
      `;
    });

    html += `</div>`;
    resultado.innerHTML = html;

  } catch (error) {
    console.error(error);
    resultado.innerHTML = `
      <div class="text-center mt-4">
        <p class="text-danger fw-semibold">Erro ao buscar pedidos. Tente novamente.</p>
      </div>`;
  } finally {
      // DESBLOQUEIA o botão no final (sempre)
      botao.disabled = false;
      botao.classList.remove("disabled", "opacity-75");
      botao.innerHTML = textoOriginal;
  }
});

// ============================================================
// 🧾 Formatação de valores monetários
// ============================================================
function formatarValor(valor) {
  return (valor / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
}

// ============================================================
// 🔍 Modal de detalhes do pedido
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById('verDetalhes');
  if (!modal) return;

  modal.addEventListener('show.bs.modal', async event => {
    const botao = event.relatedTarget;
    const loja = botao.getAttribute('data-loja');
    const pedido = botao.getAttribute('data-pedido');
    const cpf = botao.getAttribute('data-cpf');

    document.getElementById('modal-loader').classList.remove('d-none');
    document.getElementById('modal-content-body').classList.add('d-none');
    document.getElementById('modal-error').classList.add('d-none');

    try {
      const resp = await fetch(`/api/detalhes?cpf=${cpf}&loja=${loja}&pedido=${pedido}`);
      const info = await resp.json();

      if (!resp.ok || info.error) throw new Error(info.error || 'Erro ao carregar detalhes');

      // Info principal
      document.getElementById('m-loja').textContent = info.loja;
      document.getElementById('m-pedido').textContent = info.pedido;
      document.getElementById('m-cliente').textContent = info.cliente || '—';
      document.getElementById('m-data').textContent = info.data || '—';
      document.getElementById('m-valor').textContent = formatarValor(Number(info.valor) || 0);

      // Última situação
      document.getElementById('m-situacao').textContent = info.etapas?.length
        ? info.etapas[info.etapas.length - 1].situacao
        : '—';

      // Itens
      const tbody = document.getElementById('m-itens');
      tbody.innerHTML = "";
      if (info.itens?.length) {
        info.itens.forEach(i => {
          tbody.innerHTML += `
            <tr>
              <td>${i.produto || i.item}</td>
              <td class="text-end">${i.quantidade / 1000}</td>
              <td class="text-end">R$ ${formatarValor(Number(i.preco))}</td>
            </tr>`;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Nenhum item encontrado</td></tr>`;
      }

      // Histórico / Etapas
      const etapasDiv = document.getElementById("m-etapas");
      etapasDiv.innerHTML = "";
      if (info.etapas?.length) {
        info.etapas.forEach((e, index) => {
          etapasDiv.innerHTML += `
            <div class="timeline-step">
              <div class="fw-semibold">${e.situacao}</div>
              <div class="text-muted small">${e.data_formatada || '—'}</div>
            </div>
            ${index < info.etapas.length - 1 ? '<hr class="my-2">' : ""}`;
        });
      } else {
        etapasDiv.innerHTML = `<p class="text-muted">Nenhuma etapa encontrada</p>`;
      }

      document.getElementById('modal-loader').classList.add('d-none');
      document.getElementById('modal-content-body').classList.remove('d-none');

    } catch (err) {
      console.error(err);
      document.getElementById('modal-loader').classList.add('d-none');
      const modalError = document.getElementById('modal-error');
      modalError.textContent = err.message || 'Erro inesperado.';
      modalError.classList.remove('d-none');
    }
  });
});
