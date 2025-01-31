document.addEventListener('DOMContentLoaded', function() {
    // Gemeenschappelijke Chart.js opties
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                grid: {
                    display: false,
                    drawBorder: false
                },
                ticks: {
                    color: '#94a3b8'
                }
            },
            y: {
                grid: {
                    color: 'rgba(148, 163, 184, 0.1)',
                    drawBorder: false
                },
                ticks: {
                    color: '#94a3b8',
                    callback: (value) => `$${value/1000}k`
                }
            }
        }
    };

    // Revenue Chart
    const revenueChart = new Chart(
        document.getElementById('revenueChart').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: ['Jun 2023', 'Jul 2023', 'Aug 2023', 'Sep 2023', 'Oct 2023', 'Nov 2023', 'Dec 2023', 'Jan 2024'],
                datasets: [{
                    data: [300000, 400000, 350000, 450000, 500000, 480000, 600000, 754588],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: '#6366f1'
                }]
            },
            options: {
                ...commonOptions,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                height: 300
            }
        }
    );

    // Sales Plan Chart (Donut)
    const salesPlanChart = new Chart(
        document.getElementById('salesPlanChart').getContext('2d'),
        {
            type: 'doughnut',
            data: {
                labels: ['Base Plan', 'Best Case'],
                datasets: [{
                    data: [65.78, 50.78],
                    backgroundColor: ['#ffffff', '#6366f1'],
                    borderWidth: 0,
                    cutout: '80%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        }
    );

    // Growth Chart
    const growthChart = new Chart(
        document.getElementById('growthChart').getContext('2d'),
        {
            type: 'bar',
            data: {
                labels: ['Oct 2023', 'Nov 2023', 'Dec 2023', 'Jan 2024'],
                datasets: [{
                    data: [2.31, -4.68, 3.45, 8.50],
                    backgroundColor: (context) => {
                        const value = context.dataset.data[context.dataIndex];
                        return value < 0 ? '#ef4444' : '#6366f1';
                    },
                    borderRadius: 4
                }]
            },
            options: {
                ...commonOptions,
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        },
                        ticks: {
                            color: '#94a3b8',
                            callback: (value) => `${value}%`
                        }
                    }
                }
            }
        }
    );

    // Event Listeners voor interactiviteit
    document.querySelectorAll('.header-tabs button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelector('.header-tabs button.active').classList.remove('active');
            button.classList.add('active');
        });
    });
}); 