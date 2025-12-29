// static/js/cep_autofill.js

document.addEventListener('DOMContentLoaded', function() {
    const cepInput = document.getElementById('cep');
    const enderecoInput = document.getElementById('endereco');
    const bairroInput = document.getElementById('bairro');
    const numeroInput = document.getElementById('numero');

    if (cepInput) {
        // Máscara de CEP automática
        cepInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 5) {
                value = value.substring(0, 5) + '-' + value.substring(5, 8);
            }
            e.target.value = value;
        });

        // Busca automática no ViaCEP
        cepInput.addEventListener('blur', function() {
            let cep = this.value.replace(/\D/g, '');

            if (cep.length === 8) {
                enderecoInput.value = 'Buscando...';
                
                fetch(`https://viacep.com.br/ws/${cep}/json/`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.erro) {
                            alert('CEP não encontrado.');
                            enderecoInput.value = '';
                        } else {
                            enderecoInput.value = data.logradouro || '';
                            bairroInput.value = data.bairro || '';
                            // Foca no número após preencher
                            numeroInput.focus();
                        }
                    })
                    .catch(() => {
                        alert('Erro ao consultar CEP.');
                        enderecoInput.value = '';
                    });
            }
        });
    }
});