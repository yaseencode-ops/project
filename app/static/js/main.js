async function analyzeCode() {
    const codeInput = document.getElementById('code-input');
    const resultsDiv = document.getElementById('results');
    const analyzeBtn = document.querySelector('.analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const spinner = analyzeBtn.querySelector('.spinner');
    
    // Validate input
    if (!codeInput.value.trim()) {
        showError('Please enter some code to analyze');
        return;
    }

    // Show loading state
    btnText.textContent = 'Analyzing...';
    spinner.classList.remove('hidden');
    analyzeBtn.disabled = true;
    
    resultsDiv.innerHTML = '<div class="loading">Analyzing your code</div>';
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: codeInput.value
            })
        });
        
        const data = await response.json();
        resultsDiv.innerHTML = '';
        
        if (!response.ok) {
            showError(`Server Error: ${data.error || 'Unknown error'}`);
            return;
        }
        
        if (data.error) {
            showError(`Error: ${data.error}`);
            return;
        }
        
        if (data.issues && data.issues.length > 0) {
            const categories = categorizeIssues(data.issues);
            
            // Add summary
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'analysis-summary';
            summaryDiv.innerHTML = `
                <h3>ML Code Analysis Results</h3>
                <p>Found ${data.issues.length} issue${data.issues.length > 1 ? 's' : ''}</p>
            `;
            resultsDiv.appendChild(summaryDiv);

            // Display issues by category
            Object.entries(categories)
                .filter(([_, category]) => category.issues.length > 0)
                .sort((a, b) => a[1].priority - b[1].priority)
                .forEach(([_, category]) => {
                    if (category.issues.length > 0) {
                        const categoryDiv = document.createElement('div');
                        categoryDiv.className = 'error-category';
                        categoryDiv.innerHTML = `
                            <h4>${category.title} (${category.issues.length})</h4>
                            <div class="category-issues"></div>
                        `;
                        
                        const issuesContainer = categoryDiv.querySelector('.category-issues');
                        category.issues.forEach(issue => {
                            issuesContainer.appendChild(displayIssue(issue));
                        });
                        
                        resultsDiv.appendChild(categoryDiv);
                    }
                });
        } else {
            const successDiv = document.createElement('div');
            successDiv.className = 'issue success';
            successDiv.innerHTML = `
                <h3>✓ Code Analysis Complete</h3>
                <p>No issues found! Your code looks good.</p>
            `;
            resultsDiv.appendChild(successDiv);
        }
    } catch (error) {
        console.error('Error:', error);
        showError('An error occurred while analyzing the code.');
    } finally {
        // Reset button state
        btnText.textContent = 'Analyze Code';
        spinner.classList.add('hidden');
        analyzeBtn.disabled = false;
    }
}

function showError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
        <div class="issue error">
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}

function updateLineNumbers() {
    const textarea = document.getElementById('code-input');
    const lineNumbers = document.getElementById('line-numbers');
    const lines = textarea.value.split('\n');
    
    lineNumbers.innerHTML = lines.map((_, i) => i + 1).join('\n');
}

function clearCode() {
    const textarea = document.getElementById('code-input');
    const resultsDiv = document.getElementById('results');
    
    textarea.value = '';
    resultsDiv.innerHTML = '';
    updateLineNumbers();
}

function highlightLine(lineNumber) {
    const textarea = document.getElementById('code-input');
    const lines = textarea.value.split('\n');
    
    if (lineNumber > 0 && lineNumber <= lines.length) {
        const lineHeight = textarea.clientHeight / lines.length;
        const highlight = document.createElement('div');
        highlight.className = 'issue-highlight';
        highlight.style.top = `${(lineNumber - 1) * lineHeight}px`;
        highlight.style.height = `${lineHeight}px`;
        
        textarea.parentElement.appendChild(highlight);
        
        setTimeout(() => highlight.remove(), 2000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('code-input');
    
    // Initialize line numbers
    updateLineNumbers();
    
    // Update line numbers on input
    textarea.addEventListener('input', updateLineNumbers);
    
    // Handle tab key
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            
            this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
            this.selectionStart = this.selectionEnd = start + 4;
            updateLineNumbers();
        }
    });
    
    // Add click handler for line numbers
    document.getElementById('line-numbers').addEventListener('click', function(e) {
        const lineNumber = parseInt(e.target.textContent);
        if (!isNaN(lineNumber)) {
            highlightLine(lineNumber);
        }
    });
});

function categorizeIssues(issues) {
    const categories = {
        'data': {
            title: 'Data-Related Errors',
            issues: [],
            priority: 1
        },
        'model': {
            title: 'Model-Related Errors',
            issues: [],
            priority: 2
        },
        'algorithm': {
            title: 'Algorithm/Training Errors',
            issues: [],
            priority: 3
        },
        'hyperparameter': {
            title: 'Hyperparameter Tuning Errors',
            issues: [],
            priority: 4
        },
        'evaluation': {
            title: 'Evaluation and Testing Errors',
            issues: [],
            priority: 5
        },
        'deployment': {
            title: 'Deployment Errors',
            issues: [],
            priority: 6
        },
        'syntax': {
            title: 'Code and Syntax Errors',
            issues: [],
            priority: 7
        },
        'runtime': {
            title: 'Runtime Errors',
            issues: [],
            priority: 8
        }
    };

    issues.forEach(issue => {
        // Categorize issues based on their message content
        if (issue.message.match(/data|input|output|format|missing|null|nan/i)) {
            categories.data.issues.push(issue);
        }
        else if (issue.message.match(/model|prediction|inference|weights|bias/i)) {
            categories.model.issues.push(issue);
        }
        else if (issue.message.match(/algorithm|training|learning|gradient|loss/i)) {
            categories.algorithm.issues.push(issue);
        }
        else if (issue.message.match(/parameter|hyperparameter|tuning|optimization/i)) {
            categories.hyperparameter.issues.push(issue);
        }
        else if (issue.message.match(/evaluation|testing|validation|accuracy|metrics/i)) {
            categories.evaluation.issues.push(issue);
        }
        else if (issue.message.match(/deploy|production|service|api|endpoint/i)) {
            categories.deployment.issues.push(issue);
        }
        else if (issue.message.match(/syntax|indent|import|definition|naming/i)) {
            categories.syntax.issues.push(issue);
        }
        else {
            categories.runtime.issues.push(issue);
        }
    });

    return categories;
}

function displayIssue(issue) {
    const issueDiv = document.createElement('div');
    issueDiv.className = `issue ${issue.severity}`;
    
    issueDiv.innerHTML = `
        <div class="issue-header">
            ${issue.line > 0 ? `<span class="line-badge">Line ${issue.line}</span>` : ''}
            <span class="accuracy-badge">${(issue.confidence * 100).toFixed(0)}% confidence</span>
        </div>
        <p class="issue-message">${issue.message}</p>
        <div class="suggestion">
            <strong>💡 Suggestion:</strong> ${issue.suggestion}
        </div>
    `;
    
    return issueDiv;
}

function getCodePreview(lineNumber) {
    const textarea = document.getElementById('code-input');
    const lines = textarea.value.split('\n');
    const start = Math.max(0, lineNumber - 2);
    const end = Math.min(lines.length, lineNumber + 1);
    
    return lines.slice(start, end)
        .map((line, i) => `<div class="preview-line${i + start + 1 === lineNumber ? ' highlight' : ''}">${line}</div>`)
        .join('');
} 