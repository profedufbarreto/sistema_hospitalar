// static/js/main.js - VERSÃO FINALIZADA E COMPLETA COM FILTROS DE MOVIMENTAÇÃO

document.addEventListener('DOMContentLoaded', function() {
    
    // ⚠️ Variável injetada pelo Flask (do dashboard.html)
    const data = FLASK_DASHBOARD_DATA;
    let movimentacaoChartInstance = null; // Variável para armazenar a instância do gráfico de linha

    // --- 1. FUNÇÕES DE RENDERIZAÇÃO DE GRÁFICOS ---

    // Função para renderizar o Gráfico de Movimentação (Linha)
    function renderMovimentacaoChart(timeframe) {
        // Seleciona os dados baseados no filtro (mensal ou anual)
        const chartData = timeframe === 'anual' ? data.movimentacao_anual : data.movimentacao_mensal;
        const title = timeframe === 'anual' ? 'Movimentação Anual (Últimos 5 Anos)' : 'Movimentação Mensal (Ano Atual)';
        const ctx = document.getElementById('movimentacaoChart');

        // Destrói instância anterior para redesenhar
        if (movimentacaoChartInstance) {
            movimentacaoChartInstance.destroy();
        }

        if (!ctx || chartData.labels.length === 0) {
             // Caso não haja dados, exibe mensagem
             ctx.parentElement.innerHTML = '<p style="text-align: center; color: #777;">Não há dados de movimentação para o período selecionado.</p>';
             return;
        }

        movimentacaoChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: 'Novas Entradas',
                    data: chartData.entradas,
                    borderColor: '#007bff', // Azul
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: false, // Não preenche área
                    tension: 0.3
                }, {
                    label: 'Altas',
                    data: chartData.altas,
                    borderColor: '#28a745', // Verde
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: false, // Não preenche área
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
                            precision: 0 // Garante que o eixo Y mostre apenas números inteiros
                        }
                    }
                }
            }
        });
    }

    // Função para renderizar o Gráfico de Motivos (Rosca)
    function renderMotivosChart() {
        const ctxMotivos = document.getElementById('motivosChart');
        if (ctxMotivos && data.motivos_data.labels.length > 0) {
            new Chart(ctxMotivos.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: data.motivos_data.labels, 
                    datasets: [{
                        data: data.motivos_data.data,
                        backgroundColor: [
                            '#007bff', '#28a745', '#ffc107', '#dc3545', '#6c757d'
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
        } else if (ctxMotivos) {
            // Se não houver dados
            ctxMotivos.parentElement.innerHTML = '<p style="text-align: center; color: #777;">Não há dados de internações para este gráfico.</p>';
        }
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
            // Se não houver dados
            ctxDias.parentElement.innerHTML = '<p style="text-align: center; color: #777;">Não há dados de altas registradas para este gráfico.</p>';
        }
    }


    // --- 2. LÓGICA DE FILTRO E INICIALIZAÇÃO ---

    // Funções de atualização dos KPIs são removidas, pois o Jinja já faz a injeção inicial
    // e os elementos são apenas referências para garantir que o JS possa interagir
    
    // Inicializa os gráficos estáticos
    renderMotivosChart();
    renderDiasChart();
    
    // Inicializa o gráfico de movimentação como MENSAL por padrão
    renderMovimentacaoChart('mensal');

    // Lógica para alternar entre Mensal e Anual no gráfico de movimentação
    const filterButtons = document.querySelectorAll('.btn-filter');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove a classe 'active' de todos
            filterButtons.forEach(btn => btn.classList.remove('active'));
            
            // Adiciona a classe 'active' ao botão clicado
            this.classList.add('active');
            
            // Renderiza o gráfico com o filtro selecionado
            const timeframe = this.getAttribute('data-filter');
            renderMovimentacaoChart(timeframe);
        });
    });

});