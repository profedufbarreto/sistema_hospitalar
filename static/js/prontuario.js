// static/js/prontuario.js
document.addEventListener('DOMContentLoaded', function() {
    const medicamentoSelect = document.getElementById('medicamento_entrada');
    const outroMedicamentoGroup = document.getElementById('outro_medicamento_group');
    const cepInput = document.getElementById('cep');
    const enderecoInput = document.getElementById('endereco');
    const bairroInput = document.getElementById('bairro');
    const cidadeUfInput = document.getElementById('cidade_uf');
    const numeroInput = document.getElementById('numero');

    // --- Lógica: Mostrar/Esconder campo "Outro Medicamento" ---
    if (medicamentoSelect && outroMedicamentoGroup) {
        // Inicialmente verifica e aplica o display correto
        outroMedicamentoGroup.style.display = medicamentoSelect.value === 'outro' ? 'block' : 'none';

        medicamentoSelect.addEventListener('change', function() {
            outroMedicamentoGroup.style.display = this.value === 'outro' ? 'block' : 'none';
        });
    }

    // --- Lógica: Preenchimento Automático do CEP (ViaCEP) ---
    if (cepInput) {
        cepInput.addEventListener('blur', function() {
            // Remove caracteres não numéricos e limita a 8 dígitos
            const cep = this.value.replace(/\D/g, '').substring(0, 8);
            
            // Limpa os campos enquanto espera a resposta
            enderecoInput.value = '';
            bairroInput.value = '';
            cidadeUfInput.value = '';

            if (cep.length === 8) {
                // Endpoint do ViaCEP
                const url = `https://viacep.com.br/ws/${cep}/json/`;

                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        if (!("erro" in data)) {
                            // Preenche os campos se os dados existirem
                            enderecoInput.value = data.logradouro || '';
                            bairroInput.value = data.bairro || '';
                            cidadeUfInput.value = `${data.localidade || ''} / ${data.uf || ''}`;
                            
                            // Foca no campo 'Número' para continuar o preenchimento
                            numeroInput.focus(); 
                        } else {
                            alert("CEP não encontrado ou inválido. Por favor, preencha o endereço manualmente.");
                        }
                    })
                    .catch(error => {
                        console.error('Erro ao buscar CEP:', error);
                        alert("Erro na comunicação com o servidor de CEP.");
                    });
            }
        });
    }
});