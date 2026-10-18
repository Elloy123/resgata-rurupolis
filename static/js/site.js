(function () {
    // Destaca no menu a seção atual
    var caminho = window.location.pathname;
    document.querySelectorAll('#menuPrincipal .nav-link').forEach(function (link) {
        var href = link.getAttribute('href');
        if ((href === '/' && caminho === '/') || (href !== '/' && caminho.indexOf(href) === 0)) {
            link.classList.add('active');
            link.setAttribute('aria-current', 'page');
        }
    });

    // Evita clique duplo nos formulários que levam ao Mercado Pago
    document.querySelectorAll('form.form-pagamento').forEach(function (form) {
        form.addEventListener('submit', function () {
            var botao = form.querySelector('button[type="submit"]');
            if (!botao) return;
            botao.disabled = true;
            botao.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Redirecionando para o Mercado Pago...';
        });
    });

    // Evita envio duplo ao finalizar pedidos do bazar e encomendas de eventos
    document.querySelectorAll('form.form-finalizar, form.form-encomenda').forEach(function (form) {
        form.addEventListener('submit', function () {
            var botao = form.querySelector('button[type="submit"]');
            if (!botao) return;
            setTimeout(function () {
                botao.disabled = true;
                botao.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Enviando...';
            }, 0);
        });
    });

    // Cardápio de eventos: botões +/- e total da encomenda
    var formEncomenda = document.querySelector('form.form-encomenda');
    if (formEncomenda) {
        var campos = formEncomenda.querySelectorAll('.qtd-item');
        var totalEl = document.getElementById('total-encomenda');
        var formatar = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
        var atualizarTotal = function () {
            var total = 0;
            campos.forEach(function (campo) {
                total += (parseInt(campo.value, 10) || 0) * parseFloat(campo.dataset.preco);
            });
            if (totalEl) totalEl.textContent = formatar.format(total);
        };
        formEncomenda.querySelectorAll('[data-qtd]').forEach(function (botao) {
            botao.addEventListener('click', function () {
                var campo = botao.parentElement.querySelector('.qtd-item');
                var max = parseInt(campo.max, 10) || 50;
                var valor = (parseInt(campo.value, 10) || 0) + parseInt(botao.dataset.qtd, 10);
                campo.value = Math.max(0, Math.min(max, valor));
                atualizarTotal();
            });
        });
        campos.forEach(function (campo) { campo.addEventListener('input', atualizarTotal); });
        atualizarTotal();
    }

    // Botões "Copiar" (ex: chave PIX)
    document.querySelectorAll('[data-copiar]').forEach(function (botao) {
        botao.addEventListener('click', function () {
            var campo = document.querySelector(botao.dataset.copiar);
            if (!campo) return;
            var original = botao.innerHTML;
            var feito = function () {
                botao.innerHTML = '<i class="bi bi-check2"></i> Copiado!';
                setTimeout(function () { botao.innerHTML = original; }, 2000);
            };
            if (navigator.clipboard) {
                navigator.clipboard.writeText(campo.value).then(feito);
            } else {
                campo.select();
                document.execCommand('copy');
                feito();
            }
        });
    });
})();
