// static/js/conversions.js

document.addEventListener('DOMContentLoaded', function() {
    const mlInput = document.getElementById('ml_input');
    const gotasInput = document.getElementById('gotas_input');
    const resultadoGotas = document.getElementById('resultado_gotas');
    const resultadoMl = document.getElementById('resultado_ml');
    
    // Fator de Conversão Padrão: 20 gotas/mL
    const FATOR_CONVERSAO = 20;

    /**
     * Converte Mililitros (mL) para Gotas.
     */
    function convertMlToGotas() {
        // Limpa o outro campo para evitar cálculos simultâneos e confusão
        gotasInput.value = '';
        resultadoMl.textContent = '0 mL';
        
        const ml = parseFloat(mlInput.value);
        if (isNaN(ml) || ml <= 0) {
            resultadoGotas.textContent = '0 Gotas';
            return;
        }

        // 1 mL = 20 Gotas
        const gotas = ml * FATOR_CONVERSAO;
        // Usa toFixed(0) para arredondar para o número inteiro de gotas
        resultadoGotas.textContent = `${gotas.toFixed(0)} Gotas`; 
    }

    /**
     * Converte Gotas para Mililitros (mL).
     */
    function convertGotasToMl() {
        // Limpa o outro campo para evitar cálculos simultâneos e confusão
        mlInput.value = '';
        resultadoGotas.textContent = '0 Gotas';

        const gotas = parseFloat(gotasInput.value);
        if (isNaN(gotas) || gotas <= 0) {
            resultadoMl.textContent = '0 mL';
            return;
        }

        // 1 Gota = 1/20 mL = 0.05 mL
        const ml = gotas / FATOR_CONVERSAO;
        // Usa toFixed(2) para mostrar duas casas decimais, comum em mL
        resultadoMl.textContent = `${ml.toFixed(2)} mL`; 
    }

    // Adiciona ouvintes de eventos para calcular em tempo real (key up)
    mlInput.addEventListener('keyup', convertMlToGotas);
    gotasInput.addEventListener('keyup', convertGotasToMl);
    
    // Adiciona ouvintes para garantir que o cálculo ocorra ao colar ou ao navegar com o mouse
    mlInput.addEventListener('change', convertMlToGotas);
    gotasInput.addEventListener('change', convertGotasToMl);
});