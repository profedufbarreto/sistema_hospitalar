// static/js/estoque_modal.js
document.addEventListener('DOMContentLoaded', function() {
    var modal = document.getElementById("estoqueModal");
    var btn = document.getElementById("openModalBtn");
    var span = document.getElementsByClassName("close-btn")[0];

    // Abre o modal ao clicar no botão
    if (btn) {
        btn.onclick = function() {
            modal.style.display = "block";
        }
    }

    // Fecha o modal ao clicar no X
    if (span) {
        span.onclick = function() {
            modal.style.display = "none";
        }
    }

    // Fecha o modal ao clicar fora dele
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});