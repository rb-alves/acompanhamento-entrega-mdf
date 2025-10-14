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
                            <a href="/detalhes?loja=${pedido.loja}&pedido=${pedido.pedido}&cpf=${cpf}" 
                                class="text-decoration-none fw-semibold small text-secondary">
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

