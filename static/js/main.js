// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    
    // ⚠️ Usa a variável injetada pelo Flask no dashboard.html
    const data = FLASK_DASHBOARD_DATA;

    // 1. Atualiza os Cartões KPI (Usando IDs do HTML)
    // O JS agora apenas garante que os valores sejam exibidos, embora o Jinja já faça isso.
    // É mantido para compatibilidade e caso o Jinja não consiga renderizar.
    const totalInternados = document.getElementById('total-internados');
    if (totalInternados) totalInternados.textContent = data.total_internados;
    
    const altasMes = document.getElementById('altas-mes');
    if (altasMes) altasMes.textContent = data.altas_ultimos_7_dias;
    
    const estoqueCritico = document.getElementById('estoque-critico');
    if (estoqueCritico) estoqueCritico.textContent = data.baixo_estoque;
    

    // 2. Gráfico de Motivos de Internação (Gráfico de Rosca/Pizza)
    const ctxMotivos = document.getElementById('motivosChart');
    if (ctxMotivos && data.motivos_data.labels.length > 0) {
        new Chart(ctxMotivos.getContext('2d'), {
            type: 'doughnut',
            data: {
                // Usa as chaves do Python
                labels: data.motivos_data.labels, 
                datasets: [{
                    data: data.motivos_data.data,
                    backgroundColor: [
                        '#007bff', // Azul
                        '#28a745', // Verde
                        '#ffc107', // Amarelo
                        '#dc3545', // Vermelho
                        '#6c757d'  // Cinza
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
    } else if (ctxMotivos) {
        ctxMotivos.parentElement.innerHTML = '<p style="text-align: center; color: #777;">Não há dados suficientes de internações para este gráfico.</p>';
    }

    // 3. Gráfico de Dias Médios de Internação (Gráfico de Barras)
    const ctxDias = document.getElementById('diasChart');
    if (ctxDias && data.dias_data.labels.length > 0) {
        new Chart(ctxDias.getContext('2d'), {
            type: 'bar',
            data: {
                // Usa as chaves do Python
                labels: data.dias_data.labels,
                datasets: [{
                    label: 'Dias Médios',
                    data: data.dias_data.data,
                    backgroundColor: '#17a2b8', // Azul Ciano
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
});