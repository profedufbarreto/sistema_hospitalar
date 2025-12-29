// static/js/main.js - VERSÃO COM GRÁFICOS DE PRIORIDADE (VERDE, AMARELO, VERMELHO)

document.addEventListener('DOMContentLoaded', function() {
    
    // FLASK_DASHBOARD_DATA é injetado pelo Jinja no dashboard.html
    const data = FLASK_DASHBOARD_DATA; 
    
    let movimentacaoChartInstance = null;
    let diasChartInstance = null;
    let prioridadeChartInstance = null; // Rosca (Distribuição Atual)
    let tendenciaPrioridadeChartInstance = null; // Linha (Tendência Mensal)
    
    const nomesMeses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
    
    // Cores fixas para Prioridade (Triagem)
    const coresPrioridade = {
        'Verde': '#28a745',    // Verde (Não Urgente)
        'Amarelo': '#ffc107',  // Amarelo (Atenção/Urgência)
        'Vermelho': '#dc3545'  // Vermelho (Emergência/Urgente)
    };


    // --- 1. FUNÇÕES DE RENDERIZAÇÃO DE GRÁFICOS ---

    // Função para renderizar o Gráfico de Movimentação (Linha - Mantido)
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

    // NOVO GRÁFICO 1: DISTRIBUIÇÃO ATUAL POR PRIORIDADE (Rosca)
    function renderPrioridadeChart() {
        const ctx = document.getElementById('prioridadeChart');
        const chartData = data.prioridade_data; 
        
        // Verifica se o total de pacientes internados com prioridade definida é > 0
        const total = chartData.data.reduce((sum, value) => sum + value, 0);

        if (!ctx || total === 0) {
            const message = document.getElementById('prioridadeMessage');
            if (message) message.style.display = 'block';
            return;
        }

        // Mapeia os rótulos ('Verde', 'Amarelo', 'Vermelho') para as cores fixas
        const backgroundColors = chartData.labels.map(label => coresPrioridade[label]);

        if (prioridadeChartInstance) {
            prioridadeChartInstance.destroy();
        }

        prioridadeChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: chartData.labels, 
                datasets: [{
                    data: chartData.data,
                    backgroundColor: backgroundColors,
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
    
    // NOVO GRÁFICO 2: TENDÊNCIA MENSAL POR PRIORIDADE (Linha)
    function renderPrioridadeTrendChart() {
        const ctx = document.getElementById('tendenciaPrioridadeChart');
        const rawData = data.prioridade_tendencia;
        
        if (!ctx || rawData.length === 0) {
            const message = document.getElementById('tendenciaPrioridadeMessage');
            if(message) message.style.display = 'block';
            return;
        }
        
        // As categorias no backend são minúsculas ('verde', 'amarelo', 'vermelho')
        const priorityCategories = ['verde', 'amarelo', 'vermelho'];
        
        // Agrupa os dados por prioridade
        const datasets = priorityCategories.map(prio => {
            const dadosMensais = Array(12).fill(0); 
            
            rawData.filter(item => item.prioridade_atencao === prio)
                .forEach(item => {
                    // Mês é 1-baseado, ajustamos para 0-baseado
                    dadosMensais[item.mes - 1] = item.total; 
                });
            
            // Converte a primeira letra para maiúscula para exibir a cor correta
            const labelCapitalized = prio.charAt(0).toUpperCase() + prio.slice(1);

            return {
                label: labelCapitalized + ' Prioridade',
                data: dadosMensais,
                borderColor: coresPrioridade[labelCapitalized],
                backgroundColor: coresPrioridade[labelCapitalized],
                fill: false,
                tension: 0.1
            };
        });

        if (tendenciaPrioridadeChartInstance) {
            tendenciaPrioridadeChartInstance.destroy();
        }

        tendenciaPrioridadeChartInstance = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: nomesMeses,
                datasets: datasets
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Número de Internações' },
                        ticks: { precision: 0 }
                    }
                }
            }
        });
    }


    // Função para renderizar o Gráfico de Dias Médios (Barras - Mantido)
    function renderDiasChart() {
        const ctxDias = document.getElementById('diasChart');
        if (ctxDias && data.dias_data.labels.length > 0) {
            if (diasChartInstance) {
                diasChartInstance.destroy();
            }
            diasChartInstance = new Chart(ctxDias.getContext('2d'), {
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

    // --- 2. INICIALIZAÇÃO GERAL ---
    
    // Chama os novos gráficos de Prioridade
    renderPrioridadeChart();
    renderPrioridadeTrendChart(); 

    // Chama os gráficos existentes
    renderMovimentacaoChart('mensal'); 
    renderDiasChart();
    
    // Lógica para alternar entre Mensal e Anual no gráfico de movimentação (Mantido)
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

// static/js/main.js

/**
 * Função Global para abrir/fechar o menu de navegação do PEP
 */
function toggleNavMenu() {
    const menu = document.getElementById("nav-menu-list");
    if (menu) {
        menu.classList.toggle("show-menu");
    }
}

/**
 * Fechar menus ao clicar fora deles
 */
window.addEventListener('click', function(event) {
    const dropdown = document.querySelector('.nav-dropdown');
    const menu = document.getElementById("nav-menu-list");
    
    // Se o clique for fora do dropdown, remove a classe de exibição
    if (dropdown && !dropdown.contains(event.target)) {
        if (menu && menu.classList.contains('show-menu')) {
            menu.classList.remove('show-menu');
        }
    }
});

/**
 * Lógica Global de Tema (Dark Mode)
 * (Caso você queira centralizar aqui também)
 */
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    
    if (themeToggle) {
        // Lógica de alternar tema...
    }
});

// static/js/main.js

// Abre e fecha o menu dropdown do canto esquerdo
function toggleNavMenu() {
    const menu = document.getElementById("nav-menu-list");
    if (menu) menu.classList.toggle("show-menu");
}

// Gerenciamento do Tema (Sol/Lua)
document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    function refreshUI(isDark) {
        if (isDark) {
            document.body.classList.add('dark-mode');
            if (themeIcon) {
                themeIcon.innerHTML = '&#9728;'; // Ícone de Sol
                themeIcon.style.color = '#ffcc00';
            }
        } else {
            document.body.classList.remove('dark-mode');
            if (themeIcon) {
                themeIcon.innerHTML = '&#9789;'; // Ícone de Lua
                themeIcon.style.color = '#333';
            }
        }
    }

    const savedTheme = localStorage.getItem('theme') || 'dark';
    refreshUI(savedTheme === 'dark');

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isNowDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', isNowDark ? 'dark' : 'light');
            refreshUI(isNowDark);
        });
    }
});

// Fecha o menu dropdown se clicar fora dele
window.addEventListener('click', function(event) {
    if (!event.target.closest('.nav-dropdown')) {
        const menu = document.getElementById("nav-menu-list");
        if (menu) menu.classList.remove("show-menu");
    }
});