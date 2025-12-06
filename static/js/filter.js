function filterTable() {
    // 1. Obter o valor digitado (em minúsculas)
    let input = document.getElementById('search-input');
    let filter = input.value.toLowerCase();
    
    // 2. Obter a tabela e as linhas
    let table = document.getElementById('pacientes-table');
    let tr = table.getElementsByTagName('tr');

    // 3. Iterar sobre todas as linhas da tabela (exceto o cabeçalho)
    for (let i = 1; i < tr.length; i++) {
        let row = tr[i];
        
        // Obter o nome do paciente da linha (usando o atributo data-nome)
        let nomePaciente = row.getAttribute('data-nome');
        
        // 4. Verificar se o nome do paciente contém o texto do filtro
        if (nomePaciente) {
            if (nomePaciente.indexOf(filter) > -1) {
                row.style.display = ""; // Mostrar a linha
            } else {
                row.style.display = "none"; // Esconder a linha
            }
        }       
    }
}