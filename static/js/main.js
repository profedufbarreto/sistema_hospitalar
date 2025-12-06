// static/js/main.js - CORRIGIDO

document.addEventListener('DOMContentLoaded', function() {
    
    // ⚠️ Usa a variável injetada pelo Flask no dashboard.html
    const data = FLASK_DASHBOARD_DATA;

    // 1. Atualiza os Cartões KPI
    // O JavaScript AGORA USA O VALOR INJETADO PELO JINJA.
    // SE O PYTHON ENVIOU 0 (ZERO), O JS IRÁ ATUALIZAR PARA 0.
    document.getElementById('total-internados').textContent = data.total_internados;
    document.getElementById('altas-mes').textContent = data.altas_ultimos_7_dias;
    document.getElementById('estoque-critico').textContent = data.baixo_estoque;

    // 2. Gráfico de Motivos de Internação (Gráfico de Rosca/Pizza)
    const ctxMotivos = document.getElementById('motivosChart').getContext('2d');
    new Chart(ctxMotivos, {
        type: 'doughnut',
        data: {
            // Usa as chaves do Python
            labels: data.motivos_data.labels, 
            datasets: [{
                data: data.motivos_data.data,
                backgroundColor: [
                    '#007bff',
                    '#28a745',
                    '#ffc107',
                    '#dc3545',
                    '#6c757d'
                ],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: false
                }
            }
        }
    });

    // 3. Gráfico de Dias Médios de Internação (Gráfico de Barras)
    const ctxDias = document.getElementById('diasChart').getContext('2d');
    new Chart(ctxDias, {
        type: 'bar',
        data: {
            // Usa as chaves do Python
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
});