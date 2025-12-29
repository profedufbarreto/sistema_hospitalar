// static/js/prontuario.js

document.addEventListener('DOMContentLoaded', function() {
    const medicationContainer = document.getElementById('medication-container');
    const addMedBtn = document.getElementById('add-med-btn');

    /**
     * Adiciona uma nova linha de medicamento clonando o template do HTML
     */
    function addMedicationItem() {
        const template = document.getElementById('medication-template');
        if (!template) return;

        // importNode garante a clonagem profunda de todos os elementos (inclusive as options do loop)
        const clone = document.importNode(template.content, true);
        
        const select = clone.querySelector('.medicamento-select');
        const outroGroup = clone.querySelector('.outro-medicamento-group');

        // Escuta mudança no select para mostrar campo 'Outro'
        if (select && outroGroup) {
            select.addEventListener('change', function() {
                outroGroup.style.display = this.value === 'outro' ? 'block' : 'none';
            });
        }

        medicationContainer.appendChild(clone);
    }

    /**
     * Remove a linha de medicação selecionada
     */
    window.removeMedicationItem = function(btn) {
        const items = medicationContainer.querySelectorAll('.medication-item');
        if (items.length > 1) {
            btn.closest('.medication-item').remove();
        } else {
            alert("Mantenha ao menos um campo de medicação.");
        }
    };

    /**
     * Atualiza o valor oculto para o banco de dados (S/N)
     */
    window.updateSNValue = function(checkbox) {
        const hiddenInput = checkbox.closest('.checkbox-sn').querySelector('.sn-hidden-input');
        hiddenInput.value = checkbox.checked ? "1" : "0";
    };

    // Botão Adicionar
    if (addMedBtn) {
        addMedBtn.addEventListener('click', addMedicationItem);
    }

    // Adiciona a primeira linha automaticamente ao carregar
    if (medicationContainer && medicationContainer.children.length === 0) {
        addMedicationItem();
    }
});