// static/js/prova_vida.js

document.addEventListener('DOMContentLoaded', function() {
    // Função JavaScript para preencher o campo datetime-local com a data/hora atual
    const dataHoraInput = document.getElementById('data_hora');
    
    if (dataHoraInput) {
        var now = new Date();
        // Converte para o formato YYYY-MM-DDTHH:mm, ajustando o fuso horário local
        var localDatetime = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().substring(0, 16);
        dataHoraInput.value = localDatetime;
    }
});