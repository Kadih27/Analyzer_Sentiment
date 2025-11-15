const inputText = document.getElementById('input-text');
    const analyzeBtn = document.getElementById('analyze-btn');
    const clearBtn = document.getElementById('clear-btn');
    const errorBox = document.getElementById('error-box');
    const errorMsg = document.getElementById('error-msg');
    const resultCard = document.getElementById('result-card');
    const sentimentEmoji = document.getElementById('sentiment-emoji');
    const sentimentLabel = document.getElementById('sentiment-label');
    const sentimentScore = document.getElementById('sentiment-score');
    const languageInfo = document.getElementById('language-info');
    const historyList = document.getElementById('history-list');

    // Charger l’historique depuis le serveur
    async function loadHistoryFromServer() {
        try {
            const res = await fetch('/history');
            const history = await res.json();
            renderHistory(history);
        } catch (err) {
            console.warn('Impossible de charger l’historique:', err);
            historyList.innerHTML = '<div class="history-item"><em>Historique indisponible</em></div>';
        }
    }

    function renderHistory(history) {
        historyList.innerHTML = '';
        if (!Array.isArray(history) || history.length === 0) {
            historyList.innerHTML = '<div class="history-item"><em>Aucun historique</em></div>';
            return;
        }
        // Afficher les plus récents en bas → on inverse l’ordre visuel
        const recent = history.slice(-20).reverse();
        recent.forEach(item => {
            const div = document.createElement('div');
            div.className = 'history-item';
            const lang = item.language === 'undetermined' ? '??' : (item.language || '??');
            const displayText = item.text || item.full_text;
            div.innerHTML = `
                <div class="history-text" title="${displayText}">"${displayText.length > 50 ? displayText.substring(0,50) + '…' : displayText}"</div>
                <div class="history-meta">
                    <span>${getEmoji(item.label)} ${capitalize(item.label)}</span>
                    <span class="lang-badge">${lang.toUpperCase()}</span>
                </div>
            `;
            historyList.appendChild(div);
        });
    }

    function getEmoji(label) {
        switch (label) {
            case 'very positive': case 'positive': return '😊';
            case 'very negative': case 'negative': return '😞';
            case 'neutral': return '😐';
            default: return '🤔';
        }
    }

    function capitalize(str) {
        return str ? str.charAt(0).toUpperCase() + str.slice(1) : str;
    }

    function showError(message) {
        errorMsg.textContent = message;
        errorBox.classList.add('show');
        setTimeout(() => errorBox.classList.remove('show'), 5000);
    }

    analyzeBtn.addEventListener('click', async () => {
        const text = inputText.value.trim();
        if (!text) {
            showError('Veuillez saisir du texte.');
            return;
        }
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyse...';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Erreur inconnue');
            }

            // Afficher résultat
            sentimentEmoji.textContent = getEmoji(data.label);
            sentimentLabel.textContent = capitalize(data.label);
            sentimentScore.textContent = `Confiance : ${(data.score * 100).toFixed(1)}%`;
            const langDisplay = data.language === 'undetermined' ? 'inconnue' : data.language || 'inconnue';
            languageInfo.textContent = `Langue détectée : ${langDisplay}`;
            resultCard.classList.add('show');

            // Recharger l’historique
            loadHistoryFromServer();

        } catch (err) {
            showError('Erreur : ' + err.message);
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-search"></i> Analyser';
        }
    });

    clearBtn.addEventListener('click', () => {
        inputText.value = '';
        resultCard.classList.remove('show');
        inputText.focus();
    });

    // Bouton pour effacer tout l’historique
    document.getElementById('clear-history-btn').addEventListener('click', async () => {
        if (!confirm("Voulez-vous vraiment supprimer tout l’historique ? Cette action est irréversible.")) {
            return;
        }

        try {
            const response = await fetch('/clear-history', {
                method: 'DELETE'
            });
            const result = await response.json();

            if (response.ok) {
                // Recharger l’historique (vide)
                loadHistoryFromServer();
                // Optionnel : afficher un petit message de succès
                showError(result.message); // réutilise la fonction existante pour afficher brièvement
                errorBox.style.backgroundColor = '#dcfce7';
                errorBox.style.color = '#065f46';
            } else {
                throw new Error(result.message || 'Erreur inconnue');
            }
        } catch (err) {
            showError('Erreur lors de la suppression : ' + err.message);
            errorBox.style.backgroundColor = '#fee';
            errorBox.style.color = '#dc2626';
        }
    });

    // Charger au démarrage
    loadHistoryFromServer();