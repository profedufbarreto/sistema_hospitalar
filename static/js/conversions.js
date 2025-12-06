// static/js/conversions.js
// Lógica para o Módulo Conversor (mL ⇌ Gotas).

document.addEventListener('DOMContentLoaded', function() {
    const mlInput = document.getElementById('ml_input');
    const gotasInput = document.getElementById('gotas_input');
    const resultadoGotas = document.getElementById('resultado_gotas');
    const resultadoMl = document.getElementById('resultado_ml');
    
    // Fator de Conversão Padrão: 20 gotas/mL, conforme a Bula Padrão.
    const FATOR_CONVERSAO = 20;

    /**
     * Converte Mililitros (mL) para Gotas.
     */
    function converterMlParaGotas() {
        // Limpa o campo oposto e seu resultado
        gotasInput.value = '';
        resultadoMl.textContent = '0 mL';
        
        const ml = parseFloat(mlInput.value);

        if (isNaN(ml) || ml <= 0) {
            resultadoGotas.textContent = '0 Gotas';
            return;
        }

        // Conversão: mL * FATOR
        const gotas = ml * FATOR_CONVERSAO;
        // Arredonda para o número inteiro mais próximo, pois gotas são discretas
        resultadoGotas.textContent = `${gotas.toFixed(0)} Gotas`; 
    }

    /**
     * Converte Gotas para Mililitros (mL).
     */
    function converterGotasParaMl() {
        // Limpa o campo oposto e seu resultado
        mlInput.value = '';
        resultadoGotas.textContent = '0 Gotas';

        const gotas = parseFloat(gotasInput.value);
        
        if (isNaN(gotas) || gotas <= 0) {
            resultadoMl.textContent = '0 mL';
            return;
        }

        // Conversão: Gotas / FATOR
        const ml = gotas / FATOR_CONVERSAO;
        // Mostra duas casas decimais, padrão para medição de líquidos em mL
        resultadoMl.textContent = `${ml.toFixed(2)} mL`; 
    }

    // Adiciona ouvintes de eventos para calcular em tempo real (digitação)
    mlInput.addEventListener('keyup', converterMlParaGotas);
    gotasInput.addEventListener('keyup', converterGotasParaMl);
    
    // Adiciona ouvintes para garantir que o cálculo ocorra ao colar (paste) ou ao perder o foco (blur/change)
    mlInput.addEventListener('change', converterMlParaGotas);
    gotasInput.addEventListener('change', converterGotasParaMl);

    // Garante que os resultados iniciais sejam zero ao carregar a página
    converterMlParaGotas();
    converterGotasParaMl();
});