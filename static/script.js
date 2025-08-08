// Stock Direction Predictor JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('stockForm');
    const tickerInput = document.getElementById('ticker');
    const predictBtn = document.getElementById('predictBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const resultsSection = document.getElementById('resultsSection');
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');

    // Auto-uppercase ticker input
    tickerInput.addEventListener('input', function(e) {
        e.target.value = e.target.value.toUpperCase();
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const ticker = tickerInput.value.trim();
        if (!ticker) {
            showError('Please enter a stock ticker symbol');
            return;
        }

        // Validate ticker format
        if (!/^[A-Z]{1,5}$/.test(ticker)) {
            showError('Invalid ticker format. Please use 1-5 letters only.');
            return;
        }

        setLoadingState(true);
        hideResults();
        hideError();

        try {
            const formData = new FormData();
            formData.append('ticker', ticker);

            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'An error occurred');
            }

            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'An unexpected error occurred');
        } finally {
            setLoadingState(false);
        }
    });

    function setLoadingState(loading) {
        if (loading) {
            predictBtn.disabled = true;
            btnText.textContent = 'Analyzing...';
            btnSpinner.classList.remove('d-none');
            document.body.classList.add('loading');
        } else {
            predictBtn.disabled = false;
            btnText.textContent = 'Predict Direction';
            btnSpinner.classList.add('d-none');
            document.body.classList.remove('loading');
        }
    }

    function displayResults(data) {
        // Update timestamp
        document.getElementById('timestampBadge').textContent = 
            new Date().toLocaleString();

        // Main prediction
        const predictionCard = document.getElementById('predictionCard');
        const predictionText = document.getElementById('predictionText');
        const confidenceText = document.getElementById('confidenceText');

        predictionText.innerHTML = `
            <i class="fas fa-${getPredictionIcon(data.prediction)} me-2"></i>
            ${data.prediction}
        `;
        confidenceText.textContent = `Confidence: ${data.confidence}`;

        // Set prediction card color
        predictionCard.className = `text-center p-4 rounded prediction-${data.prediction.toLowerCase()}`;

        // Stock info
        document.getElementById('tickerDisplay').textContent = data.ticker;
        document.getElementById('currentPrice').textContent = `$${data.current_price}`;
        
        const lastReturnEl = document.getElementById('lastReturn');
        const returnClass = data.last_return >= 0 ? 'text-success' : 'text-danger';
        const returnIcon = data.last_return >= 0 ? 'arrow-up' : 'arrow-down';
        lastReturnEl.innerHTML = `
            <span class="${returnClass}">
                <i class="fas fa-${returnIcon} me-1"></i>
                ${data.last_return >= 0 ? '+' : ''}${data.last_return}%
            </span>
        `;

        // Scores
        updateScoreDisplay('patternScore', data.pattern_score);
        updateScoreDisplay('sentimentScore', data.sentiment_score);
        updateScoreDisplay('valuationScore', data.valuation_score);

        // News count
        document.getElementById('newsCount').textContent = `From ${data.news_count} recent articles`;

        // Analysis summary
        const summaryList = document.getElementById('analysisSummary');
        summaryList.innerHTML = '';
        
        Object.values(data.analysis_summary).forEach(summary => {
            const li = document.createElement('li');
            li.className = 'mb-2';
            li.innerHTML = `<i class="fas fa-info-circle text-info me-2"></i>${summary}`;
            summaryList.appendChild(li);
        });

        // Add sentiment summary if available
        if (data.sentiment_summary) {
            const sentimentLi = document.createElement('li');
            sentimentLi.className = 'mb-2 alert alert-info p-2';
            sentimentLi.innerHTML = `<i class="fas fa-robot text-primary me-2"></i><strong>AI Analysis:</strong> ${data.sentiment_summary}`;
            summaryList.appendChild(sentimentLi);
        }

        // Show results with animation
        resultsSection.style.display = 'block';
        resultsSection.classList.add('fade-in');
        
        // Scroll to results
        setTimeout(() => {
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }

    function updateScoreDisplay(elementId, score) {
        const element = document.getElementById(elementId);
        element.textContent = score;
        
        // Add appropriate color class
        element.className = '';
        if (score > 0) {
            element.classList.add('score-positive');
        } else if (score < 0) {
            element.classList.add('score-negative');
        } else {
            element.classList.add('score-neutral');
        }
    }

    function getPredictionIcon(prediction) {
        switch (prediction.toLowerCase()) {
            case 'up': return 'arrow-up';
            case 'down': return 'arrow-down';
            default: return 'question';
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
        errorSection.classList.add('fade-in');
        
        // Scroll to error
        setTimeout(() => {
            errorSection.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }

    function hideError() {
        errorSection.style.display = 'none';
        errorSection.classList.remove('fade-in');
    }

    function hideResults() {
        resultsSection.style.display = 'none';
        resultsSection.classList.remove('fade-in');
    }

    // Enter key support for ticker input
    tickerInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            form.dispatchEvent(new Event('submit'));
        }
    });

    // Focus ticker input on page load
    tickerInput.focus();
});
