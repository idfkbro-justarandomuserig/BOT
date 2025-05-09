// Dashboard real-time updates using jQuery
$(document).ready(function() {
    // Set up auto-refresh for dashboard data
    let refreshInterval;
    
    function startAutoRefresh() {
        refreshInterval = setInterval(refreshDashboardData, 15000); // every 15 seconds
    }
    
    function stopAutoRefresh() {
        clearInterval(refreshInterval);
    }
    
    function refreshDashboardData() {
        // Show loading indicator
        $("#dashboard-refresh-indicator").addClass("spinner-border spinner-border-sm");
        
        // Get data from API
        $.getJSON('/api/bot/status', function(botData) {
            // Update bot status
            const statusElement = $("#bot-status");
            if (botData.status === 'online') {
                statusElement.html('<span class="text-success">Online</span>');
            } else {
                statusElement.html('<span class="text-danger">Offline</span>');
            }
            
            // Update global coin boost
            if (botData.global_coin_boost_active) {
                $("#global-coin-boost").html('<span class="badge bg-success">Active</span>');
            } else {
                $("#global-coin-boost").html('<span class="badge bg-secondary">Inactive</span>');
            }
            
            // Update other bot data
            $("#slot-jackpot").text(botData.slot_jackpot_pool || 0);
            $("#lottery-pot").text(botData.lottery_pot || 0);
            $("#lottery-tickets").text((botData.lottery_tickets || []).length);
            $("#rented-vcs").text(Object.keys(botData.rented_vcs || {}).length);
            
            // Update goals
            const goalsContainer = $("#community-goals");
            goalsContainer.empty();
            
            if (botData.community_goals_progress && Object.keys(botData.community_goals_progress).length > 0) {
                for (const [goalId, progress] of Object.entries(botData.community_goals_progress)) {
                    const progressPercentage = (progress < 100 ? progress : 100);
                    const goalHtml = `
                        <div class="mb-3">
                            <div class="d-flex justify-content-between mb-1">
                                <span>${goalId}</span>
                                <span>${progress}%</span>
                            </div>
                            <div class="progress" style="height: 10px;">
                                <div class="progress-bar bg-info" role="progressbar" 
                                     style="width: ${progressPercentage}%" 
                                     aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        </div>
                    `;
                    goalsContainer.append(goalHtml);
                }
            } else {
                goalsContainer.html('<p class="text-muted">No active community goals found.</p>');
            }
            
            // Hide loading indicator
            $("#dashboard-refresh-indicator").removeClass("spinner-border spinner-border-sm");
        })
        .fail(function() {
            // If API call fails
            $("#dashboard-refresh-indicator").removeClass("spinner-border spinner-border-sm");
            $("#dashboard-status").html('<div class="alert alert-danger">Failed to refresh dashboard data</div>');
        });
    }
    
    // Add refresh button functionality
    $("#refresh-dashboard").on("click", function() {
        refreshDashboardData();
    });
    
    // Toggle auto-refresh
    $("#toggle-auto-refresh").on("click", function() {
        const btn = $(this);
        if (btn.data("active")) {
            stopAutoRefresh();
            btn.data("active", false);
            btn.html('<span data-feather="play-circle"></span> Start Auto-Refresh');
            feather.replace();
        } else {
            startAutoRefresh();
            refreshDashboardData(); // Immediate first refresh
            btn.data("active", true);
            btn.html('<span data-feather="pause-circle"></span> Pause Auto-Refresh');
            feather.replace();
        }
    });
    
    // Activate charts if present
    if ($("#usersChart").length) {
        const ctx = document.getElementById('usersChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: userActivityLabels,
                datasets: [{
                    label: 'Active Users',
                    data: userActivityData,
                    borderColor: '#0dcaf0',
                    backgroundColor: 'rgba(13, 202, 240, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Start auto-refresh if the toggle is enabled
    if ($("#toggle-auto-refresh").data("active")) {
        startAutoRefresh();
    }
});