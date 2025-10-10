document.getElementById("consultar").addEventListener("click", async () => {
    const cpf = document.getElementById("cpf").value.trim();
    const resultado = document.getElementById("resultado");

    if (!cpf) {
        resultado.innerHTML = "<p class='text-red-500'>Por favor, digite um CPF</p>";
        return;
    }

    resultado.innerHTML = "<p class='text-gray-500'>Buscando pedidos...</p>";

    try {
        const response = await fetch(`/api/pedidos?cpf=${cpf}`);
        const data = await response.json();

        if (data.length === 0) {
            resultado.innerHTML = "<p class='text-gray-600 mt-4'>Nenhum pedido encontrado</p>";
            return;
        }

        let html = `<h2 class='text-xl font-semibold mb-3'>Pedidos Encontrados (${data.length})</h2>`;

        data.forEach(pedido => {
            html += `
                <div class="bg-white rounded-xl shadow p-4 mb-4 border-l-4 border-blue-400">
                    <p><strong>Pedido:</strong> ${pedido.pedido} - <span class="text-blue-600">${pedido.situacao_pedido}</span></p>
                    <p><strong>Data:</strong> ${formatarData(pedido.data)}</p>
                    <p><strong>Valor:</strong> R$ ${Number((pedido.valor / 100)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                    <a href="/detalhes?pedido=${pedido.pedido}&cpf=${cpf}" class="text-blue-500 font-medium mt-2 inline-block">
                        Ver Detalhes →
                    </a>
                </div>
            `;
        });

        resultado.innerHTML = html
    
    } catch (error) {
        resultado.innerHTML = `<p class='text-red-500'>Erro ao buscar pedidos.</p>`;
        console.error(error);
    }
});

function formatarData(aaaammdd) {
  if (!aaaammdd || aaaammdd.length !== 8) return aaaammdd;
  const ano = aaaammdd.slice(0, 4);
  const mes = aaaammdd.slice(4, 6);
  const dia = aaaammdd.slice(6, 8);
  return `${dia}/${mes}/${ano}`;
}