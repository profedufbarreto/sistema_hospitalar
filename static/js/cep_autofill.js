// static/js/cep_autofill.js

document.addEventListener('DOMContentLoaded', function() {
    const cepInput = document.getElementById('cep');
    const enderecoInput = document.getElementById('endereco');
    const bairroInput = document.getElementById('bairro');
    const cidadeUfInput = document.getElementById('cidade_uf');
    const numeroInput = document.getElementById('numero');
    
    // Máscara de CEP (XXXXX-XXX)
    cepInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove tudo que não é dígito
        if (value.length > 5) {
            value = value.substring(0, 5) + '-' + value.substring(5, 8);
        }
        e.target.value = value;
    });

    // Evento principal: Quando o campo CEP perde o foco (blur) e tem 8 dígitos
    cepInput.addEventListener('blur', function() {
        let cep = this.value.replace(/\D/g, ''); // Limpa a máscara

        if (cep.length !== 8) {
            return; // Sai se o CEP for incompleto
        }
        
        // Limpa campos para dar feedback visual
        enderecoInput.value = 'Buscando...';
        bairroInput.value = '';
        cidadeUfInput.value = '';
        
        // Chama a API ViaCEP
        fetch(`https://viacep.com.br/ws/${cep}/json/`)
            .then(response => response.json())
            .then(data => {
                if (data.erro) {
                    alert('CEP não encontrado ou inválido.');
                    enderecoInput.value = '';
                    return;
                }

                // Preenche os campos
                enderecoInput.value = data.logradouro || '';
                bairroInput.value = data.bairro || '';
                cidadeUfInput.value = `${data.localidade} / ${data.uf}` || '';
                
                // Foca no campo número, que é o próximo a ser preenchido manualmente
                numeroInput.focus(); 
            })
            .catch(error => {
                console.error('Erro na busca de CEP:', error);
                alert('Erro ao consultar o serviço de CEP.');
                enderecoInput.value = '';
            });
    });
});