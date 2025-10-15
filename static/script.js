document.getElementById("consultar").addEventListener("click", async () => {
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

    resultado.innerHTML = `
        <div class="text-center mt-4">
            <div class="spinner-border text-secondary" role="status"></div>
            <p class="text-muted mt-2 fw-semibold">Buscando pedidos...</p>
        </div>`;

    try {
        const response = await fetch(`/api/pedidos?cpf=${cpf}`);
        const data = await response.json();

        if (data.length === 0) {
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

        // Criação dos cards de pedidos
        data.forEach(pedido => {
            // Define a cor do status
            let badgeClass = "bg-secondary";
            switch (pedido.situacao_pedido?.toLowerCase()) {
                case "confirmado":
                    badgeClass = "bg-primary";
                    break;
                case "separando":
                    badgeClass = "bg-warning text-dark";
                    break;
                case "em transito":
                    badgeClass = "bg-info text-dark";
                    break;
                case "entregue":
                    badgeClass = "bg-success";
                    break;
                case "cancelado":
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
        resultado.innerHTML = `
            <div class="text-center mt-4">
                <p class="text-danger fw-semibold">Erro ao buscar pedidos. Tente novamente.</p>
            </div>`;
        console.error(error);
    }
});

// formatação
function formatarValor(valor) {
  return (valor / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
}

// Detalhes do Pedido
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

      document.getElementById('m-loja').textContent = info.loja;
      document.getElementById('m-pedido').textContent = info.pedido;
      document.getElementById('m-cliente').textContent = info.cliente || '—';
      document.getElementById('m-data').textContent = info.data || '—';
      document.getElementById('m-valor').textContent = formatarValor(Number(info.valor) || 0);
      document.getElementById('m-situacao').textContent = info.situacao_pedido || '—';

      const tbody = document.getElementById('m-itens');
      tbody.innerHTML = "";

      if (info.itens?.length) {
        info.itens.forEach(i => {
          tbody.innerHTML += `
            <tr>
              <td>${i.item}</td>
              <td class="text-end">${(i.quantidade / 1000).toFixed(0)}</td>
              <td class="text-end">R$ ${formatarValor(Number(i.preco))}</td>
            </tr>`;
        });
      } else {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Nenhum item encontrado</td></tr>`;
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