// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Função que simula a busca de dados (em um sistema real, seria uma requisição AJAX)
    function fetchDashboardData() {
        // --- DADOS SIMULADOS (Em produção, o Python enviaria estes dados) ---
        return {
            totalInternados: 125,
            altasMes: 87,
            estoqueCritico: 3,
            
            motivosData: {
                labels: ['Infecção Respiratória', 'Trauma Leve', 'Pós-Cirúrgico', 'Diabetes', 'Cardíaco'],
                data: [30, 25, 20, 15, 10]
            },
            
            diasData: {
                labels: ['Medicina Interna', 'Pediatria', 'Cirurgia', 'UTI'],
                data: [4.5, 3.2, 5.0, 7.8] // Média de dias
            }
        };
    }

    const data = fetchDashboardData();

    // 1. Atualiza os Cartões KPI
    document.getElementById('total-internados').textContent = data.totalInternados;
    document.getElementById('altas-mes').textContent = data.altasMes;
    document.getElementById('estoque-critico').textContent = data.estoqueCritico;

    // 2. Gráfico de Motivos de Internação (Gráfico de Rosca/Pizza)
    const ctxMotivos = document.getElementById('motivosChart').getContext('2d');
    new Chart(ctxMotivos, {
        type: 'doughnut',
        data: {
            labels: data.motivosData.labels,
            datasets: [{
                data: data.motivosData.data,
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

    // 3. Gráfico de Dias Médios de Internação (Gráfico de Barras)
    const ctxDias = document.getElementById('diasChart').getContext('2d');
    new Chart(ctxDias, {
        type: 'bar',
        data: {
            labels: data.diasData.labels,
            datasets: [{
                label: 'Dias Médios',
                data: data.diasData.data,
                backgroundColor: '#17a2b8', // Cor Teal/Ciano
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