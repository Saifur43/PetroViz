// Drilling Reports Visualizer
class DrillingReportsVisualizer {
    constructor() {
        this.chartInstances = new Map();
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        document.querySelectorAll('.report-card .card-header').forEach(header => {
            header.addEventListener('click', (e) => this.handleCardClick(e));
        });

        this.expandFirstCard();
    }

    handleCardClick(event) {
        const header = event.currentTarget;
        const card = header.closest('.report-card');
        const wasExpanded = card.classList.contains('expanded');
        const isBulk = !!window.__bulkOp;
        
        if (!isBulk) {
            document.querySelectorAll('.report-card').forEach(c => {
                if (c !== card) {
                    c.classList.remove('expanded');
                    c.querySelectorAll('.lithologyChartRow').forEach(canvas => {
                        const chartId = canvas.id;
                        if (this.chartInstances.has(chartId)) {
                            this.chartInstances.get(chartId).destroy();
                            this.chartInstances.delete(chartId);
                        }
                    });
                }
            });
        }

        if (!wasExpanded) {
            card.classList.add('expanded');
            this.renderChartsInCard(card);
        } else {
            card.classList.remove('expanded');
        }
    }

    renderChartsInCard(card) {
        setTimeout(() => {
            card.querySelectorAll('.lithologyChartRow').forEach(canvas => {
                if (!this.chartInstances.has(canvas.id)) {
                    this.renderLithologyChart(canvas);
                }
            });
        }, 50);
    }

    renderLithologyChart(canvas) {
        if (!canvas || !canvas.getContext('2d')) return;

        const ctx = canvas.getContext('2d');
        const data = this.getLithologyData(canvas);

        if (this.chartInstances.has(canvas.id)) {
            this.chartInstances.get(canvas.id).destroy();
        }

        const chart = new Chart(ctx, this.getChartConfig(data));
        this.chartInstances.set(canvas.id, chart);
        const skeleton = canvas.parentElement.querySelector('.chart-skeleton');
        if (skeleton) skeleton.style.display = 'none';
    }

    getLithologyData(canvas) {
        const data = {
            shale: parseFloat(canvas.dataset.shale) || 0,
            sand: parseFloat(canvas.dataset.sand) || 0,
            clay: parseFloat(canvas.dataset.clay) || 0,
            slit: parseFloat(canvas.dataset.slit) || 0,
            depthRange: canvas.dataset.depthRange || ''
        };

        ['shale', 'sand', 'clay', 'slit'].forEach(key => {
            if (isNaN(data[key])) data[key] = 0;
            data[key] = parseFloat(data[key].toFixed(1));
        });

        return data;
    }

    getChartConfig(data) {
        return {
            type: 'bar',
            data: {
                labels: [''],
                datasets: [
                    {
                        label: 'Shale',
                        data: [data.shale],
                        backgroundColor: '#666666',
                        borderColor: '#444444',
                        borderWidth: 0
                    },
                    {
                        label: 'Sand',
                        data: [data.sand],
                        backgroundColor: '#FFD700',
                        borderColor: '#B8860B',
                        borderWidth: 0
                    },
                    {
                        label: 'Clay',
                        data: [data.clay],
                        backgroundColor: '#CD853F',
                        borderColor: '#8B4513',
                        borderWidth: 0
                    },
                    {
                        label: 'Silt',
                        data: [data.slit],
                        backgroundColor: '#DEB887',
                        borderColor: '#D2691E',
                        borderWidth: 0
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 2,
                        right: 2,
                        top: 2,
                        bottom: 2
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 10,
                        titleFont: { size: 13, weight: 'bold' },
                        bodyFont: { size: 12 },
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${context.raw.toFixed(1)}%`
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        max: 100,
                        min: 0,
                        ticks: {
                            display: true,
                            font: {
                                size: 8,
                                weight: '400'
                            },
                            maxRotation: 0,
                            autoSkip: true,
                            autoSkipPadding: 12,
                            callback: (value) => value + '%'
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.08)'
                        }
                    },
                    y: {
                        stacked: true,
                        display: false,
                        grid: { display: false }
                    }
                },
                animation: { 
                    duration: 400,
                    easing: 'easeInOutQuart'
                }
            }
        };
    }

    expandFirstCard() {
        const firstCard = document.querySelector('.report-card');
        if (firstCard) {
            firstCard.classList.add('expanded');
            setTimeout(() => {
                this.renderChartsInCard(firstCard);
            }, 100);
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded! Make sure the CDN is accessible.');
        return;
    }
    
    new DrillingReportsVisualizer();
});