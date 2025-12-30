// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    
    // =========================================================
    // 1. TÍTULO DINÂMICO DO MÓDULO (NOVO)
    // =========================================================
    const nomesModulos = {
        'dashboard': 'Dashboard',
        'pacientes': 'Pacientes',
        'prontuario': 'Novo Prontuário',
        'estoque': 'Estoque',
        'provas_vida_geral': 'Histórico ❤️',
        'arquivo': 'Arquivo/Altas',
        'conversor': 'Conversor',
        'usuarios': 'Usuários',
        'sistema': 'Módulos'
    };

    const path = window.location.pathname;
    const label = document.getElementById('current-module');

    if (label) {
        for (let chave in nomesModulos) {
            if (path.includes(chave)) {
                label.innerText = nomesModulos[chave];
                break;
            }
        }
    }

    // =========================================================
    // 2. LÓGICA DE GRÁFICOS (APENAS PARA DASHBOARD)
    // =========================================================
    
    // Verifica se os dados e elementos do gráfico existem antes de executar
    if (typeof FLASK_DASHBOARD_DATA !== 'undefined') {
        const data = FLASK_DASHBOARD_DATA; 
        
        let movimentacaoChartInstance = null;
        let diasChartInstance = null;
        let prioridadeChartInstance = null;
        let tendenciaPrioridadeChartInstance = null;
        
        const nomesMeses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
        const coresPrioridade = {
            'Verde': '#28a745',
            'Amarelo': '#ffc107',
            'Vermelho': '#dc3545'
        };

        // Renderização: Movimentação
        function renderMovimentacaoChart(timeframe) {
            const chartData = timeframe === 'anual' ? data.movimentacao_anual : data.movimentacao_mensal;
            const title = timeframe === 'anual' ? 'Movimentação Anual' : 'Movimentação Mensal';
            const ctx = document.getElementById('movimentacaoChart');

            if (movimentacaoChartInstance) movimentacaoChartInstance.destroy();
            if (!ctx || chartData.labels.length === 0) return;

            movimentacaoChartInstance = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [
                        { label: 'Entradas', data: chartData.entradas, borderColor: '#007bff', tension: 0.3 },
                        { label: 'Altas', data: chartData.altas, borderColor: '#28a745', tension: 0.3 }
                    ]
                },
                options: { responsive: true, plugins: { title: { display: true, text: title } } }
            });
        }

        // Renderização: Distribuição Atual (Rosca)
        function renderPrioridadeChart() {
            const ctx = document.getElementById('prioridadeChart');
            const chartData = data.prioridade_data;
            if (!ctx || chartData.data.reduce((a, b) => a + b, 0) === 0) return;

            if (prioridadeChartInstance) prioridadeChartInstance.destroy();
            prioridadeChartInstance = new Chart(ctx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        data: chartData.data,
                        backgroundColor: chartData.labels.map(l => coresPrioridade[l])
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }

        // Renderização: Tendência Mensal
        function renderPrioridadeTrendChart() {
            const ctx = document.getElementById('tendenciaPrioridadeChart');
            const rawData = data.prioridade_tendencia;
            if (!ctx || rawData.length === 0) return;

            const datasets = ['verde', 'amarelo', 'vermelho'].map(prio => {
                const dadosMensais = Array(12).fill(0);
                rawData.filter(item => item.prioridade_atencao === prio)
                       .forEach(item => { dadosMensais[item.mes - 1] = item.total; });
                
                const labelCap = prio.charAt(0).toUpperCase() + prio.slice(1);
                return {
                    label: labelCap,
                    data: dadosMensais,
                    borderColor: coresPrioridade[labelCap],
                    backgroundColor: coresPrioridade[labelCap],
                    fill: false,
                    tension: 0.1
                };
            });

            if (tendenciaPrioridadeChartInstance) tendenciaPrioridadeChartInstance.destroy();
            tendenciaPrioridadeChartInstance = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: { labels: nomesMeses, datasets: datasets },
                options: { responsive: true }
            });
        }

        // Renderização: Dias Médios
        function renderDiasChart() {
            const ctxDias = document.getElementById('diasChart');
            if (!ctxDias || data.dias_data.labels.length === 0) return;

            if (diasChartInstance) diasChartInstance.destroy();
            diasChartInstance = new Chart(ctxDias.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.dias_data.labels,
                    datasets: [{
                        label: 'Dias Médios',
                        data: data.dias_data.data,
                        backgroundColor: ['#61afef', '#98c379', '#e5c07b', '#c678dd', '#e06c75']
                    }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } }
            });
        }

        // Inicializa Gráficos
        renderPrioridadeChart();
        renderPrioridadeTrendChart();
        renderMovimentacaoChart('mensal');
        renderDiasChart();

        // Filtros de Movimentação
        const filterButtons = document.querySelectorAll('.btn-filter');
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                renderMovimentacaoChart(this.getAttribute('data-filter'));
            });
        });
    }

    // =========================================================
    // 3. LÓGICA DE TEMA (SOL/LUA)
    // =========================================================
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    function refreshUI(isDark) {
        if (isDark) {
            document.body.classList.add('dark-mode');
            if (themeIcon) {
                themeIcon.innerHTML = '&#9728;'; // Sol
                themeIcon.style.color = '#ffcc00';
            }
        } else {
            document.body.classList.remove('dark-mode');
            if (themeIcon) {
                themeIcon.innerHTML = '&#9789;'; // Lua
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

// =========================================================
// 4. FUNÇÕES GLOBAIS (MENU DROPDOWN)
// =========================================================
function toggleNavMenu() {
    const menu = document.getElementById("nav-menu-list");
    if (menu) menu.classList.toggle("show-menu");
}

window.addEventListener('click', function(event) {
    if (!event.target.closest('.nav-dropdown')) {
        const menu = document.getElementById("nav-menu-list");
        if (menu) menu.classList.remove("show-menu");
    }
});