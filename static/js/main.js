// static/js/main.js - VERSÃO FINALIZADA E COMPLETA COM FILTRO DE MOTIVOS

document.addEventListener('DOMContentLoaded', function() {
    
    const data = FLASK_DASHBOARD_DATA;
    let movimentacaoChartInstance = null; // Instância para gráfico de linha
    let motivosChartInstance = null; // Instância para gráfico de rosca

    // --- 1. FUNÇÕES DE RENDERIZAÇÃO ---

    // Função para renderizar o Gráfico de Movimentação (Linha)
    function renderMovimentacaoChart(timeframe) {
        const chartData = timeframe === 'anual' ? data.movimentacao_anual : data.movimentacao_mensal;
        const title = timeframe === 'anual' ? 'Movimentação Anual (Últimos 5 Anos)' : 'Movimentação Mensal (Ano Atual)';
        const ctx = document.getElementById('movimentacaoChart');

        if (movimentacaoChartInstance) {
            movimentacaoChartInstance.destroy();
        }

        if (!ctx || chartData.labels.length === 0) {
             const parent = ctx ? ctx.parentElement : document.querySelector('.charts-full-width .chart-container');
             if (parent) parent.innerHTML = '<p style="text-align: center; color: #777;">Não há dados de movimentação para o período selecionado.</p>';
             return;
        }

        movimentacaoChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Novas Entradas',
                    data: chartData.entradas,
                    borderColor: '#007bff', 
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: false, 
                    tension: 0.3
                }, {
                    label: 'Altas',
                    data: chartData.altas,
                    borderColor: '#28a745', 
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: false, 
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: title
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Número de Pacientes'
                        },
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Função para renderizar o Gráfico de Motivos (Rosca) com Filtros
    function renderMotivosChart(filteredData) {
        const ctxMotivos = document.getElementById('motivosChart');
        const message = document.getElementById('motivosMessage');
        
        if (motivosChartInstance) {
            motivosChartInstance.destroy();
        }

        if (!ctxMotivos) return;

        if (filteredData.labels.length === 0) {
            ctxMotivos.style.display = 'none';
            message.style.display = 'block';
            message.textContent = 'Nenhum motivo selecionado.';
            return;
        }
        
        ctxMotivos.style.display = 'block';
        message.style.display = 'none';

        motivosChartInstance = new Chart(ctxMotivos.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: filteredData.labels, 
                datasets: [{
                    data: filteredData.data,
                    // Garante cores suficientes para a seleção
                    backgroundColor: [
                        '#007bff', '#28a745', '#ffc107', '#dc3545', '#6c757d', 
                        '#17a2b8', '#fd7e14', '#6f42c1', '#1f77b4', '#ff7f0e' 
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    }

    // Função para renderizar o Gráfico de Dias Médios (Barras)
    function renderDiasChart() {
        const ctxDias = document.getElementById('diasChart');
        if (ctxDias && data.dias_data.labels.length > 0) {
            new Chart(ctxDias.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.dias_data.labels,
                    datasets: [{
                        label: 'Dias Médios',
                        data: data.dias_data.data,
                        backgroundColor: '#17a2b8', 
                        borderColor: '#17a2b8',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Média de Dias'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        } else if (ctxDias) {
            ctxDias.parentElement.innerHTML = '<p style="text-align: center; color: #777;">Não há dados de altas registradas para este gráfico.</p>';
        }
    }

    // Inicializa o Filtro de Motivos
    function initMotivosFilter() {
        const select = document.getElementById('motivosFilter');
        // Usamos a nova chave com todos os dados brutos
        const todosMotivos = data.todos_motivos; 

        if (!select || !todosMotivos || todosMotivos.length === 0) {
            if (select) select.style.display = 'none';
            // Mensagem de dados indisponíveis
            const chartDiv = document.querySelector('.charts-analysis .chart-half');
            chartDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><h3>Motivos de Internação</h3><p style="color: #777;">Nenhum dado de procedimento encontrado.</p></div>';
            return;
        }

        let initialSelectionCount = 0;

        // 4.1. Popula o dropdown
        todosMotivos.forEach(item => {
            const option = document.createElement('option');
            // Trunca o nome para exibição no dropdown
            option.textContent = item.procedimento.length > 30 ? item.procedimento.substring(0, 30) + '...' : item.procedimento;
            option.value = item.procedimento;
            
            // Pré-seleciona os 5 mais populares por padrão
            if (initialSelectionCount < 5) {
                option.selected = true;
                initialSelectionCount++;
            }
            select.appendChild(option);
        });
        
        // 4.2. Função de filtragem
        function filterAndRender() {
            // Pega os valores (procedimento) das opções selecionadas
            const selectedOptions = Array.from(select.selectedOptions).map(opt => opt.value);

            const filteredLabels = [];
            const filteredData = [];

            // Filtra os dados brutos com base nas opções selecionadas
            todosMotivos.forEach(item => {
                if (selectedOptions.includes(item.procedimento)) {
                    // Trunca o nome para exibição no gráfico (pode ser menor aqui)
                    const label = item.procedimento.length > 20 ? item.procedimento.substring(0, 17) + '...' : item.procedimento;
                    filteredLabels.push(label);
                    filteredData.push(item.total);
                }
            });

            // Redesenha o gráfico
            renderMotivosChart({ labels: filteredLabels, data: filteredData });
        }

        // 4.3. Adiciona Listener e faz a primeira renderização
        select.addEventListener('change', filterAndRender);

        // Renderização inicial (com os top 5 pré-selecionados)
        filterAndRender();
    }


    // --- INICIALIZAÇÃO GERAL ---
    
    renderMovimentacaoChart('mensal'); 
    renderDiasChart();
    initMotivosFilter();

    // Lógica para alternar entre Mensal e Anual no gráfico de movimentação
    const filterButtons = document.querySelectorAll('.btn-filter');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const timeframe = this.getAttribute('data-filter');
            renderMovimentacaoChart(timeframe);
        });
    });

});